---
title: Redesign Coga's git sync around explicit session-end publication
status: draft
owner: nicktoper
contexts:
  - coga-dev/principles
workflow: code/design-then-implement
---

## Description

Coga publishes state automatically. Lifecycle commands publish their own
writes, and after most state-changing commands an end-of-command sweep
(`git.sync_coga_state`, called from `cli.py` and `launch.py`) commits and pushes
every dirty eligible file under the Coga and contexts roots. On the control
checkout that includes definition edits (workflows, skills, contexts,
recurring definitions), so an unfinished or stock copy of a definition can land
on control before the user meant it to. This surfaced while designing
`v1/microkernel/05-make-packaged-behavior-discoverable-and-editable`: a fork
command would publish a byte-identical override that silently stops following
package updates. The broader problem is that `src/coga/git.py` has grown into
one very large module (thousands of lines) that keeps producing small
synchronization bugs.

Replace implicit publication with "normal Git" and one explicit, simple
command that both humans and agents can call:

- **`coga sync` is the only publication path.** It commits the Coga state
  directory (`coga/`, plus the contexts root if configured outside it), pulls
  and rebases onto main, pushes that state to main, and rebases the rest of
  the current branch onto main.
- **No command publishes implicitly**, transitions included. `bump`, `block`,
  `mark`, `create`, launch audit lines and the rest only write to the checkout.
  Their changes reach other checkouts when someone (human, agent, or the
  session end) runs `coga sync`. The per-command sweep and per-transition
  publication are removed.
- **State goes to main from any checkout.** On a feature checkout, `coga sync`
  still pushes `coga/` state directly to main while code stays on the branch
  and is rebased. The current held-for-merge behavior is dropped.

Done means: a merged PR in which `coga sync` behaves as above, the sweep and
implicit publication are gone, git-sync code is substantially smaller and
simpler than today, tests cover the new contract, and the owning topics
(`coga/state-publication`, `coga/sync`, `coga/checkouts`) describe the new
model.

## Context

### Decisions already made (owner, 2026-11-17)

- Publication is explicit everywhere: lifecycle transitions do **not**
  auto-publish either. The owner accepted this over keeping transitions as
  internal callers of `coga sync`.
- Feature checkouts push Coga state straight to main; held-for-merge goes away.
- One ticket covers design and implementation (`code/design-then-implement`).

### What the design step must resolve

Without implicit publication, every guarantee the sweep provides today has to
be re-homed or deliberately dropped. Address each one explicitly in the spec:

- **Lifecycle visibility and notifications**: other checkouts and the Slack
  notifier currently see transitions immediately. Decide when they become
  visible now (at `coga sync`) and whether notifications fire on the local
  write or on publication.
- **Unattended and launched sessions**: no human is present to run sync.
  The likely home is that the `coga launch` supervisor (and the megalaunch /
  recurring runners) run `coga sync` at session end, after the agent's
  `bump`/`block`/`mark`. Agent step skills may also call it. Note that
  `bump` ends a launched session, so the agent cannot sync after bumping
  itself.
- **Launch audit lines** in `coga/log.md`.
- **Megalaunch / recurring admission and chaining across clones**: claims
  such as `launch_generation` rely on prompt publication to avoid double
  admission.
- **Failed push / conflict**: retry and recovery behavior for `coga sync`,
  including rebase conflicts in `coga/` and in code.
- **Pre-launch sync**: `launch.py` currently syncs before launching
  ("Sync coga state before launch"); decide whether launch pulls only.
- **Definition edits**: under the new model a forked or stock definition is
  published only when someone explicitly syncs. Confirm whether `coga sync`
  needs any guard here or whether explicitness is enough.

### Code pointers (symbols, not line numbers)

- `git.sync_coga_state`: the end-of-command sweep. Called from `cli.py` (the
  post-command hook) and twice from `launch.py`.
- `git.sync_task_state` and `git.publish`: lifecycle publication paths.
- `publish_state.py` and `log_publication.py`: publication of state and
  audit-log files.
