# context-audiences/

Split Coga's context library into two explicit audiences: topics for **repos
that use Coga**, and topics for **developing Coga itself**. Coga-dev topics
stop shipping as packaged bootstrap contexts.

## Ordering

1. `01-classify-contexts-by-audience-and-decide-the-la`: drafts the criterion,
   classification table, layout and compatibility decision below. The owner
   approves.
2. `02-move-coga-dev-contexts-out-of-the-shipped-set`: carries out the
   approved decision. It depends on 01.

## Decision record

_Status: **draft by 01's agent, awaiting owner approval.** Items marked
**[owner]** are recommendations the owner should confirm or change._

Original evidence base: every `docs/contexts/**/SKILL.md` (85 topics) grepped by ref,
backticked ref, relative link, and `docs/contexts/<ref>/SKILL.md` /
GitHub-URL form across `src/`, `docs/contexts/`, `coga/`, `tests/`,
`README.md`, `AGENTS.md`, `docs/README.md` (main at `ab108fbb9`).

### Ownership relocation — 2026-10-20

The owner approved moving job-specific contracts and procedures out of
contexts. The inventory below now excludes seven former topics:

- Phone-home owns its contract in `coga/recurring/phone-home/ticket.md`
  and its maintenance runbook in the sibling `operations.md`.
- Dream owns its contract in `coga/recurring/dream/ticket.md` and its
  invoked skills.
- `coga/releasing` and `coga/testing/clean-install` (including `macos-aws`
  and `windows-aws`) are skills under `coga/skills/`, with packaged
  bootstrap skill twins. Their distribution is unchanged by this move.

Do not recreate those contexts during the audience split. Any proposal to
stop shipping the maintainer skills needs the audience decision; this
ownership correction does not settle it.

### 1. Audience criterion

Text for the docs:

> A topic is a **user** topic when an agent or human in a repo that adopts
> Coga needs it to operate Coga correctly: to configure, launch, author,
> recover, or understand a refusal from a shipped command, prompt, skill,
> workflow, or recurring template. Anything a shipped surface tells the
> reader to read is a user topic. Every other topic is a **coga-dev** topic:
> it explains how Coga itself is built, tested, released, or steered, and
> ships to no other repo.

Rules used to apply it:

- **Shipped consumer forces `user`.** A consumer is a shipped prompt
  (`src/coga/resources/*.md`), a user-visible runtime string in `src/`, a
  packaged template (ticket template, `coga.toml`, bundled launcher, skill,
  workflow, recurring ticket), or an auto-attach in code.
- **Code comments and docstrings in `src/` are not shipped consumers.** Their
  reader is a Coga developer. (So `retire_worklist.py`'s docstring citing
  `coga/codebase/gotchas` does **not** force a split; see Mixed topics.)
- **Directory paths are not refs.** `coga/recurring/<name>/` and
  `coga/workflows/` in strings name repo directories, not topics.
- **A user topic may not depend on a coga-dev topic.** It states the
  user-visible fact itself; any remaining pointer to coga-dev material is an
  absolute GitHub URL, never a relative link (see §4).

### 2. Classification table

Audience `user` = ships as a bootstrap fallback. `coga-dev` = local to this
repo. `split` = see §3. **Target** is blank when the ref does not change.
Consumer abbreviations: `prompt` = `src/coga/resources/prompt.md`;
`ticket-tpl` = `src/coga/resources/ticket.md`; `T:` = path under
`src/coga/resources/templates/coga/`; `bs:` = `T:bootstrap/skills/`;
`bw:` = `T:bootstrap/workflows/`; `rec:` = `T:recurring/`; `msg` = runtime
string in that module.

