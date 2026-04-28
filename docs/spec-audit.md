# Relay spec audit

A feature-by-feature comparison of `docs/spec.md` against the current
implementation in `src/relay/` and `relay-os/resources/`. Test baseline:
`pytest -q` → **109 passed** on Python 3.12.

Legend:

- ✅ implemented as specified
- ⚠️  implemented but deviates from spec — described inline
- 🟡 partially implemented — what's missing called out
- ❌ not implemented
- ❓ open in spec — not yet decided

Cross-references use `file:line` against `src/relay/`. The "open points"
section at the bottom merges spec.md's own *Still underspecified* list
with new gaps surfaced by this audit; it's the to-do list for the next
spec pass.

---

## 1. Configuration

### `relay.toml` (`config.py`)

| Spec | Status | Notes |
|---|---|---|
| `version`, `default_status` top-level fields | ✅ | `config.py:98-102`. `default_status` defaults to `"draft"` when absent. |
| `[agents.<type>]` blocks: `cli`, `interactive`, `auto`, `file`, `mode` | ✅ | `config.py:144-158`. Stored as `AgentType` dataclass. |
| `[assignees.<name>]` block: `agents` map (nickname → type), `slack` | ✅ | `config.py:161-172`. |
| `[slack].webhook` | ✅ | `config.py:105`. |

### `relay.local.toml`

| Spec | Status | Notes |
|---|---|---|
| `user` field | ✅ | `config.py:107-112`. |
| `[secrets]` map with `env:VAR_NAME` resolution to live env vars | ✅ | `config.py:118, 175-189`. |
| Gitignored | ✅ | Present in `.gitignore` and `relay-os/.gitignore`. |

### Agent dispatch key `(user, nickname)`

✅ — `Config.agent_type_for(user, nickname)` at `config.py:50-63` looks up
the user's `[assignees]` block, finds the nickname, and returns the
matching `[agents.<type>]` config.

---

## 2. Repo layout

| Spec path | Status | Notes |
|---|---|---|
| `relay-os/rules.md` (inlined into every prompt) | ✅ | `paths.py:10`, composed at `compose.py:47-49`. |
| `relay-os/context.md` (inlined into every prompt) | ✅ | `paths.py:34`, composed at `compose.py:52-54`. |
| `relay-os/skills/<path>/SKILL.md` arbitrary depth | ✅ | `paths.py:18`, `skill.py`. |
| `relay-os/contexts/<path>/SKILL.md` arbitrary depth | ✅ | `paths.py:26`. |
| `relay-os/workflows/<path>.md` arbitrary depth | ✅ | `paths.py:14`, `workflow.py`. |
| `relay-os/recurring/*.md` | ✅ | `paths.py:30`, `recurring.py`. |
| `relay-os/tasks/<slug>/{ticket,log,blackboard}.md + task.lock` | ✅ | `tasks.py:50-70`, `lock.py`. |
| `relay-os/bootstrap/<name>/ticket.md` shims | ✅ | `paths.py:46-51`, `tasks.py:100-110`. |
| `relay-os/scripts/cron.sh` | ⚠️ | Present, but invokes a non-existent flag. See §6. |

`relay-os/.relay/` (vendored CLI + venv from `relay init`) is implemented
but not described in `spec.md` repo layout. Worth a one-line mention.

---

## 3. Core primitives

### Ticket (`ticket.py`)

| Frontmatter field | Status | Notes |
|---|---|---|
| `title` | ✅ | property `Ticket.title`. |
| `status` (draft/active/paused/done) | ✅ | All four valid (`validate.py:33`). |
| `mode` (interactive/auto/script, default interactive) | ✅ | `Ticket.mode`. |
| `owner` | ✅ | `Ticket.owner`. |
| `assignee` | ✅ | `Ticket.assignee`. |
| `watchers` (list) | 🟡 | Field is read/written from frontmatter but no `Ticket.watchers` accessor and **no Slack code path uses it** (see §5). |
| `workflow` (frozen `{name, steps[]}`) | ✅ | Snapshot taken at create via `Workflow.freeze()`. |
| `step` (`"N (step-name)"`, 1-indexed) | ✅ | `Ticket.step_index`, `Ticket.current_step`. |
| `contexts` (list of paths) | ✅ | `Ticket.contexts`. |
| `skill` (only on bootstrap shims) | ✅ | `Ticket.skill`. |

