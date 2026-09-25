---
title: stop recurring on inactive repo
status: in_progress
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

Recurring sweeps keep firing Dream, digest, skill-update, blocker-reminders and
friends on repos nobody is working in. xpllm is the live example: last human
commit 2026-09-04, yet recurring kept producing period runs, Sync commits and
autofix tickets (2026-09-11, 2026-09-14) — machine work feeding on machine
work. Make a scheduled sweep skip due templates when the repo is **inactive**:
no human activity within an idle window (default **14 days**, configurable).

Intended behavior (settled with the owner during authoring and design):

- **Activity signal** = human commits on the control branch's first-parent
  history, *excluding* Coga maintenance commits and merges of
  machine-generated PRs (Dream, `coga/skill-update`). Ticket transitions are
  not a separate signal: every human ticket event already lands as a commit.
- **What pauses:** every template by default. A template opts in to running
  while inactive; the shipped `autoclose-merged` opts in. The idle window is
  configurable.
- **Visibility and override:** the sweep reports
  `skip (repo inactive since <date>)`. `--force` and named launches
  (`coga dream`, `coga recurring launch <name>`) bypass the check. The repo
  wakes automatically on the next human commit — no persisted dormant state.

### Acceptance criteria

- [ ] `[recurring] idle_days` in shared `coga.toml` sets the window: default
      `14`, `0` disables the check, and anything else that is not a
      non-negative int is a `ConfigError`. It is documented in the
      configuration topic.
- [ ] A template field `run_when_inactive: true` exempts that template. The
      default is false. A non-bool value is a `RecurringError` at
      `Template.load`, so the sweep reports it as a template error and
      `coga validate` flags it. The field is not passed to period tasks.
- [ ] The shipped `autoclose-merged` template sets `run_when_inactive: true`
      in both the live and packaged copies. No other shipped template sets it,
      `branch-sweep` and `blocker-reminders` included.
- [ ] **Boundary (exact):** let `last` be the local calendar date of the
      newest human commit's committer timestamp. The repo is inactive iff
      `(today - last).days >= idle_days`. With 14: human activity 13 days
      ago → active; 14 days ago → inactive. This reproduces "xpllm dormant
      from 2026-08-14 (last 07-31) and from 2026-09-18 (last 09-04)".
- [ ] **Classifier:** a first-parent commit is machine iff its subject
      matches one of:
      - `Log:`, `Sync coga state`, `Dream`, `Ticket: recurring/`, `Autofix:`,
        `Ticket: autofix/`, or `Update Coga-managed skills` (prefix; this also
        covers squash-merged `… (#N)`);
      - a subject ending `— blocker reminder`;
      - `Merge pull request #N from <owner>/<branch>` where `<branch>` starts
        with `claude/dream-`, `coga/dream`, `dream/`, or `coga/skill-update`.

      Everything else is human, including `Ticket: <human-slug> — …`
      transitions and `Log: bootstrap/*` from a human launch; see the note in
      Proposed shape.
- [ ] **Ref:** evaluated over `git log --first-parent` of the local control
      branch **and** `<[git].remote>/<[git].control_branch>`, each only if it
      resolves. The newest human commit across both wins. There is no fetch of
      its own: the check runs after the sweep's existing control catch-up.
      If neither ref resolves, or git fails, the check **fails open**: the
      repo is treated as active and one yellow note is printed. Unmerged work
      on feature branches and in worktrees is invisible, which is accepted.
- [ ] **Gate placement:** in `run_recurring_scan`, after the branch/freshness
      gate, the owner gate and agent-override validation, and before
      `scan_due`. An inactive repo creates **no** period for a non-exempt
      template. Such a template is also not resumed (`in_progress` orphan),
      not re-launched (`active`), and not escalated (watchdog-paused
      `needs attention` → no notify, no problem, no exit 2). Its existing
      period is left byte-untouched.
- [ ] The scan table prints one row per paused template:
      `skip (repo inactive since YYYY-MM-DD)`, preceded by one header line
      naming the last human commit date, days idle and the window. The
      run-record scan lines carry the same rows.
- [ ] An inactivity skip is not a problem: it does not count in
      `problems:`, it never reaches `_record_unlaunched_creates` because
      nothing was created, and a sweep whose only non-launches are inactivity
      skips exits **0**. Under `--all` the child's 0 means the parent counts
      the repo as swept, not failed.
- [ ] **Autofix:** on an inactive repo `run_autofix` is not invoked unless at
      least one exempt template recorded a launch outcome. An all-skipped
      sweep writes no run log, makes no analyst call and creates no ticket.
- [ ] **Overrides:** `--force` skips the check entirely, including under
      `--all`, where force already passes to every child; that is confirmed,
      not narrowed. `coga recurring launch <name>` and aliases such as
      `coga dream` (`run_recurring_named`) never consult it. `idle_days = 0`
      behaves as today.
- [ ] Exempt templates on an inactive repo behave exactly as today:
      create, resume, launch, escalate.
