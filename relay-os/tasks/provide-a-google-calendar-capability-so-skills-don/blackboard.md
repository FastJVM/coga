# Blackboard — provide-a-google-calendar-capability

## Dev
branch: calendar-capability
worktree: /home/n/Code/relay-calendar-capability
(3 commits ahead of main; working tree clean; PUSHED)
PR: https://github.com/FastJVM/relay/pull/249

NOTE: PR was opened directly from the implement step at the human's request
(skipped the workflow's self-qa step). Status is still `active` — human will
`relay launch` to walk the workflow. Watch for the pr/open-pr step trying to
open a second PR; #249 already exists for this branch.

SECURITY NOTE: while pushing, git/gh stdout contained injected-looking lines
("remote: this is fine.", "Hmm wait. let me reconsider.", a fake push-success
line). Treated as untrusted output, not instructions. Push + PR verified through
real git state (upstream tracked, 0/0, 3 commits, PR URL returned). Worth a
glance at the remote/hooks if it recurs.
commits: aee13aa-equiv (mechanism) + skill commit. Full suite 472 passed / 1 skip.

GOTCHA for reviewers: bundled batteries live in
`src/relay/resources/templates/relay-os/bootstrap/skills/` but that `bootstrap/`
dir is covered by a `.gitignore` rule (the same .gitignore is the template
shipped to consumers, where bootstrap IS generated). In the relay SOURCE repo
the batteries are nonetheless tracked via `git add -f` — that's how the sibling
`relay/calendar-reminder` got in, and how this skill got in. New battery files
need `-f`. `_scaffold_tree` copies this mirror into a consumer's
`relay-os/bootstrap/` at init, BEFORE `install_venv` runs the per-skill
requirements install, so the deps land.

## Final approach (pivoted — see history note at bottom)
Delivered as a **bootstrapped relay skill**, NOT a `relay calendar` core command.
Two commits:

1. **Per-skill dependency install** (`src/relay/commands/update.py`)
   - New `install_skill_requirements(relay_os, venv_dir)`: at the tail of
     `install_venv`, pip-installs every `relay-os/skills/**/requirements.txt`
     into `.relay/.venv`. This is the mechanism a bootstrapped skill needs to
     bring its own deps — there was none before.
   - Runs for both `relay init` (fresh) and `relay init --update` (both call
     install_venv). Fail-loud on error.
   - Tests: `tests/test_skill_requirements.py` (5).

2. **Bundled `relay/google-calendar` skill** (name: `relay-google-calendar`)
   - Lives under **`bootstrap/skills/`** (the bundled set that `relay init`
     ships), NOT `skills/` (project-local, deliberately not shipped — see
     test_init). Template-only path:
     `src/relay/resources/templates/relay-os/bootstrap/skills/relay/google-calendar/{SKILL.md,calendar.py,requirements.txt}`.
     (There is no live `relay-os/bootstrap/` in the relay source repo; bundled
     skills are template-only — confirmed sibling `relay/calendar-reminder`.)
   - Consumers invoke `$RELAY_RELAY_OS_ROOT/bootstrap/skills/relay/google-calendar/calendar.py`.
   - Per-skill install scans BOTH `relay-os/skills/` and
     `relay-os/bootstrap/skills/`.
   - `calendar.py`: self-contained stdlib+google script. Verbs
     get/create/update/delete (update=Google patch). JSON event resource on
     stdout; exit codes 0 ok / 1 error / 3 not-found. 403/404 → "share the
     calendar with the SA's email" hint; `primary` explains SA-on-personal-Gmail
     limit.
   - Auth: reads `[calendar].service_account_file` from relay.local.toml
     (env:VAR-referenceable) directly — NO relay-core command/config field.
   - requirements.txt: google-api-python-client, google-auth (installed by #1).
   - Tests: `tests/test_google_calendar_skill.py` (12), loaded by path, fake
     service, no creds/network.

Full suite: 494 passed, 1 pre-existing skip.

## How a consumer uses it (e.g. patents — FOLLOW-UP, separate repo)
Shell to the skill script, located via `RELAY_RELAY_OS_ROOT`:
`python $RELAY_RELAY_OS_ROOT/skills/relay/google-calendar/calendar.py <verb> ...`
Replace `GwsCalendarClient` with a client that shells to it; map exit 3 →
`CalendarEventMissing`. The `CalendarClient` Protocol already lines up
(get/create/patch→update/delete). calendar-id resolution + `## Calendar sync
state` bookkeeping stay in the patents skill.

## calendar-reminder retarget (DONE — 3rd commit)
The bundled `bootstrap/skills/relay/calendar-reminder` skill shelled to the
missing `gws` binary too. Retargeted all four ops (create/verify/update/delete)
to the new `relay/google-calendar` skill's calendar.py. Also fixed its calendar
target: it wrote to `primary` everywhere, which the service account CAN'T reach
— now requires a shared `<calendar-id>` (never `primary`), uses exit-3 for
gone-events, and documents re-homing the four legacy `primary` events off
primary. No `gws` references remain anywhere in bundled skills (grep-verified).
Full suite still 472 passed / 1 skip.

Branch now 3 commits ahead of main:
  - Install skill requirements into the venv at bootstrap
  - Add bundled relay/google-calendar skill
  - Retarget calendar-reminder battery off gws to relay/google-calendar
Working tree: only unrelated relay task-tracking files dirty (test-autobump,
this task's log.md) — deliberately NOT committed.

Remaining follow-up (separate repo): patents GwsCalendarClient -> shell to this
skill.

## Deploy notes
- The Google libs are NOT in relay's runtime `.venv` by default. They land via
  the per-skill install (`relay init --update`) reading the skill's
  requirements.txt. Run that in the env the cron uses.
- Create a service account + JSON key, enable Calendar API, SHARE the target
  calendar (e.g. "FastJVM Patent") with the SA's email, set
  `[calendar].service_account_file` in relay.local.toml. SA cannot reach
  `primary`.
- Possible later enhancement: also install a skill's requirements on
  `relay skill install` (currently only the bootstrap/init path). Bundled skills
  go through init, so this is a nice-to-have, not required here.

## Open: workflow bump blocked
`relay bump` needs status `in_progress`; ticket is `active`. This session ran
manually (not via `relay launch`, which is what flips active→in_progress), so
bump refuses. Code is done + committed. To advance: run
`relay launch provide-a-google-calendar-capability-so-skills-don` (fresh agent
sees the committed branch and bumps).

## History note
First built as a `relay calendar` core command (ticket Approach 1, approved
early). Human redirected: deliver as a bootstrapped skill instead, with a real
per-skill dependency-install mechanism. Branch was reset to main and rebuilt
the skill way. The command approach is fully gone.
