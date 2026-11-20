---
title: 'Use Git like everyone: remove Coga''s publication abstraction'
status: in_progress
owner: nicktoper
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 1 (design)
agent: claude
---

## Description

Coga stops abstracting Git: no control branch, no automatic publication or sweep, no locks. Branch creation and PR become workflow script steps; the launch kernel no longer knows Git. Owner decisions from the 2026-11-19 chat are recorded below.

This is not the microkernel group: the microkernel decides where behavior
lives (kernel vs ticket); this ticket stops abstracting Git. It supersedes
the parts of `v1/microkernel/` and `v1/why-is-the-code-so-big` that move or
polish publication, checkout, sweep and claim machinery.

### Target model: three orthogonal layers

The new system separates three concerns that today's launch fuses. Each can
change without touching the others.

1. **The kernel runs tickets.** It reads the ticket once per step, picks the
   step's executor, runs it, and records status and step in the ticket file.
   That is all. It knows nothing about Git, branches, PRs, remotes or
   publication, and it takes no locks: the ticket's owner is its single
   writer.
2. **Executors decide how a step is computed.** A step is a **script**
   (`ticket.py`: deterministic, one computation, zero tokens), an **agent**
   (an LLM session, for judgment), or **text** for a human. Deterministic by
   default; call an agent only where judgment is needed. The documented
   hybrid (`coga/script-tickets` "Chaining": a script that leaves its step
   open hands it to the agent) stays. A failure is not repaired inside the
   ticket: it becomes another ticket. Script and agent present the same
   shape to the kernel (environment, spawn, exit status); Windows and
   terminal specifics stay inside the agent executor.
3. **Version control is plain Git, outside Coga.** Humans and agents use
   `git` as in any repo. Coga's files are ordinary files in the checkout:
   on a branch, the ticket's state travels with the code and reaches main
   through the PR. Branch and PR helpers exist only as workflow script steps
   (for example `open-branch` first, `push-and-open-pr` last); a workflow
   without them, such as a recurring job, simply commits where it runs, or
   not at all. Coga would work in a directory without Git. `coga/log.md` is
   append-only, so its conflicts resolve by keeping both sides.

Failure rule across all three layers: **stop simply**. When something is
not clean (a Git conflict, a failed push, a script error), stop, keep local
state, say what happened. Recovery is a human or agent act, never kernel
machinery.

Example workflow under this model:

    1. script  open-branch        git switch -c <ticket>
    2. agent   implement
    3. agent   review
    4. script  push-and-open-pr   git push; gh pr create

What disappears: the control branch, automatic publication and the
end-of-command sweep, `prepare-checkout`, per-step `checkout:` policy, claims, generations and leases, byte-guarded
publication and retraction, exit-75 threading, blocked re-parking, the
terminal-status probe and done sentinel (session ends itself), the
one-session-per-checkout guard, and `git.py`.

### Owner decisions (2026-11-19)

1. **Git like everyone.** No control branch, no automatic publication, no
   end-of-command sweep, no `prepare-checkout`. Launching a ticket creates
   (or reuses) its branch; work and ticket state live there; the end is a PR.
   Forgetting to push is the human's (or agent's) problem, as with any Git
   use. A `coga sync` command is probably unnecessary.
2. **Branch and PR are workflow steps**, e.g. a script step that opens the
   branch and a script step that pushes and opens the PR. The kernel does not
   know Git. Workflows without such steps (recurring, script-only, text)
   simply commit where they are, or not at all.
3. **The owner is the ticket's single writer: no locks.** Drop the megalaunch
   claim transaction (`pending/admitted/released` generations, held-child
   admission, released-witness reconciliation, byte re-checks), the recurring
   period lease, and `expect`-guarded ticket publication. A crash between
   status write and spawn "is not supposed to happen": the human relaunches.
4. **Fail-stop, no automatic recovery.** If a Git operation is not clean,
   stop, keep local state, say so. No retraction, no uncertain-push
   retention, no exit-75-plus-withheld-sweep threading.
5. **`coga/log.md` is append-only**: resolve its conflicts by keeping both
   sides (union). It is the one genuinely shared file.
6. **Launch never touches `blocked`.** A launch on a blocked ticket starts
   the session with the resolve preamble and leaves the status `blocked`;
   `coga unblock --answer` moves it to `in_progress` while a session runs. A
   session ending without an answer leaves it blocked: nothing to re-park.
   No `ticket.py` runs on a blocked ticket.
7. **One ticket read per step**, one environment-isolation function, Windows
   specifics confined to the agent executor (kept from today).
8. **A ticket is a script, an agent, or text (MD).** The documented hybrid
   chaining (`coga/script-tickets` "Chaining") stays. A failure does not
   escalate inside the ticket: make another ticket.
