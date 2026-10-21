# blocks/

Slim the shipped context library (`docs/contexts/coga/*`, 60 topics) so that
each topic carries only knowledge a repo *using* Coga needs. Facts that a
template or config file can state for itself move there; knowledge only
needed to change Coga moves to `coga-dev`; duplicates collapse to one owner.

Origin: a `bootstrap/orient` audit on 2026-10-21, after `coga/dev-record` was
deleted (`3bbe41c6c`) because the self-documenting ticket template (#1034)
already stated its content.

## The test applied to every topic

1. **Who reads it?** AGENT (an agent working in an adopting repo; cited by the
   base prompt, a skill, a workflow, or a bootstrap target), HUMAN (an
   operator configuring or running Coga), DEV (only someone changing Coga).
2. **Is it already stated elsewhere?** The ticket template
   (`src/coga/resources/ticket.md`), the shipped `coga.toml` comments, the base
   prompt (`src/coga/resources/prompt.md`), `coga <cmd> --help`, or another
   topic.
3. **Verdict:** KEEP, TRIM (move named parts out), MERGE into another user
   topic, SPLIT then DELETE, or DELETE.

Worked example, `coga/agents`: no agent needs it; its keys belong in
`coga.toml` comments; its internals belong in coga-dev. It is split, not moved
wholesale, because `coga.toml` and a runtime warning point at it and coga-dev
does not ship.

## Rules for every ticket in this group

- One owner per fact (`coga/knowledge`). A shipped topic may not depend on a
  coga-dev topic as required reading; linking to coga-dev for optional depth
  is fine.
- Edit `docs/contexts/<ref>/SKILL.md` and its packaged twin
  `src/coga/resources/templates/coga/bootstrap/contexts/<ref>/SKILL.md`
  together; `tests/test_packaging.py` enforces byte-identity.
- When deleting a topic: remove both copies, drop it from
  `REQUIRED_BOOTSTRAP_CONTEXT_REFS` in `tests/test_packaging.py` if listed,
  and repoint every link (`grep -rn '<ref>' docs src tests coga README.md
  AGENTS.md`, excluding `docs/archive/` and `coga/log.md`). Old tickets that
  merely mention the ref need no change.
- Dated owner decisions, PR/ticket-number history, private function names,
  and test names do not ship. Move them to a coga-dev page (existing one
  preferred; a new one gets listed in `docs/contexts/coga-dev/internals/SKILL.md`)
  or drop them when git history is enough.
- "Known gap" bug notes do not ship. Turn each into a draft ticket with
  `coga create` (top level, not in this group) and delete the paragraph.
- Text true only inside the Coga repo (its archive, its skill packs,
  `upstream-coga`, `relay-os/`) does not ship.
- Keep `docs/contexts/coga/architecture/SKILL.md`'s topic map and
  `docs/README.md` current with deletions and merges.
- Verify with `.venv/bin/python -m pytest` and `coga validate --json`.

## Ordering

`01` and `02` go first: they delete topics that others link to and add
sections other tickets rely on (`init` gains instruction files,
`architecture` gains "Who Coga acts as"). `03`–`09` are independent families
and may run in any order; they touch some shared files (architecture map,
coga-dev internals index), so reconcile with main before publishing.

| Ticket | Topics |
|---|---|
| 01 | agents; `coga.toml` comment gaps |
| 02 | code; Coga-repo-only text and Known gaps across all topics |
| 03 | checkouts (+chat, launch-boundary, manual, reconciliation, sandbox-clone), checkout-cleanup (+branch-sweep, proofs, terminal-owners) |
| 04 | recurring (+autofix, delegation, scheduling, scheduling/failures, scheduling/inactivity, scheduling/ledger, templates), period-task |
| 05 | notifications (+failures, producers), important |
| 06 | state-publication (+authoring, sweep), sync |
| 07 | tickets (+authoring, discovery, ownership), secrets, blackboard |
| 08 | launch, prompt-composition, session-conduct, lifecycle, megalaunch, human-assist, pr-publication (+existing-pr, preparation), script-tickets, workflows |
| 09 | configuration, context-layout, edge-code, extension-model, first-task, init, install, knowledge, skill-management, sandboxes, usage, cli, uninstall, architecture |

## Audit table (2026-10-21, main at `3bbe41c6c`)

The verdicts are recommendations from the audit, not owner decisions. Each
ticket re-checks them against current main before editing; disagreement goes
on that ticket's blackboard for the owner.

### Delete, merge, or split (11)

| Topic | Reader | Verdict | Where the content goes |
|---|---|---|---|
| agents | H | Split → delete | Keys → `coga.toml` comments; warning limits → coga-dev `internals/agent-spawn`; merge/default/peer internals → new coga-dev `internals/agent-config`; instruction files → `init`; "Who Coga acts as" → `architecture` |
| code | — | Delete | Every bullet repeats another topic; repoint `architecture:76`, `lifecycle:165` (→ `blackboard#superseded-designs`); "record is explicit, not inferred from slug" → `checkouts` |
| checkout-cleanup/proofs | A, H | Merge → checkout-cleanup | Mostly the legacy linked-worktree layout; `-d`→`-D` escalation, `discover_coga_repos` → coga-dev |
| pr-publication/existing-pr | A | Merge → pr-publication | 38 lines; repoint `bootstrap/skills/code/open-pr/SKILL.md` |
| recurring/scheduling/ledger | H, D | Merge → scheduling | ~10 user lines; backward-read/union-merge → coga-dev `internals/recurring-admission` |
| recurring/scheduling/failures | H, D | Merge → scheduling | Known gaps → tickets; repoint autofix's `#failures-and-exit-code` link |
| notifications/failures | D | Split → delete | ~6-line user summary (crash vs best-effort, rotate a leaked webhook) → `notifications`; rest → new coga-dev `internals/notifications` |
| session-conduct | D, H | Merge → prompt-composition | "Postures" paraphrases the `prompt-*.md` resources; keep selection table + override note |
| state-publication/authoring | D | Split → delete | Three facts → finalize skill or `state-publication`; fingerprinting etc. → coga-dev `internals/state-publication` |
| state-publication/sweep | D, A | Split → delete | Strict recipe + recovery → `state-publication`; `_should_sweep_coga_state` etc. → coga-dev |
| tickets/ownership | H | Merge → tickets | Gates as a short section; transaction rationale → coga-dev `microkernel` |

### Trim (42)

| Topic | Reader | What leaves |
|---|---|---|
| blackboard | A | Fence regex, `split_body`/`upsert`, archive projection, `_is_stock_blackboard`, race → new coga-dev `internals/blackboard-io` |
| checkout-cleanup | A, H | Known gap → ticket; `classify_checkout`/`worktree_owner` → coga-dev; broken `../../../archive` link |
| checkout-cleanup/branch-sweep | H | patch-id/submodule algorithm, tag collisions → new coga-dev `internals/branch-sweep`; `_local_branches` gap → ticket |
| checkout-cleanup/terminal-owners | A, H | Worklist backfill/union-merge → `coga/autoclose/sweep` skill or coga-dev |
| checkouts | A | Re-preflight after refresh, "never changes directory", 2026-10-06 decision, template adoption history → coga-dev `git-refresh`; single owner for "Direct chat" (vs `chat`) |
| checkouts/chat | A | Lock location, receipt/reservation pinning → coga-dev `launch-claims` |
| checkouts/launch-boundary | A | Re-pin loop, `read-tree`/`update-ref`, contexts-root capture → coga-dev `git-refresh` |
| configuration | H | `_reject_unknown_keys` etc., "adding a key means…" → coga-dev `codebase` |
| context-layout | A, H | Distribution states, fallback-only launcher rule, "This repo overrides…" → coga-dev `packaging` |
| edge-code | H | Packaging invariants, phone-home refactor note → coga-dev `microkernel` |
| extension-model | H, A | Kernel tier, "No inversion", prepare-checkout justification, unbuilt hook → `microkernel`; recipe/alias lists: one owner (`cli`) |
| first-task | H | Step 2 restates launch activation/preflight → one sentence + link |
| human-assist | H | Function names, alignment loop, `COGA_ASSIST_*` → coga-dev `assist-publication` |
| important | H, A | Coga repo's usage-report exception (lines 10–15) |
| init | H | "Ticket-writing template" (ticket.md self-documents); gains instruction files from 01 |
| install | H | Windows `fcntl` analysis, dated owner decisions → coga-dev `current-direction` |
| knowledge | A | `docs/archive/*` rows: generalize or → coga-dev `archive-access` |
| launch | A, H | Lines 12–31 (`LaunchResult`/`LaunchBail`, phases) → coga-dev; checkout boundary → summary + link to launch-boundary |
| lifecycle | A, H | "Writer validation timing" → coga-dev; repoint `commands/owner.py` comment |
| megalaunch | H | Flag prose (`--help`); `_drain_satisfied_blockers`, `service_order` → coga-dev |
| notifications | H | Configuration section (coga.toml owns it); message format, test snapshot, history, "Adding a notifying command" → coga-dev `internals/notifications` |
| notifications/producers | H | Caller column, accounting rule → coga-dev |
| period-task | A | Digest-writer anecdote → coga-dev gotchas; Python API → `recurring/templates`. Auto-attached to every period prompt |
| pr-publication | A, H | Private function names, retired-layout clauses, record parsing → coga-dev |
| pr-publication/preparation | A | (keep) optionally shorten body-rendering paragraph |
| prompt-composition | H, D | Temp files, launch-marker/cache rationale, class/error names, validate codes, argv delivery → new coga-dev `internals/compose`; last paragraph duplicates ticket.md |
| recurring | H, A | Source-file list; commands table duplicates `--help`/scheduling |
| recurring/autofix | H | fd-tee, `parse_analysis`, codex stdin, auth retry → new coga-dev `internals/recurring-autofix` |
| recurring/delegation | H, A | "Why delegate…" alternatives → coga-dev; generation guards → link `recurring-admission` |
| recurring/scheduling | H, A | Clone deadline/Windows job object → new coga-dev `internals/recurring-clone`; skew paragraph → install; "This repo's `upstream-coga`" |
| recurring/scheduling/inactivity | H | `_read_inactivity_fields`, ledger pre-pass → coga-dev; add commented `idle_days` to coga.toml |
| recurring/templates | H, A | PR #857, test-name pin, "Shipped templates in the Coga source repo" → coga-dev `packaging`; "Weekly usage battery" (owned by phone-home) |
| sandboxes | A, H | 2026-10-14 rationale → coga-dev `agent-spawn`; stale "`git worktree add`" (line 41); repoint `agents#launch-environment-inheritance` |
| script-tickets | H, A | "Why this shape" (PR #700), `run_script_phase` internals → coga-dev |
| secrets | H, A | Syntax list (ticket.md owns it), function names → coga-dev; keep vault policy |
| skill-management | H | This repo's google-agents-cli/anthropic examples; PR-checkout failure + legacy-digest migration → coga-dev; command list → `--help` |
| sync | A, H | Control-vs-feature bullets (state-publication owns them); design rule, 2026-10-01 decision → coga-dev `patterns` |
| tickets | A | Frontmatter list (ticket.md owns it) → validation rules only; `body_sections` parser, allowlist rationale → coga-dev; repoint `agents#the-default-agent` |
| tickets/authoring | H, A | `coga create` flags (`--help`); "Creation template" → coga-dev |
| tickets/discovery | A, H | #889/#899 history, `relay-os/tasks` pathspecs → coga-dev |
| usage | H | "Facts a future price table needs" → coga-dev `activity-capture`; "team runs on a subscription"; `docs/archive/evidence` links |
| workflows | A | Branch-gate scope history, code-review gate history, Dream W43 case, measurement reading rules → coga-dev |
| cli | A, H | Recipe list missing `prepare-checkout`; alias paragraph → pointer to coga.toml |

### Keep (7)

`architecture` (gains "Who Coga acts as"), `checkouts/manual`,
`checkouts/reconciliation`, `checkouts/sandbox-clone`,
`pr-publication/preparation`, `state-publication` (absorbs sweep's user
content), `uninstall` (optionally drop `_build_plan`/`_configured_contexts_root`).

### Cross-cutting findings

- `coga.toml` lacks comments for `peer`, `file`, `[recurring] idle_days`,
  `[launch] idle_timeout`/`max_session`, `[autofix] agent`; `[notification.*]`
  is documented twice (coga.toml and `coga/notifications`).
- Facts stated several times: serviced-period ledger (recurring, period-task,
  templates, scheduling/ledger); state-publication roots and hazard
  (state-publication, sweep, sync); checkout boundary (launch, checkouts,
  launch-boundary); recurring commands (recurring, scheduling, `--help`);
  recipe and alias lists (cli, extension-model, AGENTS.md); assist
  attribution exception (launch, human-assist).
- The installed `coga 0.4.1` composed `dev/checkouts` into a chat prompt while
  repo `prompt.md` says `coga/checkouts`; the installed CLI lags the checkout.