| Ref | Audience | Target | Reason | Shipped consumers |
|---|---|---|---|---|
| `coga/agents` | user | | Configuring `[agents.*]` in any repo | `repl_supervisor.py` msg; `T:coga.toml` |
| `coga/architecture` | user | | Orientation overview | `T:bootstrap/orient`; `bs:bootstrap/ticket`; `commands/init.py` orientation text |
| `coga/blackboard` | user | | Blackboard writer contract | `prompt`; `ticket-tpl`; `dream_validate_drift.py` msg; `bs:bootstrap/ticket` |
| `coga/cli` | user | | Command index | `T:bootstrap/orient`; `commands/init.py` orientation text |
| `coga/codebase` | coga-dev | `coga-dev/codebase` | Coga source tree and contribution rules | — |
| `coga/codebase/gotchas` | coga-dev | `coga-dev/codebase/gotchas` | Hazards when editing Coga's Python | — (`retire_worklist.py` docstring only) |
| `coga/configuration` | user | | `coga.toml` / `coga.local.toml` contract | — |
| `coga/context-layout` | user | | Layout, resolution, `[layout] contexts`; gains §3 packaging cut | — |
| `coga/current-direction` | coga-dev | `coga-dev/current-direction` | Coga's own product decisions; already local-only | `bs:bootstrap/ticket` names it (bug: unresolvable outside this repo; 02 removes) |
| `coga/extension-model` | split | stays; remainder `coga-dev/microkernel` | Repo capability homes and `[aliases]` are user; kernel rule is Coga-dev | — (`launch.py` comment only) |
| `coga/first-task` | user | | First ticket walk-through | — |
| `coga/important` | user | | coga-important destination bar | `bs:coga/autoclose/sweep` |
| `coga/init` | user | | `coga init` behavior | — |
| `coga/install` | user | | Installing the CLI | — (`dependencies.py` docstring only) |
| `coga/internals/activity-capture` | coga-dev | `coga-dev/internals/activity-capture` | Usage-capture implementation | — |
| `coga/internals/agent-spawn` | coga-dev | `coga-dev/internals/agent-spawn` | Spawn path implementation | — |
| `coga/internals/assist-publication` | coga-dev | `coga-dev/internals/assist-publication` | Where assist writes land; implementation | — |
| `coga/internals/claim-recovery` | coga-dev | `coga-dev/internals/claim-recovery` | Megalaunch claim recovery machinery | — |
| `coga/internals/git-refresh` | coga-dev | `coga-dev/internals/git-refresh` | `git.refresh` / staleness implementation | — |
| `coga/internals/git-regressions` | coga-dev | `coga-dev/internals/git-regressions` | Publish provenance CAS; schema-conversion procedure | — |
| `coga/internals/human-assist` | user | `coga/human-assist` **[owner]** | Operators run `coga launch --agent` assists on owner steps | — |
| `coga/internals/launch-claims` | coga-dev | `coga-dev/internals/launch-claims` | Megalaunch claim machinery | — |
| `coga/internals/pr-publication` | user | `coga/pr-publication` **[owner]** | What `coga open-pr` proves; explains its refusals | `ticket-tpl`; `bw:docs/with-review` |
| `coga/internals/pr-publication/existing-pr` | user | `coga/pr-publication/existing-pr` **[owner]** | Refreshing an existing PR | `bs:code/open-pr` |
| `coga/internals/pr-publication/preparation` | user | `coga/pr-publication/preparation` **[owner]** | `## PR` record and review depth | `bs:code/implement`, `bs:code/open-pr`, `bs:code/self-qa`; `bw:code/with-review`, `bw:code/with-self-review`, `bw:code/design-then-implement`, `bw:docs/with-review`; `ticket-tpl` comment |
| `coga/internals/recurring-admission` | coga-dev | `coga-dev/internals/recurring-admission` | Period leases/generations machinery | — |
| `coga/internals/recurring-control` | coga-dev | `coga-dev/internals/recurring-control` | Control-branch relay machinery (user rule must be in `coga/recurring/scheduling`) | — |
| `coga/internals/recurring-temp-worktrees` | coga-dev | `coga-dev/internals/recurring-temp-worktrees` | `--all` temp-worktree machinery | — |
| `coga/internals/spool-merge` | coga-dev | `coga-dev/internals/spool-merge` | Union-merge implementation | — (`logfile.py`, `git.py` comments only) |
| `coga/internals/state-publication` | split | user cut `coga/state-publication`; remainder `coga-dev/internals/state-publication` | Which files auto-publish and the pre-review hazard are user; invariants are Coga-dev | `bs:code/self-qa` ("Pre-review state publication hazard"); `bs:retro/done-ticket` |
| `coga/internals/state-publication/authoring` | user | `coga/state-publication/authoring` **[owner]** | What `coga ticket` finalization publishes | `bs:coga/ticket/finalize` |
| `coga/internals/state-publication/publish` | coga-dev | `coga-dev/internals/state-publication/publish` | `git.publish` primitive | — |
| `coga/internals/state-publication/sweep` | user | `coga/state-publication/sweep` **[owner]** | End-of-command sweep and `coga run publish-state` recovery | — (target of the recovery that `[git] sync failed` prints) |
| `coga/knowledge` | split | stays; remainder `coga-dev/archive-access` | Where facts live is user; `docs/archive/` rule is this repo's | `T:contexts/_template`; `bs:bootstrap/ticket`; `bs:bootstrap/dream/scan/knowledge-scan`; `bs:retro/done-ticket` |
| `coga/launch` | user | | `coga launch` contract | `prompt`; `T:bootstrap/orient` |
| `coga/launch-internals` | coga-dev | `coga-dev/internals` | Index of coga-dev internals (becomes the namespace parent) | — (`launch.py` docstring only) |
| `coga/lifecycle` | user | | Status/step state machines | `T:bootstrap/orient`; `bw:code/design-then-implement` |
| `coga/megalaunch` | user | | `coga megalaunch` contract | — |
| `coga/notifications` | user | | Notification config and routing | — |
| `coga/notifications/failures` | user | | Delivery failures, redaction | — |
| `coga/notifications/producers` | user | | Which events post | `rec:blocker-reminders`; `bs:coga/blockers/remind`; `T:workflows/blocker-reminders/run` |
| `coga/packaging` | split | user cut `coga/edge-code` + into `coga/context-layout`; remainder `coga-dev/packaging` | Edge shims, local forks, overriding bundled resources are user; twins and wheel are Coga-dev | — |
| `coga/patterns` | coga-dev **[owner]** | `coga-dev/patterns` | Rules for designing new Coga features | — |
| `coga/period-task` | user | | Auto-attached to every period task | `recurring.py` auto-attach; `bs:coga/autoclose/sweep` |
| `coga/principles` | coga-dev **[owner]** | `coga-dev/principles` | Foundation for developing Coga and its README | — (`commands/update.py` legacy gitignore entry only) |
| `coga/project-stage` | coga-dev | `coga-dev/project-stage` | Coga's own stage posture; already local-only | `bs:bootstrap/ticket` names it (bug; 02 removes) |
| `coga/prompt-composition` | user | | Prompt layers and repo overrides | — |
| `coga/recurring` | user | | Recurring overview | — |
| `coga/recurring/autofix` | user | | Autofix loop and operator knobs | — |
| `coga/recurring/delegation` | user | | `delegate:` contract for templates | `rec:address-pr-comments` |
| `coga/recurring/scheduling` | user | | Sweep behavior | `rec:autoclose-merged`, `rec:branch-sweep`; `bs:coga/branch-sweep/sweep`, `bs:coga/autoclose/sweep`; `T:workflows/autoclose-merged/sweep` |
| `coga/recurring/scheduling/failures` | user | | Sweep pauses and exit codes | — |
| `coga/recurring/scheduling/inactivity` | user | | `idle_days` gate | — |
| `coga/recurring/scheduling/ledger` | user | | Period keys and ledger | — |
| `coga/recurring/templates` | user | | Authoring recurring templates | `ticket-tpl` |
| `coga/script-tickets` | user | | `ticket.py` phase contract | `T:bootstrap/retire` |
| `coga/secrets` | user | | Ticket secret refs and vault policy | — |
| `coga/session-conduct` | user | | Conduct per launch context | — |
| `coga/skill-management` | user | | `coga skill` and skill provenance | — |
| `coga/sync` | user | | Sync layers overview | — (`commands/megalaunch.py` comment only) |
| `coga/testing` | split | user cut `coga/sandboxes`; remainder `coga-dev/testing` | Agent sandbox limits/grants are user; Coga's suite is Coga-dev | `bs:code/self-qa`, `bw:code/with-review`, `rec:dream` (all "Restricted sandboxes"); `bs:bootstrap/dream/scan/scan-protocol` (interpreter; see §3) |
| `coga/tickets` | user | | Ticket file contract | `config.py` msgs; `ticket-tpl`; `bs:code/review-design` |
| `coga/tickets/authoring` | user | | `coga create` / `coga ticket` | `T:bootstrap/ticket` |
| `coga/tickets/discovery` | user | | Task discovery and refs | `bs:bootstrap/ticket` |
| `coga/tickets/ownership` | user | | `coga owner` | — |
| `coga/uninstall` | user | | `coga uninstall` | — |
| `coga/usage` | user | | `coga usage` | — |
| `coga/workflows` | user | | Workflow definitions and gates | `bs:bootstrap/ticket`; `bs:bootstrap/dream/scan/{scan-protocol,knowledge-scan}`; `bs:coga/autoclose/sweep` |
| `dev/checkout-cleanup` | user | | Disposing finished checkouts | `autoclose.py` msg; `rec:autoclose-merged`; `T:bootstrap/retire`; `bs:coga/autoclose/sweep`; `bs:retro/done-ticket`; all `bw:code/*`, `bw:docs/with-review` |
| `dev/checkout-cleanup/branch-sweep` | user | | Branch sweep archive rules | `T:coga.toml`; `rec:branch-sweep`, `rec:skill-update`; `bs:bootstrap/skill-update`; `bs:coga/branch-sweep/sweep`; `T:workflows/{branch-sweep/sweep,skill-update/run}` |
| `dev/checkout-cleanup/proofs` | user | | Checkout removal proofs | `rec:autoclose-merged`, `rec:branch-sweep`; `T:bootstrap/retire`; `bs:coga/autoclose/sweep` |
| `dev/checkout-cleanup/terminal-owners` | user | | Closed-PR branch deletion | `T:bootstrap/retire`; `bs:coga/branch-sweep/sweep`, `bs:coga/autoclose/sweep` |
| `dev/checkouts` | user | | Where agent work runs; end-of-step return | `open_pr.py`, `step_gate.py` msgs; `bs:code/{implement,open-pr,self-qa,address-pr-comments}`; `bs:coga/autoclose/sweep`; all `bw:code/*`, `bw:docs/with-review` |
| `dev/checkouts/launch-boundary` | user | | Checkout recovery every launch cites | `prompt`; `launch.py` refusal msg; `T:bootstrap/orient` |
| `dev/checkouts/reconciliation` | user | | Reconcile with main | `prompt`; `bs:code/implement` |
| `dev/checkouts/sandbox-clone` | user | | Read-only `.git` fallback | `bs:code/implement` |
| `dev/code` | user | | Code-ticket conventions | — |
| `dev/dev-record` | user | | Compatibility pointer for old attachments | — (candidate for deletion under the clean-break rule; out of scope here) |

