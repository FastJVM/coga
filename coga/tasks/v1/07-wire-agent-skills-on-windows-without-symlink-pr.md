---
title: Wire agent skills on Windows without symlink privilege
status: blocked
owner: nicktoper
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

On a default Windows 11 install, which has no Developer Mode and no elevation, Windows refuses to create symlinks (WinError 1314, SeCreateSymbolicLinkPrivilege). Coga wires agent skills with directory symlinks, so on that machine Claude Code and Codex never discover the repo's `coga` skills. The user is also told the wrong reason. Found in v1/31 walk 1 (finding 8, Windows 11 Home 26300, 2026-11-10) and seen again in all four cases of v1/20's Windows walk on 2026-11-11. The v1/14 Windows Server 2025 harness most likely ran elevated, so it never hit this.

Two code paths fail the same way:

- `coga init`: `_link_skills_for_agents` (`src/coga/commands/init.py`) catches the `symlink_to` OSError and adds the link to `blocked`. That is then reported as "`.claude\skills\coga` exists but isn't a directory. Remove or convert it so skill wiring can complete." Nothing exists there: `mkdir` succeeded, and only the symlink failed. The same happens for `.codex\skills\coga`.
- `coga launch`: the skill view in `src/coga/agent_skills.py` adds every failed `symlink_to` to `skipped`. Launch then prints "Warning: skipped 31 agent skill link(s): …" with no cause and no remedy.

Done means that on a non-elevated, non-Developer-Mode Windows 11 account, init and launch wire the skills so the agent can discover them.

The fix: where Windows refuses a symlink for lack of privilege, Coga creates an
NTFS **directory junction** instead. A junction is a directory reparse point.
Any user can create one, with no Developer Mode and no elevation. Node (Claude
Code) and Rust (Codex) both report a junction as a link and follow it the way
they already follow the symlinks Coga creates on Linux and macOS. Symlinks
stay the first choice everywhere, because a relative symlink survives a repo
move and a junction does not: a junction always stores an absolute target.
Every consumer that recognizes Coga's skill links must also recognize a
junction. Otherwise the fix just moves the failure into idempotence, uninstall,
and nested-link checks. When neither link kind can be created, the user is
told the real cause and a remedy.

### Acceptance criteria

- [ ] On Windows, when `Path.symlink_to` for a skill link raises `OSError` with
      `winerror == 1314` (ERROR_PRIVILEGE_NOT_HELD), Coga creates a directory
      junction at the same path to the same directory, using the absolute,
      resolved target. Any other symlink error, and every symlink error off
      Windows, behaves as it does today: no fallback.
- [ ] `refresh_agent_skill_view()` (`src/coga/agent_skills.py`) uses that
      fallback for every per-skill link. On a non-privileged Windows account
      it reports every ref in `linked` and none as failed.
- [ ] `_link_skills_for_agents()` (`src/coga/commands/init.py`) uses the
      fallback for `.claude/skills/coga` and `.codex/skills/coga`. On a
      non-privileged Windows account a fresh `coga init` and a clone
      `coga init --user NAME` both report Claude Code and Codex as wired, and
      the clone path saves the user. Today it exits 2.
- [ ] Re-running wiring is idempotent for junctions. An existing junction whose
      resolved target is the view counts as wired and is left alone. A
      junction with any other target is removed and recreated, like a stale
      symlink is today. Removal never deletes through a junction into its
      target.
- [ ] `_has_symlink_parent()` in `agent_skills.py` treats a junction ancestor
      as a link, exactly as it treats a symlink ancestor.
- [ ] `coga uninstall` plans and removes a junction at `.claude/skills/coga`
      or `.codex/skills/coga` the same way it handles a symlink today. The
      view directory it points at, and the skills behind that, are untouched.
