# First run

Reach a first working flow from a shell in a few commands. It needs the `atelier`
CLI only: no agent, login, server or package.

Every command in this guide runs in a terminal (shell), not as a message to an
agent. Commands that start with `/plugin` belong in a Claude Code session and do
not appear here.

## 1. Check the CLI

```bash
atelier --version
```

It prints a version such as `flow-atelier 0.12.0`. `command not found: atelier`
means the CLI is not installed or not on `PATH`. Install it:

```bash
curl -fsSL https://raw.githubusercontent.com/Andesprit/flow-atelier/main/install.sh | bash
```

Or, with Python 3.13+ and uv, `uv tool install flow-atelier`. Open a new
terminal if the command is still not found. A uv install prints
`Tip: run uv tool upgrade flow-atelier ...` on each call; it is not an error.

## 2. Run hello in a scratch directory

Use a new directory so the example cannot change an existing project's conduits:

```bash
mkdir atelier-first-run && cd atelier-first-run
atelier init
atelier check hello
atelier run hello --input name=world
```

Expected:

- `atelier init` prints `initialized <path>/.atelier` and
  `try: atelier run hello --input name=world`.
- `atelier check hello` prints `hello [project] — OK` and `requires --input: name`.
- `atelier run hello` shows one task, `greet [tool:bash]`, with the output
  `hello world`, a `✓1` summary and a `flow_id: <date>_<id>_hello` line. The
  command exits 0.

The run also prints a `run page http://127.0.0.1:8000/runs/...` link. That page
opens only while `atelier serve` is running in this same directory; you do not
need it to see the result. See "Show the user the run page" in the skill.

## What this proves, and what it does not

It proves the CLI works, can create and validate a conduit, and can run a shell
step and save the flow under `.atelier/flows/`. It does not prove that any coding
agent is installed or logged in, that a packaged conduit is installed, or that a
schedule will fire. Check an agent before its first use:

```bash
atelier harness check claude-code
```

The check sends no prompt. `atelier list harnesses` showing `ready yes` only means
the launcher was found, not that you are logged in. See
[harnesses](harnesses.md#checking-one-before-you-use-it).

## Next

- [Recipes](recipes.md): review loops, draft-then-review, an approval gate before a
  shell step, test-and-fix loops and a nightly schedule. Recipes with agent steps
  spend that agent's quota when you run them; preview first with `atelier plan`.
- [conduit.yaml reference](conduit-yaml.md) to write your own.
- Optional: [recovery exercise](recovery-exercise.md) - make a harmless shell
  flow fail on purpose, diagnose it, fix it and resume the same run.
- Optional: [choose an agent for one run](harnesses.md#choosing-an-agent-for-one-run)
  without editing the workflow, or [give tasks separate checkouts](task-worktrees.md)
  and find their results.

## When a step fails

| Symptom | Missing layer | Next check or fix |
|---|---|---|
| The skill does not load in Claude Code | plugin | `claude plugin list` shows whether the plugin is installed and enabled. `claude plugin details flow-atelier` lists its skills. Start a new session after installing. |
| `command not found: atelier` | CLI | Install it (step 1) or fix `PATH`, then `atelier --version`. |
| `unknown conduit: hello` | project not initialised here | Run `atelier init` in this directory, or `cd` to where you ran it. `atelier list conduits` shows what this directory sees. |
| `unknown conduit: <package conduit>` | package not installed | Follow that package's setup, then `atelier list conduits`. |
| An agent task cannot start or open a session | harness | `atelier harness check <name>`; log in with that agent's own CLI. See [harnesses](harnesses.md). |
| A saved run failed | the conduit or its tasks | `atelier diagnose <flow_id>` first; follow any child `atelier diagnose` it prints. See [troubleshooting](troubleshooting.md#a-run-failed-start-here). |
