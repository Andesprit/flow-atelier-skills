#!/usr/bin/env python3
"""Inspect one existing Atelier workflow without running it.

Usage: inspect_workflow.py <project_path> <conduit> [--json] [--timeout SECONDS]

Runs only `atelier check --json <conduit>` and, when that passes,
`atelier show --json <conduit>`, from <project_path>, with update checks off.
It never runs a workflow, starts an agent, or creates the directories the CLI
would create on its own; a missing layout is reported instead.

Exit codes: 0 valid definition (not run), 1 invalid definition,
2 not inspectable, 64 usage error.
"""
import argparse
import hashlib
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
from pathlib import Path

PATH_SETTINGS = ("ATELIER_ATELIER_DIR", "ATELIER_GLOBAL_ATELIER_DIR")
NOT_CHECKED = [
    "the workflow was not run",
    "input values are not resolved",
    "nested tool:conduit children are not validated",
    "agents are not started or authenticated",
    "cost and runtime success are not predicted",
]


class NotInspectable(Exception):
    def __init__(self, error, next_step):
        super().__init__(error)
        self.next_step = next_step


def exported_setting(name):
    """Return an exported setting value; pydantic-settings matches names case-insensitively."""
    for key, value in os.environ.items():
        if key.upper() == name:
            return value
    return None


def dotenv_sets(project, name):
    """True when the project's .env assigns `name`; values are never read out."""
    env_file = project / ".env"
    if not env_file.exists():
        return False
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as e:
        raise NotInspectable(
            f"cannot read {env_file} ({e.__class__.__name__}); the CLI reads it for settings",
            f"make {env_file} readable, then inspect again",
        )
    for line in lines:
        line = line.strip()
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if line.split("=", 1)[0].strip().upper() == name and "=" in line:
            return True
    return False


def layout(project):
    """Resolve the project and global Atelier dirs the CLI would use from `project`."""
    dirs = {}
    for name, default in zip(PATH_SETTINGS, (project / ".atelier", Path.home() / ".atelier")):
        value = exported_setting(name)
        if value is None and dotenv_sets(project, name):
            raise NotInspectable(
                f"{project / '.env'} sets {name}; this helper does not resolve .env path settings",
                f"export {name} explicitly, or use `atelier check` directly",
            )
        # The CLI keeps relative paths relative to its cwd, which is `project`.
        dirs[name] = project / value if value is not None else default
    atelier, global_dir = dirs.values()
    needed = [atelier / "conduits", atelier / "flows", atelier / "schedules", global_dir / "conduits"]
    missing = [str(p) for p in needed if not (p.is_dir() and os.access(p, os.R_OK | os.X_OK))]
    if missing:
        raise NotInspectable(
            "missing or unreadable Atelier directories, which the CLI would create on any call: "
            + ", ".join(missing),
            "nothing was inspected. To prepare them yourself (this writes directories): mkdir -p "
            + " ".join(shlex.quote(p) for p in missing),
        )


