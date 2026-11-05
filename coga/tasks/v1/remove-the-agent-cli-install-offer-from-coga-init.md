---
title: Remove the agent CLI install offer from coga init
status: in_progress
owner: zach
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
step: 2 (peer-review)
agent: claude
---

## Description

`coga init` offers to install an agent CLI the user does not have. Remove that
offer.

`init._offer_agent_cli` scans `PATH` for `claude` and `codex` and branches
three ways. Only the found-nothing branch goes away: the one that prints "No
agent CLI is installed" and prompts "Install which agent CLI?", then calls
`agent_cli_setup.offer_agent_cli` to run the vendor installer.

Keep the scan and the other two branches. With exactly one agent CLI on
`PATH`, init still asks to make it the `default_agent` in `coga.toml`. With
both, it still says nothing.

Done when: no `coga init` path offers to install an agent CLI or says where to
get one, init still offers an already-installed CLI as the default agent, and
`python -m pytest` passes.

### The two call sites are not the same

- `_setup_initialized_clone` (the clone path, near line 1174) passes `None`
  and discards the return, so the install offer is the call's only effect.
  Delete the call.
- `_do_init` (fresh init, near line 1359) feeds the return into the
  `default_agent` written to `coga.toml`. Keep it.

`launch.offer_agent_cli` stays. It fires only for the `coga build` onboarding
task, and this reversal is init-only, so the shared function keeps a caller.

### Stale text and tests this breaks

