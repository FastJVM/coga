---
title: Ask which agents to enable during coga init
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

`coga init` never shows the user which agent CLIs coga supports or which ones
it found. It asks a question only when no agent CLI is on PATH, decides
silently when exactly one is, and asks nothing at all when more than one is.
The packaged `coga.toml` then ships `[agents.claude]` and `[agents.codex]`
regardless, so someone with only Claude commits a config declaring a Codex
binary they do not have.

Make init scan for the supported agent CLIs, show what it found, ask which
ones coga should drive, and write only those into `coga.toml`. Offer to
install a chosen agent that is not on PATH.

### Acceptance criteria

- [ ] Interactive `coga init` on a fresh repo prints a scan line naming the
      agent CLIs found on `PATH`, or saying plainly that none were found.
- [ ] It then lists every agent in `dependencies.AGENT_CLIS` with its display
      name, binary, and `PATH` status, pre-checks the ones found, and asks
      which to enable.
- [ ] Accepting the pre-checked set takes one ENTER and no other keystroke.
- [ ] The scaffolded `coga.toml` declares exactly the chosen agents; each
      unchosen `[agents.*]` table is commented out in place with its key
      comments intact.
- [ ] That rewrite parses to the packaged config minus the unchosen agents; on
      any mismatch init leaves `coga.toml` untouched and warns.
- [ ] `default_agent` names the first chosen agent when the packaged default
      (`claude`) is not chosen, and is otherwise left as packaged.
- [ ] Choosing an agent that is not on `PATH` runs
      `agent_cli_setup.offer_agent_cli` for it; a declined or failed install
      still leaves that agent declared, with a printed line saying
      `coga launch` offers it again at the point of need.
- [ ] A single-agent selection prints a warning naming `code/with-self-review`
      and the `coga validate` error that `other-agent` workflows now produce.
- [ ] An empty selection is confirmed by a prompt naming the cost — no launch
      works and `coga build` cannot run — and declining re-opens the picker.
- [ ] `q`/Esc leaves every agent declared and `default_agent` as packaged,
      prints one line saying so, and init continues.
- [ ] After any non-empty selection every delivered ticket's `agent:` names a
      declared agent: `Config.agent_type()` resolves it and `coga validate`
      reports no `unknown-agent`.
- [ ] The next-steps list in `_do_init` matches the selection: no "set your
      agents" edit instruction, no install step for an agent already on
      `PATH`, and no `coga build --agent <other>` naming an undeclared agent.
- [ ] `coga init` asks the question on Windows through a numbered-entry path
      that calls no `termios`, `tty`, `select`, or `signal` function, and a
      test exercises that path on POSIX.
- [ ] Non-interactive init and the clone path write no `[agents.*]` or
      `default_agent` change, and the clone path still offers to install a
      missing agent CLI.
- [ ] `coga/init` and `coga/install` describe the new question, and
      `python -m pytest` passes.

### Proposed shape

**1. Extract the picker into `src/coga/picker.py` (new).** Move `_decode_key`,
`_read_key`, `_picker_window`, and the body of `_pick_selection` out of
`coga/commands/megalaunch.py`, matching the existing split where
`src/coga/<name>.py` holds the engine and `src/coga/commands/<name>.py` the CLI
wrapper. One public entry:

```python
def pick(rows, columns, *, checked=(), hint) -> list[str] | None
```

`rows` are `PickerRow(key, cells)`; `columns` are
`PickerColumn(header, width=None, ratio=None)` passed through to
`rich.Table.add_column`; `checked` seeds the selection by key; `hint` is the
footer line. The return value splits what megalaunch conflates: a confirmed
list, possibly empty, or `None` when the human quit. `_pick_selection` stays in
`commands/megalaunch.py` as the adapter that builds rows from
`list[tuple[TaskRef, Ticket]]` and maps `None` to `[]`, so megalaunch behaves
exactly as it does today. Considered and rejected: generalize in place and
import the private helper into init — `commands/init.py` importing
`commands/megalaunch.py` inverts that engine/CLI split.

