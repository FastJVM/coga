---
title: test-install-on-windows
status: active
owner: zach
workflow:
  name: human/run
  steps:
  - name: execute
    skills: []
    assignee: owner
step: 1 (execute)
agent: claude
---

## Description

A human install and first-task walk on a fresh native Windows environment,
the Windows counterpart to `v1/29-test-and-fix-install-on-macos-and-windows`.
Zach follows only the public README and linked user documentation on his own
Windows PC in a disposable VM, recording every point where a new user gets stuck.
Zach owns the entire walk and the completion decision; this ticket has no
agent preparation or verification step.

Owner clarification, 2026-10-27: v1 must actually work on Windows and install
easily. The native core port merged in PR #1093; its former import failure is
no longer the expected stopping point. Run the complete walk after
`v1/14-interactive-coga-launch-on-native-windows` lands, using a release-candidate
wheel built from a recorded commit. Use the existing Windows harness guidance
where useful; this ticket supplies the attended first-user evidence.

Done means a clean install, `coga init`, agent authentication, the documented
new-repo/onboarding path where applicable, and an actual first ticket reaching
`done` with its result inspected. Record the Windows version, Python version,
candidate commit, wheel hash, exact commands, friction, and per-step results.
Route product failures to the existing installer or Windows ticket for fixes
through its code workflow, then rerun affected steps against an unmodified
candidate containing the fixes. Keep this ticket open until the complete walk
passes. A successful `--version`, `--help`, or init alone does not satisfy this
gate. Hand the evidence to `v1/33-review-all-doc` and
`v1/43-publish-coga-1-0-as-the-final-v1-step`;
the release ticket owns the repeat check against the published 1.0 artifact.

## Context

This is a human-run release check, using the single owner-held `execute`
step in `human/run`. Zach records the run evidence on this ticket's blackboard,
inspects the completed first task's result, and closes this ticket only after
the done criteria are satisfied. Product fixes are outside this ticket's scope;
link the owning installer or Windows ticket and the candidate used for each
retest.

Follow `coga/workflows/human/run.md` for the human lifecycle: activate with
`coga mark active v1/31-test-install-on-windows`, perform the walk, then close
with `coga mark done v1/31-test-install-on-windows` once the evidence satisfies
the done criteria. No agent launch is needed. Zach selects and records the
exact candidate and VM baseline after the prerequisite lands.

The `coga/testing/clean-install/windows-aws` skill at
`coga/skills/coga/testing/clean-install/windows-aws/SKILL.md` documents the
existing automated Windows route. Its `Walk` section is useful for candidate
provenance and evidence conventions, but its Windows Server install/init
smoke does not replace Zach's attended native Windows walk on his own PC.
Follow the public README and linked user documentation during the walk;
record any undocumented intervention as friction. See
[the numbered queue](README.md) for release ordering: the native Windows
interactive-launch work must land before this complete first-task check.

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

Previous ref: `marketing/fix-installer/test-install-on-windows` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Production notes

### Documentation coordination — 2026-10-29

`v1/33-review-all-doc` reviewed candidate
`bd72b19d2a13972005285252b53df7504350bbc7`. It still refuses native Windows
agent sessions, so the README explicitly withholds a Windows first-task claim.
PyPI 0.4.1 predates even the core port. After
`v1/14-interactive-coga-launch-on-native-windows` lands, this ticket still owns
the attended install/authentication/first-task-through-done walk against an
identified unmodified candidate. Return its Windows/Python versions, commit,
wheel hash and results to ticket 33 so documentation can be refreshed and
accepted. No Windows execution or acceptance occurred in the docs pass.

### Chosen walk route — 2026-11-09

Zach runs the walk on his own Windows PC in a Windows 11 guest under
VirtualBox, following `coga/skills/coga/testing/fresh-vm/SKILL.md` for the VM
and `coga/skills/coga/testing/clean-install/human-walk/operator-guide.md` for
the walk itself. A new user account on the host does not substitute, because
it inherits machine-wide Git, Python and winget packages.

- VirtualBox with the Microsoft Windows 11 ISO, Skip Unattended Installation
  ticked so the setup screens are walked.