- `agent_cli_setup`'s module docstring says it is shared by interactive `coga
  init` and `coga build`; only `coga build` is left.
- `init._offer_optional_tools`'s docstring says agent CLIs are not warned
  about there because `_offer_agent_cli` offers them.
- `conftest._stub_init_dep_check` stubs `_offer_agent_cli` by string with
  `raising=False`, so renaming the function creates a dead attribute instead
  of failing, and the real one then runs in every init test.
- Eight tests in `tests/test_init.py` exercise the picker. The four
  install-path ones go; the four covering the scan and the default stay,
  including `test_agent_offer_proposes_the_only_installed_cli_as_default`.

### Init says nothing about where to install

Init names no install location at all. `_do_init`'s next-steps item 2
currently carries both manifest URLs and prints unconditionally; drop the URLs
and use the scan result, so a user with no agent CLI reads one statement of
fact — coga drives Claude Code (`claude`) or Codex (`codex`), neither is on
`PATH`, and launching agents needs one.

Say it once, in next steps. The scan's found-nothing branch prints nothing
where the prompt used to be.

Out of scope: `agent_cli_missing_message` still prints the manifest install
URL for `coga launch`'s point-of-need error, and the `install` field stays in
the manifest for it. A later ticket builds the supported-agents list from this
same scan and may put an install path there.

## Context

### Why

- Nico's direction, 2026-11-04: coga's users already run agentic coding tools,
  so someone with no agent CLI installed is not the audience init should be
  built around.
- The offer dead-ends on a fresh Mac. With neither brew nor npm available,
  picking `claude` prints "Install it from <url>, then re-run" and init then
  runs to completion anyway, so the advice is wrong as given.
- `v1/19-install-link-for-claude-code-yields-the-desktop-ap` closed
  2026-11-04 without fixing the related dead end where the linked installer
  yields the desktop app instead of the `claude` CLI.
- `agent_cli_setup`'s stated policy is that the installer is the vendor's
  package, never `curl | sh`, so there is no third fallback to reach for.

### This lands before ticket 20

`v1/20-ask-which-agents-to-enable-during-coga-init` rewrites the same function
into a picker that asks which agents to enable. It is parked at owner
`review-design` and unstarted; this ticket lands first and ticket 20 builds on
what remains. Its blackboard carries the 2026-11-04 reversal and has already
dropped the install offer from two acceptance criteria and a 2026-10-27 design
decision.

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

branch: coga/v1-remove-the-agent-cli-install-offer-from-coga--9980a6

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Implement handoff (2026-11-04, claude)

The install offer is gone. `init._offer_agent_cli` now only scans `PATH` and
offers an already-installed CLI as `default_agent`; nothing in init installs
an agent CLI or names a place to get one.

What changed:

- `init._installed_agent_clis` is the new named scan (`AGENT_CLIS` on `PATH`,
  manifest order). `_offer_agent_cli` and `_do_init`'s next steps both read
  it, which is also the single scan ticket 20 can build its picker on.
- `_offer_agent_cli` lost the found-nothing branch, so its guard is
  `len(installed) != 1` instead of `> 1`. The `offer_agent_cli` and
  `install_hint` imports are gone with it.
- `_setup_initialized_clone` no longer calls `_offer_agent_cli(None)`; the
  call's only effect was the install offer.
- The next-steps prerequisite dropped both manifest URLs and is now
  conditional on the scan: "Install an agent CLI — coga drives Claude Code
  (`claude`) or Codex (`codex`), and neither is on your PATH." A user who
  already has one is not told to install one.

Decisions:

- **Kept the name `_offer_agent_cli`.** `conftest._stub_init_dep_check` stubs
  it by string with `raising=False`, so a rename silently creates a dead
  attribute and runs the real function in every init test. Ticket 20 rewrites
  this function anyway, so the rename buys nothing and risks that trap.
- **Kept the `default_agent is None` guard** even though the clone call site
  is deleted. `_template_default_agent` still returns `str | None`, and
  without the guard a template declaring no agents would prompt "instead of
  `None`". It is now the only untested branch in the function; the deleted
  clone test was an install-path test.
- **Added two tests beyond the ticket's four-stay set**, for the two scan
  branches whose behavior this change merged: nothing installed (asks
  nothing, returns None) and both installed. `_agent_picker` now makes
  `typer.prompt` raise, so any future install prompt in init fails a test.
- **Next-steps text is a statement of fact, not advice.** It names the two
  CLIs and says neither is on `PATH`; where to get them is the vendor's
  business and stays out of init.

`agent_cli_setup.offer_agent_cli` is untouched and still called by
`launch.offer_agent_cli` for `coga build`. Its module docstring no longer
claims `coga init` shares it. `agent_cli_missing_message` still carries the
manifest URL for `coga launch`, as the ticket scoped out.

Context library: `coga/init` and `coga/install` both documented the picker;
both package copies were edited and byte-mirrored into their `docs/contexts/`
legacy twins (`tests/test_packaging.py` pins the pair). README's init
paragraph said init offers agent CLI installation; it now says init installs
none and offers an installed one as the default.

Verification: `python -m pytest` is 1 failed, 4450 passed, 11 skipped. The
one failure is pre-existing and unrelated (below). The real CLI was also run
twice against scratch repos — with the agent CLIs hidden from `PATH` init
printed the new next-steps item 2 and no prompt; with them on `PATH` the item
was absent.

The branch was then rebased onto `origin/main`, which had moved 43 commits
during the suite run — all of them ticket and log state, no source path
(`git diff 45a92ac86 origin/main` outside `coga/tasks` and `coga/log.md` is
empty), so nothing needed re-testing for drift. The focused suites were
re-run at the rebased head anyway; the full-suite and manual receipts keep
their own pre-rebase OIDs rather than being re-stamped.

The suite ran in a clone in the session scratchpad, because a full
`python -m pytest` in this checkout has been observed switching its own
branch mid-run and voiding the results. Note for anyone repeating it: the
editable install makes a clone's pytest import `/Users/zach2179/dev/coga/src`,
not the clone's `src/`, so the isolation is of the *working tree*, not the
source under test. The primary tree was clean at the tested commit, so the
source matched; use `PYTHONPATH=<clone>/src` to actually pin the source.

### Adjacent finding — pre-existing, not fixed here

`tests/test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`
fails on this machine for want of ripgrep.

- Symptom: `assert [] == ['coga/recurring/_custom-phone-home/ticket.py', ...]`
  at `tests/test_edge_distribution.py:347`.
- Cause: the `migration:inventory` snippet in
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/edge-code-upgrades.md`
  is `rg --files ... | LC_ALL=C sort`. No `rg` binary is installed here (what
  this session's shell has is an `rg` *function* from Claude Code's shell
  snapshot, which a `bash -c` subprocess never sees). The missing command
  exits 127, but `sort` exits 0, so `_operator_command`'s
  `returncode == 0` assertion passes and the test compares empty output.
- Evidence it is not this change: it fails identically on `origin/main`
  (45a92ac86) run with main's own source
  (`PYTHONPATH=<clone>/src python -m pytest <that test>`), and this diff
  touches none of edge distribution, recurring, or the runbook.
- Related, not a duplicate: `v1/13-repair-ci-and-resume-with-release-focused-triggers`
  records that CI's pytest job carries a "Linux ripgrep setup" step, so the
  suite's dependency on `rg` is known for CI but is not declared or skipped
  for a local run. No ticket covers the skip.
- Not filed as a ticket: this is a finding to hand to the owner, not scope
  this ticket owns.

## PR

