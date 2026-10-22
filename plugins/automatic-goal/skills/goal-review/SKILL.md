---
name: goal-review
description: Turn finished automatic-goal runs into stakeholder material - a short report, an optional round of gap-fixing subagents, a detail page (every change with What, Why and How), a short deck (one slide per project) and a narrated video of about 10 minutes. Use when one goal run or a batch of goal runs has finished and the user wants to know or show what was done, or says /goal-review, "review the goal runs", "make the stakeholder deck or video".
---

# Goal review

Make finished automatic-goal runs understandable for a stakeholder. Work in this order and
stop where the user wants: 1 report, 2 fix gaps (only if asked), 3 detail page, 4 deck,
5 video. Keep everything in a work folder in the scratchpad (WORK below). The scripts are in
`scripts/` next to this file (SK below). Never start, resume or edit goal runs or anything
under `.atelier/`.

## What a stakeholder needs

- **The goal first.** The runs' goal text once, near the start, and one "Goal:" line per
  project with the run's own target for it, in plain words.
- **For every change: What changed, Why (the problem before), How it works.** Plain English,
  short sentences, no file or function names, no internal words (milestone, scorecard,
  probe, repair, review finding).
- **A short deck: one slide per project.** No slide per change and no title-only list
  slides. The detail page holds every change, and each project slide links to its section.
- **Honest limits.** Say what was not tested (real devices, accounts, deploys, users) and
  what is not committed or not pushed. A stage pass, a usage pause or an unverified fix is not
  a finished result.
- Lead with what users get, not with counts or engineering detail.

## 1. Collect and report

Find the worktrees: each has `.atelier/conduits/goal_loop/scripts/observe.py`, and batch runs
usually live in sibling folders named `<project>-goal-<label>`. Then run:

```sh
python3 "$SK/scripts/collect.py" "$WORK" [--since YYYY-MM-DD] <worktree> [<worktree> ...]
```

It runs the package's reader with the atelier interpreter and writes `reports/`, `raw/` and
`projects.json` (outcome status per project and the changes kept per round). Also check
each branch in git: its tip equals the recorded head, the tree is clean, and whether it is
pushed. If the run opened a pull request, its link is in the report; use it. Report per
project: status, changes kept per round and the main gap left. Word outcomes the way the
goal-report skill does (ACCEPT is not ACHIEVED; an interrupted run is not a success).

## 2. Fix the gaps (only when asked)

Start one general-purpose subagent per PARTIAL project, all in one message, with the "Fix
gaps" brief in `references/briefs.md`, each with its own port range. When an agent reports,
check its diff and re-run its key tests yourself before telling the user. Then group the
projects: `met` (ACHIEVED in the run), `fixed` (main gap closed after the run), `decision`
(needs the user's choice). Write `WORK/groups.json` ({repo: group}) and `WORK/fixes.json`
({repo: [{title, what, why, how}]}) from the verified reports.

## 3. Detail page

Have a few subagents (3 to 5 projects each) turn `WORK/raw/<repo>.json` into
`WORK/out/<repo>.json` with the "What / Why / How" brief. Check that every item survived
(same titles, same order) and read samples. Then build and publish it as an Artifact:

```sh
python3 "$SK/scripts/detail_page.py" "$WORK" <session-folder>/goal-runs-detail.html --title "<name>"
```

Each project has the anchor `#p-<repo>` (lower case, other characters as "-") for the deck.

## 4. Deck (Slides artifact)

Start from the Slides type and follow its instructions. Use the structure in
`references/deck/README.md` and the markup in `references/deck/`: cover, goal, numbers,
status, one slide per project in group order, not tested, decisions, more detail.

Screenshots: the runs keep many under each worktree's `.atelier/goal/evidence/` (a symlink,
so use `find -L`). Let subagents shortlist with the "Pick screenshots" brief, then look at
every image you use: no real personal data, no local paths (crop with
`sips -c H W --cropOffset Y X`), no test-only junk. Copy them to `WORK/img/` and upload them
as assets.

## 5. Video (about 10 minutes)

Write `WORK/video/scenes.json` from `references/scenes.example.json`: intro, goal, numbers,
status, one scene per project, not tested, decisions, close. A project's narration says what
the project is, "The goal here: ...", What changed, Why, How and what is still open, in 60 to
75 words. Write names the way they are spoken. About 1,800 words gives 10 to 11 minutes.

```sh
PY=<a Python with kokoro_onnx and soundfile>       # KOKORO_MODELS = folder with the model files
"$PY" -I "$SK/scripts/video.py" voice  "$WORK"      # run in the background
python3   "$SK/scripts/video.py" frames "$WORK"     # needs Playwright's headless Chromium
"$PY" -I "$SK/scripts/video.py" build  "$WORK" <session-folder>/goal-runs-review.mp4
```

Look at 3 to 5 frames before building: text must not touch the footer, and a box label must
not repeat its own text. After building, check the length with ffprobe, the sound with
`ffmpeg -af volumedetect`, and one frame from the middle. Say plainly that you cannot listen
to the audio. Send the MP4 with SendUserFile.

## Close

Say what each piece is, what you checked and what you did not, that artifacts are private
until shared (share the deck and the detail page together), and which decisions are open.
Offer to commit fixes made after the runs; never commit or push without a yes.
