---
title: Cap requires-python and stop init leading with a coga.toml edit
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
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
step: 3 (open-pr)
agent: claude
launch_generation: e8786e77-98c2-477f-9798-a64a430effaa
---

## Description

On a machine with no Python, `uv tool install coga` picks the newest Python
(3.15). One dependency, PyYAML, has no ready-made package for 3.15, so it
compiles. On a Mac without developer tools that pops up an install dialog, but
Coga still works. Decide whether to cap Python at the tested 3.11 or leave it.

Also: when no agent CLI is found, `coga init` tells the user to uncomment a
table in `coga.toml`.

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

## Dev

pr: https://github.com/FastJVM/coga/pull/1235
branch: coga/v1-47-cap-requires-python-and-stop-init-leading--7ac3ac


## Decisions

- **Python cap: not capped.** `requires-python` stays `>=3.11`. An upper
  bound does not make `uv tool install coga` pick an older interpreter. A
  resolver on 3.15 would instead fall back to the newest *uncapped* release
  (0.4.1 on PyPI), which installs silently stale Coga. The fix is to pin the
  interpreter at install time: the README macOS/Linux command and init's
  "put coga on PATH" step now say `uv tool install --python 3.11 coga`. That
  matches the Windows instructions and the clean-install harness, which
  already use `--python 3.11`. uv downloads 3.11 if needed, PyYAML has wheels
  for it, and nothing compiles.
- **No agent CLI found → keep every `[agents.*]` table live.**
  `init._configure_agent_tables` returns the declared names unchanged on an
  empty `found`. This is the same file a non-interactive init leaves. The next
  steps name only the install (the `uncomment its table` remedy now appears
  only when coga.toml declares no agent, e.g. a scaffold). `coga validate` is
  clean on that fresh repo (previously `unknown-agent` and
  `unresolvable-operator` on coga-build). The summary's "every table commented
  out" line was removed, because init no longer produces that state.
- Tradeoff: after installing only Codex, Claude stays the declared default.
  The build line offers `coga build --agent codex`, and the `coga/init` topic
  says so.

## Handoff (implement → peer-review)

Commit 6e2732633e0d on the branch, pushed; rebased on origin/main 691c8f9d8
(no drift). Changed: `src/coga/commands/init.py`, `tests/test_init.py`,
`README.md`, and the user topics `coga/init` and `coga/configuration`. No
seeded-fixture change is needed (init-only behavior). Python 3.11 floor was not
exercised; the suite ran on 3.12.12.

## Peer review

Independent direct Codex review **completed** on head `ff0254f3a39f40f010824adf11ca059a0939f6f5`
against base `d11e9a82352bb407943a5550492e99eac7f82980` after rebasing onto fetched origin/main.
Implementation identity is Claude, as recorded in the implement handoff;
this fresh Codex session reviewed the five-path diff and surrounding init,
configuration, and install contracts. No must-fix findings; no code changes.
The no-cap decision is accepted as a bounded install-command choice; no
Python 3.15 resolver or macOS clean-install experiment was performed.

Real PTY checks at 80×24 and 120×30 ran fresh init with agent/Coga PATH
lookups forced absent; optional software installation/login was disabled.
Both showed the no-agent scan, the Python-pinned install command, and the
Claude/Codex build alternatives without an agent-table edit instruction.
Plain next-step lines wrap naturally in the terminal; no cursor/pager UI is
involved. Scratch harness: `/tmp/coga-v147-terminal.py`.

Full suite on the final head: `PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q -p no:cacheprovider`
→ 4900 passed, 33 skipped in 789.74s; Pop!_OS 24.04, Python 3.12.12.
`git diff --check` passed. Python 3.11 floor untested here; native Windows
and macOS verification deferred to release. Final fetch confirmed unchanged
main; branch force-pushed with lease and manual checkout returned to main.
Next step only opens the PR from the prepared record.

## PR

```yaml
title: Keep agent tables live when init finds no agent CLI; pin uv install to Python 3.11
author: claude
author_evidence: >-
  Implement session ran as Claude Code (claude-opus-5-5) in a megalaunch queue;
  the implement handoff records this identity.
head: ff0254f3a39f40f010824adf11ca059a0939f6f5
base: d11e9a82352bb407943a5550492e99eac7f82980
depth: skim
rationale: >-
  Small init behavior change plus install docs; the reviewer should check the
  decision not to cap requires-python and the zero-agent default-agent tradeoff.
  Independent direct review and the full Linux suite passed on the final head.
implementation: >-
  Init leaves the packaged coga.toml untouched when the agent scan finds no
  CLI, so next steps name an install, not a coga.toml edit. The README and
  init's PATH step install with uv tool install --python 3.11 coga.
deviations: >-
  The ticket title says cap requires-python; it was deliberately left uncapped
  because a cap makes resolvers on newer Pythons fall back to older uncapped
  releases. The interpreter is pinned at the install command instead.
limitations: >-
  Python 3.11 floor not exercised (3.12.12 only). No real macOS or uv
  install on Python 3.15 was run; the PyYAML-compile reasoning is from the ticket report.
  Native Windows and macOS verification is deferred to release.
files:
  README.md: "Pin the macOS/Linux uv install to Python 3.11 and say why."
  src/coga/commands/init.py: "Keep agent tables live with no CLI found; drop the stale all-commented summary; pin the PATH step to --python 3.11."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: "Document that a no-agent init comments nothing out."
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: "Document the zero-agent outcome and the pinned install step."
  tests/test_init.py: "Cover the zero-agent packaged-file outcome, clean validate, and no coga.toml edit in next steps."
review:
  reviewer: codex
  kind: independent
  status: passed
  head: ff0254f3a39f40f010824adf11ca059a0939f6f5
  base: d11e9a82352bb407943a5550492e99eac7f82980
  detail: >-
    Independent direct Codex review completed after rebase; no must-fix findings.
    Real PTY no-agent init checked at 80x24 and 120x30 with optional installs/login
    disabled; next steps showed Python pin and both build choices without an
    agent-table edit instruction.
checks:
  - command: .venv/bin/python -m pytest tests/test_init.py -q -x
    status: passed
    head: 6e2732633e0da719002ab66286c9ffa331ad79a4
    base: 691c8f9d82abe7be386c931a16e4e776a52a8cee
    detail: "170 passed; Linux Pop!_OS, Python 3.12.12. Historical pre-rebase receipt."
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider
    status: passed
    head: 6e2732633e0da719002ab66286c9ffa331ad79a4
    base: 691c8f9d82abe7be386c931a16e4e776a52a8cee
    detail: "4900 passed, 33 skipped in 765.20s; Linux Pop!_OS 24.04, Python 3.12.12, committed clean tree. Historical pre-rebase receipt."
  - command: PYTHONPATH=/home/n/Code/coga/src .venv/bin/python -m pytest -q -p no:cacheprovider
    status: passed
    head: ff0254f3a39f40f010824adf11ca059a0939f6f5
    base: d11e9a82352bb407943a5550492e99eac7f82980
    detail: >-
      4900 passed, 33 skipped in 789.74s; Linux Pop!_OS 24.04, Python 3.12.12.
      Final rebased committed tree; Python 3.11 and native checks not run here.
  - command: git diff --check
    status: passed
    head: ff0254f3a39f40f010824adf11ca059a0939f6f5
    base: d11e9a82352bb407943a5550492e99eac7f82980
    detail: "No whitespace errors."
```
