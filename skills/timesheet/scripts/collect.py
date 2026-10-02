#!/usr/bin/env python3
"""Collect the user's commits from every repo open in Herdr and group them into work sessions.

Usage: collect.py [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--gap-hours 2] [--lead-hours 0.5]

Prints JSON to stdout. Read-only: runs `herdr pane list`, `git rev-parse`, `git log`,
`git status`. Never writes anywhere.
"""
import argparse
import datetime as dt
import json
import subprocess
import sys


def run(args, cwd=None):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def herdr_repos():
    panes = json.loads(run(["herdr", "pane", "list"]))["result"]["panes"]
    repos = {}
    skipped = []
    for p in panes:
        cwd = p.get("cwd")
        if not cwd:
            continue
        try:
            root = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd).strip()
        except RuntimeError:
            skipped.append({"pane_id": p["pane_id"], "cwd": cwd, "reason": "not a git repo"})
            continue
        repos.setdefault(root, []).append(p["pane_id"])
    return repos, skipped


# Generated or vendored files that would swamp a line count without reflecting effort.
IGNORED_SUFFIXES = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "packages.lock.json",
                    ".min.js", ".min.css", ".map", ".Designer.cs", "ModelSnapshot.cs")


def changed_lines(repo, sha):
    total = 0
    for line in run(["git", "show", "--numstat", "--format=", sha], cwd=repo).splitlines():
        added, deleted, path = line.split("\t", 2)
        if added == "-" or path.endswith(IGNORED_SUFFIXES):
            continue  # binary or generated
        total += int(added) + int(deleted)
    return total


def round_half(h):
    return max(0.5, round(h * 2) / 2)


def commits(repo, since, until):
    email = run(["git", "config", "user.email"], cwd=repo).strip()
    # --since filters on committer date; the author-date check below is the real filter.
    out = run([
        "git", "log", "--all", "--no-merges", "--source", f"--author={email}",
        f"--since={since} 00:00", f"--until={until} 23:59:59",
        "--date=iso-strict", "--format=%H%x1f%h%x1f%aI%x1f%S%x1f%s",
    ], cwd=repo)
    lo = dt.date.fromisoformat(since)
    hi = dt.date.fromisoformat(until)
    result = []
    for line in out.splitlines():
        full, short, ad, ref, subject = line.split("\x1f", 4)
        t = dt.datetime.fromisoformat(ad).astimezone()
        if not (lo <= t.date() <= hi):
            continue
        if ref.startswith("refs/remotes/"):
            # refs/remotes/<remote>/<branch> -> <branch>, so local and pushed commits group together
            ref = ref.split("/", 3)[-1]
        ref = ref.removeprefix("refs/heads/")
        result.append({"hash": short, "time": t.isoformat(timespec="minutes"),
                       "ref": ref, "subject": subject, "lines": changed_lines(repo, full)})
    result.sort(key=lambda c: c["time"])
    return email, result


def sessions(cs, gap_h, lead_h):
    """Split one ref's commits on the same day into sessions where consecutive gaps <= gap_h."""
    out = []
    for c in cs:
        t = dt.datetime.fromisoformat(c["time"])
        cur = out[-1] if out else None
        if cur and cur["_day"] == t.date() and (t - cur["_last"]).total_seconds() <= gap_h * 3600:
            cur["commits"].append(c)
            cur["_last"] = t
        else:
            out.append({"_day": t.date(), "_first": t, "_last": t, "commits": [c]})
    for s in out:
        span = (s["_last"] - s["_first"]).total_seconds() / 3600
        s["date"] = s["_day"].isoformat()
        s["start"] = s["_first"].strftime("%H:%M")
        s["end"] = s["_last"].strftime("%H:%M")
        s["estimated_hours"] = round_half(span + lead_h)
        s["lines"] = sum(c["lines"] for c in s["commits"])
        for k in ("_day", "_first", "_last"):
            del s[k]
    return out


def main():
    ap = argparse.ArgumentParser()
    today = dt.date.today().isoformat()
    ap.add_argument("--since", default=today)
    ap.add_argument("--until", default=None)
    ap.add_argument("--gap-hours", type=float, default=2.0)
    ap.add_argument("--lead-hours", type=float, default=0.5)
    a = ap.parse_args()
    until = a.until or a.since

    repos, skipped = herdr_repos()
    report = {"since": a.since, "until": until, "gap_hours": a.gap_hours,
              "lead_hours": a.lead_hours, "repos": [], "skipped_panes": skipped}
    for root, pane_ids in sorted(repos.items()):
        entry = {"repo": root, "panes": pane_ids}
        try:
            email, cs = commits(root, a.since, until)
            branch = run(["git", "branch", "--show-current"], cwd=root).strip()
            dirty = run(["git", "status", "--short"], cwd=root).splitlines()
        except RuntimeError as e:
            entry["error"] = str(e)
            report["repos"].append(entry)
            continue
        by_ref = {}
        for c in cs:
            by_ref.setdefault(c["ref"], []).append(c)
        entry.update({
            "author": email,
            "current_branch": branch,
            "uncommitted": dirty,
            "groups": [{"ref": ref, "sessions": sessions(v, a.gap_hours, a.lead_hours)}
                       for ref, v in by_ref.items()],
        })
        report["repos"].append(entry)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
