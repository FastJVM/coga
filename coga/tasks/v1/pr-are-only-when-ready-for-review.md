---
title: Open PRs only when ready for review in magicator
status: draft
owner: nicktoper
workflow: docs/with-review
---

## Description

Agents working in the **magicator** repo (`/home/n/Code/magicator`) open
draft PRs early, as living status and for intermediate checkpoints. This
leaves open PRs that the owner has nothing to review. One example is
magicator #980, which stayed open during a `validate` step. Coga's posture
is different: in-progress state lives on the pushed branch plus the ticket's
`## Dev` record and blackboard, and a PR is opened only when the work is
ready to merge and needs a human review (the `open-pr` / `review` steps).
Magicator's repo guidance was never updated to match that posture, so the
problem is a stale Coga adoption. Rewrite magicator's guidance so that agents
keep unfinished work on a branch and open a PR only when it is ready for
human review.

Done means that, on magicator's `main`, no repo guidance tells an agent to
open a PR before the work is merge-ready and owner-reviewable. The remaining
guidance says where status lives instead (pushed branch + ticket blackboard,
or the final chat handoff for ticket-less sessions). The change lands as a
magicator PR that the owner reviews.

## Context

### What to change in magicator (diagnosed 2026-11-11)

- `AGENTS.md`, section **"Draft PR as Status"**:
  - Rule 2 says to create the draft PR early as living status.
  - Rule 3 says to create or update the draft PR before every handoff.
  - Rule 5 says to keep it as a draft.
  - Rewrite these rules. Keep the stated reason ("the user may shut down the
    agent at any point; another agent must be able to pick up"), and satisfy
    it with the pushed branch plus the blackboard rather than a PR.
- The subsection **"The one exception: when publication itself is
  unsafe"** in the same section refers to "rules 3–5" and to
  `coga/contexts/repo/coga-state-commits`. Keep that exception coherent with
  the renumbered or rewritten rules.
- The **branches-only rule** at the top of that section (no linked worktrees,
  no fallback clones) is unrelated and stays. It also constrains you: work on
  an ordinary branch in magicator's primary checkout, not in a worktree.
- `CONTRIBUTING.md`, "PR Scope and Workflow":
  - Rule 2 calls for a "docs checkpoint PR first".
  - Rules 3–5 and 7 call for an early draft PR as living status, kept as a
    draft until a reviewer asks otherwise.
  - Align these with the same posture. Keep "one architectural concern per
    PR" and the checkpoint-doc idea where it doesn't require an unready PR.
- Check and fix if needed:
  - `coga/contexts/repo/recurring-runs/SKILL.md`, which mentions updating
    "the same draft PR".
  - `coga/workflows/skill-update/run.md`, where the skill update lands in one
    draft PR. That PR is merge-ready by design, so it is probably fine; say
    so either way.
- Already aligned, use as the model wording: `coga/workflows/research/
  measured-experiment.md` ("Keep unfinished work on the pushed branch; do not
  open a draft PR for it").
- Search the rest of magicator's `coga/` and `docs/` (excluding archives)
  for "draft PR" / "checkpoint PR" / "living status" before declaring done.

### How this ticket runs

- The ticket lives in the Coga repo, but every edit and the PR are in
  magicator. Run git and `gh` from `/home/n/Code/magicator`. Record the
  magicator branch and PR URL under this ticket's `## Dev`; the
  `requires: branch` / `requires: pr` gates read only the blackboard.
  Coga's `open-pr` helper targets the Coga repo, so open the magicator PR
  with `gh pr create` from the magicator checkout. Follow magicator's own PR
  conventions.
- Do not open the magicator PR before the `open-pr` step. This ticket must
  follow the rule it introduces.
- Leave magicator's Coga state (its `coga/tasks`, `coga/log.md`) untouched.

### Out of scope

- Coga's own packaged workflows, skills, and PR-publication contexts. The
  sibling ticket `open-prs-only-when-ready-to-merge-and-needing-huma` covers
  those, including how `requires: pr`, autoclose, and the human-assist path
  behave without early PRs.
- solarmonero: no early-PR guidance was found there; the owner suspects the
  reported case was their own mistake.

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

## Evaluator review

- **Duplicate / wrong home.** Magicator already has a draft for this exact work: `magicator/coga/tasks/repo-maintenance/open-prs-only-when-ready-to-merge.md` (created 2026-11-10, same owner). The Coga ticket never mentions it, so a launched agent would duplicate it.
- **Clarity / done:** clear enough to start cold; done is checkable (grep magicator main + PR exists). Vague: "where status lives instead", and what happens to the existing magicator ticket.
- **docs/with-review in the cross-repo shape will misbehave:**
  - implement: `coga launch` reserves a branch in the *Coga* checkout and writes `branch:` into `## Dev` itself (`checkouts.insert_branch_line`), colliding with the plan to record the magicator branch there.
  - peer-review / open-pr: launch re-checks out the recorded branch in the Coga repo — with a magicator branch name it fails, or `git diff main...HEAD` diffs the wrong repo.
  - open-pr: the workflow forbids hand-running `gh pr create` without explicit human approval; the ticket instructs exactly that.
  - peer-review's "cross-copy sync" checklist is Coga-specific.
  - autoclose: `gh pr view <url>` works cross-repo, but branch disposal judges the branch in the Coga repo.
  - Fix: run from the magicator ticket; or, if it must stay in Coga, use a direct/manual flow with no `requires:` gates.
- **Accuracy:** AGENTS.md rules 2/3/5, the exception citing "rules 3–5" and `coga-state-commits`, CONTRIBUTING rules 2–5/7 — accurate. `measured-experiment.md` is only partly aligned (line 46 ok; line ~205 "Push/update the draft", ~216 "AGENTS.md keeps the PR draft") — poor model wording. Missed: `coga/contexts/repo/coga-state-commits/SKILL.md` (~171, "AGENTS.md's draft-PR requirement"); `coga/recurring/skill-update/ticket.md` (~28, "one draft PR" — from Coga's `coga skill update --pr`, sibling Coga ticket's scope). #980 is now merged.
- **Contexts:** cite magicator `repo/coga-state-commits`; `coga/checkouts` if it stays cross-repo.
- **Scope:** fine as one PR, no split.
- **Assumptions:** magicator's primary checkout is on `codex/keycloak-mutant-oracle-pilot` with a dirty ticket — branches-only rule means this work interrupts it. "Leave magicator's Coga state untouched" conflicts with the existing magicator ticket. Should the publication exception narrow/expire? Does the sibling Coga ticket need to land first?
- **Prompt size:** task_context 43% is mostly the mandatory guide comment; only real trim is "How this ticket runs" (~150 tokens) if the work moves to magicator.

## Disposition (2026-11-11)

Owner chose to cancel this ticket as a duplicate. Magicator's guidance is
handled by magicator's `coga/tasks/repo-maintenance/open-prs-only-when-ready-to-merge.md`,
and the evaluator's extra findings were added to that ticket's `## Context`. Coga's
packaged side is handled by `open-prs-only-when-ready-to-merge-and-needing-huma`.
