---
title: 'Premise check 2026-W40: 8 parked drafts need a verdict'
status: canceled
owner: nicktoper
workflow:
  name: brief-for-human
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: owner
  - name: verify-read-only
    skills: []
    assignee: agent
---

## Description

Filed by Dream 2026-W40, Phase 6. Dream's Phase 2 knowledge scan (shards ks-34, ks-35, ks-36) asked the four premise questions in `coga/tasks/v2/README.md` of every parked draft. These eight failed a question and no open ticket already adjudicates them (27 other premise findings this run are already owned by `premise-check-2026-w39-25-parked-drafts-need-a-ver` or `adjudicate-the-eight-premise-dead-v2-drafts`). Every verdict is the author's. Use the README's vocabulary: cancel with evidence (including already-delivered work), narrow, or rewrite. A green `coga validate` is never a reason to rule a draft dead.

1. `v2/acceptance-criteria` fails **delivered** (ks-36). Its own Context says it is superseded by `the-ticket-interview-never-asks-what-done-means`, which is done, and that deliverable is on main: the packaged `bootstrap/ticket` skill asks "what would count as done?" at lines ~100, ~113 and ~369. The successor also recorded the decisions this draft proposed: done criteria as prose in `## Description`, no validate check, no `--ac` flags. Candidate verdict: cancel as delivered.
2. `v2/measure-relay-prompt-scope-and-agent-precision` fails **delivered**, in part (ks-34). Part 1 shipped. From part 2, turn counts and per-session cost are delivered by `coga/usage` and `coga/internals/activity-capture` (`human_turns`, `agent_turns`, `elapsed_seconds`, `coga usage`). Tool-call counts, human-correction counts and the cold-relaunch continuity check are not. Candidate verdict: narrow.
3. `v2/implement-accepted-ticket-interview-improvements` fails **citations** (ks-34). Its subject is live (the Step 3/4/6 changes are undelivered in `bootstrap/ticket/SKILL.md`), but the exact wording for each change lives only in a retired ticket's blackboard. The draft says to read it via `git show ffb0a383^:coga/tasks/improve-prompt-for-relay-ticket.md` (the `### Ranked changes` section near line 185 and `### Proposed Step 3 shape` near line 329). That text is still recoverable today. Candidate verdict: rewrite, inlining the substance.
4. `v2/compose-strips-skill-md-and-context-frontmatter-be` fails **surfaces** (ks-36). The subject is live: `compose.py` still injects raw `read_text()` in `_skill_layers`, `_step_layers` and the ticket-context loop. The code map, however, is `src/relay/*` with dead line anchors, and it wraps a removed global rules layer (`coga/rules.md`). Candidate verdict: rewrite against current symbols and drop the rules item.
5. `v2/absorb-compound-engineering-leaf-skills-as-a-coga` fails **surfaces** (ks-34). Its mechanism is the `managed-skills.toml` manifest, which PR #852 deleted. Skills now enter only through an explicit `coga skill install`, so the options it would weigh have changed. Candidate verdict: rewrite or cancel.
6. `v2/validate-tickets-on-hand-edit-gap-outside-relay-co` fails **surfaces** (ks-35). It names `relay draft/validate/init/launch` and `src/relay/...`. Launch already runs `validate.assert_task_valid` after its activation writes (see `coga/lifecycle` "Writer validation timing"). Two things remain: validating a hand-edited `in_progress` ticket, and documenting the enforcement boundary. Candidate verdict: narrow or rewrite.
7. `v2/use-slack-as-a-sync-channel-for-tickets` fails **surfaces** (ks-34). It is blocked on the deleted ticket `finish-slack-integration-features`. Its premise that the product has "no multi-machine story" is false: `coga/sync` defines git publication, and current-direction says git is the sync layer. Only inbound Slack → ticket creation remains, and it is listed as deliberately deferred. Candidate verdict: cancel or narrow.
8. `v2/identify-blocking-issues` fails **subject** (ks-34). It is scoped to `relay project` output, but the `project` command was removed. Its fallback, a `dependencies:` field, was decided against: `coga/tickets` "Ownership and ticket relationships" and `coga/lifecycle` "Dependencies and supersession" use blocker asks instead. Candidate verdict: cancel as settled.

**Correction to the W39 adjudication draft** (Dream shard ks-36, class stale). In `premise-check-2026-w39-25-parked-drafts-need-a-ver`, finding F49 says `v2/cleanup-core-commands/support-commands-boundary` fails question 4. It cites an extension-model section, "Trust boundaries straddle: acquire outside, verify inside", that no longer exists. The live `docs/contexts/coga/extension-model/SKILL.md` "Open command placements" table lists `secret get` / `uninstall` as unsettled and names that draft as the deferred review. The draft therefore passes all four questions today. Withdraw F49's "cancel or narrow" option when ruling on that ticket. Dream does not edit another ticket, so the correction is recorded here.

A draft ruled on here stops appearing in later Dream runs once its verdict lands. A draft left open stays owned by this ticket until the ticket closes.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
