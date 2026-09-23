---
name: coga/dream
description: What Dream is and the contracts it keeps — a recurring janitor template with a fixed ordered phase list and no plugin discovery, bounded shard scans, retro knowledge PRs versus direct deletes, deferred checkout debt, and REM as the user-space alternative.
---

# Dream

Dream is Coga's generic ticket-cleanup pass: an ordinary recurring template at
`coga/recurring/dream/` (packaged twin in `src/coga/resources/templates/`) plus
the default alias `coga dream` = `coga recurring launch dream`. It has no
`workflow:` and so runs as `direct/body`; it is agent-backed and interactive,
and every sweep launches it **last** so its retro pass sees the period tasks the
same sweep finished (see [scheduling](../recurring/scheduling/SKILL.md)). It is
the agent instance of the correction loop: durable drift becomes a proposal PR
or draft ticket for a human to merge, never a silent edit to operating rules.

The template body is the procedure; this topic states the contracts it must keep.

## Fixed phases, no registry

The body's ordered list is the only control point. Phases 1–3 **decide** while
every done ticket still exists; phases 4–6 **execute**:

1. `validate-drift` — registered recipe (`coga run validate-drift`).
2. knowledge scan — sharded read of the repo's own corpus.
3. contract audit — sharded check of the contract surface against code.
4. retro/done-ticket — extract durable knowledge, delete eligible done tickets.
5. `cleanup-orphan-markers` — registered recipe, delete-only.
6. disposition and run summary — every finding ends in a PR, draft ticket or
   recorded marker, never only on Dream's blackboard.

Dream is not a plugin host: no recursive discovery, no registry, no daemon.
Dropping a `SKILL.md` under `bootstrap/dream/tasks/` enables nothing; adding a
phase is a normal change to the template. A failing phase is recorded and
permits no substitute. Deterministic phases read the skill's
`## Known Skill Contract` (`Purpose`, `Runs`, `Inputs`, `May change`, `Action`
— `report-only` | `proposal-only` | `pr-required` | `direct-fix` —
`Idempotency`, `Stop and ask`, `Output`) and invoke the recipe from the Dream
task itself: the recipe inherits Dream's `COGA_TASK_*` and writes
`## Dream Skill: <name>` to Dream's blackboard. No child task or worker workflow
is created, and no nested `coga launch`. The skills are
`bootstrap/dream/tasks/{validate-drift,cleanup-orphan-markers}`; the ticket.py
classifier only stats one reserved path in the named target and never scans
this tree.

The decide-half scans are prompt-only skills under `bootstrap/dream/scan/`
(`knowledge-scan`, `contract-audit`, shared rules in `scan-protocol`): only
`name`/`description` frontmatter and a prompt body, no Known Skill Contract.
They run as bounded shard subagents that write findings to disk. Completion is
reconciled at the barrier by the set of **distinct shard ids** that wrote a
completion line to the append-only `progress.md`, never by counting lines; a
missing line is not zero findings. One retry, then `partial`.

**Known corpus limitation.** Both scans exclude package-backed
`bootstrap/skills/**` (a run indexed zero entries while ~30 Markdown files live
there). Their corpora otherwise differ: the knowledge scan owns tickets and
`coga/workflows/**`; the contract audit adds recurring templates, `README.md`,
`docs/*.md`, `CLAUDE.md`/`AGENTS.md` and treats `coga/tasks/` as history. The
fix is a corpus decision for both, not a per-phase patch.

## Retro and deletion

A done ticket is eligible when its directory exists, its `## Dev` has no real
`branch:`/`worktree:`, and no open PR is already adding its `## Retro` marker or
deleting it. A ticket that contributed knowledge is deleted inside its theme's
**knowledge PR** (which records the marker); one carrying nothing durable is
**direct-deleted** (`coga delete`, no PR, no marker). Recurring period tickets
are usually nothing-durable, but read the blackboard (`## Gotchas`) before
deleting — never decide by class alone. Checkout-bearing done tickets are
**deferred retirement debt**: Dream lists them and never runs `coga retire`
(see [dev/checkouts](../../dev/checkouts/SKILL.md)). Dream never deletes its own
predecessor; the scanner removes it before creating the next Dream period.

## Results and safety

The run summary uses: `no-op`, `reported`, `partial`, `proposed`,
`direct-fixed`, `pr-opened`, `human-needed`, `upstream-captured`. The last is
the client-repo route: a finding owned by the Coga package (`owner: coga`) is
appended to that repo's `coga/upstream-coga.md`; the Coga source repo's
`recurring/upstream-coga` job sweeps those into tickets. Destructive changes
(deleting tasks or refs, lifecycle changes, secrets) are never implicit: a skill
may declare one only when it is deterministic, narrow and named in
`May change`; otherwise it proposes or opens a PR.

## REM

REM is user-space: a repo's own recurring maintenance template (health checks,
follow-ups, domain reports, repo-specific audits) with its own cadence, skill
order and review gates, authored like any template
([templates](../recurring/templates/SKILL.md)). Want a different loop than
Dream? Write a REM template; do not patch Dream. Generic Coga cleanup does not
belong in REM. A REM run writes one concise summary to its period blackboard,
listing PRs, tickets and human gates.
