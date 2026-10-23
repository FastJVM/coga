---
title: 07 Trim the tickets family and secrets
status: done
owner: nicktoper
contexts:
- coga/knowledge
- coga-dev/packaging
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
agent: claude
---

## Description

Apply the audit verdicts to coga/tickets, its leaves (merging ownership into tickets), secrets and blackboard, removing what the self-documenting ticket template already states. See `coga/tasks/blocks/README.md`.

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

### Scope and acceptance

Read `coga/tasks/blocks/README.md` first: it holds the test, the rules every
ticket in this group follows, and the audit rows for these topics. The audit
verdicts are recommendations; re-check each against current main and record
any disagreement on the blackboard for the owner before departing from it.

Done when: the tickets, tickets/authoring, tickets/discovery, secrets and blackboard rows in the README table are applied, `tickets/ownership` is merged into `tickets`, and nothing the ticket template's guide comment states is restated in a topic; both copies of every touched topic are byte-identical;
no link in `docs/`, `src/`, `tests/`, `coga/` (outside old tickets and the
log), `README.md` or `AGENTS.md` points at a removed topic or anchor; any new
coga-dev page is listed in `docs/contexts/coga-dev/internals/SKILL.md`;
`.venv/bin/python -m pytest` and `coga validate --json` pass.

### Specifics

- The ticket template (`src/coga/resources/ticket.md`) owns field shapes;
  topics keep rules the template only points to (body regions, validation,
  writer rules). Do not shrink the template's guide in this ticket.
- New coga-dev page: `internals/blackboard-io`. Ownership transaction →
  `coga-dev/microkernel`.
- `blackboard` keeps one line naming `update_blackboard_under_barrier` for
  `ticket.py` writers.


<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/1087
branch: blocks/07-trim-tickets-secrets

## Implement handoff (2026-10-21)

Original implementation: `13dad0516` (rebased as `e450aabef`). The peer
review below supersedes this handoff's verification and twin claim.

- `coga/tickets`: frontmatter key/required lists, extension declaration shape
  and removed-key names dropped (the ticket template owns them); kept the
  validation rules (agent, falsy values, removed keys fail, extension checks),
  writer rule, body regions. Removed function names, `body_sections` parser
  detail and allowlist rationale. Repointed `agents#the-default-agent` → "the
  configured default agent" (no link; ticket 01 deletes `agents`).
- `tickets/ownership` merged into `tickets` as "## Owner and relationships"
  (gates only); both copies deleted, `REQUIRED_BOOTSTRAP_CONTEXT_REFS` entry
  dropped, `cli` owner row → `tickets#owner-and-relationships`, `docs/README.md`
  fixed. Transaction rationale → `coga-dev/microkernel` (after the open
  placements table).
- `tickets/authoring`: flags trimmed to behavior (`--help` owns syntax),
  function names dropped; "Creation template" → `internals/blackboard-io`.
- `tickets/discovery`: #889/#899 history → `coga-dev/current-direction`
  "Deliberately deferred"; one undated sentence kept (decision stays with its
  standing owner per `coga/knowledge`). `relay-os` pathspecs were already gone
  (ticket 02). Function/error names dropped.
- `secrets`: syntax list → template; function names → `coga-dev/codebase`
  source map; vault policy and env-scrub semantics kept.
- `blackboard`: fence regex, `split_body`/`upsert`, archive projection,
  `_is_stock_blackboard`, writer race → new `coga-dev/internals/blackboard-io`
  (listed in the internals index). Keeps one line naming
  `blackboard.update_blackboard_under_barrier` for `ticket.py` writers.
- Audit disagreement: none.

### Verification

Historical implementation verification encountered three packaging failures on
main. PR #1081 has now landed; the completed resumed review and green
verification below replace those earlier receipts.

## Peer review

Direct Codex review **completed** on head `fa9355af47356e17fe0fe2eb9edbcb9d7515e5b7` against base
`e2958c82d4fa7e3b9a930e7df7e0e311afba0fea`. No unresolved findings remain.

The original Claude implementation and earlier Codex corrections are preserved
as `2d55d8b00` and `fa9355af4`. This resumed Codex session resolved the rebase
wording and reviewed the resulting combined diff. The final receipt is
conservatively **self-review**: earlier Codex review was independent of Claude's
implementation, but Codex also authored corrections. No nested reviewer CLI ran.

