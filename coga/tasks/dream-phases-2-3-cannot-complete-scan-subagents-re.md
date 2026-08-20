---
slug: dream-phases-2-3-cannot-complete-scan-subagents-re
title: 'Dream phases 2-3 cannot complete: scan subagents return no findings'
status: in_progress
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
step: 3 (open-pr)
---

## Description

Dream's two decide-half scan phases could not complete in the `2026-W34` run.
Phases 1, 4, 5 and 6 all worked; Phases 2 and 3 produced **no findings at all**,
so that run routed no `stale`/`drift` proposal PRs and no `gap` tickets — an
absence of input, not a clean repo.

Phase 2 (`bootstrap/dream/scan/knowledge-scan`) and Phase 3
(`bootstrap/dream/scan/contract-audit`) are both specified as
"delegate this phase to a subagent". In that run every scan subagent spawned,
read part of the corpus, and then stopped without ever returning a findings
list to Dream:

- `knowledge-scan` — read ~120KB of corpus, output froze after ~1 minute.
- `contract-audit` — read ~53KB including `coga/log.md`, froze after ~5 minutes.
- a retry with an explicitly tightened reading budget produced no transcript at
  all and returned nothing within its 5-minute window.

All three later emitted `idle_notification` / `idleReason: available`. Messaged
directly and asked to return whatever partial findings they had — including one
request that forbade any tool use and asked only for plain text — each replied
with another bare idle notification and no content.

Notably, Phase 4's Retro subagent *did* work in the same session (86 tool uses,
~9.5 minutes, opened PR #698 and landed 10 direct deletes). So this is not
simply "subagents are broken here". The distinguishing feature of the two failed
phases is that each is a single long read-only sweep over the whole corpus whose
entire value is delivered in one final message.

### What to work out

1. Reproduce, and establish whether the cause is a context/output-size limit on
   the final message, a liveness timeout on a long tool-free stretch, or
   something specific to how these two scans are prompted.
2. Decide whether a silently result-less scan phase should be *detectable* by
   Dream. Today Dream cannot tell "scan ran, found nothing" from "scan never
   returned", and only noticed because the subagent's own progress was being
   watched. A scan that must report `no findings` explicitly, or a required
   heartbeat, would remove the ambiguity.
3. Consider making the scans stream durable partial output the way Phase 4 was
   made to. The `2026-W34` Retro pass only survived scrutiny because it was told
   to append every step to an on-disk progress log; that log, not the agent's
   final message, is what made the phase verifiable. The same hedge would have
   salvaged partial scan findings.
4. If the corpus is simply too large for one subagent read, the fix may be to
   partition the scan (by area, or contexts-vs-tickets) rather than to keep
   retrying one sweep — but that changes the "single full-corpus read" design in
   `knowledge-scan/SKILL.md`, which exists so the running delta can de-duplicate
   across the whole corpus. Weigh that tradeoff explicitly.

Any behavior change here must update the matching skill file(s) under
`coga/.agent-skills/bootstrap/dream/scan/` and the packaged copies, plus the
Dream template body in both `coga/recurring/dream/ticket.md` and
`src/coga/resources/templates/coga/recurring/dream/ticket.md`.

## Context

Raised by the `recurring/dream` run for period `2026-W34`. That Dream task is
`done` and will be deleted by the next firing, so this ticket is the durable
record — its blackboard is gone by then.

<!-- coga:blackboard -->

## Plan

The contract-level defect is measurable without another live Dream run: the two
scan skills mandate a read that cannot fit, then make one final message the only
delivery path. The prior run does not distinguish the immediate stop mechanism
(context exhaustion versus liveness), so the fix removes both dependencies.

- `coga/tasks/**/*.md` — 696,419 bytes
- `coga/contexts/**` + `coga/skills/**` — 697,646 bytes
- `coga/log.md` — 805,414 bytes (the `contract-audit` run burned its budget here)
- largest single files: `coga/contexts/coga/architecture/SKILL.md` (55 KB),
  `coga/contexts/coga/sync/SKILL.md` (54 KB), `coga/tasks/recurring-recipe-question.md` (47 KB)

`knowledge-scan/SKILL.md` says "the single full-corpus read of the run: the
subagent reads every ticket body and blackboard, and every context, skill, and
workflow file" — that is ~1.4 MB, past a subagent's context window before any
findings can be emitted. Phase 4's Retro subagent survived the same session
because it works ticket-by-ticket and its value lands in PRs and deletes on
disk, not in one terminal message.