- [ ] Init no longer says "exists but isn't a directory" when nothing was in
      the way. Each blocked agent link carries its own cause, and the message
      states it:
      - a non-directory at the agent dir, or a non-link at `skills/coga`: the
        current "remove or convert it" wording, which is correct for that
        case;
      - a link that could not be created: the OS error text. When Windows
        refused the symlink (1314) and the junction also failed, the message
        also names both remedies: enable Developer Mode, or keep the repo on a
        local NTFS volume.
- [ ] When skill links fail, the launch warning
      (`_refresh_agent_skills_for_launch()` in `src/coga/launch.py`) states the
      cause (the first distinct `OSError` text) and the same remedy line, not
      just a count and refs. Refs skipped under a link ancestor are still
      reported, but separately from failures, so the two are not conflated.
- [ ] The init success line no longer says "symlinked". It says "linked", and
      when any agent link is a junction it adds a short parenthetical:
      Windows symlinks need Developer Mode, so a directory junction was used.
- [ ] Tests on Linux cover the fallback decision, the idempotence branches,
      uninstall planning, and every message branch. They fake a 1314 `OSError`
      from `symlink_to` and stub the junction primitive. Windows-only tests,
      gated by `conftest.windows_skip`, create real junctions. Those tests
      check detection, resolved-target comparison, removal, and that
      `shutil.rmtree` of a view holding junctions leaves the targets intact.
- [ ] `scripts/clean-install/windows-walk.ps1` adds a step after
      `coga init --user`. The step fails unless
      `.claude\skills\coga\code\implement\SKILL.md` and
      `.codex\skills\coga\code\implement\SKILL.md` are readable through the
      links. The walk runs as a fresh non-admin local user, so this exercises
      the junction path.
- [ ] Verification evidence: the Windows walk from the clean-install harness
      on this branch, with the new step passing as the non-admin walk user.
      Also, one attended check on that user, or on any non-elevated,
      non-Developer-Mode Windows account: start `claude` in the walked repo,
      confirm a `coga` skill is listed, and record the result on the
      blackboard. Without that receipt the ticket's "Done means" sentence is
      not met.
- [ ] The owning topics are updated in the same PR; see *Proposed shape*,
      step 6.

### Proposed shape

1. **Shared link primitives in `src/coga/agent_skills.py`.** This module is
   already the shared owner: init imports `refresh_agent_skill_view`, launch
   imports it, and uninstall will be a third consumer. Add these small public
   functions:
   - `is_junction(path) -> bool`. Return `False` off Windows. On Windows,
     return `os.lstat(path).st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT`,
     and treat a missing path as `False`. This form works on the 3.11 floor;
     `os.path.isjunction` arrives only in 3.12.
   - `is_dir_link(path) -> bool`: `path.is_symlink() or is_junction(path)`.
   - `link_directory(link, target, *, relative_to) -> str`. Try
     `link.symlink_to(<relative target, or absolute across drives as today>,
     target_is_directory=True)`. On `os.name == "nt"` with
     `getattr(exc, "winerror", None) == 1314`, call
     `_winapi.CreateJunction(str(target.resolve()), str(link))` instead.
     Return `"symlink"` or `"junction"`. On failure, raise an `OSError` that
     keeps the original symlink error, chained (`raise junction_exc from
     symlink_exc`) or wrapped, so the caller can report both. Move the
     existing relpath/`ValueError` cross-drive logic from
     `refresh_agent_skill_view()` into this helper.
   - `remove_dir_link(path)`. Remove a junction with `os.rmdir`, which
     removes the reparse point and never its target, and a symlink with
     `unlink`. Never use `shutil.rmtree` on a link.
   - `dir_link_points_to(path, target) -> bool`. For a symlink, keep today's
     `os.readlink` comparison against the relative target. For a junction,
     compare `os.path.normcase(os.path.realpath(path))` with the same form of
     `target`.

   Prefer `_winapi.CreateJunction` over spawning `cmd /c mklink /J`. It is
   one in-process call per link; launch makes about 31 of these per run. It
   has been present in CPython since 3.5 and is what CPython's own test
   support uses. It is private API, so import it lazily inside the Windows
   branch only, and note that in a comment.
