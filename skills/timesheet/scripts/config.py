#!/usr/bin/env python3
"""Read and edit the user's timesheet config — currently the Scope (saved Repo list).

Usage: config.py show | list | add <path> | remove <path>

The config lives at $XDG_CONFIG_HOME/timesheet-tools/config.json (default ~/.config/...).
Every command prints JSON to stdout. `add` exits 1 when the path is rejected; `remove` exits 1
when the Repo is not in the Scope.

A Repo is stored as the root of its main worktree, so a subdirectory or a linked worktree of the
same repository resolves to the same entry and its commits are never counted twice.
"""
import json
import os
import pathlib
import subprocess
import sys


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


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("show", "list", "add", "remove") \
            or (args[0] in ("add", "remove") and len(args) != 2):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    cmd = args[0]
    data = load()
    code = 0
    if cmd == "show":
        result = {"path": str(config_path()), "config": data}
    elif cmd == "list":
        result = {"scope": data["scope"]}
    elif cmd == "add":
        result = add(data, args[1])
        if result["status"] == "added":
            save(data)
        code = 1 if result["status"] == "rejected" else 0
    else:
        result = remove(data, args[1])
        if result["status"] == "removed":
            save(data)
        code = 1 if result["status"] == "not_found" else 0
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    sys.exit(code)


if __name__ == "__main__":
    main()