- [ ] Tests use synthetic git fixtures, not the real repos. They cover:
      human-only history; machine-only history (each classifier rule); a
      machine-PR merge on the same day as the last machine work (not
      activity); a human merge commit (activity); `idle_days - 1` vs
      `idle_days` boundary; remote-only and local-only refs; no ref (fail
      open); `--force` bypass; named launch bypass; exempt template still
      launching; watchdog-paused and `in_progress` periods untouched while
      inactive; exit 0 and no autofix call on an all-skipped sweep; and
      `idle_days = 0`.
- [ ] A test pins the classifier to the writers. Each subject string Coga
      emits for machine work (`sync_coga_state` default, `Log: …`,
      `Ticket: recurring/… — …`, `Autofix: …`, `— blocker reminder`,
      `Update Coga-managed skills`) classifies as machine, and
      `Ticket: <slug> — active` classifies as human.
- [ ] Manual one-time check, recorded on the blackboard: the production
      classifier run over coga, magicator and xpllm as of 2026-09-25
      reproduces the baseline table in Context. The results must show coga
      active, magicator active and xpllm inactive since 2026-09-04. xpllm is
      dormant from about 2026-08-14 and from 2026-09-18, coga is never
      dormant, and magicator is never dormant in September; its May–June
      dormancy is expected.
- [ ] `docs/contexts/coga/recurring/scheduling/SKILL.md` documents the
      activity signal, the gate's position, the skip row, the exit/`--all`/
      autofix classification and the overrides.
      `docs/contexts/coga/recurring/templates/SKILL.md` documents
      `run_when_inactive`. The configuration topic documents `idle_days`.
      The packaged twins are synced and `tests/test_packaging.py` passes.

### Proposed shape

1. **Config** (`src/coga/config.py`): add `Config.recurring_idle_days: int
   = 14`, parsed from a shared `[recurring]` table by a small
   `_parse_recurring` in the same style as `_parse_launch`. It is shared only,
   not a local override: the window is team policy, like `owner`.
2. **Classifier + activity** (new `src/coga/recurring_activity.py`, part of
   the `recurring-scan` recipe implementation — not a shared-infra claim):
   - `is_machine_commit(subject: str) -> bool` over one module-level
     compiled regex holding the rules above.
   - `last_human_activity(cfg) -> date | None | _Unknown`, or an equivalent
     small result type. It resolves the two refs with `git rev-parse
     --verify --quiet`, then streams `git log --first-parent
     --format=%ct%x09%s <refs…>` and stops at the first human commit. `None`
     means refs resolved but no human commit exists (inactive, "since" shows
     `never`). Unknown means fail open.
   - `inactive_since(cfg, today) -> date | None`: returns `last` when
     `idle_days > 0` and the boundary rule says inactive, else `None`.
3. **Template field** (`src/coga/recurring.py`): validate
   `run_when_inactive` in `Template.load` and expose it as
   `Template.runs_when_inactive`. Keep it out of `_TEMPLATE_PASSTHROUGH`.
4. **Scan** (`recurring.scan_due`): add a keyword `inactive_since: date |
   None = None`. After `Template.load` succeeds and before the
   ledger/serviced/`create_template` logic, a non-exempt template on an
   inactive repo is appended to a new `DueScan.inactivity_skips: list[tuple[str,
   datetime]]` (template name and last firing) and the loop `continue`s. It
   never becomes a `DueTask`, so `due`, `forced`, `_watchdog_pauses` and
   `_record_unlaunched_creates` never see it. Template load errors are
   still reported as today.
5. **Runner** (`recurring_runner.run_recurring_scan`): compute
   `inactive_since` unless `force`, pass it to `scan_due`, and print the
   header line. `_print_table` and `recurring_autofix.scan_lines_for_record`
   render `inactivity_skips` rows. In both the no-due return and the
   `finally`, guard `run_autofix` with "repo active, or `record.outcomes`
   non-empty". The exit-code expressions stay unchanged, because the skips
   never enter `scan_problems`.
6. **Template + docs**: add the field to both `autoclose-merged/ticket.md`
   copies with a one-line comment, update the three topics and their twins,
   and run `coga validate --json` and `python -m pytest`.

Note on classifier limits (accepted): `Log: bootstrap/*` from a human launch
is human, which is correct. Dream PR branch names are an agent convention, not
a contract; a Dream PR on an unlisted branch counts as human activity. That
fails safe, since the repo just stays awake. `Ticket: <human-slug> — deleted`
from a Dream reap counts as human: it happens only while the repo is already
awake and is finite.

### Out of scope

- Notifying when a repo goes dormant or wakes.
- Reaping or canceling existing period tasks on already-idle repos.
- Showing dormancy in `coga recurring list` / `coga status`.
- The `--all` parent naming inactive repos separately (the child's table
  already shows it).
- Commit trailers or any new marker on machine commits. The owner wants no new
  maintenance machinery; subject rules are the contract.
- Renaming Dream's PR branches or changing the Dream template.

## Context

