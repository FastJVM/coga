---
title: Move the assembler trial evidence out of the shipped prompt-composition topic
status: blocked
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: open-branch
    skills: []
    assignee: agent
    requires: branch
    run: git/open-branch
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: push-and-open-pr
    skills: []
    assignee: agent
    requires: pr
    run: git/push-and-open-pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 3 (peer-review)
agent: claude
---

## Description

Filed by Dream 2026-W48 (run 20261123T224856Z), Phase 2 knowledge scan, shard ks-16, class gap. Target: src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md, section "Assembler ruling" (~2 KB).

That section records Coga's own 2026-11 assembler trial (candidates C1/C1', owner rulings, links to trial reports under coga/tasks/v1/microkernel/03-prompt-assembly/). Under coga/context-layout "Context audiences", Coga-dev development knowledge never ships, yet every adopting repo receives this shipped topic as a fallback. docs/contexts/coga-dev/internals/compose already lists the move as an unanswered "Open placement question" (PR #1234 review thread); no open ticket owns it (grep for "Assembler ruling" finds only the 03-prompt-assembly README).

Proposed resolution, for human judgment: move the trial evidence to coga-dev/internals/compose (or coga-dev/testing/agent-trials), leave a one-line "the current assembler is retained" statement in the shipped topic, and delete the open-question paragraph. Note open PR https://github.com/FastJVM/coga/pull/1279 also edits prompt-composition; sequence after it.

Acceptance: the shipped topic carries only user-visible facts; the evidence lives in a coga-dev page; the open question is closed; tests/test_packaging.py passes.

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
        - name: open-branch
          run: git/open-branch               # Local-first skill directory containing run.py.
          assignee: agent
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (open-branch)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
A workflow run: selects a script for its step. A sibling ticket.py supplies the default script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

The recurring runner writes delegate on materialized period tickets. It
names the parent template's frozen bootstrap/<name> target.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev records branch:, base:, remote:, reviewed: (the commit OID),
and pr: (the full /pull/ URL). Write one field per line and omit unknown
values. coga/git owns the fields and the workflow that writes them.

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

branch: coga/move-the-assembler-trial-evidence-out-of-the-shi-1906c8
base: coga/fix-stale-doc-references-left-by-the-plain-git-m-bc5100
remote: origin
reviewed: 54a523aa545325e8afeffc4a6253bc2ac58691ca

## Implement handoff

- Placement decision: evidence went to `coga-dev/internals/compose`
  `## Assembler ruling` because it records the assembler decision.
  `testing/agent-trials` owns the method and links to the decision.
- The first full `pytest` run used the launch's in-repo `$TMPDIR`
  (`coga/.coga/tmp/…`) and deleted 35 tracked files in
  the real checkout (`coga/coga.toml`, `coga/context.md`, `coga/log.md`,
  `coga/workflows/*`, `docs/contexts/coga-dev/**`, `.gitattributes`). The
  implementation session restored those files from HEAD. The **uncommitted
  18-line `coga/log.md` delta present at session start was lost**.
  `stop-the-test-suite-from-deleting-files-in-the-rea`
  tracks the isolation bug. The same run removed the ignored `coga/coga.local.toml`.
  On 2026-11-23 the owner authorized recreating it with `user = "nicktoper"`.
  Any other previous local settings are unknown and `.coga/data/` was absent.

## Peer-review handoff

- Codex reviewed Claude Code's four-file diff against the recorded local
  base `e9f49b2089c16f76a0c734e8e61be8516c5240bf`. The review checked both
  owner decisions against the pinned reports and verified all three links
  to the `assembler-ruling` anchors. A review commit reduced the shipped
  ruling to one sentence while preserving its anchor.
- The local stack contains patch-equivalent versions of #1279's two
  prompt-composition changes. #1279 is still open. The recorded direct base
  is absent on `origin` and belongs to
  `fix-stale-doc-references-left-by-the-plain-git-mig`, which is blocked on
  publication of its own base. The PR script requires the recorded remote
  base. Recheck the stack and diff once that branch is published.
- Run pytest in an isolated clone with system temp outside every checkout.
  Unset inherited `COGA_SYSTEM_TMPDIR` so tests that redirect `tempfile`
  and `TMPDIR` exercise the same test directory through Coga. With that
  variable inherited, three temp-directory tests failed before and after
  the review correction. All three passed on the clean rerun.

## PR

```yaml
title: Move the assembler trial evidence out of the shipped prompt-composition topic
author: claude
author_evidence: >-
  Claude Code (claude-opus-5-5) wrote da2a11b67 in launch a0eebbce.
  Codex wrote the one-sentence correction in 54a523aa5 during peer review.
head: 54a523aa545325e8afeffc4a6253bc2ac58691ca
base: e9f49b2089c16f76a0c734e8e61be8516c5240bf
depth: skim
rationale: >-
  Four-file documentation move on a stacked base. The direct base branch
  needs publication before the stacked PR can open.
implementation: >-
  Keeps the shipped Assembler ruling anchor with a one-sentence statement.
  Moves both trial rulings and evidence links to coga-dev/internals/compose,
  closes its placement question, and updates links from agent-trials and the
  prompt-assembly task index.
deviations: >-
  None. The ticket allows internals/compose, which owns the assembler decision.
limitations: >-
  Native Windows and macOS verification is deferred to release.
files:
  src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md: "Shipped topic keeps only the user-visible retained-assembler fact."
  docs/contexts/coga-dev/internals/compose/SKILL.md: "Receives the trial evidence and rulings; open placement question removed."
  docs/contexts/coga-dev/testing/agent-trials/SKILL.md: "Rulings link now points at internals/compose."
  coga/tasks/v1/microkernel/03-prompt-assembly/README.md: "Current-owner link now points at internals/compose."
review:
  reviewer: codex
  kind: independent
  status: passed
  head: 54a523aa545325e8afeffc4a6253bc2ac58691ca
  base: e9f49b2089c16f76a0c734e8e61be8516c5240bf
  detail: >-
    Codex manually reviewed the entire recorded-base diff, checked both trial
    decisions against the pinned reports, and verified the local anchor targets.
    Claude implemented the move in a separate session. Codex wrote and reviewed
    the one-sentence correction while reviewing the resulting head.
checks:
  - command: 'env -u COGA_SYSTEM_TMPDIR TERM=dumb TMPDIR=/tmp TEMP=/tmp TMP=/tmp PATH="/home/n/Code/coga/.venv/bin:$PATH" PYTHONPATH="$PWD/src" /home/n/Code/coga/.venv/bin/python -m pytest -q -p no:cacheprovider'
    status: passed
    head: 54a523aa545325e8afeffc4a6253bc2ac58691ca
    base: e9f49b2089c16f76a0c734e8e61be8516c5240bf
    detail: >-
      Clean temporary clone, Pop!_OS 24.04 LTS, Python 3.12.12.
      3190 passed, 29 skipped, 0 failed in 222.39 seconds.
  - command: 'env -u TMPDIR -u TEMP -u TMP TERM=dumb PATH="/home/n/Code/coga/.venv/bin:$PATH" PYTHONPATH="$PWD/src" /home/n/Code/coga/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_packaging.py'
    status: passed
    head: 54a523aa545325e8afeffc4a6253bc2ac58691ca
    base: e9f49b2089c16f76a0c734e8e61be8516c5240bf
    detail: >-
      Clean temporary clone, Pop!_OS 24.04 LTS, Python 3.12.12.
      41 passed, 0 skipped, 0 failed in 13.54 seconds.
  - command: 'PYTHONPATH="$PWD/src" .venv/bin/coga validate --json --task move-the-assembler-trial-evidence-out-of-the-shipp'
    status: passed
    head: 54a523aa545325e8afeffc4a6253bc2ac58691ca
    base: e9f49b2089c16f76a0c734e8e61be8516c5240bf
    detail: "One ticket validated with zero issues."
  - command: 'git diff --check e9f49b208...HEAD'
    status: passed
    head: 54a523aa545325e8afeffc4a6253bc2ac58691ca
    base: e9f49b2089c16f76a0c734e8e61be8516c5240bf
    detail: "The four-file diff passed the whitespace check."
```


---

## Blockers

- [ ] [2026-11-23 17:51] [agent:codex] id=20261123T175127 Publish the recorded base branch coga/fix-stale-doc-references-left-by-the-plain-git-m-bc5100 from fix-stale-doc-references-left-by-the-plain-git-mig to origin so the reviewed assembler documentation PR can open.