**Description vs Context body sections** — both extracted at compose time
(`compose.py:62-65, 78-81`). ✅

### Status & mode

- All four statuses (`draft`/`active`/`paused`/`done`) accepted everywhere
  they're checked. ✅
- `default_status` from `relay.toml` honored at task creation
  (`create.py:115`, `recurring.py:91`). ✅
- All three modes routed correctly (`launch.py:79-87`). ✅ Script mode
  short-circuits to `launch_script.run_script_mode`.

### Workflow (`workflow.py`)

| Spec | Status | Notes |
|---|---|---|
| YAML frontmatter `name`, `description`, `steps[]` | ✅ | |
| Each step has `name` + optional `skill` | ✅ | `WorkflowStep` dataclass. |
| Inline instructions via `## <step-name>` heading | ✅ | `Workflow.inline_instructions`. |
| Frozen-into-ticket snapshot, not reference | ✅ | `Workflow.freeze` at create time. |
| In-flight tickets unaffected by workflow edits | ✅ | Flow uses the frozen copy; live workflow only consulted for inline body resolution at compose time. |
| No `run` field on steps | ✅ | Removed per spec. |

### Skill / Context (`skill.py`)

- `SKILL.md` frontmatter: `name`, `description`. ✅ — `script` (optional)
  also accepted; not in spec but harmless.
- Distinction enforced at the API surface:
  - skills attached to **workflow steps** only
  - contexts attached to **tickets** only

### Blackboard (`blackboard.md` resource + `blackboard.py`)

⚠️ **Template stripped**. Spec (lines 382-420) shows a default scaffold
with `## Plan`, `## Notes`, `## Findings`, `## Blockers`, `## Decisions`.
The shipped resource at `src/relay/resources/blackboard.md` is a one-line
placeholder. The spec itself argues *for* minimalism (line 378), but the
visible template still has all five sections. Pick one and update the
spec or restore the template.

`render_blackboard(title)` uses a `{task_title}` placeholder that the
current template doesn't contain — a no-op replacement. Minor.

`blackboard.py:append_blocker` writes timestamped lines under a
`## Blockers` section, creating the heading if missing. ✅

### Logfile (`logfile.py`)

✅ Format `YYYY-MM-DD HH:MM [actor] message` matches spec exactly.
Append-only, written only by CLI side-effects (`create`, `launch`,
`step`, `panic`, `feed`).

### Lock (`lock.py`)

| Spec | Status | Notes |
|---|---|---|
| File-existence is the lock | ✅ | |
| `holder: <nickname>` + `acquired: <ISO Z>` body | ✅ | `lock.py:86-90`. |
| Stale detection in validate (default 24h) | ✅ | `validate.py:54`, `lock.is_stale`. |
| `--force` to break stale locks | ✅ | `launch.py:39, 102-108`. |
| Released on `step` final, on `panic`, on launch exit | ✅ | Plus SIGINT/SIGTERM cleanup at `launch.py:141-146`. |

❓ **Open in spec, observed in code:** acquire timing for `mode: script`
is unspecified. Implementation: `launch_script.run_script_mode` does not
acquire `task.lock` (script mode is one-shot). Worth pinning down.

---

## 4. CLI commands

### `relay create` (`commands/create.py`, `cli.py:61`)

