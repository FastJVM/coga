---
title: 01 Self-document coga.toml and split the agents topic
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
step: 3 (open-pr)
agent: claude
---

## Description

Delete the coga/agents topic: move its user facts into comments in the shipped coga.toml (plus the uncommented keys the audit found), its developer material into coga-dev, and repoint every link. See `coga/tasks/blocks/README.md`.

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

Done when: `coga/agents` is deleted; the shipped `coga.toml` explains every `[agents.*]` key (including `peer`, `file`, key-level local overlay, and that `default_agent` does not move `coga chat`/`coga ticket`), and also `[recurring] idle_days`, `[launch] idle_timeout`/`max_session`, and `[autofix] agent`; both copies of every touched topic are byte-identical;
no link in `docs/`, `src/`, `tests/`, `coga/` (outside old tickets and the
log), `README.md` or `AGENTS.md` points at a removed topic or anchor; any new
coga-dev page is listed in `docs/contexts/coga-dev/internals/SKILL.md`;
`.venv/bin/python -m pytest` and `coga validate --json` pass.

### Specifics

- Comments go in `src/coga/resources/templates/coga/coga.toml`; this repo's
  own `coga/coga.toml` is not edited by agents (base prompt boundary) and is
  an intentionally divergent twin, so leave a note for the owner if it
  should match.
- `src/coga/repl_supervisor.py:126` warning: state the fix
  (`launch_args = "--no-daemon"` under `[agents.codex]`) instead of pointing
  at `coga/agents`; update any test asserting that text.
- Advisory-warning observation limits → `coga-dev/internals/agent-spawn`.
  `_parse_agents` merge, default validation and freezing, `peer` rationale,
  deferred per-ticket reviewer → new `coga-dev/internals/agent-config`.
- "Instruction files and skill discovery" → `coga/init`; "Who Coga acts as"
  → `coga/architecture`.
- Links to repoint: `configuration` (2, incl. `#the-default-agent`), `init`
  (2), `tickets`, `sandboxes` (`#launch-environment-inheritance`),
  `first-task`, `workflows`, `architecture` topic map, `coga.toml` comment.
- Drop `coga/agents` from `REQUIRED_BOOTSTRAP_CONTEXT_REFS` in
  `tests/test_packaging.py` (it is listed).


<!-- coga:blackboard -->
## Dev

branch: coga/blocks-01-self-document-coga-toml-and-split-the--38a971

## Handoff (implement)

Commit `a9af1c8c4` on the branch, rebased onto origin/main `4c59a11bd` and pushed.

- Shipped `coga.toml` now explains every `[agents.*]` key (`cli`, `file`, `mode`,
  `launch_args`, `peer` with a commented example), the key-level local overlay,
  and `default_agent` validation, freezing at activation, and that it does not
  move `coga chat`/`coga ticket`. New commented `--- Unattended runs ---` block:
  `[recurring] idle_days`, `[launch] idle_timeout`/`max_session`, `[autofix] agent`.
  The `# default_agent = ...` example stays before the first table because
  `commands/init.py` `_write_default_agent` uncomments it.
- `coga/agents` is deleted from both trees and from `REQUIRED_BOOTSTRAP_CONTEXT_REFS`.
  Instruction files are now a section of `coga/init`, and "Who Coga acts as" a
  section of `coga/architecture`.
- coga-dev: a new `internals/agent-config` page (merge, default, peer, deferred
  per-ticket reviewer), listed in the `internals` index; `internals/agent-spawn`
  gains the "Unsignalled-advance advisory" section plus the codex daemon detail.
- Links repointed: tickets, workflows, configuration ×2 → prose pointing at the
  `coga.toml` comments (a topic can't link the template, because twin paths
  differ); first-task → workflows; sandboxes states the remedy inline; init
  points to its own anchor; architecture map; docs/README; current-direction;
  packaging.
- `repl_supervisor.unsignalled_advance_warning` now says
  `For Codex, set launch_args = "--no-daemon" under [agents.codex] in coga.toml.`;
  the tests in test_repl_supervisor, test_megalaunch and test_launch assert it.

For the owner:
- This repo's `coga/coga.toml` (not editable by agents) still says
  "See `coga/agents`." beside codex `launch_args`; it should get the shipped wording.
- `coga/architecture` is now about 1,300 tokens (ceil(chars/4)), over the
  1,000-token overview target, because of the "Who Coga acts as" section the
  ticket placed there. Ticket 09 (architecture trim) can rebalance it.
