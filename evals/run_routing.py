#!/usr/bin/env python3
"""Evaluate all eight skills together without adding cases to shipped plugins."""

import argparse
from fnmatch import fnmatchcase
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = "routing"


def routing_passes(cases, partial):
    passed = [bool(c["runs"]) and all(r["passed"] for r in c["runs"]) for c in cases]
    return (not partial and bool(cases) and sum(passed) / len(cases) >= 0.9
            and all(ok for c, ok in zip(cases, passed) if c["negative"]))


def tool_skills(value):
    if isinstance(value, dict):
        if value.get("type") == "tool_use" and value.get("name") == "Skill":
            yield value.get("input", {}).get("skill")
        for child in value.values():
            yield from tool_skills(child)
    elif isinstance(value, list):
        for child in value:
            yield from tool_skills(child)


def archive(result, output):
    cases = []
    for case in result["cases"]:
        expected = next(g["config"]["input_match"] for g in case["graders"]
                        if g["name"] == "route")
        runs = []
        for run in case["arms"]["with"]:
            trace = Path(run["tracePath"])
            saved = output / "traces" / case["name"] / f"{len(runs)}.jsonl"
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(trace, saved)
            fired = []
            for line in saved.read_text().splitlines():
                fired.extend(tool_skills(json.loads(line)))
            run["tracePath"] = str(saved)
            runs.append({"fired": fired, "passed": run["passed"],
                         "error": run["error"], "graders": run["graders"],
                         "trace": str(saved)})
        cases.append({"case": case["name"],
                      "expected": re.search(r"routing:[\w-]+", expected).group(),
                      "negative": any(g["name"] == "forbidden" for g in case["graders"]),
                      "runs": runs})
    (output / "eval.json").write_text(json.dumps(result, indent=2) + "\n")
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / ".atelier/routing-evals" / time.strftime("%Y%m%d-%H%M%S"))
    parser.add_argument("--max-cost-usd", type=float, default=8)
    parser.add_argument("--concurrency", type=int, choices=range(1, 9), default=4)
    parser.add_argument("--case", help="Case name glob, for a focused rerun")
    args = parser.parse_args()
    if not math.isfinite(args.max_cost_usd) or args.max_cost_usd <= 0:
        parser.error("--max-cost-usd must be finite and positive")
    selected = [case for case in sorted((ROOT / "evals/routing").iterdir())
                if fnmatchcase(case.name, args.case or "*")]
    if not selected:
        parser.error("--case matched no routing cases")
    output = args.output_dir.resolve()
    if output.exists():
        parser.error("--output-dir already exists; choose a fresh directory to preserve evidence")
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="atelier-routing-") as temporary:
        plugin = Path(temporary)
        (plugin / ".claude-plugin").mkdir()
        (plugin / ".claude-plugin/plugin.json").write_text(json.dumps({
            "name": NAMESPACE, "version": "1.0.0",
            "description": "Maintainer routing evaluation of all four plugins"}))
        versions = {}
        for source in sorted((ROOT / "plugins").iterdir()):
            manifest = json.loads((source / ".claude-plugin/plugin.json").read_text())
            versions[manifest["name"]] = manifest["version"]
            for skill in sorted((source / "skills").iterdir()):
                shutil.copytree(skill, plugin / "skills" / skill.name)
        for case in selected:
            shutil.copytree(case, plugin / "evals" / case.name)
        command = ["claude", "plugin", "eval", str(plugin), "--trust-plugin",
                   "--no-publish", "--ablation", "none", "--runs", "1",
                   "--max-cost-usd", str(args.max_cost_usd),
                   "--concurrency", str(args.concurrency), "--keep-temp",
                   "--json", str(output / "eval.json"), "--output-dir", str(output)]
        started = time.monotonic()
        completed = subprocess.run(command, cwd=ROOT)
        exit_code = completed.returncode
        summary = {"command": command, "native_exit_code": completed.returncode,
                   "duration_seconds": round(time.monotonic() - started, 3),
                   "plugins": versions, "case_filter": args.case, "published": False}
        if (output / "eval.json").exists():
            result = json.loads((output / "eval.json").read_text())
            summary.update(cost_usd=result["costUsd"], partial=result["partial"],
                           aggregates=result["aggregates"], cases=archive(result, output))
            if completed.returncode in (0, 1):
                complete = len(summary["cases"]) == len(selected)
                exit_code = 0 if complete and routing_passes(summary["cases"], result["partial"]) else 1
            print(f"Cases passed: {result['aggregates']['casesPassed']}/{len(selected)}; "
                  f"routing gate: {'PASS' if exit_code == 0 else 'FAIL'}", flush=True)
        summary["exit_code"] = exit_code
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(f"Routing evidence: {output}", flush=True)
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