2. **Skill view (`refresh_agent_skill_view`).** Replace the inline
   `symlink_to` with `link_directory()`. Split `AgentSkillViewResult` so
   that `skipped` keeps refs left out under a link ancestor, and a new
   `failed: list[tuple[str, OSError]]` holds refs whose link could not be
   created. `_has_symlink_parent()` switches to `is_dir_link()`.
   `_remove_existing()` stays as it is. `shutil.rmtree` on 3.8+ does not
   recurse into junctions; the Windows test from the acceptance criteria
   pins that.
3. **Launch warning (`_refresh_agent_skills_for_launch` in
   `src/coga/launch.py`).** Report `failed` with its first cause and, for the
   1314-then-junction-failed case, the remedy line. Report `skipped` on its
   own line as today. Keep it a warning, not a bail. Put the remedy text in
   one helper in `agent_skills.py`, for example
   `link_failure_hint(exc) -> str | None`, so init and launch word it
   identically.
4. **Init (`_link_skills_for_agents` in `src/coga/commands/init.py`).** Use
   `is_dir_link()` and `dir_link_points_to()` in place of `link.is_symlink()`
   plus `os.readlink`. Use `remove_dir_link()` to replace a stale link, and
   `link_directory()` to create one. Change `blocked` to carry a reason, for
   example `list[tuple[str, Path, str]]` or a small dataclass. Also track
   whether any link is a junction, for the success parenthetical. Update both
   callers: `_setup_initialized_clone()`, which stays fail-closed with exit 2,
   and `_do_init()`, which stays a warning. Fix the "symlinked into their
   skill dirs" text in both, and update the `_AGENT_SKILL_DIRS` comment and
   the docstring.
5. **Uninstall (`src/coga/commands/uninstall.py`).** The planning loop that
   fills `plan.skill_links` uses `is_dir_link()`, and `_remove_skill_link()`
   uses `remove_dir_link()`.
6. **Docs, in the same PR.** All paths are under
   `src/coga/resources/templates/coga/bootstrap/contexts/coga/`:
   - `init/SKILL.md`: change step 6 ("symlinks"), the clone section, and
     "Instruction files and skill discovery" to say "links: symlinks, or
     directory junctions on Windows without symlink privilege".
   - `skill-management/SKILL.md`: extend the paragraph on the generated
     view's links with the junction fallback and its absolute target.
   - `uninstall/SKILL.md`: the bullet on agent skill links says junctions too.
   - `docs/contexts/coga-dev/testing/SKILL.md`: one line saying the walk user
     is non-admin, so the walk exercises the junction path, and that the
     Administrator checkout does not.
7. **Tests.** `tests/test_init.py` already owns the `_link_skills_for_agents`
   idempotence tests and the view-shape assertions. Extend those, plus
   `tests/test_uninstall.py` and the `_refresh_agent_skills_for_launch`
   callers in `tests/test_launch.py`. Put the helper unit tests in a new
   `tests/test_agent_skills.py`; no file owns `agent_skills` unit tests
   today. Monkeypatch `os.name` and `_winapi`, or inject the junction
   primitive, so the Windows branch runs on Linux. Real-junction tests use
   `conftest.windows_skip`.

Order of work: steps 1 and 2 with their unit tests first, then 4 and 5, then
3, then the walk step, the docs, and the Windows verification.

### Out of scope

- A copy fallback when neither symlinks nor junctions work, for example a
  repo on a network share or FAT volume. That case gets an accurate error and
  remedy, not a third link kind.
- Having `coga launch` repair or re-wire `.claude/skills/coga` and
  `.codex/skills/coga`. Today only init creates them. See the open question
  about junctions after a repo move.
- Switching Windows to junctions unconditionally, or changing the
  POSIX/privileged-Windows symlink behavior.
