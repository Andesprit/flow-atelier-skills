# Recipes for common jobs

For Atelier 0.12.0. Start in a Git project with Atelier installed. Each job takes
three steps: **save** its YAML at the paths shown (create the directories),
**check**, then **plan or run**. For a two-file recipe, save both files before
checking. `atelier check` validates every conduit saved in the project and runs
nothing; `atelier plan` also starts no agents.

| Your job | Recipe |
|---|---|
| Have a worker fix a change until another agent approves | [Review loop](#review-until-another-agent-approves) |
| Hand a draft from one agent to another | [Draft then review](#draft-then-review) |
| Ask a person before a shell step | [Approval gate](#ask-before-a-shell-step) |
| Run tests, fix failures, and test again | [Test and fix loop](#test-and-fix-until-green) |
| Try a loop without agent logins | [Bash demo](#bash-only-loop-demo) |
| Run a status report every night | [Nightly job](#run-a-job-every-night) |

**Verification:** every conduit below passed `atelier check` and `atelier plan`.
The bash demo, both approval answers, and the nightly conduit were run on 0.12.0.
The schedule was added, listed and removed without a daemon. The agent recipes
were **not run with real agents**; validation does not prove their judgments or
repairs will succeed. Before running those, have the named agents installed and
logged in (`atelier harness check codex` and `atelier harness check claude-code`).

Run these recipes one at a time in a dedicated checkout. They use named scratch
files under `.atelier/recipe-*`; the review loop resets its feedback on a new
run. Inputs in agent prompts describe the job; `test_command` is trusted shell
code, executed as supplied. [Field and loop details](conduit-yaml.md).

## Review until another agent approves

Use this for an existing working-tree change that needs repair and independent
review. Codex works; Claude Code reviews the resulting diff. Review findings go
in `.atelier/recipe-review.md` so the next worker turn can act on them. Neither
agent commits. Only the reviewer emits a verdict; the worker must never emit one.
Agent permission requests go to a human through `permissions: human` in the
child conduit; keep the run in a terminal. [Interaction policy](conduit-yaml.md#interaction-policy).

Save `.atelier/conduits/review_round/conduit.yaml`:

```yaml
name: review_round
description: One worker turn followed by independent review
inputs:
  request: {default: "Repair concrete correctness defects in the current working-tree diff only."}
interaction:
  permissions: human
tasks:
  - work:
      description: Repair the change using the previous review
      tool: harness:codex
      task: |
        {{inputs.request}}
        Read .atelier/recipe-review.md for any previous review findings.
        Inspect the current diff, make scoped repairs and run relevant checks.
        Do not commit or change the review file. Never emit a VERDICT line;
        a separate reviewer decides whether the result is ready.
  - review:
      description: Independently review the resulting diff
      tool: harness:claude-code
      depends_on: [work]
      task: |
        Independently inspect the current working-tree diff against this request:
        {{inputs.request}}
        Check correctness and relevant verification. Do not edit source or commit.
        Overwrite .atelier/recipe-review.md with concrete remaining findings,
        or with a short explanation that no blocking findings remain.
        End your reply with exactly one standalone verdict line:
        VERDICT: APPROVE
        or VERDICT: REVISE
        Approve only if the requested change is ready. Do not quote an approval
        line elsewhere in your reply.
```

Save `.atelier/conduits/review_until_approved/conduit.yaml`:

```yaml
name: review_until_approved
description: Repeat worker and reviewer until approved, at most three rounds
inputs:
  request: {default: "Repair concrete correctness defects in the current working-tree diff only."}
tasks:
  - prepare:
      description: Clear feedback from an earlier run of this recipe
      tool: tool:bash
      task: printf 'No earlier review findings.\n' > .atelier/recipe-review.md
  - rounds:
      description: Repeat the worker and independent reviewer together
      tool: tool:conduit
      task: review_round
      depends_on: [prepare]
      inputs:
        request: "{{inputs.request}}"
      repeat: 3
      until: 'output.match((?m)^VERDICT: APPROVE$)'
      on_exhaust: fail
```

Check, then preview (the third step); run instead when ready to start agents:

```bash
atelier check
atelier plan review_until_approved
# To execute instead of previewing:
atelier run review_until_approved
```

Expect at most three worker/reviewer rounds, ending with `VERDICT: APPROVE`.
A review that still requests changes after round three fails the parent flow;
it cannot silently count an exhausted loop as approval. Nested loop predicates
inspect all completed child-task outputs, so reserving the verdict for the
reviewer matters. Read the diff and checks yourself before accepting the work.

If it fails: `atelier diagnose latest`. For a nested failure, follow the child
diagnose command it prints; the feedback file retains the last review findings.

## Draft then review

Use this when one agent should propose an approach and a different agent should
challenge it, without implementing it. The draft is an explicit file handoff,
so this does not depend on session continuation or a shared harness.
Agent permission requests go to a human through `permissions: human`.
[Interaction policy](conduit-yaml.md#interaction-policy).

Save `.atelier/conduits/draft_review/conduit.yaml`:

```yaml
name: draft_review
description: Draft an approach with Codex and review it with Claude Code
inputs:
  request: {default: "Propose one small improvement to this project's getting-started documentation."}
interaction:
  permissions: human
tasks:
  - draft:
      description: Write a proposed approach without changing the project
      tool: harness:codex
      task: |
        {{inputs.request}}
        Inspect the project. Write your proposed approach, affected files and
        verification plan to .atelier/recipe-draft.md, replacing any old draft.
        Do not implement the proposal or commit. Report where you saved it.
  - review:
      description: Review the draft independently
      tool: harness:claude-code
      depends_on: [draft]
      task: |
        Review .atelier/recipe-draft.md against the project and this request:
        {{inputs.request}}
        Identify concrete risks and missing steps, then recommend whether to
        proceed. Do not edit any file or commit. Return the review in your reply.
```

```bash
atelier check
atelier plan draft_review
# To execute instead of previewing:
atelier run draft_review
```

Expect `draft` before `review`; a run leaves the proposal in
`.atelier/recipe-draft.md` and prints the second agent's review. Override the
job with `--input request="Describe the change you want planned"` on `run`.

If it fails: `atelier diagnose latest`.

## Ask before a shell step

Use this before a step that needs a person's explicit approval. The sample
shell step is harmless: it writes `.atelier/approved-demo.txt`. Replace that
step with your intended command only after reviewing it. A completed HITL task
alone is not approval; the dependency checks the answer, and every other answer
takes the declined branch. The answer is never interpolated into shell code.

Save `.atelier/conduits/approval_gate/conduit.yaml`:

```yaml
name: approval_gate
description: Run a shell step only after an explicit human approval
tasks:
  - approve:
      description: Ask before the shell step
      tool: tool:hitl
      task: "May I write the approval demo file?"
      inputs:
        approval: "Type APPROVE to proceed; anything else declines"
  - approved_step:
      description: Write the harmless demo file after approval
      tool: tool:bash
      depends_on: ['approve.output.match(^approval: APPROVE$)']
      task: |
        printf 'APPROVED_STEP_RAN\n' > .atelier/approved-demo.txt
        cat .atelier/approved-demo.txt
  - declined:
      description: Explain why the shell step was skipped
      tool: tool:bash
      depends_on: ['approve.output.not_match(^approval: APPROVE$)']
      task: printf 'DECLINED - shell step skipped\n'
```

```bash
atelier check
atelier run approval_gate
```

Keep the run in the foreground. Type exactly `APPROVE`: expect
`APPROVED_STEP_RAN` and the demo file. Type `no`: expect
`DECLINED - shell step skipped` and no new demo file. A declined run completes
successfully with `approved_step` skipped; check the branch output, not just the
flow's exit code. `atelier plan approval_gate` previews both branches without
asking for input.

If it fails: `atelier diagnose latest`.

## Test and fix until green

Use this when a real test command can decide whether an agent's repair worked.
The child tests first, calls Codex only on a red result, then tests the repair.
The parent repeats the whole round up to five times. A nonzero test exit is
converted to a red marker so the fix task can run; the parent fails if no test
ever turns green. Test logs are indented so a marker printed by a test cannot
masquerade as the wrapper's verdict.
Agent permission requests go to a human through `permissions: human` in the
child. [Interaction policy](conduit-yaml.md#interaction-policy).

Save `.atelier/conduits/test_fix_round/conduit.yaml`:

```yaml
name: test_fix_round
description: Test, repair a failure, and independently test the repair
inputs:
  test_command: {default: "python3 -m unittest discover"}
interaction:
  permissions: human
tasks:
  - test:
      description: Capture the test exit status without aborting the round
      tool: tool:bash
      task: |
        if ({{inputs.test_command}}) > .atelier/recipe-test.log 2>&1; then
          sed 's/^/  /' .atelier/recipe-test.log
          printf '\nATELIER_TESTS_GREEN\n'
        else
          sed 's/^/  /' .atelier/recipe-test.log
          printf '\nATELIER_TESTS_RED\n'
        fi
  - fix:
      description: Repair only the failing tests' cause
      tool: harness:codex
      depends_on: ['test.output.match((?m)^ATELIER_TESTS_RED$)']
      task: |
        The test command failed: {{inputs.test_command}}
        Read .atelier/recipe-test.log and inspect the relevant code.
        Repair the cause without weakening or skipping tests. Do not commit.
        A separate shell task will verify the repair. Do not emit
        ATELIER_TESTS_GREEN or ATELIER_TESTS_RED in your reply.
  - verify:
      description: Check the repair with the same test command
      tool: tool:bash
      depends_on: [fix]
      task: |
        if ({{inputs.test_command}}) > .atelier/recipe-test.log 2>&1; then
          sed 's/^/  /' .atelier/recipe-test.log
          printf '\nATELIER_TESTS_GREEN\n'
        else
          sed 's/^/  /' .atelier/recipe-test.log
          printf '\nATELIER_TESTS_RED\n'
        fi
```

Save `.atelier/conduits/tests_until_green/conduit.yaml`:

```yaml
name: tests_until_green
description: Repeat test and fix rounds until a test passes
inputs:
  test_command: {default: "python3 -m unittest discover"}
tasks:
  - rounds:
      description: Repeat test, fix and verification as a unit
      tool: tool:conduit
      task: test_fix_round
      inputs:
        test_command: "{{inputs.test_command}}"
      repeat: 5
      until: 'output.match((?m)^ATELIER_TESTS_GREEN$)'
      on_exhaust: fail
```

```bash
atelier check
atelier plan tests_until_green
# To execute instead of previewing, choose your project's real test command:
atelier run tests_until_green --input test_command="python3 -m unittest discover"
```

The default fits Python `unittest`; use your project's actual suite (for example,
`--input test_command="npm test"`). A command that exits 0 without discovering
tests is still green to this recipe, so confirm it runs the intended tests.
Expect `ATELIER_TESTS_GREEN` only after a test exits 0. When the initial test is
green, `fix` and `verify` skip and the parent stops without calling an agent.
A repair on the last round still gets its verification test. Agent failure
fails the child immediately; five red rounds fail the parent. The final test
log stays at `.atelier/recipe-test.log`.

If it fails: `atelier diagnose latest`. Follow a suggested child-diagnose
command for a nested failure; inspect the test log for the failing assertions.

### Bash-only loop demo

Use this to learn `repeat`/`until` without agents or a real repair. It is a
counter fixture, not a way to fix your tests: the simulated test turns green on
attempt three. It resets its counter on each run.

Save `.atelier/conduits/loop_demo/conduit.yaml`:

```yaml
name: loop_demo
description: Demonstrate a bounded loop that succeeds on attempt three
tasks:
  - prepare:
      description: Reset this demo's counter
      tool: tool:bash
      task: printf '0\n' > .atelier/recipe-attempt
  - attempt:
      description: Simulate a test and another repair attempt
      tool: tool:bash
      depends_on: [prepare]
      repeat: 5
      until: 'output.match((?m)^TESTS_GREEN$)'
      on_exhaust: fail
      task: |
        n=$(cat .atelier/recipe-attempt)
        n=$((n + 1))
        printf '%s\n' "$n" > .atelier/recipe-attempt
        printf 'ATTEMPT %s\n' "$n"
        if test "$n" -ge 3; then
          printf 'TESTS_GREEN\n'
        else
          printf 'TESTS_RED - another repair attempt needed\n'
        fi
```

```bash
atelier check
atelier run loop_demo
```

Expect attempts 1 and 2 to say `condition not met`, then attempt 3 to print
`TESTS_GREEN`, `condition met`, and exit 0. The counter file contains `3`.

If it fails: `atelier diagnose latest`.

## Run a job every night

Use this for a daily report at 02:00 in an explicit timezone. First save the
conduit, check it, and run it manually. This report prints the working-tree
status and a completion marker; replace its task when you have another job.

Save `.atelier/conduits/nightly_status/conduit.yaml`:

```yaml
name: nightly_status
description: Report working-tree status for a nightly schedule
tasks:
  - report:
      description: Print status and confirm completion
      tool: tool:bash
      task: |
        git status --short && printf 'NIGHTLY_OK\n'
```

```bash
atelier check
atelier run nightly_status
```

Expect `NIGHTLY_OK` after the status listing (which is empty for a clean tree).
Then save `nightly-status.yaml` in the project root. Replace `run_path` with
the absolute path to that project; the conduit resolves inside that directory.
Change `timezone` and `times` if your intended night is elsewhere.

```yaml
conduit_name: nightly_status
run_path: /absolute/path/to/your/repo
schedule:
  mode: recurring
  name: nightly-status
  days: [1, 2, 3, 4, 5, 6, 7]
  times: ["02:00"]
  timezone: America/Bogota
```

Install, inspect the next fire time, then keep the scheduler running:

```bash
atelier schedule add nightly-status.yaml
atelier list schedules
atelier schedule daemon
```

The daemon runs in the foreground; Ctrl+C stops it. Listing a schedule does
not start it or prove a scheduler is alive. This project-local schedule needs
`atelier schedule daemon` running from the project root to fire. `atelier serve`
also embeds a scheduler, but it reads **global** schedules instead; see
[scheduling](scheduling.md#where-schedules-live) before using that alternative.
Only the conduit's manual run and the add/list/remove path were verified here;
no daemon was started and no timed fire was tested.

When you no longer want the schedule:

```bash
atelier schedule rm nightly-status
```

If it fails: `atelier diagnose latest`. If no flow was created, check
`atelier list schedules`, the absolute `run_path`, and that the project daemon
is running; there is no failed flow for `diagnose` to explain yet.
