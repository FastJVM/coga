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
step: 5 (peer-review)
agent: claude
---

## Description

`coga init` never shows the user which agent CLIs coga supports or which ones
it found. It scans `PATH`, then keeps the result to itself: it decides silently
when exactly one agent is installed, and asks nothing at all when none or more
than one is. The packaged `coga.toml` then ships `[agents.claude]` and
`[agents.codex]` regardless, so someone with only Claude commits a config
declaring a Codex binary they do not have.

Make init scan for the supported agent CLIs, show the result, ask which ones
coga should drive, and write only those into `coga.toml`. The scan is the
visible part and the first thing to get right: a user should be able to run
`coga init` on a clean machine and read, from the output alone, which agents
coga can drive and which of them it found.

Init offers no install. An agent that is not on `PATH` is named with its
binary so the user can install it or put it on `PATH` themselves.

### Acceptance criteria

- [ ] Interactive `coga init` on a fresh repo prints a scan of the supported
      agent CLIs before it asks anything: a heading, then one line per agent in
      `dependencies.AGENT_CLIS` carrying its display name, its binary, and
      whether that binary was found on `PATH`. The list is complete in every
      state, including when nothing was found.
- [ ] Nothing in the scan or the question is hardcoded: both are built from
      `AGENT_CLIS` and `_AGENT_LABELS`, so an agent added to `AGENT_CLIS`
      appears in both with no further edit here.
- [ ] The scan then drives the question — the same agents offered as a
      multi-select with the found ones pre-checked, asking which to enable.
- [ ] Accepting the pre-checked set takes one ENTER and no other keystroke.
- [ ] The scaffolded `coga.toml` declares exactly the chosen agents; each
      unchosen `[agents.*]` table is commented out in place with its key
      comments intact.
- [ ] That rewrite parses to the packaged config minus the unchosen agents; on
      any mismatch init leaves `coga.toml` untouched and warns.
- [ ] `default_agent` names the first chosen agent when the packaged default
      (`claude`) is not chosen, and is otherwise left as packaged.
- [ ] Init offers no install anywhere in this flow. Choosing an agent that is
      not on `PATH` leaves it declared and prints its binary with the fact that
      coga needs that binary on `PATH` before it can launch the agent.
- [ ] A single-agent selection prints a warning naming `code/with-self-review`
      and the `coga validate` error that `other-agent` workflows now produce.
- [ ] An empty selection is confirmed by a prompt naming the cost — no launch
      works and `coga build` cannot run — and declining re-opens the picker.
- [ ] `q`/Esc leaves every agent declared and `default_agent` as packaged,
      prints one line saying so, and init continues.
- [ ] Ctrl-C in the picker aborts init instead of meaning `q`. Nothing is
      written, because the picker runs before `target.mkdir()`. Megalaunch's
      `--pick` behaviour on Ctrl-C does not change.
- [ ] After any non-empty selection every scaffolded ticket that names an agent
      names a declared one: `Config.agent_type()` resolves it and
      `coga validate` reports no `unknown-agent`.
- [ ] The packaged stateless targets stop pinning `claude`. `bootstrap/ticket`
      and `bootstrap/orient` carry no `agent:`, so each resolves to the
      configured default the way `bootstrap/resolve-conflicts` already does.
- [ ] In a repo where `claude` was not enabled, `coga build`, `coga ticket`,
      and `coga chat` each resolve a declared agent instead of raising on
      `claude`. `coga validate` is the gate only for the first — it checks
      `agent:` on `list_tasks(cfg)` targets, never on a bootstrap target — so
      the other two are gated by resolving the agent directly.
- [ ] The next-steps list in `_do_init` matches the selection: the
      `Edit <coga_os>/coga.toml` step no longer says "set your agents", and the
      `coga build --agent <other>` clause is built from the enabled agents and
      omitted when there is no second one. Today's
      `next(name for name in AGENT_CLIS if name != build_agent)` cannot raise
      because `AGENT_CLIS` always holds two names; it advertises an agent the
      selection may not have declared, and it needs a default once it reads the
      enabled list instead.
- [ ] `coga init` asks the question on Windows through a numbered-entry path
      that calls no `termios`, `tty`, `select`, or `signal` function, and a
      test exercises that path on POSIX.
- [ ] Non-interactive init asks nothing, prints no scan, and writes no
      `[agents.*]` or `default_agent` change; the clone path asks nothing about
      agents at all.
- [ ] `coga/init` and `coga/install` describe the scan and the question as what
      init does now, `coga/tickets/authoring` says what supplies its term 5
      after the unpinning, each context's bundled twin matches, and
      `python -m pytest` passes.

### Proposed shape

Rebased 2026-11-05 onto sibling PR #1176
(`v1/remove-the-agent-cli-install-offer-from-coga-init`), which is in review
and lands first. Verified against that PR's diff on 2026-11-05, with `main`
still unmerged: #1176 deletes `agent_cli_setup` and the install prompt, adds
`init._installed_agent_clis()` — the `AGENT_CLIS`-ordered `PATH` scan this
ticket builds the display on — removes the clone path's `_offer_agent_cli`
call entirely, and makes the next-steps agent line conditional on that scan.
It also deletes `dependencies.install_hint` and the `claude`/`codex`
`Dependency` entries, so the next-steps rewrite in item 7 has no install URL
left to drop. `AGENT_CLIS` keeps its shape, `("claude", "codex")`.
`_AGENT_LABELS` is untouched. Re-read `commands/init.py` before starting; if
#1176 changed further by merge time, the shape below yields to the code.

**1. Extract the picker into `src/coga/picker.py` (new).** Move `_decode_key`,
`_read_key`, `_picker_window`, `_picker_view`, and the body of
`_pick_selection` out of `coga/commands/megalaunch.py`, matching the existing
split where `src/coga/<name>.py` holds the engine and
`src/coga/commands/<name>.py` the CLI wrapper. One public entry:

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

Two details of `_picker_view` are load-bearing and must not become caller
choices. It sets `no_wrap=True, overflow="ellipsis"` on every column, which is
what makes each row cost exactly one terminal line — the budget
`_picker_window` is computed in; `pick()` applies both itself, so
`PickerColumn` carries only the header and the width or ratio. And
`_picker_view`'s row budget, `max(1, console.size.height - 5)`, reserves one
line for the hint, so `hint` must be a single line.

Ctrl-C gets its own action. `_decode_key` currently folds `b"\x03"` in with
`b"q"` and bare Esc as `"quit"` — raw mode clears `ISIG`, so Ctrl-C arrives as
a byte, not a signal. Decode it as `"cancel"` and have `pick()` raise
`KeyboardInterrupt`; `_pick_selection` catches that and returns `[]`, keeping
megalaunch's behaviour byte-for-byte while init can abort (Zach, 2026-11-05).

