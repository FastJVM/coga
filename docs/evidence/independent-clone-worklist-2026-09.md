# Another clone's primary checkout on the autoclose worklist

Evidence recorded 2026-09-29 for the known failure mode in
[`dev/checkout-cleanup`](../contexts/dev/checkout-cleanup/SKILL.md)
(*another clone's primary checkout never discharges*). These are
point-in-time, machine-specific observations; the topic keeps only the
durable failure mode and workaround.

## Observations

- The 2026-09-29 `recurring/autoclose-merged` run from
  `/home/n/Code/claude/coga` reported six entries naming `/home/n/Code/coga`
  (for example `installer-managed-skills-the-local-adaptation-guar`) or
  `/home/n/Code/codex/coga` (for example
  `make-dream-run-correctly-under-codex`), each with its branch absent
  locally and on `origin`.
- A machine-wide worktree inventory on 2026-09-23 confirmed that both paths
  are primary checkouts of separate FastJVM/coga clones with their own linked
  worktrees, and that `/home/n/Code/coga` had live sessions.
- The owner decided on 2026-09-22 to keep independent clones on the worklist
  as their only durable trace. That decision was made with disposable
  fallback clones in mind and did not address this case.
- As of 2026-09-29, no fix or follow-up ticket existed.
