---
title: 02 Delete the code topic and remove Coga-repo-only text from shipped topics
status: in_progress
owner: nicktoper
contexts:
- coga/knowledge
- coga-dev/packaging
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
step: 2 (peer-review)
agent: claude
---

## Description

Delete the coga/code topic, fix links and statements that are only true inside the Coga repo, and turn 'Known gap' bug notes in shipped topics into tickets. See `coga/tasks/blocks/README.md`.

## Context

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

### Scope and acceptance

Read `coga/tasks/blocks/README.md` first: it holds the test, the rules every
ticket in this group follows, and the audit rows for these topics. The audit
verdicts are recommendations; re-check each against current main and record
any disagreement on the blackboard for the owner before departing from it.

Done when: `coga/code` is deleted, no shipped topic states something true only inside the Coga repo, and no shipped topic carries a "Known gap" bug note; both copies of every touched topic are byte-identical;
no link in `docs/`, `src/`, `tests/`, `coga/` (outside old tickets and the
log), `README.md` or `AGENTS.md` points at a removed topic or anchor; any new
coga-dev page is listed in `docs/contexts/coga-dev/internals/SKILL.md`;
`.venv/bin/python -m pytest` and `coga validate --json` pass.

### Specifics

- `coga/code`: repoint `architecture:76` (drop the map entry) and
  `lifecycle:165` (→ `../blackboard/SKILL.md#superseded-designs`); move the
  "record is explicit, not inferred from the slug" rationale into
  `coga/checkouts` if it is not already there.
- Coga-repo-only text to remove or generalize: `checkout-cleanup:81` link to
  `../../../archive/evidence/...` (broken in the packaged copy);
  `recurring/scheduling:76` "This repo's `upstream-coga`"; `context-layout`
  "This repo overrides `coga/bootstrap/resolve-conflicts`"; `important`
  lines 10–15 (usage-report routing); `knowledge` `docs/archive/*` rows;
  `skill-management` google-agents-cli/anthropic pack examples;
  `tickets/discovery` `relay-os/tasks` pathspecs; `usage` "team runs on a
  subscription" and `docs/archive/evidence` links. Search for more
  (`grep -rn 'archive/\|This repo\|relay-os' docs/contexts/coga`).
- Known gaps: `checkout-cleanup` (foreign linked branch),
  `checkout-cleanup/branch-sweep` (`_local_branches` return code),
  `recurring/scheduling/failures` (`_record_unlaunched_creates`,
  `run_recurring_named` sync sink), and any other
  `grep -rn 'Known gap' docs/contexts/coga`. Create one draft ticket per gap
  at the top level (not in `blocks/`), then delete the paragraph.
- Also fix `sandboxes:41` ("When `git worktree add` cannot write…" is stale:
  sandbox-clone now triggers on branch creation failing) and add
  `prepare-checkout` to the recipe list in `coga/cli`.
- Leave tickets 03–09's structural trims to them; this ticket only removes
  the text named here, so later tickets start clean.


<!-- coga:blackboard -->
## Dev

branch: coga/blocks-02-delete-the-code-topic-and-remove-coga--23a0ec


## Implement handoff (2026-10-21)

Done on the branch (commit `d487710bb`), all twins byte-identical:

- Deleted `coga/code` (both copies; dropped from `REQUIRED_BOOTSTRAP_CONTEXT_REFS`).
  Repointed `architecture` map, `lifecycle` (→ `blackboard#superseded-designs`),
  `docs/README.md`, `coga-dev/codebase`. The "record is explicit, not inferred
  from the slug" rationale is now a paragraph in `coga/checkouts` intro.
- Coga-repo-only text: `checkout-cleanup` archive link dropped;
  `recurring/scheduling` upstream-coga sentence dropped (its own ticket states
  `scope: clone`); `context-layout` override sentence → `coga-dev/packaging`;
  `important` usage-report example generalized (usage-report ticket owns its
  routing); `knowledge` three archive rows → one generic row, Coga's paths →
  `coga-dev/archive-access`; `skill-management` google/anthropic examples
  generalized, pack decision → `coga-dev/current-direction`; `tickets/discovery`
  relay-os pathspecs → `coga-dev/codebase/gotchas`; `usage` subscription clause
  and archive links dropped, links → `coga-dev/internals/activity-capture`.
- Known gaps → drafts (top level): `guard-foreign-linked-worktree-branch-cleanup`,
  `fail-the-branch-sweep-when-local-branch-enumeratio`,
  `name-unlaunched-created-periods-when-the-recurring`,
  `report-failed-create-syncs-from-named-recurring-la`. Paragraphs deleted;
  `checkout-cleanup` "known gap below" pointer rewritten as a behavior fact.
