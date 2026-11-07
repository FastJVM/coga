---
title: Mention coga build in the install flow
status: in_progress
owner: zach
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills: []
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 4 (review)
agent: claude
---

## Description

The `coga/install` page ends its install path without naming the next
command. Its `## Verify` section stops at "continue with
[coga/first-task]", so a reader who installs from that page is never told
that `coga build` is their next step. (The page mentions `coga build`
only under Prerequisites, as the command that offers to install a missing
agent CLI.) Add the next step there, split by repo state, matching
what `coga init` prints:

- **Otherwise empty Git repo:** `coga build` (or `coga build --agent <other>`
  for the other agent CLI).
- **Repo that already has files:** `coga ticket "<title>"`, not `coga build`.

Done when `coga/install`'s `## Verify` section (or the sentence that hands
off from it) says the next step comes after `coga init`, names
`coga build` for the empty-repo case and `coga ticket "<title>"` for the
existing-repo case, keeps the link to `coga/first-task`, leaves the page with
one next-step hand-off rather than two overlapping ones, and the packaged copy and its legacy live twin are
byte-identical. No code change.

## Context

### Files to edit (cited, not attached)

- Package owner:
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md`.
- Legacy live twin: `docs/contexts/coga/install/SKILL.md`. It is
  byte-identical to the package copy today, and `tests/test_packaging.py`
  requires them to stay identical. Edit both in the same commit (see
  AGENTS.md), then run `python -m pytest tests/test_packaging.py`.
- Current `## Verify` text ends: "These commands check the CLI installation,
  not agent authentication or a completed first task; continue with
  [coga/first-task](../first-task/SKILL.md)." The change belongs at that
  hand-off.
- A second hand-off sits at the end of `## Upgrading and removing`: "Next:
  adopt Coga into a repository with [coga/init], then walk a first ticket
  with [coga/first-task]." Put the build/ticket split in one place only. Either
  write it at the Verify hand-off and leave the "Next:" line as a pointer, or
  fold it into the "Next:" line and trim Verify. The reviewer must not find
  two overlapping next-step paragraphs.

### Facts to match, not restate

- `coga init` already prints this split. In `init` (the next-steps block at
  the end of the init command), an empty repo gets "Run `coga build` … or
  `coga build --agent <other>`", where `<other>` is whichever agent is not the
  configured default, and a filled repo gets
  "Run `coga ticket "<title>"` to author your first task". `coga/init`
  (`src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md`,
  "printed next steps") documents the same. The install page must agree with
  both.
- `coga/init` owns what "empty" means: nothing but `.git`, `.DS_Store`,
  and a short starter README, LICENSE or `.gitattributes`. Link to it
  instead of defining "empty" again on the install page (`coga/knowledge`:
  one owner per fact).
- `coga/first-task` already explains what `coga build` does (onboarding
  chat, vision, starter batch). Keep the install page to one or two
  sentences naming the command, and leave the explanation to first-task.
- Installing never modifies a repo; `coga init` does. The next step comes
  after `coga init`, so the sentence should say "after `coga init`" rather
  than suggest `coga build` straight after `uv tool install`.

### Scope and known tension

- Edit only `coga/install`. The README already names `coga build` for the
  empty-repo case in its "Choose how to begin" block, and
  `v1/23-scan-for-an-existing-repo-during-install` owns the README's
  existing-repo line (`coga chat` → `coga ticket "<title>"`). Do not touch
  the README here.
- Zach decided on 2026-10-17 to delete `coga/install` in favour of the
  README, and `v1/26-make-the-readme-install-section-the-only-install-p`
  owns that removal. The owner chose on 2026-11-04 to fix this page anyway
  while it still ships. Keep the edit small so v1/26 can drop or carry it
  over cheaply.
- Order versus v1/23 is not enforced. If this lands first, the install page
  says `coga ticket "<title>"` for existing repos while the README still says
  `coga chat` until v1/23 merges. That short gap is accepted. Both tickets
  touch `coga/install` only if v1/23 finds a prerequisite contradiction,
  which would be in a different section, so a rebase is enough.

### History

- Nico flagged the missing `coga build` in the review on 2026-10-19.
- Self-QA on `v1/29-test-and-fix-install-on-macos-and-windows` removed
  `coga build` from the README install block on 2026-10-18, because it
  told every reader to run it, including existing repos. Zach on 2026-10-21:
  `coga build` belongs to the new-repo case only.
- The ticket originally targeted the README. On 2026-11-04 it was rescoped
  to `coga/install`, because the README now covers the new-repo case and
  v1/23 covers the existing-repo one.

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

Previous ref: `marketing/fix-installer/mention-coga-build-in-the-install-flow` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/1171
branch: coga/v1-24-mention-coga-build-install

## Plan (implement)

- Put the build/ticket split at `coga/install` `## Verify` hand-off (after
  `coga init`), link `coga/init#fresh-repo` for "empty", keep first-task link.
- Remove the duplicate "Next:" line under `## Upgrading and removing` so the
  page has one next-step hand-off; its `coga/init` link moves into Verify.
- Edit package owner and `docs/contexts/coga/install/SKILL.md` twin together.

## Handoff (implement → peer-review)

Done on `coga/v1-24-mention-coga-build-install` (commit 0cb12b242, pushed,
rebased on origin/main). Docs-only; no code touched.

