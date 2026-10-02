"""One-time Import of a Herdr workspace's Repos into the Scope, with a fake `herdr` on PATH."""
import unittest

from fixtures import ScriptTest


class Import(ScriptTest):
    def test_imports_the_current_workspace_by_default(self):
        a, b = self.make_repo("a"), self.make_repo("b")
        self.fake_herdr({"w1": [a, b / "."], "w2": [self.make_repo("c")]}, current="w1")
        result = self.script("config.py", "import-herdr")
        self.assertEqual(result, {"workspace": "w1", "added": [str(a), str(b)],
                                  "exists": [], "skipped": []})
        self.assertEqual(self.config_file()["scope"], [str(a), str(b)])

    def test_imports_a_named_workspace(self):
        a, c = self.make_repo("a"), self.make_repo("c")
        self.fake_herdr({"w1": [a], "w2": [c]}, current="w1")
        result = self.script("config.py", "import-herdr", "--workspace", "w2")
        self.assertEqual(result["added"], [str(c)])
        self.assertEqual(self.config_file()["scope"], [str(c)])

    def test_reports_added_existing_and_skipped(self):
        a, b = self.make_repo("a"), self.make_repo("b")
        plain = self.tmp / "plain"
        plain.mkdir()
        self.script("config.py", "add", a)
        self.fake_herdr({"w1": [a, b, b / ".", plain]})
        result = self.script("config.py", "import-herdr")
        self.assertEqual(result["added"], [str(b)])
        self.assertEqual(result["exists"], [str(a)])
        self.assertEqual(result["skipped"], [{"pane_id": "w1:p4", "cwd": str(plain),
                                              "reason": "not a git repository"}])

    def test_outside_herdr_changes_nothing(self):
        a = self.make_repo("a")
        self.script("config.py", "add", a)
        self.env.pop("HERDR_ENV", None)
        result = self.script("config.py", "import-herdr", expect=1)
        self.assertEqual(result["error"], "not_in_herdr")
        self.assertEqual(self.config_file()["scope"], [str(a)])

    def test_unknown_workspace_is_an_error(self):
        self.fake_herdr({"w1": [self.make_repo("a")]})
        result = self.script("config.py", "import-herdr", "--workspace", "w9", expect=1)
        self.assertEqual(result["error"], "herdr_failed")
        self.assertIn("w9", result["message"])

    def test_import_is_a_snapshot(self):
        a, b = self.make_repo("a"), self.make_repo("b")
        self.fake_herdr({"w1": [a]})
        self.script("config.py", "import-herdr")
        self.fake_herdr({"w1": [b]})  # Herdr changes later
        self.assertEqual(self.script("config.py", "list"), {"scope": [str(a)]})
        self.assertEqual(set(self.config_file()), {"scope"})


if __name__ == "__main__":
    unittest.main()
