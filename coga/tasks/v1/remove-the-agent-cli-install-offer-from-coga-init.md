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
step: 4 (review)
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

pr: https://github.com/FastJVM/coga/pull/1176
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

## Open-PR handoff (2026-11-05, claude)

PR #1176 is open at head `3badabee5`: https://github.com/FastJVM/coga/pull/1176.
`coga open-pr` confirmed `origin/main` advanced only through non-overlapping
Coga task/log state, so the branch published without a rebase.

Zach is testing the branch in a UTM macOS VM before merging, from a fresh VM
clone and a from-scratch install.

Harness note for that test: `scripts/clean-install/run.sh` and `aws-mac.sh`
build only `pypi` or `origin/main` and hardcode `git fetch origin main`, so
neither tests this branch. Testing this code needs a wheel built from
`3badabee5` and handed to the inner `wheel` mode (`container.sh`,
`macos-walk.sh`), or installed directly in the VM.

Two items are open for the owner's review gate:

- No clean `python -m pytest` receipt exists at the final head. Both earlier
  runs failed for environment reasons that reproduce on clean main: the local
  run wants an `rg` binary, and the Codex sandbox rejects `/dev/fd`. The
  focused 449-test init/launch/megalaunch/dependencies/packaging suite passes
  at `3badabee5`.
- The ripgrep finding above is still unfiled. Zach has it and has not yet said
  whether it becomes its own draft.

## Fresh-VM verification walk (2026-11-05, zach)

Attended walk on a fresh macOS guest in UTM, user `cogatest`, with no agent CLI,
no Homebrew, and no npm. That is the machine state where the removed offer
dead-ended.

Source under test: `uv tool install --force git+https://github.com/FastJVM/coga@3badabee5`.
uv resolved it to `coga==0.4.1 (from git+...@3badabee50b3e046ddf9205db0c1ff13c6454855)`,
so the run is the PR head and not the PyPI release.

Passed:

- `coga init --user zach` in a new `git init -b main` repo printed no install prompt and no agent-install URL.
- Next steps item 2 read "No agent CLI was found on PATH — coga drives Claude Code (`claude`) or Codex (`codex`). Coga requires one on PATH for agent-backed commands (`coga build`, `coga launch`, `coga ticket`)."
- `coga build` failed with "Agent CLI 'claude' not found in PATH. Coga requires the configured agent CLI on PATH for agent-backed commands." and printed nothing else.
- The `gh` and `op` install URLs still print, as this ticket intends.

Not covered: the single-installed-CLI default-agent offer needs an agent CLI in
the guest. The walk does not close the missing full-suite receipt.

An earlier run on the same guest installed from PyPI by mistake and showed the
old picker. It is the before-image, not a finding. Its `op` wording also differs,
because `_note_missing_op` landed on main after 0.4.1 shipped.

## Nico closed PR #1176 — handoff (2026-11-07, claude, from the v1/20 session)

Written from a session launched on `v1/20-ask-which-agents-to-enable-during-coga-init`,
which is blocked on this ticket. No code was changed here. The `review` step is
still this ticket's current step; verify this note before acting on it.

Nico closed #1176 at 05:01Z with one comment, no review object, and no inline
comments. Verbatim:

> coga build failed with "Agent CLI 'claude' not found in PATH. Coga requires
> the configured agent CLI on PATH for agent-backed commands." and printed
> nothing else.
>  => it's not supposed to be in the PATH but in the toml

### The change to make (Zach, 2026-11-07)

**The message is wrong. It should name the config that declared `cli = "claude"`
and point at the toml as the place to change it.**