| Spec | Status | Notes |
|---|---|---|
| `relay create "<title>"` scaffolds a `draft` ticket | ✅ | |
| Auto-launches `bootstrap/ticket` skill on the new task | ✅ | `create.py:88-90` calls `launch_command(task=ref["slug"])`. |
| `--no-launch` for scripted use | ✅ | `create.py:37, 80-81`. |
| Slug-only naming, lowercase, hyphenated, ≤50 chars | ✅ | `slugify.py`. |
| Slug collision auto-suffix `-2`, `-3`, … | ✅ | `create.py:139-143`. |
| Validate context refs at create time | ✅ | `create.py:118-121` raises on missing. |
| Validate workflow + skill refs at create time | ✅ | `create.py:127-133`. |
| Scaffold ticket.md + blackboard.md + log.md (first entry) | ✅ | `create.py:166-176`. |
| `--description / -d` shorthand | ✅ — extra | Not in spec, but matches "minimal ticket" example. |
| Recurring template integration | ⚠️ | See §6 — implemented as separate `relay recurring check` rather than `relay create --check-recurring`. |

**Spec contradiction surfaced:** the *Still underspecified* block lists
"create-with-suggestions integration" as open. The bootstrap/ticket skill
is the implementation, but the spec doesn't mention `--no-launch` (it's
implied by "scripted use"). Document the actual contract.

### `relay launch` (`commands/launch.py`)

| Spec | Status | Notes |
|---|---|---|
| `relay launch <task-id> [title]` positional, `[title]` is bootstrap factory shorthand | ✅ | `launch.py:33-38`. |
| Slug exact / unique-prefix / ambiguous-prefix-error resolution | ✅ | `tasks.resolve_target` + `resolve_task`. |
| Verify status ∈ {draft, active}; error otherwise | ✅ | `launch.py:67-71`. |
| Resolve `(current_user, assignee_nickname)` → agent type | ✅ | `launch.py:91-93`. |
| Verify `agent.cli` exists in PATH | ✅ | `launch.py:96-97`. |
| Inject secrets as env vars from `relay.local.toml` | ✅ | `launch.py:117-118`. |
| Compose prompt to `/tmp/relay-<slug>-<ts>.md` | ✅ | `compose.write_prompt_file`. |
| Acquire lock for normal tasks | ✅ | `launch.py:101-108`. |
| Bootstrap shims: no lock, no status flip, factory shorthand | ✅ | `launch.py:52-63, 99-101`. |
| Append log line "launched in {mode} mode" | ✅ | `launch.py:121-125`. |
| Slack FYI on launch | ✅ | `launch.py:126-130`. |
| Cleanup on exit / SIGINT / SIGTERM | ✅ | `launch.py:132-146`. |
| Fail loud when CLI binary not found | ✅ | `launch.py:96, 153-155`. |
| Fail loud on missing context/skill at compose | ❌ | **Real deviation.** `compose.py:57-60` *silently skips* missing context files; `compose.py:127-130` and `:148-151` inline a `*Skill file not found at <path>.*` placeholder and **launch proceeds**. Spec says: *"Error. List the missing references. Do not launch."* (line 765). Create-time validation does fail-fast, but a context that disappears between create and launch slips through. |
| Composition order (8 layers per spec lines 738-751) | ⚠️ | Layers 1-8 match. Implementation appends a 9th "Task description" section *after* the blackboard (`compose.py:78-81`). Spec puts the description body inside the ticket (already covered by inline-context handling) and lists blackboard as the trailing layer. Either fix the order (move description into the inline-context layer) or update spec to describe it. |

### `relay step` (`commands/step.py`)

| Spec | Status | Notes |
|---|---|---|
| Positional `<next-step-number>` (1-indexed) | ✅ | `step.py:21-22`. |
| `--task` required option | ✅ | |
| Refuse if task not `active` | ✅ | `step.py:37-38`. |
| Refuse if no workflow | ✅ | `step.py:40-42`. |
| Refuse backward movement | ✅ — extra | `step.py:48-49`. Sensible; not in spec. |
| Update `step` field in ticket | ✅ | |
| Set `status: done` + release lock on last step | ✅ | `step.py:55-66`. |
| Append log line `"advanced to step N (step-name)"` or `"task done"` | ✅ | |
| Slack FYI | ✅ | |