**2. Add the Windows input path as `picker._pick_numbered`.** `pick()`
dispatches on `os.name == "posix"` at call time: POSIX gets the moved
arrow-key loop, anything else gets `_pick_numbered`, which echoes the same rows
numbered and loops on `typer.prompt` — numbers toggle, `a`/`n` select all and
none, bare ENTER confirms, `q` quits, anything else re-prompts. It is a
separate function, not a wrapper: the POSIX-only imports stay behind the
module's `if os.name == "posix"` guard and `_pick_numbered` reaches no
`signal`, `termios`, `tty`, `select`, or `rich.Live` call. Dispatching at call
time rather than import time is what lets a POSIX test reach it.

**3. Ask the question in `commands/init._choose_agents`.** It replaces the
fresh-repo half of `_offer_agent_cli`, as
`_choose_agents(packaged_default: str) -> AgentChoice | None` where
`AgentChoice` is a frozen dataclass of `enabled: tuple[str, ...]` (in
`AGENT_CLIS` order) and `default: str | None` — the first enabled agent when
`packaged_default` is not enabled, else `None`. `None` means "make no agent
edits": non-interactive, or the human quit. Display names come from
`_AGENT_LABELS.get(name, name)`, so an agent added to `AGENT_CLIS` without a
label cannot `KeyError`. The install offer, the single-agent warning, and the
empty-selection confirm all live here.

**4. Keep the clone path on its own function.** Narrow the existing
`_offer_agent_cli` to take no arguments: ask which CLI to install when none is
on `PATH`, call `offer_agent_cli`, return nothing. Its default-agent half only
ever ran with a non-`None` argument, which now only the fresh path supplies.
`_setup_initialized_clone` keeps calling it, unchanged.

**5. Comment the unchosen tables out in `commands/init`.**
`_disable_unchosen_agents(coga_toml: Path, enabled: Collection[str]) ->
tuple[str, ...]` returns the names it commented out, or `()` when it wrote
nothing. It extends `_write_default_agent`'s approach instead of round-tripping
the document: find each `[agents.<name>]` header line, take the lines through
to the next line matching the existing `_TABLE_START`, prefix `# ` to the lines
that are not already comments, and insert one line above the header saying init
did not enable this agent and that uncommenting re-enables it. Then parse back
with `tomllib` and require the result to equal the original config minus
exactly those `agents` keys; on any mismatch write nothing and return `()`.
`tomlkit` is already a dependency and already used by `_write_local_user`, but
it is the wrong tool here: it has no "comment this table out" operation, and
its comment trivia attaches the `# --- Agents ---` block and the trailing
`# peer = "codex"` example to neighbouring items unpredictably.

**6. Wire it into `_do_init`.** `_choose_agents` replaces the
`_offer_agent_cli(template_default_agent)` call in the same place — after
`_offer_optional_tools()` and before `target.mkdir()` — so a refused run still
leaves the disk untouched. The config edits land where `_write_default_agent`
is called today: `_disable_unchosen_agents` first, then the existing
`_write_default_agent` and `_stamp_agent_into_delivered_tickets` pair when
`AgentChoice.default` is set. Report lines go beside the existing
``Made `...` the default agent`` line.

**7. Fix the three next-steps strings.** Drop "set your agents" from the
`Edit {coga_os}/coga.toml` step; skip the "Install an agent CLI" step when
every enabled agent is on `PATH` and name only the missing ones otherwise; and
build the `coga build --agent <other>` clause from the enabled agents,
omitting it when there is no second one. The current
`next(name for name in AGENT_CLIS if name != build_agent)` has no default and
raises `StopIteration` as soon as one agent is enabled.

**8. Tests.**

- `tests/conftest.py` — add `_choose_agents` to `_stub_init_dep_check`'s tuple.
  It patches with `raising=False`, so a renamed function silently stops being
  stubbed and real prompts leak into every init-invoking test.
- `tests/test_picker.py` (new) — the geometry tests (`_picker_window`, and
  `_picker_view` at every terminal size) move here from `test_megalaunch.py`.
  Add `pick()` coverage for pre-checked rows, space/`a`/`n`/ENTER, quit
  returning `None`, and `_pick_numbered` driven through a monkeypatched
  `typer.prompt` (toggle by number, bare ENTER, `q`, garbage re-prompts), plus
  one dispatch test that sets `picker.os.name` to `"nt"`.
- `tests/test_megalaunch.py` — repoint the moved imports and `_feed_keys`'
  patch target to `coga.picker._read_key`. The `test_megalaunch_cli_picker_*`
  tests stay as the adapter's coverage.
