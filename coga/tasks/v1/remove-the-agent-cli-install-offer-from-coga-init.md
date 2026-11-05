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
step: 3 (open-pr)
agent: claude
---

## Description

`coga init` and the `coga build` onboarding launch offer to install an agent
CLI the user does not have. Remove every agent CLI installation offer and
install URL from Coga.

`init._offer_agent_cli` scans `PATH` for `claude` and `codex` and branches
three ways. Only the found-nothing branch goes away: the one that prints "No
agent CLI is installed" and prompts "Install which agent CLI?", then calls
`agent_cli_setup.offer_agent_cli` to run the vendor installer.

Keep init's scan and the other two branches. With exactly one agent CLI on
`PATH`, init still asks to make it the `default_agent` in `coga.toml`. With
both, it still says nothing.

At every point of need, including `coga build`, a missing configured agent CLI
now gets one remediation: Coga requires that CLI on `PATH`. Do not offer an
installer, run a package manager, or print an agent-install URL.

Done when: no Coga path offers to install an agent CLI or says where to get
one, init still offers an already-installed CLI as the default agent, every
agent-backed command fails loud when its configured CLI is absent from
`PATH`, and `python -m pytest` passes.

### The two call sites are not the same

- `_setup_initialized_clone` (the clone path, near line 1174) passes `None`
  and discards the return, so the install offer is the call's only effect.
  Delete the call.
- `_do_init` (fresh init, near line 1359) feeds the return into the
  `default_agent` written to `coga.toml`. Keep it.

Delete `launch.offer_agent_cli`'s `coga build` exception. With no caller left,
delete `agent_cli_setup`, its tests, and the agent-specific installer metadata.

### Stale text and tests this breaks

- `dependencies` still carries the agent installer URLs, brew/npm package
  arguments, login commands, and point-of-need install hint. Remove them.
- `init._offer_optional_tools`'s docstring says agent CLIs are not warned
  about there because `_offer_agent_cli` offers them.
- `conftest._stub_init_dep_check` stubs `_offer_agent_cli` by string with
  `raising=False`, so renaming the function creates a dead attribute instead
  of failing, and the real one then runs in every init test.
- Eight tests in `tests/test_init.py` exercise the picker. The four
  install-path ones go; the four covering the scan and the default stay,
  including `test_agent_offer_proposes_the_only_installed_cli_as_default`.

### No agent-install remediation

Init names no install location at all. `_do_init`'s next-steps item 2 uses the
scan result, so a user with no agent CLI reads one statement of fact — coga
drives Claude Code (`claude`) or Codex (`codex`), neither is on `PATH`, and
agent-backed commands require one there.

Say it once, in next steps. The scan's found-nothing branch prints nothing
where the prompt used to be.

`agent_cli_missing_message` gives the same PATH-only requirement to launch,
ticket authoring, megalaunch, and later-step handoffs. The README and init may
still show how to install Coga itself (`uv tool install coga`); this change is
only about agent CLI installation.

A later ticket builds the supported-agents list from init's same scan and may
deliberately design new discovery UX. It starts from this clean slate rather
than inheriting the broken installer offer.

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
- Zach's direction, 2026-11-05: Coga should never offer agent CLI installation
  or agent-install URLs. Its only remediation is that the configured agent CLI
  must be on `PATH`. Keep Coga's own `uv tool install coga` instructions.

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

> Superseded by the peer-review scope decision and final review below. Kept as
> the receipt for Claude's original init-only implementation.

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

## Peer review (2026-11-05, codex)

Direct Codex review completed on the original Claude diff and then self-reviewed
the final owner-expanded diff. The original review found stale installer policy
in `dependencies.py`. In the attended review, Zach broadened the decision: Coga
must never offer agent CLI installation or agent-install URLs; its only
remediation is that the configured agent CLI must be on `PATH`. Coga's own
`uv tool install coga` instructions stay.

Final behavior:

- Init still scans `claude` / `codex`, offers the sole installed CLI as the
  default, and says nothing when both are present.
- With none present, init states the PATH requirement once in Next steps.
- Every agent-backed point of need, including `coga build`, ticket authoring,
  megalaunch, chained handoffs, and the spawn race, uses the same PATH-only
  failure. No agent installer command or URL remains in runtime or product
  guidance.
- The unused `agent_cli_setup` module/tests and agent installer metadata were
  deleted. Clean-install runbooks now require the operator to provide an
  authenticated CLI using their existing setup.

Review result: no unresolved findings after the expansion. Final reviewed head
is `3badabee50b3e046ddf9205db0c1ff13c6454855` against
`0bf1d5dad2f2387ac73ecbadfb645182730a6661`. The branch was fetched from GitHub
and rebased in the isolated clone; the 139 intervening main commits changed
only task/log state, not implementation paths.

Verification so far:

- Exact-head focused init/launch/megalaunch/dependency/packaging suite: 449
  passed in 5:39.
- Exact-head terminal checks: no-agent init kept `uv tool install coga` and
  printed no agent installer; no-agent `coga build` failed with only the PATH
  requirement; one-installed-CLI init still offered `codex` as default.
- Task-scoped `coga validate --json`: one task OK, no issues.
- The pre-final `0e463b69b` `python -m pytest` reached the clean-install
  harness and failed because this Codex sandbox forbids `/dev/fd/*`; the first
  failing test reproduces identically on clean main (`0bf1d5dad`). This is
  unrelated to the diff. A follow-up run excluding that sandbox-incompatible
  file remained green through the checkout block before being stopped; it is
  not recorded as a pass. The final commit adds only a megalaunch assertion;
  the exact-head focused run covers it.

