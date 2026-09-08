---
slug: redo-documentation-dir-and-merge-it-with-context-b
title: redo documentation dir and merge it with context blocks
status: in_progress
owner: nicktoper
human: nick
agent: claude
assignee: codex
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
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
step: 2 (evaluate-design)
---

## Description

Rebuild Coga's documentation and reusable contexts as one knowledge library
under `docs/`, readable by humans and selectively composable into task prompts.
Today README, 13 documentation files, 22 live contexts, and a package-only CLI
context contain overlapping explanations, conflicting authority claims, and
large prompt payloads. The existing relocation capability is sufficient; this
work changes the knowledge organization and its maintained consumers, not the
context primitive.

This is the proposed migration contract for independent evaluation and the
owner's `review-design` gate. The pitch, cuts, distribution decisions, and work
split below are recommendations, not owner-approved deletions or product
changes. Contexts are the preferred starting evidence for behavior, checked
against source/tests; they are not automatically correct because they are
contexts.

### Proposed pitch and authority

Proposed opening:

> Coga is a company OS for small technical teams that run work with agents.
> Tickets, knowledge, and working state live in your Git repo. Agents and
> scripts do the work; humans direct it, review the result, and turn corrections
> into guidance the next session can use.

Lead with owned, correctable operations. Use the work queue and parallel agent
sessions as the concrete example, preserving the current README's useful
entry point. This keeps the company-OS scope and the pinned internal-OSS /
field-report posture, at the cost of a broader opening than a coding-queue
pitch. The owner may choose the narrower opening at the gate.

README should have the opening, one concrete correction example, a short
install/start path, honest audience/limits, and links into the library. It is
navigation and introduction, not another reference manual. Keep the
two-person/output-of-ten statement explicitly a thesis if retained. The
31-workstream observation has a reproducible, dated receipt; human-minutes per
shipped task remains unmeasured, and the proof experiment remains shelved.
Do not turn those into a productivity result.

Resolve authority by subject rather than by a chain of mutually overriding
files:

- `coga/principles`: enduring design constraints; preserve all seven rules.
- `product/vision`: purpose, intended audience, bet, and operating limitations.
- Focused `coga/*` and `dev/*` pages: shipped contracts, with source symbols and
  tests. A source/contract disagreement is recorded and adjudicated; this
  migration does not silently alter product intent to match either side.
- `coga/current-direction`, `coga/project-stage`, `coga/roadmap`: explicitly
  dated posture and sequencing. Live tasks own current execution state.
- `marketing/positioning`: approved public voice and the pinned field-report
  posture. `marketing/plan` owns campaign decisions, not product behavior.
- `docs/design/` and `docs/archive/`: visibly labeled proposals or history.
  They do not override shipped contracts or automatically enter prompts.

### Acceptance criteria

- [ ] The owner has settled the pitch, final tree/ref map, merge/removal list,
  local-versus-bundled policy, and publication/cutover order at `review-design`.
  The implementation scope reflects the split decision below.
- [ ] Every source in the corpus ledger has a recorded disposition and its
  useful sections have a canonical destination. Preserve behavioral edge
  cases; deletion requires a destination, a reason the content is obsolete,
  or an owner-approved historical disposition.
- [ ] `docs/README.md` supports start, understand, operate, develop, and
  positioning/evidence reading paths. It links every maintained topic directly
  or through a focused topic index. Each fact has one authored home; short
  navigation summaries link to it instead of restating its full contract.
- [ ] Canonical reusable knowledge is at
  `docs/contexts/<ref>/SKILL.md`, retaining `name` and `description` metadata
  and current ref resolution. Humans and agents read the same authored file.
  Skills continue to own executable procedures and workflow process.
- [ ] The owner has set `[layout] contexts = "docs/contexts"` in
  `coga/coga.toml` at the cutover point below. Verify the loaded root, a fresh
  checkout, local precedence, and package fallback. Do not change the packaged
  default, another repo's config, or `coga.local.toml`.
- [ ] All maintained consumers have been classified and updated: attached refs,
  executable reading instructions, navigation, agent guides, bootstrap targets,
  recurring templates, package resources, and fixtures. Old broad attachments
  are replaced by the particular contracts the task needs, not by every child
  page. No maintained consumer silently falls through to an old bundled essay.
- [ ] The shipped context set has enforced canonical/package correspondence
  with completeness checks, not merely byte checks over whichever pairs still
  exist. Local-only topics have explicit reasons. Keep unrelated template twin
  checks and their existing intentional-divergence rules intact.
- [ ] File-size and representative composition checks below pass. Report
  resolved paths, included and excluded content, context-token subtotals, and
  total prompt sizes; do not claim measured task-performance improvements.
- [ ] Validation, relative links/anchors, context refs, relevant package/fixture
  tests, and a built-wheel fallback check have been run. Record exact commands,
  counts, existing failures, and any remaining gaps in the handoff.

### Proposed shape: final documentation tree

Choose `docs/contexts`, not all of `docs`, as the configured root. The whole
configured directory is Coga-owned synchronized state and uninstall removes
it. Keeping indexes, historical evidence, and pending designs outside it limits
that ownership boundary. The owner is explicitly accepting that uninstall also
removes the canonical knowledge subtree; Git remains its recovery source.

Every leaf below the configured root is a directory containing `SKILL.md`.
Brace groups below enumerate proposed refs, not a new filesystem/ref syntax.
The topic ledger below specifies how the present sources populate these leaves.

