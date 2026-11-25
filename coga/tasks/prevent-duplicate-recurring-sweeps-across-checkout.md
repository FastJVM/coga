---
title: Prevent duplicate recurring sweeps across checkouts of the same repo
status: draft
owner: nicktoper
workflow: null
---

## Description

### What broke

Two checkouts of the same repo (magicator2: `~/Code/claude/magicator2` and `~/Code/codex/magicator2`) each ran `coga recurring` on 2026-11-23, and both serviced period 2026-W48 for every template. Nothing stopped the second sweep:

- 13:32–13:47 — sweep in the `claude/` checkout services W48 (Dream opens PRs #1057–#1063). Its `coga/log.md` is not pushed.
- 13:48 — sweep in the `codex/` checkout reads its own `coga/log.md`, finds no W48 serviced lines, and fires everything again: a duplicate Dream run, a second `rebase-stale-worktrees` run, and duplicate script runs for `skill-update` and `blocker-reminders`.
- 15:12 — a third firing recreates `recurring/dream` and `recurring/rebase-stale-worktrees` for W48.

The second `rebase-stale-worktrees` run force-pushed magicator2 PR #1055 (`91e032f7b`→`cb660d112`). The other checkout had that branch checked out with uncommitted changes at the time. A duplicate sweep is not just wasted work: it can force-push under another checkout's work.

### Cause

Period dedup reads only the checkout-local working-tree log. `serviced_periods` / `read_serviced_ledger` and `_period_already_serviced` (`src/coga/recurring.py`, around lines 2317 and 2464) consult `cfg`'s `coga/log.md` and nothing else. No lock is shared across checkouts, and origin's log is never read. Any two checkouts whose logs have diverged (unpushed, or not pulled) will both consider the period unserviced. The sweep is started by hand (no cron), so this happens whenever the operator runs `coga recurring` in more than one checkout in the same period.

### Design options (not decided)

1. A machine-local, cross-checkout lock plus serviced ledger keyed by the repo's committed UUID, stored outside the checkout. It would have stopped this incident. It does not cover two machines, and it puts coga state outside the repo, which coga avoids by design (see `v1/no-weird-state-in-personal-dir`).
2. Fetch, then union `origin/<control>:coga/log.md` with the local log before deciding. This fits "state lives in git", but it only works if every sweep pushes its serviced lines immediately. It would not have caught this case, because the first sweep's log was unpushed.
3. Both, with the sweep pushing its log as soon as it finishes.

A rebase/force-push guard is also worth considering: refuse to force-push a branch that is checked out in another local checkout (`git worktree list` would not see a separate clone, so this needs another signal).

### Done means

- A second `coga recurring` in another checkout of the same repo, within the same period, skips templates already serviced elsewhere, or refuses with a clear reason.
- A regression test covers two checkouts with diverged logs.
- The chosen design and its limits (single machine vs. multiple machines) are written into the recurring topic.

Workaround in magicator2: draft PR #1064 (`decide-which-checkout-owns-the-weekly-recurring-sw`) picks one checkout to own the sweep.

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

The blackboard is a notepad to be written to often as the human and agent works through a task.