Count after the ownership relocation: 78 rows. 54 `user` (6 renamed out of
`coga/internals/`), 19 `coga-dev`, 5 `split`.

`docs/contexts/coga/manifesto/` is an empty directory with no topic: **remove
it** in 02 (Git does not track it; delete locally and confirm nothing
references it).

### 3. Mixed topics: the cuts

| Topic | User part → target | Coga-dev remainder → target |
|---|---|---|
| `coga/testing` | "Restricted sandboxes" and "Codex sandbox grant", minus the `codex review` pytest-collection bullet → new `coga/sandboxes` | Commands, "Which code you are actually testing", test-writing rules, CI posture and receipts, the `codex review` collection bullet → `coga-dev/testing` |
| `coga/packaging` | "Wheel-owned edge implementations", "Explicit local forks", and `edge-code-upgrades.md` → new `coga/edge-code`; the "Three distribution states" bootstrap/init-seeded/override facts and "Bundled launchers may only name fallback contexts" → merge into `coga/context-layout` | "Where bundled resources live", "Canonical copies and twins", "Wheel packaging", the local-only definition → `coga-dev/packaging` |
| `coga/extension-model` | "Choosing a home", "Parameters and trust boundaries", "`coga run <recipe>`", "Aliases" stay in `coga/extension-model` | "The microkernel rule", "Open command placements", "Migrating a built-in to the edge" → `coga-dev/microkernel` |
| `coga/knowledge` | Everything except archive access stays | "Archive access" → `coga-dev/archive-access` (`AGENTS.md` links it) |
| `coga/internals/state-publication` | "The Coga roots" (membership, eligibility) and the pre-review publication hazard → `coga/state-publication` (parent of `authoring` and `sweep`) | "Invariants" and `src/coga/git.py` mechanics → `coga-dev/internals/state-publication` (parent of `publish`) |