- Wiring agents beyond Claude Code and Codex.
- Changing how retire (`src/coga/branchcleanup.py`, `REGENERABLE_IGNORED_DIRS`)
  or `git worktree remove` treat `.agent-skills/`. The existing classification
  by directory name already covers it. A Windows check that worktree removal
  does not follow junctions is a nice-to-have receipt, not a deliverable.

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

### Codebase facts

- **Two link layers.** `refresh_agent_skill_view()` (`src/coga/agent_skills.py`)
  rebuilds `coga/.agent-skills/` from scratch. It calls `_remove_existing()`
  and then creates one directory link per skill ref. Each link points at the
  local override or at the packaged copy under
  `packaged_template_path("bootstrap", "skills")`. `_link_skills_for_agents()`
  (`src/coga/commands/init.py`) first calls `refresh_agent_skill_view()`. It
  then links `<repo>/.claude/skills/coga` and `<repo>/.codex/skills/coga`
  (`_AGENT_SKILL_DIRS`) to that view. A non-privileged Windows user therefore
  hits 1314 at both layers. Fixing only the outer link would still leave an
  empty view.
- **Who refreshes what.** Launch calls `refresh_agent_skill_view()` through
  `_refresh_agent_skills_for_launch()` (`src/coga/launch.py`) on every run,
  but it never touches the `.claude`/`.codex` links. Only init creates those.
  The two init callers differ: `_setup_initialized_clone()` treats any
  `blocked` entry as fatal and exits 2 before saving `user`, and `_do_init()`
  prints a yellow per-entry warning and continues. The wrong "exists but
  isn't a directory" text is in `_do_init()`. The clone path says "Could not
  wire … Fix this path or its permissions", which is vague but not wrong.
- **Why the bad message happens.** In `_link_skills_for_agents()`, the
  `except OSError` around `skills_dir.mkdir()` and `link.symlink_to()`
  appends `(label, link)` to the same `blocked` list as the real "something
  is in the way" branches. The caller can't tell them apart.
- **Symlink-only checks a junction would slip past.** `Path.is_symlink()`
  returns `False` for a junction, and `Path.exists()` / `is_dir()` return
  `True` because they follow it. Every one of these checks must learn about
  junctions:
  - `_link_skills_for_agents()`: `link.is_symlink()` and `os.readlink`. A
    junction from an earlier run would otherwise fall through to
    `elif link.exists()` and be reported as blocked.
  - `_has_symlink_parent()` in `agent_skills.py`.
  - `uninstall.py`: the planning loop over `_AGENT_SKILL_DIRS`
    (`link.is_symlink()`) and `_remove_skill_link()`.
- **Fine as they are.** Both of these classify `.agent-skills` by name, not
  by link type: `branchcleanup.REGENERABLE_IGNORED_DIRS` and the
  `.agent-skills` exclusions in `skill_manager.py` and
  `tests/test_packaging.py`. The `shutil.rmtree` in `_remove_existing()` and
  in `_do_init()`'s rollback does not descend into junctions on Python 3.8+.
- **Python floor is 3.11** (`pyproject.toml` `requires-python`).
  `os.path.isjunction` / `Path.is_junction` are 3.12+, so detect junctions
  with `os.lstat(...).st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT`
  (Windows only). `_winapi.CreateJunction(target, link)` exists in every
  supported CPython on Windows. It needs an absolute target that already
  exists, and a link path whose parent exists but which does not exist itself.
