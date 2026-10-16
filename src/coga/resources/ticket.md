## Description

{description}

## Context

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
These are explanations and examples, not values to copy into every ticket.
Omit optional fields and sections until needed. Preserve existing metadata,
field order, and formatting; write YAML lists one item per line.
Ordinary agents may edit contexts, body prose, and the blackboard. Other
frontmatter belongs to CLI commands and humans unless a specialized authoring
skill explicitly grants an exception. Never edit the CLI-written coga/log.md.

BODY AND WORKING MEMORY
Description: what needs to happen, why, and what counts as done.
Context: facts, constraints, and code pointers. Cite module plus symbol,
explain the relationship that matters, and use line numbers only as an aid.
Copy the substance of a cited ticket here; its path may later be retired.
Only Description, Context (including this guide), and the live blackboard
reach the launch prompt. Use ### subheadings inside these body sections;
another ## heading above the fence would put requirements outside the prompt.
The single-line HTML comment containing coga:blackboard separates the body
from working memory. Keep exactly one such fence; even one inside a code block counts.

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
values live below the # --- extensions --- marker in the YAML header. Preserve
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

Optional ## PR: one fenced YAML mapping for PR preparation. These fields record
actual implementation and evidence; placeholders are not receipts. Use full
commit OIDs for head/base, and keep each check/review tied to the revision it
actually examined. Omit receipt head/base only when status is not-run.

    title: <change title>
    author: <actual implementing agent, or unknown>
    author_evidence: <session or tool evidence for authorship>
    head: <full feature commit OID>
    base: <full reviewed merge-base OID>
    depth: deep                            # Advisory review depth: merge, skim, or deep.
    rationale: <why this review depth fits>
    implementation: <what changed and why>
    deviations: <departures from the ticket, or none>
    limitations: <remaining risks or verification gaps, or none>
    files:
      path/to/file: <why this path belongs; cover every diff path, both names of a rename>
    review:
      reviewer: <actual reviewing agent, or none>
      kind: independent                    # independent, self, or none; never infer independent review.
      status: passed                       # passed, failed, pending, or not-run.
      head: <full reviewed feature commit OID>
      base: <full reviewed merge-base OID>
      detail: <result or reason for omission>
    checks:
      - command: <actual command>
        status: passed                     # Same status choices as review.
        head: <full tested feature commit OID>
        base: <full tested merge-base OID>
        detail: <result and counts>

Use merge only with passed independent review and applicable checks, skim for
a bounded change with explained tradeoffs, and deep for unresolved or missing
evidence. The publishing workflow applies the detailed review requirements.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

When a design changes, rewrite the body for current work and append the old plan
under one ## Superseded designs section, with dated ### entries, Superseded by:
and Reason: lines, and copied headings at #### or deeper. Only a pointer to
that history reaches launch; keep the current rationale in live text.

Before launching a draft, fold durable Evaluator review, Proposals, and Ticket
authoring notes into the body. Preserve superseded designs and reset remaining
scratch to the stock blackboard placeholder. An explicit ## Production notes
section marks intentional launch material to retain, exempting it from that
readiness check. During an existing task, preserve unrelated working notes and
live workflow reviews; remove only the authoring scratch you have incorporated.
For oversized live notes, move dated evidence into sibling attachments and
leave same-heading pointers. Keep current handoff and verification, along with
the ## Dev and ## Blockers sections, in place. Do not trim done tickets or
recurring sections another writer replaces; route those to their owner.

RECURRING PARENTS ONLY (coga/recurring/<name>/ticket.md)
These are template settings, not fields to add to an ordinary ticket:

    schedule: "0 9 * * 1"                  # Required five-field cron.
    schedule_comment: Every Monday at nine # Optional human annotation; no scheduling effect.
    scope: repo                           # Optional: repo (default) or clone.
    run_when_inactive: false               # Optional boolean; bypass the repo inactivity gate when true.
    state_keys:                           # Optional parent-blackboard keys every period must advance.
      - last_processed
    delegate: bootstrap/example           # Optional target, mutually exclusive with a sibling ticket.py.

A clone-scoped parent requires ticket.py, creates no period ticket, and rejects
delegate, state_keys, and workflow. A repo-scoped parent defaults an omitted
workflow to direct/body. Its title, owner, agent, contexts, and secrets pass to
each period; ticket-level skills and extension values do not. Parent blackboards
hold job-owned cursors/state (including declared state_keys); preserve each
producer's format. Generated ## Recipe Failure records describe recipe, exit,
task, recorded time, and error output; preserve them as evidence.
-->