### `relay panic` (`commands/panic.py`)

| Spec | Status | Notes |
|---|---|---|
| `--task <id> --reason "<text>"`, both required | ✅ | |
| Append timestamped blocker line to blackboard | ✅ | `panic.py:42` → `append_blocker`. |
| Append log line | ✅ | |
| @mention task owner in Slack | ✅ | `panic.py:49-52`. |
| Release lock | ✅ | `panic.py:46`. |
| Stop the agent | 🟡 | The CLI exits 0; spec implies the *agent process* should also stop. Today the agent has to read the panic acknowledgment and decide to exit. Consider returning a non-zero exit code so the parent agent can detect it. |
| Change task status (e.g. to `paused`)? | ❓ | Open in spec. Implementation leaves status untouched. |
| Format of blocker line | ❓ | Open in spec. Implementation: `"- [<ISO ts>] [<actor>] <reason>"` (`blackboard.py:51-55`). |

### `relay feed` (`commands/feed.py`)

| Spec | Status | Notes |
|---|---|---|
| Posts an FYI to Slack channel | ✅ | |
| `--task` required | ✅ | (resolves spec open question) |
| `--message` required | ✅ | |
| Append log line | ✅ | |
| Auto-include task context in posted message | ⚠️ | Posts as `"<assignee>: <message> (<slug>)"` — task slug only, no title or further context. Spec asks "raw string vs auto-context" — pin down the format. |
| Character limit | ❌ | Not enforced. |

### `relay status` (`commands/status.py`)

| Spec | Status | Notes |
|---|---|---|
| One-line per task: id, title, assignee, step, mode | ✅ | Plus `status` column. |
| Hide `done` by default; `--all` to include | ✅ — extra | Not in spec, sensible. |
| Filtering (`--assignee`, `--status`) | ❌ | Open in spec. |
| Sorting (`--sort`) | ❌ | Open in spec. |
| Output format | ⚠️ | Uses Rich tables. On narrow terminals (≤80 cols) the title column wraps to one character per line — see live `relay status` in this repo. Worth pre-truncating titles or shipping a flat one-line-per-task fallback. |

### `relay recurring check` (`commands/recurring.py`)

⚠️ **Spec internally contradicts itself.** Spec line 684 lists `relay
recurring check` as a foreground command, but spec line 996 (in
*Removed*) says `relay recurring` was absorbed into `relay create
--check-recurring`. Implementation matches line 684 (recurring is its
own subcommand). Cron script (§6) tries to call the absorbed-form flag
that doesn't exist.

Action: pick one, then update the other.

| Spec (per command table) | Status | Notes |
|---|---|---|
| Scan recurring templates, scaffold due tasks | ✅ | `recurring.check_recurring`. |
| Idempotent (skip already-created period) | ✅ | `recurring.py:79`. Period key is heuristic per cadence (`_period_key`). |
| Schedule frontmatter, mode default `auto` | ✅ | `recurring.py:87`. |
| Skip `_*` templates | ✅ | `recurring.py:64-65`. |

### `relay init` (`commands/init.py`)

Spec says "manual repo setup works for v1", listed under can-defer. In
practice fully implemented and well-tested.

| Behavior | Status | Notes |
|---|---|---|
| `relay init [path]` scaffolds fresh `relay-os/` from upstream | ✅ | |
| Refuses if `relay-os/` already exists | ✅ | |
| `--update` refreshes vendored CLI + `_*` scaffolds, leaves user config | ✅ | |
| Creates `.relay/` venv with the matching pinned upstream | ✅ | |
| Wires Claude / Codex skill discovery via symlinks | ✅ | |
| Writes `relay.local.toml` template | ✅ | |
| Commits initial scaffold in git | ✅ | |