```text
README.md                              introduction and entry links
AGENTS.md / CLAUDE.md                   contribution rules and topic entry links
docs/
  README.md                            browsable index and reading paths
  context-migration.md                 old path/ref map and cutover record
  evidence/velocity.md                 dated counting method and limitations
  design/cli-extension-audit.md         dated inventory; unresolved classifications
  design/cli-external-surface.md        unimplemented design, with owning tickets
  archive/{relay-migration,origins,market-landscape,launch-programs,
           superseded-decisions}.md    only the history approved for retention
  contexts/
    .gitignore / _template/SKILL.md     existing scaffold convention
    product/vision/SKILL.md
    coga/{principles,architecture,knowledge,cli}/SKILL.md
    coga/{install,init,first-task,uninstall,configuration,context-layout,
          agents,tickets,lifecycle,workflows,blackboard,prompt-composition}/SKILL.md
    coga/{launch,script-tickets,session-conduct,megalaunch,launch-internals}/SKILL.md
    coga/{recurring,period-task,dream}/SKILL.md
    coga/recurring/{templates,scheduling,delegation,autofix}/SKILL.md
    coga/{notifications,important,digest,sync,secrets,usage,patterns}/SKILL.md
    coga/{extension-model,skill-management,codebase,testing,packaging,releasing}/SKILL.md
    coga/internals/{agent-spawn,human-assist,assist-publication,launch-claims,
          claim-recovery,pr-publication,state-publication,git-regressions,
          git-refresh,recurring-admission,recurring-control,
          recurring-temp-worktrees,spool-merge,activity-capture}/SKILL.md
    coga/{current-direction,project-stage,roadmap}/SKILL.md
    dev/{code,checkouts,dev-record,design-history}/SKILL.md
    browser/{api-first,dom-backed}/SKILL.md
    docs/gdrive-mcp/SKILL.md
    marketing/{positioning,strategy,plan,post-declutter,post-amplify,
          post-doc-cache,channels,scorecard,token-receipts}/SKILL.md
```

The many leaves replace a few manuals with selectable topics; the index should
present reading paths, not an undifferentiated list. Keep a leaf smaller or
combine two only when they serve the same reader need and remain within the
size checks. Any such refinement must update the ref map and consumer census
before the corresponding PR is reviewed.

`coga/knowledge` records the permanent authoring rule: facts/contracts go in
these docs, reusable process in skills, a task's temporary state on its
blackboard, and execution history in the CLI-owned log. Narrative may link to
facts without copying their specifications. Markdown links do not cause
recursive prompt loading; required knowledge must be attached explicitly.
No short agent rendition beside a longer human rendition.

### Proposed shape: corpus and disposition ledger

Audit snapshot: checkout `e742d929`, 2026-09-08. Sizes are bytes, not rendered
page lengths. README + docs + live topics + the unique package-only CLI topic
sum to 696,224 bytes before counting scaffold files. The other 11 bundled
contexts are byte-identical copies, not additional knowledge. `S` means a
current bundled twin; `L` means currently local-only. Final refs in the right
column live under `docs/contexts/` unless an explicit `docs/...md` path is given.

| Current document | Bytes | Proposed disposition and canonical home |
| --- | ---: | --- |
| `README.md` | 8,076 | Rewrite around approved pitch; retain entry example/install links, link evidence and topic pages; assess named competitor section for removal. |
| `docs/README.md` | 2,373 | Rewrite as the single browse index; remove its duplicate model summary. |
| `docs/getting-started.md` | 10,184 | Split/merge into `coga/install`, `coga/init`, `coga/first-task`; link lifecycle/composition instead of re-explaining them. |
| `docs/concepts.md` | 14,130 | Merge into architecture, tickets, blackboard, workflows, lifecycle, knowledge and prompt-composition pages; remove the superseded manual. |
| `docs/reference.md` | 29,870 | Merge with bundled `coga/cli`; `coga/cli` becomes a command index whose command-specific contracts live in topic pages below. Remove the duplicate reference. |
| `docs/operations.md` | 12,003 | Split/merge into notifications, digest, sync, recurring, dream, secrets and testing/readiness; remove the superseded manual. |
| `docs/development.md` | 6,549 | Merge into codebase, testing, packaging and `dev/*`; remove the duplicate guide after updating callers. |
| `docs/releasing.md` | 4,655 | Move/review as `coga/releasing`; preserve Trusted Publishing and clean-install harness, date one-time setup assumptions. |
| `docs/vision.md` | 31,163 | Rewrite purpose/bet/limits into `product/vision`; merge normative constraints into principles; retain selected dated founding history in `docs/archive/origins.md`. Cut repeated philosophy only with owner approval. |
| `docs/market-thesis.md` | 59,512 | Split strategic rationale into `marketing/strategy`, approved message into positioning, dated competitor research into `docs/archive/market-landscape.md`; remove duplicate philosophical and product explanations after mapping them. |
| `docs/velocity-report.md` | 4,388 | Retain at `docs/evidence/velocity.md`; correct the experiment's current shelved status without manufacturing a new result. |
| `docs/migrating-to-coga.md` | 4,140 | Retain as dated `docs/archive/relay-migration.md`, away from the default start path. Flag hazardous blanket rollback snippets for removal/replacement, not as instructions for this migration. |
| `docs/cli-extension-audit.md` | 19,329 | Retain/split current inventory and dated rationale at `docs/design/cli-extension-audit.md`; put settled boundary rules only in extension-model. Do not settle the command-cleanup tickets here. |
| `docs/cli-extension-external-surface.md` | 15,737 | Retain at `docs/design/cli-external-surface.md` as a proposal; verify-at-compose and extraction are not shipped. Separate candidate analysis from settled rules. |

Live paths in the following table are `coga/contexts/<ref>/SKILL.md`.
Each `S` row also inventories
`src/coga/resources/templates/coga/bootstrap/contexts/<ref>/SKILL.md`.
The final row accounts for the package-only entry explicitly.