- `## Verify` now ends: CLI check caveat, then one paragraph: "Next, adopt
  Coga … with `coga init`. After `coga init`, run `coga build` in an
  otherwise empty repo (`coga build --agent <other>` …), or
  `coga ticket "<title>"` in a repo that already has files;
  coga/first-task walks through both." "Empty" links to
  `coga/init#fresh-repo` (owner of the definition), not redefined.
- Removed the "Next: adopt Coga … coga/init … coga/first-task" line from
  `## Upgrading and removing` (would have overlapped). Its links live on
  in the Verify paragraph.
- Matches `coga/init` "printed next steps" and first-task (which covers
  both `coga build` and `coga ticket`). README untouched (v1/23 owns it).
- Package copy and `docs/contexts/coga/install/SKILL.md` are byte-identical.

Verification: `.venv/bin/python -m pytest tests/test_packaging.py -q` →
37 passed. (System `python` lacks `tomlkit`; use the repo venv.)

Reviewer focus: wording of the single hand-off paragraph; whether dropping
the "Next:" line (vs. leaving a pointer) is acceptable — ticket allowed
either fold or pointer; I chose one hand-off only.

## Peer review

2026-11-04 — Codex: passed, no must-fix findings or content edits.

- Reviewed the complete two-file Markdown diff against current main. The
  hand-off explicitly follows `coga init`, names the build/other-agent and
  existing-repo ticket commands, and keeps first-task guidance in its owner.
  It agrees with `src/coga/commands/init.py:1591-1605` and `coga/init`.
- Removing the old "Next:" paragraph is within scope and leaves one
  next-step hand-off. The init and first-task links resolve in both copies;
  the `#fresh-repo` anchor exists. README, code, and fixtures are untouched.
- Independent authorship is established by the implementation audit receipt
  in `coga/log.md` (Claude session
  `99564b46-452e-489f-9b9f-de07b0fae0f9`, step `implement`) and its Claude
  co-author trailer, rather than the configured agent assignment.
- Rebased onto `b446530c153d4d9e52d50c92f0934c45bd651b90`; only ticket/log
  state had advanced. Reviewed head is
  `c6019d577d2d7cfffc44e4adb8263c59e09efe59`, pushed with an explicit lease.
  The install pages and reference sources are unchanged by the rebase.
  Returned to clean, current `main` before writing this handoff.
- `cmp` of the package owner and legacy twin and `git diff --check main...HEAD`
  both passed on that head. Pytest was not rerun for this prose-only review;
  the implement handoff's 37 passing packaging tests remain historical
  evidence for `0cb12b2423f36907cc2010883f8ec9d259b2b98a`.
- `coga validate --task v1/24-mention-coga-build-in-the-install-flow --json`
  passed with no issues after recording the review and PR preparation.

Ready for `open-pr`; no blockers or remaining review findings.

## PR

```yaml
title: Name coga build and coga ticket after coga init
author: claude
author_evidence: >-
  The coga/log.md implementation receipt identifies CLI claude, model
  claude-opus-5-5, session 99564b46-452e-489f-9b9f-de07b0fae0f9, and step
  implement. The implementation commit also has a Claude co-author trailer.
head: c6019d577d2d7cfffc44e4adb8263c59e09efe59
base: b446530c153d4d9e52d50c92f0934c45bd651b90
depth: merge
rationale: >-
  Small documentation change with independent Codex review and no unresolved
  findings. Source comparison, link inspection, twin equality, and whitespace
  checks cover the changed prose; no runtime code or fixtures changed.
implementation: >-
  The install Verify hand-off now names coga build (including the other-agent
  option) for an otherwise empty repo and coga ticket "<title>" for an existing
  repo after coga init. It links the empty-repo definition and first-task walk,
  and removes the duplicate next-step paragraph under Upgrading and removing.
deviations: None; only the install topic and its legacy twin changed.
limitations: >-
  No end-to-end install run or pytest rerun during peer review because the
  change is prose only. Implementation reported 37 passing packaging tests
  before the rebase; that historical result is not a current-head test receipt.
files:
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: >-
    Package owner of the single install hand-off with the repo-state split.
  docs/contexts/coga/install/SKILL.md: >-
    Legacy live twin kept byte-identical to the package owner.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: c6019d577d2d7cfffc44e4adb8263c59e09efe59
  base: b446530c153d4d9e52d50c92f0934c45bd651b90
  detail: >-
    Reviewed both complete Markdown diffs, init's next-steps implementation,
    init and first-task contexts, internal links and the fresh-repo anchor.
    All acceptance criteria are satisfied; no must-fix findings.
checks:
  - command: cmp src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md docs/contexts/coga/install/SKILL.md
    status: passed
    head: c6019d577d2d7cfffc44e4adb8263c59e09efe59
    base: b446530c153d4d9e52d50c92f0934c45bd651b90
    detail: Exit 0; package owner and legacy live twin are byte-identical.
  - command: git diff --check main...HEAD
    status: passed
    head: c6019d577d2d7cfffc44e4adb8263c59e09efe59
    base: b446530c153d4d9e52d50c92f0934c45bd651b90
    detail: Exit 0; no whitespace errors in the reviewed branch diff.
  - command: .venv/bin/python -m pytest tests/test_packaging.py -q
    status: not-run
    detail: >-
      Not rerun during prose-only peer review. The implement handoff reports
      37 passed on 0cb12b2423f36907cc2010883f8ec9d259b2b98a; current twin
      equality was checked separately after rebasing over ticket/log updates.
  - command: python -m pytest
    status: not-run
    detail: No code or fixtures changed; the peer-review step excludes a full-suite run for pure prose.
```
