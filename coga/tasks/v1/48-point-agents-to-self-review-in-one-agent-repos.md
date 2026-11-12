---
title: Point agents to self-review in one-agent repos
status: in_progress
owner: zach
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
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
step: 2 (peer-review)
agent: claude
---

## Description

Coga ships three workflows with `other-agent` steps: `code/with-review`,
`code/design-then-implement`, and `docs/with-review`. In a repo where no peer
agent resolves (one declared agent, or three or more with no `peer =`) those
steps can never run. One-agent repos are now the norm on single-agent machines
(v1/20), yet `coga build` hands every starter implementation ticket
`code/design-then-implement` and Dream files `code/with-review` drafts.

We need a simple prose change so the agent picking a workflow first checks
`[agents.*]` in `coga/coga.toml` (and `coga.local.toml`). If only one agent is
configured, or three or more with no `peer =` on the main agent, it uses
`code/with-self-review` instead. With exactly two agents no `peer =` is needed,
so a missing `peer =` alone is not the signal. The change should be a few lines.

### Prose to add

Add this section near the top of each peer workflow's body, verbatim:

```markdown
## Before choosing this workflow

This workflow needs a second agent to review the code. Check `[agents.*]` in
`coga/coga.toml` and `coga.local.toml`. If only one agent is configured — or
three or more with no `peer =` on the main agent — use `code/with-self-review`
instead.
```

### Acceptance criteria

- `src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md`
  and `.../workflows/code/design-then-implement.md` carry the section above.
- `src/coga/resources/templates/coga/bootstrap/workflows/build/onboarding.md`,
  where it tells the build agent to create implementation tickets with
  `--workflow code/design-then-implement`, adds one clause: in a one-agent repo
  (as defined above), use `code/with-self-review` instead.
- `src/coga/resources/templates/coga/recurring/dream/ticket.md` adds the same
  clause wherever it files `code/with-review` drafts.
- Out of scope: `docs/with-review` (there is no docs self-review workflow to
  point to), and any Python or `coga create` behavior change. Prose only.
- `python -m pytest` and `coga validate` pass.

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
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

## Dev

branch: coga/v1-48-point-agents-to-self-review-in-one-agent-r-7c4a8d


## Implement handoff (2026-11-12)

Commit abd765f1d on the branch (rebased on origin/main c370f1ee3, pushed).
Prose only, 4 files:
- `bootstrap/workflows/code/with-review.md` and `code/design-then-implement.md`:
  the "## Before choosing this workflow" section, word for word from the ticket,
  is the first body section (before the skilled-step framing note).
- `bootstrap/workflows/build/onboarding.md`: the implementation-work bullet now
  says that in a one-agent repo (definition inlined) it uses
  `--workflow code/with-self-review` instead.
- `recurring/dream/ticket.md`: the clause is added once, in "Filing rules for
  every draft ticket Dream creates". All three places Dream files a
  `code/with-review` draft (proposal ownership, Phase 1 PR proposals, gap
  findings) already say "under the filing rules above", so one sentence
  covers every site without repeating it.
- `docs/with-review` was left alone (out of scope).

Tests: `python -m pytest`: 5 failures. The same 5 fail on a clean origin/main
worktree, so they were already broken and are unrelated to this change:
test_config::test_layout_contexts_cyclic_root_rejected,
test_edge_distribution::test_documented_legacy_adoption_preserves_state_and_reconciles_callers,
test_git::test_final_package_edits_never_escape_a_mutating_cli_sweep[dirty-package, committed-package],
test_packaging::test_context_navigation_has_no_broken_links (README links to
the missing ticket document-the-remedy-for-a-bloated-blackboard-sibli.md).
`coga validate --json` gave warnings only (existing hand-authored tickets).

Human request: Zach wants to see the agent handle this live in the VMware VM
(`coga-win11-walk`) by installing from this branch's SHA before the ticket moves on.

### Live VM check (2026-11-12, coga-win11-walk, coga installed from git+…@abd765f1d)

Zach ran `coga build` with the vision "a small Python command that tells me the
date and time".
- Two agents (claude + codex configured by init): the 5 build tickets came out
  `code/design-then-implement`, and the agent's stated reason was "claude and
  codex are both configured, so codex can be the second-agent reviewer". PASS
  (this is the control).
- One agent (fresh repo, `[agents.codex]` removed, only claude): the 6 build
  tickets came out frozen `name: code/with-self-review` (Zach checked the
  ticket files), and the agent said "Only one agent is configured, so the
  build tickets use code/with-self-review". Decision tickets stayed
  `draft-for-human`. PASS.
- Three agents with no `peer =`: not run.

## PR

```yaml
title: Point one-agent repos to code/with-self-review
author: Claude Code (claude-opus-5-5), attended session
head: abd765f1d9d99d12c8d2b1c220a25e1c88fadbcd
base: c370f1ee398e9f5c3abd2a2c266bc6b841c835fa
review_depth: light
review_depth_rationale: four prose-only template edits; the shipped workflow text was specified word for word in the ticket
files:
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-review.md: add the Before choosing this workflow section
  src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md: add the Before choosing this workflow section
  src/coga/resources/templates/coga/bootstrap/workflows/build/onboarding.md: one-agent clause on the implementation-ticket create
  src/coga/resources/templates/coga/recurring/dream/ticket.md: one-agent clause in the draft filing rules covering every code/with-review filing
review: not yet run (the peer-review step follows)
checks:
  - command: python -m pytest
    result: on head abd765f1d (committed tree, clean src/tests), 4761 passed, 33 skipped, 5 failed; all 5 also fail on origin/main c370f1ee3 (listed under Tests above)
  - command: coga validate --json
    result: exit 0, warnings only
```
