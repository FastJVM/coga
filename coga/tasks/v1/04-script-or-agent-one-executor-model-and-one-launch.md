---
title: 'Script or agent: one executor model and one launch loop'
status: active
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

Follow-up to the plain-Git ticket. Make script and agent two executors of one step model, deterministic by default, and collapse launch's three step loops and mode flags into one loop with callers. Owner finds the current script/ticket model unsatisfying; this ticket redesigns it.

Depends on `v1/03-use-git-like-everyone-remove-coga-s-publication-ab`: read
its "Target model" and "Owner decisions" first. That ticket removes Git
from the kernel; this one reshapes what remains of launch.

### Settled (owner, 2026-11-19)

- A ticket is a script, an agent, or text. Deterministic by default: an
  agent is called only for judgment. Rationale: a script computes once; an
  LLM recomputes the whole model per token, which is waste when it sits at
  the core of routine work (crons, opening PRs).
- The documented hybrid chaining in `coga/script-tickets` stays. A failure
  is not escalated inside the ticket: it becomes another ticket.

### Scope to design

- **One executor shape.** Script and agent present the same interface to
  the kernel: environment build (one isolation function instead of three
  scrub copies), spawn, exit normalization. Four `ticket.py` spawn sites with
  different primitives become one. Terminal/PTY and Windows specifics stay
  inside the agent executor.
- **One step loop.** Today there are three: `launch_script.run_script_chain`,
  `launch._LaunchInvocation._supervise_steps`, megalaunch
  `_launch_until_stop`. Megalaunch has no script phase at all (a ticket with
  `ticket.py` gets an agent there). "Step unchanged" means "agent continues"
  after a script and "failure" after an agent in megalaunch; pick one rule.
- **Modes become callers, not flags.** `_launch` takes 16 mode parameters
  (`prompt_report`, `recurring_authorized`, `direct_chat`,
  `require_agent_target`, `before_recompose`...). Chat, recurring,
  megalaunch, prompt-report and read-only dispatch call the loop instead.
  Recurring delegation's double `_launch` with an exception-driven restart
  goes.
- **One `in_progress` writer** instead of four; operator derived once per
  step instead of ~15 times per launch.
- **Agent session end: the session ends itself, explicitly** (owner,
  2026-11-19). The supervisor passes the agent's PID (`COGA_AGENT_PID`).
  `mark`, `bump` and `block` only write the ticket and know nothing about
  sessions, because a `coga chat` or coordinator session changes other
  tickets without ending. When the agent has finished its step it runs
  `coga exit`, which SIGTERMs that PID (name confirmed by the owner; `suicide` rejected
  for a public CLI and because it trips model safety behavior). An agent
  that forgets leaves the session open until the human or the idle limit
  closes it; that costs time, not tokens. The supervisor only
  spawns, waits, then re-reads the ticket to decide what follows (status or
  step changed: chain; otherwise normal exit or crash), plus idle and
  max-session limits. Drop the done sentinel, its file watching, the
  session-id environment plumbing (`COGA_DONE_SENTINEL`, `EXPECTED_*`), the
  terminal-status probe, the deferred done marker and `.pending-<pid>`. A
  `<END>` stdout marker was rejected: tool output is captured by the agent
  CLI, rendered with escapes, prone to false positives, and invisible on
  Windows. To verify: whether Codex's Linux sandbox allows signalling a
  process outside it (fallback: print "step finished, exit the session" and
  let the human or idle timeout end it); TTY reset after a kill already
  exists (`_TTY_SANITIZE`); on Windows `os.kill` terminates the process.
- **Dead code**: `_prospective_assist_ticket` (no references), unreachable
  returns, forwarders.

### Open question

- Owner is unsure whether Git helpers belong as workflow **steps** (they
  then live in workflow markdown) or elsewhere; settle together with the
  plain-Git ticket.

The full launch audit is in the plain-Git ticket's Production notes.

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

The blackboard is a notepad to be written to often as the human and agent works through a task.
