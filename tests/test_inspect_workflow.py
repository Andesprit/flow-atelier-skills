"""Drive the published inspect_workflow.py CLI against a recording fake `atelier`."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/flow-atelier/skills/flow-atelier/scripts/inspect_workflow.py"

# Fails loudly on anything but the two allowlisted calls; otherwise replays
# the scenario for that call and records argv, cwd and the relevant env.
FAKE = """#!{python}
import json, os, subprocess, sys, time
scenario = json.load(open(os.environ["FAKE_SCENARIO"]))
with open(os.environ["FAKE_LOG"], "a") as log:
    log.write(json.dumps({{"argv": sys.argv[1:], "cwd": os.getcwd(),
        "no_update": os.environ.get("ATELIER_NO_UPDATE_CHECK"),
        "no_bytecode": os.environ.get("PYTHONDONTWRITEBYTECODE")}}) + "\\n")
if sys.argv[1:] not in (["check", "--json", "{name}"], ["show", "--json", "{name}"]):
    sys.stderr.write("FORBIDDEN fake atelier call: %r\\n" % sys.argv[1:])
    sys.exit(99)
step = scenario[sys.argv[1]]
if step.get("mutate"):
    open(step["mutate"], "a").write("# changed\\n")
if step.get("sleep"):
    child = subprocess.Popen(["sleep", "60"])
    open(os.environ["FAKE_LOG"] + ".pid", "w").write(str(child.pid))
    time.sleep(step["sleep"])