def atelier_json(atelier, args, project, timeout):
    """Run one allowlisted read-only CLI call; return (exit code, parsed stdout or None, stderr)."""
    env = {**os.environ, "ATELIER_NO_UPDATE_CHECK": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.Popen(
        [atelier, *args], cwd=project, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # ponytail: POSIX only; elsewhere killpg is missing and only the direct child is killed.
        if hasattr(os, "killpg"):
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
        proc.communicate()
        raise NotInspectable(
            f"`atelier {' '.join(args)}` did not finish within {timeout:g}s and was stopped",
            "retry with a larger --timeout",
        )
    if proc.returncode == 2:
        raise NotInspectable(
            f"this atelier does not accept `{' '.join(args)}`: {err.strip()[-300:]}",
            "upgrade flow-atelier (check/show --json need atelier 0.12 or newer)",
        )
    try:
        data = json.loads(out) if out.strip() else None
    except json.JSONDecodeError:
        raise NotInspectable(f"`atelier {args[0]}` printed output that is not JSON", "run `atelier --version` and report it")
    return proc.returncode, data, err.strip()


def file_hash(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def str_list(value):
    return isinstance(value, list) and all(isinstance(v, str) for v in value)


def inspect(project_arg, conduit, timeout):
    report = {"conduit": conduit, "status": "not_inspectable", "source": None, "path": None,
              "required_inputs": None, "accepted_inputs": None, "tools": None,
              "error": None, "next": None, "not_checked": NOT_CHECKED}
    try:
        project = Path(project_arg).expanduser().absolute()
        if not (project.is_dir() and os.access(project, os.R_OK | os.X_OK)):
            raise NotInspectable(f"project path is not a readable directory: {project}", "pass the folder that holds .atelier/")
        atelier = shutil.which("atelier")
        if atelier is None:
            raise NotInspectable("the atelier command is not on PATH", "install the CLI: see references/first-run.md")
        layout(project)
        cd = f"cd {shlex.quote(str(project))} && "

        code, rows, err = atelier_json(atelier, ["check", "--json", conduit], project, timeout)
        if rows is None:
            if code == 1 and "unknown conduit" in err:
                raise NotInspectable(f"no conduit named {conduit!r} in this project or the global store",
                                     cd + "atelier list conduits")
            raise NotInspectable(f"`atelier check` exited {code} without a report: {err[-300:]}",
                                 cd + f"atelier check {shlex.quote(conduit)}")
        row = rows[0] if isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict) else None
        if (row is None or row.get("name") != conduit or row.get("source") not in ("project", "global")
                or not isinstance(row.get("path"), str) or not isinstance(row.get("ok"), bool)):
            raise NotInspectable("`atelier check` returned a report this helper does not understand",
                                 cd + f"atelier check {shlex.quote(conduit)}")
        report["source"], report["path"] = row["source"], row["path"]
        if row["ok"] != (code == 0):
            raise NotInspectable(f"`atelier check` exit {code} contradicts its ok={row['ok']} report",
                                 cd + f"atelier check {shlex.quote(conduit)}")
        if not row["ok"]:
            report["status"] = "invalid"
            report["error"] = str(row.get("error") or "invalid definition")
            report["next"] = (f"fix {row['path']}; this {row['source']} copy is the one `atelier run` uses, "
                              f"then: {cd}atelier check {shlex.quote(conduit)}")
            return report, 1
        if not str_list(row.get("required_inputs")):
            raise NotInspectable("`atelier check` did not list required inputs", cd + f"atelier check {shlex.quote(conduit)}")
        report["required_inputs"] = row["required_inputs"]

        before = file_hash(row["path"])
        code, shown, err = atelier_json(atelier, ["show", "--json", conduit], project, timeout)
        incomplete = "definition passed `atelier check`, but its details could not be read: "
        if code != 0 or not isinstance(shown, dict):
            raise NotInspectable(incomplete + f"`atelier show` exited {code} {err[-300:]}", cd + f"atelier show {shlex.quote(conduit)}")
        if shown.get("path") != row["path"] or shown.get("source") != row["source"] or file_hash(row["path"]) != before:
            raise NotInspectable(incomplete + "the definition changed or resolved to another file between check and show",
                                 "inspect again")
        tasks = (shown.get("conduit") or {}).get("tasks") if isinstance(shown.get("conduit"), dict) else None
        if (not isinstance(tasks, list) or not all(isinstance(t, dict) and isinstance(t.get("name"), str)
                                                    and isinstance(t.get("tool"), str) for t in tasks)
                or not str_list(shown.get("accepted_inputs")) or shown.get("required_inputs") != row["required_inputs"]):
            raise NotInspectable(incomplete + "`atelier show` returned unexpected task or input fields",
                                 cd + f"atelier show {shlex.quote(conduit)}")
        report["accepted_inputs"] = shown["accepted_inputs"]
        report["tools"] = [{"task": t["name"], "tool": t["tool"]} for t in tasks]
        report["status"] = "valid"
        steps = [f"{cd}atelier plan {shlex.quote(conduit)}"]
        if any(t["tool"] == "tool:conduit" for t in tasks):
            steps.append(f"{cd}atelier check {shlex.quote(conduit)} --recursive")
        report["next"] = " ; ".join(steps)
        return report, 0
    except NotInspectable as e:
        report["error"], report["next"] = str(e), e.next_step
        return report, 2


def text(report):
    status = {"valid": "valid definition (inspected, not run)", "invalid": "INVALID definition",
              "not_inspectable": "NOT INSPECTED"}[report["status"]]
    lines = [f"{report['conduit']}  [{report['source'] or 'source unknown'}]  {report['path'] or ''}".rstrip(),
             f"status:      {status}"]
    if report["error"]:
        lines.append(f"problem:     {report['error']}")
    if report["required_inputs"] is not None:
        lines.append(f"inputs:      required: {', '.join(report['required_inputs']) or 'none'}"
                     + (f"; accepted: {', '.join(report['accepted_inputs']) or 'none'}" if report["accepted_inputs"] is not None else ""))
    if report["tools"] is not None:
        lines.append(f"tasks:       {len(report['tools'])}: " + ", ".join(f"{t['task']} ({t['tool']})" for t in report["tools"]))
    lines.append(f"next:        {report['next']}")
    lines.append("not checked: " + "; ".join(report["not_checked"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect one Atelier workflow without running it.")
    parser.add_argument("project", help="folder that holds the project's .atelier/")
    parser.add_argument("conduit", help="workflow (conduit) name")
    parser.add_argument("--json", action="store_true", help="print one JSON object")
    parser.add_argument("--timeout", type=float, default=60.0, help="seconds per atelier call (default 60)")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 64 if e.code else 0
    if not args.timeout > 0:
        print("--timeout must be a positive number", file=sys.stderr)
        return 64
    report, code = inspect(args.project, args.conduit, args.timeout)
    print(json.dumps(report, indent=2) if args.json else text(report))
    return code


if __name__ == "__main__":
    sys.exit(main())
