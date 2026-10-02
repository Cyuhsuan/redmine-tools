"""Shared helpers: run a timesheet script as a CLI against a throwaway config dir and git repos."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "skills/timesheet/scripts"
EMAIL = "me@example.com"


class ScriptTest(unittest.TestCase):
    """Each test gets its own temp dir, used as both XDG_CONFIG_HOME and a home for git repos."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(os.path.realpath(self._tmp.name))
        self.env = {**os.environ, "XDG_CONFIG_HOME": str(self.tmp / "config"),
                    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                    "TZ": "Asia/Taipei"}

    def tearDown(self):
        self._tmp.cleanup()

    def script(self, name, *args, expect=0):
        r = subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)],
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, expect, r.stderr or r.stdout)
        return json.loads(r.stdout)

    def config_file(self):
        return json.loads((self.tmp / "config/timesheet-tools/config.json").read_text())

    def git(self, repo, *args, date=None):
        env = dict(self.env)
        if date:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
        return subprocess.run(["git", *args], cwd=repo, env=env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def make_repo(self, name):
        repo = self.tmp / name
        repo.mkdir(parents=True)
        self.git(repo, "init", "-q", "-b", "main")
        self.git(repo, "config", "user.email", EMAIL)
        self.git(repo, "config", "user.name", "Me")
        return repo

    def commit(self, repo, date, subject, lines=1, email=EMAIL):
        """Commit `lines` new lines at `date` (ISO with offset, e.g. 2026-10-01T10:00:00+08:00)."""
        f = repo / "work.txt"
        with f.open("a") as fh:
            fh.write("x\n" * lines)
        self.git(repo, "add", ".")
        self.git(repo, "-c", f"user.email={email}", "commit", "-q", "-m", subject, date=date)

    def fake_herdr(self, workspaces, current=None):
        """Put a fake `herdr` on PATH whose `pane list --workspace <id>` returns panes with the
        given cwds; unknown workspaces fail like the real CLI. Also marks the env as in-Herdr."""
        bindir = self.tmp / "bin"
        bindir.mkdir(exist_ok=True)
        data = {ws: {"id": "cli:pane:list", "result": {"type": "pane_list", "panes": [
            {"pane_id": f"{ws}:p{i}", "workspace_id": ws, "cwd": str(cwd)}
            for i, cwd in enumerate(cwds, 1)]}} for ws, cwds in workspaces.items()}
        (bindir / "herdr.json").write_text(json.dumps(data))
        fake = bindir / "herdr"
        fake.write_text(f"""#!{sys.executable}
import json, sys
data = json.load(open({str(bindir / "herdr.json")!r}))
args = sys.argv[1:]
ws = args[args.index("--workspace") + 1]
if args[:2] != ["pane", "list"] or ws not in data:
    print(json.dumps({{"error": {{"code": "workspace_not_found",
                                 "message": f"workspace {{ws}} not found"}}}}))
    sys.exit(1)
print(json.dumps(data[ws]))
""")
        fake.chmod(0o755)
        self.env["PATH"] = f"{bindir}{os.pathsep}{self.env['PATH']}"
        self.env["HERDR_ENV"] = "1"
        self.env["HERDR_WORKSPACE_ID"] = current or next(iter(workspaces))
