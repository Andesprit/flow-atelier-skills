"""Offline check of packaging, budget flags and retained routing evidence."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_routing


class RoutingRunnerTest(unittest.TestCase):
    def test_gate_requires_ninety_percent_and_every_negative_case(self):
        cases = [{"negative": i < 3, "runs": [{"passed": True}]} for i in range(18)]
        cases[-1]["runs"][0]["passed"] = False
        self.assertTrue(run_routing.routing_passes(cases, False))
        self.assertFalse(run_routing.routing_passes(cases, True))
        cases[-2]["runs"][0]["passed"] = False
        self.assertFalse(run_routing.routing_passes(cases, False))
        cases[-2]["runs"][0]["passed"] = True
        cases[-1]["runs"][0]["passed"] = True
        cases[0]["runs"][0]["passed"] = False
        self.assertFalse(run_routing.routing_passes(cases, False))
        self.assertFalse(run_routing.routing_passes([], False))

    def test_invalid_cost_cannot_launch_a_paid_run(self):
        for value in ("0", "-1", "nan", "inf"):
            with self.subTest(value=value), patch("sys.argv", ["run_routing.py", "--max-cost-usd", value]), patch("subprocess.run") as run:
                with self.assertRaises(SystemExit) as error:
                    run_routing.main()
                self.assertEqual(error.exception.code, 2)
                run.assert_not_called()

    def test_combines_plugins_and_archives_exact_skill_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results"
            trace = Path(directory) / "trace.jsonl"
            trace.write_text(json.dumps({"message": {"content": [
                {"type": "tool_use", "name": "Skill",
                 "input": {"skill": "routing:flow-atelier"}}
            ]}}) + "\n")

            def evaluate(command, cwd):
                plugin = Path(command[3])
                self.assertEqual(cwd, run_routing.ROOT)
                self.assertEqual(len(list((plugin / "skills").glob("*/SKILL.md"))), 8)
                self.assertEqual([p.parent.name for p in (plugin / "evals").glob("*/prompt.md")], ["workflow-check"])
                self.assertEqual(json.loads((plugin / ".claude-plugin/plugin.json").read_text())["name"], "routing")
                for flag in ("--trust-plugin", "--no-publish", "--keep-temp"):
                    self.assertIn(flag, command)
                for flag, value in (("--runs", "1"), ("--ablation", "none"),
                                    ("--max-cost-usd", "2.0"), ("--concurrency", "1")):
                    self.assertEqual(command[command.index(flag) + 1], value)
                (output / "eval.json").write_text(json.dumps({
                    "costUsd": 0.1, "partial": False, "aggregates": {"casesPassed": 1},
                    "cases": [{"name": "workflow-check",
                               "graders": [{"name": "route", "config": {
                                   "input_match": '"routing:flow-atelier"'}}],
                               "arms": {"with": [{"tracePath": str(trace),
                                                   "passed": True, "error": None,
                                                   "graders": []}]}}]}))
                return type("Completed", (), {"returncode": 0})()

            arguments = ["run_routing.py", "--output-dir", str(output),
                         "--max-cost-usd", "2", "--concurrency", "1", "--case", "workflow-*"]
            with patch("sys.argv", arguments), patch("subprocess.run", side_effect=evaluate):
                self.assertEqual(run_routing.main(), 0)
            summary = json.loads((output / "summary.json").read_text())
            self.assertFalse(summary["published"])
            self.assertEqual(summary["cases"][0]["expected"], "routing:flow-atelier")
            self.assertEqual(summary["cases"][0]["runs"][0]["fired"], ["routing:flow-atelier"])
            self.assertTrue(Path(summary["cases"][0]["runs"][0]["trace"]).is_file())
            self.assertFalse(Path(summary["command"][3]).exists())
            with patch("sys.argv", arguments), self.assertRaises(SystemExit) as error:
                run_routing.main()
            self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