**2. Add the Windows input path as `picker._pick_numbered`.** `pick()`
dispatches on `os.name == "posix"` at call time: POSIX gets the moved
arrow-key loop, anything else gets `_pick_numbered`, which echoes the same rows
numbered and loops on `typer.prompt` — numbers toggle, `a`/`n` select all and
none, bare ENTER confirms, `q` quits, anything else re-prompts. It is a
separate function, not a wrapper: the POSIX-only imports stay behind the
module's `if os.name == "posix"` guard and `_pick_numbered` reaches no
`signal`, `termios`, `tty`, `select`, or `rich.Live` call. Dispatching at call
time rather than import time is what lets a POSIX test reach it.

This path needs no Ctrl-C handling of its own. It reads through
`typer.prompt`, which is in cooked mode, so Ctrl-C raises `click.Abort` and
aborts the command already.

**3. Render the scan in `commands/init._print_agent_scan`.** Its own function,
printed before the picker opens, built from `_installed_agent_clis()` (#1176)
plus `AGENT_CLIS` and `_AGENT_LABELS.get(name, name)` — the `.get` so an agent
added to `AGENT_CLIS` without a label cannot `KeyError`. A heading, then one
row per supported agent: display name, binary, found / not found. Every
supported agent appears in every state, so the found-nothing case is a list of
"not found" rows rather than an absence. This is the part to eyeball on a
clean machine, so keep it plain text an implementer can read in a terminal
transcript; `rich` is available but nothing here needs it.

**4. Ask the question in `commands/init._choose_agents`.** It replaces the
fresh-repo half of `_offer_agent_cli`, as
`_choose_agents(packaged_default: str) -> AgentChoice | None` where
`AgentChoice` is a frozen dataclass of `enabled: tuple[str, ...]` (in
`AGENT_CLIS` order) and `default: str | None` — the first enabled agent when
`packaged_default` is not enabled, else `None`. `None` means "make no agent
edits": non-interactive, or the human quit with `q`/Esc. A `KeyboardInterrupt`
from `pick()` is not caught here; letting it propagate is what aborts init.
The single-agent warning, the empty-selection confirm, and the "not on `PATH`"
note for a chosen-but-missing agent all live here. There is no install branch
to write: #1176 removed the only one init had.

Non-interactive returns `None` before printing anything, so `_print_agent_scan`
is called from `_choose_agents` rather than beside it — a scripted init prints
no scan. The scan exists to drive the question, a CI log cannot act on it, and
keeping scripted output unchanged avoids churning the init tests that assert on
it. Cheap to reverse if a provisioning log turns out to want it.

The clone path needs nothing. #1176 deletes its `_offer_agent_cli(None)` call
outright, so the invariant that a clone never rewrites committed team config
holds by construction — just do not add a new call there.

**5. Comment the unchosen tables out in `commands/init`.**

```python
def _disable_unchosen_agents(
    text: str, enabled: Collection[str]
) -> tuple[str, tuple[str, ...]] | None
```

A pure text transform, not a writer: the edited document plus the names it
commented out, or `None` when the rewrite fails its own check. Item 6 is what
writes, once, so this must not touch the disk — and `None` rather than `()`
for failure, so the caller can tell "the rewrite is unsafe" from "every agent
was enabled, nothing to comment out". Those two collapsing into one return is
what let the earlier draft's partial-write states exist.

It extends `_write_default_agent`'s approach instead of round-tripping the
document: find each `[agents.<name>]` header line, take the lines through to
the next line matching the existing `_TABLE_START`, prefix `# ` to the lines in
that range that are **neither blank nor already comments**, and insert one line
above the header saying init did not enable this agent and that uncommenting
re-enables it. Then parse back with `tomllib` and require the result to equal
the original config minus exactly those `agents` keys; return `None` on any
mismatch or on input that does not parse.

Skipping blank lines is not cosmetic, it is the correctness condition.
`_TABLE_START` is `^[ \t]*\[`, so it does not match a commented table header,
and the packaged `coga.toml` ships `[recurring]` and `[launch]` commented out.
The next line it matches after `[agents.codex]` is therefore `[notification]`,
roughly eighty lines later, swallowing the whole `# --- Unattended runs ---`
block. Already-comment lines there survive untouched, but the blank separator
lines would each become a bare `# `, and the parse-back check cannot see it
because comments do not affect the parse. With blanks skipped, the range
yields exactly the five `[agents.codex]` key lines plus its header, and six
lines for `[agents.claude]`. Verify that on the packaged template rather than
trusting these counts; the surrounding comment blocks are free to move.

`tomlkit` is already a dependency and already used by `_write_local_user`, but
it is the wrong tool here: it has no "comment this table out" operation, and
its comment trivia attaches the `# --- Agents ---` block and the trailing
`# peer = "codex"` example to neighbouring items unpredictably.

**6. Wire it into `_do_init`, as one all-or-nothing config edit.**
`_choose_agents` replaces the `_offer_agent_cli(template_default_agent)` call
in the same place — after `_offer_optional_tools()` and before
`target.mkdir()` — so a refused run, and a Ctrl-C, still leave the disk
untouched. One call site: the scan prints from inside `_choose_agents`.

The config edits land where `_write_default_agent` is called today, but they
are one transaction, not two independent writes. The obvious sequence —
`_disable_unchosen_agents`, then `_write_default_agent`, then
`_stamp_agent_into_delivered_tickets` — has two partial-failure states that
the acceptance criteria forbid: disabling fails while the default write
succeeds, leaving unchosen agents declared under a moved default; or disabling
succeeds and the default write fails, leaving `coga.toml` already rewritten.
`_write_default_agent` only preserves the bytes handed to it, not the
pre-disable template, so it cannot undo the first write.

So: read the packaged `coga.toml` once and keep those bytes. Run
`_disable_unchosen_agents` on the text, then the `default_agent` edit on its
result, both in memory. Write only if every stage returned a value; otherwise
write nothing, leave the complete original in place, and warn. Ticket stamping
runs only after that write succeeds. Report lines go beside the existing
``Made `...` the default agent`` line.

That means factoring the text half of `_write_default_agent` out from its
read-and-write half, so the same `str -> str | None` transform can run on the
disabled text. Keep `_write_default_agent(Path, str) -> bool` as a thin
wrapper over it: `_do_init` is its only production caller, but three
`test_write_default_agent_*` tests drive it by path, and leaving the signature
alone keeps them as regression cover for the transform.

Warn, specifically — do not raise. These writes sit inside `_do_init`'s
rollback `try`, whose comment ("Init is atomic") states that any exception
below it removes the half-built `coga/` and re-raises. So a failed config edit
that raises costs the user the entire init, where the acceptance criteria want
the packaged `coga.toml` and a warning.

**7. Unpin the packaged stateless targets.** Delete `agent: claude` from
`resources/templates/coga/bootstrap/ticket/ticket.md` and
`bootstrap/orient/ticket.md`, replacing it with the comment
`bootstrap/resolve-conflicts/ticket.md` already carries for the same reason
("No `agent:` on purpose … resolves to the configured default, so a repository
without Claude still runs …"). Decided with Zach, 2026-11-05, over the
alternative of init scaffolding local overrides.

Both are packaged files, so init cannot rewrite them — they live in
site-packages, and `_stamp_agent_into_delivered_tickets` only walks
`coga_os / "tasks"`. Left pinned, a selection without `claude` breaks three
commands at the point of use, none of which `coga validate` covers:

- `coga ticket` — `authoring.resolve_authoring_agent` tries
  `bootstrap/ticket`'s `agent:` as term 5 and calls `cfg.agent_type(name)`,
  which raises before term 6 (`Config.default_agent()`) can be reached. This is
  the bare command `_do_init` advertises as the filled-repo next step.
- `coga chat` — `aliases.py` maps it to `launch bootstrap/orient`, and
  `launch._target_operator` resolves a `BootstrapRef`'s explicit `agent:`
  through `bump.resolve_main_agent`, which raises on an unconfigured name.
- the agent guides init itself writes — `init.AGENT_GUIDE_TEMPLATE` tells the
  reader to `Run coga launch bootstrap/orient`, so init would commit
  instructions for a command that cannot run in the repo it just made.

Removing the pin makes each fall through to `Config.default_agent()`, which
by construction names a declared agent after any non-empty selection. The
install-level override survives: both ticket bodies already document that a
local `coga/bootstrap/<name>/ticket.md` beats the packaged copy.

Accepted behaviour change, outside init: in an existing repo that declares both
agents and sets `default_agent = "codex"`, a bare `coga ticket` interviews with
`claude` today, because term 5 beats term 6, and will interview with `codex`
after this. Coga's own repo is unaffected — it sets no `default_agent`, so its
default is the first declared table, `claude`.

The mechanism tests are safe: `tests/test_ticket.py`'s `_authoring_setup`
writes a *local* bootstrap ticket to exercise term 5, and
`test_ticket_bare_interview_falls_back_to_the_default_agent_key` already covers
`bootstrap_agent=None`. Two docstrings go stale and should be reworded —
`test_megalaunch.py`'s `test_author_draft_prefers_draft_agent_over_bootstrap`
names "the packaged bootstrap/ticket's `agent: claude`" (the test itself still
passes, since term 4 beats term 6), and `authoring.resolve_authoring_agent`'s
own docstring calls term 5 "the install-level default".

**8. Fix the next-steps strings in `_do_init`.** There is no
`_print_next_steps`; they are built inline in the `steps` list after the commit
report. Two are this ticket's:

- Drop "set your agents" from the `Edit {coga_os}/coga.toml` step. The question
  has already set them, so the instruction now sends the user to re-do what
  init just did.
- Build the `coga build --agent <other>` clause from the *enabled* agents and
  omit it when there is no second one. Today's
  `next(name for name in AGENT_CLIS if name != build_agent)` cannot raise,
  because it iterates the two-name `AGENT_CLIS`; the bug is that it names an
  agent the selection may have commented out. Reading the enabled list instead
  is what introduces the one-element case, so give the `next()` a default.
  While there, `build_agent = default_agent or AGENT_CLIS[0]` still wants
  `AGENT_CLIS[0]` as its fallback, since `AgentChoice.default` is `None`
  exactly when the packaged `claude` default stands.

Both surviving label lookups spell `_AGENT_LABELS[name]`, which `KeyError`s on
an agent added to `AGENT_CLIS` without a label. Use `.get(name, name)` here
too, matching item 3.

The third, the agent-CLI prerequisite line, belongs to #1176, which already
gates it on `if not _installed_agent_clis()`. Retune it to the selection
rather than the raw scan — an enabled agent that is missing from `PATH` is the
case worth naming — and leave it alone if that already reads correctly after
the merge.

**9. Tests.**

- `tests/conftest.py` — add `_print_agent_scan` and `_choose_agents` to
  `_stub_init_dep_check`'s tuple. It patches with `raising=False`, so a
  function it names but that no longer exists is silently not stubbed, and the
  real one then prompts in every init-invoking test. Check the tuple still
  matches the post-#1176 function names rather than assuming it does.
- `tests/test_picker.py` (new) — four tests move here from
  `test_megalaunch.py`: `test_decode_key`, `test_picker_window_keeps_cursor_visible`,
  `test_picker_view_fits_the_terminal_at_every_size`, and
  `test_read_key_resize_beats_pending_keypress`. `test_decode_key` grows the
  `b"\x03"` → `"cancel"` case it currently asserts as `"quit"`.
  Add `pick()` coverage for pre-checked rows, space/`a`/`n`/ENTER, `q`
  returning `None`, Ctrl-C raising `KeyboardInterrupt`, and `_pick_numbered`
  driven through a monkeypatched `typer.prompt` (toggle by number, bare ENTER,
  `q`, garbage re-prompts), plus one dispatch test that sets `picker.os.name`
  to `"nt"`.
- `tests/test_megalaunch.py` — repoint the moved imports and `_feed_keys`'
  patch target to `coga.picker._read_key`. The `test_megalaunch_cli_picker_*`
  tests stay as the adapter's coverage; add one that Ctrl-C still yields no
  launch rather than propagating.
- `tests/test_init.py` — cover the scan, the write, and the selection cases.
  - `_print_agent_scan` on its own: both found, one found, none found. Assert
    every supported agent appears in all three, and that the rows come from
    `AGENT_CLIS` — a test that monkeypatches an extra name into `AGENT_CLIS`
    and sees it rendered without a label is what keeps the Gemini sibling from
    needing an edit here.
  - `_disable_unchosen_agents` the way `test_write_default_agent_*` tests its
    sibling, but on text rather than a path: packaged template in, exact text
    out, parse-back equality, `None` for unparseable input, and an all-enabled
    call returning the text unchanged with an empty name tuple — distinct from
    the `None`. Assert directly that the
    `# --- Unattended runs ---` block below `[agents.codex]` comes through
    unchanged — that is the blank-line bug, and nothing else in the suite
    would catch it.
  - The transaction from item 6: force the parse-back check to fail and assert
    `coga.toml` is byte-identical to the packaged template afterwards, that no
    `default_agent` moved, that no delivered ticket was stamped, that init
    warned, and that init still exited 0 with `coga/` intact rather than
    rolling the whole scaffold back.
  - Rework the `_agent_picker` helper to feed the new picker and cover
    claude-only (codex commented, `default_agent` untouched), codex-only
    (claude commented, `default_agent = "codex"`, `coga-build.md` repointed),
    both chosen (`coga.toml` byte-identical to the packaged template), an
    enabled agent that is not on `PATH` (declared, binary named, no install
    offered), the empty selection confirmed and declined, the single-agent
    warning text, `q`/Esc, Ctrl-C leaving no `coga/` behind, non-interactive
    printing no scan, and the clone path.
  - A codex-only init, then resolve the agent for each command the packaged
    `bootstrap/*` targets used to break: `coga ticket`
    (`resolve_authoring_agent`), `coga chat` (`launch._target_operator`), and
    `coga build`. The regression they guard is
    `Agent type 'claude' is not defined in [agents]`.
  - `test_init_writes_the_chosen_default_agent` is the end-to-end test to
    rewrite against the new shape.
- `tests/test_ticket.py` and `tests/test_launch.py` — re-run both after item
  7. They exercise `bootstrap/ticket` and `bootstrap/orient` heavily, and the
  unpinning is the change most likely to surface there.
- `tests/test_agent_cli_setup.py` — gone with #1176; nothing to do here.

### Out of scope

- **Offering to install an agent CLI.** Out for this ticket, not ruled out
  forever. Build the scan first; whether init should offer an install, and in
  what shape, is a question to answer after seeing the scan run on a clean
  machine (Zach, 2026-11-05). So: add no install offer here, and equally,
  write no rule anywhere that says coga never offers one. The context updates
  in particular describe what init does now rather than declaring an
  invariant, so a later ticket can add an offer back without first having to
  retract a promise. Sibling `v1/remove-the-agent-cli-install-offer-from-coga-init`
  (PR #1176) is what removes the existing offer; this ticket just does not
  reintroduce it.
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
  simple per-agent toggle). `AGENT_GUIDE_TEMPLATE`'s
  `coga launch bootstrap/orient` line needs no edit either — item 7 makes that
  command work in a repo without Claude, which is the whole problem with it.
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
  the user who has none — not really the audience — saying so plainly is what
  matters. (The same remark originally also valued installing it for them;
  that half was reversed on 2026-11-04, below.)
- Nico on 2026-11-04: init should not offer to install an agent CLI at all.
  Coga's users already run agentic coding tools, so a user with none installed
  is not the audience init is built around.
- Zach on 2026-11-05: build the scan first and ship it with no install offer.
  Seeing it render on a fresh VM is what decides whether an install offer
  comes back later and in what form, so nothing here should prejudge that.
  The reference point for the display is GitHub Spec Kit's `specify check`,
  which lists every supported agent tool with a found / not-found marker.

### What init does today

`init._offer_agent_cli` is the only agent question, and it is narrower than it
looks. Non-interactive returns immediately. More than one agent CLI on PATH
returns early and asks nothing. Claude-only is chosen silently, because the
packaged default is already `claude`; codex-only instead reaches a confirm
asking whether to make `codex` the default agent in coga.toml. Only the
no-agent-on-PATH case prompts, as free text (`claude/codex/skip`).

After #1176 that last branch is gone: a user with no agent CLI is asked
nothing, and `_offer_agent_cli` handles only the exactly-one case. Nothing in
any branch shows the user the supported list — that absence is what this
ticket fixes.

A successful answer changes exactly one line: `default_agent = "..."`, written
by `init._write_default_agent`. Both `[agents.*]` tables land either way,
because init copies the packaged `coga.toml` verbatim — its agents section is
literal text, not a template.

### The shape of the scan and the question (Zach, 2026-10-27 and 2026-11-05)

A scan of every supported agent with its `PATH` status, then the same list as
a question, pre-checked from the scan. Rendering below is **illustrative, not
normative** — the scan is plain text and the question matches whatever the
reused picker draws:

```
Checking for agent CLIs...
  ● Claude Code   claude   found
  ○ Codex         codex    not found

Which agents should coga drive in this repo?
Each one gets an [agents.*] block in coga.toml, which is committed,
so this applies to everyone who clones the repo.

  [x] Claude Code   claude   found
  [ ] Codex         codex    not found
```

The binding rules are:

- The scan lists every supported agent in every state, found or not. A user
  with nothing installed reads a complete list of what coga can drive, not an
  absence. A user with everything installed still sees the list, which is what
  makes "I have the critical piece" legible.
- Each row carries the display name, the binary, and the `PATH` status, because
  the binary name is what the user acts on.
- Found agents start checked, so ENTER is the right answer for the common case.
- Enabling an agent that is not on `PATH` is allowed and is not an error. It is
  declared, and init says the binary has to be on `PATH` before coga can launch
  it. Init does not offer to install it (see *Out of scope*).
- An empty selection is confirmed, not silent. Say what it costs: with no
  agents declared, every launch fails and `coga build` cannot run.
- A single-agent selection is allowed and warned about (see below).

### What already exists and should be reused

- `coga.commands.megalaunch._pick_selection` (the CLI module, not the
  `coga.megalaunch` engine) is a hand-rolled arrow-key multi-select picker on
  `termios`/`tty` plus `rich.Live`: ↑/↓ and `j`/`k`, SPACE toggle, ENTER
  confirm, `a`/`n` all/none, `q`/Esc/Ctrl-C quit. It takes
  `list[tuple[TaskRef, Ticket]]` and pre-checks nothing, so it needs
  generalizing to a generic item list with an initial selection. No new
  dependency; `_picker_view` renders a `rich.Table`, which is why the mock
  above is illustrative.
  Ctrl-C is in that quit set because `_read_key` calls `tty.setraw`, which
  clears `ISIG`: the keypress arrives as a `b"\x03"` byte and `_decode_key`
  maps it alongside `q`. Harmless in megalaunch, where quitting launches
  nothing; in init it would mean "commit the packaged both-agents config",
  which is the outcome this ticket exists to prevent. Hence the separate
  `"cancel"` action in Proposed shape item 1.
- `init._installed_agent_clis()` — added by #1176 — is the `PATH` scan itself:
  the `AGENT_CLIS` on `PATH`, in supported order. The scan display and the
  pre-checked set both come from it; do not re-derive either with a second
  `shutil.which` loop.
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

- **The clone path must not change.** A clone's `coga.toml` is committed team
  config; `coga/init` ("Clone of a repo that already uses Coga") states the
  invariant that a clone never changes the default agent. A scan or picker that
  writes `[agents.*]` tables must not run there. After #1176 the clone branch
  calls nothing about agents at all, so this is a matter of not adding a call —
  but the invariant is the reason, and it survives #1176 either way.
- **Delivered tickets pin an agent.** The packaged `coga-build.md` ships
  `agent: claude`. If a codex-only selection leaves no `[agents.claude]`,
  `Config.agent_type` raises `Agent type 'claude' is not defined in [agents]`
  and onboarding is dead on arrival. Today
  `init._stamp_agent_into_delivered_tickets` repoints delivered tickets when
  the default moves; the new flow has to keep that working for every selection.
- **Two packaged tickets pin one that init cannot reach.**
  `bootstrap/ticket/ticket.md` and `bootstrap/orient/ticket.md` also ship
  `agent: claude`, but they live in the installed package, and
  `_stamp_agent_into_delivered_tickets` only walks `coga_os / "tasks"`. They
  break `coga ticket`, `coga chat`, and the guides init writes. Proposed shape
  item 7 unpins them.
- **`coga validate` does not cover a bootstrap target's `agent:`.** Its
  unknown-agent check reads `ticket.frontmatter["agent"]` for the refs
  `list_tasks(cfg)` returns. It resolves a recurring template's `delegate:`
  through `resolve_bootstrap` to prove the target exists, and checks nothing
  about that target's agent. So validate is the right gate for the scaffolded
  tickets and no gate at all for `bootstrap/ticket` or `bootstrap/orient`.
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
- **Init writes instruction files that advertise a bootstrap target.**
  `init.AGENT_GUIDE_TEMPLATE` — the text of the `CLAUDE.md` and `AGENTS.md`
  that `_write_agent_guides` commits — says to run
  `coga launch bootstrap/orient`. That is a second reason item 7 unpins
  `bootstrap/orient`, independent of `coga chat`.

### Testing conventions

Run the suite with `python -m pytest`. `coga-dev/testing` has the fallback
spellings for when the ambient interpreter is not Coga-capable, and
`coga-dev/codebase` is the entry point for Coga's own contribution rules. Both
are cited rather than attached — they are broad, and the implement step can
open them on demand.

### Contexts to update in the same PR

#1176 edits both of these files first; read them as they are at merge, not as
described here. Write both updates as *what init does*, not as a rule about
what coga will never do — see *Out of scope* on keeping the install question
open.

- `coga/init` (`docs/contexts/coga/init/SKILL.md`), "Fresh repo" — describes
  the agent question and says init writes `default_agent` while leaving the
  `[agents.*]` tables alone. The second half becomes wrong: init now also
  comments out the tables for unchosen agents.
- `coga/install` (`docs/contexts/coga/install/SKILL.md`), "Prerequisites" —
  describes what a user needs on `PATH` before init. Add that init scans for
  the supported agent CLIs and shows what it found.
- `coga/tickets/authoring` (`docs/contexts/coga/tickets/authoring/SKILL.md`),
  "Authoring agent" — numbers term 5 as "`bootstrap/ticket`'s `agent:`, the
  install-level default". After item 7 the packaged copy sets no `agent:`, so
  term 5 fires only for a repo that adds a local
  `coga/bootstrap/ticket/ticket.md`. Keep the term; say what now supplies it.

Each context has a bundled twin under
`src/coga/resources/templates/coga/bootstrap/contexts/`. #1176 edits both
copies of `coga/init` and `coga/install`; match that.

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

Previous ref: `marketing/fix-installer/ask-which-agents-to-enable-during-coga-init` (renamed 2026-10-27); earlier audit lines retain that ref.

<!-- coga:blackboard -->

## Dev

branch: coga/v1-20-ask-which-agents-to-enable-during-coga-ini-83a35a


## PR

```yaml
title: Ask which agents to enable during coga init
author: claude
author_evidence: >-
  Implement step ran as claude (claude-opus-5) in an attended session; no
  --agent override. Commits 2ea90376f..5de54e71c carry that authorship.
head: 5de54e71c3974e13e51328038e974182a7bd917d
base: 08dd27a78b216611117f5a6da5cfa8cd436a7759
depth: deep
rationale: >-
  No code review has run yet, and the diff changes behavior outside init: the
  packaged bootstrap targets lose `agent: claude`, so a bare `coga ticket` in
  an existing repo that sets a non-claude `default_agent` switches interviewer
  — reachable by `coga update` with no re-init. It also refactors a working
  picker out of an unrelated command. Both warrant reading the diff rather
  than trusting green tests.
implementation: >-
  init scans AGENT_CLIS for PATH presence and prints every supported agent in
  every state, then offers the same list as a multi-select with found agents
  pre-checked. The selection is written to coga.toml as one all-or-nothing
  edit: unchosen `[agents.*]` tables are commented out in place, and
  `default_agent` moves only when the packaged default was not chosen. The
  picker moved to `src/coga/picker.py` so init and megalaunch share it, with
  a non-POSIX numbered-entry path. The packaged `bootstrap/ticket` and
  `bootstrap/orient` lose `agent: claude` so a repo without claude can still
  run `coga ticket` and `coga chat`.
deviations: >-
  Built on pre-#1176 main rather than waiting for that PR to merge, which the
  design assumed. Verified the scan depends only on AGENT_CLIS, _AGENT_LABELS
  and a shutil.which loop, none of which #1176 changes, so
  `_installed_agent_clis()` was written here in #1176's shape. Owner's call,
  to unblock the fresh-VM test the scope decision makes the gate for the rest
  of the ticket.
limitations: >-
  (1) A rebase onto #1176 is still owed and will re-touch commands/init.py and
  tests/test_init.py. (2) Evaluator must-fix 3 is unresolved — softening
  #1176's "never offers an install" statements needs that PR's merged text.
  (3) Only the scan has run on real hardware (fresh macOS VM at ff502c154);
  the picker and the coga.toml rewrite are covered by tests only. (4) The
  3+-agent peer-inference gap in bump.resolve_other_agent is out of scope and
  unfiled.
files:
  src/coga/commands/init.py: Scan, question, AgentChoice, the all-or-nothing coga.toml edit, and selection-aware next steps.
  src/coga/picker.py: New shared picker engine; pick() plus the non-POSIX numbered path.
  src/coga/commands/megalaunch.py: Picker moved out; _pick_selection stays as the adapter preserving existing behavior.
  src/coga/resources/templates/coga/bootstrap/ticket/ticket.md: "Drop the `agent: claude` pin so a repo without claude can run `coga ticket`; body made consistent."
  src/coga/resources/templates/coga/bootstrap/orient/ticket.md: Same for `coga chat`; body made consistent.
  src/coga/resources/templates/coga/coga.toml: Its default_agent comment claimed chat/ticket do not follow the key; the unpinning makes them.
  src/coga/config.py: Comment naming bootstrap/ticket's `agent:` as the committed install-level default.
  src/coga/authoring.py: resolve_authoring_agent docstring, term 5, for the same reason.
  docs/contexts/coga/init/SKILL.md: Describes the scan and question as what init does now.
  docs/contexts/coga/install/SKILL.md: Prerequisites note that init scans and shows what it found.
  docs/contexts/coga/tickets/authoring/SKILL.md: Says what supplies term 5 after the unpinning.
  docs/contexts/coga/configuration/SKILL.md: Same stale install-level-default claim.
  docs/contexts/coga-dev/internals/agent-config/SKILL.md: Said the packaged bootstrap tickets pin claude.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Bundled twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/install/SKILL.md: Bundled twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/authoring/SKILL.md: Bundled twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: Bundled twin.
  tests/test_init.py: Scan, _disable_unchosen_agents incl. the blank-line regression, the transaction, every selection case, and the codex-only command resolution.
  tests/test_picker.py: Moved picker tests plus pick(), Ctrl-C, and numbered-path coverage.
  tests/test_megalaunch.py: Repointed moved imports; added the Ctrl-C adapter test.
  tests/conftest.py: _stub_init_dep_check learns _print_agent_scan and _choose_agents.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: >-
    No code review has run. peer-review is the next workflow step. The
    evaluate-design step (codex, 2026-11-05) reviewed the spec, not this diff,
    and design approval is not code review.
checks:
  - command: python -m pytest
    status: failed
    head: 589b799873ed96bccda84d6054edb9d704957c61
    base: 6a9b95c331ca5e20f61b1f809d73c5819300b6f8
    detail: >-
      4482 passed, 11 skipped, 1 failed in 1:24:11. The single failure,
      test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers,
      is pre-existing: it reproduces in isolation and fails identically on a
      clean origin/main worktree, and touches coga_edge distribution, which
      this diff does not. Recorded at the pre-rebase OID it actually ran at;
      not restamped onto the current head.
  - command: python -m pytest tests/test_init.py tests/test_picker.py
    status: passed
    head: 5de54e71c3974e13e51328038e974182a7bd917d
    base: 08dd27a78b216611117f5a6da5cfa8cd436a7759
    detail: >-
      184 passed. Fresh verification at the current head, covering both the
      warning-string commit made after the full run and the rebase onto
      08dd27a78. Incoming main commits touched only coga state files, no
      source.
  - command: python -m pytest tests/test_launch.py tests/test_megalaunch.py
    status: passed
    head: 589b799873ed96bccda84d6054edb9d704957c61
    base: 6a9b95c331ca5e20f61b1f809d73c5819300b6f8
    detail: >-
      391 passed. Run separately because the bootstrap unpinning and the
      picker move land hardest there. Superseded by the full run above.
```


## Implement progress 2026-11-05

**Built on pre-#1176 `main`, deliberately.** #1176 was still open
(`mergeStateStatus: CLEAN`, no reviews) when implement started, and the
evaluator's "do not start on the current base" assumed every item needed it.
Re-checked against the code: the scan needs only `AGENT_CLIS` (unchanged by
#1176), `_AGENT_LABELS` (untouched), and the `shutil.which` loop that already
existed inline in `_offer_agent_cli`. So `_installed_agent_clis()` was written
here, in #1176's shape, rather than waited for. Zach's call, to unblock the
fresh-VM test his own scope decision makes the gate for the rest of the ticket.

Accepted cost: a rebase conflict when #1176 lands, concentrated in
`commands/init.py` (its deletions vs these additions — this ticket replaces
`_offer_agent_cli` wholesale anyway) and `tests/test_init.py` (#1176 rewrites
64+/55−, and this ticket's test additions land in the same file). Re-read
`commands/init.py` and re-run the suite after that rebase.

**Done and verified.**

- Scan: `_installed_agent_clis()` + `_print_agent_scan()` in `commands/init.py`,
  printed from inside the interactive guard so scripted init stays silent.
  Commit `ff502c154`. **Verified on a fresh macOS VM** at that sha via
  `uv tool install --force git+…@ff502c154` — uv's `(from git+…)` clause
  confirmed the branch, not PyPI. The no-agent case rendered as two "not found"
  rows, which is the criterion that mattered.
  - Fix the VM run surfaced: the scan collided with the `op` paragraph above
    it and read as another line of that block. Leading blank line added.
- Picker: `src/coga/picker.py` with `pick()`, `PickerRow`, `PickerColumn`,
  and `_pick_numbered`; `_pick_selection` stays in `commands/megalaunch.py` as
  the adapter. Commit `9e7fa6d2a`. `tests/test_picker.py` (13) and
  `tests/test_megalaunch.py` (129, plus a new Ctrl-C adapter test) pass.

- Question and config write: `_choose_agents` + `AgentChoice`,
  `_disable_unchosen_agents`, `_apply_agent_choice` + `AgentConfigEdit`,
  `_default_agent_text` split out of `_write_default_agent`, and item 8's
  next-steps strings. Commit `77c1106aa`.
- Item 7's unpinning plus every falsified surface, and the `coga/init` /
  `coga/install` context updates. Commit `dd239551e`.

**Implement is complete.** Six commits, rebased onto `08dd27a78` and pushed.
Full suite: 4482 passed, 11 skipped, 1 failed — the failure
(`test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`)
is pre-existing, verified by reproducing it on a clean `origin/main` worktree.
Receipts are in `## PR`.

### Handoff to peer-review

Three things to weigh that green tests do not cover:

1. **The bootstrap unpinning is the risk.** It changes behaviour in repos that
   never run the new picker: a bare `coga ticket` in an existing repo setting a
   non-claude `default_agent` switches interviewer, reachable by `coga update`
   with no re-init. Term 5 no longer outranks term 6. Owner-accepted
   2026-11-05. Coga's own repo sets no `default_agent`, so it is unaffected.
2. **The picker extraction touches a command this ticket does not own.**
   Megalaunch behaviour is meant to be byte-for-byte unchanged; the one
   semantic difference is Ctrl-C, now a `KeyboardInterrupt` that the adapter
   catches and maps to `[]`. `test_megalaunch_cli_ctrl_c_launches_nothing`
   pins it. Worth confirming the adapter really is behaviour-preserving.
3. **Only the scan has run on real hardware.** Fresh macOS VM at `ff502c154`,
   no-agent case rendered correctly. The picker and the `coga.toml` rewrite are
   covered by tests only.

Still owed, and deliberately not done here: the rebase onto #1176 (open at the
time of writing), which re-touches `commands/init.py` and `tests/test_init.py`,
and evaluator must-fix 3, which needs #1176's merged text to search for the
"never offers an install" statements and soften them.

Out of scope and unfiled: `bump.resolve_other_agent` infers the peer only at
exactly two declared agents and raises at three or more. Nothing warns until
the first handoff. Becomes live when the Gemini sibling lands.

### Verified against the packaged template, not assumed

`_disable_unchosen_agents` was run against the real
`resources/templates/coga/coga.toml`: commenting codex touches exactly 6 lines
(header + 5 keys), claude exactly 7 (header + 6) — the design predicted 6 for
claude, which is why it said to verify rather than trust the count. No blank
line becomes a bare `# `, and the `# --- Unattended runs ---` block comes
through byte-identical. `tests/test_init.py` pins all three.

Two things the design got wrong that the code corrected:

- **`resolve_main_agent` raises on `agent=None`** unless
  `allow_prospective_default=True`. Item 7 would break `coga chat` rather than
  fix it if launch did not already pass that flag — `launch._target_operator`
  does, which is what makes the unpinning safe. The test drives that real call
  path rather than calling `resolve_main_agent` directly, so it would catch a
  regression in the flag.
- **`fake_vendor` does not reach `_do_init`.** It patches
  `update_cmd.packaged_template_root`, but `commands/init.py` imported the
  name directly, so init copies the *real* packaged template. Tests comparing
  against the packaged coga.toml must use `_PACKAGED_COGA_TOML`, not
  `fake_vendor / "coga.toml"` (which is a stub `version = 1\n`).

### Evaluator must-fix 1 — resolved (Zach, 2026-11-05)

An accepted empty selection: `AgentChoice.default` stays `None`, and init's
next steps **name the re-enable path and advertise no agent-backed command**.
No `coga build`, no `coga ticket` — `Config.default_agent()` returns `None`
with no `[agents]`, so both would fail at the point of use. Init says no agents
are declared, that no launch works and `coga build` cannot run, and points at
`coga.toml` to uncomment an `[agents.*]` table.

### Evaluator must-fix 2 — confirmed real, all surfaces repaired

Verified against the code rather than taken on faith. Item 7's unpinning
falsifies these, and the Proposed shape lists none of them. None collide with
#1176:

- `src/coga/resources/templates/coga/coga.toml:13-15` — "It does not move
  `coga chat` or `coga ticket`: their packaged tickets pin `agent: claude`."
  This is the file every repo gets, so it matters most.
- `docs/contexts/coga/configuration/SKILL.md:104` **and its bundled twin** —
  "the install-level default is `bootstrap/ticket`'s `agent:`". The ticket's
  `## Context` says `coga/configuration` stays correct; that holds for the
  `[agents.<name>]` key list, not for this line.
- `docs/contexts/coga-dev/internals/agent-config/SKILL.md:58` — "onboarding
  tickets pin `agent: claude`, which outranks the default."
- `src/coga/config.py:374-376` comment — same stale claim.

Plus the two docstrings item 7 already names.

### Evaluator must-fix 3 — deferred to the #1176 rebase

Needs #1176's merged text to search. Do it then: find any statement that coga
*never* offers an agent install (the `dependencies` module contract and
`launch._LaunchInvocation._prepare_agent` are the two the evaluator named) and
soften it to describe present behaviour, per `## Description` → *Out of scope*.


## Design re-run 2026-11-05 (second pass, after the backward bump)

The spec was re-derived against the code rather than against the earlier draft.
Both evaluator must-fixes are now answered in `## Description`, and five claims
the spec rested on turned out to be wrong.

**Decided with Zach this session.**

- **The packaged `bootstrap/ticket` and `bootstrap/orient` lose their
  `agent: claude`** (Proposed shape item 7). Chosen over having init scaffold
  local overrides, which would copy two packaged files into every repo where
  they then go stale across `coga update`. `bootstrap/resolve-conflicts`
  already does exactly this and carries the comment explaining why, so this is
  following an existing convention, not inventing one. Accepted cost: in an
  existing repo declaring both agents with `default_agent = "codex"`, a bare
  `coga ticket` switches interviewer from claude to codex. Coga's own repo sets
  no `default_agent`, so it is unaffected.
- **Ctrl-C in the picker aborts init**, where `q`/Esc keeps the packaged config
  and continues. `tty.setraw` clears `ISIG`, so Ctrl-C is a `b"\x03"` byte that
  `_decode_key` currently folds in with `q` — meaning Ctrl-C would commit the
  both-agents config this ticket exists to prevent. The shared decoder gains a
  `"cancel"` action; megalaunch's adapter catches the `KeyboardInterrupt` and
  returns `[]`, so `megalaunch --pick` is unchanged.

**Corrections to the previous draft's shape.**

- **Item 5 would have mangled the config.** `_TABLE_START` (`^[ \t]*\[`) does
  not match a commented table header, and the packaged `coga.toml` ships
  `[recurring]` and `[launch]` commented out — so the first line it matches
  after `[agents.codex]` is `[notification]`, about eighty lines later. "Prefix
  `# ` to the lines that are not already comments" would have commented every
  blank separator line in the `# --- Unattended runs ---` block, and the
  parse-back check cannot catch it because comments do not affect the parse.
  Fixed by skipping blank lines as well; verified on the packaged template that
  the ranges then yield exactly the two tables' header and key lines.
- **`coga validate` was the wrong gate for the bootstrap targets.** Its
  unknown-agent check only reads `agent:` on `list_tasks(cfg)` refs. It
  resolves a recurring `delegate:` through `resolve_bootstrap` to prove the
  target exists and checks nothing about that target's agent. The criteria now
  gate those two behaviorally, through `coga ticket` / `coga chat` /
  `coga build`.
- **The `StopIteration` claim was wrong.**
  `next(name for name in AGENT_CLIS if name != build_agent)` iterates the
  two-name `AGENT_CLIS`, so it cannot raise today. The real defect is that it
  advertises an agent the selection may have commented out; the raise becomes
  possible only once it reads the enabled list, which is why it needs a
  default.
- **Item 1's move list was short.** `_picker_view` also moves, and with it
  `test_decode_key` and `test_read_key_resize_beats_pending_keypress` alongside
  the two geometry tests. `_picker_view`'s `no_wrap`/`ellipsis` and its
  `height - 5` budget are load-bearing, so `pick()` owns them rather than
  exposing them through `PickerColumn`.
- **A third reason to unpin `bootstrap/orient`**, beyond `coga chat`:
  `init.AGENT_GUIDE_TEMPLATE` tells the reader to run
  `coga launch bootstrap/orient`, so init would commit instructions for a
  command that cannot run in the repo it just made.

## Scope decision 2026-11-05 (Zach, at the review-design gate)

Build the agent scan first; it is the deliverable to judge this ticket by.
Scope stays scan **plus** picker plus the `coga.toml` write — the ticket keeps
its original fix — and loses only the install offer.

- **No install offer, and no rule against one.** Ship with none. Whether init
  should offer an install later, and in what form, gets decided after seeing
  the scan run on a clean machine. So nothing in the code, the contexts, or
  this ticket should assert that coga never offers installs — the question is
  deferred, not closed. Recorded in `## Description` → *Out of scope*.
- **Zach will test on a fresh VM from the implementation branch** to see how
  the scan renders before deciding what else to add. Keep the scan's output
  plain and legible in a terminal transcript for that reason.
- **Supported set stays Claude Code and Codex**, which needs no work:
  `AGENT_CLIS` is already exactly `("claude", "codex")`. Drive the scan and the
  picker off it so the Gemini sibling needs no edit here.
- The body was rewritten this session against the above and rebased onto
  #1176; see the next section. Zach bumps backward from here to re-run
  `design` and `implement` on the new scope.

## Rebase onto PR #1176 (2026-11-05)

Sibling `v1/remove-the-agent-cli-install-offer-from-coga-init` is at step 4
(review) as PR #1176, open and unmerged at the time of writing — `agent_cli_setup.py`
is still on `main`. It lands first and changes this ticket's starting point:

- Adds `init._installed_agent_clis()` — the `AGENT_CLIS`-ordered `PATH` scan.
  This ticket builds its display on that rather than a new `shutil.which` loop.
- Deletes `agent_cli_setup` and the install prompt, so there is no install
  branch left to drop. **This settles the 2026-11-04 open question of which
  ticket deletes `_offer_agent_cli`: #1176 does.**
- Deletes the clone path's `_offer_agent_cli(None)` call, which retired the
  old Proposed-shape item 4 ("keep the clone path on its own function").
- Makes the next-steps agent-CLI line conditional on the scan, which overlaps
  the old item 7. `next(name for name in AGENT_CLIS if name != build_agent)` is
  untouched by #1176 and is still this ticket's to fix — see the correction
  above for what is actually wrong with it.
- Also edits `docs/contexts/coga/init` and `coga/install`, so read both as of
  the merge rather than as this ticket's `## Context` describes them.

Re-verified against the PR diff on 2026-11-05, still open and unmerged. Two
further facts the earlier note missed:

- It deletes `dependencies.install_hint` and the `claude`/`codex` `Dependency`
  entries. `_do_init`'s next steps currently interpolate `install_hint('claude')`
  and `install_hint('codex')`, so that line cannot survive #1176 in its present
  form; by the time this ticket starts it is already rewritten.
- `AGENT_CLIS` keeps its shape, `("claude", "codex")`, and `_AGENT_LABELS` is
  untouched. Both criteria that rest on driving the scan and question off them
  hold after the merge.

Still re-read `commands/init.py` before implementing: the shape is written
against the PR diff, not merged code.

## Direction change 2026-11-04

- **init no longer offers to install an agent CLI** (Nico, 2026-11-04). Coga's
  users already run agentic coding tools, so someone with no agent CLI
  installed is not the audience init should be built around. This reverses the
  declined-install decision below and changed two acceptance criteria. The
  removal from init is its own ticket,
  `v1/remove-the-agent-cli-install-offer-from-coga-init`; keep the two
  consistent. *Settled 2026-11-05: #1176 deletes `_offer_agent_cli`'s install
  branch; this ticket replaces what remains.* Note the decision was that init
  does not offer an install **now** — see the 2026-11-05 scope decision above
  for why it is not written down as a permanent rule.
- **Telling the user to put their agent CLI on `PATH` is an acceptable
  outcome** (Zach, 2026-11-04) if the scan and picker turn out not to be worth
  building. A printed line naming the supported binaries and asking the user to
  install one or add it to `PATH` satisfies the underlying need; the scan is the
  better version of that, not the only acceptable one. *Resolved 2026-11-05:
  build the scan and the picker.*

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
  arrives later. **Superseded 2026-11-04:** init offers no install at all, so
  there is no declined install to handle. Choosing an off-`PATH` agent still
  leaves it declared, which is the part of this decision that survives.

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

Two of the four below were resolved in this design pass; the remaining two are
for the owner.

- *Resolved 2026-11-05 (design's call).* **Non-interactive init prints no
  scan.** The scan exists to drive the question, a CI or provisioning log
  cannot act on it, and keeping scripted output unchanged avoids churning the
  init tests that assert on it. `_choose_agents` returns before printing, which
  is why item 4 puts the print inside it rather than beside it. Cheap to
  reverse if a provisioning log turns out to want the line.
- *Resolved 2026-11-05 (design's call).* **The empty-selection confirm
  re-opens the picker on every decline, with no retry limit.** The picker's own
  `q`/Esc is already the escape hatch, and it lands on a defined outcome — keep
  the packaged config, continue — so a retry counter would add a second way to
  reach the same place. Ctrl-C now aborts outright, which gives the stuck user
  a second exit.

- Handoff from `show-which-agents-are-available-on-the-machine-dur`
  (2026-10-28, human approved closing it as a duplicate): decide whether init
  needs wording about agents outside the built-in list. `dependencies.AGENT_CLIS`
  owns built-in discovery and installation; `config._parse_agents` permits
  custom agent names, so absence from that list does not mean Coga cannot
  drive an agent. PATH presence also does not prove authentication or readiness.
  The existing detection, selection, and install scope already covers the
  duplicate's main request. Its Spec Kit trial pointer is retired; the detailed
  findings stayed in a private document and are not a prerequisite for this
  decision. This is a handoff for this ticket's owner review, not a change to
  its approved requirements or a disposition of the evaluator findings below.
- Users who already have both agent CLIs installed get a question today's init
  never asks them. The ticket treats "asks nothing when more than one is
  installed" as the defect, so this is intended; flagging it because it is the
  one behaviour change an existing user will notice on a new repo.
- New 2026-11-05, from Proposed shape item 7: unpinning the packaged
  `bootstrap/ticket` changes a bare `coga ticket` in *existing* repos that set
  `default_agent` to something other than `claude` — the interviewer becomes
  that default instead of `claude`. Zach accepted it this session as the right
  behaviour. Flagging it here because it is a behaviour change outside init,
  reachable by `coga update` with no re-init, and the only part of this ticket
  that touches a repo nobody ran the new picker in.

## Evaluator review

Verdict: not ready for implementation until the three must-fix gaps below are
resolved. The earlier evaluator findings are answered by the revised body; this
review is against that revision and PR #1176's current diff.

### Must fix

1. **The empty selection has no complete data or next-steps contract.**
   Proposed Shape 4 defines `AgentChoice.default` as the first enabled agent
   when the packaged default is absent, but an accepted empty selection has no
   such agent. Proposed Shape 8 then computes `build_agent` from that value or
   `AGENT_CLIS[0]`, so an empty-repo init would still tell the user to run
   `coga build` with an undeclared agent; a filled repo would still advertise
   `coga ticket`. Both contradict the empty-selection confirmation that no
   launch works. `Config.default_agent()` explicitly returns `None` when
   `cfg.agents` is empty, and `authoring.resolve_authoring_agent` and
   `bump.resolve_main_agent` then fail loud. Specify the empty choice's
   `default` value and selection-aware next steps for both empty and filled
   repos, and test that no unusable agent-backed command is advertised.

2. **Unpinning the packaged stateless targets leaves several owned surfaces
   false, beyond the two docstrings named in item 7.** The body of
   `bootstrap/ticket/ticket.md` says its `agent:` is the install-level default,
   and `bootstrap/orient/ticket.md` says to swap its `agent:`; replacing only
   their frontmatter leaves both tickets internally contradictory. The shipped
   `coga.toml` says `coga chat` and `coga ticket` do not follow
   `default_agent` because their packaged tickets pin Claude.
   `coga/configuration` and its bundled twin repeat that term 5 is the
   install-level default, while `coga-dev/internals/agent-config` and the
   comment in `config.load_config` also say the packaged targets pin Claude.
   Repository guidance requires the same PR to repair every surface that
   summarizes the changed owner. Add these files and their tests to the shape;
   the ticket currently says `coga/configuration` stays correct, which is
   demonstrably false.

3. **The deferred install-policy decision is not fully reconciled with the
   prerequisite PR.** Out of Scope says no code or context may assert that
   Coga *never* offers agent installation, but PR #1176 currently introduces
   exactly that invariant in the `dependencies` module contract and the
   configured-CLI check in `launch._LaunchInvocation._prepare_agent` (as well
   as in the `coga/init` and `coga/install` topics that this ticket already
   plans to revise). Proposed Shape only revisits the topics. Require a post-merge
   search and soften the remaining code statements to describe present
   behavior, so this ticket does not ship the permanent rule it explicitly
   rejects.

### Dependency note

PR #1176 remains open at head `3badabee50b3e046ddf9205db0c1ff13c6454855`;
current `main` still has `_offer_agent_cli`, `agent_cli_setup`, and no
`_installed_agent_clis`. The ticket correctly says #1176 lands first and tells
the implementer to re-read the merged source. Do not start implementation on
the current base.
