---
title: Split contexts for Coga users from contexts for developing Coga
status: draft
owner: nicktoper
workflow: code/with-review
---

## Description

Coga's context library mixes two audiences without saying so. Some topics are
for **operating Coga in any adopting repo** (`coga/launch`, `coga/tickets`,
`coga/first-task`, ...). Others are for **developing Coga itself**
(`coga/codebase`, `coga/testing`, `coga/packaging`, `coga/releasing`, most of
`coga/internals/*`, ...). Today nearly all of them are packaged under
`src/coga/resources/templates/coga/bootstrap/contexts/` and ship to every
adopting repo. Only `coga/current-direction` and `coga/project-stage` are
local-only. Ticket authors, both people and the `bootstrap/ticket` interviewer,
can't tell which set to attach. Adopting repos also get Coga-dev material
they never need.

Make the split explicit and real:

1. Define the two audiences and classify every topic under `docs/contexts/`
   into exactly one.
2. Make the location or ref show the audience. A namespace split is the
   leading candidate, e.g. keep `coga/*` for users and move Coga-dev topics
   under a distinct namespace. The implement step weighs it against
   alternatives (path/namespace, a frontmatter field, test lists) and records
   how the audience is expressed before moving any files.
3. Change what ships: Coga-dev topics stop being packaged bootstrap contexts
   and become local-only, with `tests/test_packaging.py`
   (`REQUIRED_BOOTSTRAP_CONTEXT_REFS`, `LOCAL_ONLY_CONTEXT_REFS`) updated to
   match. `LOCAL_ONLY_CONTEXT_REFS` currently demands a per-topic reason, so
   expect to change how that test expresses a whole local-only audience.
4. Update the docs that guide context choice: `docs/README.md`,
   `coga/knowledge`, `coga/packaging`, `coga/context-layout`, and the
   `bootstrap/ticket` skill's context-selection guidance. A ticket author
   should be able to tell which set to draw from.

Done when:

- every topic under `docs/contexts/` carries exactly one audience, recorded
  in the way the implement step chose;
- the packaged bootstrap set contains only user-facing topics, and the
  packaging test enforces it;
- every ref and link to a moved topic is updated across repo docs, skills,
  workflows, source strings, tests and fixtures, including GitHub-URL links;
- the compatibility decision is recorded and applied;
- `docs/README.md` and `bootstrap/ticket`'s context-selection contract each
  name both sets and the criterion, so a ticket author can tell which set to
  attach for a repo that uses Coga vs. Coga itself;
- `python -m pytest` and `coga validate --json` pass.

## Context

### Classification is not "path prefix decides"

Shipped behavior points at some topics a naive reading would file as Coga-dev,
so those must stay packaged:

- The base prompt tells every launched agent in every repo to read
  `dev/checkouts/launch-boundary` and `dev/checkouts/reconciliation` "from the
  configured contexts root or the bundled package".
- Core source strings cite `dev/checkouts`, `dev/checkout-cleanup` (and its
  `terminal-owners` / `branch-sweep` children), and `coga/codebase/gotchas`,
  e.g. in `launch`, `open_pr`, `autoclose`, `branchsweep`,
  `branchcleanup`, `retire_worklist`, `config`, `step_gate`,
  `repl_supervisor`, `recurring_runner`. `coga/codebase/gotchas` is cited
  by `retire_worklist`, so de-packaging `coga/codebase` likely means
  splitting gotchas out (or keeping it shipped).
- Bundled workflows and skills are read in adopting repos, e.g.
  `code/self-qa` citing `coga/testing` "Restricted sandboxes", and
  `code/implement` / `code/open-pr` / `code/self-qa` citing
  `coga/internals/pr-publication/preparation`.

So the criterion is "does an agent or human in an adopting repo need this to
operate Coga correctly?", not the namespace. Some topics may need splitting:
a user-facing part that ships and a Coga-dev remainder. Grep for every ref
(`rg "<ref>"` across `src/`, `docs/contexts/`, `coga/`, `tests/`,
`README.md`, `AGENTS.md`, `CLAUDE.md`) before moving one. Grep URL and path
forms too: about 11 packaged templates link topics as
`https://github.com/FastJVM/coga/blob/main/docs/contexts/<ref>/SKILL.md`, and
moving a topic breaks those links in already-installed copies.

`docs/contexts/coga/manifesto/` is an empty directory with no SKILL.md;
remove it or classify it.

### Compatibility