- 8 GB memory, 4 CPUs, 64 GB disk. Defer the product key and record the
  edition and activation state.
- Local `cogatest` account when setup offers one; do not rely on
  `start ms-cxh:localonly`.
- Record the fresh-vm baseline before installing anything, then snapshot the
  guest as bare.
- Restore that snapshot for every re-walk. Deleting the VM through VirtualBox
  would delete the snapshot with it.
- Install the candidate by pinned commit, not from PyPI: release 0.4.1
  predates the Windows port.
- The candidate is a `main` commit after PR #1189, which merged `v1/14` on
  2026-11-09 while that ticket sits at its review step.

An agent assist records findings per the human-walk skill. Zach keeps
execution and the completion decision.

### Walk 1 summary — 2026-11-10

Walk 1 passed. A fresh Windows 11 Home VM (build 26300) went from nothing to
a first ticket at `done` by following the README: uv, Python 3.11, Git
2.56, Claude Code 2.1.322, then coga built from main ffa0dc1e3 as a wheel,
because PyPI 0.4.1 predates the Windows port. The native launch, step
handoffs and the watcher all worked. Five things will stop or confuse a new
user. (1) The README's uv command fails silently under Windows' default
`Restricted` execution policy: the window just closes. The
`-ExecutionPolicy ByPass` form is needed. (2) Init cannot create symlinks
without Developer Mode, so agent skill wiring is skipped and blamed on a
file that "exists but isn't a directory" when nothing is there. (3)
Onboarding gives a Claude-only, no-remote repo the two-agent
`code/design-then-implement` workflow. The code tickets then stop after
design with a "codex not found" error, whose advice points the wrong way.
(4) `uv python install` leaves no `python` command, so the agent hits the
Microsoft Store stub and reports that Python isn't installed. (5) The README
never says to create a project folder or repo, while PowerShell opens in
`C:\WINDOWS\system32`.

Smaller friction: the README has no install links for Git or Claude Code;
its `git var GIT_AUTHOR_IDENT` step is easy to miss and repeats init's own
clear check; init's offer to install `gh` triggers winget and UAC prompts
and is then followed by "install gh from cli.github.com"; owner-step
handoffs don't say what to do next; and Git's LF/CRLF warnings and the
watcher's internal messages print to the user. The full step log and
findings 1–11 follow; fixes are owned by v1/33 (docs), v1/43 (release) and
the init, onboarding and Windows-launch owners. This walk changes no code
or docs.

### Walk 1 (cold) — setup and baseline, 2026-11-10

Route as executed (supersedes the chosen-route notes above where they differ):

- Host: Windows 11 Home 25H2 (build 26200), WSL2 enabled, so Hyper-V and
  VBS with Memory Integrity are on.
- VirtualBox 7.2.22 was abandoned. Under Hyper-V/WHP, the guest hung on every
  restart (black screen, no disk I/O). Turning the hypervisor off failed
  because VBS kept it loaded, and the host security settings were restored.
  This is a VM setup artifact, not a Coga finding.
- VM app: VMware Workstation Pro 26H1u1 (build 25688693), personal use,
  running alongside Hyper-V with side-channel mitigations on. Guest
  `coga-win11-walk`: 8 GB, 4 vCPU, 64 GB NVMe, NAT, vTPM (TPM-only
  encryption), EFI. Installed from `Windows11_Client_x64_en-us_26300_9457.iso`
  with "install the OS later" (no Easy Install).
- Guest: Microsoft Windows 11 Home, 10.0.26300, build 26300, 64-bit, no
  product key. OOBE updates were skipped ("Update later").
- Account: local user `walker` (not `cogatest`). Shift+F10
  `start ms-cxh:localonly` still worked on this build. Untested as a result:
  the Microsoft-account and OneDrive known-folder layout that most consumer
  installs have.
- Snapshots: `bare` (first sign-in done, powered off, no tools) and
  `bare + tools` (VMware Tools added for clipboard and drag-drop, a setup
  addition; restore this one for re-walks).