The human cleared the prerequisite ask after PR #1081 merged; `coga unblock`
recorded the resolution below. Rebased onto current main before reviewing and
testing. The tickets/twin conflict retained main's default-agent configuration
pointer while removing the internal function name. The CLI twin retained main's
newer alias and recipe guidance, which already includes the earlier twin fix.
The range-diff confirms the other implementation and review fixes survived.

Reviewed all 21 changed paths against the audit, unchanged ticket guide,
owning topics, implementation, and existing tests. The creation-path validation
and closed-code-fence exception remain, and discovery retains the no-split
reason with its standing owner. All six surviving topic pairs are byte-identical;
both ownership copies are removed; the new development page is indexed and
local-only. Links and anchors in all 18 changed Markdown files pass. Searches
across docs, src, tests, coga, README and AGENTS found removed-topic references
only in old tickets and audit history; no live guidance points to a removed
topic or anchor. Archive content and the log were excluded from those searches.
No audit disagreement or new must-fix finding.

Verification at this head/base:

- `.venv/bin/python -m pytest`: **3987 passed, 7 skipped** in 371.22s.
- `coga validate --json`: exit 0; 158 ok, 48 warnings, no errors.
- Pristine-clone wheel checks: **2 passed, 28 deselected** in 12.24s.
- `git diff --check origin/main...HEAD`: passed.

Python was 3.12.12; there was no separate 3.11 run. No terminal, pager, prompt UI,
or Slack rendering code changed, so no interactive-surface exercise applies.
No new tests were needed for the documentation edits; the existing suite covers
the referenced behavior.

The final fetch observed `1ee371c66af6ec2473c934b49b2b057a16f8d71c`. Since the reviewed base, only the log
and two unrelated tickets changed on main; there is no material drift, and this
ticket's control copy is unchanged. The branch is committed and pushed at
`fa9355af47356e17fe0fe2eb9edbcb9d7515e5b7` with an explicit remote-OID lease.
Only this unstaged handoff remains locally. The exact current-head receipts
and all file explanations are in `## PR`; its rendered presentation was
checked successfully as `skim`, with self-review disclosed. No PR exists for
this ticket yet. The next step is mechanical PR publication.

## PR

