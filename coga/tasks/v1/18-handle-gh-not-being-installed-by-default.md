---
title: Handle gh not being installed by default
status: in_progress
owner: zach
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
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
step: 2 (evaluate-design)
agent: claude
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

### Design decisions

This section answers the "open for the design step" questions. The owner
approves it at `review-design`.

- **Mechanism: download the official release archive.** The route needs no
  package manager and no sudo. Bootstrapping Homebrew is rejected: it needs
  sudo and the Xcode CLT, and takes minutes, which is out of proportion
  (see *Out of scope*). The documented link is the final fallback.
- **Asset per platform.** Use the archive, never the installer:
  - macOS: `gh_<v>_macOS_{arm64,amd64}.zip`. The universal `.pkg` needs
    `installer` and sudo.
  - Windows: `gh_<v>_windows_{amd64,arm64}.zip`. The `.msi` needs elevation.
  - Linux: `gh_<v>_linux_{amd64,arm64}.tar.gz`. The `.deb` and `.rpm` need
    root.

  Each archive is self-contained, and only the one binary is copied out
  (layout under *Context*).
- **Architecture.** Map `platform.machine()` lowercased: `x86_64`/`amd64` →
  `amd64`, `arm64`/`aarch64` → `arm64`. Anything else (i386, armv6/7)
  makes the route unavailable, with no prompt. Under Rosetta, x86_64 Python
  reports `x86_64` and gets the amd64 build, which runs. That is acceptable.
- **Trust: pin the version and SHA-256 digests in the package.** Do not
  resolve "latest".
  - A digest shipped in the coga wheel anchors integrity in coga's own
    release (PyPI). A checksums file fetched from the same GitHub release
    would prove only transport integrity.
  - Pinning needs no API call, so there is no rate limit and no `latest`
    redirect to follow.
  - Tests are deterministic.
  - Cost: the pinned `gh` ages between coga releases. Initial pin: 2.103.3,
    with digests under *Context*.
  - Updating: `gh` prints its own "new release available" notice. The user
    updates by re-downloading from https://cli.github.com, or by installing a
    package manager. `coga init` installs only when `gh` is missing and never
    upgrades it. The install topic says so.
- **Install directory.** `_gh_install_dir()` returns the first candidate
  that exists, is a directory, is writable (`os.access(W_OK)`), and is on
  `PATH` (reuse `init._on_path`):
  1. The parent of the unresolved `shutil.which("coga")`. This is the
     directory the user already runs coga from: uv tool's and pipx's
     `~/.local/bin` (`%USERPROFILE%\.local\bin` on Windows). Skip it when
     coga runs from a virtualenv (`sys.prefix != sys.base_prefix`) *and* the
     directory is inside `sys.prefix`, so a project `.venv/bin` or editable
     checkout never receives `gh`. uv tool and pipx place the shim outside
     the tool venv, so they pass.
  2. `Path.home() / ".local" / "bin"` on all three platforms.
  3. `Path.home() / "bin"`, POSIX only.

  System directories (`/usr/local/bin`, Windows `WindowsApps`) are never
  written. If no candidate qualifies, fall back to `~/.local/bin`, created
  with `parents=True`, and report it as off-`PATH`. If that cannot be created
  or written either, the route is unavailable.
- **Shown before the confirm.** The exact URL
  (`https://github.com/cli/cli/releases/download/v<v>/<asset>`), the pinned
  SHA-256, and the destination file path. When the destination is the
  off-`PATH` fallback, also say that it is not on `PATH` yet.
- **Gatekeeper (macOS): non-issue.** Quarantine (`com.apple.quarantine`) is
  set only by apps that opt in, such as browsers. Bytes written by urllib and
  `zipfile` carry none, so Gatekeeper never assesses the binary. gh's
  release binaries are also Developer-ID signed, which Apple Silicon's
  signature requirement needs.
- **SmartScreen (Windows): non-issue.** SmartScreen keys on the
  Mark-of-the-Web (`Zone.Identifier` stream), which browsers and Attachment
  Manager add. A file written by Python has none. `gh.exe` is also
  Authenticode-signed by GitHub.
- **Fresh-Mac `git` stub.** The `gh` offer is never reached with a stub
  `git`. `_require_init_tools` passes because `shutil.which` finds
  `/usr/bin/git`. But `_do_init` then calls `_require_git_work_tree`,
  `_host_ignores_coga` and `_check_git_identity` before
  `_offer_optional_tools`. Each of these either needs a repo the user created
  with `git init` (which triggers the CLT install) or runs `git` and hits
  the stub. The install topic's "macOS: check Git before init" already
  covers this. Better stub detection is not part of this ticket.