Not split, though the ticket suspected it: `coga/codebase/gotchas`. Its only
`src/` citation is a docstring in `retire_worklist.py`, which is Coga-dev
reading.

Shipped consumers 02 must re-point:

| Consumer | Today cites | Change |
|---|---|---|
| `bs:code/self-qa`, `bw:code/with-review`, `rec:dream` | `coga/testing` "Restricted sandboxes" | → `coga/sandboxes` |
| `bs:bootstrap/dream/scan/scan-protocol` | `coga/testing` (interpreter lookup) | Drop the citation; the skill already carries its own block |
| `bs:bootstrap/ticket` | `coga/current-direction`, `coga/project-stage` | Remove from the example list (never resolvable in adopting repos) |
| `bs:code/{implement,open-pr,self-qa}`, `bw:*`, `ticket-tpl` | `coga/internals/pr-publication/**` | → `coga/pr-publication/**` (if renames confirmed) |
| `bs:code/self-qa`, `bs:retro/done-ticket`, `bs:coga/ticket/finalize` | `coga/internals/state-publication{,/authoring}` | → `coga/state-publication{,/authoring}` |

User topics that today link to a coga-dev topic (02 rewrites each so the user
fact stands alone; any remaining pointer becomes a GitHub URL):

| User topic | Links to (coga-dev) |
|---|---|
| `coga/agents` | `internals/agent-spawn` |
| `coga/architecture` | `codebase`, `current-direction`, `launch-internals`, `packaging`, `patterns`, `principles`, `project-stage`, `releasing`, `testing` |
| `coga/blackboard` | `patterns` |
| `coga/cli` | `testing` |
| `coga/context-layout` | `internals/state-publication` |
| `coga/extension-model` | `packaging` (→ `coga/edge-code`) |
| `coga/install` | `codebase`, `testing/clean-install/macos-aws` |
| `coga/internals/human-assist` | `internals/assist-publication` |
| `coga/internals/state-publication/{authoring,sweep}` | `internals/state-publication`; sweep also `testing` |
| `coga/launch` | `internals/{agent-spawn,launch-claims,recurring-admission}` |
| `coga/megalaunch` | `internals/launch-claims` |
| `coga/prompt-composition` | `internals/{activity-capture,agent-spawn}`, `packaging` |
| `coga/recurring` | `internals/{recurring-admission,recurring-control,recurring-temp-worktrees}` |
| `coga/recurring/delegation`, `coga/recurring/scheduling/ledger` | `internals/recurring-admission` |
| `coga/recurring/scheduling` | `internals/{recurring-control,recurring-temp-worktrees}` |
| `coga/recurring/templates`, `coga/script-tickets`, `coga/skill-management` | `packaging` (→ `coga/edge-code` or `coga/context-layout`) |
| `coga/sync` | `internals/{git-refresh,git-regressions,spool-merge,state-publication,state-publication/publish}`, `patterns` |
| `coga/tickets/ownership` | `internals/{claim-recovery,state-publication/publish}` |
| `coga/usage` | `internals/{activity-capture,spool-merge}` |
| `dev/checkouts` | `internals/{recurring-temp-worktrees,state-publication}`, `testing` |
| `dev/checkouts/launch-boundary` | `internals/git-refresh` |
| `dev/code` | `codebase`, `internals/git-regressions` |

