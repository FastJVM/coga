---
title: 07 Trim the tickets family and secrets
status: blocked
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
step: 2 (peer-review)
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

- `.venv/bin/python -m pytest`: 3952 passed, 7 skipped, 3 failed, all in
  `tests/test_packaging.py` (`coga/code` twin without a canonical copy,
  `architecture` drift, `docs/README.md` link to `coga/code`). These are
  main's known red state from `001aad66f` (ticket 02's sweep incident; fixed
  by PR #1081), not this change. With ticket 02's branch merged into this one
  in a scratch worktree, `tests/test_packaging.py` passed 30/30.
- `coga validate --json`: exit 0.
- Next step: after PR #1081 merges, rebase and re-run the full suite.
  Conflicts are expected only in `cli`, `tickets/discovery` twin and
  `test_packaging.py` (auto-merged cleanly in the trial).

## Peer review

Direct Codex review **completed** on head `a9d6165d54a371b9fbe8d608d033365898b8ef09` against base
`080d9d172d984c0eb6fdfb939251ac7841cfc59e`. The initial Claude implementation (rebased as
`e450aabefb011ca511deb32417f00d994e2a07ba`) was reviewed independently;
Codex then authored and self-reviewed correction commit `a9d6165d5`.
The final receipt conservatively records self-review of the combined diff,
while preserving Claude's implementation identity. No nested reviewer CLI ran.

Must-fix findings addressed:

- Restored creation path validation and the description's closed-code-fence
  exception in `tickets/authoring` and its twin. The shortened wording
  incorrectly prohibited valid fenced `##` examples; `create.description_structure_problem`
  and the existing create tests confirm the retained contract.
- Synchronized the touched packaged `cli` with canonical `cli`: the packaged
  recipe list was missing `prepare-checkout`. The implement handoff's claim
  that every touched pair matched was not true before this correction.
- Kept the no-split decision's reason with its standing owner,
  `tickets/discovery`; `current-direction` now points there for the rationale
  and reopening criterion instead of owning a second copy.

All 21 diff paths were reviewed against the group audit, the unchanged ticket
field guide, current owning topics, and affected implementations. All six
surviving touched context pairs are byte-identical; both ownership copies are
removed and the new development page is indexed and local-only. Searches of
`docs/`, `src/`, `tests/`, `coga/`, README and AGENTS (excluding the archive and
log) found no live links to the removed topic or anchors; remaining mentions
are audit history or old tickets. Link/anchor checking of the 18 changed
Markdown files found only the pre-existing `docs/README.md` link to `coga/code`.
No runtime, raw-terminal, prompt UI, pager, or Slack rendering code changed,
so no interactive-surface exercise applies. No new tests were added for these
documentation corrections; the existing suite covers the referenced behavior.
Audit disagreement: none.

Final verification (exact commands and current-head receipts are in `## PR`):

- Full suite: **3952 passed, 7 skipped, 3 failed** on Python 3.12.12.
- Repo validation: exit 0, 151 ok, 47 warnings, no errors.
- Pristine-clone wheel checks: **2 passed, 28 deselected**.
- `git diff --check main...HEAD`: passed.

Baseline reproduction was run in the pristine clone after checking out
untouched main `080d9d172d984c0eb6fdfb939251ac7841cfc59e` (head and base both that OID):

```sh
PYTHONPATH=/tmp/coga-blocks07-peer-a9d6165d/src /home/n/Code/claude/coga/.venv/bin/python -m pytest tests/test_packaging.py::test_live_and_packaged_copies_stay_identical tests/test_packaging.py::test_context_distribution_is_complete tests/test_packaging.py::test_context_navigation_has_no_broken_links
```

Result: the same **3 failures** (architecture twin drift, orphaned packaged
`coga/code`/required-ref entry, and stale `coga/code` links). An earlier
exploratory full run began before the review corrections and also reported
3952 passed, 7 skipped, 3 failed; it is not used as final-head evidence.

The branch was fetched/rebased onto current main, committed and pushed with
`--force-with-lease`; the primary checkout was returned cleanly to `main`
before this handoff. PR #1081 remains open at the owner review gate for
`blocks/02-delete-the-code-topic-and-remove-coga-repo-only`. Its missing
prerequisite cleanup is the only remaining gate: do not bump while the
required full suite is red. After that task lands, rebase this branch,
re-review the resulting diff and rerun the suite and validation, then refresh
these receipts before bumping. No PR exists for this ticket yet.

## PR