- **The cross-drive precedent.** `refresh_agent_skill_view()` already falls
  back to `source.resolve()` when `os.path.relpath` raises `ValueError` across
  Windows drives. `docs/contexts/coga-dev/testing/SKILL.md` ("A Windows
  checkout and temp directory on different drives") cites it. Junctions use
  absolute targets anyway, so that note still holds.
- **Windows verification harness.** The `coga/testing/clean-install/windows-aws`
  skill (`src/coga/resources/templates/coga/bootstrap/skills/coga/testing/clean-install/windows-aws/SKILL.md`)
  says each walk creates a fresh local user in Users, Remote Desktop Users,
  and OpenSSH Users, and runs `scripts/clean-install/windows-walk.ps1 walk`
  over a password SSH logon. That user is not an Administrator, so it lacks
  SeCreateSymbolicLinkPrivilege. That is the configuration this ticket
  targets. The Administrator checkout/fix loop is elevated and does not
  reproduce the bug. The walk's `coga init --user` step currently passes
  even when the links are blocked, because fresh init only warns. That is why
  the new readability step is needed.
- **Tests that own this today.** `tests/test_init.py` has the
  `_link_skills_for_agents` idempotence test and the view assertions
  (`.agent-skills/retro/done-ticket` `is_symlink()`). Those assertions will
  need to accept either link kind only in the Windows-run variants.
  `tests/test_uninstall.py` builds `.claude/skills/coga` symlinks by hand.
  `tests/conftest.py` `windows_skip(reason)` is the required gate for
  Windows-only exclusions, per `coga-dev/testing`.
- **Origin evidence.** v1/31 walk 1, finding 8 (Windows 11 Home 26300,
  2026-11-10), and the v1/20 Windows walk on 2026-11-11, all four cases.
  `coga/tasks/v1/06-handle-gh-not-being-installed-by-default.md` refers to
  this finding as "the known Windows symlink finding" and does not fix it.

<!-- coga:blackboard -->

## Design notes

- Design step, 2026-11-20. The spec is in `## Description` / `## Context`.
- Key choices, with reasons:
  - **Symlink first, junction only on 1314.** This keeps relative links
    where they work, which survive a repo move, and leaves POSIX and
    Developer-Mode behavior unchanged.
  - **`_winapi.CreateJunction` rather than `mklink /J`.** Launch makes about
    31 links per run, and this avoids a subprocess for each. It is private
    CPython API, used by CPython's own test support. If the evaluator
    prefers to avoid private API, `subprocess.run(["cmd", "/c", "mklink",
    "/J", link, target])` is the drop-in alternative.
  - **The primitives live in `agent_skills.py`.** It has three consumers:
    view, init, and uninstall, which satisfies the microkernel rule of two or
    more real consumers. `oscompat.py` is scoped to locks and process trees.
- I had no Windows machine in this session, so nothing here has run on
  Windows. The claim that Node and Rust follow junctions like symlinks is
  from platform knowledge. The attended `claude` check in the acceptance
  criteria is what confirms it.

## Open Questions

1. **A junction breaks if the repo moves.** `.claude/skills/coga` and
   `.codex/skills/coga` are created only by init, and on a non-privileged
   Windows account they become absolute junctions. If the repo directory is
   moved or renamed, they point at nothing. Launch rebuilds only the inner
   view, and `coga init --user` is refused once `user` is set, so the user
   has no supported repair besides deleting the links and running
   uninstall + init. Options:
   (a) Accept and document it. This is the current spec; repair is out of
       scope.
   (b) Have launch also re-link the two agent links when they are missing or
       stale. This is a small extension of step 4 and touches launch.
   (c) Let `coga init --user` re-wire links when `user` is already set.
   Owner to choose. If (b) or (c), move it into scope before implement.
2. **The remedy wording when both link kinds fail.** The spec names "enable
   Developer Mode" and "keep the repo on a local NTFS volume". Should it also
   mention running elevated? I left that out on purpose. Running elevated is
   a heavier ask than Developer Mode, and it would have to be repeated for
   every init and launch, but the owner may want it listed.

---

## Blockers

- [ ] [2026-11-20 17:25] [agent:codex] id=20261120T172513 Relaunch evaluate-design from a clean, current main checkout. The supplied checkout is on refresh-v1-microkernel-readmes-after-retro, holding unmerged commit 258ca14c7 for refresh-the-v1-microkernel-task-readmes-after-the (in progress, no linked PR). All four unstaged ticket and log files matched fetched origin/main before blocking. Preserve the implementation branch and its commit when returning to main.

---

## Blocker reminders

- fcea6ff1cddb last_reminded: 2026-11-23 14:48