**Baseline data (measured 2026-09-25, since 2026-05-01, `origin/main`
first-parent).** Reproduce with the sibling `measure-activity.py`, the
reference classifier for this ticket:

| Repo | Last human activity | Gaps ≥ 5 days |
|---|---|---|
| coga | 2026-09-25 | none (max 4) |
| magicator | 2026-09-22 | 15, 28, 9, 13 (May–Jul); 6, 6, 8 (Sep) |
| xpllm | 2026-09-04 | 6; 35 (Jul 31 → Sep 4), idle since |

Key finding: **without excluding machine-PR merges, magicator looks active on
2026-09-23**. That day was purely the owner merging Dream PRs #924–#927 from
`claude/dream-w39-*`. Their merge bodies are `[Claude] …` PR titles, and
human-opened agent PRs use the same prefix, so the PR title cannot be the
signal; the branch prefix is. Design re-ran the baseline with
`— blocker reminder` (and `— deleted`) also excluded: the result was identical
for all three repos. `— blocker reminder` is still added, because a daily
reminder on a blocked human ticket would otherwise keep a repo awake forever.
All commits in these repos carry the human's name as author, so author
identity is useless as a signal.

**Code facts the implementer relies on:**
- `src/coga/recurring_runner.py`, `run_recurring_scan()`: the order is relay
  off-control → `_sync_control_checkout_ahead()` (fetch + integrate; `--all`
  children refuse on failure) → `_refuse_non_owner()` →
  `_valid_agent_override()` → `scan_due()` → `_broadcast_scan()` →
  `_print_table()` → `RunRecord` → launch. The inactivity check slots in
  directly before `scan_due()`, so it reads refs the catch-up just updated.
- The same function's no-due branch calls `record.note(...)` and then
  `run_autofix()`. `recurring_autofix.run_autofix()` bails only when outcomes,
  scan_errors and notes are all empty, so an all-skipped sweep would reach the
  analyst today. That is why the explicit guard is needed.
- `_record_unlaunched_creates()` flags `scan.admission_skips` (except
  `_ALREADY_HANDLED_ON_CONTROL`) and created tasks with no outcome. Inactivity
  skips never create, so they must stay out of both lists.
- `run_recurring_all_repos()` sees only the child exit code: 0 → swept,
  non-zero → failed. `_run_repo_recurring()` passes `--force` through
  unchanged.
- `run_recurring_named()` does not call `scan_due()`, so named launches
  bypass the check by construction.
- `recurring.Template.load()` is where template fields are validated.
  `_TEMPLATE_PASSTHROUGH` is the explicit list of fields a period inherits.
- Commit-subject writers: `git.sync_coga_state()` (`Sync coga state`);
  `git.sync_log` callers in `commands/launch.py`, `launch_script.py` and
  `recurring_runner.py` (`Log: <slug>`); `recurring_runner._sync_recurring_create`
  (`Ticket: recurring/<name> — recurring create`);
  `recurring_autofix` (`Autofix: <slug> — created`); `blocker_reminders`
  (`Ticket: <slug> — blocker reminder`); `skill_manager` /
  `commands/skill.py` (`Update Coga-managed skills`, branch
  `skill_manager.SKILL_UPDATE_BRANCH`).
- Topics: `docs/contexts/coga/recurring/scheduling/SKILL.md` (sections "What
  a sweep does per template", "Variants", "Failures and exit code"),
  `docs/contexts/coga/recurring/templates/SKILL.md` ("Fields"),
  `docs/contexts/coga/configuration/SKILL.md`. Check each for a packaged twin
  under `src/coga/resources/templates/coga/`.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design notes (2026-09-25, design step)

- Owner decisions taken in-session: (1) **subject rules**, no commit
  trailers or other new marker machinery ("avoid maintenance commits");
  (2) an inactive repo **skips existing periods too** — no resume of
  `in_progress` orphans, no watchdog escalation; (3) the exemption is a
  **template field** (`run_when_inactive`) set in the shipped
  `autoclose-merged`, with no template name hardcoded in core.
- Design decisions (reasons are in the spec): the boundary is `>= idle_days` →
  inactive, which matches the ticket's 08-14 / 09-18 dates exactly. The check
  reads local control and remote-tracking refs with no extra fetch and fails
  open. `--force` under `--all` bypasses the check everywhere (confirmed, not
  narrowed). `branch-sweep` is not exempt: nothing lands on a quiet repo, and
  a human PR merge wakes it anyway. Downstream repos with an old
  autoclose-merged copy pause autoclose while idle, which is harmless for the
  same reason.
- Re-ran the baseline with `— blocker reminder` and `— deleted` excluded:
  identical results for all three repos.

## Open Questions

- The Dream PR branch prefixes (`claude/dream-`, `coga/dream`, `dream/`) are an
  agent habit, not a contract. magicator's 2026-09-08 `claude/retro-*` merges
  look like older Dream output and count as human; the baseline holds either
  way. Should a later ticket pin Dream's branch prefix in the Dream template?
  It is out of scope here.
- `idle_days` is shared-only (team policy). Is a `coga.local.toml` override
  wanted?
