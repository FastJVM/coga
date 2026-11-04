---
title: Handle gh not being installed by default
status: draft
owner: zach
workflow: code/design-then-implement
---

## Description

`coga init` should get `gh` onto the machine when it is missing, on every
platform (macOS, Windows, Linux): offer to install it, and install it on a
yes. Getting `gh` is the first step of every install. Today the offer works
only when init finds a known package manager. `init._package_manager` tries
`brew` on macOS, `winget` on Windows, and apt-get, dnf, pacman or brew on
Linux. `init._offer_install` returns False when none is found, and also when
sudo is needed but missing. The clearest case is a fresh Mac, which has no
Homebrew. In those cases the user falls through to a yellow "Optional tools
not on PATH" warning. Give `init` a route to `gh` that works on all three
platforms without a package manager, and present `gh` as needed rather than
as one more optional tool.

Order of routes when `gh` is missing:

1. **A package manager is present.** Keep today's offer (`brew`, `winget`,
   or `apt-get`/`dnf`/`pacman` with sudo).
2. **That install fails, or no package manager is usable.** Ask again and
   fall back to the package-manager-free route. Package-manager failures
   include a non-zero exit, a missing package (older Debian/Ubuntu or RHEL
   without GitHub's repo), sudo missing or refused, and `gh` still not on
   `PATH` afterwards.
3. **Everything fails or the user declines.** Show the plain "`gh` is
   needed" message with the install link.

A "no" at any prompt ends the chain. Never ask twice for the same route.

Done when: on each of macOS, Windows and Linux, interactive `coga init` on
a machine with no usable package manager and no `gh` asks to install `gh` and, on a yes, installs a working `gh`. Success means
`gh` resolves on the current process's `PATH`, and init then offers
`gh auth login` as it already does. An install that only becomes visible in
a new shell must say so explicitly, using `_offer_install`'s existing note. Declining, a failed install, or a
non-interactive init prints a clear "`gh` is needed for PR workflows, install
it from https://cli.github.com" message, not the "optional tools" heading.
`init` still never fails because `gh` is missing. `tests/test_init.py`
covers the no-package-manager path for each platform, and the fallback
after a failed package-manager install, through an injectable install seam.
No test touches the network. The install topic describes the new
behaviour.

### Owner direction

- Zach on 2026-11-04: "install it if it's not there! or ask the user". The
  default is to install, behind the same yes/no confirm `_offer_install`
  already uses (default yes). Nothing installs without a yes.
- Zach on 2026-10-21: `gh` is required and should be installed, offered
  through `coga init` if that is the way to do it.
- "Required" means *presented* as needed. It does not mean `required_at_init`.
  `git` is the only tool that stops init, and a user who never opens PRs must
  still be able to init. Every `gh` consumer already enforces it at the point
  of use. Ask the owner before turning a missing `gh` into an init failure.

### Open for the design step

The design step picks the mechanism. The owner approves it at `review-design`.
Weigh at least these options:

- **Download the official `gh` release for the platform** from
  `github.com/cli/cli/releases` into a user-writable directory on `PATH`. No
  package manager and no sudo are needed. The design must cover:
  - platform and architecture detection (arm64 or amd64);
  - checksum verification against the release's checksums file;
  - which directory is on `PATH`, and what happens when none is writable;
  - how the exact command or URL is shown before the confirm.
- **Bootstrap a package manager first**, for example Homebrew and then
  `brew install gh`. This is a much larger change to the user's machine:
  Homebrew's curl-pipe-bash installer needs sudo and the Xcode Command Line
  Tools, and takes minutes. It is probably out of proportion.
- **Documented route only.** This is the fallback whatever is chosen: an
  explicit, non-"optional" message with the install link.

The design must also settle:

- **Install directory, per platform.** The default macOS `PATH` is
  `/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`. `/usr/local/bin` is
  root-owned and may be absent on Apple Silicon without brew. `~/.local/bin`
  is not on `PATH` by default. Consider the directory that holds the running
  `coga` executable, such as uv tool's or pipx's `~/.local/bin`: the user can
  already run coga from there. Windows and Linux need the same answer.
- **Asset, per platform.** Releases ship:
  - macOS: `gh_<v>_macOS_{arm64,amd64}.zip` and a universal `.pkg`. The
    `.pkg` needs `installer` and sudo, so the zip is the no-sudo route.
  - Windows: `.zip` and `.msi`.
  - Linux: `.tar.gz`, `.deb` and `.rpm`.

  Prefer the archive that needs no admin rights.
- **Trust.** The checksums file comes from the same release over HTTPS, so it
  proves integrity only. Decide whether that is enough, or pin the version
  and digest in the package. Also decide how "latest" is resolved: the API
  has rate limits and fails offline. Say how the user updates a `gh`
  installed this way.
- **Gatekeeper and SmartScreen.** On macOS, urllib downloads carry no
  quarantine attribute and `gh` is notarized, so this is likely a non-issue.
  Check the Windows equivalent too. State the conclusion explicitly for both.
- **Fresh-Mac `git`.** `/usr/bin/git` on a fresh Mac is a shim that triggers
  the Xcode Command Line Tools install, and `shutil.which` sees it as
  present. Check what this user hits in `_require_init_tools` and the git
  steps before the `gh` offer ever appears.
- **Linux with a package manager but no sudo.** `_offer_install` already
  gives up here. The download route should cover it.
- **No package-manager bootstrap here.** If the design wants one, split it
  into its own ticket.

## Context

### Current code

The functions below are in `src/coga/commands/init.py` unless named
otherwise. Cite them by symbol; line numbers drift.

- `_offer_optional_tools`:
  - offers every missing non-`required_at_init` dependency whose
    `offer_install` is not None. Today that is only `gh`.
  - then calls `_offer_gh_login`.
  - prints any tool still missing under "Optional tools not on PATH (init
    continues without them):". That heading is the message to replace for
    `gh`.