That covers the actionable part of items 1 and 4: the corpus really is too large
for the specified one-subagent read, and all-or-nothing final delivery makes
any early stop silent regardless of whether the immediate trigger is a context
ceiling or a liveness failure.

### Design

1. **Shard both scans.** Dream computes a shard manifest under a byte budget
   and runs one subagent per shard.
2. **Durable partial output** (item 3). Each shard appends every finding to a
   run-scoped `findings.md` the moment it decides it. Dream reads findings from
   disk, never from the subagent's final message.
3. **Explicit completion** (item 2). Each shard's last action is a completion
   line carrying its finding count; `0 findings` is a required, explicit
   result. Dream reconciles manifest vs completion lines, so "scan ran, found
   nothing" and "scan never returned" are now different observable states.
4. **Merge in Dream.** Dedup/grouping moves from raw-corpus level to the
   bounded findings file.

### Tradeoff (item 4, weighed)

The "single full-corpus read" existed so the running delta could compare
tickets with knowledge and de-duplicate across the whole corpus. Area shards
now preserve the first property by carrying both ticket and knowledge evidence;
relevant evidence may be repeated across assignments, and an enriched compact
index routes targeted cross-area reads. Global merge-time de-duplication is
still weaker than holding all evidence in one context, and duplicated evidence
costs extra reads. Accepted because concrete cross-corpus classification remains
intact while every worker stays bounded and can deliver partial work.

### Files

- new `bootstrap/dream/scan/scan-protocol/SKILL.md` — the shared durable-shard
  protocol (two consumers, so it is one file rather than duplicated prose that
  the contract audit would later flag as drift)
- `bootstrap/dream/scan/knowledge-scan/SKILL.md`
- `bootstrap/dream/scan/contract-audit/SKILL.md`
- `coga/recurring/dream/ticket.md` + packaged copy — Phases 2/3 orchestration,
  run-summary vocabulary
- `coga/contexts/coga/architecture/SKILL.md` + packaged copy — canonical
  sharded-scan and `partial` result contract
- `tests/test_dream_worker_templates.py`
- `tests/test_packaging.py`

### Note on the ticket's file list

The ticket asks to update both `coga/.agent-skills/bootstrap/dream/scan/` and
"the packaged copies". They are the same files: `coga/.agent-skills/` is a
gitignored, generated symlink view (`agent_skills.refresh_agent_skill_view`)
pointing at `src/coga/resources/templates/coga/bootstrap/skills/`. Only the
packaged path is tracked; the view is refreshed, not edited. The two
`recurring/dream/ticket.md` copies *are* genuinely separate tracked files and
both need the edit.

## Dev

pr: https://github.com/FastJVM/coga/pull/703
branch: dream-scan-shards
worktree: /home/n/Code/claude/coga-dream-scan-shards

## Implemented

Commits `ca8c99d5` (implementation) and `b7be1585` (peer-review fixes) on
`dream-scan-shards`, rebased onto `origin/main` at `80239dae`.

- **new** `.../bootstrap/skills/bootstrap/dream/scan/scan-protocol/SKILL.md` —
  the shared delivery contract both scans follow: the scan directory
  (`manifest.md`, `index.md`, `findings.md`, `progress.md`), a 150 KB / 40-file
  shard budget, "never read a file over 60 KB whole", "never read `coga/log.md`
  whole", append each finding the moment it is decided, a per-file heartbeat
  line, and the terminal `<shard-id> complete — <N> findings` line where
  `0 findings` is explicitly a valid result and a missing line explicitly is
  not. It also states that the subagent's final message is not the delivery
  mechanism — Dream reads `findings.md` from disk.
- `knowledge-scan/SKILL.md` — area shards contain both ticket and knowledge
  evidence, with compact routing metadata and bounded targeted reads for
  cross-area comparisons. It states the de-duplication/repeated-read tradeoff;
  taxonomy and the `extract` grouping are unchanged.
- `contract-audit/SKILL.md` — sharded by contract-surface group, plus a
  dedicated copy-divergence shard driven by the explicit
  `IDENTICAL_LIVE_PACKAGED_PAIRS` contract. It never recursively diffs the
  intentionally different roots, and documents that `coga/.agent-skills/` is a
  generated symlink view rather than a copy to compare.
