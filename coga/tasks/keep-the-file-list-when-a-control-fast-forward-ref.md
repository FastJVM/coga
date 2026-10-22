---
title: Keep the file list when a control fast-forward refuses over local changes
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
step: 3 (open-pr)
agent: claude
launch_generation: 0c250d6f-d1bd-4e58-acf5-225f8e41218d
---

## Description

During `coga recurring --all` on 2026-10-22, the multiply clone failed with `[git] note: local 'main' in /home/n/Code/multiply not fast-forwarded: error: Your local changes to the following files would be overwritten by merge:` and then nothing: the note never named the file (it was `coga/log.md`). Cause, verified: `summarize_git_failure` in `src/coga/git.py` keeps only `error:`/`fatal:`/`CONFLICT` lines, and git prints the blocking paths on the following tab-indented lines, so they are discarded. Keep those path lines (bounded, e.g. first N plus a count) so the operator can see what blocks the fast-forward without running git by hand. Add a test covering git's 'would be overwritten by merge' and 'untracked working tree files would be overwritten' outputs.

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

## Dev

branch: coga/keep-control-fast-forward-paths

## Implement handoff

- Original implementation: Codex launch `cdea37f1-2c2b-4096-bbe0-dbf19effc106`,
  pushed as `af0423e0fc106d70b2f684892a0c14d21c3b942d` before review rebases.
  The configured Claude agent did not implement this change.
- Before the implementation fix, the focused selection reproduced the missing
  path with 9 failures and 2 passes; after the fix, 11 passed. Both original
  full-suite runs passed with 3996 passed and 7 Windows-only skips. These are
  historical results; the final revision's receipts are under `## PR` below.

## Peer review

- **Completed** direct Codex review in launch
  `8c655e81-195c-4cfc-8d17-107faa799647`. Final reviewed head:
  `fc07de3b7cd9b55b1c621087a2cabaa640075199`; diff base:
  `64c008fc2fa80a9f978cfb2f47af9779d6596c37`. Read the entire four-file diff, the
  shared summary's callers, and the owning state-publication contract.
  Recorded as **self-review** because Codex also authored the implementation
  and review fix; the configured peer is not evidence of independence.
- Fixed one correctness finding in `fc07de3b7`: Git emits
  filename spaces literally, but stripping path lines changed filenames and
  let a whitespace-only name end collection, hiding all following paths.
  The parser now removes only Git's indentation tab. Added regression cases
  for both overwrite headings and updated the canonical/packaged contract.
- Red/green proof before the final rebase:
  `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_git.py -k summarize_git_failure_keeps_overwrite_paths -q`
  failed with 2 failed, 232 deselected before the fix;
  `PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest tests/test_git.py -k 'summarize_git_failure or fast_forward_names_files' -q`
  then passed with 11 passed, 223 deselected. An initial suite was interrupted
  when this finding surfaced. The complete replacement suite passed with
  3996 passed, 7 skipped in 383.12s before the final rebase.
- Freshened the branch twice as main advanced only in ticket/log state;
  both rebases were clean. Re-reviewed the final diff and reran the full suite
  on the final committed head: **3996 passed, 7 skipped in 375.58s**. Earlier
  results above are historical, not re-stamped as final verification.
  The final freshness fetch found only further updates to the unrelated
  `blocks/08-trim-launch-prompt-and-workflow-topics` ticket and the log.
  Inspected those deltas; the publisher's freshness check passed with
  `state-only-drift`, preserving this exact tested and reviewed head/base.
- Drove the actual stderr emitter using real Git refusals in a PTY at
  **80x24 and 40x12**. At each size checked tracked, untracked, mixed lists
  of 12 tracked plus 12 untracked files, and filenames with surrounding or
  only spaces. The notes named `coga/log.md`, kept both headings and ten paths
  per list, reported `(+2 more files)` for each longer list, and retained paths
  after the whitespace-only name. All eight cases preserved local file bytes
  and the main tip. Exact final commands are below.
- No unresolved must-fix findings. Advisory recommendation: **skim**.
  The branch is committed and pushed; this manual checkout is back on `main`.
  This session did not open a PR. The next workflow step owns publication.

## PR