| Current ref | Bytes / distribution | Proposed disposition and final topic homes |
| --- | --- | --- |
| `coga/principles` | 11,090 / S | Retain seven constraints; shorten receipts into links; same ref. |
| `coga/architecture` | 74,246 / S | Split; keep a genuine concise model at the same ref. Detailed section mapping below. |
| `coga/codebase` | 27,997 / S | Split into codebase (source map), testing (local/CI contract and environment pitfalls), packaging (resources/twins/wheel), agents/configuration, `dev/checkouts`; centralize microkernel rules in extension-model. |
| `coga/current-direction` | 21,855 / L | Rewrite as short dated current decisions; move enduring rules to their topics and superseded decisions to a concise archive. Link the live board instead of caching its status. |
| `coga/project-stage` | 3,082 / L | Retain same ref, explicit expiry and compatibility posture; owner verifies the current-stage premise. |
| `coga/roadmap` | 3,490 / L | Retain same ref as sequencing guidance; preserve parked-v2 premise check, link tasks for current status. |
| `coga/extension-model` | 16,636 / S | Condense settled home/alias/recipe rules at same ref; move actual command syntax to CLI topic homes and proposal reasoning to `docs/design/`. Link launch guarantees instead of copying them. |
| `coga/launch-internals` | 29,083 / S | Split into the six launch/publication internals below; retain same ref as a short guarantee index, not a replacement manual. |
| `coga/recurring` | 53,849 / S | Split into recurring overview, templates, scheduling, delegation, autofix, period-task, dream and control/admission/temp-worktree internals. |
| `coga/period-task` | 3,895 / S | Retain small same-ref runtime contract; preserve auto-attachment and parent-state/period-ledger distinction. |
| `coga/sync` | 67,095 / S | Split into sync overview, notifications, digest and Git/state/spool internals; map important/usage/Dream material to its own home. |
| `coga/important` | 3,727 / S | Retain action-needed destination policy at same ref; configuration/cadence owned by notifications. |
| `coga/patterns` | 5,882 / S | Retain spool's reusable API/use case; merge low-level merge/concurrency discussion into `coga/internals/spool-merge`. |
| `coga/secrets` | 5,878 / L | Merge with architecture's capability boundary and operations' ref syntax at same ref; distinguish repo vault policy from the CLI's actual environment behavior. |
| `coga/usage` | 9,302 / L | Split read/ledger contract at same ref from `coga/internals/activity-capture` (schema, provider matching, bounded/redacted content). |
| `dev/code` | 13,097 / S | Split: same-ref convention overview, `dev/checkouts`, `dev/dev-record`, `dev/design-history`; preserve review/retirement and superseded-plan rules. |
| `browser/api-first` | 1,855 / L | Retain policy at same ref. Bundled browser target's missing fallback is a separate distribution defect, recorded below. |
| `browser/dom-backed` | 6,136 / L | Retain runner/DOM constraints at same ref; leave actual execution process in browser skills. |
| `docs/gdrive-mcp` | 2,363 / L | Retain only as an explicitly dated contract for the identified MCP, pending capability re-verification; never present its 2026-06 limitations as universal Google Docs facts. |
| `marketing/positioning` | 8,480 / L | Rewrite around approved voice/ownership/limits and pinned fork A; merge repeated strategy into strategy page. |
| `marketing/plan` | 25,542 / L | Split live phase gates/ownership at same ref from three post briefs, channels, scorecard, and token-receipts; process stays in `marketing/write-post`. |
| `marketing/launch-history` | 2,283 / L | Move to `docs/archive/launch-programs.md`; retire the attachable ref and update the writing skill's historical pointer. Keep no automatic live attachment. |
| Bundled-only `coga/cli` | 77,252 / package only | Bring its useful contracts into the canonical doc tree and topic homes; keep same ref as a short command index, mirrored into the package. No giant fallback left behind. |

Scaffolds are also in scope: live `coga/contexts/.gitignore` (101 bytes) and
`_template/SKILL.md` (1,664 bytes), with their packaged scaffold counterparts
under `templates/coga/contexts/`, move with the live root. Preserve the
`**/_template/` and `**/_template.md` ignores and metadata conventions.
Do not migrate `.coga`, `.agent-skills`, `.claude`, `.codex`, `.venv`, caches,
or local TOML files as documentation.

### Proposed shape: section-level contract map

This is the coverage checklist for splitting the large sources. Each row owns
its detailed facts; overviews and other consumers link to that row's home.
The implementer must reconcile the corresponding sections in all listed
sources before deleting them.

