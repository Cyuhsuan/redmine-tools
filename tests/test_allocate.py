"""Characterization tests for the Top-up script: JSON in, JSON out, through its CLI."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "skills/timesheet/scripts/allocate.py"
DAY = "2026-10-01"


def row(id, hours, lines, date=DAY, **flags):
    return {"id": id, "date": date, "hours": hours, "lines": lines, **flags}


def allocate(rows, logged=None, target=8):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"target_hours": target, "logged": logged or {}, "rows": rows}, f)
    out = subprocess.run([sys.executable, str(SCRIPT), f.name],
                         capture_output=True, text=True, check=True).stdout
    pathlib.Path(f.name).unlink()
    result = json.loads(out)
    result["by_id"] = {r["id"]: r for r in result["rows"]}
    return result


class TopUp(unittest.TestCase):
    def test_shortfall_is_split_by_square_root_of_changed_lines(self):
        r = allocate([row("a", 1.0, 100), row("b", 1.0, 400)])
        # weights 10 : 20 over 12 half-hour units -> 4 : 8
        self.assertEqual(r["by_id"]["a"]["added_hours"], 2.0)
        self.assertEqual(r["by_id"]["b"]["added_hours"], 4.0)
        self.assertEqual(r["days"][DAY]["total_after"], 8.0)

    def test_largest_remainder_lands_the_day_exactly_on_target(self):
        r = allocate([row("a", 1.0, 50), row("b", 1.0, 50), row("c", 1.0, 50)])
        added = sorted(x["added_hours"] for x in r["rows"])
        self.assertEqual(added, [1.5, 1.5, 2.0])
        self.assertEqual(r["days"][DAY]["total_after"], 8.0)

    def test_all_hours_stay_in_half_hour_units(self):
        r = allocate([row("a", 0.5, 7), row("b", 1.5, 1234), row("c", 2.0, 99)])
        for x in r["rows"]:
            self.assertEqual(x["hours"] * 2, int(x["hours"] * 2))

    def test_locked_row_keeps_its_hours_and_the_rest_rebalance(self):
        r = allocate([row("a", 3.0, 10000, locked=True), row("b", 1.0, 10)])
        self.assertEqual(r["by_id"]["a"]["hours"], 3.0)
        self.assertEqual(r["by_id"]["b"]["hours"], 5.0)

    def test_unmapped_row_gets_nothing_and_does_not_count(self):
        r = allocate([row("a", 2.0, 10), row("u", 3.0, 10000, allocatable=False)])
        self.assertEqual(r["by_id"]["u"]["hours"], 3.0)
        self.assertEqual(r["by_id"]["u"]["added_hours"], 0.0)
        self.assertEqual(r["by_id"]["a"]["hours"], 8.0)
        self.assertEqual(r["days"][DAY]["total_after"], 8.0)

    def test_already_logged_hours_reduce_the_shortfall(self):
        r = allocate([row("a", 1.0, 10)], logged={DAY: 5.0})
        self.assertEqual(r["by_id"]["a"]["hours"], 3.0)
        self.assertEqual(r["days"][DAY]["total_after"], 8.0)

    def test_day_at_or_over_target_is_left_alone_and_flagged(self):
        r = allocate([row("a", 2.0, 10)], logged={DAY: 7.0})
        self.assertEqual(r["by_id"]["a"]["hours"], 2.0)
        self.assertTrue(r["days"][DAY]["over_target"])

    def test_zero_changed_lines_split_evenly(self):
        r = allocate([row("a", 1.0, 0), row("b", 1.0, 0)])
        self.assertEqual(r["by_id"]["a"]["added_hours"], 3.0)
        self.assertEqual(r["by_id"]["b"]["added_hours"], 3.0)

    def test_shortfall_below_half_hour_unit_is_not_rounded_up(self):
        r = allocate([row("a", 1.0, 10)], logged={DAY: 0.25})
        self.assertEqual(r["by_id"]["a"]["hours"], 7.5)
        self.assertLessEqual(r["days"][DAY]["total_after"], 8.0)

    def test_days_are_topped_up_independently(self):
        other = "2026-10-02"
        r = allocate([row("a", 1.0, 10), row("b", 4.0, 10, date=other)])
        self.assertEqual(r["by_id"]["a"]["hours"], 8.0)
        self.assertEqual(r["by_id"]["b"]["hours"], 8.0)

    def test_target_hours_comes_from_input(self):
        r = allocate([row("a", 1.0, 10)], target=6)
        self.assertEqual(r["by_id"]["a"]["hours"], 6.0)


if __name__ == "__main__":
    unittest.main()
