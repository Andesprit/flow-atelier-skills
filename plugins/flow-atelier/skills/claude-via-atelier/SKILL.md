---
name: claude-via-atelier
description: Delegate work to Claude Code through Flow Atelier's interactive `atelier ask`, answer Claude's follow-up questions, independently inspect and verify the result, and report Claude's final response alongside Codex's own conclusion. Use only when the user explicitly asks to use, consult, delegate to, pair with, or otherwise ask Claude, or invokes `$claude-via-atelier`; otherwise handle work with Codex. For explicit requests to use another Atelier harness, use the `flow-atelier` skill.
version: 1.0.0
---

# Claude via Atelier

Use this workflow only after an explicit user request for Claude. Ordinary work
remains with Codex. For an explicit request to use another Atelier harness, use
the `flow-atelier` skill.

Claude performs the first pass through the locally authenticated Claude Code ACP
harness. Codex remains present for questions and accountable for the final result.

Source: <https://github.com/Andesprit/flow-atelier>

Codex is the caller throughout; any agent that can drive a PTY plays the same
role.

## Workflow

1. Resolve the absolute working directory.
   - Use the repository or workspace in scope.
   - For a general task with no better target, use the current working directory.
   - Before a task that may edit files, record the existing git status and
     preserve unrelated changes.

2. Write a self-contained delegation prompt.
   - Include the user's requested outcome, relevant constraints, target files,
     and acceptance checks.
   - Tell Claude whether the task is read-only or may modify files.
   - Ask Claude to request clarification when needed and not to signal completion
     until it has performed and checked the work.
   - Do not forward secrets or credentials. Flow logs are unredacted.

3. Start Claude through Flow Atelier in a PTY:

   ```bash
   atelier ask "<delegation prompt>" --path "<absolute working directory>"
   ```

   Pass the prompt as one safely quoted argument. Never allow prompt text to
   become shell syntax. Keep the command attached to a live terminal so Claude
   can hand the turn back.
   - An explicit request to use, consult, delegate to, or pair with Claude
     authorizes sending task-relevant, non-secret context to the local Claude
     harness. Cite that authorization if sandbox escalation is required.
   - If the standalone binary fails with a `semctl` or semaphore permission
     error, retry the same narrowly scoped command with sandbox escalation. This
     is an execution restriction, not a missing Atelier installation.

4. Answer every Claude question.
   - Answer from the repository, conversation, and the user's stated intent
     whenever the answer is discoverable.
   - Ask the user only when Claude exposes a material product choice, missing
     authority, secret, or irreversible decision that belongs to them.
   - Send the answer to the running PTY. For the multiline prompt, submit with
     Alt+Enter; when controlling a PTY programmatically, send Escape and Enter
     separately if a combined sequence does not submit.
   - Continue until the flow completes. Do not leave Claude waiting for input.
   - `atelier ask` prints `· run page <url>` when the flow starts. Give the user
     that link so they can follow Claude's work live, as the flow-atelier
     skill's "Show the user the run page" section describes.

5. Recover Claude's final statement from the recorded flow.
   - Capture the `flow_id` printed by `atelier ask`.
   - Run `atelier outputs <flow_id> --json`. The `chat` value is Claude's final
     turn with the internal completion marker removed.
   - Use `atelier logs <flow_id> --json` only when the earlier conversation is
     needed; never paste unredacted logs blindly.

6. Verify independently.
   - For code changes, inspect the diff and run the most relevant tests or
     checks yourself.
   - For analysis or writing, check Claude's claims against the available
     evidence and the user's constraints.
   - If the result is incomplete or incorrect, delegate a focused correction
     through another `atelier ask` run and verify again.
   - Do not silently replace a failed delegation by doing the primary work
     yourself. Re-delegate or report the blocker.

## Final response

Always present both perspectives:

```markdown
Codex

<Codex's verified conclusion and what actually changed>

Claude said

> <Claude's final `chat` output, verbatim>

Interaction

- <questions Claude asked and the answers Codex supplied, or "No questions">

Verification

- <checks run and their outcomes>
```

Keep Claude's final wording unchanged. If it contains a credential or other
sensitive value, redact only that value and state that a redaction was made. Do
not present Claude's words as Codex's independent verification.

## Failure handling

- If `atelier ask` is unavailable, run `atelier --version` and
  `atelier harness check claude-code` to distinguish installation from harness
  authentication problems.
- Never fabricate a Claude response. State that delegation failed and why.
- If the user required delegation, ask before proceeding without Claude.
- Do not start a second delegation for the same task while one is already
  running.
