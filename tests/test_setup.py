"""Platform settings written by Setup, through the config script's CLI."""
import json
import unittest

from fixtures import ScriptTest

ACTIVITIES = {"development": {"id": 9, "name": "程式開發"},
              "review": {"id": 11, "name": "Code Review(審核)"},
              "discussion": {"id": 12, "name": "問題討論"}}
SETUP = {"platform": "redmine", "activities": ACTIVITIES, "target_hours": 7.5}


class Setup(ScriptTest):
    def test_fresh_config_is_not_ready(self):
        self.assertEqual(self.script("config.py", "check"),
                         {"ready": False, "missing": ["platform", "activities"],
                          "platform": None, "target_hours": 8.0, "scope_size": 0})

    def test_setup_writes_everything_at_once(self):
        result = self.script("config.py", "setup", json.dumps(SETUP))
        self.assertTrue(result["ready"])
        config = self.config_file()
        self.assertEqual(config["platform"], "redmine")
        self.assertEqual(config["activities"], ACTIVITIES)
        self.assertEqual(config["target_hours"], 7.5)

    def test_invalid_setup_writes_nothing(self):
        bad = {**SETUP, "activities": {"development": ACTIVITIES["development"]}}
        result = self.script("config.py", "setup", json.dumps(bad), expect=1)
        self.assertEqual(result["error"], "invalid")
        self.assertFalse((self.tmp / "config/timesheet-tools/config.json").exists())

    def test_setup_keeps_the_scope(self):
        repo = self.make_repo("a")
        self.script("config.py", "add", repo)
        self.script("config.py", "setup", json.dumps(SETUP))
        self.assertEqual(self.config_file()["scope"], [str(repo)])

    def test_set_target(self):
        self.assertEqual(self.script("config.py", "set-target", "6"), {"target_hours": 6.0})
        self.assertEqual(self.config_file()["target_hours"], 6.0)
        for bad in ("0", "25", "7.3", "abc"):
            self.script("config.py", "set-target", bad, expect=1)
        self.assertEqual(self.config_file()["target_hours"], 6.0)

    def test_set_activities_validates_shape(self):
        self.script("config.py", "set-activities", json.dumps(ACTIVITIES))
        self.assertEqual(self.config_file()["activities"], ACTIVITIES)
        wrong = {**ACTIVITIES, "review": {"id": "11", "name": "x"}}
        self.script("config.py", "set-activities", json.dumps(wrong), expect=1)
        self.assertEqual(self.config_file()["activities"], ACTIVITIES)

    def test_set_platform_rejects_unknown_and_keeps_activities_when_unchanged(self):
        self.script("config.py", "set-platform", "jira", expect=1)
        self.script("config.py", "setup", json.dumps(SETUP))
        self.script("config.py", "set-platform", "redmine")
        self.assertEqual(self.config_file()["activities"], ACTIVITIES)

    def test_show_reports_path_and_config(self):
        self.script("config.py", "setup", json.dumps(SETUP))
        shown = self.script("config.py", "show")
        self.assertEqual(shown["config"]["platform"], "redmine")
        self.assertNotIn("url", json.dumps(shown).lower())

    def test_top_up_uses_the_configured_daily_target(self):
        self.script("config.py", "set-target", "6")
        rows = self.tmp / "rows.json"
        rows.write_text(json.dumps({"rows": [
            {"id": "a", "date": "2026-10-01", "hours": 1.0, "lines": 10}]}))
        out = self.script("allocate.py", rows)
        self.assertEqual(out["target_hours"], 6.0)
        self.assertEqual(out["rows"][0]["hours"], 6.0)


if __name__ == "__main__":
    unittest.main()