Zach read the comment that way and confirmed it in session. The competing
reading — that `cli` should accept a path so the binary need not be on `PATH`
at all — is **rejected**: that is a design change to the agent-spawn contract,
the packaged `coga.toml` documents the opposite ("executable to spawn; launch
fails before writing any state when it is not on PATH"), and it is not this
ticket's. Zach's words: discuss it if the fix turns out to need it.

This does **not** reintroduce what the ticket removed. A remedy that points at
the toml is a config remedy, not an install remedy. Do not bring back an
install URL, an installer command, or `install_hint`; `### No agent-install
remediation` and Zach's 2026-11-05 direction both still hold.

### This is a direction change, not a bug that slipped through

The exact output Nico objects to is recorded as **passing** in
`## Fresh-VM verification walk (2026-11-05, zach)` above, and the ticket's
`### No agent-install remediation` specified it deliberately: one PATH-only
requirement, stated once, everywhere. Zach signed that off on 2026-11-05 and
Nico reversed it on 2026-11-07. Treat the walk's receipt as superseded on this
one point rather than as a contradiction to explain away.

### What the error site knows today

`dependencies.agent_cli_missing_message(cli: str)` takes only the binary name,
which is why it cannot name the table. Every caller already holds an
`AgentType` (`config.py:36`, with `.name` and `.cli`), so naming
`[agents.<name>]` needs a signature change and no new plumbing:

    src/coga/launch.py:1809, 2021, 2614   — self.agent / agent
    src/coga/megalaunch.py:2152           — agent
    src/coga/commands/ticket.py:301       — agent

Whether to also name the `coga.toml` path is open; `Config` does not obviously
expose it at these sites, so check before promising it in the text. Two tests
pin the current message: `tests/test_dependencies.py:27` and `:33`.

### The branch no longer merges, and `coga/install` was deleted under it

Branch tip `25e310236` is 49 behind main and 3 ahead. `git merge-tree
origin/main <branch>` conflicts in five paths:

    docs/contexts/coga-dev/current-direction/SKILL.md      (content)
    docs/contexts/coga/init/SKILL.md                       (content)
    src/coga/.../bootstrap/contexts/coga/init/SKILL.md     (content)
    src/coga/dependencies.py                               (content)
    docs/contexts/coga/install/SKILL.md                    (modify/delete)
    src/coga/.../bootstrap/contexts/coga/install/SKILL.md  (modify/delete)

The two modify/delete conflicts are the substantive ones. `8a88b5ada` on main
("Retire the coga/install topic", ticket
`v1/26-make-the-readme-install-section-the-only-install-p`) deleted both copies
of `coga/install` and re-homed its facts into `coga/init` and the README's
"Get started". This branch still edits both deleted files, and the PR receipt
below lists them as the owners of the no-agent-installer policy. So that policy
text needs re-homing into `coga/init` (itself conflicted) or the README as part
of resolving, not a copy of the old file restored.

### PR state

#1176 is closed, not merged, and the branch still exists, so `gh pr reopen 1176`
is available once the branch is reconciled and the message fixed. Opening a
fresh PR is equally fine; Zach wants it back in front of Nico either way. The
`## PR` receipt below is stale from `b9057a89b` — its `head`, `checks`, and the
two `install/SKILL.md` file entries all need rewriting before it goes back out.

## Review assist — message fixed, #1176 reopened (2026-11-07, claude, attended)

Attended assist with Zach. PR #1176 is **open again** at `781a3377d`, retitled
"Remove agent CLI install offers; point missing-CLI errors at coga.toml". The
ticket stays `in_progress` on `review`; no bump.

### The skill could not run as written

`code/address-pr-comments` requires an open PR with unresolved review threads.
#1176 was `CLOSED` and had **zero** review threads and zero review objects —
Nico's feedback was one top-level issue comment posted 61 seconds before he
closed it. Verified, not inferred. Reopening was Zach's explicit direction.

### The finding that shaped the fix

`shutil.which()` already accepts a full path, so `cli = "/opt/homebrew/bin/claude"`
in `coga.toml` **already worked before this change**. Proven end to end: with
`cli` pointed at a binary in a directory absent from `PATH`, launch resolved and
spawned it. So the earlier blackboard reading — that Nico's comment implied a
design change to the agent-spawn contract — was wrong on its premise. No
behavior changed; only text that denied an existing capability.

This supersedes the "competing reading is rejected" paragraph above: there was
nothing to reject, because there was no design change to make.

### What changed

- `dependencies.agent_cli_missing_message(name, cli)` — was `(cli)`. Takes the
  `[agents.<name>]` table so it can name the one line to change. Now reads:
  "Agent CLI 'claude' not found. Set `cli` in [agents.claude] in coga.toml to
  your agent CLI." No `PATH`, no installer, no URL.
- Seven call sites pass `agent.name, agent.cli` (launch ×4, megalaunch ×2,
  commands/ticket ×1). All already held the `AgentType`; no new plumbing.
- Packaged `coga.toml` `cli` comment — "either a command name or a full path".
  Only the template; `coga/coga.toml` is a `SCAFFOLD_COUNTERPART` and exempt
  from byte-matching it, so the repo's own config was untouched.
- init next-steps item 2 — dropped the PATH sentence. It deliberately does
  **not** name `coga.toml`: that reader has no agent CLI, and Nico's
  `test_init_next_steps_do_not_send_the_user_to_edit_coga_toml` (`8a8941a38`)
  forbids sending anyone to edit a `.toml`.
- `coga-dev/internals/agent-spawn` — its missing-CLI paragraph still asserted
  the PATH requirement.

### Reconciliation

Merged `origin/main` at `7c26221cb` (was 56 behind, six conflicts). The two
modify/delete conflicts were the `coga/install` copies `8a88b5ada` deleted; the
deletion was accepted and the no-agent-installer policy re-homed into
`coga/init` (both twins mirrored) and the README's Get started, which the branch
had already edited. Nothing restored from the deleted files. Now 0 behind.

Checked first that Nico had not started the same work: of the last 40 main
commits he wrote 37, and the two touching this ground (`8a8941a38` init next
steps, `9dc9eee11` op install offer — the latter Zach's) do not overlap.

### Verification

Focused suites at `781a3377d`, all passing: `test_dependencies` 4,
`test_init` 151, `test_launch` + `test_megalaunch` 412, `test_packaging` 37,
`test_ticket` + `test_compose` + `test_layout_contexts` 180. Real-pty runs with
the agent CLIs off `PATH` confirmed the new init item 2, the new `coga build`
failure (exit 2, nothing else), and the off-`PATH` `cli` spawn.

Still no full `python -m pytest` receipt, for the same reason as before: the
suite wants an `rg` binary this machine lacks, which fails identically on clean
main. Zach has the finding and has not filed it; it has now cost two PRs a
full-suite receipt.

### Left alone deliberately

README lines 86 and 132 still say "on `PATH`". Line 132 is factually right (the
scan does use `PATH`); line 86 is a Get-started prerequisite, true as advice but
not the only way. Zach scoped this change to three surfaces and the README was
not one. Flagged, not changed.

> Superseded the same day: Nico's second pass widened the scope and both README
> lines were reworded. See the next section.

## Second review pass — the PATH/toml split (2026-11-07, claude, attended)

Nico reopened and closed #1176 again, this time with two inline threads on
`init.py` (`:446` and `:581`) and the comment: *"the message was the only thing
wrong." — Not really; I skimmed through the code and could find a lot of places.*
He was right; the previous section's claim was too narrow. PR reopened at
`8d2ed4c85` with both threads replied to (not resolved — owner gate).

### The rule, from Nico via Zach

`git`, `gh`, `op` and `coga` itself are found on `PATH`. **Agent CLIs are found
through `coga.toml`.** So nothing agent-related names `PATH` at all; the remedy
is always the `[agents.*]` table. This is the durable rule for later tickets,
and it is cleaner than how this ticket's Description states it. All 16 non-agent
`PATH` mentions in `src/` stay untouched.

### Two of the finds were defects, not wording

- **`recurring_autofix.analyze_record` was an eighth presence check** with its
  own `"agent CLI {cli!r} is not on PATH, so the run cannot be analyzed"` text.
  The earlier pass found seven sites and missed it, which is precisely how a
  PATH claim survived a sweep that fixed the others. It now calls
  `agent_cli_missing_message`. **A structural guard
  (`test_every_agent_cli_check_routes_through_the_shared_message`) now fails if
  any module matching `shutil.which(*agent*.cli)` omits that function** — it
  currently covers `launch`, `megalaunch`, `commands/ticket`, `recurring_autofix`.
  Prefer extending that guard over another manual sweep.
- **`coga/first-task` documented the deleted offer**: "When the onboarding
  agent's CLI is not on `PATH`, it offers to install it and log in first." Wrong
  before this branch existed.

### Wording, for the record

Six docstrings/comments (`init.py` 446/580/588/590, `launch.py` 2008/3644),
`coga/init` and the two clean-install runbooks in both twins, README ×2, three
test references, and the stale `test_launch.py` docstring.

### Where PATH legitimately survives near an agent word

Five places, each checked against the rule. Do not "fix" these:

- `test_launch_script.py:245,1574` — `setenv("PATH", "/agents-absent")`, the
  mechanism that makes a CLI unfindable in a test.
- `test_init.py:1263` — `assert "PATH" not in agent_step`, enforcing the rule.
- `coga-dev/current-direction` — the direction log, naming `PATH` to record that
  the requirement was dropped.
- `coga-dev/testing` — what environment a spawned agent inherits
  (`build_launch_env`), not how the agent is found.

### Held for ticket 20, and said out loud to Nico

`_installed_agent_clis` still scans `PATH` for hardcoded `claude`/`codex`, so
agents are genuinely not yet found via the toml *in init*. Reason: init is the
command that creates `coga.toml`, so there is no config to read. Zach's call was
to hold the scan for `v1/20-ask-which-agents-to-enable-during-coga-init`; the
docstring now records both the reason and the owner, and the thread reply offers
to change it in this PR if Nico wants it sooner. **Ticket 20 should expect this
to be the next thing Nico asks about.**

### Verification

1280 tests at `8d2ed4c85`, all passing: launch + megalaunch + launch_script +
recurring 1007; dependencies + packaging + recurring_autofix + init 273. Plus
the real-pty runs from the previous section, which the message change did not
alter. Full `python -m pytest` still blocked on the missing `rg` binary.

### The sweep was incomplete — second pass at `b95bd3c48`

Zach asked whether the PR body reflected the changes. It did not, and checking
exposed the method error: **I grepped for `PATH` on lines that also named an
agent, so any reference phrased without one survived.** Diffing the branch
against main found five more. Use the diff, not a keyword grep, for this class
of question.

- `repl_supervisor.AgentCliNotFound` — its docstring said only this exception
  means "install the CLI / fix your PATH". The exception class for this exact
  failure still recommended an install this branch removes.
- `tests/test_launch.py` — a docstring asserting "only the PATH requirement",
  and a comment about debugging "a PATH".
- `tests/test_init.py` — "With neither CLI on PATH" and "init scans PATH for
  them".
- `code/peer-review` ×2 twins — "if your review tool isn't on PATH" is
  ambiguous about whose tool; now "isn't available".

Net across the branch, audited line by line: **38 `PATH` lines removed, 14
added**. All 14 are `assert "PATH" not in …` guards, statements of the rule, or
quotes of the removed wording explaining why a guard exists. Nothing added
asserts a `PATH` requirement.

The PR body also had two wrong counts and credited real-pty receipts taken at
an earlier head. Both fixed; the pty runs were redone at `b95bd3c48`.

Final verification at `b95bd3c48`: **1324 tests** — megalaunch + launch_script +
recurring 737, launch 270, dependencies + autofix + packaging + repl_supervisor
+ init 317 (1 skipped). Real-pty at the same head: init next step names no
`PATH`, no URL, no `coga.toml`; `coga build` prints only the new message at exit
2. Full `python -m pytest` still blocked on the missing `rg` binary.

### Five `PATH` mentions remain near an agent word — do not "fix" these

Superseding the list in the previous section, which is now stale by one entry:

- `test_launch_script.py:245,1574` — `setenv("PATH", "/agents-absent")`, the
  mechanism that makes a CLI unfindable in a test.
- `test_init.py:1263` — `assert "PATH" not in agent_step`, enforcing the rule.
- `coga-dev/current-direction` — the direction log, naming `PATH` to record the
  requirement was dropped.
- `coga-dev/testing` — what environment a spawned agent inherits
  (`build_launch_env`), not how the agent is found.

All 16 non-agent `PATH` mentions in `src/` (git ×3, gh ×5, op ×1, coga/uv and
generic tooling ×7) are untouched by design.

## PR

```yaml
title: Remove agent CLI install offers; point missing-CLI errors at coga.toml
author: claude_codex
author_evidence: Claude wrote the init-only removal and the post-review coga.toml fix; Codex extended the removal to every agent-backed command and reviewed its own extension.
head: b95bd3c4809a1e1daed6b2768ef04ce2cb4af819
base: 29df72447b0d18123cf9488dee9ffbaa498f5b6d
depth: deep
rationale: Codex reviewed changes it wrote itself, and Nico's review reversed the remedy after that. Read the diff rather than the receipt.
implementation: 'Deletes init''s "install which agent CLI?" picker, the `coga build` install exception, and the `agent_cli_setup` module. After Nico''s review the single point-of-need failure names the `[agents.<name>]` table in coga.toml instead of asserting a PATH requirement — `shutil.which` already accepted a full path, so no behavior changed. Init still scans PATH and still offers a single installed CLI as the default agent.'
deviations: Began as init-only, grew to every agent-backed command during Codex review, then changed remedy from "must be on PATH" to "set `cli` in coga.toml" after Nico's 2026-11-07 review. Coga's own `uv tool install coga` instructions stay.
limitations: 'Coga no longer says how to install an agent CLI. Users install one themselves. README lines 86/132 still say "on PATH": line 132 is factually correct and line 86 is Get-started advice, both left in scope-respecting deliberately.'
files:
  README.md: Removes agent installer links and states the prerequisite while retaining Coga's uv install.
  coga/skills/coga/testing/clean-install/SKILL.md: Legacy live twin; replaces embedded agent setup commands/URL with an operator-provided PATH prerequisite.
  coga/skills/coga/testing/clean-install/macos-aws/SKILL.md: Legacy live twin; removes the macOS agent installer command/URL.
  docs/contexts/coga-dev/codebase/SKILL.md: Removes the deleted installer module from the source map.
  docs/contexts/coga-dev/current-direction/SKILL.md: Records the owner reversal to no agent installation offers or links, then the 2026-11-07 shift to a coga.toml remedy.
  docs/contexts/coga-dev/internals/agent-spawn/SKILL.md: Points the missing-CLI remedy at the `[agents.*]` table instead of a PATH requirement.
  docs/contexts/coga/init/SKILL.md: Legacy live twin documenting scan/default behavior and the factual missing-CLI next step; also absorbs the retired install topic's agent policy.
  src/coga/agent_cli_setup.py: Deleted the now-unused agent installer/login implementation.
  src/coga/commands/init.py: Removes init's install picker and clone call, keeps scan/default behavior, and prints one statement of fact with no PATH claim and no coga.toml pointer.
  src/coga/dependencies.py: Removes agent install URLs/package/login metadata; `agent_cli_missing_message(name, cli)` names the `[agents.<name>]` table and sends the reader to coga.toml.
  src/coga/launch.py: Removes the coga-build installer exception; four call sites pass the agent type name.
  src/coga/megalaunch.py: Two call sites pass the agent type name for its FileNotFoundError and preflight boundaries.
  src/coga/commands/ticket.py: Authoring preflight passes the agent type name.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Package owner of the init contract; mirrored to docs.
  src/coga/resources/templates/coga/coga.toml: The `cli` key comment now says a command name or a full path, not a PATH requirement.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/SKILL.md: Package owner of the clean-install runbook; removes agent installer commands/URL.
  src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/macos-aws/SKILL.md: Package owner of the macOS runbook; removes agent installer commands/URL.
  tests/test_agent_cli_setup.py: Deleted tests for the removed installer module.
  tests/test_dependencies.py: Pins the absence of agent installer metadata, the coga.toml remedy, the absence of PATH, and a path-valued `cli` still naming its table.
  tests/test_init.py: Removes install-picker cases and covers no/one/both installed scan behavior plus next steps free of URL, PATH and coga.toml.
  tests/test_launch.py: Removes build-installer cases and pins the coga.toml remedy for launch, chained-handoff, and spawn-race failures.
  tests/test_megalaunch.py: Pins megalaunch's missing-agent coga.toml remedy and the absence of PATH.
review:
  reviewer: nicktoper
  kind: human
  status: changes-requested-and-addressed
  head: 25e310236ca9b4c1698b4197dffe6cefff1255eb
  base: 0a150faf1a0925530533812de8927b6dabb8d042
  detail: Nico closed the PR with one top-level comment (no review object, no inline threads) rejecting the PATH requirement in favor of the toml. Addressed at 781a3377d and the PR reopened with a reply in the same thread. An earlier Codex self-review passed at 3badabee5 against 0bf1d5dad, but it reviewed its own expansion.
checks:
  - command: python -m pytest tests/test_dependencies.py tests/test_init.py tests/test_launch.py tests/test_megalaunch.py tests/test_packaging.py tests/test_ticket.py tests/test_compose.py tests/test_layout_contexts.py
    status: passed
    head: b95bd3c4809a1e1daed6b2768ef04ce2cb4af819
    base: 29df72447b0d18123cf9488dee9ffbaa498f5b6d
    detail: 784 passed across the five runs (4 + 151 + 412 + 37 + 180). Run as separate invocations, not one command.
  - command: coga init; coga build; coga build with `cli` set to an off-PATH absolute path
    status: passed
    head: b95bd3c4809a1e1daed6b2768ef04ce2cb4af819
    base: 29df72447b0d18123cf9488dee9ffbaa498f5b6d
    detail: 'Real pty via pty.fork, agent CLIs absent from a shim PATH. Init item 2 named no PATH, no URL and no coga.toml; coga build printed only "Agent CLI ''claude'' not found. Set `cli` in [agents.claude] in coga.toml to your agent CLI." at exit 2; with `cli` pointed outside PATH, launch resolved and spawned it, proving the path form already worked.'
  - command: python -m pytest
    status: not-run
    head: b95bd3c4809a1e1daed6b2768ef04ce2cb4af819
    detail: No full-suite receipt at this head. test_edge_distribution.py needs an `rg` binary this machine lacks and fails identically on clean main. Second PR in a row blocked on it; still unfiled.
  - command: python -m pytest
    status: failed
    head: b9057a89b51d5bbd436416dc5c2ae9d4bd68dd67
    base: 0ecfd8e8f0708a52dfe7be3d9d78b3c1fe11ec67
    detail: 'Superseded, kept for history. 3 failed, 4472 passed, 11 skipped in 1:28:00; all three reproduced on clean main at 0ecfd8e8f. Two were twin-drift/broken-anchor checks against the live install/SKILL.md, which main has since deleted.'
  - command: uv tool install --force git+https://github.com/FastJVM/coga@3badabee5; coga init --user zach; coga build
    status: passed
    head: 3badabee50b3e046ddf9205db0c1ff13c6454855
    base: 0bf1d5dad2f2387ac73ecbadfb645182730a6661
    detail: Fresh macOS guest with no agent CLI, Homebrew, or npm. Covers the install-offer removal only; its PATH-requirement wording is the text Nico then rejected.
```