- Candidate: `main` at `ffa0dc1e304fa2d609870160911c0d203a0a1ff8` (contains
  PR #1189 / v1/14; PR #1192 / v1/20 is not included). Wheel
  `coga-0.4.1-py3-none-any.whl`, SHA-256
  `03f215a60764205ea376af5c9b9170188bcf24c8c07e52447166e39b6591278b`, built
  with `uv build --wheel` on the helper host and dragged into the guest's
  Downloads (VMware Tools). In the guest, `Get-FileHash` reported
  `03F215A6…6591278B`, which matches.

Baseline (guest PowerShell, before any install):

```
Caption                  Version    BuildNumber OSArchitecture
Microsoft Windows 11 Home 10.0.26300 26300       64-bit
Get-ExecutionPolicy: Restricted
Get-Command: python.exe -> C:\Users\walker\AppData\Local\Microsoft\WindowsApps\python.exe (Store alias)
             winget.exe -> C:\Users\walker\AppData\Local\Microsoft\WindowsApps\winget.exe
             (git, py, uv, coga, claude, codex, gh absent)
```

Findings (predictions until the walk reaches them):

1. **The wheel version is indistinguishable from PyPI** (prediction, low).
   The candidate wheel reports 0.4.1, the same as the PyPI release that
   predates the Windows port, so `coga --version` cannot tell them apart.
   Owner: v1/43 release versioning. Status: open.
2. **The README has no working native-Windows install command** (prediction,
   high). It says PyPI 0.4.1 does not run on Windows but still says
   `uv tool install coga`. The walk substitutes the candidate wheel at this
   step. Owner: v1/33 docs / v1/43 release. Status: open.
3. **The default execution policy is `Restricted`** (confirmed by finding 5). The
   `irm … | iex` uv installer is unaffected, but any `.ps1` shim or profile
   step would be blocked. Owner: TBD if hit. Status: open.
4. **PowerShell opens in `C:\WINDOWS\system32`** (observed, watch). A
   non-elevated PowerShell (IsInRole Administrators = False) launched from
   Start in this guest starts in `system32`, not `$HOME`. A user who follows
   the README without changing directory could run uv, Git or `coga init`
   there. The walk deliberately leaves the directory alone to see whether the
   README steers the user out. Owner: v1/33 docs, if the walk confirms it.
   Status: open.
5. **The README's uv install command silently fails on default Windows 11**
   (observed, high). In regular PowerShell, `irm https://astral.sh/uv/install.ps1 | iex`
   closed the terminal window, and `uv` was "not recognized" in a new window.
   Confirmed cause: the uv installer refuses to run under execution policy
   `Restricted` (the Windows 11 client default, finding 3) and calls `exit`,
   which closes the interactive session before the user can read the message.
   Rerun in a child process (`powershell -c "irm … | iex"`), it printed:
   `Error: PowerShell requires an execution policy in [Unrestricted,
   RemoteSigned, Bypass] to run uv. For example, to set the execution policy
   to 'RemoteSigned' please run: Set-ExecutionPolicy RemoteSigned -scope
   CurrentUser`. The walk continued with the one-shot `-ExecutionPolicy ByPass`
   form, which leaves the policy `Restricted` so later steps are still tested
   against the default. Windows Server 2025, where the README was tested,
   defaults to `RemoteSigned`, so the harness never saw this. uv's own docs use
   `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`.
   Owner: README Windows section (v1/33 docs; Windows install ticket).
   Status: open.

Walk 1 step results:

- S1 uv. The README command failed (finding 5). The ByPass form installed
  uv 0.13.7 (316c827e0 2026-11-03, x86_64-pc-windows-msvc) to
  `C:\Users\walker\.local\bin` and said to restart the shell. In a new
  PowerShell window, `uv --version` worked.
- S2 Python. `uv python install 3.11` installed CPython 3.11.18
  (cpython-3.11.18-windows-x86_64-none, `python3.11.exe`) in 23.54s. No
  friction.
- S3 Git. Found by web search: git-scm.com/install, "Click here to download",
  giving Git for Windows 2.56.0(4) x64. All installer defaults were kept, on
  purpose: initial branch "Let Git decide" (`master`, while coga's
  `git_control_branch` defaults to `main`, so watch init and first commit),
  bundled OpenSSH, `core.autocrlf=true` (the README says this is fine, so the
  walk tests that claim), PATH "Git from the command line and also from
  3rd-party software".
  The installer finished (release notes and Git Bash unticked). The VM was
  shut down and resumed later the same day (not reverted). In a new
  non-admin PowerShell window, `git --version` printed
  `git version 2.56.0.windows.4`. The window again opened in
  `C:\WINDOWS\system32` (finding 4). Result: pass, no friction beyond
  locating the installer.
- S4 Claude Code. The README names "Claude Code's native installer" but gives
  no link. Found by an Edge search for "install claude code windows 11",
  which led to code.claude.com/docs/en/setup. That page's top banner offers
  the desktop-app download, a different product from the CLI; the PowerShell
  command `irm https://claude.ai/install.ps1 | iex` is the third block, after
  macOS/Linux. Run in the same non-admin window, it printed nothing for a
  long stretch while downloading (it looks hung; friction). It then printed
  `Claude Code successfully installed!`, version 2.1.322, at
  `C:\Users\walker\.local\bin\claude.exe`. It worked under the default
  `Restricted` policy, unlike the uv installer (finding 5), so the policy
  failure is specific to uv's installer. Result: pass, with friction (no
  README link, desktop-app banner, no progress output).