- `tests/test_init.py` — unit-test `_disable_unchosen_agents` the way
  `test_write_default_agent_*` tests its sibling: packaged template in, exact
  text out, parse-back equality, unparseable file left untouched. Rework the
  `_agent_picker` helper to feed the new picker and cover claude-only (codex
  commented, `default_agent` untouched), codex-only (claude commented,
  `default_agent = "codex"`, `coga-build.md` repointed), both chosen
  (`coga.toml` byte-identical to the packaged template), none found then
  installed, the empty selection confirmed and declined, the single-agent
  warning text, `q`/Esc, non-interactive, and the clone path.
  `test_init_writes_the_chosen_default_agent` is the end-to-end test to rewrite
  against the new shape.
- `tests/test_agent_cli_setup.py` — no change; `offer_agent_cli` is reused
  as-is.

### Out of scope

- **Gemini.** Carved out to sibling ticket
  `marketing/fix-installer/add-gemini-as-an-agent-coga-can-drive`. Nothing
  here blocks on it: the picker lists whatever `AGENT_CLIS` holds, so Gemini
  joins for free once added there.
- **Designing a single-agent peer-review answer.** One already exists:
  `code/with-self-review` is the deliberate single-agent fallback, named as
  such in `coga/workflows` ("Code review gate") and used automatically by
  `recurring_autofix.AUTOFIX_NO_PEER_WORKFLOW`. So this ticket owes only a
  warning that names it. Worth knowing when wording that warning:
  `bump.resolve_other_agent` raises when there is not exactly one peer
  candidate, and `validate.py` reports `unresolvable-step-assignee` at
  `severity="error"` — so a one-agent repo makes `coga validate` error on any
  ticket already frozen on `code/with-review` or `code/design-then-implement`,
  not merely fail later at handoff.
- **Root instruction files and skill symlinks.** `init._write_agent_guides`
  writes both `CLAUDE.md` and `AGENTS.md`, and `init._link_skills_for_agents`
  links `.claude/skills/coga` and `.codex/skills/coga`, from hardcoded tuples
  that never consult `coga.toml`. Leave both alone — the gain is invisible to
  the user and the precedence rules are fiddly (`coga/init`, "Instruction
  files and skill discovery": Claude Code reads `AGENTS.md` only when no
  `CLAUDE.md` or `CLAUDE.local.md` exists at or above cwd, so this is not a
  simple per-agent toggle).
- **An `enabled` key under `[agents.*]`.** `config._parse_agents` rejects
  unknown keys loudly, so a flag would be a schema change; absence from
  `[agents]` is already how coga knows it cannot drive an agent.
- **Making `megalaunch --pick` work on Windows.** It picks up the numbered path
  incidentally from the shared `pick()`, untested here; sibling ticket
  `test-install-on-windows` owns proving it.

## Context

### Why

- Nico raised this in the review on 2026-10-19 and called the both-installed
  assumption a mess for anyone who has one.
- He confirmed Codex needs no special flag: `coga.toml` declares where each
  agent lives and how to launch it, so any agent is added the same way.
- Zach on 2026-10-21: init should open with a question about which agent the
  `coga.toml` should enable.
- Zach on 2026-10-27: the point of this ticket is making the install moment
  clear, not making the config tidy. Seeing the supported agents listed and
  scanned tells a user "I have the critical piece, this should be easy." For
  the user who has none — not really the audience — saying so plainly and
  being able to install it for them is what matters.

### What init does today

`init._offer_agent_cli` is the only agent question, and it is narrower than it
looks. Non-interactive returns immediately. More than one agent CLI on PATH
returns early and asks nothing. Claude-only is chosen silently, because the
packaged default is already `claude`; codex-only instead reaches a confirm
asking whether to make `codex` the default agent in coga.toml. Only the
no-agent-on-PATH case prompts, as free text (`claude/codex/skip`).

A successful answer changes exactly one line: `default_agent = "..."`, written
by `init._write_default_agent`. Both `[agents.*]` tables land either way,
because init copies the packaged `coga.toml` verbatim — its agents section is
literal text, not a template.

### The shape of the question (agreed with Zach, 2026-10-27)

A scan line, then a complete list of supported agents with PATH status,
pre-checked from the scan. Rendering below is **illustrative, not normative** —
match whatever the reused picker already draws:

```
Found on PATH: Claude Code.

Which agents should coga drive in this repo?
Each one gets an [agents.*] block in coga.toml, which is committed,
so this applies to everyone who clones the repo.

  [x] Claude Code   claude   found
  [ ] Codex         codex    not installed — coga can install it
```

The binding rules are:

- The scan line states what was found, and says so plainly when nothing was
  ("No agent CLI found on PATH — coga runs every launch through one").
- The list stays complete in every state. Listing only what was found would
  remove the ability to enable an agent the user is about to install, which is
  the case `agent_cli_setup.offer_agent_cli` exists to serve.
- Found agents start checked, so ENTER is the right answer for the common case.
- Checking an agent that is not on PATH leads to the existing install offer.
- An empty selection is confirmed, not silent. Say what it costs: with no
  agents declared, every launch fails and `coga build` cannot run.
- A single-agent selection is allowed and warned about (see below).

### What already exists and should be reused

- `coga.commands.megalaunch._pick_selection` (the CLI module, not the
  `coga.megalaunch` engine) is a hand-rolled arrow-key multi-select picker on
  `termios`/`tty` plus `rich.Live`: ↑/↓ and `j`/`k`, SPACE toggle, ENTER
  confirm, `a`/`n` all/none, `q`/Esc quit. It takes
  `list[tuple[TaskRef, Ticket]]` and pre-checks nothing, so it needs
  generalizing to a generic item list with an initial selection. No new
  dependency; `_picker_view` renders a `rich.Table`, which is why the mock
  above is illustrative.