- **Linux with a package manager but no sudo.** `_offer_install` gives up
  without prompting. The new chain treats that as "package manager
  unavailable" and offers the download.

### Acceptance criteria

- [ ] Interactive init, `gh` missing, with a usable package manager: the
      package-manager offer is unchanged (same "Will run: …" line and
      confirm). A yes that leaves `gh` on `PATH` ends the chain, and
      `_offer_gh_login` runs as today.
- [ ] If that install exits non-zero, or leaves `gh` off `PATH`, init asks
      once more and offers the release download. It never repeats the
      package-manager prompt.
- [ ] No package manager, a manager without a `gh` package, or root needed
      with no `sudo`: the *first* prompt is the release download, on
      darwin, win32 and linux alike.
- [ ] The download prompt prints the URL, the pinned SHA-256 and the
      destination path before the confirm (default from `dep.offer_install`,
      that is yes).
- [ ] On a yes, init downloads the asset for the platform and architecture,
      verifies the pinned SHA-256 before writing anything, and copies only
      the `gh` binary into the chosen directory. The write is atomic: a temp
      file in the same directory, then `os.replace`. On POSIX the file is
      mode 0755. It never overwrites an existing file at the destination;
      that case is reported and the route is unavailable.
- [ ] On success `shutil.which("gh")` resolves, and the existing
      `_offer_gh_login` offer follows.
- [ ] Installed into the off-`PATH` fallback: init says so explicitly,
      naming the path and asking the user to add the directory to `PATH`.
      It reuses the existing "not on PATH yet — open a new shell" note,
      factored out of `_offer_install`. It prints no "needed" message and
      does not fall back further.
- [ ] A "no" at any prompt ends the chain.
- [ ] Declining, every route failing (download error, checksum mismatch,
      binary missing from the archive, unsupported architecture, no
      writable directory), or a non-interactive init prints
      ``"`gh` is needed for PR workflows, install it from https://cli.github.com"``
      to stderr. The output no longer contains
      "Optional tools not on PATH".
- [ ] A download or checksum failure prints its own one-line reason
      (yellow, stderr) before that message. No traceback.
- [ ] `coga init` never exits non-zero because `gh` is missing.
      `test_dep_check_ignores_missing_gh` still passes.
- [ ] `git`'s behaviour in `_require_init_tools` is unchanged: same offer,
      and a missing tool still exits 2.
- [ ] `op`'s note (`_note_missing_op`) and its never-offered behaviour are
      unchanged.
- [ ] `dependencies.DEPENDENCIES`'s `gh.purpose` presents `gh` as needed for
      PR workflows, still not enforced at init.
- [ ] `tests/test_init.py` covers, through a monkeypatched download seam
      with no network:
      - no-package-manager → download → success, parametrized over darwin,
        win32 and linux. Each test builds an in-memory archive in that
        platform's layout and patches the pinned digest to match.
      - package-manager install fails (non-zero exit) → download offered →
        success.
      - package-manager install succeeds but `gh` is still off `PATH` →
        download offered.
      - download declined → "needed" message, nothing written.
      - checksum mismatch → nothing written, "needed" message.
      - existing file at the destination → not overwritten.
      - fallback directory off `PATH` → explicit note, no "needed" message.
      - install-directory choice: the coga-shim directory wins, a venv
        `bin` inside `sys.prefix` is skipped, then `~/.local/bin`.
      - asset selection for each supported `(platform, machine)` pair, plus
        an unsupported one.
      - the pin table has a 64-hex digest for every supported pair.

      Existing `test_dep_check_*` assertions on "Optional tools not on PATH"
      / "gh: install from" move to the new message.
- [ ] The `coga/install` topic describes the new chain, the download route,
      the pinned version and how to update `gh`. The package copy and its
      legacy live twin under `docs/contexts/` are byte-identical
      (`tests/test_packaging.py`).
- [ ] `docs/contexts/coga-dev/codebase/SKILL.md` lists the new module next
      to `dependencies.py`.
- [ ] `python -m pytest` passes.

### Proposed shape