- `sandboxes`: trigger is now "creating the feature branch fails because the
  primary `.git` is read-only". `cli`: `prepare-checkout` added to recipes.
- Left alone on purpose: `workflows` "known gaps in PRs #1058…" (W43 history,
  ticket 08); `tests/test_init.py` synthetic `coga/code` fixture strings;
  `docs/release-notes/context-audiences.md` rename table (history, not a link);
  `sandbox-clone` "this repo's checkout root" (means the adopting repo).
- Audit disagreement: none.

**Incident — main is red until this PR lands.** Running `coga create` with the
docs edits uncommitted made its exit sweep publish the whole `docs/contexts/`
half to main as `001aad66f` "Sync coga state" (the contexts root is Coga state).
Main therefore has the canonical edits and the `coga/code` deletion but not the
packaged twins or the `test_packaging.py` line: on `origin/main` (a0982d68c)
`tests/test_packaging.py` has 3 failures. After rebase this branch's diff is
only the twins + test (18 files). Lesson: commit before any mutating `coga`
command when contexts-root files are dirty.

Pre-existing, unrelated: `coga validate --json` exits 1 on
`marketing/fix-installer/find-out-what-macos-actually-ships`
(`unsynthesized-draft-blackboard`); same 48 issues on main.

## Peer review

Direct Codex review is in progress after the required rebase onto
`b888023bb`. The implementing commit records Claude Opus 5.5; this is a fresh
Codex reviewer session, not self-review. No nested reviewer was launched.

Must-fix finding (fixed): deleting the package fallback leaves two stored tickets
with unresolved `contexts: coga/code` attachments, which source-backed
validation reports even though both tickets are done. Repointed
`fix-parser-bugs-documented-in-pr-1055` to `coga/checkouts` and remove the
duplicate obsolete attachment from
`match-concurrent-codex-sessions-to-their-launch-so`, which already attaches
`coga/checkouts`. Historical prose mentions remain untouched. Both fixes
published to control in `717ffdd37`.

Initial source-backed validation at `2ce7a2aec` reports 50 issues: the two
new `broken-context` errors above, the existing
`marketing/fix-installer/find-out-what-macos-actually-ships`
`unsynthesized-draft-blackboard` error, and 47 warnings. After the attachment
fix, only the existing draft error remained. The attending human then
requested fixing it too: synthesized the evaluator's substantive findings
into that draft's body (machine-state questions, primary sources, pip-to-uv
bootstrap, PATH/externally-managed checks, explicit findings attachment),
kept its frontmatter unchanged, and preserved the old body and evaluator
evidence under `## Superseded designs`. Scoped validation now exits 0; its
unfrozen draft workflow is a warning, not an activation request.

The first source-backed full suite completed at `2ce7a2aec` against
`b888023bb`: `PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest -q`
— 3955 passed, 7 skipped in 367.69s, Python 3.12.12. A final freshness pass,
full-suite rerun, and pristine-checkout packaging check follow state publication.

## PR

```yaml
title: Delete coga/code and strip Coga-repo-only text from shipped topics
author:
  agent: claude
  model: claude-opus-5-5
head: d487710bb3d18bf1b9351b356bae6afd71325284
base: a0982d68cd1f9c3648db491c99b50d84a0460b9d
review_depth: standard
review_depth_rationale: Docs-only twin sync plus one test-list line; the canonical half already landed on main via an accidental state sweep, so this PR restores twin byte-identity.
implementation: Packaged twins of the edited coga/* topics, deletion of the packaged coga/code topic, and removal of coga/code from REQUIRED_BOOTSTRAP_CONTEXT_REFS. The canonical docs/contexts edits are already on main (001aad66f).
deviations: Canonical half landed on main outside the PR (see blackboard incident).
limitations: None known.
files:
  src/coga/resources/templates/coga/bootstrap/contexts/coga/**: packaged twins of the canonical edits; code/ deleted
  docs/README.md: drop the coga/code overview link
  tests/test_packaging.py: drop coga/code from required bootstrap refs
review: not run; code review is a later workflow step
checks:
  - command: .venv/bin/python -m pytest -q
    result: 3955 passed, 7 skipped (pre-rebase tree; content identical after rebase)
  - command: .venv/bin/python -m pytest -q tests/test_packaging.py
    result: 30 passed at d487710bb
  - command: coga validate --json
    result: exit 1, 48 issues, the single error pre-existing and unrelated; identical count on main
```