| Topic / present sources | Final owning refs | Rules and edges to preserve |
| --- | --- | --- |
| Primitives and root model: architecture `Primitives`, concepts, README, vision | `coga/architecture`, `coga/knowledge` | Durable files versus transient runtime; contexts versus skills; local/package resolution; no transitive Markdown inclusion. |
| Ticket shape: architecture `Canonical ticket frontmatter` / `Ticket frontmatter extensions`, concepts, CLI create/ticket/show | `coga/tickets`, `coga/blackboard` | File/directory tasks, qualified refs, README exclusion, no file/dir collisions, canonical keys, extension declarations, allowed writers, Description/Context/fence, log separation. |
| Workflow/state: architecture `Workflow gated at activation`, `Two state machines`, `Step completion gates`, CLI mark/bump/block/unblock/delete/retire | `coga/lifecycle`, `coga/workflows`, `dev/checkouts`, `dev/dev-record` | Draft/terminal workflow exceptions, inline instructions remain live despite frozen metadata, peer routing, branch/PR gates, owner gates, blocked resume, no agent rewind, explicit retirement. |
| Composition: architecture `Prompt composition`, concepts composition, launch internals, dev/design history | `coga/prompt-composition`, `coga/session-conduct`, `coga/blackboard` | Exact layer order and three-region extract; SKILL.md frontmatter currently included; missing refs fail; conduct selected once; blocked preamble versus authoring projection; no log layer; large-argv prompt-file delivery. |
| Configuration: architecture relocation/config/identity sections, getting started, codebase, operations secrets | `coga/configuration`, `coga/context-layout`, `coga/agents`, `coga/secrets` | Shared/local allowlists, checkout-root anchor and rejection cases, trackability, prior-root deletions, uninstall ownership, agent overlay/peer asymmetry, env/op refs and inheritance is not confinement. |
| Launch model: architecture launch phases/shared spawn, CLI launch, launch-internals | `coga/launch`, `coga/script-tickets`, `coga/internals/agent-spawn` | Exact ticket.py classifier, script-before-agent and reloads, script has no operands, TTY boundaries, exit/sentinel/supervisor behavior, user assist, source/installed skew, unknown usage. |
| Strict publication: launch-internals all sections; architecture `Status is the signal` and shared-spawn detail | `coga/internals/human-assist`, `coga/internals/assist-publication`, `coga/internals/launch-claims`, `coga/internals/claim-recovery`, `coga/internals/pr-publication`, `coga/internals/state-publication` | Recorded checkout and PR-head proof, leases and compare-and-set, scripts under assist, compensation/uncertain pushes, pending/admitted/released claims, child/audit/release ordering, local barrier versus ownership lock, exact PR gate witness. |
| Queue operation: architecture `Megalaunch dependency drain`, CLI megalaunch/pick | `coga/megalaunch` plus claim internals | Selection/owner/status gates, oldest/numbered order, exact dependency refs, fixed-point drain, no expansion of explicit picks, max-tasks accounting, retained recovery evidence. |
| Recurring definition: recurring directory/example/state/creation sections, architecture recurring primitive, CLI recurring/promote/list | `coga/recurring/templates`, `coga/recurring/scheduling`, `coga/period-task` | Template versus stable task, underscore parking, calendar ledger parsing/tail stop, owner gate, current-period/force semantics, Dream-last ordering, parent cursors/state_keys, direct/body default, promotion and copied attachment rules. |
| Recurring execution: recurring control/temp-worktree sections, launch-internals admission, architecture delegation | `coga/recurring/delegation`, `coga/internals/recurring-admission`, `coga/internals/recurring-control`, `coga/internals/recurring-temp-worktrees` | Frozen delegate/period generation, final reread/pre-spawn lease, multi-repo workspace identity, fresh control, narrow fetch, deterministic-only temporary service, hybrid pause, process-group cancellation, ambiguous-spawn retention and transcript recovery. |
| Maintenance: recurring REM/Dream/autofix sections, architecture Dream known-skill/task-env sections, current-direction cleanup history | `coga/dream`, `coga/recurring/autofix`, `coga/script-tickets`, `dev/checkouts` | Fixed phases/registry, bounded shard completion and known corpus limitation, retro knowledge PR versus direct delete, checkout retirement debt, no nested agent launch, COGA_TASK_* contract, one-shot autofix and exit-code independence. Skills own the procedure. |
| Notification delivery: sync live/digest/optional/config/mention/format/implementation sections, important, operations | `coga/notifications`, `coga/important` | Cadence versus destination, no-digest fallback, optional first-run versus configured failure, preflight_post, failure redaction, mentions, one-attempt reminder watermark, no retry; no delivery promises beyond implementation. |
| Digest/spool: sync digest/concurrency sections, patterns, CLI digest | `coga/digest`, `coga/patterns`, `coga/internals/spool-merge` | Outcome kinds, git high-water state, post-before-drain, anchor watermark, union merges, crash-safe replacement is not a lock, no hidden queue. |
| Git state: sync durable sync/regression/sweep/pull-back sections, codebase checkout warnings, CLI state-command prose | `coga/sync`, `coga/internals/git-regressions`, `coga/internals/git-refresh`, `coga/internals/state-publication` | Control/feature publication, best-effort versus strict paths, union-file handling, stale-generation refusal, dirty state sweep and relocated root, deletion handling, pre-review publication hazard, refresh/stranding rules. |
| Developer surface: codebase/development/dev-code, extension model and audits, CLI run/skill/open-pr | `coga/codebase`, `coga/testing`, `coga/packaging`, `coga/extension-model`, `coga/skill-management`, `dev/*`, `coga/releasing` | Shared-infra/command proof, closed recipes, no executable skill plugins, imported/hand-vendored skills, package-only resolution, portable fixtures, launch-env isolation, wheel test dependencies, exact test receipts and publish-only CI. |
| Usage/evidence: usage, CLI usage, velocity, marketing token protocol | `coga/usage`, `coga/internals/activity-capture`, `docs/evidence/velocity.md`, `marketing/token-receipts` | Read API versus capture schema, Claude deltas/Codex cumulative counts, ambiguity => unknown, bounded secret-redacted content, elapsed time is not active human time, observed workstreams are not simultaneous processes or a multiplier. |

The CLI index maps each installed public command/alias to the owning topic
above. In particular: init/build/install -> setup pages; create/ticket/show ->
tickets; mark/bump/block/unblock -> lifecycle/workflows; status/validate ->
triage/readiness sections in lifecycle/testing; launch/chat -> launch/model;
megalaunch/pick -> megalaunch; delete/retire/open-pr/resolve-conflicts ->
`dev/checkouts` and `dev/dev-record`; run/aliases -> extension-model;
skill/skill-update -> skill-management; recurring/dream/autoclose -> recurring
and dream; slack/digest -> notifications/digest; secret -> secrets; usage ->
usage; uninstall -> uninstall. Copy neither detailed flags nor concurrency
proofs back into the index. Recheck `coga --help`, subcommand help, `aliases.py`
and `runner.RECIPES` during implementation; the surface is moving.

### Proposed shape: old refs, readers, and bundled distribution

Keep existing useful core refs (`coga/architecture`, `coga/cli`, `coga/sync`,
`coga/recurring`, `coga/launch-internals`, `coga/codebase`, `dev/code`) as real
short overviews with current content, mirrored in the package. They are not
compatibility stubs, include directives, or claims that all child contracts
were loaded. Rewrite their descriptions to make their reduced scope clear.
`marketing/launch-history` is retired; no maintained attachment may retain it.
Do not leave an old full essay under either resolver root.

The audit found 147 nonterminal ticket files with a `contexts` list (many
empty). Broad refs occur in 18 codebase, 15 architecture, 14 dev/code, eight
CLI, and three sync selections. Six tickets select marketing/plan. Treat each
selection as prompt payload and inspect the task's actual work before replacing
it; there is no correct global one-to-many substitution. Update only allowed
`contexts` frontmatter and current body instructions, preserving all other
fields and frozen workflow snapshots. Inspect draft/paused/v2 consumers too.
Do not rewrite historical blackboards, log lines, quotes, or obsolete designs
as if they were current; record exceptions in the migration map.

Specific non-ticket consumers:

- `bootstrap/orient/ticket.md`: replace the architecture+principles+full-CLI
  load with the three concise current overviews; remove docs/spec.md and
  task-lock claims. Orientation is the automatic selection here, not a global
  default for all tasks.
- `recurring._create_at_slug` and promotion: preserve the small
  `coga/period-task` automatic attachment at the same ref. Existing periods
  keep their frozen runtime identity and receive only necessary context-list
  edits. Do not regenerate tasks or their workflows for this migration.
- Root AGENTS/CLAUDE and `commands/init.py::AGENT_GUIDE_TEMPLATE`: point at
  real docs/refs, say which target attaches what, and remove the false claim
  that canonical contexts are composed into every ticket. Generic generated
  guidance must continue to describe other repos' default or configured root.