9. **Git is outside the kernel; `git.py` disappears.** Coga could in
   principle run without Git at all. Git helpers that speed things up are
   workflow steps (scripts), never kernel code. There is no `coga sync`
   command: syncing is `git pull` / `git push`. The `git-sync/` group (01 add
   `coga sync`, 02 automatic sync at session end, 03 shrink `git.py`) was
   canceled on 2026-11-19 as a trap that kept the two-destination model;
   03's goal is absorbed here as "delete `git.py`".
10. **The per-step `checkout:` field goes**, with `checkout_policy.py`,
    `checkouts.py` and launch's `_prepare_step_checkout`. Opening a branch
    is a command or script a workflow may use, never an obligation of the
    model. `v1/microkernel/18-retire-the-legacy-checkout-policy…` was
    canceled as moot.
11. **No one-session-per-checkout guard.** Drop the chat guard (the
    toplevel-keyed `flock`, chat receipt, `checkout_guard_scope`,
    `_orientation_checkout_guard`) and launch's "occupied checkout" checks.
    Two sessions in one checkout are the human's business, as with two
    editors on one repo. Session end no longer needs a per-checkout channel
    (see the script-or-agent ticket).

### Documentation

`coga-dev/principles` gained "Deterministic by default" and "Use tools
plainly" and a stop-simply clause in "Fail loud" on 2026-11-19, ahead of
implementation. Align the README with them in this ticket's implementation
PR, not before, so first users never read about behavior that does not
exist yet. Rewrite or delete the user topics that describe today's
publication model (`coga/checkouts`, `coga/state-publication`, `coga/sync`,
`coga/checkout-cleanup`, the base prompt's checkout and reconciliation
sections) in the same PR. Also fix the stale ticket ref in
`src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md`:
`v1/44-verify-the-macos-full-suite-procedure-on-the-ec` is now
`v1/11-verify-the-macos-full-suite-procedure-on-the-ec` (renumbered
2026-11-19).

### Open questions

- Branch/PR as a workflow **step** goes through the workflow markdown; is
  that the right home versus ticket-level behavior? (Owner unsure.)
- A separate effort will rework the script/ticket model itself (owner finds
  it unsatisfying). Not in this ticket's scope.

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

## Production notes

### Launch audit (2026-11-19, main at 470238016)

Read-only audit of `launch.py` and its satellites, done in an orient chat.
Line numbers are against that revision.

Size: launch machinery ~8,900 lines (`launch.py` 4,631; supervisors 1,730;
`compose.py` 891; `launch_script.py` 702; `claimed_session.py` 654). Git /
checkout modules ~10,900 (`git.py` 3,772; `autoclose.py` 1,842;
`branchsweep.py` 1,730; `checkouts.py` 1,198; `branchcleanup.py` 1,175;
`open_pr.py` 1,018).

`launch.py` by concern (overlapping): agent ~31%, Git/sync ~24%,
mode-specific (recurring, megalaunch, chat, prompt-report, read-only) ~17%,
lifecycle ~11%, script ~6%.

Findings:
- Script is a pre-phase of an agent loop; the in-loop re-run drops args,
  exit-75 handling, spawn refusal. Megalaunch has no script phase at all: a
  ticket with `ticket.py` gets an agent there.
- "Step unchanged" means "agent continues" after a script but "failure"
  after an agent in megalaunch.
- Three step loops (`run_script_chain`, `_supervise_steps`, megalaunch
  `_launch_until_stop`); four `ticket.py` spawn sites with different
  primitives; four `in_progress` flip implementations; three env-scrub copies.
- Seven distinct sync points; exit 75 + withheld sweep at ~27 sites.
- `_launch` has 16 mode parameters; `_manages_branch_checkout` is a 13-term
  exclusion. Recurring delegation runs `_launch` twice with an
  exception-driven restart. Private imports go both ways launch ↔
  recurring_runner and launch ↔ claimed_session.
- Ticket read ~12 times, operator derived ~15 times per launch.
- Dead code: `_prospective_assist_ticket` (no references), ~8 unreachable
  returns.

Guarantee families and their fate: (1) byte-guarded publication → plain
commit/push, fail-stop; (2) reload after sync → once per step; (3) env
isolation → kept; (4) claim/admission/lease → dropped (owner is single
writer); (5) blocked re-park → launch never touches blocked; (6) Windows →
kept in the agent executor.

### Next

- Re-evaluate every `v1/microkernel/` ticket and `v1/why-is-the-code-so-big`
  against these decisions; drop what this ticket supersedes (owner request,
  2026-11-19).