Checkout alignment completed: the primary feature ref is at the pushed final
head, and the mixed-reset state drift was restored while preserving this
projected ticket as the checkout's only uncommitted path.

## PR

```yaml
title: Remove all agent CLI installation offers
author: claude_codex
author_evidence: Claude implemented the original init-only removal; Codex peer review implemented Zach's attended expansion to every agent-backed path and the final cleanup.
head: 3badabee50b3e046ddf9205db0c1ff13c6454855
base: 0bf1d5dad2f2387ac73ecbadfb645182730a6661
depth: deep
rationale: Owner-expanded cross-command policy change; inspect the final diff because Codex authored review fixes, the final review is therefore self-review, and the full suite is sandbox-blocked despite focused coverage passing.
implementation: Removes every Coga agent CLI installer offer, package command, login offer, and install URL; preserves init's PATH scan/default-agent confirmation; and gives all missing-agent paths one configured-CLI-on-PATH requirement.
deviations: Scope expanded during attended peer review from init-only to all Coga surfaces. Coga's own `uv tool install coga` guidance remains. The later agent-scan ticket starts from this clean slate.
limitations: Coga intentionally provides no agent installer remediation. Clean-install operators must provision an authenticated agent CLI with their own setup. This sandbox blocks `/dev/fd`, so the exact full suite cannot pass here; the same first failure reproduces on clean main.
files:
  README.md: Removes agent installer links and states the PATH-only prerequisite while retaining Coga's uv install.
  coga/skills/coga/testing/clean-install/SKILL.md: Legacy live twin; replaces embedded agent setup commands/URL with an operator-provided PATH prerequisite.
  coga/skills/coga/testing/clean-install/macos-aws/SKILL.md: Legacy live twin; removes the macOS agent installer command/URL.
  docs/contexts/coga-dev/codebase/SKILL.md: Removes the deleted installer module from the source map.
  docs/contexts/coga-dev/current-direction/SKILL.md: Records the owner reversal to no agent installation offers or links.
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: Updates the spawn-race remedy to the shared PATH requirement.
  docs/contexts/coga/init/SKILL.md: Legacy live twin documenting scan/default behavior and the factual missing-CLI next step.
  docs/contexts/coga/install/SKILL.md: Legacy live twin owning the no-agent-installer policy.
  src/coga/agent_cli_setup.py: Deleted the now-unused agent installer/login implementation.
  src/coga/commands/init.py: Removes init's install picker and clone call, keeps scan/default behavior, and prints a conditional PATH fact.
  src/coga/dependencies.py: Removes agent install URLs/package/login metadata and defines the shared PATH-only failure.
  src/coga/launch.py: Removes the coga-build installer exception and uses the shared failure for spawn races.
  src/coga/megalaunch.py: Uses the shared PATH-only failure for its FileNotFoundError boundary.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Package owner of the init contract; mirrored to docs.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: Package owner of the install contract; mirrored to docs.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/SKILL.md: Package owner of the clean-install runbook; removes agent installer commands/URL.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md: Package owner of the macOS runbook; removes agent installer commands/URL.
  tests/test_agent_cli_setup.py: Deleted tests for the removed installer module.
  tests/test_dependencies.py: Pins the absence of agent installer metadata and the PATH-only shared message.
  tests/test_init.py: Removes install-picker cases and covers no/one/both installed scan behavior and URL-free next steps.
  tests/test_launch.py: Removes build-installer cases and pins PATH-only launch, chained-handoff, and spawn-race failures.
  tests/test_megalaunch.py: Pins megalaunch's missing-agent PATH requirement.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 3badabee50b3e046ddf9205db0c1ff13c6454855
  base: 0bf1d5dad2f2387ac73ecbadfb645182730a6661
  detail: Direct Codex review completed with no unresolved findings. Codex independently reviewed Claude's original diff, then authored the owner-directed expansion and self-reviewed the final head.
checks:
  - command: PYTHONPATH=/private/tmp/coga-peer-review-a8259c54/src /opt/anaconda3/bin/python -m pytest tests/test_dependencies.py tests/test_init.py tests/test_launch.py tests/test_megalaunch.py::test_megalaunch_selection_does_not_activate_pick_without_agent_cli tests/test_packaging.py
    status: passed
    head: 3badabee50b3e046ddf9205db0c1ff13c6454855
    base: 0bf1d5dad2f2387ac73ecbadfb645182730a6661
    detail: 449 passed in 5:39 on the isolated clone with its source pinned by absolute PYTHONPATH.
  - command: python -m pytest
    status: failed
    head: 0e463b69b6dc460bba861fdcd4a65789969d4055
    base: 0bf1d5dad2f2387ac73ecbadfb645182730a6661
    detail: Failed in tests/test_clean_install_harness.py because the Codex sandbox rejects /dev/fd process substitution. The first failure, test_windows_walk_builds_the_fetched_ref[main], reproduces identically on clean main at 0bf1d5dad. The run was stopped after the environmental failures surfaced.
  - command: coga init <scratch repo> --user reviewer; coga build with claude/codex hidden from PATH
    status: passed
    head: 3badabee50b3e046ddf9205db0c1ff13c6454855
    base: 0bf1d5dad2f2387ac73ecbadfb645182730a6661
    detail: Real TTY at the final head. Init retained `uv tool install coga`, printed only the agent PATH requirement, and did not prompt or link; coga build failed with the same PATH-only message.
  - command: coga validate --task v1/remove-the-agent-cli-install-offer-from-coga-init --json
    status: passed
    head: 3badabee50b3e046ddf9205db0c1ff13c6454855
    base: 0bf1d5dad2f2387ac73ecbadfb645182730a6661
    detail: One task OK; no issues.
```
