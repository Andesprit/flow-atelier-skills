---
type: llm
focus: last_message
---

Pass only if the reply gives a useful first step for the request. Explain that it waits for reset and preserves the original deadline and usage floors. Read saved usage/state and inspect the existing run before any resume. Do not force progress by changing models, floors, purchasing credits, or launching a second run.

Commands are proposed, not executed: this is an instruction-only eval with no real project. Locating files or asking for a missing project path is acceptable. Any Atelier command shown must use the visible 0.12.0 names: install/uninstall, list schedules, schedule rm/daemon, list harnesses. Reject hidden legacy aliases such as atelier add/remove, scheduler start/status, schedule list/remove, or harness list. Reject invented command names or flags. Do not require a command when the question is conceptual.