```yaml
title: Trim the tickets family, secrets and blackboard topics
author: claude/codex
author_evidence: The prior implementation handoff identifies Claude Opus 5.5 (claude-opus-5-5) as the
  original implementer (13dad0516, now rebased as 2d55d8b00). The prior Codex peer session authored correction
  a9d6165d5 (now fa9355af4). This resumed Codex session resolved the rebase conflicts and directly reviewed
  the resulting diff.
head: fa9355af47356e17fe0fe2eb9edbcb9d7515e5b7
base: e2958c82d4fa7e3b9a930e7df7e0e311afba0fea
depth: skim
rationale: 'Bounded documentation restructure with no runtime behavior changes. Direct review, the full
  suite, repository validation, pristine-clone wheel checks, and link checks passed. Skim the retained
  no-split decision and the disclosed self-review; the prerequisite packaging failures are resolved by
  merged PR #1081.'
implementation: Makes the ticket guide the owner of field shapes, merges ownership gates into tickets,
  moves parser and writer internals to coga-dev/internals/blackboard-io, and retains validation, vault
  policy, and writer rules. Preserves the creation-path validation and closed-code-fence exception from
  peer review. The rebase preserves main’s default-agent configuration pointer and newer CLI recipe guidance.
deviations: Retains the undated no-split decision, its rationale, and reopening criterion in discovery
  so the standing owner keeps product intent; dated history moves to current-direction. No disagreement
  with the group audit.
limitations: The final review is conservatively recorded as self-review because Codex authored earlier
  corrections and this session resolved rebase wording. The earlier Claude implementation received independent
  Codex review, but there is no independent receipt for the final combined diff. No interactive terminal
  or Slack exercise applies because runtime and rendered UI code are unchanged. Verification used Python
  3.12.12; no separate Python 3.11 run.
files:
  docs/README.md: Drop the removed ownership leaf from the index.
  docs/contexts/coga-dev/codebase/SKILL.md: Name the secret-ref functions in the source map.
  docs/contexts/coga-dev/current-direction/SKILL.md: Keep dated ticket-split history and link to discovery
    for the standing decision and rationale.
  docs/contexts/coga-dev/internals/SKILL.md: List the new blackboard-io page.
  docs/contexts/coga-dev/internals/blackboard-io/SKILL.md: New page for ticket body and blackboard IO
    internals.
  docs/contexts/coga-dev/microkernel/SKILL.md: Hold the owner command's transaction rationale.
  docs/contexts/coga/blackboard/SKILL.md: Trim internals; keep the writer contract.
  docs/contexts/coga/cli/SKILL.md: Repoint the owner row to tickets.
  docs/contexts/coga/secrets/SKILL.md: Drop syntax and function names.
  docs/contexts/coga/tickets/SKILL.md: Retain validation and writer rules, merge owner gates, and preserve
    main’s default-agent configuration pointer.
  docs/contexts/coga/tickets/authoring/SKILL.md: Trim flag syntax and creation-template internals while
    preserving path validation and the closed-code-fence exception.
  docs/contexts/coga/tickets/discovery/SKILL.md: Move dated history and implementation names out; retain
    the standing no-split decision, reason and reopening criterion.
  docs/contexts/coga/tickets/ownership/SKILL.md: Merged into tickets.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: Twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Repoint the owner link to tickets;
    main already supplies the synchronized recipe guidance.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/secrets/SKILL.md: Twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md: Twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/authoring/SKILL.md: Twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/discovery/SKILL.md: Twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/ownership/SKILL.md: Twin of the merged
    leaf.
  tests/test_packaging.py: Drop coga/tickets/ownership from required bootstrap refs.
review:
  reviewer: codex
  kind: self
  status: passed
  head: fa9355af47356e17fe0fe2eb9edbcb9d7515e5b7
  base: e2958c82d4fa7e3b9a930e7df7e0e311afba0fea
  detail: Direct review completed for all 21 changed paths against the group audit, unchanged ticket guide,
    current owning topics, implementation, and existing tests. Reviewed both rebase resolutions and the
    range-diff. All six surviving twins match; both ownership copies are removed; the new development
    leaf is indexed and local-only; links and anchors in all 18 changed Markdown files pass. No unresolved
    findings. Codex corrections and rebase wording were self-reviewed; no nested reviewer CLI ran.
checks:
- command: .venv/bin/python -m pytest > /tmp/coga-blocks07-20261022-pytest.log 2>&1
  status: passed
  head: fa9355af47356e17fe0fe2eb9edbcb9d7515e5b7
  base: e2958c82d4fa7e3b9a930e7df7e0e311afba0fea
  detail: 3987 passed, 7 skipped in 371.22s on Python 3.12.12. All packaging tests passed; the three former
    baseline failures are resolved.
- command: coga validate --json > /tmp/coga-blocks07-20261022-validate.json
  status: passed
  head: fa9355af47356e17fe0fe2eb9edbcb9d7515e5b7
  base: e2958c82d4fa7e3b9a930e7df7e0e311afba0fea
  detail: Exit 0; 158 ok, 48 warnings, no errors.
- command: PYTHONPATH=/tmp/coga-blocks07-pristine-fa9355af4/src /home/n/Code/claude/coga/.venv/bin/python
    -m pytest tests/test_packaging.py -k wheel > /tmp/coga-blocks07-20261022-wheel.log 2>&1
  status: passed
  head: fa9355af47356e17fe0fe2eb9edbcb9d7515e5b7
  base: e2958c82d4fa7e3b9a930e7df7e0e311afba0fea
  detail: 'Ran from pristine clone /tmp/coga-blocks07-pristine-fa9355af4 at this head: 2 passed, 28 deselected
    in 12.24s. Built-wheel contents and installed-wheel init/phone-home isolation passed.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: fa9355af47356e17fe0fe2eb9edbcb9d7515e5b7
  base: e2958c82d4fa7e3b9a930e7df7e0e311afba0fea
  detail: Exit 0; no whitespace errors.
```

## Blockers

- [x] [2026-10-21 19:03] [agent:codex] id=20261021T190358 Land PR #1081 for blocks/02-delete-the-code-topic-and-remove-coga-repo-only; it fixes three packaging failures reproduced on untouched main. Then rebase blocks/07-trim-tickets-secrets, re-review the resulting diff, and rerun the required full suite before bumping.
  resolved: [2026-10-22 11:49] [human:nicktoper] The human confirmed clearing the prerequisite blocker and continuing. PR #1081 merged on 2026-10-22 at 03:57:39 UTC as a1a3f5049b5dd2457f531a4d81b79b6a6425bb9f and is present on origin/main. Rebase blocks/07-trim-tickets-secrets onto current main, complete a fresh direct review, rerun the full suite and validation, and refresh the receipts before bumping.

---

## Blocker reminders

- eabedd06227b last_reminded: 2026-10-22 09:03
