---
title: no weird state in personal dir
status: draft
owner: nicktoper
workflow: null
---

## Description

Agents and the scripts they write keep run state outside the repo when they
need somewhere unversioned to put it: `~/.local/state/<tool>`, `$XDG_STATE_HOME`,
`/tmp/...`, `~/.codex/...`, or a sibling directory such as
`~/Code/<repo>-validation`. That state is invisible, unshared and unbacked, and
outlives the repo that made it. Coga must own this: a ticket or script that
needs unversioned state gets a Coga-managed place inside the repo, and nothing
else.

### Requirements

- **One managed place.** Coga provides a git-ignored, repo-local directory for
  unversioned state (keys, run records, traces, evidence, caches), created and
  ignored by `coga init`, beside today's `.coga/`. The exact path is a design
  decision for this ticket.
- **Handed to every executor.** Launch exposes it to agents and script phases
  (for example an environment variable), and the base prompt says to use it
  for anything unversioned.
- **The rule, stated once.** Nothing a launch runs writes to the user's home
  (`~/.local`, `$XDG_*`, `~/.<agent>`), to `/tmp`, to a sibling directory, or to
  external storage, unless the owner explicitly allows it. The agent's own
  session files (`~/.claude`, `~/.codex`) are the agent CLI's business, not
  this rule's.
- **Visible.** The managed directory's size and contents are discoverable
  (`coga status` or `coga validate` reports it), so state is never silently
  lost or forgotten.

### Context

Found in `manycore-com/magicator2` and `manycore-com/fastci` on 2026-11-21. An
agent-written `scripts/aws-bench.sh` (magicator2 `5850817c4`, 2026-11-06) kept
benchmark keys and evidence under `~/.local/state/magicator-bench`. Other runs
used `~/.codex/magicator-bench-state`, `/tmp/...` and
`~/Code/fastci-sota1-validation`, about 17 GB of research evidence in all. It
was all moved by hand into each repo's ignored `data/`, and the repos now state
the rule in `coga/context.md`. Coga should make that the default instead of a
per-repo rule.

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
