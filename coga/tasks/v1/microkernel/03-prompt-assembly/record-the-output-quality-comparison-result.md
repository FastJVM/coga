---
title: Record the output-quality comparison result
status: in_progress
owner: nicktoper
workflow:
  name: docs/with-review
  steps:
  - name: implement
    skills: []
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills: []
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills: []
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 4 (review)
agent: claude
---

## Description

Record in `coga/prompt-composition` (`src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md`) the result of ticket `v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality`. The owner judged 8 blinded output pairs (PR body/diff, design spec, topic edit, authored ticket) comparing the current assembly against C1′, which is C1 with the baseline checkout/reconcile guidance restored. Result: baseline 4, C1′ 3, tie 1. Every mechanical gate passed in both arms. Owner decision (2026-11-15): **inconclusive**; keep the current assembly. No further trial was commissioned.

### What to write

- One or two sentences extending the assembler ruling that PR #1234 (`record-the-prompt-assembly-non-replacement-ruling`) adds. Ticket 02 measured rule compliance only. Ticket 04 measured output quality and found no clear difference. The current assembler stays.
- Note the limits: a one-model pilot with two repetitions, judged from chat presentations with varying abridgment.
- Link `coga/tasks/v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality/report.md` (§3, §5) the same way PR #1234 links ticket 02 evidence (GitHub main URL).

### Sequencing and scope

- Start after PR #1234 merges. This builds on its `## Assembler ruling` section; do not duplicate it.
- Summarise and link only; do not restate the protocol.
- Edit only the packaged topic. No production code.
- Ticket 03 has been rescoped to fix current-assembly defects. Do not describe that work here.

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
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
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

pr: https://github.com/FastJVM/coga/pull/1237
branch: coga/v1-microkernel-03-prompt-assembly-record-the-out-38f7c9


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Handoff (implement, 2026-11-15)

- Sequencing: PR #1234 was still open. With the owner's explicit approval, I
  merged it (merge commit 210a140fb) and fast-forwarded this branch onto it.
- Change: commit 3685c8d38 adds one paragraph to `## Assembler ruling` in
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md`.
  It says ticket 02 measured rule compliance only. It records ticket 04's
  output-quality result: baseline 4, C1' 3, tie 1, all gates passed in both
  arms, and the owner ruled it inconclusive, so the current assembler stays.
  It names the limits: one model, two reps, chat presentations with varying
  abridgment. It links report.md §3, §5 by GitHub main URL, as the ticket-02
  evidence is linked. It does not restate the protocol or mention ticket 03's
  rescope.
- Verified: the link target is tracked on main.
  `python -m pytest -q tests/test_packaging.py` gave 40 passed.
  `coga validate --json` exited 0.
- Pushed. The PR is not opened yet; that is the next step.

## Peer review

- Independent Codex content review of Claude's commit 3685c8d38; authorship
  confirmed by its Claude co-author trailer and the implement handoff.
- No must-fix findings. The result, mechanical gates, owner decision and
  limitations match report sections 2, 3 and 5; the GitHub main target is
  tracked. Only the packaged topic changes; no duplicate definition is added.
- The paragraph uses more than the suggested one or two sentences but remains
  a concise summary; no protocol restatement or ticket-03 discussion.
- Freshness: fetched origin/main twice. Its changes since the reviewed base
  affect only this ticket and coga/log.md, not the topic or evidence. This
  read-only review requires no branch merge; projected ticket state is preserved.
- `git diff --check origin/main...HEAD` passed. Pytest was not run because
  neither code nor fixtures changed. Branch push confirmed up to date.

## PR

```yaml
title: Record the prompt-assembly output-quality result
author: claude
author_evidence: >-
  Implementation commit 3685c8d38 has a Claude Opus 5.5 co-author trailer;
  the implement handoff records that change.
head: 3685c8d38f329eceee788833f18499fec768ec0f
base: 210a140fbeb9613151eabcc9e8bdbd0c1c8e5b3b
depth: merge
rationale: >-
  Small prose-only evidence summary; independent content review and whitespace
  check passed, with no unresolved findings.
implementation: >-
  Extends the assembler ruling with the inconclusive output-quality pilot,
  its 4/3/1 result, passed gates, limitations and report link.
deviations: >-
  Uses a short paragraph rather than the suggested one or two sentences to
  preserve readability while including the requested evidence and limits.
limitations: >-
  The underlying comparison is a one-model pilot with two repetitions and
  varying abridgment in chat presentations; it establishes no replacement.
files:
  src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md: >-
    The packaged topic owns the assembler ruling and links the comparison evidence.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 3685c8d38f329eceee788833f18499fec768ec0f
  base: 210a140fbeb9613151eabcc9e8bdbd0c1c8e5b3b
  detail: >-
    Reviewed the complete Markdown diff, surrounding ruling, report sections
    2/3/5, prerequisite merge and tracked link target; no must-fix findings.
checks:
  - command: git diff --check origin/main...HEAD
    status: passed
    head: 3685c8d38f329eceee788833f18499fec768ec0f
    base: 210a140fbeb9613151eabcc9e8bdbd0c1c8e5b3b
    detail: >-
      Exit 0; no whitespace errors.
  - command: python -m pytest
    status: not-run
    detail: >-
      Pure prose change; the peer-review workflow directs pytest only for code
      or fixture changes.
```