- `resources/prompt.md`, repo `coga/context.md` and its template, onboarding,
  `bootstrap/ticket`, Dream scans, Retro, code skills, marketing/write-post,
  browser/doc workflows and recurring templates: replace old reading paths
  and choose topic refs where they instruct loading knowledge. Preserve
  procedure/conduct and the fixed location of the repo-context layer.
- `tests/test_packaging.py`, `example/`, `scripts/`, `.github/workflows/release.yml`
  comments, and source error/docstring references: update maintained pointers,
  including stale docs/spec.md references. Historical migration constants in
  `commands/update.py` still describe old layouts and must not be renamed.

Keep package runtime resolution exactly where it is:
`src/coga/resources/templates/coga/bootstrap/contexts/<ref>/SKILL.md`.
The docs are the authored source in this repo; these resources are reviewed,
byte-identical distribution copies. No symlink, runtime generator, docs loader,
new metadata key, or package-install dependency on a source checkout.

Proposed final distribution: generic Coga operator/developer topics and their
split internals, including CLI-derived secrets/usage and `dev/*`, ship. Repo
posture (`current-direction`, `project-stage`, `roadmap`), product/marketing
material and the browser/Drive domain contracts stay local unless separately
approved for bundling. Every bundled context should now have a canonical doc,
including formerly package-only `coga/cli`. This adds focused package resources
without changing the unset `[layout]` default in other repos.

Strengthen existing packaging tests as part of adoption:

1. Resolve this repo's canonical contexts location from committed shared TOML
   using `tomllib`, with the existing default while preparatory PRs still use
   it. Do not load machine-local configuration to discover test pairs.
2. For every packaged bootstrap context, require the canonical counterpart to
   exist and compare bytes. For packaged context scaffolds, map to the same
   configured root. Keep the existing mappings for all other template areas.
3. In the reverse direction, classify every canonical topic as shipped or in a
   small explicit local-only exception set with reasons. Assert exceptions
   still exist. This prevents deleting both halves or forgetting to distribute
   a new split contract without review; required topic/consumer checks provide
   the additional floor against both-side deletion.
4. Exercise discovery with a relocated temporary tree and with a missing
   canonical counterpart so missing files cannot silently shrink coverage.
   Retain the generated-artifact exclusions and intentional-divergence checks;
   do not solve relocation by weakening the existing count floor.
5. Check maintained shipped attachments against bundled resources alone, and
   compose from a built wheel with no local overrides. Track the known
   browser/api-first gap separately until its focused repair lands.

Use relative links between canonical topics so the mirrored subtree has the
same link topology. A bundled relative link must resolve within bundled
resources. For source code, this repo's archives, or local-only posture, use a
repository source pointer/link rather than an invalid path outside the wheel.
No link is an implicit dependency loader.

### Proposed shape: publication and owner config cutover

Automatic state sync publishes dirty contexts from a feature checkout to the
control branch. Merely opening a PR does not create a human merge gate for
those uncommitted files. The relocation carries that behavior into
`docs/contexts`; it does not fix it. Preserve the human review boundary through
the sequence, not through an invented sync switch.

1. Land the approved preparatory topic PRs below. Each must remain usable with
   the then-current root and installed package. Author split files at the
   current contexts root, mirror shipped ones, update refs atomically, and
   replace superseded docs sections with links to their canonical topic.
   Commit all context/skill/template edits on the feature branch before any
   state-changing Coga command. Run workflow transitions from the up-to-date
   control checkout as the workflow requires. Never rely on a feature branch
   name to protect dirty Coga state.
2. Prepare the complete final move, mapping-test changes, navigation changes,
   and deletions in an isolated feature checkout. Keep live control at the old
   setting during preparation. The destination must be real and trackable;
   no symlink or empty/ignored-root workaround. The move follows the topic
   revisions accepted in the preparatory PRs, not the audit's older bytes.
3. Once that concrete migration is ready, ask the owner to append the following
   table to **that checkout's** `coga/coga.toml`, preserving every other setting
   (or add the key to `[layout]` if one has since appeared):

   ```toml
   [layout]
   contexts = "docs/contexts"
   ```

   The path is relative to the Git checkout root. Do not set it in local TOML
   or the packaged seed. The agent does not apply this edit under the launch
   instructions' configuration ownership boundary.
4. Verify the applied configuration with `load_config(...).contexts_root`,
   `coga validate --json`, exact resolved paths and read-only composition.
   Commit the **entire** move and owner edit together with ordinary Git before
   running any mutating Coga command in that checkout. Review/merge the whole
   diff through the owner PR gate; do not publish a config-only transition to
   control or use Coga's catch-all sweep to publish the migration.
5. At merge/cutover, the owner pauses schedulers and finishes or pauses old
   sessions/checkouts that can publish Coga state. Every operating checkout
   takes the merged config+docs together and uses the matching reviewed package
   (editable source or released wheel). Verify actual installed code/resources,
   not only a passing source-tree import. Resume operation only after the
   resolved paths and representative prompts agree. Do not run init/uninstall
   on the live repo as a test.
6. Record the cutover revision, commands, package version/source, ref map,
   approved cuts, and remaining exceptions in `docs/context-migration.md`.
   If cutover fails, keep writers paused and have the owner restore/revert the
   matching config+content revision together; never restore only the old config
   against already-removed files. Do not delete unmatched working files.

`coga launch ... --prompt-report` is not safe to assume read-only in this
revision: its handler refreshes the generated skill view, then returns, but
`cli._should_sweep_coga_state` still classifies the command as sweeping. Use
`compose.compose_prompt_report` for in-place investigation. Exercise the actual
CLI report only in a disposable checkout with no production remote and no
live launch metadata, until the focused follow-up fixes the diagnostic.

### Proposed shape: reviewable work split

The audit is larger than one honest implementation PR. Recommend the following
sequence, with this ticket retained as the integration/cutover work after the
owner scopes/creates its prerequisites. Do not silently implement the whole
corpus in the next step or create/activate these follow-ups during design.

