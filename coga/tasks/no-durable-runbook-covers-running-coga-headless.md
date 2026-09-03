---
slug: no-durable-runbook-covers-running-coga-headless
title: No durable runbook covers running Coga headless
status: canceled
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
---

## Description

Three separate `v2/` drafts each rebuild the same headless-operation runbook from scratch:
service-account auth without an interactive `op` prompt, what `missing-user` means for a runner
(it warns and exits 0, but the sweep then exits 2, and since PR #613 `recurring --all` skips such a
checkout as "unconfigured" while the aggregate run still succeeds), and how to preflight a cron
host. The shared runbook is knowledge that exists independently of any of those three tickets.

Write it once — likely a new `coga/headless` context — and let the drafts reference it.

## Context

Found by Dream 2026-08-24, Phase 2 knowledge scan (shard-11), classified `gap`.

Note the related `stale` finding on `coga/contexts/coga/secrets/SKILL.md`: it claims the SA token
makes "every `op://` ref" resolve, which is true for ticket `secrets:` frontmatter and false for
config values, which are not `op://`-aware at all. Fix that before writing a runbook on top of it.

<!-- coga:blackboard -->

## Premise check (2026-09-03) — result: premise-dead, canceled

Run per the `coga/tasks/v2/README.md` premise check before pulling any of the
three motivating drafts forward.

**1. Does the subject still exist?** Not as live work. All three drafts this
ticket generalizes are parked in `coga/tasks/v2/`, which `coga/roadmap`
("Deferred work") defines as work *not on the current execution path*:

- `v2/op-service-account-auth-to-skip-op-read-prompt` — likely premise-dead on
  its own terms. `coga/contexts/coga/secrets/SKILL.md` already records that the
  `op` CLI auto-uses `OP_SERVICE_ACCOUNT_TOKEN` when set, so headless SA auth
  needs **no coga code change** — which is that draft's entire ask.
- `v2/wire-recurring-sweep-into-system-cron` — pre-rename `relay` cohort (9
  `relay` mentions). Its central surface, `relay-os/scripts/cron.sh`, does not
  exist in this repo. Known-stale per the v2 README.
- `v2/fail-validation-when-local-user-is-required-for-ex` — the only one with a
  live premise and a real downstream consumer (FastJVM/patents PR #130). It
  already carries its own `code/with-review` workflow, so the `missing-user`
  preflight semantics are covered there, not here.

**2. Do the surfaces it names still resolve?** The one concrete task in
`## Context` — fix the stale `op://` claim in `coga/contexts/coga/secrets/SKILL.md`
— already shipped in commit `7d220a1f` ("Correct three contradicted claims in
the coga/secrets context", #714). That context now reads: *"Config values
resolve almost nothing… `op://` is not understood in config at all."* Nothing
left to fix.

**3. Would a new `coga/headless` context earn its place?** No. The headless
facts Coga actually ships in v1 are already homed and would be duplicated:

- `coga/contexts/coga/recurring/SKILL.md` — TTY admission (agent templates need
  stdin+stdout TTYs and run under the REPL supervisor; a TTY-less sweep skips
  them with a warning), the `ticket.py` headless path as the appropriate shape
  for an unattended scheduler, and console output being the only failure
  surface under cron.
- `coga/contexts/coga/secrets/SKILL.md` — SA auth, and the human delivering
  `OP_SERVICE_ACCOUNT_TOKEN` into the cron/systemd environment at run time.

A third context restating both would violate `coga/project-stage` ("no
premature generality" / "bias toward deletion") to document a mode
`coga/roadmap` item 3 says Coga has not shipped: *"Operator scheduling remains
outside Coga until a concrete scheduling design is approved."*

**Disposition.** Canceled by nicktoper on 2026-09-03 after review. If operator
scheduling is ever approved and a real runbook is needed, the live facts to
start from are the two contexts named above — not this ticket's three parked
drafts.