- `agent_cli_setup.offer_agent_cli` already offers the vendor's package (brew
  cask, else global npm, else the install URL), prints the exact command,
  runs only on an explicit yes, re-checks PATH, then offers the login. Reuse
  it rather than writing a second install path. (`launch.py` also calls it
  when a configured agent's CLI is absent.)
- `dependencies.AGENT_CLIS` is the ordered list of supported agents, and
  `init._AGENT_LABELS` maps slug to display name. Drive the picker from those
  rather than a new hardcoded list, so the Gemini sibling needs no edit here.
- Commenting config out is already this file's idiom, not a new convention:
  the packaged `coga.toml` ships `# default_agent = "claude"`,
  `# peer = "codex"`, the `[recurring]` and `[launch]` tables, and the
  per-agent aliases as commented examples — and `init._write_default_agent`
  works by *uncommenting* that `default_agent` line.
- `tests/test_megalaunch.py` already drives the picker without a terminal:
  `_feed_keys` monkeypatches `_read_key` to yield decoded actions, and
  `test_picker_view_fits_the_terminal_at_every_size` renders through
  `rich.Console(width=..., height=...)`. Both patterns carry over.
- `tests/conftest.py`'s autouse `_stub_init_dep_check` replaces
  `_require_init_tools`, `_offer_optional_tools`, and `_offer_agent_cli` with
  `lambda *args: None` for every init-invoking test. That is why a new
  "make no agent edits" return of `None` keeps the existing suite honest — and
  why the fixture has to learn the new function's name.

### Constraints that are easy to miss

- **The clone path must not change.** `init` calls `_offer_agent_cli` twice.
  The second call, in the clone branch, passes `None` precisely because a
  clone's `coga.toml` is committed team config; `coga/init` ("Clone of a repo
  that already uses Coga") states the invariant that a clone never changes the
  default agent. A picker that writes `[agents.*]` tables must not run there.
- **Delivered tickets pin an agent.** The packaged `coga-build.md` ships
  `agent: claude`. If a codex-only selection leaves no `[agents.claude]`,
  `Config.agent_type` raises `Agent type 'claude' is not defined in [agents]`
  and onboarding is dead on arrival. Today
  `init._stamp_agent_into_delivered_tickets` repoints delivered tickets when
  the default moves; the new flow has to keep that working for every selection.
- **Windows is not a `NameError` to catch.** `_pick_selection` is POSIX-shaped
  end to end: it installs a `signal.SIGWINCH` handler (that signal does not
  exist on Windows) and a `signal.set_wakeup_fd` self-pipe (Windows accepts
  only sockets), before `termios` is ever touched. The numbered-entry fallback
  therefore has to be a whole separate input path, not a wrapper. `coga init`
  must work there even though `megalaunch --pick` need not. Sibling ticket
  `test-install-on-windows` covers the wider Windows question.
- **Init's own next steps contradict the new question.** There is no
  `_print_next_steps` function — the strings are built inline in
  `init._do_init`, in the `steps` list it fills after the commit report. Three
  of them are wrong once the question exists: one tells the user to edit
  `coga.toml` to "set your agents", one names both Claude Code and Codex as
  what coga drives, and the empty-repo one advertises
  `coga build --agent <other>` for whichever agent is not the default, which
  may no longer be declared. Sibling ticket
  `init-sends-the-user-to-edit-a-toml-nothing-can-ope` already assumes this
  ticket removes the agents half of that edit.

### Testing conventions

Run the suite with `python -m pytest`. `coga-dev/testing` has the fallback
spellings for when the ambient interpreter is not Coga-capable, and
`coga-dev/codebase` is the entry point for Coga's own contribution rules. Both
are cited rather than attached — they are broad, and the implement step can
open them on demand.

### Contexts to update in the same PR

- `coga/init` (`docs/contexts/coga/init/SKILL.md`), "Fresh repo" — states that
  init asks which agent CLI to install only when neither is on PATH, and that
  it writes `default_agent` while leaving the `[agents.*]` tables alone. Both
  halves become wrong.
- `coga/install` (`docs/contexts/coga/install/SKILL.md`), "Prerequisites" —
  states the same no-agent-on-PATH condition and lists the installer routes.

Two more contexts describe this config and stay correct *because* the unchosen
table is commented rather than deleted; check them, do not edit them.
`coga/configuration` lists the `[agents.<name>]` keys and defers their
explanation to "the shipped `coga.toml`", and `coga/sandboxes` says the shipped
`coga.toml` "sets and explains" `launch_args = "--no-daemon"`. Deleting the
codex table would have falsified both in a claude-only repo.

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

## Decisions from the design step

- **Unchosen `[agents.*]` tables are commented out, not deleted** (Zach,
  2026-10-27). Both produce an identical parsed config — `config._parse_agents`
  builds `cfg.agents` from the tables that exist, and there is no on/off key —
  so this is purely what a human sees in the committed file. Commenting wins
  because re-enabling later is deleting `# `s, because `coga update` never
  rewrites `coga.toml` so whatever init writes is permanent, and because
  `coga/sandboxes` and `coga/configuration` both point at the shipped
  `coga.toml` as the explanation of record for these keys.
- **`q`/Esc in the picker changes nothing** (Zach, 2026-10-27): init continues,
  every agent stays declared, `default_agent` stays as packaged, one line says
  so. Matches megalaunch, where `q` does the harmless thing, and init's habit
  of continuing with a warning rather than exiting. Accepted cost: an
  accidental Esc leaves the both-agents config this ticket exists to fix.
- **A declined install keeps the agent declared**, with a line saying
  `coga launch` offers it again (`launch.py` already calls `offer_agent_cli`
  when a configured agent's CLI is absent). The alternative — silently dropping
  what the user just asked for — is worse than a config entry whose binary
  arrives later.

## Corrections to the ticket's own context

- There is no `init._print_next_steps`. The next-steps strings are built inline
  in `_do_init`. The ticket text has been fixed.
- `tomlkit` is not a new dependency: it is in `pyproject.toml` and already used
  by `init._write_local_user`. It is still the wrong tool here — it cannot
  comment a table out — but the reason is capability, not dependency weight.
- The unchosen table is not the "only in-repo documentation" of the agent keys.
  `coga/configuration` lists them and `coga/sandboxes` carries the
  `--no-daemon` rationale; both are bundled into every repo. They do, however,
  defer to the shipped `coga.toml` for the explanation, which is what makes
  commenting out the better of the two options rather than merely the safer.

## Open Questions

- The empty-selection confirm re-opens the picker when declined, with no retry
  limit — the human can always Esc out. Fine, or should a second decline fall
  through to the Esc behaviour (keep the packaged config)?
- Users who already have both agent CLIs installed get a question today's init
  never asks them. The ticket treats "asks nothing when more than one is
  installed" as the defect, so this is intended; flagging it because it is the
  one behaviour change an existing user will notice on a new repo.
