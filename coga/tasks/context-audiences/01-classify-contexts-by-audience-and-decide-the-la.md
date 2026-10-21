---
title: 01 Classify contexts by audience and decide the layout
status: in_progress
owner: nicktoper
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
step: 3 (report-to-coga)
agent: claude
---

## Description

Coga's context library mixes two audiences without saying so: topics for
**operating Coga in any adopting repo** (`coga/launch`, `coga/tickets`,
`coga/first-task`, ...) and topics for **developing Coga itself**
(`coga/codebase`, `coga/testing`, `coga/packaging`, most of
`coga/internals/*`, ...). Nearly all of them ship to every adopting repo as
packaged bootstrap contexts, and ticket authors can't tell which set to
attach. This ticket makes the product decisions. Sibling `02` executes them.

The agent drafts, and the owner finishes and approves, a decision record in
this group's `README.md` (`coga/tasks/context-audiences/README.md`):

1. **The audience criterion**, worded so it can go straight into the docs.
   Working wording: "does an agent or human in an adopting repo need this
   topic to operate Coga correctly?"
2. **A classification table** listing every topic under `docs/contexts/`
   (there are about 85 SKILL.md topics). Each row gives the ref, the audience
   (`user` or `coga-dev`), a one-line reason, and the shipped consumers that
   force `user` (prompt, source module, bundled skill/workflow) where there
   are any.
3. **Mixed topics** that must be split into a shipped part and a Coga-dev
   remainder, with the proposed cut for each.
4. **How the audience is expressed.** A namespace split is the leading
   candidate (e.g. keep `coga/*` and `dev/*` for users, move Coga-dev topics
   under a new namespace). Weigh it against a frontmatter field or test lists
   only. Record the target ref for every topic that moves.
5. **Compatibility.** The expected answer is a clean break (see Context).
   Confirm it, or record the concrete user-blocking reason for anything else.

No files under `docs/contexts/` or `src/` change in this ticket.

Done when the owner has approved the README decision record and it covers all
five points, with a table row for every topic under `docs/contexts/`.
`02` can then run from the README without reopening any product question.

## Context

### Classification is not "path prefix decides"

Shipped behavior points at some topics a naive reading would file as Coga-dev,
so those must stay `user`:

- The base prompt (`src/coga/resources/prompt.md`) tells every launched agent
  in every repo to read `dev/checkouts/launch-boundary` and
  `dev/checkouts/reconciliation` "from the configured contexts root or the
  bundled package".
- Core source strings cite `dev/checkouts`, `dev/checkout-cleanup` (and its
  `terminal-owners` / `branch-sweep` children), and `coga/codebase/gotchas`.
  Modules include `launch`, `open_pr`, `autoclose`, `branchsweep`,
  `branchcleanup`, `retire_worklist`, `config`, `step_gate`,
  `repl_supervisor`, `recurring_runner`. Re-grep rather than trusting this
  list. `coga/codebase/gotchas` is cited by `retire_worklist`, so it may need
  splitting out of `coga/codebase`.
- Bundled skills and workflows under
  `src/coga/resources/templates/coga/bootstrap/` run in adopting repos, e.g.
  `code/self-qa` cites `coga/testing` "Restricted sandboxes", and
  `code/implement` / `code/open-pr` / `code/self-qa` cite
  `coga/internals/pr-publication/preparation`. Some cite by GitHub URL
  (`https://github.com/FastJVM/coga/blob/main/docs/contexts/<ref>/SKILL.md`).

For each topic, grep the ref and its URL/path form across `src/`,
`docs/contexts/`, `coga/`, `tests/`, `README.md`, `AGENTS.md`. A citation from
something that ships means `user`, or a split.

Also: `docs/contexts/coga/manifesto/` is an empty directory with no SKILL.md.
Recommend removing it or classify it. `coga/current-direction` and
`coga/project-stage` are already local-only (`LOCAL_ONLY_CONTEXT_REFS` in
`tests/test_packaging.py`), so they are `coga-dev` by definition.

### Compatibility

`coga/project-stage` ("Compatibility is migration-only", "Code review") rules
out open-ended aliases and deprecation shims. The expected answer is a clean
break: renamed or de-packaged refs fail loud in adopting repos, and the release
notes name the renames.

### Where the result goes

The README is shared group material and isn't composed into either ticket's
prompt. `02` reads it explicitly. Write it for that reader: tables over prose,
and no rationale beyond one line per row.

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
implementation and evidence, never placeholders; coga/internals/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

## agent-produces (done)

Drafted all five parts of the decision record in
`coga/tasks/context-audiences/README.md`, originally covering 85 topics.

## report-to-coga (2026-10-20)

Final artifact: [approved decision record](README.md#decision-record) at
`coga/tasks/context-audiences/README.md`. The owner (nicktoper) approved it
on 2026-10-20 and advanced this ticket to the reporting step; all former
owner recommendations and weak-spot calls are confirmed as drafted.

Approved outcome: use `coga-dev/` for Coga development topics, keep user
topics under `coga/` and `dev/`, rename the six user topics out of
`coga/internals/`, and split the mixed topics as specified in the README.
`principles` and `patterns` are Coga-dev. Compatibility is a clean break
with release-note mappings, without aliases, redirects, or stub topics.

The owner's separate ownership relocation (commit `5c2caadca`) moved seven
former topics to their owning tickets or skills. The final inventory is
therefore 78 topics: 54 user, 19 Coga-dev, and 5 mixed. The README records
the destinations; 02 must not recreate those contexts. Maintainer skills
still ship; the ownership relocation did not decide to remove them.

Report-step edits corrected the README's stale comparison counts and
removed a resolved rename-approval qualifier. No product decision changed.
No files under `docs/contexts/` or `src/` changed in this step.

Verification: compared the classification rows with
`rg --files docs/contexts -g SKILL.md` using a Python set/count check:
78 topics, 78 rows, no missing, stale, or duplicate refs; all five decision
sections and the owner approval are present.
`coga validate --task context-audiences/01-classify-contexts-by-audience-and-decide-the-la --json`
passed (1 OK, no issues).

Handoff: ticket 02 implements the approved README, including the five cuts,
consumer/link updates, packaging checks, release notes, and empty manifesto
directory cleanup. The pending owner decisions from the draft are resolved.
