---
title: 02 Move Coga-dev contexts out of the shipped set
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
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
step: 1 (implement)
agent: claude
---

## Description

Carry out the decision record in `coga/tasks/context-audiences/README.md`,
which sibling `01` writes and the owner approves. It defines two context
audiences, for repos that use Coga and for developing Coga. Make the split real
in the tree, the package, the tests and the guidance docs. Do not reopen the
README's product decisions. If the README is missing, unapproved, or doesn't
cover something you hit, ask the owner.

1. **Move and split topics** as the README's classification table says, in
   `docs/contexts/` and in the packaged twins under
   `src/coga/resources/templates/coga/bootstrap/contexts/`.
2. **Stop shipping Coga-dev topics.** Delete their packaged copies and make
   `tests/test_packaging.py` enforce the split: `REQUIRED_BOOTSTRAP_CONTEXT_REFS`
   holds only user topics. `LOCAL_ONLY_CONTEXT_REFS` currently demands a reason
   per topic, so change how it expresses a whole local-only audience (e.g. by
   namespace) rather than listing about 30 identical reasons.
3. **Update every ref and link** to a moved topic: ticket `contexts:` in
   `coga/tasks/`, skills, workflows, source strings, tests, fixtures
   (`tests/fixtures/seeded-repo/`), `README.md`, `AGENTS.md`, and GitHub-URL
   links in packaged templates.
4. **Update the guidance docs** so they name both sets and the criterion:
   `docs/README.md`, `coga/knowledge`, `coga/packaging`,
   `coga/context-layout`, the `bootstrap/ticket` skill's "Context and skill
   selection contract", and `AGENTS.md`'s canonical-topics list.
5. **Release note** naming the renamed and de-packaged refs, per the README's
   compatibility decision.

Done when every topic under `docs/contexts/` matches its README row, the
packaged bootstrap set contains only `user` topics and the packaging test
enforces it, no reference to an old ref or URL remains outside
`docs/archive/`, `docs/README.md` and `bootstrap/ticket`'s selection contract
each name both sets and the criterion, and `python -m pytest` and
`coga validate --json` pass.

## Context

### Depends on 01

Don't start until `context-audiences/01-classify-contexts-by-audience-and-decide-the-la`
is done and the README decision record is approved. Read the README first. It
is not composed into this prompt.

### Topics this ticket edits (cited, not attached)

These are read and edited, so they are left off `contexts:`:

- `coga/packaging` (`docs/contexts/coga/packaging/SKILL.md`): twin mapping,
  the "Local-only" definition, and the bootstrap/init-seeded/local-only
  categories. Read it whole before touching twins.
- `coga/knowledge` (`docs/contexts/coga/knowledge/SKILL.md`): "Attach or
  cite".
- `coga/context-layout` (`docs/contexts/coga/context-layout/SKILL.md`). This
  repo sets `[layout] contexts = "docs/contexts"` in `coga/coga.toml`, and
  `config.contexts_root` resolves it.
- `docs/README.md`, whose Start / Understand / Operate / Internals grouping is
  a rough precursor of the split.
- The `bootstrap/ticket` skill
  (`src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/`). It
  has no live twin under `coga/skills/`.
- `AGENTS.md`.

### Mechanics

- Packaged twins must stay byte-identical with their canonical copies, which
  `tests/test_packaging.py` derives and enforces. A moved user topic moves in
  both trees. A de-packaged topic loses its packaged copy and becomes
  local-only.
- Composition fails loud on an unknown ref, so a missed `contexts:` entry in
  `coga/tasks/` breaks that ticket's next launch. Grep refs, `docs/contexts/<ref>`
  paths, and `github.com/FastJVM/coga/blob/main/docs/contexts/` URLs.
- Exclude `docs/archive/**` from the rewrite. It is dated history.

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
