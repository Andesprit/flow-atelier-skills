---
type: llm
focus: last_message
---

Pass only if the reply gives a useful first step for the request. The first recovery command must be atelier diagnose 20261021_d34db33f_tick, before logs, status or retry.

Commands are proposed, not executed: this is an instruction-only eval with no real project. Locating files or asking for a missing project path is acceptable. Any Atelier command shown must use the visible 0.12.0 names: install/uninstall, list schedules, schedule rm/daemon, list harnesses. Reject hidden legacy aliases such as atelier add/remove, scheduler start/status, schedule list/remove, or harness list. Reject invented command names or flags. Do not require a command when the question is conceptual.