(Refs abbreviated: `internals/x` = `coga/internals/x`; others are `coga/x`.)

### 4. How the audience is expressed

**Decision: namespace split.** Coga-dev topics live under a new top-level
namespace **`coga-dev/`** **[owner: name]** in this repo's contexts root.
`coga/*` and `dev/*` hold only user topics.

| Option | For | Against |
|---|---|---|
| **Namespace `coga-dev/*`** (chosen) | The ref itself tells a ticket author the audience; packaging test can declare the whole namespace local-only in one line; a stale ref in an adopting repo fails loud at compose/validate with no extra code | 23 moves + 6 user renames + 6 splits; relative links rewritten |
| Frontmatter `audience:` field | No renames; no link churn | Invisible at the point of attaching (`contexts:` lists refs); adds a third frontmatter key against `coga/knowledge`'s "only name and description"; still needs a test list to stop shipping |
| Test lists only | Least work | Nobody reading a ref can tell; this is the status quo with one more list |

Consequences 02 implements:

- `tests/test_packaging.py`: replace per-topic `LOCAL_ONLY_CONTEXT_REFS`
  reasons with a namespace rule (e.g. `LOCAL_ONLY_CONTEXT_NAMESPACES =
  {"coga-dev/": "<reason>"}`); assert no packaged context under `coga-dev/`;
  `REQUIRED_BOOTSTRAP_CONTEXT_REFS` lists only user refs.