| Proposed prerequisite | Work and review boundary |
| --- | --- |
| 1. Pitch, knowledge policy, marketing and historical cuts | Owner-approved pitch, principles/knowledge rule, marketing splits and historical disposition; update README/evidence/navigation for pages actually present. |
| 2. Model, configuration and contributor documentation | Tickets/workflows/blackboard/composition/setup/config; codebase/testing/packaging/dev contracts; CLI topic index; keep unrelated command-cleanup proposals separate. |
| 3. Launch and recurring documentation | Launch/publication internals, scheduling/delegation/autofix/Dream, their bundled counterparts and targeted consumers. |
| 4. Notifications, Git state, secrets and usage documentation | Delivery/digest/spool, state-publication/regression/refresh, environment/capture details and targeted consumers. |
| This ticket after prerequisites: relocate and adopt | Byte-preserving final relocation of reviewed topics, pairing completeness, remaining path consumers, owner config edit, final coverage/prompt/wheel checks and cutover record. |

Each prerequisite removes only explanations it has replaced and leaves working
links/refs at its merge boundary. Later PRs cannot rely on unpublished pages.
If a prerequisite still exceeds a reviewable topic change, split it before
implementation. The owner must reconcile this decomposition with the existing
frozen workflow at the design gate; no workflow/status fields are edited by the
design agent.

### Verification plan and selective-reading budgets

Aim for 60-160 lines and 500-1,500 estimated tokens per ordinary topic. Review
any canonical leaf over 200 lines, 10,000 UTF-8 bytes, or 2,500 estimated tokens;
split it or record a specific owner-approved exception. Check all three:
market-thesis demonstrates why line count alone is insufficient. Overviews and
the CLI index target at most 1,000 tokens; principles may use 1,500 to preserve
all seven constraints. Archived originals are not normal launch material and
must be clearly indexed as such; archive size does not justify a second live
manual.

Use Coga's existing estimate (ceil(characters / 4)), including rendered headers
and frontmatter, rather than claiming tokenizer precision. The following
baselines were composed from this checkout with the real task text and source
composer, without running a ticket or script. For the after comparison, freeze
that task text/step/conduct in temporary fixtures and change only attached refs;
then also inspect current live prompts separately so unrelated blackboard
changes cannot be credited to documentation work.

| Representative target | Before contexts / total tokens | Proposed selection and acceptance |
| --- | ---: | --- |
| `bootstrap/orient` | 40,475 / 42,604 | principles + architecture + CLI index; <=3,500 context tokens and <=6,000 total for the frozen fixture. Include correction loop, lifecycle outline, and topic/command navigation; exclude proofs, all command flags, recurring internals and campaign material. |
| `cloning-a-coga-repo-has-no-setup-path` | 26,191 / 32,453 | install + init + agents + codebase as needed; <=5,000 context tokens. Include machine-local user/CLI setup and fresh-versus-existing repo behavior, no scheduler/claim proofs. |
| `service-recurring-from-a-temp-control-worktree-ins` | 37,718 / 46,200 | recurring overview + recurring-control + recurring-temp-worktrees + recurring-admission + script-tickets; <=8,000 context tokens. Include workspace identity, fresh control, hybrid refusal, cancellation and recovery, not the whole CLI. |
| `stop-syncing-task-state-onto-the-feature-branch` | 26,424 / 29,690 | sync + state-publication + git-regressions + dev/checkouts; <=6,000 context tokens. Include control/feature paths, dirty sweep and union/CAS rules; exclude Slack setup and release instructions. |
| `launch-activates-before-preflight` | 7,275 / 17,232 | launch + relevant human-assist/assist-publication/claim pages after rereading scope; <=5,000 context tokens. Preserve no-mutation preflight and exact publication obligations; no blanket launch-internals inclusion. |
| `marketing/post-doc-as-cache` | 8,474 / 13,772 | positioning + post-doc-cache + token-receipts + only required plan gates; <=4,000 context tokens. Preserve evidence and claim restrictions; exclude other post briefs and historical competitor matrix. |
| `recurring/dream` | 976 / 8,525 | Keep automatic period-task alone unless its body needs an additional specific fact; <=1,100 context tokens. Parent state versus per-run scratch/ledger must remain present. Do not execute Dream for this check. |

For every sample, record each layer's path/ref/bytes/token estimate, inspect the
actual composed text, and assert intended omissions as well as presence.
Ordinary samples must resolve selected local topics to `docs/contexts`, not
merely pass validation via fallback. A separate no-overrides wheel fixture must
resolve the approved shipped refs from package resources and match the
canonical content. Two small frozen fixtures selecting disjoint topics (for
example notifications versus context-layout) should prove one selection never
implicitly loads the other. Total prompt size may remain dominated by a task's
own spec or blackboard; report that rather than expanding this ticket into
unrelated ticket cleanup. Flag total prompts near the launcher's large-argv
fallback threshold independently of the context budgets.

Implementation verification commands/checks:

- `coga validate --json` and `coga validate --task <changed-task> --json`;
  compare the existing error baseline recorded below. Never use auto-fixes for
  unrelated drafts. Recheck recurring-template refs before task instantiation.
- Read-only `compose_prompt_report` / `compose_prompt` inspection as above;
  `coga launch <target> --prompt-report` only in the isolated diagnostic fixture.
  It emits a layer report, not prompt text, and rejects a ticket.py-backed
  target rather than simulating its post-script agent prompt.
- `python -m pytest tests/test_packaging.py tests/test_layout_contexts.py
  tests/test_compose.py tests/test_init.py tests/test_uninstall.py` in the
  declared test-extra environment after relevant fixture/string/test edits.
  Add focused coverage to these tests for actual migration guarantees rather
  than snapshotting prose. Broaden to config/Git/authoring tests only if their
  behavior changes (which requires a separate scope decision).
- Run the wheel-content check on a pristine checkout as well as the developer
  tree, and exercise bundled fallback without the live overrides. Reuse
  `test_wheel_includes_bootstrap_batteries`; do not mistake source-tree files
  for proof that the installed wheel contains the new split topics.
- Walk relative Markdown links **and anchors**, YAML context refs, bare old-ref
  instructions, and shipped relative-link/attachment closure across docs,
  agents, resources, skills/workflows/recurring and fixtures. Check historical
  exceptions against `docs/context-migration.md`; no blind global rename.
