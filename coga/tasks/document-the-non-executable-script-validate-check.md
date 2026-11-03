---
title: Document the non-executable-script validate check in the user-facing coga validate
  topic
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
step: 3 (open-pr)
agent: claude
launch_generation: 533e8134-e57b-471f-9469-a72c9460894f
---

## Description

Filed by Dream run 2026-11-02 (run 20261102T223931Z), Phase 2 knowledge scan, shard ks-code-skills-2: an extract finding with source done+checkout. The source ticket validate-that-committed-skill-scripts-with-a-sheba is retirement debt: its local branch shebang-exec-check still exists. coga retire deletes it without Retro, so this ticket is the only route for the fact.

Fact: done PR #800 added the non-executable-script error to repo-wide coga validate (validate._check_shebang_executables). The error fires in any adopting repo with vendored skills. The only owner today is docs/contexts/coga-dev/testing/SKILL.md (lines ~30-44), which is local-only and never ships; no coga/** topic or packaged bootstrap context mentions it. Move these user-facing facts into the topic that owns coga validate (coga/first-task, per the coga/cli command map) and its packaged twin:
- A file with a #! line under the skills root or the packaged bootstrap skills must be executable.
- --task does not run the check.
- The remedy is chmod +x or git add --chmod=+x; a hit in the packaged tree routes to upgrading Coga.
- The mode comes from the working tree on POSIX, and from the git index on Windows or with core.fileMode=false; roots with neither are skipped.
Then make coga-dev/testing summarize and link instead of owning the facts.

Overlap: open PR https://github.com/FastJVM/coga/pull/1139 edits docs/contexts/coga/first-task/SKILL.md, including its validate passage, and does not carry this fact. Handle this after that PR's review to avoid a conflicting edit.

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

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/1154
branch: document-non-executable-script-check

## Handoff (implement)

