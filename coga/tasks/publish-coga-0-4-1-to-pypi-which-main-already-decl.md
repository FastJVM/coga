---
title: Publish coga 0.4.1 to PyPI, which main already declares
status: done
owner: nicktoper
workflow:
  name: brief-for-human
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: owner
  - name: verify-read-only
    skills: []
    assignee: agent
agent: claude
---

## Description

Filed by Dream 2026-W43 (recurring/dream, Phase 6; Retro unshipped scope from marketing/fix-installer/release-0-4-1-so-new-context-files-publish, deleted in Retro PR #1058). pyproject.toml on main says 0.4.1, but PyPI's latest is 0.4.0 and origin has only the v0.4.0 tag: only the version bump landed. Still owed from the source ticket's Done criteria: TestPyPI dry run, the pre-tag gate on the merged main commit, owner publication of the tag/release, and the post-PyPI clean-install plus attended coga build vision-file check. Owner action (credentials and release are the owner's). coga/releasing owns the procedure; #1058 records the gap there.

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

## Brief (2026-10-21, brief-and-hand-off)

Ticket premise is stale: 0.4.1 is already published.
- Tag `v0.4.1` on origin -> 370ee83d9 (merge of PR #1075, 2026-10-20), an ancestor of main.
- GitHub Release `v0.4.1` published 2026-10-21T04:28Z; Release workflow run 39544218627 succeeded.
- PyPI JSON lists 0.4.1 as latest. TestPyPI JSON returned no release listing (dry run probably skipped; moot now).
- No receipt found for the pre-tag gate on 370ee83d9; it can no longer gate the upload.

Still owed (owner, from coga/releasing "Real release" step 5 + "Clean first-install gate"):
1. Fresh-venv PyPI check: `python3.11 -m venv <dir>`; `<dir>/bin/python -m pip install --no-cache-dir --index-url https://pypi.org/simple coga==0.4.1`; `<dir>/bin/coga --version` -> 0.4.1.
2. Clean-install release continuation: `COGA_CLEAN_INSTALL_VERSION=0.4.1 ./scripts/clean-install/run.sh pypi release-041 installer`, authenticate agent in container, then `docker exec -it release-041 coga-clean-install release claude`. Done when `release-passed.txt` exists; keep receipts.
3. Attended `coga build` vision-file check against the installed 0.4.1 (source ticket's Done criterion).
4. Optional: in that run, confirm the new context files the release was for are present in the installed package.

Irreversible action: none left (the PyPI upload already happened). If a check fails, the remedy is a yank and a 0.4.2, not a re-upload.
Agent-run checks (2026-10-21, at owner's request; scratchpad only):
- PyPI wheel coga-0.4.1-py3-none-any.whl: `coga/` and `coga_edge/` byte-identical to `git archive v0.4.1 src` (257 files, 77 packaged context SKILL.md). New context files shipped.
- Fresh python3.11 venv, `pip install --no-cache-dir --index-url https://pypi.org/simple coga==0.4.1`: `coga --version` -> 0.4.1; `coga init --user tester` exit 0; `coga validate --json` exit 0, 0 issues. Items 1 and 4 done.
- Finding: a bare `SLACK_WEBHOOK_URL` in the operator shell makes 0.4.1 refuse (intended fail-loud change); rerun with it unset.
- Items 2 and 3 not run: both launch an interactive, authenticated agent (`coga build` = `coga launch coga-build`), which an agent launch must not nest.

Done check (verify-read-only): fresh-install output shows 0.4.1; release-passed.txt and receipts exist; vision-file check outcome recorded here.