- Install-source decision (2026-11-10): the package is not released until a
  source install has been proven, so the walk installs from source rather
  than PyPI. PyPI 0.4.1 predates the native-Windows port. The candidate is a
  wheel built from origin/main ffa0dc1e3 with `uv build --wheel`. A wheel is
  the artifact PyPI would serve, so it is the closest stand-in for the future
  `uv tool install coga`. A `git+https://...@<sha>` install was considered
  and not used, because it adds a clone-and-build step that end users will
  not have. Deviation from the README: S5 replaces `uv tool install coga`
  with `uv tool install <path to wheel>`. Once the release ships, a short
  re-walk is needed to verify the plain PyPI command.
- S5 coga. `uv tool install $HOME\Downloads\coga-0.4.1-py3-none-any.whl`:
  resolved 25 packages in 1.31s, prepared in 11.23s, installed in 1.26s,
  `coga==0.4.1 (from file:///C:/Users/walker/Downloads/...)`, then
  `Installed 1 executable: coga`. `coga --version` printed `coga 0.4.1` in
  the same window, with no new window needed and no PATH warning. The output
  matches PyPI's 0.4.1 exactly (finding 1 confirmed: from the version alone,
  the user cannot tell they have the Windows-capable build). Result: pass.
- S6 README "Change into your project's Git repository." Prediction: a new
  Windows user has no repo, and the README gives no `mkdir`/`git init` step
  even for its "New, otherwise empty Git repo" path. Every PowerShell window
  so far opened in `C:\WINDOWS\system32`, so a literal reader would run
  init there. The walk creates `$HOME\coga-walk` with `git init`, which
  uses Git's default `master` branch (watch against coga's
  `git_control_branch = "main"`).
  Executed: `cd $HOME; mkdir coga-walk; cd coga-walk; git init` printed
  only `Initialized empty Git repository in C:/Users/walker/coga-walk/.git/`,
  with no branch-name hint. `git symbolic-ref --short HEAD` printed `master`.
- S7 README identity check. `git var GIT_AUTHOR_IDENT` printed
  `Author identity unknown` / `fatal: unable to auto-detect email address
  (got 'walker@coga-walk.(none)')`. Friction: the walker did not spot the
  check in the README. It sits mid-paragraph, not in a command block, and
  `git var` is an unfamiliar command.
- S7a deliberate deviation: ran `coga init --user walker` before setting an
  identity, to test the missed-step path. Init refused, before writing
  anything, with a red message: `git has no identity configured on this
  machine — coga is git-backed and \`coga init\` commits coga/ into your
  repo, but git cannot author a commit (Author identity unknown). Tell git
  who you are, then re-run \`coga init\`:` followed by the two
  `git config --global` commands. The guard is `_check_git_identity`,
  src/coga/commands/init.py:705. Result: pass; the message renders correctly
  in Windows Terminal, em dash included.