- `coga/recurring/dream/ticket.md` + packaged copy — new
  `### Decide-half scan mechanics (Phases 2 and 3)` section: mktemp the scan
  directory, size portably with `find ... -exec wc -c`, chunk ownership and
  evidence to budget, run the shards, reconcile active manifest leaves against
  completion lines ("Do not treat a missing line as zero findings"), append an
  explicit parent-to-child supersession on retry, then merge and de-duplicate
  into `## Findings`. `partial` is in the run-summary vocabulary; console
  progress reports shards launched vs completed. Both copies are byte-identical.
- `coga/contexts/coga/architecture/SKILL.md` + packaged copy — describes the
  shared protocol, leaf reconciliation, durable findings, and `partial` result.
- `tests/test_dream_worker_templates.py` — the two existing scan tests updated
  for the sharded contract, plus
  `test_dream_scans_stream_durable_findings_and_report_completion` and
  `test_dream_shards_and_reconciles_the_scan_phases`; packaging coverage now
  proves the new protocol ships and the changed live/packaged pairs stay equal.

### Answers to the ticket's four questions

1. **Cause** — the specified sweep is larger than one bounded subagent read,
   and its all-or-nothing final delivery makes any early stop result-less. The
   captured run cannot distinguish context exhaustion from the immediate
   liveness mechanism; the new design depends on neither. Phase 4 survived
   because its value landed on disk as it went.
2. **Detectable** — yes, and now required. Explicit per-shard completion lines
   plus Dream's manifest reconciliation make "ran, found nothing" (`no-op`) a
   different state from "never returned" (`partial` + `human-needed`).
3. **Durable partial output** — adopted, and generalized from Phase 4's ad-hoc
   progress log into the protocol skill so it is contract rather than a
   per-run instruction. That hedge was never written down in
   `retro/done-ticket/SKILL.md`; it is now written down for the scans.
4. **Partition vs single sweep** — partitioned, with the cost stated in
   `knowledge-scan/SKILL.md` and above.

## Adjacent — not fixed here

Three tests fail on `main` before this change, unrelated to it (they concern
autoclose preflight and the recurring control-branch gate). Verified failing at
`70c6ec26` in the primary checkout:

- `tests/test_autoclose.py::test_recipe_preflights_live_summary_before_closing`
- `tests/test_recurring.py::test_named_launch_keeps_control_only_malformed_ledger_blocked_on_retry`
- `tests/test_recurring.py::test_sweep_retry_revalidates_control_only_malformed_ledger`

Otherwise `python3.12 -m pytest -p no:cacheprovider` on the rebased branch is
1796 passed, 1 skipped.
(The repo's `python` is 3.9; the suite needs `python3.12`.)

## Note

`scan-protocol` will not appear in this checkout's `coga/.agent-skills/` view
until the branch merges: the view is generated from the primary checkout's
packaged templates, so a skill added on a feature branch links itself after
merge. Nothing to do.

## Peer review

`codex review --base main` returned five must-fix findings:

- the ticket-only and knowledge-only shard groups cannot perform the required
  cross-corpus comparison;
- `diff -r coga/ src/coga/resources/templates/coga/` compares intentionally
  different roots and emits about 828 KB / 4,105 lines in this checkout;
- retry child shards cannot satisfy an append-only manifest that still expects
  their incomplete parent;
- `find -printf` is GNU-only and fails on macOS/BSD; and
- both architecture context copies still describe one subagent per phase and
  omit the new `partial` result.

All five are resolved in `b7be1585`. The shard partition is by area with both
ticket and knowledge evidence in each assignment; the manifest appends explicit
parent-to-child supersession records and reconciles only leaf assignments. Copy
checks use the repo's explicit `IDENTICAL_LIVE_PACKAGED_PAIRS` contract rather
than a recursive tree diff, and portable `find ... -exec wc -c {} \\;` replaces
`-printf`. Focused tests pass (14 passed, 1 skipped); both pre- and post-rebase
full suites have 1796 passed, 1 skipped, with only the three failures reproduced
on `main` above. A final `git fetch origin main` still resolved to `80239dae`;
the branch is clean and two commits ahead. Scoped validation reports one task
OK with no issues.

## PR

Shard Dream's knowledge scan and contract audit into bounded, area-aware
subagents that stream findings and heartbeats to disk, report explicit zero or
partial results, and retry through append-only manifest supersession. Preserve
ticket-vs-knowledge comparisons inside each area, audit only explicit
live/packaged counterpart pairs, use portable corpus sizing, and keep the
canonical architecture contract synchronized.

Tests: `python3.12 -m pytest -p no:cacheprovider` — 1796 passed, 1 skipped; 3 pre-existing `main` failures in autoclose preflight and recurring control-branch tests.
