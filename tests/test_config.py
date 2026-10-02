"""Scope editing through the config script's CLI."""
import shutil
import unittest

from fixtures import ScriptTest


class Scope(ScriptTest):
    def test_empty_scope_before_any_config(self):
        self.assertEqual(self.script("config.py", "list"), {"scope": []})

    def test_add_list_remove(self):
        repo = self.make_repo("a")
        self.assertEqual(self.script("config.py", "add", repo),
                         {"status": "added", "repo": str(repo)})
        self.assertEqual(self.script("config.py", "list"), {"scope": [str(repo)]})
        self.assertEqual(self.config_file()["scope"], [str(repo)])
        self.assertEqual(self.script("config.py", "remove", repo),
                         {"status": "removed", "repo": str(repo)})
        self.assertEqual(self.script("config.py", "list"), {"scope": []})

    def test_config_location_follows_xdg_config_home(self):
        shown = self.script("config.py", "show")
        self.assertEqual(shown["path"], str(self.tmp / "config/timesheet-tools/config.json"))

    def test_subdirectory_is_saved_as_git_root(self):
        repo = self.make_repo("a")
        (repo / "src/deep").mkdir(parents=True)
        self.assertEqual(self.script("config.py", "add", repo / "src/deep")["repo"], str(repo))

    def test_linked_worktree_is_the_same_repo(self):
        repo = self.make_repo("a")
        self.commit(repo, "2026-10-01T10:00:00+08:00", "init")
        self.git(repo, "worktree", "add", "-q", str(self.tmp / "a-wt"), "-b", "feature")
        self.script("config.py", "add", repo)
        result = self.script("config.py", "add", self.tmp / "a-wt")
        self.assertEqual(result, {"status": "exists", "repo": str(repo)})
        self.assertEqual(self.config_file()["scope"], [str(repo)])

    def test_worktree_added_first_is_saved_as_main_root(self):
        repo = self.make_repo("a")
        self.commit(repo, "2026-10-01T10:00:00+08:00", "init")
        self.git(repo, "worktree", "add", "-q", str(self.tmp / "a-wt"), "-b", "feature")
        self.assertEqual(self.script("config.py", "add", self.tmp / "a-wt")["repo"], str(repo))

    def test_non_git_directory_is_rejected(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        result = self.script("config.py", "add", plain, expect=1)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "not a git repository")
        self.assertEqual(self.script("config.py", "list"), {"scope": []})

    def test_nonexistent_path_is_rejected(self):
        result = self.script("config.py", "add", self.tmp / "nope", expect=1)
        self.assertEqual(result["reason"], "path does not exist")

    def test_duplicate_add_is_skipped(self):
        repo = self.make_repo("a")
        self.script("config.py", "add", repo)
        self.assertEqual(self.script("config.py", "add", repo)["status"], "exists")
        self.assertEqual(self.config_file()["scope"], [str(repo)])

    def test_missing_repo_can_still_be_removed(self):
        repo = self.make_repo("a")
        self.script("config.py", "add", repo)
        shutil.rmtree(repo)
        self.assertEqual(self.script("config.py", "remove", repo)["status"], "removed")

    def test_removing_unknown_repo_reports_not_found(self):
        self.assertEqual(self.script("config.py", "remove", self.tmp / "x", expect=1)["status"],
                         "not_found")


if __name__ == "__main__":
    unittest.main()