```yaml
title: Remove the agent CLI install offer from coga init
author: claude
author_evidence: This implement session ran as Claude (Opus 5) under `coga launch`; no agent override.
head: 1fb7524a175376a5d1a7e24e3e8afd4e701374af
base: 2b4bb7b45a5433e0c970fd27a3bfcfda2f4a30aa
depth: deep
rationale: The change itself is a bounded removal with tests, but no code review has run on this diff — peer-review is the next workflow step. Re-judge once it returns.
implementation: Drops the found-nothing branch of `init._offer_agent_cli` (the "Install which agent CLI?" picker and its `agent_cli_setup.offer_agent_cli` call), names the surviving PATH scan `_installed_agent_clis`, deletes the clone path's install-only call, and makes the next-steps agent prerequisite conditional on that scan with both manifest URLs removed.
deviations: Kept the function name `_offer_agent_cli` — the conftest stub matches it by string with `raising=False`, so a rename would silently go dead and run the real function in every init test. Added two tests beyond the ticket's four-stay set, covering the no-CLI and both-installed scan branches whose behavior changed.
limitations: Interactive init was not exercised against a real terminal; coverage fakes the tty and PATH through monkeypatch, as the existing suite does. The `default_agent is None` guard in `_offer_agent_cli` is now untested — the deleted clone test was an install-path test, and `_template_default_agent` can still return None.
files:
  src/coga/commands/init.py: Removes the install offer and its imports, adds `_installed_agent_clis`, deletes the clone call site, and conditions the next-steps prerequisite on the scan.
  src/coga/agent_cli_setup.py: Module docstring no longer claims interactive `coga init` shares the installer; only `coga build` does.
  tests/test_init.py: Deletes the four install-path tests, rewrites `_agent_picker` so `typer.prompt` raises, repoints the declined/tty tests at an installed CLI, adds no-CLI and both-installed coverage, and splits the next-steps assertion into present/absent cases.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Package owner of `coga/init` — documents the scan-only behavior and the conditional next step instead of the picker.
  docs/contexts/coga/init/SKILL.md: Legacy live twin of that topic, byte-mirrored as `tests/test_packaging.py` requires.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: Package owner of `coga/install` — the agent-CLI route is now `coga build` only.
  docs/contexts/coga/install/SKILL.md: Legacy live twin of that topic, byte-mirrored.
  README.md: Init paragraph said it offers agent CLI installation; it now says init installs none.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Code review has not run. `code/with-review` puts peer-review (other-agent) after implement; this record is written before it.
checks:
  - command: python -m pytest tests/test_init.py tests/test_packaging.py tests/test_dependencies.py tests/test_agent_cli_setup.py
    status: passed
    head: 1fb7524a175376a5d1a7e24e3e8afd4e701374af
    base: 2b4bb7b45a5433e0c970fd27a3bfcfda2f4a30aa
    detail: 199 passed in 49s, run at this exact head after the rebase onto origin/main.
  - command: python -m pytest
    status: failed
    head: 44afc942d638482ecbe10f78db96100489ca253f
    base: 45a92ac8660f15e8112e29871787f76d6150c9b6
    detail: 1 failed, 4450 passed, 11 skipped in 1:27:25. The failure is `tests/test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`, pre-existing and unrelated — it fails identically on origin/main with main's own source, because no `rg` binary is installed on this machine. See "Adjacent finding" above. Pre-rebase head, kept with its own OIDs rather than re-stamped; `git diff 44afc942d 1fb7524a1` touches only `coga/log.md` and `coga/tasks/**`, so no source path moved.
  - command: python -m pytest tests/test_launch.py
    status: passed
    head: 44afc942d638482ecbe10f78db96100489ca253f
    base: 45a92ac8660f15e8112e29871787f76d6150c9b6
    detail: 261 passed, covering that `launch.offer_agent_cli` keeps its caller. Pre-rebase head, as above; also subsumed by the full-suite run.
  - command: coga init <scratch repo> --user demo, run twice with and without the agent CLIs on PATH
    status: passed
    head: 44afc942d638482ecbe10f78db96100489ca253f
    base: 45a92ac8660f15e8112e29871787f76d6150c9b6
    detail: With `claude` and `codex` hidden from PATH, next-steps item 2 read "Install an agent CLI — coga drives Claude Code (`claude`) or Codex (`codex`), and neither is on your PATH." with no install prompt and no URL. With both on PATH the item was absent and the remaining steps renumbered. Pre-rebase head, as above.
  - command: coga validate --json
    status: not-run
    detail: No validation behavior changed — this diff touches init's interactive offers, two context topics, and the README.
```

