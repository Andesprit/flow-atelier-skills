# Subagent briefs

Fill in the <angle-bracket> parts. Paths must be absolute.

## Fix gaps (one general-purpose agent per PARTIAL project)

Write a gap brief per project first, from `WORK/reports/<repo>.json` (the newest run's
summary.pending, summary.abandoned with their details, summary.remaining, summary.next_run
and outcome.reason), into `WORK/gaps/<repo>.md`.

```
You are fixing gaps that an automated improvement run left in one project.

Project worktree: <worktree> (git branch <branch> is checked out; stay on it).
Read first: <WORK>/gaps/<repo>.md. Full detail if needed: run
<atelier python> <worktree>/.atelier/conduits/goal_loop/scripts/observe.py report --root <worktree> --details

Top priority here: <the most serious gap in one or two sentences, from the brief>.

Task: Fix the gaps that are real product defects or unfinished user-facing behavior and that
you can fix and verify locally. Priority: data loss / critical / high first, then unmet
outcomes, then unfinished or dropped work. For gaps that are only "not verified", run that
verification yourself and fix what fails. Skip gaps that need real people, real devices,
external accounts or credentials, paid APIs, or production deploys, and say so.

Rules:
- Root cause first. Reproduce each bug with a failing test or a runnable reproduction before
  changing code; make it pass after.
- Minimum change. Match existing code style. No new dependencies unless unavoidable.
- Run the project's existing checks before and after; report exact commands and results.
- Do NOT commit, push, merge, rebase, stash or switch branches.
- Do NOT run, resume or edit the automatic-goal conduits or anything under .atelier/.
- Only touch files inside the worktree. If you start servers, use ports <lo>-<hi> only and
  stop them before you finish. No emojis. Never enter real credentials.
- Time box: stop once the most important gaps are fixed and verified.

Final report (plain text, short): 1. FIXED (gap, cause, fix, how verified) 2. NOT FIXED and
why 3. CHECKS before and after 4. FILES CHANGED (git status --short).
```

## What / Why / How (model sonnet, 3 to 5 projects per agent)

```
Turn saved technical records of software changes into plain-language entries for a
stakeholder who wants simple B1-level English.

Input: <WORK>/raw/<repo>.json for each of your projects: <repos>. Each has goal, target and
rounds[] -> items[] with title, what_record (what was built, often how), upside and benefit
(why), action and because (the plan and how it works).
Also <WORK>/fixes.json under each repo key, if present: changes made after the run.

For each project write <WORK>/out/<repo>.json with exactly this shape:
{"repo": "<repo>", "about": "<one short sentence: what this app or tool is>",
 "goal": "<the run's target for this project in at most 100 characters, plain words>",
 "items": [{"round": "<copy the round label exactly>", "title": "<copy the title exactly>",
            "what": "...", "why": "...", "how": "..."}]}
Keep every item, in input order. Do not add or drop items. Do not include the fixes.

- what: what changed for the person using it (2 short sentences at most).
- why: the problem before, or why it is worth it ("Before, ..." in the record helps).
- how: how it works, the mechanism a smart non-engineer understands (1 to 2 sentences).
- Use only facts in the record. No invented numbers, features or reasons.
- No file names, function names, code identifiers, commit hashes, milestone numbers, test
  names, or the words scorecard, outcome, milestone, probe, repair, review finding.
  Button labels, screen names and commands the user types are fine.
- No emojis, no em dashes. Valid JSON; check with python3 -c "import json,sys;json.load(open(sys.argv[1]))".
Reply with one line per project: name and item count.
```

## Pick screenshots (model sonnet, about 6 projects per agent)

```
Pick the best screenshots for a stakeholder slide deck. One slide per project shows its
headline change with an AFTER screenshot, and a BEFORE screenshot when a good matching one
exists. Screenshots are under each worktree's goal evidence folder, a symlink, so use:
find -L <worktree>/.atelier/goal/ -type f \( -name '*.png' -o -name '*.jpg' \)
Shortlist by file and folder names, then LOOK at the images (at most about 10 per project).

Projects, worktree and the headline the image should support:
<n. repo: worktree: "headline">

Rules: readable at about 700 px wide (desktop views, large clear UI; no tiny, empty,
error-only or debug shots); no real personal data (real emails, names, keys, local paths);
a BEFORE only if it clearly shows the same screen before the change. Read only.
Reply with ONLY JSON: {"<repo>": {"after": "<path or null>", "before": "<path or null>",
"caption": "<max 10 words>"}, ...}
```