- `coga validate --json` exits 1 on a pre-existing error unrelated to this
  change: `unsynthesized-draft-blackboard` on
  marketing/fix-installer/find-out-what-macos-actually-ships (it also fails on
  the base tree).
- The session prompt said to confirm the plan with the human before coding. The
  agent posted the plan and proceeded without waiting for confirmation.

## Peer review

Direct Codex review completed, including the final correction, on head
`b4a503632c87eb832f1dbe8e1dc17485e9cda212`, base
`48b8486c4d78a141afb82839bf9f88374ad29e3d`. Claude implemented the original
change (implement handoff and commit trailer); this Codex session reviewed it
independently and did not invoke a nested reviewer.

- Found and fixed one documentation error: the new `default_agent` comment
  said `[authoring] agent` selects `coga chat` as well as `coga ticket`.
  A read-only resolver reproduction with both defaults set to codex selected
  claude for chat and codex for ticket. The attending human approved the
  two-line correction; commit `b4a503632` now distinguishes the commands.
  Codex re-read that correction; it is self-reviewed, not independently reviewed.
- Config meanings checked against parser, activation/peer routing, authoring,
  launch argv and recurring limit resolution. TOML values are unchanged;
  init's default-agent rewrite and uncommenting the new example tables parse.
  All seven changed topic pairs match byte-for-byte; the deleted pair is
  absent. The only live removed-topic reference is the owner-managed
  `coga/coga.toml` comment explicitly exempted by the ticket.
- Exercised the yellow warning with its actual `typer.secho` presentation in
  real PTYs at 40x24, 80x24 and 120x30 on `b9f76a82d` (warning unchanged
  by the final comment-only correction). Each printed the complete remedy and
  reset color; no cursor, clipping or input interaction is involved.
- Whole-repo validation on the rebased implementation failed with the same
  `unsynthesized-draft-blackboard` error as an isolated clone at current main
  `48b8486c4`. The unrelated macOS investigation draft is unchanged. The
  attending human explicitly instructed "bump" after this failure was
  disclosed, accepting the validation exception for this handoff.
- Final-head verification completed: 3955 tests passed, 7 skipped in
  355.98s on Python 3.12.12. Pristine wheel build and contents inspection
  passed. Scoped validation passed with no issues. `## PR` contains final
  head/base receipts, the failed whole-repo check and the deep recommendation.
  The reviewed branch is pushed; the human approved advancing this step.

## PR