```yaml
title: Trim the tickets family, secrets and blackboard topics
author: claude/codex
author_evidence: The implement handoff records Claude Opus 5.5 (claude-opus-5-5) as the original
  implementer. Codex authored peer-review correction commit a9d6165d54a371b9fbe8d608d033365898b8ef09
  in this session.
head: a9d6165d54a371b9fbe8d608d033365898b8ef09
base: 080d9d172d984c0eb6fdfb939251ac7841cfc59e
depth: deep
rationale: 'Bounded documentation restructure with completed direct review, but the required full
  suite still fails on three packaging defects reproduced on untouched main. Wait for blocks/02-delete-the-code-topic-and-remove-coga-repo-only
  (PR #1081), then rebase, review the resulting diff, and refresh verification before publication.'
implementation: Makes the ticket guide the owner of field shapes, merges ownership gates into
  tickets, moves parser and writer internals to coga-dev/internals/blackboard-io, and retains
  user-facing validation, vault policy, and writer rules. Peer review restored the fenced-description
  exception and path validation, retained the split decision rationale in discovery, and synchronized
  the CLI twin.
deviations: Retains the undated no-split decision, its rationale and reopening criterion in discovery
  so the standing owner keeps the product intent; dated history is in current-direction. Synchronizes
  the touched CLI twin with the existing canonical prepare-checkout entry.
limitations: 'The three baseline packaging failures require owner-reviewed PR #1081 to land. Codex
  independently reviewed the Claude implementation and self-reviewed its own subsequent corrections;
  the final receipt conservatively records self-review. No terminal or Slack rendering check applies
  because runtime and rendered UI code are unchanged. Verification used Python 3.12.12, not a
  separate Python 3.11 run.'
files:
  docs/README.md: Drop the removed ownership leaf from the index.
  docs/contexts/coga-dev/codebase/SKILL.md: Name the secret-ref functions in the source map.
  docs/contexts/coga-dev/current-direction/SKILL.md: Keep dated ticket-split history and link
    to discovery for the standing decision and rationale.
  docs/contexts/coga-dev/internals/SKILL.md: List the new blackboard-io page.
  docs/contexts/coga-dev/internals/blackboard-io/SKILL.md: New page for ticket body and blackboard
    IO internals.
  docs/contexts/coga-dev/microkernel/SKILL.md: Hold the owner command's transaction rationale.
  docs/contexts/coga/blackboard/SKILL.md: Trim internals; keep the writer contract.
  docs/contexts/coga/cli/SKILL.md: Repoint the owner row to tickets.
  docs/contexts/coga/secrets/SKILL.md: Drop syntax and function names.
  docs/contexts/coga/tickets/SKILL.md: Validation rules only; absorb ownership gates.
  docs/contexts/coga/tickets/authoring/SKILL.md: Trim flag syntax and creation-template internals
    while preserving path validation and the closed-code-fence exception.
  docs/contexts/coga/tickets/discovery/SKILL.md: Move dated history and implementation names out;
    retain the standing no-split decision, reason and reopening criterion.
  docs/contexts/coga/tickets/ownership/SKILL.md: Merged into tickets.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: Twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/cli/SKILL.md: Match the canonical
    owner link and its existing prepare-checkout recipe entry.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/secrets/SKILL.md: Twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md: Twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/authoring/SKILL.md: Twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/discovery/SKILL.md: Twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/ownership/SKILL.md: Twin of
    the merged leaf.
  tests/test_packaging.py: Drop coga/tickets/ownership from required bootstrap refs.
review:
  reviewer: codex
  kind: self
  status: passed
  head: a9d6165d54a371b9fbe8d608d033365898b8ef09
  base: 080d9d172d984c0eb6fdfb939251ac7841cfc59e
  detail: Direct review completed for all 21 changed paths against the audit, template, owning
    topics, source and existing tests. Initial implementation was independently reviewed; Codex
    then applied and self-reviewed the review fixes. No unresolved branch-specific findings; the
    required green-suite gate is blocked by the separately reproduced main failures.
checks:
- command: .venv/bin/python -m pytest > /tmp/coga-blocks07-peer-final-pytest.log 2>&1
  status: failed
  head: a9d6165d54a371b9fbe8d608d033365898b8ef09
  base: 080d9d172d984c0eb6fdfb939251ac7841cfc59e
  detail: '3952 passed, 7 skipped, 3 failed in 345.29s on Python 3.12.12. All failures are in
    test_packaging: architecture twin drift, missing canonical coga/code, and stale coga/code
    links. The same three failures reproduce on untouched base 080d9d172d984c0eb6fdfb939251ac7841cfc59e.'
- command: .venv/bin/coga validate --json > /tmp/coga-blocks07-peer-final-validate.json
  status: passed
  head: a9d6165d54a371b9fbe8d608d033365898b8ef09
  base: 080d9d172d984c0eb6fdfb939251ac7841cfc59e
  detail: Exit 0; 151 ok, 47 warnings, no errors.
- command: PYTHONPATH=/tmp/coga-blocks07-peer-a9d6165d/src /home/n/Code/claude/coga/.venv/bin/python
    -m pytest tests/test_packaging.py -k wheel
  status: passed
  head: a9d6165d54a371b9fbe8d608d033365898b8ef09
  base: 080d9d172d984c0eb6fdfb939251ac7841cfc59e
  detail: 'Ran from a pristine clone at this head: 2 passed, 28 deselected; built-wheel contents
    and installed-wheel init/phone-home isolation passed.'
- command: git diff --check main...HEAD
  status: passed
  head: a9d6165d54a371b9fbe8d608d033365898b8ef09
  base: 080d9d172d984c0eb6fdfb939251ac7841cfc59e
  detail: Exit 0 on the reviewed feature branch; no whitespace errors.
```

---

## Blockers

- [ ] [2026-10-21 19:03] [agent:codex] id=20261021T190358 Land PR #1081 for blocks/02-delete-the-code-topic-and-remove-coga-repo-only; it fixes three packaging failures reproduced on untouched main. Then rebase blocks/07-trim-tickets-secrets, re-review the resulting diff, and rerun the required full suite before bumping.

---

## Blocker reminders

- eabedd06227b last_reminded: 2026-10-22 09:03