1. **New module `src/coga/gh_release.py`.** It is part of the `init`
   command's implementation, as `agent_cli_setup.py` is for agent CLIs. It
   is not shared infra and is not a new command. Contents:
   - `GH_VERSION = "2.103.3"` and
     `GH_ASSET_SHA256: dict[tuple[str, str], str]`, keyed by
     `(os, arch)` with os ∈ {`macOS`, `windows`, `linux`} and
     arch ∈ {`amd64`, `arm64`}.
   - `release_asset(platform: str, machine: str) -> ReleaseAsset | None`, a
     frozen dataclass with `name`, `url`, `sha256` and `binary` (`gh` or
     `gh.exe`). Pure function, so tests call it directly.
   - `download(url: str) -> bytes`, the injectable network seam: urllib with
     a timeout and a size cap. Tests monkeypatch
     `coga.gh_release.download`.
   - `extract_binary(archive: bytes, asset: ReleaseAsset) -> bytes`. It
     reads the single member whose last two path parts are
     `("bin", asset.binary)`, using `zipfile` for `.zip` and `tarfile` for
     `.tar.gz` (a regular-file member only). It never extracts the whole
     archive, and raises if the match count is not exactly one.
   - `install_dir() -> tuple[Path, bool]` (directory, on_path), following
     the rule above. Import `_on_path` from init, or move it here and
     re-export it. Prefer moving it, since this module would be its second
     user.
2. **`src/coga/commands/init.py`.**
   - Add a small `InstallOutcome` enum: `INSTALLED`, `OFF_PATH`, `DECLINED`,
     `FAILED`, `UNAVAILABLE`.
   - Split `_offer_install` into `_install_with_manager(dep, manager) ->
     InstallOutcome` and the existing `_offer_install(dep, manager) -> bool`
     wrapper, which `_require_init_tools` keeps using unchanged for `git`.
     A not-on-`PATH` result after a successful package-manager run stays
     `FAILED` for this purpose and still prints today's note.
   - `_offer_gh_release(dep) -> InstallOutcome` runs the download route:
     resolve the asset and directory (`UNAVAILABLE` without a prompt), print
     the URL, digest and destination, confirm, then download, verify,
     extract and write atomically. Catch `OSError`/`URLError`/archive errors
     into `FAILED` with a one-line reason.
   - `_offer_gh(dep) -> InstallOutcome` chains the two routes as the ticket
     orders them. A `DECLINED` from either ends the chain.
   - `_offer_optional_tools` calls `_offer_gh` for `gh`, since `gh` is the
     only dependency with `offer_install` set. When the outcome is not
     `INSTALLED`/`OFF_PATH`, or when non-interactive, it prints the "needed"
     line instead of the "Optional tools" block. Keep the call to
     `_offer_gh_login` and `_note_missing_op`. Update the docstrings.
3. **`src/coga/dependencies.py`.** Reword `gh`'s `purpose`: needed for PR
   workflows, offered at init, enforced at the point of use, init still
   proceeds without it. Leave `packages` unchanged.
4. **Tests.** Extend the `_interactive` helper in `tests/test_init.py`:
   - a `fail_install` option (non-zero exit for package-manager argv);
   - a `which` that also reports `coga`;
   - a `tmp_path` home via `monkeypatch.setenv("HOME"/"USERPROFILE")`, so
     `Path.home()` lands in the test dir.

   Add the cases listed in the acceptance criteria.
5. **Docs.** Update the `coga/install` topic (package copy plus legacy
   twin):
   - the `gh` Prerequisites bullet: needed for PR workflows, init offers it,
     init never fails without it;
   - the interactive-install paragraph: the package-manager route, then the
     release download (pinned version, verified digest, destination rule,
     no sudo), then the link;
   - one sentence on updating a downloaded `gh`.

   Add the module line in `coga-dev/codebase`.

### Out of scope

- Bootstrapping Homebrew or any package manager. That needs its own ticket
  if wanted.
- Editing shell profiles or the Windows user `PATH` to add the fallback
  directory. Init only tells the user.
- Upgrading an existing `gh`, or any `coga` command to manage `gh`
  versions.
- Making a missing `gh` fail init. That needs the owner, per *Owner
  direction*.
- Detecting the macOS `/usr/bin/git` stub.
- Downloading `git`, `op` or agent CLIs. `agent_cli_setup` is untouched.
- 32-bit and armv6 assets.
- The README install section, which belongs to `v1/17`.
- Automating the bump of the pinned `gh` version.

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

### `gh` release facts (checked 2026-11-04 against v2.103.3)

