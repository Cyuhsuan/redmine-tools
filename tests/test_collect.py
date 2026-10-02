"""Commit collection from the Scope through the collect script's CLI."""
import shutil
import unittest

from fixtures import ScriptTest

DAY = "2026-10-01"


def at(time, day=DAY):
    return f"{day}T{time}:00+08:00"


class Collect(ScriptTest):
    def collect(self, *args, expect=0):
        return self.script("collect.py", "--since", DAY, *args, expect=expect)

    def add(self, repo):
        self.script("config.py", "add", repo)

    def test_empty_scope_stops_with_error(self):
        self.assertEqual(self.collect(expect=1)["error"], "empty_scope")

    def test_collects_only_repos_in_scope(self):
        a, b = self.make_repo("a"), self.make_repo("b")
        self.commit(a, at("10:00"), "work in a")
        self.commit(b, at("10:00"), "work in b")
        self.add(a)
        report = self.collect()
        self.assertEqual([r["repo"] for r in report["repos"]], [str(a)])
        self.assertEqual(report["missing_repos"], [])

    def test_sessions_split_on_gap_and_estimate_hours(self):
        a = self.make_repo("a")
        self.commit(a, at("09:00"), "one", lines=3)
        self.commit(a, at("10:30"), "two", lines=4)
        self.commit(a, at("14:00"), "three")  # 3.5 h gap -> new session
        self.add(a)
        sessions = self.collect()["repos"][0]["groups"][0]["sessions"]
        self.assertEqual([(s["start"], s["end"]) for s in sessions],
                         [("09:00", "10:30"), ("14:00", "14:00")])
        self.assertEqual([s["estimated_hours"] for s in sessions], [2.0, 0.5])
        self.assertEqual(sessions[0]["lines"], 7)

    def test_only_the_users_own_commits_in_range(self):
        a = self.make_repo("a")
        self.commit(a, at("10:00", day="2026-09-30"), "yesterday")
        self.commit(a, at("10:00"), "mine")
        self.commit(a, at("11:00"), "theirs", email="other@example.com")
        self.add(a)
        sessions = self.collect()["repos"][0]["groups"][0]["sessions"]
        self.assertEqual([c["subject"] for s in sessions for c in s["commits"]], ["mine"])

    def test_repo_filter_narrows_the_run(self):
        a, b = self.make_repo("a"), self.make_repo("b")
        for r in (a, b):
            self.commit(r, at("10:00"), "work")
            self.add(r)
        report = self.collect("--repo", b / ".")
        self.assertEqual([r["repo"] for r in report["repos"]], [str(b)])

    def test_repo_filter_outside_scope_is_an_error(self):
        a, b = self.make_repo("a"), self.make_repo("b")
        self.add(a)
        result = self.collect("--repo", b, expect=1)
        self.assertEqual(result, {"error": "not_in_scope", "repos": [str(b)]})

    def test_missing_repo_is_reported_and_others_still_collected(self):
        a, gone = self.make_repo("a"), self.make_repo("gone")
        self.commit(a, at("10:00"), "work")
        self.add(a)
        self.add(gone)
        shutil.rmtree(gone)
        report = self.collect()
        self.assertEqual([r["repo"] for r in report["repos"]], [str(a)])
        self.assertEqual(report["missing_repos"],
                         [{"repo": str(gone), "reason": "path does not exist"}])
        self.assertEqual(self.config_file()["scope"], [str(a), str(gone)])

    def test_worktree_commits_are_counted_once(self):
        a = self.make_repo("a")
        self.commit(a, at("09:00"), "init")
        self.git(a, "worktree", "add", "-q", str(self.tmp / "a-wt"), "-b", "feature")
        self.commit(self.tmp / "a-wt", at("10:00"), "feature work")
        self.add(a)
        self.add(self.tmp / "a-wt")
        report = self.collect()
        self.assertEqual(len(report["repos"]), 1)
        subjects = sorted(c["subject"] for g in report["repos"][0]["groups"]
                          for s in g["sessions"] for c in s["commits"])
        self.assertEqual(subjects, ["feature work", "init"])


if __name__ == "__main__":
    unittest.main()