- New rule, enforced by test if cheap: **a shipped surface or user topic never
  cites a `coga-dev/` ref**, except by absolute GitHub URL.
- `coga-dev/internals/SKILL.md` is the old `coga/launch-internals` index,
  trimmed to coga-dev pages; user pages it listed (`pr-publication`,
  `human-assist`, `state-publication`) are linked from `coga/architecture`.
- **[owner]** Rename the six user topics out of `coga/internals/` (to
  `coga/pr-publication/**`, `coga/human-assist`, `coga/state-publication/**`)
  so "internals" means coga-dev only. Tradeoff: adopting repos that attach
  those refs break once. Alternative: keep their refs and leave
  `coga/internals/` as a user-only namespace with a misleading name.

### 5. Compatibility

**Clean break, confirmed.** No aliases, redirects, or stub topics.

- A renamed or de-packaged ref fails loud in an adopting repo (`validate` and
  `create` reject it; compose raises `ComposeError`), which is the intended
  signal.
- No user-blocking reason for anything softer was found: no shipped surface
  will cite a removed ref after 02's re-pointing, and the only user refs that
  change are the six `coga/internals/*` renames above.
- The release note lists every old ref → new ref, and every ref that stops
  shipping (all `coga-dev/` targets).

### Weak spots for the owner

- **`coga/principles` → coga-dev.** It is Coga's identity, but nothing shipped
  cites it and its own description says it is for developing Coga. Keep `user`
  if adopting repos should see it.
- **`coga/patterns` → coga-dev.** Reads as feature-design guidance for Coga;
  someone authoring recurring templates in their own repo might want it.
- **`coga/internals/recurring-control` → coga-dev** assumes
  `coga/recurring/scheduling` already states the control-branch requirement
  operators hit; 02 must verify and add it if not.
- **`coga/extension-model` split** keeps "Choosing a home" as user. If that
  section is really about Coga's own capabilities, the whole topic becomes
  coga-dev and `[aliases]` moves to `coga/configuration`.
- **`coga/secrets` vault policy** is kept user as general guidance; if it is
  really FastJVM's own 1Password setup, cut it to coga-dev.
