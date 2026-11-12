---
title: 'validate-drift: large-blackboard — live ticket blackboard over the size threshold'
status: in_progress
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
step: 2 (human-executes)
agent: claude
---

## Description

Filed by Dream run recurring/dream, period 2026-W46 (run 20261112T051938Z), Phase 6 disposition. validate-drift: large-blackboard (rerouted as an owner-directed state edit per the Dream template).

Live member needing an owner decision: v1/20-ask-which-agents-to-enable-during-coga-init (in_progress), blackboard region 36.8 KiB over the 32.0 KiB threshold. Remedy per coga/blackboard: promote to directory form, move dated evidence into sibling attachments, move abandoned designs into the single Superseded designs section, keep Dev, Blockers, the current handoff, worklist and verification in place; move, do not delete. Owner may edit directly on control; publish via coga/state-publication. No branch or PR requirement.

Other members this run, not covered here: v1/14-interactive-coga-launch-on-native-windows (done with live checkout, 49.3 KiB — retirement debt, run coga retire, do not slim) and v1/package-definitions/02-repo-cutover-to-package-owned-definitions (done, 40.0 KiB — removed by Dream Retro PR #1201).

coga validate --json is the live member list. Keep this ticket open until the class is empty or the decision is recorded in a context, preserving the tag line 'validate-drift: large-blackboard', decision, rationale, and scope there before closing with accepted warnings.

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

## Brief (2026-11-12, brief-and-hand-off, read-only)

**Goal.** Get `v1/20-ask-which-agents-to-enable-during-coga-init` out of
`coga validate`'s `large-blackboard` class (live region 36.8 KiB vs 32.0 KiB),
per the `coga/blackboard` size remedy: move, never delete.

**Facts observed (main @ 550516642).**
- Target: `coga/tasks/v1/20-ask-which-agents-to-enable-during-coga-init.md`,
  file form, `in_progress`, `step: 7 (review)`, **owner: zach** (not this
  ticket's owner). PR #1196 is OPEN, unmerged. Last touched 92f10606f
  (2026-11-11). So it is actively worked: coordinate with Zach first.
- Live sections (the counted region; `## Superseded designs` at line 1327
  is excluded): `## Dev` 0.3 KB, `## Evaluator review` 5.2 KB, six dated
  `## 2026-11-10/11 — …` logs 25.0 KB (lines 776–1194), `## PR` 6.9 KB,
  `## Open Questions` (None).
- The current handoff is `### Handoff — what is left…` (line 1089), nested
  inside `## 2026-11-11 — peer-review (codex)…`; it is partly stale (step
  has moved 5 → 7, Windows walk now recorded at line 1120).
- Other class members, out of scope here: v1/14 (49.3 KiB, done with live
  checkout — retirement debt, `coga retire`), v1/package-definitions/02
  (40.0 KiB, done — Dream Retro PR #1201), and **`recurring/dream`
  (73.4 KiB)**, which the Dream disposition did not name. Dream's template
  blackboard is rewritten each run, so per `coga/blackboard` it is not
  trimmed by hand: route it to its owner as a decision (attachment,
  exemption, or accepted warning) before this ticket can close.

**Ordered steps for the human.**
1. Confirm with Zach (target owner) that slimming now is fine while #1196 is
   in review; otherwise record "accepted warning until #1196 merges" instead.
2. Promote to directory form: `git mv` the `.md` to
   `coga/tasks/v1/20-ask-which-agents-to-enable-during-coga-init/ticket.md`
   (check `coga/tickets` for any CLI-supported promote path first).
3. Move the six dated `## 2026-11-1x — …` sections verbatim into a sibling
   attachment, e.g. `.../20-…/history-2026-11-10-11.md`, opening with
   `<!-- moved from v1/20-… blackboard on 2026-11-12 -->`. Leave each moved
   heading in place holding only a pointer line.
4. Keep in place: `## Dev`, `## PR`, `## Open Questions`, and a current
   handoff (lift the `### Handoff` block out of the moved log, or rewrite it
   to reflect step 7 and #1196). Optionally move the resolved
   `## Evaluator review` into the attachment too (5.2 KB) — it is history
   once dispositioned.
5. Record before/after live-region sizes on the target blackboard.
6. Publish as state on control (`coga/state-publication`; e.g.
   `coga run publish-state <path>` or the next lifecycle sweep). No branch/PR.

**Irreversible action.** Pushing the restructure to control (the file move
to directory form changes the task path every reader resolves). It is
recoverable via git, but a concurrent edit on Zach's side would then
conflict — hence step 1.

**Done check.** `coga validate --json` shows no `large-blackboard` row for
v1/20 (live region < 32 KiB), `coga validate` reports no new errors for the
directory-form task, and the attachment holds every moved byte (diff the
removed lines against the attachment). Then this ticket closes when the
class is empty or the remaining rows are recorded as accepted/retire-owned.