- Held-for-merge handling lives in `git.py`.
- `src/coga/git.py` is the main simplification target. Splitting what stays
  into small focused modules is in scope; respect the microkernel rule in
  `AGENTS.md`.

### Topics to edit (cited, not attached)

These are edited by this ticket, so they are read directly rather than
composed into the prompt. Update them in the same PR:

- `coga/state-publication`:
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/state-publication/SKILL.md`
- `coga/sync`:
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/sync/SKILL.md`
- `coga/checkouts` (including its `reconciliation` child), under
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/checkouts/`

Also check the step skills and the base prompt's "Reconcile before
publishing" text, which assume the current model.

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

## Evaluator review

**Clarity to start: mostly yes.** Motivation, the three-part target model, owner decisions, and the guarantee checklist are clear. Verified claims hold: `git.py` is 3772 lines; `sync_coga_state` called from `cli.py:218` and `launch.py:3104`/`3172` ("Sync coga state before launch"); held-for-merge logic lives in `git.py`. Gaps:
- **`coga sync` does not exist today.** No `sync` command in `cli.py`/`commands/`. The ticket reads as if it does. State it's a new command, and require the design to justify its core placement under the microkernel rule in `AGENTS.md` (Typer command vs `runner.RECIPES` vs alias).
- **Caller inventory is understated.** ~20 modules call `sync_task_state`/`publish`/`sync_coga_state`: `megalaunch.py`, `bump.py`, `mark.py`, `commands/{create,delete,owner,unblock,recurring}.py`, `branchsweep.py`, `recurring_runner.py`, `recurring_autofix.py`, `blocker_reminders.py`, `checkouts.py`, `github_preflight.py`, `notification/__init__.py`, `bootstrap/retire/ticket.py`. Name them or tell the agent to grep — the inventory is part of the design.
- **Reverses a deliberate invariant without saying so.** `coga/sync` currently states Git publication happens "without committing on a local branch, stashing, or rebasing." The new model rebases. Call that out.

**Done criteria: partly judgeable.** "Substantially smaller and simpler" is subjective — give a measurable target (e.g. `git.py` line ceiling, or named modules/functions deleted). Done omits `prompt.md` "Reconcile before publishing", `prompt-ticket.md`, and step skills, which Context mentions but Done doesn't require.

**Workflow fit: good.** `code/design-then-implement` matches "one ticket covers design and implementation." Requires two configured agents (main + peer) — confirm.

**Contexts.** `coga-dev/principles` is relevant (~26% of prompt). Missing: `coga-dev/internals/state-publication` (~2.25k words) and `coga-dev/patterns` (~600 words, state-changing-command rule) — `coga/sync` routes to both; cite at minimum. Also cite `coga-dev/microkernel` for the new-command placement decision. The cite-not-attach for edited topics is correctly justified by "edited by this ticket," not by tokens — no cite quotes a size.

**Scope: large.** ~12k words of topics (state-publication, launch-boundaries, checkouts + 4 children), ~20 callers, prompts, skills, tests (`test_git.py` has 220 tests). Consider letting the design step decide a split: (a) add `coga sync` + remove implicit publication, (b) launch/megalaunch/recurring session-end sync + admission claims, (c) `git.py` shrink/split.

**Assumptions to question before launch.**
- "Rebases the rest of the current branch onto main" implies force-push for any branch with a pushed PR. Should `coga sync` force-push? What about uncommitted code changes?
- Pushing `coga/` to main from a feature checkout requires a commit not on the branch (or a split). What happens to `coga/` commits already on the branch?
- Protected/unreachable control remotes (the config comment at `coga.toml:151`): direct pushes to main from any checkout need a policy.
- `bump` ends a launched session, so session-end sync must be supervisor-owned — specify what happens if the supervisor crashes before syncing.
- `launch_generation` admission races are now open until sync. Should the claim alone keep an atomic publish? That exception should be explicitly ruled by the owner.
- Check `coga/recurring/scheduling/inactivity` "Sync coga state" prefix rules, since commit subjects change.

**Prompt size.** No layer exceeds 40% of ~4976 tokens. Largest is `coga-dev/principles` at 1317 (26%).