- `git diff --check`; file-size report over canonical leaves; final corpus
  coverage comparison and re-diff of every live/package twin after rebasing.
  Prose-only preparatory changes need their link/ref and pairing checks, not a
  full Python suite by default.

### Out of scope

No loader/ref syntax changes, automatic link traversal, new context primitive,
global default-root change, runtime docs generator, hosted wiki, new CLI surface,
or rewriting deterministic code as agent process. Do not move skills/tasks,
relocate `coga/context.md`, alter session conduct, rename workflow to playbook,
change sync semantics, add CI, run marketing experiments, refresh all competitor
research, close overlapping tickets, or implement the command-cleanup designs.
Product defects discovered in the audit receive focused follow-up proposals.
No branch, code changes, manual commits, PR, config edits, or actual rewrite in this
**design** step.

## Context

### Source and test anchors

Use symbols and paths, not the line numbers of this audit:

- `config.Config.contexts_root`, `_parse_layout`,
  `resolve_layout_contexts_path`, `_require_trackable_context_entry`;
  `paths.context_path`, `resolve_context_path`, `bootstrap_context_path`.
  Current layout is unset. Config rejects invalid/untrackable roots; per-ref
  local-first bundled fallback remains intentional.
- `compose.compose_prompt_report`, `compose_prompt`, `_extract_section`,
  `PromptLayer`, `PromptComposition`; `tasks.resolve_target`, `read_ticket`;
  `validate.validate_task`. Composition reads only explicitly attached
  contexts, currently including their frontmatter.
- `authoring.authoring_sync_roots`, `snapshot_authoring_files`, `support_paths`;
  `git._coga_state_pathspecs`, `_removed_paths_from_previous_contexts_root`,
  `sync_coga_state`, `refresh_coga_state_from_control`; `cli.main`,
  `_should_sweep_coga_state`. Relocation affects reads and publication.
- `commands/init.py::AGENT_GUIDE_TEMPLATE`, `_relocate_fresh_contexts`;
  `commands/uninstall.py::_configured_contexts_root` and removal plan;
  `tests/test_init.py::test_init_materializes_configured_contexts_at_checkout_root`;
  `tests/test_layout_contexts.py::test_relocated_contexts_resolve_compose_validate_and_sync`.
- `recurring._create_at_slug`, `promote_task`, `read_serviced_ledger`;
  `recurring_runner.py`, `recurring_autofix.py`, `task_env.TASK_ENV_KEYS`;
  tests for recurring templates/ledger/admission and script launch.
- `commands/launch.py::_launch`, `spawn_agent_session`, `_format_prompt_report`;
  `megalaunch.py`, `repl_supervisor.py`, `step_gate.py`, `open_pr.py`;
  `tests/test_launch.py`, `test_launch_script.py`, `test_megalaunch.py`.
- `notification.preflight_post`, `post`, `notify`; `notification/slack.py`;
  `commands/digest.py::run_digest`, `spool.append_record` / `drain`,
  `usage.py`; notification/recurring/usage tests. These own behavior, not the
  prose's broad promises about delivery, locking, or credential isolation.
- `tests/test_packaging.py::_live_counterparts`,
  `_discover_live_packaged_twins`, `IDENTICAL_LIVE_PACKAGED_PAIRS`,
  `INTENTIONALLY_DIVERGENT_TWINS`, `EXPECTED_BOOTSTRAP_RESOURCES`;
  `pyproject.toml` package-resource declarations. Current existence-based pair
  discovery can lose relocated twins; the floor alone is insufficient.
- `.github/workflows/release.yml`, `scripts/verify-clean-install.sh`:
  release/manual builds, metadata check and OIDC publish; no pytest or PR/push
  test job. The codebase context currently omits this posture.

### Contradictions, gaps, and claim classification

| Finding | Evidence / disposition |
| --- | --- |
| Docs and contexts claim layered authority while repeating contracts. | concepts defers to architecture/principles; vision to principles; positioning/plan to vision/market-thesis. Apply the subject-based authority proposal. |
| Pitch/strategy chronology conflicts. | Market-thesis leaves fork A/B open and uses a dated feature-gap narrative; positioning and 2026-09-04 plan pin fork A. Preserve the owner decision; label earlier argument historical, not a live instruction. |
| Orientation overstates attachment and locking. | `AGENT_GUIDE_TEMPLATE` says canonical refs enter every ticket; composer iterates `ticket.contexts`. Bundled orient still mentions a task lock and nonexistent docs/spec.md. Repair documentation/guidance strings, without adding an auto-attach mechanism or lock. |
| Setup prose can imply activation precedes all preflight. | Getting-started orders activation before composition; launch/architecture describe deferred durable activation for agent preflight. Rewrite the explanation to match the actual phase boundary and link the detailed contract. |
| Reference's authority description and content disagree with the current CLI. | Docs index calls it generated; reference says version prints vendored CLI versions; current CLI prints `coga 0.3.1`. Bundled CLI duplicates long concurrency/recurring prose. Treat installed help as syntax evidence and consolidate semantics by topic. |
| Release CI exists but does not run tests. | Source workflow inspected: release/manual build + twine metadata check + publish. Record in testing/releasing; adding CI is separate work. |
| Diagnostic publication defect. | `_should_sweep_coga_state(['coga','launch','sample','--prompt-report'])` evaluated true; report handler returns through the sweeping CLI wrapper. Propose a separate fix making report mode read-only, with a dirty-state regression test. Use composer API for this design. |
| Missing bundled context masked by local knowledge. | `bootstrap/browser-automation/ticket.md` attaches `browser/api-first`, absent from package contexts. Propose a focused battery/clean-install repair; do not expand this ticket into browser feature work or hide this baseline in green closure claims. |
| Historical operational proposals appear beside live contracts. | verify-at-compose is explicitly unbuilt; workflow-to-playbook and command-cleanup work are in v2. Current-direction's historical assignee/watchers/scheduler decisions must not override shipped source. Keep proposal ownership and status visible. |
| Some factual generalizations need qualification. | patterns says no external cron while cadence is only serviced by an operator invocation/scheduler; secrets declaration is not process isolation; usage is local/git-backed and synced, not literally never off-machine. Preserve the precise contract rather than the absolute slogan. |
| External capability/market claims are dated evidence. | Drive context records a particular 2026-06 MCP, and market-thesis competitor matrices were checked mid-2026. This audit does not reverify external services; date/scope or archive these claims, and require fresh evidence before reusing them in current public claims. |
| Performance claims have different evidentiary status. | Recomputed `(31, (2026, 27))` with velocity's July-5 cutoff. It counts weekly distinct workstreams, not concurrent processes. Founder hours are owner-reported; two-to-ten and two-minute examples are thesis/illustration, not controlled measurements. Preserve labels. |