Finding 6 (docs, minor; owner v1/33; open): the README's manual
`git var GIT_AUTHOR_IDENT` pre-check repeats `coga init`'s own fail-loud
guard (S7a) and is easy to miss (S7). Suggest dropping it: a user who skips
it gets a clear fix from init anyway. The README also says to set the
identity "in this repo" (no `--global`), while init's message says
`--global`; they should agree.

Finding 7 (docs, moderate; owner v1/33; open): the README's "Change into your
project's Git repository" gives no way to create one for its "new, otherwise
empty Git repo" path, and PowerShell opens in `C:\WINDOWS\system32` (finding
4). A new user needs `mkdir <name>; cd <name>; git init` spelled out.

- S8 identity set: `dir` printed nothing, so the failed init left no files.
  Then `git config --global user.name "Walker Test"` and
  `git config --global user.email "walker@example.com"`.
- S9 `coga init --user walker` (real run).
  - Prompted `` `gh` is not installed (GitHub PR workflows). Will run: winget
    install --id GitHub.cli -e. Install it now? [Y/n] ``. The README does not
    mention this prompt (it only says gh is optional for init). Answered y
    (the default). winget then showed its first-run `msstore` source
    agreement (Y), downloaded gh 2.103.3 (msi, 14.7 MB), verified the hash,
    and raised a UAC prompt for GitHub CLI (verified publisher GitHub, Inc.;
    focus on "No" by default). Accepted, and it installed successfully.
  - Init then printed `Installed 'gh', but it is not on PATH yet — open a new
    shell...` and, right after, `Optional tools not on PATH (init continues
    without them): - gh: install from https://cli.github.com`. These
    contradict each other: the user is told to install a tool init has just
    installed.
  - It also printed an `op` (1Password CLI) notice, plus a green Slack
    notification config block, unprompted.
  - `Initialized coga repo at C:\Users\walker\coga-walk\coga`, wrote
    coga.local.toml with user "walker".
  - YELLOW: `Skipped Claude Code skill wiring —
    C:\Users\walker\coga-walk\.claude\skills\coga exists but isn't a
    directory. Remove or convert it so skill wiring can complete.` and the
    same for `.codex\skills\coga`. Nothing was at those paths: the repo had
    only been created by `git init`.
  - `Set [git] control_branch = "master" in ...coga.toml — this repo has no
    'main' branch.` This resolves the master/main watch item: init adapts.
  - It updated .gitignore, wrote CLAUDE.md and AGENTS.md, and printed
    `Committed coga/ as 8159202c5e9b`.
  - Next steps named `coga build` (Claude) or `coga build --agent codex`.
    There was no default-agent question, because Claude is already the
    template default.

Finding 8 (bug, high; owner: the Windows-launch follow-up, new ticket
needed; open): on default Windows 11, init's agent skill wiring fails and
the message misreports the cause. `_link_skills_for_agents`
(src/coga/commands/init.py:1665) calls `link.symlink_to(...)`. Without
Developer Mode or elevation, Windows refuses to create symlinks (WinError
1314, SeCreateSymbolicLinkPrivilege). The `except OSError` branch puts the
link on the `blocked` list, which is reported as "exists but isn't a
directory. Remove or convert it". So the user is told to delete a file that
does not exist, and Claude Code and Codex get no `coga` skill discovery in
the repo. The v1/14 Server 2025 harness most likely ran elevated, where
symlinks work, so it never hit this. Confirmed in the VM:
`Test-Path .claude\skills\coga` printed `False`, and
`Get-ChildItem -Force .claude\skills` listed an empty directory. So
`mkdir` succeeded and only the symlink creation failed; nothing "existed". Fix directions: a junction
(`mklink /J`, which needs no privilege) or a copied view on Windows, plus a
distinct message for symlink failure.

Finding 9 (UX, minor; owner: init; open): after init installs gh via
winget, the optional-tools summary still says "gh: install from
https://cli.github.com". It should say "installed; open a new shell". The
`op` and Slack blocks add noise to a first run, and the README does not
mention init's install offer.