This deserves a paragraph in `spec.md` rather than a "may not need"
footnote.

### `relay validate` (script, not CLI subcommand) (`validate.py`)

Per spec the dream/drift skill embeds a deterministic validator. Today
the validator is exposed as `python -m relay.validate [--json]` (the
canonical command in `CLAUDE.md`).

| Check | Status | Notes |
|---|---|---|
| Required files per task (ticket, log, blackboard) | ✅ | |
| Stale-lock threshold (default 24h) | ✅ | Not configurable from CLI yet — would belong as a flag. |
| Stuck-active-task threshold (default 72h idle) | ✅ | |
| Workflow step → skill exists | ✅ | |
| Ticket context → context exists | ✅ | |
| Assignee/agent in `relay.toml` | ✅ | |
| Status value valid | ✅ | |
| `--json` output | ✅ | |
| Exit 0 / 1 / 2 (clean / issues / tool error) | ✅ | |

⚠️ Validator is **not invoked by the dream skill yet** — `bootstrap/dream/scan.py` exists but the spec links validation to the dream skill. Confirm wiring or rephrase spec.

---

## 5. Slack feed

| Spec | Status | Notes |
|---|---|---|
| Posts via webhook in `[slack].webhook` | ✅ | `slack.py:43-54`. |
| Two tiers: `post_feed` (FYI), `post_mention` (@user) | ✅ | `slack.py:21-29`. |
| Translates assignee → Slack user ID via `[assignees.<x>].slack` | ✅ | `slack.py:35-40`. |
| Falls back to `@<name>` literal if no Slack ID | ⚠️ | Slack does **not** render `@username` as a mention. Either map at config-load time (require a Slack ID for any human assignee) or surface a warning. |
| `relay create` → FYI "new task created" | ❌ | **Missing.** `commands/create.py:78` only echoes to terminal; no Slack post. Spec line 897 says `relay create` posts a FYI. |
| `relay launch` → FYI with mode | ✅ | `launch.py:126-130`. |
| `relay step` → FYI on advance / completion | ✅ | `step.py:61-76`. |
| `relay panic` → @mention to owner | ✅ | `panic.py:49-52`. |
| `relay feed` → FYI | ✅ | `feed.py:40-44`. |
| Assignee-change notifications | ❌ | No code path observes assignee edits — humans edit the ticket directly. Spec lines 902-903 imply auto-watch and @mention triggers on assignee→human flips. |
| Status-change notifications | ❌ | Same — no observer when humans flip `status`. |
| Watchers list additive @mentions | ❌ | `watchers` is in the frontmatter but never read by `slack.py`. |
| Owner/assignee implicit auto-watch | 🟡 | Owner is @mentioned only on panic. Assignee surfaces by name in step messages. There's no centralized "compute recipients for this event" function. |

### Slack: take-aways

The Slack feed is the spec's *primary awareness layer*. Today it covers
the agent-driven events but not the human-driven ones (ticket edits,
assignee/status flips, watchers). The two open `relay-os/tasks/` tickets
`finish-slack-integration-features` and
`use-slack-as-a-sync-channel-for-tickets` look targeted at exactly this.

---

## 6. Cron runner & recurring

`scripts/cron.sh`:

```sh
exec relay create --check-recurring
```

❌ **`relay create` has no `--check-recurring` flag.** The actual
implementation is `relay recurring check`. Both copies of the script
ship the broken command:

- `src/relay/resources/cron.sh`
- `src/relay/resources/templates/relay-os/scripts/cron.sh`
- `relay-os/scripts/cron.sh` (live)

Symptom: `set -eu` plus typer's "Got unexpected extra argument" exit code
2 → cron run fails silently for the user, no recurring tasks materialize.

Fix is one line. The deeper fix is reconciling the spec contradiction
(§4 `relay recurring check`) so the script and CLI agree.