- `_package_manager` returns the first available entry from a per-platform
  candidate list. On darwin the list is `["brew"]`.
- `_offer_install(dep, manager)`:
  - returns False when `manager` is None or not in `dep.packages`;
  - otherwise prints "Will run: <argv>" and confirms with
    `default=dep.offer_install`;
  - runs the command and re-checks `PATH`, printing a "not on PATH yet — open
    a new shell" note.
  - A new install route should reuse this confirm/verify shape rather than
    fork it.
- `dependencies.DEPENDENCIES` holds the `gh` entry:
  - `offer_install=True`, `install="https://cli.github.com"`;
  - `packages` for brew, apt-get, dnf, pacman and winget;
  - a `purpose` string saying it is "Not required at init". Update that
    wording if the positioning changes.
- `PACKAGE_MANAGERS` and `NEEDS_ROOT` hold the per-manager argv prefixes and
  the managers that need sudo.
- The `gh` tests in `tests/test_init.py` are the `test_dep_check_*` family.
  They monkeypatch `shutil.which`, `sys.platform` and the confirm. Extend
  them.

### `op` half already landed

`v1/25-position-op-as-optional` is done. `op` now has `offer_install=None`,
is never offered, and is kept out of the `_offer_optional_tools` list.
`_note_missing_op` prints its own note. Leave that wording and behaviour
intact.

### Docs to update in the same PR

- `src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md`
  is the owner. Its legacy live twin `docs/contexts/coga/install/SKILL.md`
  must stay byte-identical, which `tests/test_packaging.py` enforces. Edit
  both.
- Two sections describe today's behaviour:
  - "Prerequisites" calls `gh` "recommended but not required at init".
  - The paragraph on what interactive `coga init` offers to install names
    the package managers.
- The README install section is out of scope.
  `v1/17-separate-installing-coga-from-installing-its-depen` owns the README's
  required/optional dependency split and will cite this ticket's outcome.

### Why

This is finding 8 of the macOS/Windows install test. Owner reversal on
2026-09-30: users read a missing `gh` as a broken, unprofessional install and
churn.

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

Previous ref: `marketing/fix-installer/handle-gh-not-being-installed-by-default` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