Watch item resolved: the `master` default is handled. Init pins
`control_branch = "master"` and says so.
- S10 `coga build`. It ran `coga launch coga-build` and found the agent
  CLI at `C:\Users\walker\.local\bin\claude.EXE`. YELLOW: `Warning: skipped
  31 agent skill link(s): _template, bootstrap/delete-task,
  bootstrap/dream/scan/contract-audit, ...` (cut off at terminal width).
  This is likely the same symlink-privilege failure as finding 8, now in the
  launch-time skill view. Further output: `[notification] no channels
  configured`; `[git] no 'origin' remote configured — coga state committed
  on local 'master' only` (printed twice); `entering step 1
  (gather-and-spec)`; the prompt was written to
  `C:\Users\walker\AppData\Local\Temp\coga-coga-build-*.md` (12081 chars);
  then Claude Code v2.1.322 started its first-run setup (theme picker).
  coga asked no question before launch, despite init's "one question about
  what you want to build" (watch: whether the agent asks it).
- S11 Claude first run inside `coga build`: theme picker (default Dark),
  login method → "Claude account with subscription" → browser login → "Login
  successful". Workspace trust prompt for `C:\Users\walker\coga-walk` →
  Yes. The composed coga prompt rendered as the first message, ending with
  `coga-launch: <id>`. Claude then asked `What do you want to build?`, so the
  "one question" comes from the agent, not from coga before launch (resolves
  the S10 watch). Claude ran in auto mode. Result: pass; the missing skill
  links (finding 8) did not block onboarding.
- S12 vision approval → step handoff. Claude drafted a vision without asking
  follow-ups ("The scope is clear"), listing open decisions. The walker
  typed `Approved`. Claude wrote the vision and bumped. Then the native
  Windows watcher (v1/14) printed: `[coga watcher] stopping REPL —
  trigger=sentinel-file (COGA_DONE_SENTINEL touched)`, `CTRL_BREAK sent to the
  agent's process group`, Claude's `Resume this session with: claude
  --resume <id>`, `child still alive after 2.0s — terminating its Job
  Object`, `child exited with code 0x00000000 after our stop`, `reporting
  exit 0 (completion observed)`. Launch then entered step 2
  (generate-batch) and started a fresh Claude session. Result: pass. The
  sentinel stop and Job Object fallback work on Windows 11 Home. Cosmetic:
  the watcher's internals (CTRL_BREAK, Job Object, hex exit code) and
  Claude's "Resume this session" hint print to the user; the hint is
  misleading, because coga moves on by itself.
- S13 generate-batch. Claude tried a Bash `python - <<'EOF'` helper and got
  the Windows Store stub: `Python was not found; run without arguments to
  install from the Microsoft Store...`. It recovered ("No Python on this
  machine, so I'll make the edits directly") and edited the ticket files.
  It proposed three draft tickets: build-the-today-date-script and
  add-a-minimal-test-for-the-today-script (both `code/design-then-implement`),
  and decide-the-output-format (`draft-for-human`). On `Approved` it ran
  `coga bump coga-build` (done). The watcher stopped the REPL again (Job
  Object fallback, exit 0), and launch printed `coga-build: task is done`.
  `coga status` listed the 3 drafts (operator `claude?`, step 1), plus
  `Recurring: 9 templates · 9 due` and one hidden done task. Result: pass.
  Onboarding reached done on native Windows 11 Home.

Finding 10 (docs/env, moderate; owner v1/33; open): the README's
`uv python install 3.11` gives the user no `python` command. uv installs a
managed interpreter and exposes only a versioned shim, so `python` resolves
to the WindowsApps Store stub found in the baseline. The agent's first
Python call failed with the Store message; the walker had expected Python to
work. Suggested directions: `uv python install 3.11 --default`, or a README
note. This matters more for Python projects, because the onboarding example
is itself a Python script.

Finding 11 (onboarding, high; owner: coga-build generate-batch, the
v1/20-adjacent agent selection; open): on a Claude-only machine with no git
remote, onboarding gave both code tickets `code/design-then-implement`. Its
`evaluate-design` and `peer-review` steps are `other-agent`, and per the
workflow text they fail loud (`unresolvable-step-assignee`) when no peer
resolves; "a single-agent install uses `code/with-self-review` instead".
Its `open-pr` step `requires: pr`, which needs a GitHub remote and gh auth.
So neither starter code ticket can reach `done` on this install without
the user changing the workflow. The walker spotted this unprompted: "isn't
code/design-then-implement a peer-review workflow? I only have Claude".
CONFIRMED (S17): `coga launch build-the-today-date-script` ran step 1
(design). Claude wrote the spec ("The spec validates cleanly") and bumped
to evaluate-design. The watcher stopped the REPL with exit 0, and launch
stopped with, in yellow: `build-the-today-date-script: next step needs agent
'codex' but Agent CLI 'codex' not found. Set 'cli' in [agents.codex] in
coga.toml to your agent CLI. Stopping; then run 'coga launch
build-the-today-date-script' to continue.` The peer resolves to `codex`
(not `unresolvable-step-assignee`), so the failure surfaces only after the
user has already spent a design step. The suggested remedy is also
misleading for this user: they have no Codex, and pointing `[agents.codex]
cli` at Claude would make Claude review itself under Codex's name. The real
remedies are switching the ticket to `code/with-self-review` (plus a no-PR
path, since there is no remote) or installing Codex, and the message names
neither. Fix directions: onboarding (generate-batch) picks a workflow that
fits the agent CLIs actually installed and whether a remote exists;
`coga launch` checks every step's agent at launch, before step 1; the
error names the single-agent workflow.
- S14 first ticket: `coga launch decide-the-output-format` (draft-for-human).
  draft → active → in_progress, step 1 agent-produces. Claude wrote four
  format options (A–D) to the blackboard and recommended A. Unprompted, it
  noted that `%-d` is Linux-only and fails on Windows. It said "Python isn't
  installed on this machine, so I worked out the sample outputs by hand"
  (finding 10 again). On "no changes, go ahead and bump" it ran
  `coga bump` → `step 2 (human-owns-and-finishes) → walker`; the watcher
  stopped the REPL; launch printed `decide-the-output-format: next step
  hands off to walker; returning to caller`. Friction: the handoff names no
  next action. It does not say to open the ticket, record the choice, run
  `coga bump`, then `coga launch` again for step 3. The walker had to be
  told.
