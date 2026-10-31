"""Collect finished automatic-goal runs into one work folder for a stakeholder review.

Usage: collect.py WORK [--since YYYY-MM-DD] WORKTREE [WORKTREE ...]

For each worktree it runs the package's own reader (observe.py json), keeps the runs that
started on or after --since (default: the newest run's start date), and writes:
  WORK/reports/<name>.json   the reader's full snapshot
  WORK/raw/<name>.json       goal, target and every ACCEPTed change per round
  WORK/projects.json         one row per project: status, counts, branch, head
"""
import argparse, glob, json, os, subprocess, sys
from datetime import datetime


def atelier_python():
    # The reader needs PyYAML; the atelier CLI's own interpreter has it.
    exe = subprocess.run(["which", "atelier"], capture_output=True, text=True).stdout.strip()
    if exe:
        first = open(exe).readline()
        if first.startswith("#!") and os.path.exists(first[2:].strip()):
            return first[2:].strip()
    return sys.executable


def project_name(root):
    base = os.path.basename(os.path.normpath(root))
    return base.split("-goal-")[0] if "-goal-" in base else base


def local(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%-I:%M %p")


ap = argparse.ArgumentParser()
ap.add_argument("work")
ap.add_argument("--since")
ap.add_argument("roots", nargs="+")
a = ap.parse_args()
py = atelier_python()
for d in ("reports", "raw"):
    os.makedirs(os.path.join(a.work, d), exist_ok=True)

snaps = {}
for root in a.roots:
    obs = os.path.join(root, ".atelier", "conduits", "goal_loop", "scripts", "observe.py")
    if not os.path.exists(obs):
        print(f"skip {root}: no goal_loop reader", file=sys.stderr)
        continue
    env = dict(os.environ, PYTHONIOENCODING="utf-8:replace")  # some records hold invalid surrogates
    out = subprocess.run([py, obs, "json", "--root", root], capture_output=True, text=True, env=env)
    if out.returncode:
        print(f"skip {root}: reader failed: {out.stderr[-300:]}", file=sys.stderr)
        continue
    snaps[root] = json.loads(out.stdout)

since = a.since or max(r["started"][:10] for s in snaps.values() for r in s["runs"] if r.get("started"))
rows = []
for root, snap in snaps.items():
    name = project_name(root)
    runs = sorted((r for r in snap["runs"] if (r.get("started") or "")[:10] >= since and r.get("outcome")),
                  key=lambda r: r["started"])
    if not runs:
        continue
    json.dump(snap, open(os.path.join(a.work, "reports", f"{name}.json"), "w"), indent=1)
    rounds = []
    for i, r in enumerate(runs, 1):
        o = r["outcome"]
        end = r.get("finished") or ""
        label = f"Round {i}, {local(r['started'])} to {local(end) if end else 'running'}"
        items = []
        for m in o.get("milestones", []):
            if m.get("status") != "ACCEPT":
                continue
            h, im = m.get("hypothesis") or {}, m.get("implementation") or {}
            items.append({"title": m["title"], "what_record": im.get("summary", ""), "upside": m.get("upside", ""),
                          "benefit": m.get("benefit", ""), "action": h.get("action", ""), "because": h.get("because", "")})
        rounds.append({"round": label, "status": o.get("status"), "reason": o.get("reason", ""), "items": items})
    last = runs[-1]["outcome"]
    brief = last.get("brief") or {}
    remaining = (runs[-1].get("summary") or {}).get("remaining", [])
    json.dump({"repo": name, "root": root, "goal": runs[0]["goal"], "goal_last": runs[-1]["goal"],
               "target": brief.get("outcome", ""), "rounds": rounds, "remaining": remaining},
              open(os.path.join(a.work, "raw", f"{name}.json"), "w"), indent=1, ensure_ascii=False)
    rows.append({"repo": name, "root": root, "status": last.get("status"), "branch": last.get("branch"),
                 "head": last.get("accepted_head"), "base": runs[0]["outcome"].get("initial_base"),
                 "kept": [len(x["items"]) for x in rounds]})
json.dump(rows, open(os.path.join(a.work, "projects.json"), "w"), indent=1)
for r in rows:
    print(f"{r['repo']:24} {r['status']:9} kept per round {r['kept']}")
print(f"{len(rows)} projects, runs since {since}")