Adopting repos and existing tickets may already attach refs that move or stop
shipping, and composition fails loud on an unknown ref. The design should say
what happens to them. `coga/project-stage` ("Compatibility is
migration-only", "Code review") already rules out open-ended aliases and
deprecation shims, so the expected answer is a clean break: refs fail loud,
and release notes name the renames. A transitional alias needs a concrete
user-blocking reason.

### Topics this ticket edits (cited, not attached)

These are read and edited, so they are left off `contexts:`:

- `coga/packaging` (`docs/contexts/coga/packaging/SKILL.md`): twin mapping,
  "Local-only" definition, and the bootstrap/init-seeded/local-only categories.
- `coga/knowledge` (`docs/contexts/coga/knowledge/SKILL.md`): "Attach or
  cite" and where a fact lives.
- `coga/context-layout` (`docs/contexts/coga/context-layout/SKILL.md`):
  directory layout. This repo sets `[layout] contexts = "docs/contexts"` in
  `coga/coga.toml`; `config.contexts_root` resolves it.
- `docs/README.md`: the reading index. Its Start / Understand / Operate /
  Internals grouping is a rough precursor of the split.
- `bootstrap/ticket` skill (packaged under
  `src/coga/resources/templates/coga/bootstrap/skills/`, plus any live twin):
  "Context and skill selection contract".
- `AGENTS.md`: the canonical-topics list and twin rules.

Packaged twins must stay byte-identical with their canonical copies, which
`tests/test_packaging.py` enforces. Moving a topic means moving both copies, or
deleting the packaged one and registering it as local-only.

### Workflow note

`code/with-review` has no separate design step. The implement step should
settle the audience criterion, the namespace decision, and the compatibility
answer first, and record them on the blackboard before mass-moving files. If
the classification turns up genuinely ambiguous topics, ask the owner.

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/internals/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

**Clarity for a cold agent:** Mostly good. Problem, four deliverables, and the audience criterion ("does an agent or human in an adopting repo need this?") are stated plainly; the "not path-prefix" section is excellent and preempts the obvious wrong move. One contradiction: Description item 2 says "The design step should weigh it against alternatives," but the Workflow note correctly says there is no design step. Reword item 2 to "the implement step, before moving files."

**Done clarity:** Good but partially subjective. "Every topic carries exactly one audience," "packaging test enforces it," "refs updated," "pytest + validate pass" are checkable. "A ticket author can tell from the docs which set to attach" is a judgment call — tighten to something concrete, e.g. "docs/README.md and bootstrap/ticket's selection contract each name both sets and the criterion." Also unclear *how* "carries exactly one audience" is recorded (path/namespace? a frontmatter field? test lists?) — say so, or state the implement step decides it. The Compatibility answer (alias vs. release-note vs. accepted break) isn't in "done"; add "compatibility decision recorded and applied."

**Workflow fit:** `code/with-review` is acceptable only if implement genuinely stops to ask the owner after classifying. Currently "ask the owner" is conditional on ambiguity; the namespace and compatibility calls are product decisions — consider making an owner check-in on the classification table mandatory before mass moves. Alternative: a design-first workflow, or split (below).

**Contexts:** Citing-not-attaching the edited topics is correct. Consider attaching `coga/packaging` — implement depends on its twin rules/category definitions throughout, and the AGENTS.md summary is partial. `coga/project-stage` is cited for breakage tolerance; its "Compatibility is migration-only" section (line 24) and push-back on compat paths (line 58) already largely answer the alias question — the ticket could just state that. Missing: packaged skills link topics by GitHub URL (e.g. `https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/internals/pr-publication/preparation/SKILL.md` in `code/implement`, `code/open-pr`, `code/self-qa`; 11 template files contain `docs/contexts/` URLs). Moving canonical topics breaks those in installed copies — the grep list should include URL forms.

**Scope:** Large — 85 canonical topics, ~87 required bootstrap refs, twin moves across two trees. Recommend split: **(A)** audience criterion + classification table + namespace/compat decision + guidance docs (README, knowledge, context-layout, bootstrap/ticket), owner-reviewed; **(B)** moves, de-packaging, and `LOCAL_ONLY_CONTEXT_REFS`/`REQUIRED_BOOTSTRAP_CONTEXT_REFS` test restructuring; optionally **(C)** splitting mixed topics. B depends on A.

**Spot-checks (all held):**
- `REQUIRED_BOOTSTRAP_CONTEXT_REFS` (line 363) and `LOCAL_ONLY_CONTEXT_REFS` (line 455, only current-direction/project-stage, per-topic reasons) exist as described.
- `coga/coga.toml:181` sets `[layout] contexts = "docs/contexts"`.
- `src/coga/resources/prompt.md:15,34` cite `dev/checkouts/launch-boundary` / `reconciliation` "from the configured contexts root or bundled".
- Python modules citing `dev/checkouts`/`dev/checkout-cleanup`/`coga/codebase/gotchas`: launch, open_pr, autoclose, branchsweep, branchcleanup, retire_worklist — plus config, step_gate, repl_supervisor, recurring_runner (the "e.g." list undercounts).
- Bundled skills cite `coga/testing` "Restricted sandboxes" (`code/self-qa`) and `coga/internals/pr-publication/preparation`; the workflow file doesn't cite them directly.
- `bootstrap/ticket` "Context and skill selection contract" exists (line 145); no live twin under `coga/skills/`.
- `docs/contexts/coga/manifesto/` is an empty directory (no SKILL.md) — worth classifying or deleting.
- `coga/codebase` and `coga/codebase/gotchas` are both currently required-bootstrap; de-packaging `codebase` conflicts with the `retire_worklist.py` citation unless gotchas is split out.

**Prompt size** (composed read-only from an in-memory copy with frozen workflow, no file edits):
- implement: ~8,645 tokens; largest layer `code/implement` skill 3,344 (38.7%) — just under the 40% flag; task_context 2,049 (23.7%); base_prompt 1,626 (18.8%).
- peer-review: ~6,770 tokens; largest task_context 30.3%.
- No layer exceeds 40%. ~1,200 of the 2,049 Context tokens are the standard ticket-guide comment (reaches the prompt by design). Small prompt overall.

**Before launch:** fix the "design step" wording; decide on a mandatory owner checkpoint after classification; settle compatibility up front (likely "accept the break" per project-stage); add GitHub-URL links to the grep/update list; consider splitting A from B.