### Related work to reconcile at the gate

- `move-cogacontext-to-roodoc-so-its-easier-for-human`: **done**; delivered the
  knob (PR #704). Its design text describes older source; use the current
  implementation and tests, not the old path-construction census.
- `the-human-doc-vs-agent-context-boundary-is-decided`: **draft**; its remaining
  boundary rule is covered by `coga/knowledge` here. Owner should mark it
  superseded/covered only after the approved rule lands.
- `v2/docs-and-contt-block-should-be-merged`: **draft**, empty description;
  overlapping title, no additional implementation requirements established.
- `v2/split-context-to-doc-user-accessible-and-editable`: **draft**, stale Relay
  paths and evaluator notes; specifically about the fixed repo-context layer.
  Leave that different feature deferred; this ticket does not satisfy it by
  relocating reusable contexts.
- `no-context-records-the-ci-posture-publish-only-rel`: **draft**; fold its
  documentation requirement into the model/contributor prerequisite, or let
  it land first and consume the corrected text. Do not add a parallel CI change.
- Other concrete overlap inputs: `recurring-context-never-mentions-the-packaged-twin`,
  `live-and-packaged-twin-pairs-are-edited-together-b`,
  `sync-context-omits-preflight-post-from-the-notific`,
  `v2/document-contexts-as-prompt-payload-not-tags-princ`, and the command-cleanup
  directory. Recheck current scope/status before implementation; do not close
  them during this design step.

<!-- coga:blackboard -->

## Design handoff (2026-09-08)

- Spec, corpus ledger, section/ref map, pitch/cut recommendations, distribution
  contract, owner edit/cutover plan, and prompt budgets are now in Description
  and Context so the evaluator/implementer actually receives them.
- Recommendation is five reviewed changes: four topic prerequisites, then
  relocation/adoption on this ticket. The corpus is too large for one honest
  rewrite PR. Owner must scope the prerequisites and this ticket at the gate.
- No owner pitch answer was received during the audit; owned company operations
  is the provisional opening. No pitch, cut, or split is treated as approved.
- Initial worktree already had a `coga/log.md` modification. Only this ticket
  was edited by design; leave the CLI-owned log alone. No branch/code/config
  edit, manual commit, PR, subagent, actual task launch, or documentation rewrite.

## Validation evidence

- `coga --version`: `coga 0.3.1`; `coga --help`: inspected actual commands and
  alias descriptions. The CLI environment imports this checkout's source.
- `coga validate --json`: exit 1, 175 OK, 40 warnings, four existing
  `unsynthesized-draft-blackboard` errors: `v2/autotrigger-ticket-type`,
  `v2/measure-relay-prompt-scope-and-agent-precision`,
  `v2/split-context-to-doc-user-accessible-and-editable`, and
  `v2/use-worktree-when-starting-a-dev-task`. Do not fix them under this ticket.
- Read-only Python using the CLI interpreter
  `/home/n/.local/share/uv/tools/coga/bin/python3`, `load_config`,
  `tasks.resolve_target` / `read_ticket`, and `compose_prompt_report` measured
  the seven samples in the spec; no launch wrapper or ticket.py was executed.
  Detailed temporary receipt: `/tmp/coga-docs-prompt-baseline.json`; all key
  numbers and reproduction inputs are in the spec and do not depend on it.
- Inventory/byte comparison: all 11 existing live/bundled topic pairs match;
  `coga/cli` is the twelfth package topic and has no live counterpart.
- Simple read-only Markdown file-target scan: zero missing relative file links
  across README/docs/live contexts. This excludes anchors, code-span references,
  package topology, and external URLs; the stale bare docs/spec.md pointers are
  separately recorded above. The implementation needs the broader link check.
- Recomputed the velocity report's bounded ledger count: `(31, (2026, 27))`.
  Inspected config/compose/sync/init/uninstall/recurring/package code and
  relevant tests, plus the sole release workflow. No Python suite was run for
  this ticket-only design edit.
- `coga validate --task redo-documentation-dir-and-merge-it-with-context-b
  --json`: exit 0, one OK, no issues. `git diff --check`: passed.
- Read-only composition of this design ticket confirms one blackboard fence,
  exactly Description and Context as top-level body sections, and inclusion
  of acceptance criteria, proposed shape, cutover, scope, audit findings and
  open questions. Before this final receipt, the design prompt was 65,501 bytes
  / 16,365 estimated tokens; its size is the explicit audit/spec payload, with
  no attached contexts. Frontmatter bytes were preserved by the body edit.

## Open Questions

For independent evaluation and the following owner `review-design` gate:

1. Approve the owned-company-operations pitch with queue as the example, or
   lead with the narrower work-queue pitch. Confirm the field-report posture
   and which founding/philosophical material remains in the default reading path.
2. Approve `docs/contexts/<ref>/SKILL.md`, the subject/ref map, and the explicit
   sync/uninstall ownership boundary. Accept that links to removed docs paths
   must be updated; no permanent duplicate manuals or implicit ref expansion.
3. Approve the reasoned cuts and historical disposition: dated competitor
   matrix off the default path, concise founding/decision history, Relay
   migration archived, shelved launch apparatus retained as history. Nothing
   here preauthorizes deletion of useful content without accounting for it.
4. Approve the shipped/local policy and pairing completeness checks; decide
   sequencing for the separate missing browser battery and report-mode sync
   defects. Neither defect is repaired by this design.
5. Approve/create the four prerequisite scopes and retain this ticket for final
   adoption, or supply a smaller implementation scope. Confirm the owner will
   make the exact shared-config edit in the prepared migration checkout and
   coordinate the final publication/cutover sequence.