- coga/first-task "0. Check readiness" (and its byte-identical packaged twin)
  gains one paragraph after the readiness code block: #! files under the
  skills root / packaged bootstrap skills must be executable
  (`non-executable-script` error); `--task` skips the check; remedy
  `chmod +x` + commit or `git add --chmod=+x`; a packaged-tree hit means
  upgrade/reinstall Coga (links coga/install#upgrading-and-removing); mode
  source is working tree on POSIX, git index on Windows or
  `core.fileMode=false` (untracked skipped); roots with neither are skipped.
- coga-dev/testing now summarizes and links to coga/first-task; it keeps only
  developer facts: commit packaged shebang scripts 100755, packaged-tree hits
  are fixed upstream / Dream routes them human-needed, and the walk's
  symlink/pruned-dir details with the `validate._check_shebang_executables`
  pointer.
- Implementation placed the paragraph between PR #1139's first-task hunks;
  its trial merge was clean. Peer review corrected the earlier assumption
  that #1139 had no review: its Coga direct review completed on 2026-10-29.
  Owner acceptance remains pending; see the peer-review record below.
- Test env note: the shell's `python` lacks Coga deps (tomlkit); tests were
  run with `.venv/bin/python`.
- Retirement debt: the source ticket's local branch `shebang-exec-check` still
  exists; this ticket now carries its fact, so retire can delete it.

## Peer review

Completed direct Codex review on 2026-11-02. Claude authored the implementation
(the implement handoff and original commit's Claude coauthor trailer agree).
This was an independent review of that implementation; Codex also applied and
self-reviewed the small correction below. No review tool or child agent was
started, and no review remains in flight.

Reviewed and pushed head: `fff3034d1911557da441664485c78bc7d71a136d`.
Reviewed diff base: `49907ab2fce16137f17fffedeefb318acdc33840`.

- Fixed one accuracy finding in both first-task copies: the Git-index
  fallback uses a **repo-local** `core.fileMode=false`. The implementation
  had dropped that qualifier from the old owning text. Confirmed against
  `validate._check_shebang_executables` (`git config --local`) and the existing
  global-fileMode and index-mode tests. Fix commit: `fff3034d1`.
- Re-reviewed the final three-file diff after the fix: scope, error severity,
  `--task` exclusion, remedies, mode sources, skip cases, knowledge ownership,
  twin identity, and all three changed link destinations/headings. No
  unresolved findings. No terminal or interactive surface changed; rendered
  Markdown was not previewed.
- PR #1139 remains open at `45a5636ec810411996b6007bad90cd4b59ac0255`.
  Its PR body and `v1/33-review-all-doc` blackboard record a completed Coga
  self-review on 2026-10-29; GitHub has no submitted reviews and owner
  acceptance is still pending. The requested review sequencing is satisfied
  by that completed review. A fresh trial merge is clean, and inspection of
  its first-task text confirms both changes survive with identical twins.
- Rebased onto fetched main before review; `git range-diff` confirmed the
  original patch was unchanged. Final fetches found no further main movement.
  The full suite below ran after the correction; an earlier pre-fix run was
  intentionally interrupted and is not a passing receipt.
- Pushed with an explicit lease against the old remote tip and returned to
  clean, current main before writing this handoff. The branch has two commits
  ahead of the reviewed base. Prepared `## PR` for the open-pr step.

## PR

```yaml
title: Document the non-executable-script validate check in coga/first-task
author: claude
author_evidence: Claude (Opus 5.5) authored the implementation, supported by the implement handoff and original commit's coauthor trailer. Codex restored the repo-local qualifier during peer review.
head: fff3034d1911557da441664485c78bc7d71a136d
base: 49907ab2fce16137f17fffedeefb318acdc33840
depth: skim
rationale: Bounded documentation change checked against the validator and existing tests, with the full suite passing and byte-identical twins. Skim the reviewer-authored qualifier correction and the PR 1139 coordination note; no runtime behavior changes.
implementation: Documents the non-executable-script error, scope, task-only exclusion, remedies, and mode sources in coga/first-task and its packaged twin. coga-dev/testing now summarizes and links while retaining developer guidance. Peer review restored the repo-local qualification on core.fileMode=false.
deviations: Implementation proceeded while PR 1139 was open. Peer review verified that its Coga review had already completed on 2026-10-29 and that a current trial merge is clean; owner acceptance remains pending. No scope expansion.
limitations: Rendered Markdown was not previewed; changed link targets and headings were checked directly. Tests ran on Linux/Python 3.12.12, with no fresh Python 3.11 or native Windows run. Codex self-reviewed its small qualifier correction; no second reviewer inspected that correction.
files:
  docs/contexts/coga/first-task/SKILL.md: Owns the user-facing non-executable-script rule, remedy, and mode sources.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: Packaged twin of coga/first-task, kept byte-identical.
  docs/contexts/coga-dev/testing/SKILL.md: Stops owning the user facts; summarizes, links, and keeps developer-only details.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: fff3034d1911557da441664485c78bc7d71a136d
  base: 49907ab2fce16137f17fffedeefb318acdc33840
  detail: Direct independent review of Claude's implementation completed. Fixed the missing repo-local qualifier, then re-reviewed the entire final diff against source, tests, ownership, links, and twins. Codex self-reviewed that small correction. No unresolved findings or review in flight.
checks:
  - command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m pytest -q
    status: passed
    head: fff3034d1911557da441664485c78bc7d71a136d
    base: 49907ab2fce16137f17fffedeefb318acdc33840
    detail: 4306 passed, 10 skipped in 530.34s on Linux/Python 3.12.12, after rebase and the review fix. Includes validator and packaging checks.
  - command: PYTHONPATH=/home/n/Code/claude/coga/src .venv/bin/python -m coga.cli validate --task document-the-non-executable-script-validate-check --json
    status: passed
    head: fff3034d1911557da441664485c78bc7d71a136d
    base: 49907ab2fce16137f17fffedeefb318acdc33840
    detail: One valid task, no issues or fixes, checked on the feature branch.
  - command: cmp docs/contexts/coga/first-task/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md
    status: passed
    head: fff3034d1911557da441664485c78bc7d71a136d
    base: 49907ab2fce16137f17fffedeefb318acdc33840
    detail: Byte-identical canonical and packaged first-task topics after the final fetch.
  - command: git diff --check origin/main...HEAD
    status: passed
    head: fff3034d1911557da441664485c78bc7d71a136d
    base: 49907ab2fce16137f17fffedeefb318acdc33840
    detail: No whitespace errors after the final fetch; main had not moved.
  - command: git merge-tree --write-tree origin/pr-1139 document-non-executable-script-check
    status: passed
    head: fff3034d1911557da441664485c78bc7d71a136d
    base: 49907ab2fce16137f17fffedeefb318acdc33840
    detail: Clean trial merge with PR 1139 at 45a5636ec810411996b6007bad90cd4b59ac0255; combined first-task text preserves both changes and matching twins.
```
