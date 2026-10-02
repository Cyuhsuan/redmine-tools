#!/usr/bin/env python3
"""Render the Timesheet review table from allocate.py's output, always in the same format.

Usage: render.py <allocated.json>    (prints markdown to stdout)

Input is allocate.py's output; it passes through everything rows.json carried:

{
  "since": "2026-10-01", "until": "2026-10-01",
  "target_hours": 8,
  "days": {...},                                  # from allocate.py
  "rows": [{
    "id": "57379@2026-10-01", "date": "2026-10-01",
    "base_hours": 2.0, "added_hours": 3.5, "hours": 5.5, "allocatable": true,
    "ticket": "57379", "subject": "...", "activity": "9 程式開發",
    "summary": "...", "basis": "14:19–15:47 d26b18a…378e3fa (7)", "mapping": "明確票號",
    "sessions": [{"repo": "/path/a", "start": "14:19", "end": "15:47"}]
  }],
  "existing_entries": [{"ticket": "57379", "date": "2026-10-01"}],   # already on the Platform
  "missing_repos": [{"repo": "/path/gone", "reason": "path does not exist"}]   # from collect.py
}

Unmapped rows have `allocatable: false` and no ticket. Output: the 11-column table, the per-day
totals, the ⚠ list and the Top-up note. The model never formats any of these by hand.
"""
import json
import sys

COLUMNS = ["#", "日期", "票號", "主旨", "活動", "估算", "補分配", "時數", "說明", "依據", "對應方式"]
NONE = "—"


def cell(value):
    if value is None or value == "":
        return NONE
    return str(value).replace("\n", " ").replace("|", "\\|")


def hours(h):
    return f"{float(h):.1f}"


def ticket(r):
    return f"#{r['ticket']}" if r.get("ticket") else NONE


def table(rows):
    lines = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    for n, r in enumerate(rows, 1):
        mapped = r.get("allocatable", True)
        values = [
            n, r["date"], ticket(r), r.get("subject"), r.get("activity") if mapped else None,
            hours(r["base_hours"]),
            hours(r["added_hours"]) if mapped else None,
            hours(r["hours"]) if mapped else "不送出",
            r.get("summary"), r.get("basis"), r.get("mapping") or ("未對應" if not mapped else None),
        ]
        lines.append("| " + " | ".join(cell(v) for v in values) + " |")
    return lines


def day_totals(days, target):
    lines = ["| 日期 | 已在平台 | 本次估算 | 補分配 | 送出後合計 |", "|---|---|---|---|---|"]
    for date, d in sorted(days.items()):
        total = hours(d["total_after"])
        if d["total_after"] != target:
            total += " ⚠"
        lines.append(f"| {date} | {hours(d['logged'])} | {hours(d['before'])} | "
                     f"{hours(d['after'] - d['before'])} | {total} |")
    return lines


def overlaps(rows):
    """Sessions in different Repos on the same date whose times intersect."""
    found = []
    seen = set()
    sessions = [(r["date"], s) for r in rows for s in r.get("sessions", [])]
    for i, (date_a, a) in enumerate(sessions):
        for date_b, b in sessions[i + 1:]:
            if date_a != date_b or a["repo"] == b["repo"]:
                continue
            if a["start"] <= b["end"] and b["start"] <= a["end"]:
                first, second = sorted([a, b], key=lambda s: (s["start"], s["repo"]))
                key = (date_a, first["repo"], first["start"], second["repo"], second["start"])
                if key not in seen:
                    seen.add(key)
                    found.append((date_a, first, second))
    return found


def warnings(data, rows):
    target = float(data.get("target_hours", 8))
    existing = {(str(e["ticket"]), e["date"]) for e in data.get("existing_entries", [])}
    out = []
    for n, r in enumerate(rows, 1):
        if not r.get("allocatable", True):
            out.append(f"#{n} {r['date']} 未對應：不會送出、不分配補時；指定票號後需重跑補分配")
        elif r.get("ticket") and (str(r["ticket"]), r["date"]) in existing:
            out.append(f"#{n} {ticket(r)} {r['date']} 平台上已有同票同日的工時紀錄")
    for date, d in sorted(data.get("days", {}).items()):
        if d.get("over_target"):
            out.append(f"{date} 已在平台 {hours(d['logged'])} + 本次估算 {hours(d['before'])}"
                       f" 超過每日目標 {hours(target)}，未補分配")
    for date, a, b in overlaps(rows):
        out.append(f"{date} {a['repo']} {a['start']}–{a['end']} 與 {b['repo']} "
                   f"{b['start']}–{b['end']} 時段重疊（平行作業，請決定是否都計入）")
    for m in data.get("missing_repos", []):
        out.append(f"Repo 失效：{m['repo']}（{m['reason']}）— 已跳過；說「移除 {m['repo']}」可從檢查範圍刪除")
    return out


def render(data):
    rows = sorted(data["rows"], key=lambda r: r["date"])  # stable: keeps input order within a day
    target = float(data.get("target_hours", 8))
    since, until = data.get("since"), data.get("until")
    span = since if not until or until == since else f"{since} – {until}"
    out = [f"## 工時表 {span}" if span else "## 工時表", ""]
    out += table(rows) if rows else ["（此區間沒有任何 commit）"]
    out += ["", f"### 每日合計（目標 {hours(target)} h）", ""]
    out += day_totals(data.get("days", {}), target) if data.get("days") else ["（無）"]
    out += ["", "### ⚠ 注意", ""]
    out += [f"- {w}" for w in warnings(data, rows)] or ["- 無"]
    out += ["", "補分配依改動行數的 √ 比例分配，不是實測時間；說「指定某列時數」可鎖定該列並重新分配其餘列。"]
    return "\n".join(out) + "\n"


def main():
    sys.stdout.write(render(json.load(open(sys.argv[1]))))


if __name__ == "__main__":
    main()