The pidfile-locking part of the script is correct and matches spec.

---

## 7. Self-bootstrapping

### `bootstrap/ticket` skill

✅ Fully implemented at `src/relay/resources/skills/bootstrap/ticket/SKILL.md`.
Behavior matches spec: interview, scan inventory, edit frontmatter, edit
description, note rationale on blackboard, stop at draft, never invent
workflows or contexts.

### `bootstrap/dream` skill

🟡 Implemented:

- `src/relay/resources/skills/bootstrap/dream/SKILL.md`
- `src/relay/resources/skills/bootstrap/dream/scan.py`
- `src/relay/resources/workflows/bootstrap/dream-run.md`
- `src/relay/resources/recurring/weekly-dream.md`

Wiring gaps to verify:

- The recurring template `weekly-dream.md` is in `resources/`, not
  copied into a fresh `relay-os/` by `init` (only `_template.md`
  scaffolds get installed). Either ship the active template or
  document that users opt in.
- The deterministic validator (`relay.validate`) is mentioned in spec
  as belonging to the dream skill, but `scan.py` is a separate piece of
  Python and doesn't call `relay.validate`. Decide whether dream owns
  validation or just consumes it.

### Bootstrap shim tickets

✅ `relay-os/bootstrap/ticket/ticket.md` exists. Frontmatter pins
`skill: bootstrap/ticket`, no status, no workflow. `launch.py:99-101`
treats bootstrap shims as stateless re-entry points (no lock, no status
check). Factory shorthand (`relay launch bootstrap/ticket "title"`)
works at `launch.py:54-63` via `_scaffold_from_shim`.

### `bootstrap/ticket` is the only shim shipped

Future shims (`bootstrap/dream`, etc.) are anticipated by spec but not
yet present.

---

## 8. Base prompt

✅ Files exist and cover spec sections 1-7 (identity, files, blackboard
discipline, step transitions, escalation, feed, YAML discipline):

- `src/relay/resources/prompt.md`
- `src/relay/resources/prompt-interactive.md`
- `src/relay/resources/prompt-auto.md`

Composition wires them in correct order at `compose.py:36-43`. Script
mode skips both base prompt and mode block (no agent spawned).

---

## 9. Crash recovery

Per spec, manual in v1: blackboard is the persistence layer; humans
clear stale locks; relaunch picks up from blackboard.

- ✅ Blackboard included in composed prompt at `compose.py:73-76`.
- ✅ Stale locks flagged by `relay.validate`.
- ✅ `relay launch --force` breaks stale locks.

No automatic crash detection. Matches spec.

---

## 10. Error model

| Spec failure case | Status | Notes |
|---|---|---|
| Lock can't be acquired (held) | ✅ | `LockHeldError` includes holder + acquired ts. `--force` to break. |
| `relay launch mode:script` exits non-zero → log + Slack | 🟡 | Logging done in `launch_script.run_script_mode`; **no Slack notification on script failure**. Spec lines 942-943 require it. |
| `relay step` on non-active | ✅ | |
| `relay create` with missing context/skill refs | ✅ | Validated in `scaffold_task`. |
| `relay create` outside a relay-os/ tree | ✅ | `find_repo_root` raises `ConfigError`. |
| `git push` rejected | n/a | Git is not invoked by the CLI today. |
| `relay launch`: assignee not in user's agents | ✅ | `agent_type_for` raises `ConfigError`. |
| `relay launch`: missing context/skill | ❌ | Compose silently skips/placeholders. See §4 `relay launch`. |

---

## 11. Open points

This consolidates spec.md's *Still underspecified* section with new gaps
this audit surfaced. Items marked **NEW** are not in spec.md today.

### A. Fix-or-document spec contradictions

1. **`relay recurring check` vs `relay create --check-recurring`.** Spec
   describes both, only the first exists. `cron.sh` calls the second
   (broken). Pick one and update the other side.