- S15 owner step and finish. The walker opened the ticket in Notepad, added
  `Decision: A — "Tuesday, 2026-11-10". Chosen by walker.`, ran
  `coga bump decide-the-output-format`, then
  `coga launch decide-the-output-format` (step 3 report-to-coga). Claude
  replaced "Open for owner" with a `## Report (step 3)` section: decision,
  the code `datetime.date.today().strftime("%A, %Y-%m-%d")`, and follow-ups
  (move the vision's deferred decision; the examples were hand-derived
  because there is no Python on PATH). It committed with `git commit`; Git
  printed `warning: in the working copy of
  'coga/tasks/decide-the-output-format.md', LF will be replaced by CRLF the
  next time Git touches it`. It said "There's no remote to reconcile with",
  then `coga bump ... --message ...` → `decide-the-output-format: done`. The
  watcher stopped the REPL; the Job Object fallback ran; the child exited
  with `0x0000007C`, reported as `exit 0 (completion observed)`; launch
  printed `decide-the-output-format: task is done`. Result: PASS. A first
  real ticket reached done on native Windows 11 Home.
  - autocrlf watch: works as the README says, but Git's LF→CRLF warning is
    shown to the user on agent commits (cosmetic, and confusing to a new
    user).
  - Watcher: the child exit code varies after a forced stop (0x0 vs 0x7C),
    and coga correctly reports completion either way.
- S16 result inspected. `coga status --all`: decide-the-output-format done,
  coga-build done, two code tickets still draft at step 1 (design).
  `git log --oneline` on `master`: 22 commits, from `8159202 Create coga via
  coga init` through `cc3fcfe Ticket: decide-the-output-format — done` and
  `61822e4 Log: decide-the-output-format`. Each lifecycle change is its own
  `Ticket:`/`Log:` commit, which is by design but noisy for a one-line
  decision. The blackboard holds the A–D comparison, the walker's decision
  and the step-3 report. Result: pass. Walk 1's done criterion is met.