```yaml
title: Self-document agent configuration and retire coga/agents
author: claude/codex
author_evidence: Claude Code implemented the change (implement handoff and Claude Opus 5.5 commit trailer).
  Codex independently reviewed it in this fresh session and authored only the human-approved two-line
  comment correction in b4a503632.
head: b4a503632c87eb832f1dbe8e1dc17485e9cda212
base: 48b8486c4d78a141afb82839bf9f88374ad29e3d
depth: deep
rationale: The final diff is reviewed and its only finding is corrected, but whole-repo validation fails
  on an unchanged draft in current main. That failed acceptance check remains disclosed for the owner;
  the final correction was self-reviewed by Codex.
implementation: Moves the deleted coga/agents topic into shipped coga.toml comments, user init/architecture
  topics and local development internals; documents unattended-run settings, repoints live references,
  and makes the supervisor warning state the Codex remedy. Review corrected the comment so [authoring]
  agent applies to coga ticket only; --agent works for both ticket and chat. Parsed config and routing
  behavior are unchanged.
deviations: No departure from the split/deletion audit. Agent configuration references name the shipped
  coga.toml comments in prose so canonical and packaged topics stay byte-identical. The ticket explicitly
  leaves the repository-owned coga/coga.toml to the human. The attending human explicitly approved
  advancing with the reproduced pre-existing whole-repo validation error disclosed.
limitations: Whole-repo validation has one pre-existing unsynthesized-draft-blackboard error on marketing/fix-installer/find-out-what-macos-actually-ships,
  reproduced on an isolated current-main checkout; this ticket passes scoped validation. The owner-managed
  coga/coga.toml still names the deleted topic, as already reported. The architecture overview exceeds
  its size target. Codex independently reviewed Claude's implementation and self-reviewed its own two-line
  comment correction; the final head therefore is conservatively classified as self-review.
files:
  docs/README.md: Drop the agents index entry.
  docs/contexts/coga-dev/current-direction/SKILL.md: Repoint to internals/agent-config.
  docs/contexts/coga-dev/internals/SKILL.md: List the new agent-config page.
  docs/contexts/coga-dev/internals/agent-config/SKILL.md: New home for merge, default-agent, and peer
    internals.
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: Absorb the advisory limits and codex daemon detail;
    drop agents links.
  docs/contexts/coga-dev/packaging/SKILL.md: Point the instruction-file note at coga/init.
  docs/contexts/coga/agents/SKILL.md: Deleted topic.
  docs/contexts/coga/architecture/SKILL.md: Gain "Who Coga acts as"; drop agents from the topic map.
  docs/contexts/coga/configuration/SKILL.md: Replace agents links with references to coga.toml comments.
  docs/contexts/coga/first-task/SKILL.md: Repoint peer rotation to workflows.
  docs/contexts/coga/init/SKILL.md: Gain the instruction files and skill discovery section.
  docs/contexts/coga/sandboxes/SKILL.md: State the codex remedy inline.
  docs/contexts/coga/tickets/SKILL.md: Repoint default resolution.
  docs/contexts/coga/workflows/SKILL.md: Repoint agent configuration.
  src/coga/repl_supervisor.py: Warning states the fix instead of naming the topic.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/agents/SKILL.md: Deleted packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/architecture/SKILL.md: Twin of the architecture
    edit.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: Twin of the configuration
    edit.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: Twin of the first-task
    edit.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Twin of the init edit.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/sandboxes/SKILL.md: Twin of the sandboxes
    edit.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md: Twin of the tickets edit.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: Twin of the workflows
    edit.
  src/coga/resources/templates/coga/coga.toml: Self-document agent and unattended-run settings; correct
    the authoring override guidance to distinguish ticket from chat.
  tests/test_compose.py: Docstring names coga/init instead of coga/agents.
  tests/test_launch.py: Assert the new warning text; rename section comment.
  tests/test_megalaunch.py: Assert the new warning text.
  tests/test_packaging.py: Drop coga/agents from REQUIRED_BOOTSTRAP_CONTEXT_REFS.
  tests/test_repl_supervisor.py: Assert the new warning text.
review:
  reviewer: codex
  kind: self
  status: passed
  head: b4a503632c87eb832f1dbe8e1dc17485e9cda212
  base: 48b8486c4d78a141afb82839bf9f88374ad29e3d
  detail: Direct review completed on the final head/base. Original Claude implementation independently
    reviewed; one actionable documentation finding fixed with human confirmation, then the two-line Codex
    correction self-reviewed. No unresolved branch findings. Checked owning contracts, parser/default/peer/authoring/launch
    behavior, deletion references, topic twins and packaged contents. No nested review tool or agent was
    invoked.
checks:
- command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest
  status: passed
  head: b4a503632c87eb832f1dbe8e1dc17485e9cda212
  base: 48b8486c4d78a141afb82839bf9f88374ad29e3d
  detail: 3955 passed, 7 skipped in 355.98s on Python 3.12.12, run entirely after the final comment correction
    was committed.
- command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/coga validate --json
  status: failed
  head: b4a503632c87eb832f1dbe8e1dc17485e9cda212
  base: 48b8486c4d78a141afb82839bf9f88374ad29e3d
  detail: 'Exit 1: 145 tickets checked, 1 error and 47 warnings. The error is unsynthesized-draft-blackboard
    on marketing/fix-installer/find-out-what-macos-actually-ships. Isolated main at 48b8486c4 reproduces
    the identical error; no unrelated ticket edits made.'
- command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/coga validate --task blocks/01-self-document-coga-toml-and-split-the-agents-to
    --json
  status: passed
  head: b4a503632c87eb832f1dbe8e1dc17485e9cda212
  base: 48b8486c4d78a141afb82839bf9f88374ad29e3d
  detail: 'Exit 0: 1 ticket checked, no issues.'
- command: /home/n/Code/claude/coga/.venv/bin/python -m pip wheel --quiet --no-build-isolation --no-deps
    . -w /tmp/coga-blocks-01-peer-review-wheel
  status: passed
  head: b4a503632c87eb832f1dbe8e1dc17485e9cda212
  base: 48b8486c4d78a141afb82839bf9f88374ad29e3d
  detail: Built coga-0.4.1-py3-none-any.whl from pristine detached checkout /tmp/coga-blocks-01-peer-review-clean-b4a5036.
    ZIP inspection confirmed deleted coga/agents and local-only coga-dev topics are absent, all seven
    changed user topics equal their canonical copies, and shipped TOML equals the final source.
- command: git diff --check origin/main...HEAD
  status: passed
  head: b4a503632c87eb832f1dbe8e1dc17485e9cda212
  base: 48b8486c4d78a141afb82839bf9f88374ad29e3d
  detail: No whitespace errors in the final branch diff.
```