2. **Blackboard default template.** Spec body shows full
   Plan/Notes/Findings/Blockers/Decisions skeleton; spec narrative
   argues for minimal; `resources/blackboard.md` is minimal. Update
   the spec body to match the chosen direction.
3. **Composition order layer 9.** Spec lists 8 layers ending with
   blackboard; implementation appends a 9th `## Task description`. Move
   description into the inline-context layer or extend spec to 9.
4. **Missing context/skill at launch.** Spec error table says fail
   loud; compose silently skips/placeholders. **NEW** — fix compose to
   match spec, or update spec to allow soft skip.
5. **`relay create` posts to Slack.** Spec table says yes; implementation
   doesn't. **NEW** — wire it or remove from the spec table.

### B. Resolve before next milestone (spec called these blocking)

6. **`relay create` arg interface.** Today: `relay create "<title>" [-d desc] [--no-launch]`. Spec asks for definitive list of fields auto-set vs CLI args. Document.
7. **Lock lifecycle precision.** Acquire/release events for each command
   (covered for normal tasks; spec says open). Decide:
   - Does `mode: script` acquire a lock? (Today: no.)
   - Stale-lock threshold default — currently 24h hard-coded; surface as a flag and document.
   - Spec mentions Ctrl+C signal handler — present (`launch.py:141-146`); add to spec.

### C. Resolve when convenient (spec called these non-blocking)

8. **`relay panic`:** does it set `status: paused`? format of blocker
   line? exit code semantics for the agent? Today: status untouched,
   exit 0, line format `"- [ts] [actor] reason"`.
9. **Step transitions with assignee changes.** When the next step
   should be done by a different person, who reassigns? Today: nothing
   does — base prompt teaches the agent to write into Notes and panic
   if it can't proceed. Codify.
10. **Task lifecycle transitions.** Spec asks: paused→active preserves
    step? draft→back preserves step? Both: yes per implementation, but
    not asserted by tests. Add tests + freeze in spec.
11. **Workflow-less tasks.** `relay step` errors on these (`step.py:40`).
    `relay status` shows them with `step` blank. Spec calls this open;
    behavior matches the most natural reading.
12. **Step field manual edits.** Source of truth is the ticket file; if
    a human edits `step`, the next `relay step` operates on that value.
    Document.
13. **`relay status` filters / sorting / format.** None implemented;
    Rich table wraps poorly on narrow terminals (**NEW**).
14. **`relay feed` format & limits.** Today posts
    `"<assignee>: <msg> (<slug>)"` — pin format; add length cap.
15. **Script mode execution path.** Today: skill must declare
    `script:` in frontmatter; runs from repo root with secrets in env.
    Spec asks for explicit decisions on resolution, working dir, and
    inline-only step error case.
16. **`relay step`/`panic`/`feed` task inference from cwd.** Today
    `--task` is required everywhere. Worth adding cwd inference when
    invoked from inside `relay-os/tasks/<slug>/`.

### D. Newly surfaced — not yet in spec

