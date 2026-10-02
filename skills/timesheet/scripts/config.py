#!/usr/bin/env python3
"""Read and edit the user's timesheet config: Platform settings and the Scope (saved Repo list).

Usage:
  config.py show | check | list
  config.py add <path> | remove <path> | import-herdr [--workspace <id>]
  config.py setup <json> | set-platform <name> | set-activities <json> | set-target <hours>

The config lives at $XDG_CONFIG_HOME/timesheet-tools/config.json (default ~/.config/...).
Every command prints JSON to stdout and exits 1, changing nothing, when it fails or rejects its
input. `check` reports whether Setup is complete.

Platform settings: `platform` (one of PLATFORMS), `activities` mapping each use in USES to the
Platform's {"id", "name"}, and `target_hours` (Daily target, default 8). `setup` writes all three
at once so a failed Setup never leaves a half-written config; the `set-*` commands change one.
Changing the Platform clears `activities`, which belong to the old Platform. URLs, API keys and
emails are never stored here.

`import-herdr` is a one-time Import: the Repos open in a Herdr workspace (default: the current
one) are added under the same rules as `add`. Later changes in Herdr never alter the Scope.

A Repo is stored as the root of its main worktree, so a subdirectory or a linked worktree of the
same repository resolves to the same entry and its commits are never counted twice.
"""
import json
import os
import pathlib
import subprocess
import sys


PLATFORMS = ("redmine",)
USES = ("development", "review", "discussion")
DEFAULT_TARGET = 8.0


def config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return pathlib.Path(base) / "timesheet-tools" / "config.json"


def load():
    p = config_path()
    if not p.exists():
        return {"scope": []}
    data = json.loads(p.read_text())
    data.setdefault("scope", [])
    return data


def save(data):
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(p)


def git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def repo_root(path):
    """The main worktree root for any path inside a git repo, or None if it is not in one."""
    path = os.path.realpath(os.path.expanduser(path))
    if not os.path.isdir(path):
        return None
    top = git(["rev-parse", "--show-toplevel"], path)
    if top is None:
        return None
    porcelain = git(["worktree", "list", "--porcelain"], path) or ""
    first = porcelain.split("\n\n", 1)[0].splitlines()
    if first and first[0].startswith("worktree ") and "bare" not in first:
        return os.path.realpath(first[0].removeprefix("worktree "))
    return os.path.realpath(top)


def add(data, path):
    root = repo_root(path)
    if root is None:
        reason = "path does not exist" if not os.path.exists(os.path.expanduser(path)) \
            else "not a git repository"
        return {"status": "rejected", "path": path, "reason": reason}
    if root in data["scope"]:
        return {"status": "exists", "repo": root}
    data["scope"].append(root)
    return {"status": "added", "repo": root}


def remove(data, path):
    # A Repo whose directory is gone can still be removed by the path it was saved under.
    candidates = {os.path.realpath(os.path.expanduser(path)), repo_root(path)}
    for repo in data["scope"]:
        if repo in candidates:
            data["scope"].remove(repo)
            return {"status": "removed", "repo": repo}
    return {"status": "not_found", "path": path}


def import_herdr(data, workspace):
    if os.environ.get("HERDR_ENV") != "1":
        return {"error": "not_in_herdr", "message": "Import must run inside a Herdr pane."}
    workspace = workspace or os.environ.get("HERDR_WORKSPACE_ID")
    if not workspace:
        return {"error": "no_workspace", "message": "Pass --workspace; no current workspace."}
    r = subprocess.run(["herdr", "pane", "list", "--workspace", workspace],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": "herdr_failed", "message": (r.stdout + r.stderr).strip()}
    result = {"workspace": workspace, "added": [], "exists": [], "skipped": []}
    for pane in json.loads(r.stdout)["result"]["panes"]:
        cwd = pane.get("cwd")
        if not cwd:
            continue
        outcome = add(data, cwd)
        if outcome["status"] == "rejected":
            result["skipped"].append({"pane_id": pane["pane_id"], "cwd": cwd,
                                      "reason": outcome["reason"]})
        elif outcome["repo"] not in result["added"] + result["exists"]:
            result[outcome["status"]].append(outcome["repo"])
    return result


def check(data):
    missing = [k for k in ("platform", "activities") if not data.get(k)]
    return {"ready": not missing, "missing": missing, "platform": data.get("platform"),
            "target_hours": data.get("target_hours", DEFAULT_TARGET),
            "scope_size": len(data["scope"])}


def parse_platform(name):
    if name not in PLATFORMS:
        raise ValueError(f"unknown platform {name!r}; choose one of {list(PLATFORMS)}")
    return name


def parse_activities(raw):
    acts = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(acts, dict) or set(acts) != set(USES):
        raise ValueError(f"activities must map exactly {list(USES)}")
    out = {}
    for use in USES:
        a = acts[use]
        if not isinstance(a, dict) or not isinstance(a.get("id"), int) or not a.get("name"):
            raise ValueError(f"activities.{use} must be {{\"id\": <int>, \"name\": <str>}}")
        out[use] = {"id": a["id"], "name": str(a["name"])}
    return out


def parse_target(raw):
    try:
        h = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"target hours must be a number, got {raw!r}")
    if not 0 < h <= 24 or h * 2 != int(h * 2):
        raise ValueError("target hours must be in 0.5 h steps between 0.5 and 24")
    return h


def setup(data, raw):
    s = json.loads(raw)
    data["platform"] = parse_platform(s.get("platform"))
    data["activities"] = parse_activities(s.get("activities"))
    data["target_hours"] = parse_target(s.get("target_hours", DEFAULT_TARGET))
    return check(data)


def set_platform(data, name):
    name = parse_platform(name)
    if data.get("platform") != name:
        data.pop("activities", None)
    data["platform"] = name
    return check(data)


def set_activities(data, raw):
    data["activities"] = parse_activities(raw)
    return {"activities": data["activities"]}


def set_target(data, raw):
    data["target_hours"] = parse_target(raw)
    return {"target_hours": data["target_hours"]}


def run(cmd, rest, data):
    """Returns (result, save?, exit code)."""
    if cmd == "show" and not rest:
        return {"path": str(config_path()), "config": data}, False, 0
    if cmd == "check" and not rest:
        return check(data), False, 0
    if cmd == "list" and not rest:
        return {"scope": data["scope"]}, False, 0
    if cmd == "add" and len(rest) == 1:
        r = add(data, rest[0])
        return r, r["status"] == "added", 1 if r["status"] == "rejected" else 0
    if cmd == "remove" and len(rest) == 1:
        r = remove(data, rest[0])
        return r, r["status"] == "removed", 1 if r["status"] == "not_found" else 0
    if cmd == "import-herdr" and (not rest or (len(rest) == 2 and rest[0] == "--workspace")):
        r = import_herdr(data, rest[1] if rest else None)
        if "error" in r:
            return r, False, 1
        return r, bool(r["added"]), 0
    setters = {"setup": setup, "set-platform": set_platform,
               "set-activities": set_activities, "set-target": set_target}
    if cmd in setters and len(rest) == 1:
        try:
            return setters[cmd](data, rest[0]), True, 0
        except (ValueError, json.JSONDecodeError) as e:
            return {"error": "invalid", "message": str(e)}, False, 1
    return None, False, 2


def main():
    args = sys.argv[1:]
    data = load()
    result, changed, code = run(args[0], args[1:], data) if args else (None, False, 2)
    if result is None:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    if changed:
        save(data)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    sys.exit(code)


if __name__ == "__main__":
    main()