sys.stdout.write(step.get("stdout", ""))
sys.stdout.flush()
sys.stdout.buffer.write(bytes.fromhex(step.get("raw_hex", "")))
sys.stderr.write(step.get("stderr", ""))
sys.exit(step.get("exit", 0))
"""


def check_row(path, ok=True, source="project", name="greet", required=("name",), error=None):
    return json.dumps([{"name": name, "source": source, "path": str(path), "ok": ok,
                        "error": error, "required_inputs": list(required) if ok else None}])


def show_doc(path, source="project", tasks=None, required=("name",)):
    tasks = tasks if tasks is not None else [{"name": "greet", "tool": "tool:bash", "task": "echo SECRET-PROMPT"}]
    return json.dumps({"source": source, "path": str(path), "conduit": {"name": "greet", "tasks": tasks},
                       "accepted_inputs": ["name"], "required_inputs": list(required)})


class InspectWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="inspect "))
        self.home = self.tmp / "home"
        (self.home / ".atelier/conduits").mkdir(parents=True)
        self.project = self.tmp / "project with space"
        for d in ("conduits/greet", "flows", "schedules"):
            (self.project / ".atelier" / d).mkdir(parents=True)
        self.conduit = self.project / ".atelier/conduits/greet/conduit.yaml"
        self.conduit.write_text("name: greet\n")
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.log = self.tmp / "calls.jsonl"
        self.scenario = self.tmp / "scenario.json"

    def fake(self, check=None, show=None, name="greet"):
        fake = self.bin / "atelier"
        fake.write_text(FAKE.format(python=sys.executable, name=name))
        fake.chmod(0o755)
        self.scenario.write_text(json.dumps({"check": check or {}, "show": show or {}}))

    def snapshot(self):
        return {str(p.relative_to(self.tmp)): p.is_dir() or (p.stat().st_size, p.stat().st_mtime_ns)
                for p in self.tmp.rglob("*") if not p.name.startswith("calls.jsonl") and p.parent != self.bin}

    def run_cli(self, *args, env=None, path=None):
        environ = {"PATH": f"{self.bin}:/usr/bin:/bin" if path is None else path, "HOME": str(self.home),
                   "FAKE_SCENARIO": str(self.scenario), "FAKE_LOG": str(self.log), **(env or {})}
        before = self.snapshot()
        r = subprocess.run([sys.executable, str(SCRIPT), *args], env=environ, capture_output=True, text=True, timeout=60)
        self.assertEqual(before, self.snapshot(), "the helper changed files")
        return r

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def inspect_json(self, *extra, **kw):
        r = self.run_cli(str(self.project), "greet", "--json", *extra, **kw)
        return r.returncode, json.loads(r.stdout)

    def test_valid_definition_runs_only_check_then_show_with_safe_env(self):
        self.fake({"stdout": check_row(self.conduit)}, {"stdout": show_doc(self.conduit)})
        code, rep = self.inspect_json()
        self.assertEqual(code, 0)
        self.assertEqual((rep["status"], rep["source"], rep["path"]), ("valid", "project", str(self.conduit)))
        self.assertEqual(rep["tools"], [{"task": "greet", "tool": "tool:bash"}])
        self.assertEqual((rep["required_inputs"], rep["accepted_inputs"]), (["name"], ["name"]))
        self.assertIn("atelier plan greet", rep["next"])
        self.assertIn("'", rep["next"])  # project path with a space is quoted
        self.assertNotIn("atelier run", rep["next"])
        self.assertNotIn("SECRET-PROMPT", json.dumps(rep))
        self.assertEqual([c["argv"] for c in self.calls()], [["check", "--json", "greet"], ["show", "--json", "greet"]])
        for c in self.calls():
            self.assertEqual((os.path.realpath(c["cwd"]), c["no_update"], c["no_bytecode"]),
                             (os.path.realpath(self.project), "1", "1"))
        text = self.run_cli(str(self.project), "greet").stdout
        self.assertIn("valid definition (inspected, not run)", text)
        self.assertIn("not checked:", text)

    def test_nested_workflow_suggests_recursive_check(self):
        tasks = [{"name": "child", "tool": "tool:conduit"}]
        self.fake({"stdout": check_row(self.conduit)}, {"stdout": show_doc(self.conduit, tasks=tasks)})
        self.assertIn("--recursive", self.inspect_json()[1]["next"])

    def test_broken_project_override_is_reported_not_replaced_by_global(self):
        self.fake({"exit": 1, "stdout": check_row(self.conduit, ok=False, error="conduit.yaml:5 missing description")})
        code, rep = self.inspect_json()
        self.assertEqual((code, rep["status"], rep["source"], rep["path"]), (1, "invalid", "project", str(self.conduit)))
        self.assertIn("missing description", rep["error"])
        self.assertIn("project copy is the one `atelier run` uses", rep["next"])
        self.assertEqual(len(self.calls()), 1)  # show is never called for an invalid definition

    def test_contradictory_or_malformed_check_output_is_not_inspectable(self):
        cases = {
            "empty": {"exit": 0, "stdout": ""},
            "not json": {"exit": 0, "stdout": "OK greet"},
            "exit 0 but ok false": {"exit": 0, "stdout": check_row(self.conduit, ok=False, error="x")},
            "exit 1 but ok true": {"exit": 1, "stdout": check_row(self.conduit)},
            "other row": {"exit": 0, "stdout": check_row(self.conduit, name="other")},
            "no rows": {"exit": 0, "stdout": "[]"},
            "bad source": {"exit": 0, "stdout": check_row(self.conduit, source="cache")},
        }
        for label, check in cases.items():
            with self.subTest(label):
                self.fake(check)
                code, rep = self.inspect_json()
                self.assertEqual((code, rep["status"]), (2, "not_inspectable"))

    def test_bad_show_output_reports_incomplete_not_valid(self):
        cases = {
            "show fails": {"exit": 1, "stderr": "FAIL: boom"},
            "other path": {"stdout": show_doc(self.tmp / "elsewhere.yaml")},
            "other source": {"stdout": show_doc(self.conduit, source="global")},
            "task without tool": {"stdout": show_doc(self.conduit, tasks=[{"name": "greet"}])},
            "tasks not a list": {"stdout": show_doc(self.conduit, tasks="greet")},
            "inputs disagree": {"stdout": show_doc(self.conduit, required=("other",))},
            "different conduit name": {"stdout": show_doc(self.conduit).replace('"name": "greet", "tasks"', '"name": "other", "tasks"')},
        }
        for label, show in cases.items():
            with self.subTest(label):
                self.fake({"stdout": check_row(self.conduit)}, show)
                self.conduit.write_text("name: greet\n")
                environ = {"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": str(self.home),
                           "FAKE_SCENARIO": str(self.scenario), "FAKE_LOG": str(self.log)}
                r = subprocess.run([sys.executable, str(SCRIPT), str(self.project), "greet", "--json"],
                                   env=environ, capture_output=True, text=True, timeout=60)
                rep = json.loads(r.stdout)
                self.assertEqual((r.returncode, rep["status"], rep["tools"]), (2, "not_inspectable", None))
                self.assertIn("passed `atelier check`", rep["error"])

    def test_definition_changing_during_check_or_show_is_never_reported(self):
        cases = {
            "during show": ({"stdout": check_row(self.conduit)}, {"stdout": show_doc(self.conduit), "mutate": str(self.conduit)}),
            "during valid check": ({"stdout": check_row(self.conduit), "mutate": str(self.conduit)}, {"stdout": show_doc(self.conduit)}),
            "during invalid check": ({"exit": 1, "stdout": check_row(self.conduit, ok=False, error="x"), "mutate": str(self.conduit)}, None),
        }
        for label, (check, show) in cases.items():
            with self.subTest(label):
                self.fake(check, show)
                self.conduit.write_text("name: greet\n")
                environ = {"PATH": f"{self.bin}:/usr/bin:/bin", "HOME": str(self.home),
                           "FAKE_SCENARIO": str(self.scenario), "FAKE_LOG": str(self.log)}
                r = subprocess.run([sys.executable, str(SCRIPT), str(self.project), "greet", "--json"],
                                   env=environ, capture_output=True, text=True, timeout=60)
                rep = json.loads(r.stdout)
                self.assertEqual((r.returncode, rep["status"]), (2, "not_inspectable"))
                self.assertIn("changed while it was being inspected", rep["error"])

    def test_check_selecting_an_unexpected_or_unreadable_file_is_not_inspectable(self):
        self.fake({"stdout": check_row(self.tmp / "elsewhere/conduit.yaml")})
        code, rep = self.inspect_json()
        self.assertEqual((code, rep["status"]), (2, "not_inspectable"))
        self.assertIn("not the expected project file", rep["error"])
        global_copy = self.home / ".atelier/conduits/greet/conduit.yaml"
        self.fake({"stdout": check_row(global_copy, source="global")})  # project copy exists, so global is wrong
        self.assertEqual(self.inspect_json()[0], 2)
        self.fake({"stdout": check_row(self.conduit)}, {"stdout": show_doc(self.conduit)})
        self.conduit.chmod(0)
        try:
            code, rep = self.inspect_json()
        finally:
            self.conduit.chmod(0o644)
        self.assertEqual(code, 2)
        self.assertIn("cannot read", rep["error"])

    def test_unlaunchable_cli_and_undecodable_output_give_a_report_not_a_traceback(self):
        fake = self.bin / "atelier"
        for label, body in {"missing interpreter": b"#!/nonexistent/python3\n", "exec format": b"\x00\x01garbage"}.items():
            with self.subTest(label):
                fake.write_bytes(body)
                fake.chmod(0o755)
                for extra in ([], ["--json"]):
                    r = self.run_cli(str(self.project), "greet", *extra)
                    self.assertEqual(r.returncode, 2)
                    self.assertNotIn("Traceback", r.stdout + r.stderr)
                    self.assertIn("could not be started", r.stdout)
        self.fake({"raw_hex": "5bff fe00"})
        code, rep = self.inspect_json()
        self.assertEqual((code, rep["status"]), (2, "not_inspectable"))
        self.assertIn("not JSON", rep["error"])

    def test_unsafe_conduit_name_never_calls_atelier(self):
        self.fake()
        r = self.run_cli(str(self.project), "../greet", "--json")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(self.calls(), [])

    def test_unknown_conduit_and_unsupported_cli(self):
        self.fake({"exit": 1, "stderr": "unknown conduit: greet — try 'atelier list conduits'"})
        code, rep = self.inspect_json()
        self.assertEqual((code, rep["status"]), (2, "not_inspectable"))
        self.assertIn("atelier list conduits", rep["next"])
        self.fake({"exit": 2, "stderr": "No such option: --json"})
        code, rep = self.inspect_json()
        self.assertEqual(code, 2)
        self.assertIn("does not accept", rep["error"])

    def test_missing_cli_and_bad_project_path_never_call_atelier(self):
        code, rep = self.inspect_json(path="/usr/bin:/bin")
        self.assertEqual((code, rep["status"]), (2, "not_inspectable"))
        self.assertIn("not on PATH", rep["error"])
        self.fake()
        r = self.run_cli(str(self.tmp / "nope"), "greet", "--json")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not a readable directory", json.loads(r.stdout)["error"])
        self.assertEqual(self.calls(), [])

    def test_missing_layout_is_reported_without_creating_it(self):
        self.fake()
        (self.project / ".atelier/schedules").rmdir()
        (self.home / ".atelier/conduits").rmdir()
        code, rep = self.inspect_json()
        self.assertEqual((code, rep["status"]), (2, "not_inspectable"))
        self.assertIn(str(self.project / ".atelier/schedules"), rep["error"])
        self.assertIn(str(self.home / ".atelier/conduits"), rep["error"])
        self.assertIn("writes directories", rep["next"])
        self.assertEqual(self.calls(), [])
        self.assertFalse((self.project / ".atelier/schedules").exists())

    def test_unsearchable_layout_directory_is_refused(self):
        self.fake()
        flows = self.project / ".atelier/flows"
        flows.chmod(0o600)
        try:
            code, rep = self.inspect_json()
        finally:
            flows.chmod(0o755)
        self.assertEqual(code, 2)
        self.assertIn(str(flows), rep["error"])

    def test_exported_dir_overrides_use_cli_relative_semantics(self):
        custom = self.project / "custom"
        for d in ("conduits/greet", "flows", "schedules"):
            (custom / d).mkdir(parents=True)
        shared = self.tmp / "shared"
        (shared / "conduits").mkdir(parents=True)
        selected = custom / "conduits/greet/conduit.yaml"
        selected.write_text("name: greet\n")
        self.fake({"stdout": check_row(selected)}, {"stdout": show_doc(selected)})
        (self.project / ".atelier/flows").rmdir()  # the default layout is no longer needed
        (self.home / ".atelier/conduits").rmdir()
        env = {"ATELIER_ATELIER_DIR": "custom", "ATELIER_GLOBAL_ATELIER_DIR": str(shared)}
        self.assertEqual(self.inspect_json(env=env)[0], 0)
        code, rep = self.inspect_json(env={**env, "ATELIER_ATELIER_DIR": "elsewhere"})
        self.assertEqual(code, 2)
        self.assertIn(str(self.project / "elsewhere/conduits"), rep["error"])
        code, rep = self.inspect_json(env={**env, "atelier_atelier_dir": "custom"})
        self.assertEqual(code, 2)
        self.assertIn("ambiguous", rep["error"])

    def test_dotenv_path_settings_are_refused_but_harmless_dotenv_is_fine(self):
        self.fake({"stdout": check_row(self.conduit)}, {"stdout": show_doc(self.conduit)})
        dotenv = self.project / ".env"
        dotenv.write_text("API_TOKEN=do-not-print\n")
        self.assertEqual(self.inspect_json()[0], 0)
        dotenv.write_text("API_TOKEN=do-not-print\nexport atelier_global_atelier_dir = /x\n")
        code, rep = self.inspect_json()
        self.assertEqual(code, 2)
        self.assertIn("ATELIER_GLOBAL_ATELIER_DIR", rep["error"])
        self.assertNotIn("do-not-print", json.dumps(rep))
        self.assertEqual(self.inspect_json(env={"ATELIER_GLOBAL_ATELIER_DIR": str(self.home / ".atelier")})[0], 0)
        for line in ("'ATELIER_ATELIER_DIR'=redirected", '"ATELIER_ATELIER_DIR" = "redirected"',
                     "export\tATELIER_ATELIER_DIR=redirected", "  Atelier_Global_Atelier_Dir=x"):
            with self.subTest(line):
                dotenv.write_text(f"API_TOKEN=do-not-print\n{line}\n")
                self.log.unlink(missing_ok=True)
                code, rep = self.inspect_json()
                self.assertEqual((code, rep["status"]), (2, "not_inspectable"))
                self.assertEqual(self.calls(), [])
                self.assertFalse((self.project / "redirected").exists())
                self.assertNotIn("do-not-print", json.dumps(rep))
        dotenv.chmod(0)
        try:
            code, rep = self.inspect_json()
        finally:
            dotenv.chmod(0o644)
        self.assertEqual(code, 2)
        self.assertIn("cannot read", rep["error"])

    def test_timeout_kills_the_whole_process_group(self):
        self.fake({"sleep": 30, "stdout": check_row(self.conduit)})
        started = time.monotonic()
        code, rep = self.inspect_json("--timeout", "1")
        self.assertLess(time.monotonic() - started, 15)
        self.assertEqual((code, rep["status"]), (2, "not_inspectable"))
        self.assertIn("did not finish within 1s", rep["error"])
        grandchild = int(Path(str(self.log) + ".pid").read_text())
        time.sleep(0.2)
        with self.assertRaises(ProcessLookupError):
            os.kill(grandchild, 0)

    def test_usage_errors_exit_64(self):
        self.assertEqual(self.run_cli(str(self.project)).returncode, 64)
        self.assertEqual(self.run_cli(str(self.project), "greet", "--timeout", "0").returncode, 64)
        self.assertEqual(self.run_cli("--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