```yaml
title: Keep blocking file lists in Git failure summaries
author: codex
author_evidence: Original implementation by Codex in launch cdea37f1-2c2b-4096-bbe0-dbf19effc106;
  review fix by Codex in launch 8c655e81-195c-4cfc-8d17-107faa799647. The configured Claude
  agent was not the implementer.
head: fc07de3b7cd9b55b1c621087a2cabaa640075199
base: 64c008fc2fa80a9f978cfb2f47af9779d6596c37
depth: skim
rationale: The change affects only diagnostics. Direct Codex self-review completed, the filename-whitespace
  finding is fixed, and the full suite and real terminal checks passed on the final revision.
  Skim for the disclosed self-review and platform limits.
implementation: Keep the first 10 tab-indented paths per overwrite refusal, preserving filename
  spaces and association with the error heading, and report the exact omitted count. Deduplicate
  complete messages while retaining different displayed file lists. Existing actionable-error
  filtering and the unknown-error fallback remain intact.
deviations: None. The review fix preserves the requested path list even when a filename contains
  only spaces.
limitations: Verified on Linux with Python 3.12.12. Seven Windows job-object and PowerShell
  checks were skipped; no Python 3.11 run was performed. Both implementation and review used
  Codex, so no independent review is claimed.
files:
  src/coga/git.py: Preserve bounded overwrite path lists, filename spaces, and their error headings
    in the shared summary.
  tests/test_git.py: Cover real tracked/untracked Git refusals, unchanged local state, whitespace,
    bounds, grouping, and deduplication.
  docs/contexts/coga/state-publication/SKILL.md: Document the operator-visible file-list and
    omitted-count contract.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md: Keep
    the packaged fallback byte-identical to its canonical topic.
review:
  reviewer: codex
  kind: self
  status: passed
  head: fc07de3b7cd9b55b1c621087a2cabaa640075199
  base: 64c008fc2fa80a9f978cfb2f47af9779d6596c37
  detail: 'Direct review completed on the final diff after fixes and rebase, including all four
    paths, shared callers, and owning contracts. One correctness finding fixed: stripping filename
    whitespace could drop the rest of the list. No unresolved must-fix findings.'
checks:
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python -m pytest > /tmp/coga-control-ff-peer-pytest-rebased.log
    2>&1
  status: passed
  head: fc07de3b7cd9b55b1c621087a2cabaa640075199
  base: 64c008fc2fa80a9f978cfb2f47af9779d6596c37
  detail: 3996 passed, 7 skipped in 375.58s. Full suite on the final committed head after rebase;
    Python 3.12.12. All seven skips require Windows.
- command: PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python /tmp/coga-control-ff-peer-smoke.py
  status: passed
  head: fc07de3b7cd9b55b1c621087a2cabaa640075199
  base: 64c008fc2fa80a9f978cfb2f47af9779d6596c37
  detail: 'Eight real-Git smoke cases in a PTY: tracked, untracked, mixed 12+12 bounded lists,
    and whitespace filenames at 80x24 and 40x12. Inspected stderr contained the expected paths
    and omitted counts; local bytes and main tip stayed unchanged. The disposable harness uses
    temporary repositories.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: fc07de3b7cd9b55b1c621087a2cabaa640075199
  base: 64c008fc2fa80a9f978cfb2f47af9779d6596c37
  detail: No whitespace errors in the committed feature diff.
- command: cmp docs/contexts/coga/state-publication/SKILL.md src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md
  status: passed
  head: fc07de3b7cd9b55b1c621087a2cabaa640075199
  base: 64c008fc2fa80a9f978cfb2f47af9779d6596c37
  detail: Canonical and packaged contexts are byte-identical.
- command: 'PYTHONPATH=/home/n/Code/codex/coga/src .venv/bin/python - <<''PY''

    from coga.github_preflight import check_branch_contains_control

    check = check_branch_contains_control(''origin'', ''main'', cwd=''/home/n/Code/codex/coga'',
    coga_root=''/home/n/Code/codex/coga/coga'', head=''refs/heads/coga/keep-control-fast-forward-paths'')

    print(check)

    assert check.ok

    PY'
  status: passed
  head: fc07de3b7cd9b55b1c621087a2cabaa640075199
  base: 64c008fc2fa80a9f978cfb2f47af9779d6596c37
  detail: The publication freshness gate passed. Main advanced only in an unrelated ticket and
    the log, with no overlap or material drift; the reviewed head and merge base remain unchanged.
- command: coga validate --json
  status: not-run
  detail: No configuration, validation, task-model, prompt-composition, or workflow behavior
    changed; the seeded fixture needed no update.
```