17. **Slack notifications for human-driven ticket edits.** Assignee or
    status change in `ticket.md` (e.g. human-to-human reassignment)
    isn't mirrored to Slack. Decide between (a) a `relay assign / relay
    status` companion command that emits the side-effect, (b) git-hook
    sync, or (c) accept that direct file edits are silent.
18. **`watchers` field is dead code.** Frontmatter accepts it,
    validator ignores it, Slack ignores it. Either wire it to
    `post_mention` recipients or remove.
19. **`Ticket.watchers` accessor.** Round-tripped via raw frontmatter
    only. If watchers gain meaning, add the property.
20. **`relay init` is a real CLI surface.** Spec relegates it to "manual
    setup works"; implementation is feature-rich (path, `--update`, venv
    install, symlink wiring, gitignore management). Document.
21. **Vendored `.relay/` directory.** `relay init` installs an isolated
    venv + vendored CLI source under `relay-os/.relay/`. Not mentioned
    in the repo-layout tree (spec lines 90-150).
22. **Slack fallback `@<username>` is non-functional** (Slack only honors
    `<@USERID>`). Today's fallback prints text only. Either require
    Slack IDs for all humans or document the limitation.
23. **`relay launch` script-mode failures don't post to Slack.** Spec
    requires it (lines 942-943).
24. **Validator → dream wiring.** Spec implies dream calls the
    validator; implementation has both as separate pieces.
25. **`weekly-dream.md` recurring template not installed by `init`.**
    Only `_template.md` scaffolds get copied into a fresh repo. Either
    ship the live recurring or note that users opt in.
26. **Slug containing all digits / pure-digit titles.** `slugify("001")
    → "001"`; tasks like `001-pin-...` exist in this repo because the
    title started with `001`. The earlier numeric-counter design was
    explicitly removed; current behavior is fine but worth a sentence
    of guidance ("don't prefix titles with numeric IDs").

### E. Can defer (per spec, with current state noted)

27. **Archival of done tasks** — none; `--all` flag on `status` already
    hides them by default.
28. **Task dependencies** — none; freeform on blackboard.
29. **Context/skill staleness** — only via dream skill review.
30. **Git merge conflicts** — manual. One-task-one-worker keeps this
    rare.
31. **Prompt-size detection** — none.
32. **Blackboard pruning** — none. Git history is the archive.
33. **Temp-file cleanup on crash** — relies on `/tmp` being ephemeral
    plus signal handlers in normal exits.

---

## 12. Test coverage at a glance

```
$ pytest -q
.....................  109 passed in 0.81s
```

Spread across:

- `test_compose.py` — composition order, sections, missing refs (does
  not assert "fail-loud on missing ref" — that's the gap in §4)
- `test_create.py`, `test_launch*.py` — happy paths, slug collisions
- `test_commands.py` — step, panic, feed, status
- `test_recurring.py` — period keys, idempotency, bad-template skip
- `test_validate.py` — every validator check
- `test_init.py` — fresh init + `--update`
- `test_slack.py` — webhook posting tiers
- `test_smoke.py` — end-to-end via `CliRunner`

What the suite doesn't cover yet (matches the gaps above):

- launch-time missing context/skill should error
- `relay create` Slack post
- `relay launch mode:script` failure → Slack
- watchers fan-out
- assignee/status-change notifications
- pidfile contents of `cron.sh`
- `weekly-dream.md` end-to-end (template → due → scaffolded)

---

## 13. One-screen summary

**Implemented and stable:** every CLI command, all primitives (ticket,
blackboard, log, lock, workflow, skill, context), prompt composition,
both base prompt mode blocks, validator, recurring scheduling,
bootstrap/ticket shim, init (fresh + update), Slack feed for
agent-driven events.

**Bugs to fix:**

1. `cron.sh` calls non-existent `relay create --check-recurring`.
2. Compose silently swallows missing context/skill refs at launch time.
3. `relay create` doesn't post a "new task" FYI to Slack despite spec
   requiring it.
4. Slack fallback `@<name>` doesn't actually @-mention.

**Spec contradictions to settle:**

5. Recurring command name (`relay recurring check` vs `relay create
   --check-recurring`).
6. Blackboard default template (full skeleton vs minimal).
7. Composition order — 8 layers in spec, 9 in code.

**Functional gaps to wire:**

8. Watchers list → Slack recipients.
9. Human-driven ticket edits → Slack notifications (the
   `finish-slack-integration-features` and
   `use-slack-as-a-sync-channel-for-tickets` tickets in this repo).
10. `mode: script` failures → Slack.
11. dream skill → validator.
12. Ship `weekly-dream.md` from `init` (or document opt-in).

The implementation is ~90% spec-compliant on happy paths. The remaining
10% is spread across error paths, Slack human-event coverage, and
self-bootstrapping wiring.