- Asset URL: `https://github.com/cli/cli/releases/download/v2.103.3/<asset>`.
  The checksums file is `gh_2.103.3_checksums.txt` in the same release.
  `https://github.com/cli/cli/releases/latest` redirects to the newest tag.
  Use it only when bumping the pin by hand.
- Archive layouts:
  - macOS zip: `gh_<v>_macOS_<arch>/bin/gh`, plus `LICENSE` and
    `share/man/...`.
  - Linux tar.gz: `gh_<v>_linux_<arch>/bin/gh`, same layout.
  - Windows zip: `bin/gh.exe` and `LICENSE` at the archive root, with no
    top directory.

  Match the member by its trailing `bin/<binary>`, not by the full path.
  `zipfile` does not restore exec bits, so chmod the file explicitly.
- SHA-256 for the initial pin, from `gh_2.103.3_checksums.txt`:
  - `gh_2.103.3_macOS_amd64.zip` —
    `a2f86418f4350ae6e9ec60d5000bdf7665728436946a97fc27fe50e6ae752682`
  - `gh_2.103.3_macOS_arm64.zip` —
    `d700207eae9ae98fe2b89535c2c087c07823d4628c56364695a5a07ef311c062`
  - `gh_2.103.3_linux_amd64.tar.gz` —
    `4c806978ffce1cec70853302a56d70ac6da4f19bae7adca4e1a8ab00633dd91d`
  - `gh_2.103.3_linux_arm64.tar.gz` —
    `ee32df2323c8847f5fac6cb6b4b69ca75828e9329a8f22f677021f7b3306ce63`
  - `gh_2.103.3_windows_amd64.zip` —
    `98d0cfa794721665d7973dd728c78aff7bd836d58f10f6d7a03568eccb0a22e0`
  - `gh_2.103.3_windows_arm64.zip` —
    `197211c98687d7770ac331fe8a3b6c198c389108c1536cdbedf659fe4703e484`

  The macOS arm64, Linux amd64 and Windows amd64 digests were re-verified
  by downloading those archives. Re-check all six against the checksums file
  when implementing.
- Existing helpers to reuse rather than fork:
  - `coga.commands.init._on_path(directory)`, the PATH-membership test.
  - `coga.commands.update.running_cli_location()`, which shows uv tool and
    pipx detection from the unresolved `sys.executable`. It is reference
    only, because the install directory keys on `shutil.which("coga")`.
  - `coga.skill_manager.download_url()`, the plain urllib fetch pattern
    (30s timeout, no size cap). `gh_release.download` should add a cap.
- `_do_init` order: `_require_init_tools`, `_require_git_work_tree`,
  `_host_ignores_coga`, `_check_git_identity`, then later
  `_offer_optional_tools`, then `_offer_agent_cli`. The `gh` chain runs where
  `_offer_optional_tools` does today, after every precondition and before
  the first write. `test_init_offers_nothing_when_preflight_fails` pins that
  ordering. Keep it green.

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

## Design status

Design written 2026-11-04 (design step): the spec is under `## Description`
(decisions, acceptance criteria, proposed shape, out of scope), and release
facts and pinned digests are under `## Context`. Recommended mechanism: a
pinned, SHA-256-verified official release archive, installed into coga's own
bin directory or `~/.local/bin`, as route 2 after the package manager.

## Open Questions

1. **Pin versus latest.** The design pins the `gh` version and digests in
   the coga package. That gives stronger integrity and no API or rate-limit
   exposure, but `gh` goes stale between coga releases. The alternative is
   to resolve `releases/latest` through its redirect and verify against
   that release's checksums file. That gets the newest `gh` but proves only
   transport integrity. Is the pin acceptable, and who bumps it, and when
   (for example, at each coga release)?
2. **Off-`PATH` fallback.** When no writable directory on `PATH` exists,
   the design still installs into `~/.local/bin` and tells the user to add
   it to `PATH`. Init does not edit shell profiles or the Windows user
   `PATH`. Is "installed, add this directory to PATH" acceptable, or should
   init skip the download and show only the "needed" link in that case?
3. **Placement.** The design proposes a new `src/coga/gh_release.py` as part
   of `init`'s implementation, like `agent_cli_setup.py`, rather than
   growing `commands/init.py`, which is about 1,860 lines. Does that fit
   the microkernel rule, or should the helpers stay inside `init.py`?
4. **Follow-up ticket?** Should detecting the macOS `/usr/bin/git` stub
   (`xcode-select -p` failing) become its own ticket? It stops a fresh-Mac
   user before the `gh` offer, and the install topic covers it only by hand
   today.
