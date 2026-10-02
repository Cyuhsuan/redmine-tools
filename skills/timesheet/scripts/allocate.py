#!/usr/bin/env python3
"""Top up each day's timesheet to the target hours by spreading the shortfall over that day's rows.

Usage: allocate.py <rows.json>    (prints JSON to stdout)

Input:
{
  "target_hours": 8,
  "logged": {"2026-10-01": 1.0},          # hours already in Redmine per date
  "rows": [
    {"id": "r1", "date": "2026-10-01", "hours": 2.0, "lines": 640,
     "locked": false, "allocatable": true}
  ]
}

A row receives extra hours only when allocatable (mapped to an issue) and not locked (the user set
its hours by hand). Weight = sqrt(changed lines), so one huge diff does not take the whole
shortfall; when every eligible row has 0 lines the shortfall is split evenly. Shares are whole
0.5 h units handed out by largest remainder, so a day never goes over the target.

Any other top-level keys and row fields pass through unchanged, so the output can go straight to
render.py.
"""
import json
import math
import sys

UNIT = 0.5


def allocate_day(rows, shortfall_units):
    eligible = [r for r in rows if r.get("allocatable", True) and not r.get("locked", False)]
    if shortfall_units <= 0 or not eligible:
        return
    weights = [math.sqrt(max(r.get("lines", 0), 0)) for r in eligible]
    if sum(weights) == 0:
        weights = [1.0] * len(eligible)
    total_w = sum(weights)
    ideal = [shortfall_units * w / total_w for w in weights]
    units = [math.floor(x) for x in ideal]
    leftover = shortfall_units - sum(units)
    by_remainder = sorted(range(len(eligible)), key=lambda i: ideal[i] - units[i], reverse=True)
    for i in by_remainder[:leftover]:
        units[i] += 1
    for r, u in zip(eligible, units):
        r["added_hours"] = u * UNIT
        r["hours"] = r["base_hours"] + r["added_hours"]


def main():
    data = json.load(open(sys.argv[1]))
    target = float(data.get("target_hours", 8))
    logged = data.get("logged", {})
    rows = data["rows"]
    for r in rows:
        r["base_hours"] = float(r["hours"])
        r["added_hours"] = 0.0

    days = {}
    for r in rows:
        days.setdefault(r["date"], []).append(r)

    summary = {}
    for date, day_rows in sorted(days.items()):
        already = float(logged.get(date, 0))
        # Unmapped rows are never sent, so they do not count toward the day's total.
        planned = sum(r["base_hours"] for r in day_rows if r.get("allocatable", True))
        shortfall = target - already - planned
        allocate_day(day_rows, math.floor(max(shortfall, 0) / UNIT + 1e-9))
        final = sum(r["hours"] for r in day_rows if r.get("allocatable", True))
        summary[date] = {"logged": already, "before": planned, "after": final,
                         "total_after": already + final, "over_target": already + planned > target}

    json.dump({**data, "target_hours": target, "days": summary, "rows": rows},
              sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
