"""The Timesheet table: rows.json -> allocate.py -> render.py, compared against fixed snapshots."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from fixtures import SCRIPTS

SNAPSHOTS = pathlib.Path(__file__).parent / "snapshots"
D1, D2 = "2026-10-01", "2026-10-02"


def row(id, date, hours, lines, ticket=None, **extra):
    r = {"id": id, "date": date, "hours": hours, "lines": lines,
         "allocatable": ticket is not None, "locked": False}
    if ticket:
        r.update(ticket=ticket, activity="9 程式開發", mapping="明確票號")
    return {**r, **extra}


FULL = {
    "since": D1, "until": D2, "target_hours": 8,
    "logged": {D1: 1.0, D2: 7.5},
    "rows": [
        row("a", D1, 2.0, 400, ticket="57379", subject="開發-B1-7-0 公司治理",
            summary="新增表單定義 | 欄位驗證", basis="09:00–10:30 d26b18a…378e3fa (3)",
            sessions=[{"repo": "/w/api", "start": "09:00", "end": "10:30"}]),
        row("b", D1, 1.0, 100, ticket="57400", subject="[後台] 表單管理",
            activity="11 Code Review(審核)", mapping="主旨比對",
            summary="審核表單 PR", basis="10:00–10:45 aaa1111 (1)",
            sessions=[{"repo": "/w/web", "start": "10:00", "end": "10:45"}]),
        row("u", D1, 0.5, 50, summary="調整 CI 設定", basis="16:00 bbb2222 (1)",
            sessions=[{"repo": "/w/api", "start": "16:00", "end": "16:00"}]),
        row("c", D2, 1.0, 10, ticket="57379", subject="開發-B1-7-0 公司治理",
            summary="修正驗證錯誤", basis="11:00 ccc3333 (1)",
            sessions=[{"repo": "/w/api", "start": "11:00", "end": "11:00"}]),
    ],
    "existing_entries": [{"ticket": "57379", "date": D2}],
    "missing_repos": [{"repo": "/w/gone", "reason": "path does not exist"}],
}


def run(script, path):
    return subprocess.run([sys.executable, str(SCRIPTS / script), str(path)],
                          capture_output=True, text=True, check=True).stdout


def render(data):
    with tempfile.TemporaryDirectory() as tmp:
        rows = pathlib.Path(tmp) / "rows.json"
        rows.write_text(json.dumps(data, ensure_ascii=False))
        allocated = pathlib.Path(tmp) / "allocated.json"
        allocated.write_text(run("allocate.py", rows))
        return run("render.py", allocated)


class Render(unittest.TestCase):
    def assertSnapshot(self, name, text):
        path = SNAPSHOTS / name
        if os.environ.get("UPDATE_SNAPSHOTS"):
            path.write_text(text)
        self.assertEqual(text, path.read_text())

    def test_full_timesheet_matches_snapshot(self):
        self.assertSnapshot("full.md", render(FULL))

    def test_no_commits_matches_snapshot(self):
        self.assertSnapshot("empty.md", render({"since": D1, "until": D1, "rows": []}))

    def test_same_input_renders_identically(self):
        self.assertEqual(render(FULL), render(FULL))

    def test_header_has_the_eleven_columns_in_order(self):
        header = render(FULL).splitlines()[2]
        self.assertEqual([c.strip() for c in header.strip("|").split("|")],
                         ["#", "日期", "票號", "主旨", "活動", "估算", "補分配", "時數",
                          "說明", "依據", "對應方式"])


if __name__ == "__main__":
    unittest.main()
