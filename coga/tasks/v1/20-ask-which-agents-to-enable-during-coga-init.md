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

`coga init` scans `PATH` for the agent CLIs coga supports, then shows the user
none of it and writes a `coga.toml` that declares every supported agent
whether or not it is installed. A Claude-only user commits a config declaring a
Codex binary they do not have.

Read `PATH` first, and let what it finds decide what init writes (Nico, review
of PR #1192, 2026-11-10: "use the path to detect and self configure the
toml"). Init is the one command that reads `PATH` to find an agent, because it
is the one command that creates the `coga.toml` every later command reads. That
one read feeds both of init's outputs, so the list the user reads is the list
that configured the repo.

The first output is a printout copying GitHub Spec Kit's `specify check`: a
heading, then one row per agent in the registry with its display name, its
binary, and found / not found. The list is complete in every state, including
when nothing was found.

The second output is the generated `coga.toml`, which declares the agents the
scan found. A not-found agent's `[agents.*]` table is written commented out, so
enabling it later is uncommenting a block. The default agent is the first table
the file still declares, which is the first found agent in registry order. If
nothing was found, every agent table is written commented out, and init's next
steps say to install an agent CLI and uncomment its table.

Coga drives Claude Code and Codex today. A scan row needs an agent's display
name and its binary together, and those sit in two separate lists. Today they
are `dependencies.AGENT_CLIS` and `init._AGENT_LABELS`. They become one record
that the scan, the toml configuration, and init's next-steps labels all read.

The scan offers no install. An agent that is not on `PATH` is named with its
binary, so the user can install it and uncomment its table.

### Acceptance criteria

**The scan**

- [ ] Interactive `coga init` on a fresh repo prints the scan: a heading, then
      one row per registry agent with its display name, its binary, and
      whether that binary was found on `PATH`.
- [ ] Every registry agent appears in every state, including when none was
      found. A machine with nothing installed reads a complete list, not an
      absence.
- [ ] The scan prints on every interactive fresh-repo init, including when
      more than one agent CLI is installed.
- [ ] The scan is separated from whatever init printed above it by a blank
      line, so it does not read as another line of the `op` note.
- [ ] The printing function is standalone and takes no init state, so a later
      `coga check` can call it without a refactor.
- [ ] One `PATH` read serves both the printout and the configuration, so the
      rows the user read are the agents `coga.toml` declares. A second read
      could disagree with the first.

**The configuration**

- [ ] The generated `coga.toml` declares exactly the agents the scan found;
      every other registry agent's `[agents.*]` table is present but commented
      out.
- [ ] The default agent is the first found agent in registry order, and the
      delivered tickets that ship `agent: claude` (`coga/tasks/coga-build.md`)
      are pointed at it when it is not `claude`.
- [ ] With nothing found, every agent table is commented out and init's next
      steps say to install an agent CLI and uncomment its `[agents.*]` table in
      `coga.toml`.
- [ ] Tests cover only-claude, only-codex, both found, and none found,
      asserting the generated `coga.toml` (which tables are live, which are
      commented out, the default agent) in each case.
- [ ] `coga validate` passes on the repo init generates when at least one
      agent was found (only-claude, only-codex, both). With none found, its
      only errors are `coga-build`'s `unknown-agent` and
      `unresolvable-operator` for `agent: claude`. That is the accurate state
      (no agent is configured), and both messages already say to restore the
      `[agents.*]` table (Zach, 2026-11-10).
- [ ] No `default_agent` line is written: the default comes from declaration
      order (see Proposed shape). The packaged `# default_agent = "claude"`
      example stays as it is.
- [ ] The edit is all-or-nothing: if the rewritten `coga.toml` fails its own
      parse-back check, init warns and writes the packaged `coga.toml`
      unchanged rather than failing the whole init. In that case nothing is
      stamped into delivered tickets, and the next steps treat every registry
      agent as declared, which is what the packaged file says.
- [ ] Init's summary (the block after "Initialized coga repo at …") says what
      the configuration did whenever it commented anything out: which agents
      `coga.toml` declares, and which tables are commented out because their
      binary was not found.
- [ ] `_offer_agent_cli`, its confirm prompt, `_write_default_agent`,
      `_DEFAULT_AGENT_KEY`, `_DEFAULT_AGENT_EXAMPLE`, the "Made `X` the default
      agent" / "Could not make `X` the default agent" summary lines, and their
      tests are gone. Init asks no agent question.

**Scope of the behaviour**

- [ ] Non-interactive init prints no scan and writes the packaged `coga.toml`
      unchanged.
- [ ] The clone path neither scans nor touches `coga.toml`: a clone's
      `coga.toml` is committed team config.

**The registry**

- [ ] Nothing in the scan or the configuration is hardcoded. Rows and table
      handling are driven by the supported-agent registry, so an agent added
      there renders and is configured with no edit to either. "Configured"
      here means its packaged `[agents.<name>]` table is kept or commented out
      by the same loop. A registry agent with no packaged table has nothing to
      comment out and is skipped. Shipping its table is the out-of-scope
      template edit below.
- [ ] A test adds an agent to the registry, with a matching packaged table,
      and asserts the scan renders it and the configuration comments its table
      out when its binary is absent.
- [ ] A found registry agent with no packaged table is skipped, and the
      default agent is the first found agent the file actually declares. A
      skipped agent is never stamped into a delivered ticket.
- [ ] A registry entry with no display name renders under its slug instead of
      raising, in the scan and in init's next-steps strings.
- [ ] Init's next steps name agents through the registry, not literals: the
      no-agent prerequisite line and the `coga build` coax. The coax advertises
      only agents the generated `coga.toml` declares — with one found agent it
      offers no `--agent` alternative.

**Docs and suite**

- [ ] `coga/init` describes the scan and the configuration, and
      `python -m pytest` passes.

### Proposed shape

Verified against main `655e561dd` on 2026-11-10 (design step). Main has not
touched `src/` or `tests/` since the branch head `fa36ebd2c`, so the registry
and scan below are already on the branch as described.

**One record, in `src/coga/dependencies.py`.** Add a frozen dataclass:

    @dataclass(frozen=True)
    class AgentCLI:
        name: str
        label: str = ""

        @property
        def display(self) -> str:
            return self.label or self.name

`name` is the binary coga scans `PATH` for and the `[agents.*]` table the
packaged `coga.toml` declares. These are one string because the packaged
template's `[agents.claude]`/`cli = "claude"` and `[agents.codex]`/
`cli = "codex"` make them equal for every agent coga ships. `display` makes the
missing-label case total by construction.

`AGENT_CLIS` changes from `tuple[str, ...]` to `tuple[AgentCLI, ...]` holding
`AgentCLI("claude", "Claude Code")` and `AgentCLI("codex", "Codex")`, in that
order. Registry order is the scan order and the default-agent order. Do not add
a derived `tuple[str, ...]` alias. Delete `init._AGENT_LABELS` and add
`dependencies.agent_label(name: str) -> str`, returning the matching record's
`display`, otherwise `name`. The record carries no install URL and no
`packages`: coga never installs or names an installer for an agent CLI (see the
`dependencies.py` module docstring).

**One scan.** `init._installed_agent_clis()` already exists on main and is the
only `PATH` walk; keep it as the single scan and do not add a second. Add a
public, argument-free `print_agent_scan()` in `init.py` that renders it with
`typer.echo` / `typer.secho` (no `rich`), starting with an empty line. Rendering
(Zach, 2026-11-06 — copy Spec Kit's tree):

        Checking for agent CLIs...

        Agent CLIs coga can drive
        ├── ● Claude Code (claude) — found
        └── ○ Codex (codex) — not found

Green for found, uncolored for not found: having one agent is the normal case,
so not found is not a warning. The non-ASCII glyphs follow the precedent of
`_print_notification_state`'s `✓`; the Windows console question belongs to
`v1/31-test-install-on-windows`. Do not downgrade the glyphs here.

The scan itself does not say what init will write. `print_agent_scan` must
stay free of init state so a later `coga check` can call it, so the
configuration outcome is reported in init's summary instead (see
"Summary and next steps").

**One configuration step: `_configure_agent_tables`.** Add to `init.py`:

    def _configure_agent_tables(
        coga_toml: Path, found: Sequence[str]
    ) -> list[str] | None:

It comments out the `[agents.<name>]` table of every `AGENT_CLIS` record whose
`name` is not in `found`, and returns the names the file now declares, in
declaration order. That includes the no-op case where every agent was found and
nothing is rewritten. It returns None, leaving the file untouched, on any
failure. Returning the declared list rather than a bool is what keeps the
default agent and the summary honest when a found agent has no packaged table:
callers read the first declared name, never `found[0]`. Steps:

1. Read the text and `tomllib.loads` it as `before`. On a decode error or
   `OSError`, return False.
2. For each registry agent not in `found` whose table `before["agents"]`
   declares: find the line matching `^[ \t]*\[agents\.<name>\][ \t]*$`. From
   there up to the next live table header (`_TABLE_START`, which ignores
   commented headers), prefix `# ` to every live line, meaning lines that are
   not blank and not already comments. Comments and blank lines are left
   alone. This bounds the table by its live keys, not by the next header
   (the `[recurring]`/`[launch]` trap in Context), and leaves the packaged
   file's own prose — including the `# analyze` and `# peer` examples — byte
   for byte as it ships.
3. Parse the new text as `after`. Write it only if `after["agents"]` (or `{}`
   when the key is gone) has exactly the expected names in the original order,
   and `after` with `agents` removed equals `before` with `agents` removed.
   Otherwise return None. Write it atomically: a temporary file beside
   `coga_toml` (`newline="\n"`), then `os.replace` onto it, removing the
   temporary file if either step raises. A direct write that fails partway
   leaves a truncated `coga.toml` that init would go on to commit, which is
   worse than not configuring at all.

Expected names = `[a.name for a in AGENT_CLIS if a.name in found and a.name in
before["agents"]]`, which is also the return value on success. Do not collect
`before`'s other, non-registry tables into this list; there are none in the
packaged file, and they would stay live.

**The default agent needs no key.** Confirmed: `Config.default_agent()`
(`src/coga/config.py`) returns the first-declared `[agents.*]` table when no
`default_agent` key is set, and the packaged `coga.toml` declares claude then
codex in registry order. So commenting out the not-found tables leaves the
first found agent as the default. Writing `default_agent` anyway would add a
second statement of the same fact and needs `_write_default_agent`'s whole
insertion machinery, so it is not written. After a successful configuration
that declared at least one agent, with the first declared name differing from
`_template_default_agent(template_root)`, call
`_stamp_agent_into_delivered_tickets(coga_os, template_default, declared[0])`.
Stamp the first *declared* name, not `found[0]`: a found agent with no packaged
table is skipped, and stamping it would write an `agent:` the file does not
declare, which `Config.default_agent` disagrees with and `coga validate`
reports as `unknown-agent`. Keep `_template_default_agent` for that "old"
value. Then `coga-build.md` reads `agent: codex` in a Codex-only repo, and
`coga validate` passes there (verified by hand on 2026-11-10).

**Remove the offer.** Delete `_offer_agent_cli`, `_write_default_agent`,
`_DEFAULT_AGENT_KEY` and `_DEFAULT_AGENT_EXAMPLE`. Also delete the
`default_agent_set` branch in `_do_init`, its two summary messages, and the
tests named `test_agent_offer_*`, `test_write_default_agent_*` and
`test_init_writes_the_chosen_default_agent` in `tests/test_init.py`. A test
asserting the both-installed case still writes a two-table `coga.toml` covers
what those guarded.

**Call sites in `_do_init`.**

- Before `target.mkdir()` and after `_offer_optional_tools()`:

      found = print_agent_scan() if _interactive() else None

  `print_agent_scan` stays argument-free and returns the `PATH` snapshot it
  just printed, so there is exactly one read and the printed rows cannot
  disagree with what gets configured. A later `coga check` calls it the same
  way and ignores the return. `None` means non-interactive, which is distinct
  from `[]`, found nothing. `template_default_agent` is computed as today.
- Inside the rollback `try`, where `_write_default_agent` is called today
  (after `_pin_control_branch`, before the commit): call
  `_configure_agent_tables(coga_os / "coga.toml", found)` when `found is not
  None` and keep its return as `configured`, then the stamp described above.
  `found is None` (non-interactive) never touches the file.
  `_configure_agent_tables` must not raise. Catch `OSError` and
  `tomllib.TOMLDecodeError` inside it, so a failure cannot trigger the
  rollback.
- `_setup_initialized_clone` gets neither call. Its existing behaviour is
  unchanged.

**Summary and next steps.** Let `declared` be the agents `coga.toml` now
declares: `configured` when the rewrite succeeded, else every registry name in
the packaged file. Let `default` be `declared[0]` if any. Every line below
reads `declared`, never `found`: after a failed rewrite the file still declares
everything, and a message that said otherwise would describe a file the user
does not have.

- Summary, only when something was commented out:
  `Declared Claude Code in coga/coga.toml; commented out [agents.codex]
  (codex not on PATH) — uncomment it once installed.` Name agents through
  `agent_label()` and tables through `AgentCLI.name`. With none declared:
  `No agent CLI found, so every [agents.*] table in coga/coga.toml is
  commented out.` If the configuration failed (interactive, `found` given,
  returned None), print a yellow warning that `coga.toml` was left as
  packaged and declares every supported agent.
- No-agent prerequisite, when no agent CLI was found — `found == []`, or for
  non-interactive init when `_installed_agent_clis()` is empty, as today. The
  `drivable` list is built from `AGENT_CLIS` as on the branch. The remedy
  depends on `declared`, because only a successful rewrite leaves a table to
  uncomment:
  - Nothing declared, the successful none-found case: `No agent CLI was
    found — coga drives Claude Code (`claude`) or Codex (`codex`). Install
    one, then uncomment its [agents.*] table in coga/coga.toml. Agent-backed
    commands (`coga build`, `coga launch`, `coga ticket`) need one.` Rewrite
    the comment above this line, which says the next steps never send anyone
    to a `.toml`. They now do in this one case, because uncommenting a table
    is the remedy.
  - Agents still declared, meaning non-interactive init or a failed rewrite:
    today's text, with no `coga.toml` pointer. The tables are already live, so
    installing the binary is the whole remedy.
- `coga build` coax (empty repo): `Run `coga build` with
  {agent_label(default)}`, plus `, or `coga build --agent {other}` with
  {agent_label(other)}` for each other agent in `declared`. With one declared
  agent there is no alternative. With none declared, name the delivered
  ticket's agent (the template default, `claude`) with no alternative. The
  prerequisite line above has already said what to do first.

**Tests**, in `tests/test_init.py`, replacing the deleted agent-offer tests:

- Scan (already on the branch): no agent on `PATH` renders every registry
  entry as not found; both on `PATH` still prints; an added registry agent
  renders (patch `coga.commands.init.AGENT_CLIS`); `AgentCLI("gizmo")`
  renders as `gizmo`.
- `_configure_agent_tables` unit tests against a copy of
  `_PACKAGED_COGA_TOML`, one per case (only-claude, only-codex, both, none).
  Assert the live tables, that each commented table's header and keys are
  present as `# ` lines, that the packaged file's own comment lines are
  unchanged, that `[notification]` and everything after it are
  byte-identical, and `Config.default_agent()` (or the first `agents` key)
  in each case.
- Parse-back failure returns None and leaves the file byte-identical. For
  example, a header with no live keys after it, or monkeypatch `tomllib.loads`
  to return a mismatched dict on the second call.
- A failing write returns None and leaves the file byte-identical, proving the
  `os.replace` transaction: monkeypatch `os.replace` (or the temporary file's
  write) to raise `OSError`, and assert no temporary file is left behind.
- A registry agent added with a matching packaged table is configured by the
  same loop: patch `coga.commands.init.AGENT_CLIS` with a third record, add its
  table to the copied toml, and assert the configuration keeps it when found
  and comments it out when not. This is the configuration half of the
  no-hardcoding claim the scan test makes.
- A found registry agent with *no* packaged table is skipped: the return value
  omits it, the first declared name is the default, and nothing stamps it into
  `coga-build.md`.
- End-to-end interactive init (fake TTY, `shutil.which` patched) for
  only-claude, only-codex, both and none: assert the generated `coga.toml`,
  `coga-build.md`'s `agent:`, the summary line and the coax. Run
  `coga validate` and assert it passes for the three found cases, and that
  for none its errors are exactly the two `coga-build` agent issues.
- End-to-end with the configuration failed (patch `_configure_agent_tables` to
  return None) and nothing found: the yellow warning prints, `coga.toml` is
  byte-identical to `_PACKAGED_COGA_TOML`, `coga-build.md` still reads
  `agent: claude`, and the prerequisite line names no `coga.toml` table.
- Non-interactive init prints no scan and leaves `coga.toml` byte-identical to
  `_PACKAGED_COGA_TOML`.
- Clone setup prints no scan and does not touch `coga.toml`.

In `tests/test_dependencies.py` (already on the branch): `agent_label` returns
the label for a known agent and the input string for an unknown one.

**Docs, same PR.**

- `coga/init` (`src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md`),
  "Fresh repo": replace the paragraph from "When exactly one agent CLI
  resolves…" through "…init asks nothing." with the scan and the
  configuration. Cover commented-out not-found tables, the default as the
  first found agent, the coga-build stamp, the parse-back fallback, the
  non-interactive no-op, and the next-steps change. The clone paragraph's
  "never changes the default agent" becomes "never scans or rewrites
  `coga.toml`".
- `docs/contexts/coga-dev/internals/agent-config/SKILL.md` cites
  `_write_default_agent` under "The default agent". Repoint it at
  `_configure_agent_tables` and declaration order.
- Packaged `coga.toml`: the `default_agent` comment ("Unset, it's the first
  [agents.*] table below") stays true. Add one line above `[agents.claude]`
  saying `coga init` comments out the table of any agent whose CLI it did
  not find, and that uncommenting it enables that agent. Changing the
  packaged file changes `_PACKAGED_COGA_TOML`, so re-run the line-count
  assertions.
- `coga/configuration`
  (`src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md`),
  the paragraph starting "Init supplies definitions for Claude Code and
  Codex": it is now false for a one-agent machine. Say that init declares the
  agents whose CLI it found and comments out the rest, so with one agent
  installed no config edit is needed, and to add another, uncomment its
  table. Keep the `default_agent` example for a repo that declares both. Its
  advice `coga chat --agent codex` fails in a Codex-only repo, because
  `bootstrap/orient`'s `agent: claude` must name a declared type. State that
  limit plainly rather than inventing a workaround, and have the topic own it
  in its own words. Do not cite the follow-up ticket: `coga/knowledge` keeps a
  durable topic off task links that vanish at retirement.

### Out of scope

- **An interactive agent picker.** Init detects; it does not ask. The picker
  designed on 2026-11-06 is in `## Superseded designs`.
- **Offering to install an agent CLI.** Out now, not ruled out forever (Nico,
  2026-11-04). Do not reintroduce one, and do not write a rule anywhere saying
  coga never will.
- **Making the built-in commands agent-agnostic.** `bootstrap/ticket`,
  `bootstrap/orient` and `coga-build` keep `agent: claude`. Design found
  that a Codex-only repo is worse off than today: `coga chat` fails even
  with `--agent codex` (details in Context). Zach decided on 2026-11-10 that
  this belongs in a follow-up ticket that makes the built-in commands
  agent-agnostic properly, not a launch bandaid here. This ticket ships with
  that gap and says so in `coga/configuration` and in the PR body. Do not
  touch launch, `resolve_main_agent`, or the pins.
- **Fixing single-agent peer resolution.** `bump.resolve_other_agent` infers
  the peer only at exactly two declared agents. A repo configured with one
  agent cannot resolve an `other-agent` step; see the constraint below.
- **A standalone `coga check`.** The scan stays callable from one later; that
  is all this ticket owes it.
- **Adding a third agent.** This ticket makes room for one and adds none.
- **Splitting the agent type from its binary.** Split `AgentCLI.name` when a
  supported agent's binary first differs from its table name.

## Context

### Why

- Nico raised this in the review on 2026-10-19 and called the both-installed
  assumption a mess for anyone who has one.
- Zach on 2026-10-27: seeing the supported agents listed and scanned tells a
  user "I have the critical piece, this should be easy." For the user who has
  none, saying so plainly is what matters.
- Nico on 2026-11-04: init should not offer to install an agent CLI. Coga's
  users already run agentic coding tools.
- Nico, relayed by Zach on 2026-11-06: a user usually has exactly one agent,
  and it is often an off-mainstream one such as Kimi, Grok Build, or Gemini.
- Nico, closing PR #1192 on 2026-11-10: printing the scan is not enough — "use
  the path to detect and self configure the toml." The print-only version is
  in `## Superseded designs`.

### The reference

GitHub Spec Kit's `specify check` prints a tree, one row per supported tool:

    Checking for installed tools...

    Check Available Tools
    ├── ● Antigravity (not found)
    ├── ● Claude Code (not found)
    ├── ○ Cline (no CLI required)
    ├── ● Codex CLI (not found)
    ├── ● Gemini CLI (not found)
    └── ● Grok Build (not found)

Two deliberate departures: coga carries the binary name, because the binary is
what the user acts on; and every agent coga drives is a CLI, so coga's markers
are found / not found.

### `PATH` is the input, `coga.toml` is the output

Nico's rule from #1176: an agent is declared in `coga.toml`, not required on
`PATH`. Every command after init reads the toml. Init is the one place that
creates the toml, so init is where `PATH` is read, and what it finds becomes
the declaration. At scan time there is no `coga.toml` to read; the clone path,
where one already exists, neither scans nor rewrites it.

### What init does today (main, after #1176)

- `init._installed_agent_clis()` is the only `PATH` scan, returning the
  installed `AGENT_CLIS` in order.
- `init._offer_agent_cli` returns early unless interactive with exactly one
  agent installed that differs from the template default; then it confirms
  making that agent the default. On a yes `_write_default_agent` writes
  `default_agent` and `_stamp_agent_into_delivered_tickets` rewrites
  `agent: claude` in delivered tickets.
- The packaged `coga.toml` ships `[agents.claude]` then `[agents.codex]`, both
  live, with `# default_agent = "claude"` commented out.
- `_do_init`'s next steps print a no-agent prerequisite line that spells both
  agents as literals, then the `coga build` coax built from
  `_AGENT_LABELS[build_agent]` and `_AGENT_LABELS[other]`.
- A comment above the no-agent line says the next steps "deliberately never
  send anyone to edit a `.toml`". This ticket reverses that for the none-found
  case: with every table commented out, uncommenting one is the remedy. Update
  the comment.

### Starting point on the branch

`branch:` in `## Dev` holds the print-only implementation from PR #1192
(`fa36ebd2c`): the `AgentCLI` registry, `agent_label`, `print_agent_scan` and
its tests, reviewed with no code defects. Implement should build on it rather
than redo it. The toml configuration is the new work.

### Constraints that are easy to miss

- **Commenting out a table.** `_TABLE_START` (`^[ \t]*\[`) does not match a
  commented header, and the packaged `coga.toml` ships `[recurring]` and
  `[launch]` commented out, so the next live header after `[agents.codex]` is
  `[notification]`, about eighty lines later. A naive "comment every line until
  the next table" would comment the whole unattended-runs block. The shape
  above comments only live lines, which is safe for the same reason;
  re-measured counts are in Proposed shape.
- **Pinned `agent: claude` targets: what a Codex-only user sees** (verified
  2026-11-10 in a throwaway repo with `[agents.claude]` commented out):
  - `coga ticket "x"` fails: "No authoring agent available: Agent type
    'claude' is not defined in [agents]. Known: ['codex']. (from
    bootstrap/ticket's `agent:`; pass --agent <name> to override)".
    `coga ticket --agent codex` works, because
    `authoring.resolve_authoring_agent` checks the override first.
  - `coga chat` fails, and so does `coga chat --agent codex`: "`agent:
    claude` on bootstrap/orient is not a configured agent type (configured:
    ['codex']) … a `--agent` override is ephemeral and cannot repair an
    invalid routing input." The error comes from `bump.resolve_main_agent`,
    reached through launch's operator resolution. It validates the pinned
    name before the override applies. Today, with both tables live,
    `coga chat --agent codex` gets past routing. This regression is accepted
    and goes to the follow-up (Out of scope).
  - `coga build` in a Codex-only repo works, because init stamps `agent:
    codex` into `coga-build.md`.
- **No agent found, then the user uncomments only `[agents.codex]`.**
  `coga-build.md` still says `agent: claude`, so `coga build` and
  `coga build --agent codex` fail with the same routing error (verified). It
  has the same root cause as `coga chat` and goes to the same follow-up. The
  next steps here still say "uncomment its table" without singling out Claude.
- **Single-agent repos and `other-agent` steps.** With one declared agent,
  `bump.resolve_other_agent` raises "assignee='other-agent' needs exactly two
  configured `[agents.*]` types…" at the hand-off to the peer step, and
  `coga validate` reports `unresolvable-step-assignee` on any ticket whose
  frozen workflow has one. Only authored workflows carry `assignee:
  other-agent` (`code/with-review`, `docs/with-review`,
  `code/design-then-implement`). No recurring job or delivered ticket does,
  so a freshly initialized one-agent repo validates clean. Init's next steps
  do not mention `code/with-self-review`: they point at `coga build`, and
  workflow choice happens later in authoring (see Open Questions).
- **Zero declared agents** (verified): config load succeeds (`coga status`
  runs and shows the operator as `(unresolved)`), and init's own
  `_load_scaffolded_config` for the audit write works. `coga validate`
  reports exactly two errors, both on `coga-build`: `unknown-agent` and
  `unresolvable-operator`. Removing `agent:` instead swaps the first for
  `missing-main-agent`, so that does not help. The criterion is written
  accordingly.
- **Scan before anything is written.** `_do_init` removes a half-built `coga/`
  on any exception. Print before `target.mkdir()`; make the toml rewrite warn,
  not raise.
- **The more-than-one-installed case.** `_offer_agent_cli` is deleted, so
  this trap goes with it. The scan and configuration call sites above are not
  inside any branch that depends on the count.
- **The clone path must not scan or configure.** `coga/init` ("Clone of a repo
  that already uses Coga") is where that boundary is written down.

### A gotcha that will cost time otherwise

`commands/init.py` does `from coga.dependencies import AGENT_CLIS`, binding the
name into the init module. A test that patches `coga.dependencies.AGENT_CLIS`
does not change what the scan renders — patch `coga.commands.init.AGENT_CLIS`.
Likewise `fake_vendor` patches `update_cmd.packaged_template_root`, but init
imports the name directly and copies the real packaged template; tests that
compare against the packaged `coga.toml` must use `_PACKAGED_COGA_TOML`.

### Testing conventions

Run the suite with `python -m pytest`. `coga-dev/testing` has the fallback
spellings for when the ambient interpreter is not Coga-capable, and
`coga-dev/codebase` is the entry point for Coga's own contribution rules. The
scan's glyphs make this platform-sensitive: `coga-dev/testing` says when a
native-Windows receipt is required.

### The context to update in the same PR

`src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md`,
under "Fresh repo": init prints the scan and writes `coga.toml` from it,
commenting out not-found agents. It is the sole owner of `coga/init`
(`tests/required_package_resources.txt`); there is no live twin. Also check
the packaged `coga.toml`'s comments about `default_agent` and the agent
tables, and `coga/configuration`, for claims the generated file now
falsifies. Write it as what init does, not as a rule about what coga will
never do.

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

PR #1192 (print-only scan) was closed unmerged by Nico on 2026-11-10; the next
open-pr opens a new PR. The branch head `fa36ebd2c` is the starting point
described in `### Starting point on the branch`.

## Evaluator review

Verdict: not ready for implementation. The overall direction and repository
placement are sound, and the accepted Codex-only and single-agent limitations
are stated clearly, but the following design defects need owner resolution.

### Must resolve before implementation

1. **The printed scan is not the snapshot that configures the repo.** Under
   `Proposed shape` / `Call sites in _do_init`, `print_agent_scan()` calls
   `_installed_agent_clis()` internally and `_do_init` immediately calls it a
   second time for `found`. That conflicts with both "Make the scan drive init"
   and the preceding "One scan" contract: a binary appearing or disappearing
   between calls can make the displayed result disagree with `coga.toml`.
   `src/coga/commands/init.py::_installed_agent_clis` is already the one PATH
   reader, and the branch's `print_agent_scan` can remain argument-free while
   returning the snapshot it printed (or while delegating rendering to a
   helper). Specify one result for both output and configuration, or explicitly
   weaken the acceptance language and cover the intended two-snapshot behavior.

2. **A found registry entry without a packaged table selects an undeclared
   ticket agent.** The registry acceptance says such an entry is skipped, and
   `_configure_agent_tables` computes `expected` by filtering against
   `before["agents"]`. But `The default agent needs no key` stamps
   `found[0]`, not the first name in that filtered declared set. If a newly
   registered `gizmo` is found but has no packaged table, configuration can
   succeed while `src/coga/commands/init.py::_stamp_agent_into_delivered_tickets`
   writes `agent: gizmo`; `src/coga/config.py::Config.default_agent` instead
   resolves the first live table, and `coga validate` reports the stamped name
   as unknown. Define "default" and stamping as the first *declared found*
   agent, and reconcile the broader "declares exactly the agents the scan
   found" criterion with the explicit no-table exception.

3. **The configuration-failure next steps contradict the fallback state.**
   The all-or-nothing criterion says a failed rewrite leaves the packaged
   `coga.toml` unchanged and next steps treat every packaged registry agent as
   declared. But `Summary and next steps` emits the no-agent prerequisite
   whenever `found == []`, including that failure, and its exact text says to
   uncomment an `[agents.*]` table. In the fallback file both packaged tables
   are already live. Make this line depend on the effective `declared` /
   configuration outcome, or define distinct successful-zero and fallback
   wording; add the fallback case to the end-to-end assertions.

4. **The proposed write is not all-or-nothing on `OSError`.**
   `_configure_agent_tables` promises to return `False` with the original file
   untouched on any failure, yet step 3 directly opens/writes the destination
   and the call-site instructions say to catch `OSError`. A write can truncate
   or partially replace the file before raising, after which init may continue
   with a corrupt committed config. The existing
   `src/coga/commands/init.py::_write_default_agent` also writes directly, so it
   is not evidence for this stronger contract. Specify an atomic temporary-file
   plus replace transaction (including cleanup), or narrow the guarantee and
   let a write error enter init's existing rollback. Test a write/replace
   failure as well as the parse-back mismatch.

5. **The tests do not enforce the central one-record extension claim.** The
   acceptance criteria promise that adding a registry record drives the scan,
   table handling, and next-step labels, but `Proposed shape` only reuses the
   branch's `tests/test_init.py::test_agent_scan_renders_an_agent_added_to_the_registry`.
   That test cannot catch hardcoding in `_configure_agent_tables`, declaration
   summaries, or the build coax; the separate `agent_label` unit tests do not
   compose those paths. Add a temporary third record *and matching temporary
   table* and assert scan rendering, configuration, summary, and next-step
   label behavior from the same simulated registry addition. Include the
   no-packaged-table skip case separately because it controls finding 2.

6. **The docs plan depends on an unfiled, transient ticket.** `Docs, same PR`
   tells the packaged `coga/configuration` topic to point at a follow-up ticket,
   while the blackboard says that ticket does not exist yet. Even after filing,
   `coga/knowledge` (`Narrative links, never restates` and the retirement
   guidance) says durable topics must not rely on task links that disappear at
   retirement. Have `coga/configuration` own the user-visible limitation and
   remedy boundary directly; track the implementation follow-up on the
   blackboard/task system without making that transient file required reading.

### Optional recommendation

- The scan changes terminal glyph/encoding behavior, which
  `docs/contexts/coga-dev/testing/SKILL.md` classifies as platform-sensitive.
  Add the required native-Windows full-suite receipt to the verification plan;
  the current Mac UTM hand walk is useful product evidence but does not replace
  that pre-merge receipt.

## 2026-11-10 — PR #1192 closed; re-scoped to scan-and-configure (Zach)

Nico closed #1192 with changes requested: "that won't work. For that one I
would actually use the path to detect and self configure the toml." The scan
now drives the generated `coga.toml` as well as printing.

Zach rewound the ticket to step 1 (design) and rewrote `## Description` and
`## Context` (with Claude) for the new scope. Decisions taken, Zach 2026-11-10:

- Not-found agents' `[agents.*]` tables are written commented out, not deleted.
- The default agent is the first found agent in registry order.
- None found: every agent table commented out; next steps say to install an
  agent CLI and uncomment its table.
- Non-interactive init and the clone path leave `coga.toml` as is.
- `_offer_agent_cli`'s default-agent confirm becomes redundant and goes.
- Zach tests the branch by hand (a fresh `coga init`, installed from source)
  before any PR is opened. Peer-review's handoff should say what to try:
  the only-claude, only-codex, both and none cases.

Everything recorded on this blackboard about the print-only version — its
design, the #1176 sequencing, the implement and peer-review notes and the
PR receipt — moved to `## Superseded designs` as the 2026-11-06 → 2026-11-10
entry. The decisions it records (registry shape, Spec Kit tree rendering, the
blank line before the scan) carry forward and are restated in the body.

## 2026-11-10 — design (scan-and-configure)

The spec is in the body. Verified against main `655e561dd`. Main has not
touched `src/`/`tests/` since `fa36ebd2c`, so implement can build on the
branch as is (still reconcile first).

Decisions taken in this step:

- **No `default_agent` key.** Declaration order already makes the first found
  agent the default. `_write_default_agent` and its regexes go along with
  `_offer_agent_cli`.
- **Comment-out rule: live lines only,** from the agent's header to the next
  live header. Counts: claude 7, codex 6 (re-measured).
- **The configuration outcome is reported in init's summary, not in the
  scan,** so `print_agent_scan` stays init-agnostic for a later `coga check`.
- **None-found validate errors are accepted** (Zach, 2026-11-10): the two
  `coga-build` agent errors are the honest state and already tell the user
  to restore the table.
- **The Codex-only `coga chat` regression is accepted** (Zach, 2026-11-10:
  "not the lane of this ticket … better handled with a follow-up ticket,
  making sure the built-in commands are agent agnostic rather than a
  bandaid"). Evidence is in `### Constraints that are easy to miss`.

Follow-up to file (not filed yet; Zach to create it with `coga ticket` or
ask for a draft): make the built-in commands agent-agnostic. `coga chat`
(bootstrap/orient), `coga ticket` (bootstrap/ticket) and `coga build`
(coga-build) pin `agent: claude`. `--agent` cannot override a pin that names
an undeclared type for orient/coga-build, so a repo that declares only Codex
cannot use them. This ticket makes that repo shape the norm for Codex-only
machines. Its scope also covers one-agent repos and `code/with-review` (see
the 2026-11-10 review-design entry): authoring should default to
`code/with-self-review` when only one agent is declared.

Hand-test plan: Zach is on the Windows laptop. The hand test before any PR
runs on the Mac in a UTM VM, installing coga from the branch commit (not
PyPI). Cases: only-claude, only-codex, both, none. Peer-review's handoff
should list what to look at in each: the scan tree, the summary line, the
`coga.toml` tables, `coga-build.md`'s `agent:`, and `coga validate`.

## 2026-11-10 — review-design (Zach)

The design's two open questions are resolved; the spec in the body stands
unchanged.

- **None-found next steps stay neutral.** They keep "install one, uncomment
  its table" with no "`coga build` currently needs Claude Code" caveat. The
  agent-agnostic follow-up fixes the underlying gap, so the message does not
  go stale.
- **One-agent repos and `code/with-review` go to the follow-up.** A one-agent
  repo whose author picks `code/with-review` gets `unresolvable-step-assignee`
  from validate and fails at the peer hand-off. This ticket leaves init's next
  steps alone; the agent-agnostic follow-up (or a ticket it spawns) should
  make authoring default to `code/with-self-review` when only one agent is
  declared.

## 2026-11-10 — implement: ticket edited, evaluator findings dispositioned

Zach asked during implement whether the registry's "make a third agent
cheaper" goal belonged in this ticket. It did not, as a goal. The merged record
is forced by the feature — a scan row needs an agent's display name and its
binary together, and those were two lists in two modules — but the claim built
on top of it, "adding an agent is one record", is false while
`init._AGENT_SKILL_DIRS` carries its own label pairs and the packaged
`coga.toml` ships each `[agents.*]` table as hand-written text. A third agent
is three edits. The ticket had an Out-of-scope bullet admitting exactly that,
which is the tell: the carve-out existed only to defend the claim.

Body edits, Zach approved 2026-11-10:

- `## Description` leads with the `PATH`-first ordering, which Zach judged
  unclear in the previous design: init is the one command that reads `PATH`,
  because it is the one command that creates the `coga.toml` every later
  command reads, and that one read feeds both outputs. Named the two outputs
  first and second so the causality is on the page.
- Dropped the "other half of this ticket" framing and the one-record claim.
  The registry paragraph now says why the two lists merge.
- Dropped Out of scope's "The other place a third agent still needs." See the
  follow-up note below; the fact survives there.
- Reworded the registry test criterion to assert this change reads a list
  instead of `claude`/`codex` literals, rather than underwriting a promise
  about future agents.

Evaluator findings, all six resolved in the body rather than deferred. None
contradicted an acceptance criterion:

1. **Two `PATH` reads.** `print_agent_scan` now returns the snapshot it
   printed; still argument-free, so a later `coga check` ignores the return.
   New scan criterion states the invariant.
2. **Found agent with no packaged table.** `_configure_agent_tables` returns
   the declared list instead of a bool, and the default and the stamp read its
   first element, never `found[0]`. New registry criterion.
3. **Fallback next steps contradicted the fallback file.** Every summary and
   next-steps line now reads `declared`, not `found`. The no-agent
   prerequisite has two forms: with nothing declared it points at the table to
   uncomment; with tables still live, non-interactive or a failed rewrite, it
   keeps today's text and no `coga.toml` pointer.
4. **Non-atomic write.** Temporary file beside `coga.toml` plus `os.replace`,
   with cleanup, so a partway failure cannot leave a truncated config for init
   to commit.
5. **One-record claim untested through configuration.** Test plan adds a third
   record with a matching packaged table asserted through the configuration,
   and the no-packaged-table skip as its own case.
6. **Docs cited an unfiled, retirement-transient ticket.** `coga/configuration`
   owns the Codex-only `coga chat` limitation in its own words, with no task
   link, per `coga/knowledge`.

Still open, Zach's call: the native-Windows full-suite receipt. The toml
rewrite is filesystem and encoding work on top of the scan's non-ASCII glyphs,
which `coga-dev/testing` tier 2 calls platform-sensitive and requires before
merge. The AWS harness is not reachable from this session, so implement records
it as an outstanding gate in the `## PR` receipt rather than satisfying it.

For the agent-agnostic follow-up, in addition to what the design entry above
records: making a third agent genuinely one edit also needs
`init._AGENT_SKILL_DIRS` folded into the registry and the packaged
`[agents.*]` tables generated from the record instead of shipped as text.
Generating them would delete most of what this ticket adds — the line-by-line
commenting, the `[recurring]`/`[launch]` trap, the parse-back check — at the
cost of the packaged file's hand-written explanatory comments, which is why
this ticket comments shipped text instead.

## 2026-11-10 — implement: built, hand-walked, one design fix

The spec in the body is implemented. Two commits on the branch above the
print-only scan.

**What changed.** `print_agent_scan` returns the snapshot it printed, so one
`PATH` read feeds both outputs. `_configure_agent_tables` comments out the
not-found agents' tables and returns the names still declared;
`_agent_table_state` reads the outcome back off disk for the summary and next
steps. `_offer_agent_cli`, `_write_default_agent`, `_DEFAULT_AGENT_KEY` and
`_DEFAULT_AGENT_EXAMPLE` are gone, with their tests. Docs updated: `coga/init`,
`coga/configuration`, `coga-dev/internals/agent-config`, and the packaged
`coga.toml`'s own comment.

**The one design change, decided with Zach mid-step.** The approved shape
commented only live lines, which does not satisfy the ticket's own "enabling it
later is uncommenting a block". A hand walk of a real Codex-only init showed
why: the disabled block sits flush against the packaged file's `# analyze` and
`# peer` examples with no boundary, and init's commented keys are
indistinguishable from the file's explanatory prose, so a mechanical `# ` strip
runs past the last key and turns prose into TOML statements. `tomllib` rejected
it. Zach chose boundary markers over dropping the prose or rewording the
instruction. Now every non-blank line in the table's range is prefixed, prose
included (`# # ...`), the range ends at the last live key, and two marker
comments bracket it. A mechanical uncomment restores the packaged file byte for
byte, asserted for only-claude, only-codex and none. Body spec and test plan
updated to match.

**Hand walk on this Mac, from source.** Interactive init in throwaway repos
with `PATH` controlled:

| Case | Scan | coga.toml | coga-build `agent:` | validate |
| --- | --- | --- | --- | --- |
| only-codex | claude ○, codex ● | `[agents.codex]` live, claude bracketed | `codex` | All good (1 task) |
| none | both ○ | no live agent table | `claude` | the 2 predicted `coga-build` errors |
| both | both ● | byte-identical to packaged | `claude` | — |

The none-found errors are verbatim `unknown-agent` and
`unresolvable-operator`, both naming the table to restore, which is the
criterion. This Mac has a real `claude`, so only-claude could not be walked
with a real binary; its coverage is the parametrized end-to-end test.

**Adjacent finding, not fixed here.** A `coga` command published this
session's uncommitted work to `main`. At 17:51 Zach ran `coga mark active` on
`v1/re-run-the-macos-install-walk-from-source` in this checkout;
`7e342fbfa "Sync coga state"` committed and pushed both this ticket's
then-current edits *and* my uncommitted
`docs/contexts/coga-dev/internals/agent-config/SKILL.md` edit, a source file
outside `coga/`. Nothing was lost — the published docs edit is identical to the
one in this branch's second commit, and the rebase deduplicated it — but a
state sync that sweeps unrelated dirty source files can publish half-finished
work to the control branch. `v1/coga-bump-on-feature-branch-leaves-stale-index-loc`
is already in flight on sync behaviour and may be the right home.
`retro/done-ticket` owns carrying this into a durable context.

**Suite.** Every collected test ran at `d7d1518`, in two runs rather than one
(counts and commands in `## PR`). Six failures, none from this change. Four are
a single pre-existing `main` defect: `docs/contexts/coga-dev/internals/
branch-sweep/SKILL.md` links `#review-and-release-a-retained-local-draft` in
the packaged `coga/checkout-cleanup/branch-sweep` topic, which has no such
heading, so `test_packaging::test_context_navigation_has_no_broken_links` fails
and three wrapper tests that shell out to that file fail with it. Reproduced on
a clean clone of `origin/main` (`7e342fbfa`) with none of this branch applied.
It arrived with main's `6d1ca237f`; the fix is either adding the heading or
repointing the link, and it is not this ticket's to make. The other two
(`test_repl_supervisor`'s sentinel test, `test_trim_log`'s status test) pass
alone and pass with their own modules, matching the documented cross-test
pollution of a full in-place run in this checkout.

**Still outstanding.** The native-Windows full-suite receipt (tier 2 in
`coga-dev/testing`): this change does filesystem and encoding work on top of
the scan's non-ASCII glyphs, and the AWS harness is not reachable from this
session. It does not need a merge —
`scripts/clean-install/aws-windows.sh walk NAME <REF> WIN_USER` takes an
arbitrary ref. Recorded as a gate in `## PR`.

**What the tests cannot tell us.** The scan's assertions compare captured
Python strings, so they pass regardless of how a console renders
`├── └── ● ○`. A green native Windows suite is not evidence the tree displays
correctly; only an eyeball on a real Windows console is.
`v1/31-test-install-on-windows` (active, `human/run`) owns that question. To
run this branch there without merging: `uv tool install --force
git+https://github.com/FastJVM/coga@803c88b`. Both branch and main report
version `0.4.1`, so the reliable tell is that `main` has no `print_agent_scan`
at all — if `coga init` prints "Checking for agent CLIs...", it is this branch.

**For the hand test before the PR.** Zach's four-case VM walk from the branch
commit. In each case look at: the scan tree and the blank line above it; the
summary line naming what was commented out; the `[agents.*]` tables and the
markers around a disabled one; `coga-build.md`'s `agent:`; the `coga build`
coax and whether it offers an `--agent` alternative; and `coga validate`. The
case this Mac could not cover is only-claude with a real binary, and the case
never seen on any real machine is none-found — a fresh VM is exactly that.

## 2026-11-11 — peer-review (codex), then the markers came back out

**Peer review: no code defects.** Codex reviewed the branch on 2026-11-11
(session `01a1c922-798d-71a1-ae5c-d2b5dfa2b951`). Focused suite 181 passed in
32.17s; it also drove the scan in a real 42-column PTY for both-found and
none-found and confirmed the tree, glyphs, blank separation and green-only
colouring render without wrapping. Its full local suite was 4717 passed, 34
skipped, 15 failed in 1:36:05, and it classified every failure as outside this
change: twelve are sandbox-only `/dev/fd/*: Operation not permitted` errors in
unchanged clean-install harnesses, three are the already-recorded broken
branch-sweep anchor on `main` (one direct, two wrappers). Two non-blocking
notes: a stale test fixture comment naming the deleted `_offer_agent_cli`, and
a `## PR` file list carrying `docs/contexts/coga-dev/internals/agent-config/
SKILL.md`, which had already landed on `main` and is not in the branch diff.

The session ended before it could write any of that into this ticket or bump,
asking the owner for a rebase it could not perform from its sandbox. The
rebase happened on 2026-11-11 and the branch was force-pushed; `git diff`
across it is empty for `src`, `tests` and `docs`, so the receipts above carry.

**The markers were removed (Zach, 2026-11-11, mid hand-walk).** The
boundary-marker comments and the "re-enabling is mechanical, byte for byte"
criterion they satisfied were both added during the previous step. That
criterion was not in the approved ticket, which asked only that a not-found
agent's table be present but commented out and that init's next steps say to
uncomment it. Adding a criterion and then building to it is how the step
widened: this ticket adds the scan, the `PATH` read, and letting that read
write the toml. How the packaged file explains itself is Nico's, and not in
scope. The generated file is back to a plain `# ` on the table's own lines,
with the packaged prose and the `# analyze` / `# peer` examples untouched.
Focused suite re-ran at 178 passed — three fewer, being the marker round-trip
tests, which left with the code they covered.

**Known limitation, accepted.** A disabled table's commented lines sit
directly above the packaged file's own commented prose, so nothing marks where
the table ends. Someone stripping `# ` across the whole region would turn
prose into TOML statements; `coga validate` catches the result. This is a
property of the packaged file's layout rather than of the scan, and is not
this ticket's to fix.

**macOS hand walk — four cases, all passing.** Run by Zach 2026-11-11 in the
`cogatest-path-toml-write` VM at `c50a583a`, installed with `uv tool install
--force git+…@c50a583a` (uv's `(from git+…)` clause read back to confirm the
branch and not PyPI). `claude` was really installed in that VM, so only-claude
and both ran against a real binary — the case the previous step could not
cover. `codex` was an inert stub, which is faithful here because detection is
`shutil.which` and init never executes the binary. Each case ran in a fresh
repo under a `PATH` of one case directory plus `/usr/bin:/bin:/usr/sbin:/sbin`,
with `coga` invoked by absolute path because `claude` and `coga` share
`~/.local/bin`.

| Case | Scan | coga.toml | coga-build `agent:` | validate |
| --- | --- | --- | --- | --- |
| none | both ○ | no live table; both commented | `claude` | the 2 predicted errors |
| only-claude | claude ●, codex ○ | claude live (56), codex commented (85) | `claude` | All good |
| only-codex | claude ○, codex ● | codex live (85), claude commented (56) | `codex` | All good |
| both | both ● | both live at 56 and 85, none commented | `claude` | All good |

The two agent tables sit at lines 56 and 85 of the packaged template, and
appear at those same lines in every case, so commenting preserves the file's
structure. Observed by eye in every case: the tree glyphs `├── └── ● ○` render
as real characters with no wrapping, the blank line above the heading is
present, and green appears on found rows only. The summary line names what was
commented out and is absent in the both case, where there was nothing to say.
Next steps tracked the outcome without hardcoding: "install an agent CLI" only
when none was found, "with Codex" when codex was the default, and the
`coga build --agent codex` alternative only when both were present. The
disabled `[agents.codex]` block was read directly: its header and keys carry a
single `# `, and the packaged prose around it is unchanged.

**Adjacent, not fixed here:** `coga validate` prints `All good (1 tasks
checked)`. Pre-existing output this branch does not touch.

### Handoff — what is left, for whoever picks this up

Written 2026-11-11 on Zach's Mac, published to `main` without bumping so the
Windows checkout can take it from here. `status` and `step` are untouched:
still `in_progress` / `5 (peer-review)`.

1. **Windows VMware walk at `c50a583a`.** The last gate. Procedure and the
   expected table are in the artifact
   `https://claude.ai/code/artifact/69b3a926-21a6-4d7e-ab58-9c25952ec235`.
   Install with `uv tool install --force git+https://github.com/FastJVM/
   coga@c50a583a` and confirm uv's `(from git+…)` clause — the branch and
   `main` both report version `0.4.1`, so the version number proves nothing.
   What only this walk can answer is whether `├── └── ● ○` render on a
   Windows console; the tests compare Python strings and cannot see it.
2. **Record the result** in the table style used above, then update the
   `four-case interactive walk, Windows VMware VM` entry under `## PR`
   `checks`, which currently reads `PENDING`.
3. **Rebase onto current `main` before opening the PR.** As of this writing
   the branch is behind by the #1193 and #1194 merges. Verified clean:
   `git diff --name-only HEAD...origin/main` over this branch's seven files
   is empty, so the replay has nothing to conflict with. Re-point `base:` in
   `## PR` at whatever `main` is at that moment.
4. **Then `coga bump` (5 → 6) and `coga open-pr`.**

One receipt is now partly obsolete in a good way: `main`'s `4ee4d7e73` drops
the branch-sweep link anchor that caused the broken-link packaging failure,
which is three of the fifteen failures in codex's full-suite run and four of
the six in the implement run. A full suite taken after a rebase should show
those gone. Nobody needs to re-run one on that account; it is only noted so a
reviewer comparing counts is not surprised.

## 2026-11-11 — Windows VMware walk: four cases, all passing (Zach)

Handoff item 1 is done. Run by Zach in VMware Workstation's
`coga-win11-walk` (Windows 11 Home, build 26300), starting from the
`bare + tools` snapshot: clean Windows plus VMware Tools, with no Git, no
Python and no agent CLI. `walk1-done` was not used because it has a real
`claude`. Setup was Git 2.56.0.windows.4 through `winget` (it was present on
this fresh install), then uv 0.13.7, then `uv tool install --force --python
3.13 git+…@c50a583a`. uv's `(from git+https://github.com/FastJVM/
coga@c50a583a088bcba889b9ef0d745886628498aefe)` clause was read back. Recon
before the cases: `Get-Command claude, codex, coga` printed nothing, and the
shell was not elevated. Both agents were inert `.cmd` stubs, one case
directory each, prepended to the full `PATH`. Answered `n` to init's `gh`
install offer every time, so every case ran on the same machine. Windows
Terminal, Windows PowerShell 5.1.

| Case | Scan | coga.toml | coga-build `agent:` | validate |
| --- | --- | --- | --- | --- |
| none | both ○ | no live table; both commented (56, 85) | `claude` | the 2 predicted errors |
| only-claude | claude ●, codex ○ | claude live (56), codex commented (85) | `claude` | All good |
| only-codex | claude ○, codex ● | codex live (85), claude commented (56) | `codex` | All good |
| both | both ● | both live at 56 and 85, none commented | `claude` | All good |

Same table, same line numbers as macOS. Observed by eye in every case:
`├── └── ● ○` render as real glyphs on the Windows console with no wrapping,
the blank line above `Checking for agent CLIs...` is present, and green is on
found rows only. The summary line named what was commented out, and was
absent in both. Next steps matched macOS: install-and-uncomment only for
none, "with Codex" for only-codex, the `--agent codex` alternative only for
both. The none-case validate errors are verbatim `unknown-agent` and
`unresolvable-operator`, both pointing at the `[agents.*]` table to restore.

Two Windows-specific checks beyond macOS's:

- **Byte-identical, both case.** `Get-FileHash` of the generated
  `coga/coga.toml` and of the installed package's
  `resources/templates/coga/coga.toml` are equal (`28ECC840…FD76`). The
  rewrite path does not change line endings or encoding on Windows.
- **The disabled table, only-claude.** Lines 85–89 and 99 (`[agents.codex]`
  and its five keys) carry a single `# `. The prose at 90–98 and everything
  from 100 on is identical to the packaged template at `c50a583a`.

**Not this ticket's, recorded for v1/31.**

- `uv tool install` without `--python` fails on a machine with no Python.
  uv picks CPython 3.15.2, PyYAML 6.0.3 has no Windows wheel for 3.15, and
  the source build stops at "Microsoft Visual C++ 14.0 or greater is
  required". coga's `requires-python = ">=3.11"` has no upper bound. Walk 1
  missed this only because it installed Python 3.11 explicitly first.
- Every case printed `Skipped … skill wiring — …\.claude\skills\coga exists
  but isn't a directory` (and the same for Codex). `Get-Item` shows nothing
  exists there. This is v1/31 finding 8 (no symlink privilege without
  Developer Mode, reported under the wrong message), unchanged on `main`.
- Next steps in the none case still list "Run `coga build` with Claude Code"
  as item 2, after item 1 says no agent is installed. Minor wording; the
  agent-agnostic follow-up is the natural home.

## PR

```yaml
title: "Write coga.toml from init's agent-CLI scan"
author: claude (Claude Opus 5, 1M context) — implementing agent for this step
head: 01ce1cc180cd4367ecb3881a489469688cce6934  # c50a583a rebased onto 8baf8e326 on 2026-11-11; branch patch byte-identical, focused suite 178 passed after the rebase
base: 8baf8e326
review_depth: deep
review_depth_rationale: >
  Rewrites a committed config file that every later command reads, on the one
  code path a new user cannot skip, with a fallback that must never leave a
  truncated file. The commenting rule has two traps (the commented
  [recurring]/[launch] headers, and the prose interleaved with the keys) and
  the second already produced a real defect caught by hand, not by tests.
implementation: >
  One PATH read drives both init outputs. print_agent_scan returns its
  snapshot; _configure_agent_tables comments out the not-found agents' tables
  by prefixing their live lines and returns the names still declared; summary
  and next steps read the file back rather than the scan. The default comes
  from declaration order, so no default_agent key is written and the offer
  machinery is deleted.
deviations:
  - >
    Boundary markers around a disabled table shipped briefly and were removed
    by the owner on 2026-11-11, along with the "re-enabling is mechanical"
    criterion they satisfied — both had been added mid-implement rather than
    approved. The generated file matches the approved live-lines-only rule.
    Landed after peer review; the focused suite re-ran at 178 passed.
  - >
    _configure_agent_tables returns list[str] | None rather than bool, and the
    write goes through a temp file plus os.replace. Both came from the
    evaluator review's findings 2 and 4.
limitations:
  - >
    A repo that declares only Codex cannot run `coga chat`, even with
    `--agent codex`: bootstrap/orient pins `agent: claude` and a --agent
    override cannot repair a pin naming an undeclared type. Accepted by Zach
    2026-11-10; coga/configuration states the limit and the remedy.
  - >
    A one-agent repo cannot resolve an `other-agent` workflow step.
    Pre-existing in bump.resolve_other_agent; this change makes one-agent
    repos the norm for single-agent machines.
  - >
    A disabled table's commented lines sit directly above the packaged file's
    own commented prose with nothing marking where the table ends. Stripping
    `# ` across the whole region turns prose into TOML statements; validate
    catches it. A property of the packaged file's layout, out of scope here.
files:
  - src/coga/commands/init.py: >
      print_agent_scan returns its snapshot; _configure_agent_tables and
      _agent_table_state added; _offer_agent_cli, _write_default_agent and
      their two regexes deleted; call sites, summary and next steps rewritten.
  - src/coga/dependencies.py: >
      AGENT_CLIS registry and the PATH lookup the scan and the configuration
      both read.
  - tests/test_init.py: >
      agent-offer and write-default-agent tests deleted; configuration unit
      tests (4 cases), registry-extension and no-packaged-table cases,
      parse-back and write-failure cases, four end-to-end cases, summary,
      fallback and validate coverage.
  - tests/test_dependencies.py: >
      registry and PATH-lookup coverage for the scan's input.
  - src/coga/resources/templates/coga/coga.toml: >
      one comment block saying init comments out tables whose CLI it did not
      find, and to uncomment one to enable it.
  - src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: >
      Fresh repo rewritten for the scan-and-configure behaviour; clone
      paragraph says it neither scans nor rewrites coga.toml.
  - src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: >
      Choosing an agent rewritten for a one-agent repo; owns the Codex-only
      coga chat limitation in its own words, with no task link.
review:
  code_review: >
    Run by codex 2026-11-11 (session 01a1c922-798d-71a1-ae5c-d2b5dfa2b951):
    no must-fix findings. 181 focused passed, a real 42-column PTY check of
    the scan, and a full local suite of 4717 passed / 34 skipped / 15 failed
    with every failure classified as pre-existing and outside this change.
    Two non-blocking notes. The file list below no longer carries
    docs/contexts/coga-dev/internals/agent-config/SKILL.md, which had already
    landed on main and is not in the branch diff. The other is left in place:
    tests/conftest.py's _stub_init_dep_check still names the deleted
    _offer_agent_cli in its docstring and its monkeypatch loop. It is inert
    (raising=False, and tests/ is not shipped in the wheel); fixing it would
    move the head off the commit both hand walks ran against, which is not
    worth it for a dead test-only reference. Tidy it in a later change.
    The marker removal landed after this review at the owner's direction; it
    only deletes code, and the focused suite re-ran at 178 passed.
tested_tree: >
  Three trees are involved and they are not interchangeable. The implement
  receipts ran at d7d1518; the rebase onto main produced 803c88b5b with an
  identical `src`/`tests`/`docs` tree (`git diff d7d1518 803c88b5b -- src
  tests docs` empty). A second rebase onto current main produced 1405cc43e,
  again tree-identical, and that is the commit codex peer-reviewed. Removing
  the markers then produced c50a583a, the head of this PR, whose tree is
  byte-identical to f848223e0 — the commit before the markers landed. So the
  full-suite receipts below describe the marker-era tree, and everything at
  c50a583a is the same code minus the marker block. The focused suite and
  both hand walks ran at c50a583a itself.
checks:
  - command: PYTHONPATH=$PWD/src TERM=dumb python -m pytest tests/test_init.py tests/test_dependencies.py -q -p no:randomly
    result: 178 passed in 38.40s
    platform: macOS (Darwin 25.4.0), Python 3.12.7
    commit: c50a583a088bcba889b9ef0d745886628498aefe
    note: >
      The head of this PR. 181 at 1405cc43e; the three fewer are the marker
      round-trip tests, removed with the code they covered. Everything this
      change touches lives in these two files.
  - command: PYTHONPATH=$PWD/src TERM=dumb python -m pytest tests/test_init.py tests/test_dependencies.py -q
    result: 181 passed
    platform: macOS (Darwin 25.4.0), Python 3.12.7
    commit: d7d1518466a7d36bef698a3e5040bd37f62dd4ad
    note: >
      Re-run at the rebased head 803c88b5b with `-p no:randomly`: 181 passed,
      33s.
  - command: PYTHONPATH=$PWD/src TERM=dumb python -m pytest -q -p no:randomly
    result: >
      4418 passed, 25 skipped, 6 failed — of 4766 collected. Stopped at 93%
      (test 4449) by the harness, not by a failure. HEAD verified identical
      before and after, so the real checkout did not move under the run.
    platform: macOS (Darwin 25.4.0), Python 3.12.7
    commit: d7d1518466a7d36bef698a3e5040bd37f62dd4ad
    runtime: ~140 min
  - command: >
      PYTHONPATH=$PWD/src TERM=dumb python -m pytest -q -p no:randomly
      tests/test_trim_log.py tests/test_uninstall.py tests/test_upstream_coga.py
      tests/test_usage_report.py tests/test_usage.py tests/test_validate.py
      tests/test_version_guard.py tests/test_views.py
      tests/test_windows_clean_install.py tests/test_windows_process_recovery.py
      tests/test_workspace_discovery.py tests/test_repl_supervisor.py
    result: 402 passed, 10 skipped
    platform: macOS (Darwin 25.4.0), Python 3.12.7
    commit: d7d1518466a7d36bef698a3e5040bd37f62dd4ad
    runtime: 305s
    note: >
      The 317 tests the stopped run never reached (4450-4766), plus the two
      modules that held its unexplained failures. Together with the run above,
      every collected test has executed on this tree — but as two runs, not
      one clean full run. A reviewer wanting a single receipt should take one.
  - command: coga validate (by hand, in repos generated by a real interactive init)
    result: >
      clean for only-codex and both; for none, exactly unknown-agent and
      unresolvable-operator on coga-build
    platform: macOS (Darwin 25.4.0), Python 3.12.7
    commit: d7d1518466a7d36bef698a3e5040bd37f62dd4ad
  - command: full local suite (codex, during peer review)
    result: >
      4717 passed, 34 skipped, 15 failed in 1:36:05 — twelve sandbox-only
      `/dev/fd/*: Operation not permitted` errors in unchanged clean-install
      harnesses, three the known broken branch-sweep anchor on main. None
      touch this branch's code.
    platform: macOS, in codex's sandbox
    commit: 1405cc43eee461f265d966a189de1a5dfeee41f4
  - command: four-case interactive walk, macOS VM, installed from the branch SHA
    result: >
      all four match the predicted table (none / only-claude / only-codex /
      both); glyphs render, colour is correct, coga-build's agent: flips to
      codex in the only-codex case, validate clean except the two predicted
      coga-build errors in the none case
    platform: macOS VM (cogatest-path-toml-write), uv tool install from git
    commit: c50a583a088bcba889b9ef0d745886628498aefe
  - command: full suite natively on Windows (AWS harness)
    result: WAIVED BY OWNER 2026-11-11
    note: >
      coga-dev/testing tier 2 prescribes the AWS Windows harness for
      platform-sensitive changes, and the implement step copied that in as a
      merge gate. Zach waived it: Nico's harness work already covers native
      Windows, and the attended four-case walks are what answer whether this
      commit breaks anything. The harness is also unreachable from this
      machine — no aws CLI and no credentials — so it was never an option
      here. The Windows VMware walk below is this commit's native-Windows
      evidence.
  - command: four-case interactive walk, Windows VMware VM, installed from the branch SHA
    result: >
      4 of 4 passed (none, only-claude, only-codex, both). Glyphs render in
      Windows Terminal; the both-case coga.toml is byte-identical to the
      packaged template (Get-FileHash).
    platform: Windows 11 Home build 26300 (VMware Workstation VM), Python 3.13 via uv
    commit: c50a583a088bcba889b9ef0d745886628498aefe
    note: >
      The glyph question is the reason this one matters: the automated suite
      compares Python strings and cannot see how a Windows console renders
      the scan tree. Details under the 2026-11-11 Windows VMware walk entry.
  - command: Python 3.11 floor
    result: >
      not covered — 3.12.7 was the only interpreter available here
full_suite_failures: >
  6 failures, none from this change, all classified. Four are one defect:
  tests/test_packaging.py::test_context_navigation_has_no_broken_links fails
  because docs/contexts/coga-dev/internals/branch-sweep/SKILL.md links
  #review-and-release-a-retained-local-draft in the packaged
  coga/checkout-cleanup/branch-sweep topic, which has no such heading.
  Reproduced on a clean clone of origin/main (7e342fbfa) with none of this
  branch applied, so it is pre-existing; it arrived with main's 6d1ca237f.
  test_edge_distribution::test_documented_legacy_adoption_preserves_state_and_reconciles_callers
  and test_git::test_final_package_edits_never_escape_a_mutating_cli_sweep
  (both parametrizations) shell out to run tests/test_packaging.py, so they are
  that same defect, not three more. The other two —
  test_repl_supervisor::test_terminal_ticket_stops_repl_without_claiming_a_sentinel
  and test_trim_log::test_trim_preserves_all_discovered_statuses — pass alone
  and pass with their own modules on this tree, which matches the known
  cross-test pollution of a full in-place run in this checkout. Not fixed here:
  code/implement does not own unrelated failures.
```

## Open Questions

None.

## Superseded designs

### 2026-11-06 — the agent picker, the coga.toml rewrite, and the bootstrap unpinning

Superseded by: the scan-only scope in `## Description`.
Reason: Zach, during peer-review, judged the work far outside the ticket's
lane. The deliverable is Spec Kit's `specify check`, not a selection flow.

This entry retains the abandoned plan and the evidence gathered against it.
The code is at tag `archive/v1-20-pre-rescope` (`0156b008e`).

#### The abandoned shape

1. **Extract the picker into `src/coga/picker.py`.** Move `_decode_key`,
   `_read_key`, `_picker_window`, `_picker_view` and the body of
   `_pick_selection` out of `coga/commands/megalaunch.py`. One public entry,
   `pick(rows, columns, *, checked=(), hint) -> list[str] | None`, splitting
   what megalaunch conflates: a confirmed list, possibly empty, or `None` on
   quit. `_pick_selection` stays as the megalaunch adapter.
   `_picker_view`'s `no_wrap=True, overflow="ellipsis"` and its
   `max(1, console.size.height - 5)` row budget are load-bearing and must not
   become caller choices.
2. **A Windows input path, `picker._pick_numbered`.** `pick()` dispatches on
   `os.name == "posix"` at call time so a POSIX test can reach the numbered
   path. It must touch no `signal`, `termios`, `tty`, `select`, or
   `rich.Live` call — `_pick_selection` is POSIX-shaped end to end, installing
   a `SIGWINCH` handler and a `set_wakeup_fd` self-pipe before `termios` is
   ever reached.
3. **Ctrl-C gets its own action.** `tty.setraw` clears `ISIG`, so Ctrl-C
   arrives as a `b"\x03"` byte that `_decode_key` folds in with `q`. Harmless
   in megalaunch; in init it would have meant "commit the packaged
   both-agents config". Decoded as `"cancel"`, raising `KeyboardInterrupt`,
   with the megalaunch adapter catching it to stay byte-for-byte unchanged.
4. **`_choose_agents` + `AgentChoice`.** `enabled: tuple[str, ...]` in
   `AGENT_CLIS` order plus `default: str | None`. `None` meant "make no agent
   edits" — non-interactive, or the human quit with `q`/Esc.
5. **`_disable_unchosen_agents(text, enabled)`**, a pure text transform
   returning the edited document plus the names commented out, or `None` when
   the rewrite failed its own parse-back check.
6. **One all-or-nothing config edit** in `_do_init`: read the packaged
   `coga.toml` once, run both transforms in memory, write only if every stage
   returned a value, otherwise warn and leave the original. Warn rather than
   raise, because `_do_init`'s rollback `try` would otherwise cost the user
   the whole init.
7. **Unpin the packaged stateless targets** so a repo without `claude` can run
   `coga ticket` and `coga chat`.
8. Selection-aware next-steps strings.

#### Decisions taken, in case the selection flow returns

- **Unchosen tables are commented out, not deleted** (Zach, 2026-10-27). Both
  parse identically; commenting wins because re-enabling is deleting `# `s,
  because `coga update` never rewrites `coga.toml`, and because
  `coga/sandboxes` and `coga/configuration` both point at the shipped
  `coga.toml` as the explanation of record for these keys.
- **`q`/Esc changes nothing** (Zach, 2026-10-27): init continues, every agent
  stays declared, one line says so. Accepted cost: an accidental Esc leaves
  the both-agents config the ticket existed to fix.
- **Non-interactive prints no scan** — carried forward into the live scope.
- **The empty-selection confirm re-opens the picker with no retry limit**,
  because `q`/Esc is already the escape hatch and lands on a defined outcome.

#### Findings that cost real time — read these before redesigning

- **`_TABLE_START` (`^[ \t]*\[`) does not match a commented table header**,
  and the packaged `coga.toml` ships `[recurring]` and `[launch]` commented
  out. The first line it matches after `[agents.codex]` is `[notification]`,
  roughly eighty lines later. "Prefix `# ` to lines that are not already
  comments" would have commented every blank separator line in the
  `# --- Unattended runs ---` block, and the parse-back check cannot catch it
  because comments do not affect the parse. Fixed by skipping blank lines too.
- **Verified against the real packaged template:** commenting codex touches
  exactly 6 lines (header + 5 keys), claude exactly 7 (header + 6). The design
  had predicted 6 for claude.
- **`resolve_main_agent` raises on `agent=None`** unless
  `allow_prospective_default=True`. The unpinning would have broken
  `coga chat` rather than fixed it if `launch._target_operator` did not
  already pass that flag.
- **`fake_vendor` does not reach `_do_init`.** It patches
  `update_cmd.packaged_template_root`, but `commands/init.py` imports the name
  directly, so init copies the *real* packaged template. Tests comparing
  against the packaged `coga.toml` must use `_PACKAGED_COGA_TOML`.
- **`coga validate` does not cover a bootstrap target's `agent:`.** Its
  unknown-agent check only reads `agent:` on the refs `list_tasks(cfg)`
  returns, so it is no gate at all for `bootstrap/ticket` or
  `bootstrap/orient`.
- **`next(name for name in AGENT_CLIS if name != build_agent)` cannot raise
  today**, because `AGENT_CLIS` always holds two names. The real defect is
  that it advertises an agent the selection may not have declared.

#### Surfaces the unpinning falsified

Confirmed against the code, and all repaired on the abandoned branch. They
matter again only if the unpinning returns:

- `src/coga/resources/templates/coga/coga.toml:13-15` — "It does not move
  `coga chat` or `coga ticket`: their packaged tickets pin `agent: claude`."
- `docs/contexts/coga/configuration/SKILL.md:104` and its bundled twin — "the
  install-level default is `bootstrap/ticket`'s `agent:`".
- `docs/contexts/coga-dev/internals/agent-config/SKILL.md:58` — "onboarding
  tickets pin `agent: claude`, which outranks the default."
- `src/coga/config.py:374-376` comment — the same stale claim.
- `authoring.resolve_authoring_agent`'s docstring, and
  `test_megalaunch.py::test_author_draft_prefers_draft_agent_over_bootstrap`.

#### Evidence from the abandoned branch

Codex reviewed it directly and applied fixes, so the final-head receipt was
self-review at `0156b008e` / base `064917020`. Affected suites passed (637
tests). Direct PTY checks passed at 50x10 and 100x24 for pre-checked ENTER,
arrow/Space selection, and raw Ctrl-C restoring the terminal. The full suite
ran 4463 passed / 11 skipped / 15 failed, with twelve `/dev/fd` sandbox
failures and two packaging failures reproducing on an exact `origin/main`
archive, and one REPL timing failure that passed on rerun.

#### Open questions that died with the design

- Whether to warn when a single-agent selection makes `coga validate` error on
  tickets frozen on `code/with-review`. `code/with-self-review` was the
  intended answer.
- `bump.resolve_other_agent` infers the peer only at exactly two declared
  agents and raises at three or more, with nothing warning until the first
  handoff. **Still unfiled, and it becomes live when the Gemini sibling
  lands** — this one outlived the design.


### 2026-11-06 → 2026-11-10 — print-only scan (PR #1192)

Superseded by: scan-and-configure (`## Description`, 2026-11-10).
Reason: Nico closed PR #1192 — the scan must self-configure `coga.toml`, not
only print. The registry, rendering, and branch work carry forward.

The blackboard sections from that period follow verbatim, headings demoted.

#### Re-scope 2026-11-06 (Zach, during peer-review)

The ticket was cut to the scan alone, with Spec Kit's `specify check` as the
reference: show which agents coga supports and which are present on the
machine, and nothing else.

**Cut:** the multi-select picker, the `coga.toml` rewrite that commented
unchosen `[agents.*]` tables out, the `default_agent` move, and the unpinning
of the packaged `bootstrap/ticket` and `bootstrap/orient`. The whole abandoned
design is in `## Superseded designs`.

**Added:** the supported-agent registry. Nico's point that a user usually has
exactly one agent and it is often off-mainstream makes "adding the third agent
is one record" the part of this ticket with a future.

Zach's framing was that the previous session went far outside the ticket's
lane. It had: 8 commits, 1850+/694− across 26 files, four separable changes,
one of which belonged to open sibling PR #1176 and one of which changed
`coga ticket` / `coga chat` behaviour in existing repos that never run init.

##### What happened to the branch

No PR was opened. The branch was reset to `4c7751674` ("feat: scan for
supported agent CLIs during coga init", 34 lines) — the only commit inside the
new scope.

That commit is a **starting point, not the deliverable**. It predates the
registry work, and it hangs the scan inside `_offer_agent_cli`, which #1176
deletes and which returns early when both agents are installed. Both are
acceptance criteria now.

Nothing was lost. The abandoned work is at local tag
`archive/v1-20-pre-rescope` (`0156b008e`), and `origin/<branch>` still holds
pre-rebase copies of 7 of its 8 commits. Origin was deliberately not
force-pushed, so it is still the pre-reset history.

##### Findings worth keeping from the cut work

- The scan was run on a **fresh macOS VM** at `ff502c154`. The no-agent case
  rendered as two "not found" rows, which was the case that mattered.
- One defect that run surfaced: the scan collided with the `op` paragraph
  above it and read as another line of that block. It needs a leading blank
  line. Not yet fixed in `4c7751674`.
- `_AGENT_LABELS.get(name, name)` rather than `[name]`, so an unlabelled agent
  renders under its slug instead of raising. The registry should make this
  moot rather than repeating the `.get`.


#### Design 2026-11-06

Spec written into `## Description` (`### Proposed shape`) and `## Context`.
Derived against the code at `main` = `2a7f16f08` and against PR #1176's diff as
of today, since #1176 rewrites both modules this ticket touches.

What the read changed versus the ticket as written:

- #1176 **narrows** `_offer_agent_cli` rather than deleting it, and adds
  `_installed_agent_clis()`. The constraint bullet claiming deletion is
  replaced by `### Sequencing against #1176`, which records what #1176
  actually does to `dependencies.py` and `init.py`.
- #1176 deletes `install_hint` and both agent `Dependency` records, so the
  registry is built fresh and carries no install URL. #1176's `coga/install`
  text commits coga to "no agent installer command or URL", which rules a URL
  on the record out rather than leaving it a preference.
- Two new acceptance criteria: the leading blank line (the VM defect), and the
  next-steps strings going through the registry.

Zach chose the rendering in-session: Spec Kit's box-drawing tree, with the
binary in parens inside the label, over the flat three-column list the design
had proposed as its default.

The `_offer_agent_cli` default-agent confirm is untouched. It is #1176's
behaviour, not this ticket's.

#### Open Questions

None. The one the design raised — flat rows versus Spec Kit's box-drawing
tree — was put to Zach in-session on 2026-11-06 and answered: copy the tree.
The chosen rendering is in `### Proposed shape`.


#### Evaluator review

Verdict: not ready for implementation. Two scope contradictions need owner
resolution; the remaining proposed scan shape matches the current code and
PR #1176's head (`3badabee50b3e046ddf9205db0c1ff13c6454855`).

##### Must resolve before implementation

1. **Reconcile the no-question/no-write acceptance criterion with the
   preserved default-agent flow.** The Description says init "asks no
   question," and an acceptance criterion says it writes no `default_agent`
   change. But Proposed shape deliberately calls `_offer_agent_cli` and says
   its confirmation is untouched. On PR #1176's head,
   `src/coga/commands/init.py::_offer_agent_cli` asks a Codex-only user whether
   to change the default, and `_do_init` applies that answer through
   `_write_default_agent`. An implementer cannot satisfy both instructions.
   Either narrow the prohibition to the new scan itself and explicitly retain
   #1176's existing confirmation/write, or expand this ticket to remove that
   behavior and update the proposed shape and tests accordingly.

2. **Bound the "one record adds an agent" promise to the surfaces it actually
   covers, or include the remaining registries.** The acceptance criteria and
   opening rationale currently say adding an agent is one record in one
   module, and that every other label reader is total. Yet
   `src/coga/commands/init.py::_AGENT_SKILL_DIRS` remains a separate labeled
   Claude/Codex registry used by `_link_skills_for_agents`, while
   `src/coga/resources/templates/coga/coga.toml` separately declares the agent
   types Coga can drive. A third agent therefore cannot literally be added to
   Coga with only the proposed `AgentCLI` record. If the intended guarantee is
   only "one record adds a row to the scan and supplies init's next-step
   labels," say that consistently; otherwise the proposed shape is missing
   current consumers.

##### Optional recommendations

1. **Repeat the fresh-VM rendering check before handoff.** Zach requested a
   second interactive fresh-repo init run on the fresh VM. Inspect the leading
   separation from the `op` note, heading and blank line, tree branches and
   glyphs, color treatment, binaries, and found/not-found text in the real
   terminal; retain the result as implementation evidence.

##### Disposition (Zach, 2026-11-06, review-design)

Both must-fix findings were real and are resolved in the ticket text, not by
changing the planned code. Zach's instruction: this ticket does the scan and
nothing else, and #1176 removes the install offer and nothing else. The
`default_agent` behaviour is a separate question he and Nico will discuss
before anyone changes it.

1. **Resolved by narrowing the criterion.** "Init asks no question about
   agents and writes no `[agents.*]` or `default_agent` change" now reads "the
   scan asks no question and writes nothing," and a new Out-of-scope bullet
   records that the pre-existing confirm is untouched. The behaviour was
   verified by executing #1176's code rather than reading it: with only
   `codex` on `PATH`, `_offer_agent_cli('claude')` prompts "Make `codex` the
   default agent in coga.toml (instead of `claude`)?" with `default=True` and
   returns `'codex'`; `_write_default_agent` then uncomments line 16 of the
   shipped template to `default_agent = "codex"`. Three facts the evaluator did
   not state: that confirm is on `main` at `init.py:616` and predates both
   tickets, so #1176 neither adds nor edits it; the template ships
   `default_agent` commented out, so `claude` is the default only by
   declaration order and nothing is overwritten; and a yes also rewrites
   `agent: claude` in `coga/tasks/coga-build.md` (not in `bootstrap/`, which
   the glob does not reach). Deleting the confirm would also leave the
   empty-repo next-steps line telling a codex-only user to run `coga build`
   with Claude Code, since `build_agent` falls back to `AGENT_CLIS[0]` —
   fixable only by redesigning the coax, which is out of scope.

2. **Resolved by narrowing the claim.** "One record in one module" now reads
   "one record for the scan and for init's next-steps labels," in both the
   acceptance criteria and the Description. `_AGENT_SKILL_DIRS` and the
   packaged `coga.toml` are named in Out of scope as the surfaces a third
   agent still needs. Adding Gemini goes from four edits to three. Absorbing
   `_AGENT_SKILL_DIRS` into the record was considered and declined as outside
   the scan.

The optional fresh-VM render check stands as implementation evidence; the
collision with the `op` note that the first VM run found is already an
acceptance criterion.

#### Parked 2026-11-06 — waiting on #1176

Zach parked this at `review-design` rather than bumping. #1176 has merge
conflicts; the order is: fix #1176, present it to Nico, he merges if he likes
it, then restart this ticket. **Not bumped — `review-design` is still the
current step.** Both evaluator must-fix findings are already resolved in the
ticket text above, so the next session can bump without redoing review.

##### #1176's conflicts, verified

`git merge-tree origin/main pr/1176` against main at `16cb28a57` conflicts in
four files, and they are docs and tests only:

- `docs/contexts/coga/init/SKILL.md`
- `src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md`
  (the bundled twin of the above — one topic, two copies)
- `docs/contexts/coga-dev/internals/agent-spawn/SKILL.md`
- `tests/test_init.py`

`src/coga/commands/init.py`, `src/coga/dependencies.py` and `src/coga/launch.py`
all auto-merge clean. GitHub reports `mergeable: UNKNOWN`, so check locally
rather than trusting the API. Note that `coga/init` is a file *this* ticket
also edits, so whatever resolution #1176 lands with is the text to edit from.

##### What is actually on the branch

`4c7751674` is the only commit, and it is the pre-rescope scan. Treat it as a
sketch, not a starting point to extend — five acceptance criteria are unmet:

- it renders the flat three-column layout, not the Spec Kit tree Zach chose
- `_print_agent_scan(installed)` is private and takes an argument, so a later
  `coga check` cannot call it
- it is called from inside `_offer_agent_cli`, not from `_do_init`
- no registry: it still reads `_AGENT_LABELS.get(name, name)`
- no leading blank line, so the `op`-note collision is still there

It also adds its own tuple-returning `_installed_agent_clis`, which conflicts
with #1176's list-returning one. Resolve in favour of #1176's.

**Correction to the re-scope note above:** it says the scan "returns early when
both agents are installed." It does not — the call sits above
`if len(installed) > 1: return None`, so it prints in that case. The reason to
move the scan into `_do_init` is the five items listed here, not an early
return.

##### When restarting

**Reversed by Zach on 2026-11-09 — build on current main; see the note at the
end of this blackboard.** The two reasons given below are now accepted costs,
not blockers: the helper is extracted here instead of reused, and the
`AgentCLI` records do land beside `Dependency` records #1176 deletes.

~~Base implement on #1176's head, or on main once #1176 merges. Do not
implement against current main: `_installed_agent_clis` does not exist there,
and the `AgentCLI` records would land beside the `Dependency` records #1176
deletes.~~ The fresh-VM render check wants the redesigned scan, so it comes
after implement, not before.

##### A referenced sibling went away

`17a3b37a5` on main **canceled**
`marketing/fix-installer/add-gemini-as-an-agent-coga-can-drive`. *Out of scope*
still points at it as the owner of the third agent. Nico's reason for the
registry — users arrive with off-mainstream agents such as Kimi or Grok Build —
does not depend on Gemini, so the registry's justification stands. Decide
whether to re-point that bullet at the general case when the ticket restarts.

The post-#1176 helper and control-flow claims were verified: that PR is still
open, it defines `_installed_agent_clis`, the proposed fresh-init call site is
before `target.mkdir`, and `_setup_initialized_clone` is a separate path. The
ticket's explicit wait-for-#1176 sequencing handles the open PR.

#### Re-check 2026-11-06 (still parked, still waiting on #1176)

##### #1176's conflicts are gone

Its head moved to `b9057a89b` (two commits, 22 files, +252/−598) and
`git merge-tree origin/main refs/remotes/pr/1176` now returns a tree with no
conflicted paths, against main at `0309c437a`. The four files recorded as
conflicting above — both copies of `coga/init`, `coga-dev/internals/agent-spawn`,
and `tests/test_init.py` — all merge clean. GitHub still reports
`mergeable: UNKNOWN`, so keep checking locally. The PR is **open**, in front of
Nico; nothing to do here until he merges it.

##### The design spec was re-verified against `b9057a89b`

The evaluator reviewed `3badabee5`, so every anchor was re-read at the new head.
All of them hold, with exact lines:

- `dependencies.py:118` is still `AGENT_CLIS: tuple[str, ...] = ("claude", "codex")`, and the module has no `agent_label` and no `install_hint`.
- `init.py:579` defines `_installed_agent_clis() -> list[str]`; reuse it.
- `init.py:598-600` is the `if len(installed) != 1: return None` narrowing.
- `init.py:629` is `_AGENT_LABELS`, still the second registry to delete.
- `init.py:1343/1345/1347` are `_offer_optional_tools()`, `_offer_agent_cli(...)`, `target.mkdir(...)` — the proposed call site sits between the first two and is before the mkdir, as designed.
- `init.py:1578-1579` still spell `_AGENT_LABELS[build_agent]` and `_AGENT_LABELS[other]`, and `init.py:1569-1572` still spell "Claude Code (`claude`) or Codex (`codex`)" as a literal.
- `init.py:1650` is `_AGENT_SKILL_DIRS`, out of scope and unchanged.
- `coga/install`'s Prerequisites bullet still ends "Coga provides no agent installer command or URL"; `coga/init`'s "Fresh repo" still says "Init only scans `PATH` for them" at line 106.

##### Main's twin-parity test was red — fixed on main 2026-11-07, ignore this

**Resolved, kept only so the finding is not rediscovered.** The ten drifted
twins below were repaired on main by `ad2716f65`
(`fix/revert-swept-legacy-doc-copies`) and its neighbours. The test passes on
main at `3942e54b7`. There is nothing to work around and no ticket to file.

`python -m pytest tests/test_packaging.py::test_live_and_packaged_copies_stay_identical`
fails on clean `main` at `0309c437a`, before this ticket touches anything. Ten
twins have drifted:

    docs/contexts/coga/checkouts/launch-boundary/SKILL.md
    docs/contexts/coga/first-task/SKILL.md
    docs/contexts/coga/install/SKILL.md
    docs/contexts/coga/launch/SKILL.md
    docs/contexts/coga/recurring/scheduling/SKILL.md
    docs/contexts/coga/script-tickets/SKILL.md
    docs/contexts/coga/tickets/authoring/SKILL.md
    coga/skills/coga/releasing/SKILL.md
    coga/skills/coga/testing/clean-install/macos-aws/SKILL.md
    coga/skills/coga/testing/clean-install/windows-aws/SKILL.md

`coga/install` is one of them: its bundled twin carries the pre-native-Windows
Prerequisites text while the live copy has the Windows-baseline section. This
is unowned pre-existing drift, not this ticket's. Two consequences for
implement: still edit both copies of both topics verbatim, because the test
pins the pair this ticket touches as soon as the rest is fixed; and expect this
test to be red before and after, so read its failure for *this ticket's* two
paths rather than treating a red run as a regression.


#### 2026-11-07 — #1176 was closed, and this ticket's sequencing is now void

**Partly superseded by the 2026-11-09 note below: #1176 was reopened, so the
sequencing has a target again. The `coga/install` finding here still stands and
is now fixed in the ticket body.** Kept so the closure is not rediscovered.

Still parked at `review-design`, not bumped. Main moved 79 commits overnight
(`0309c437a` → `3942e54b7`). Three things changed that this ticket depends on.

##### #1176 is closed, not merged

Nico closed it at 2026-11-07 05:01Z with one comment and no review. It is not
merged: `agent_cli_setup.py`, `install_hint`, and the agent `Dependency`
records are all still on main. So every instruction in `### Sequencing against
#1176` and `### When restarting` that says "base implement on #1176's head, or
on main once #1176 merges" has no target. Do not act on it. The sibling ticket
`v1/remove-the-agent-cli-install-offer-from-coga-init` is at `step: 4 (review)`
and owns the response to Nico; what this ticket builds on depends on how that
lands, so the dependency stays but its shape is unknown.

Nico's comment, in full:

> coga build failed with "Agent CLI 'claude' not found in PATH. Coga requires
> the configured agent CLI on PATH for agent-backed commands." and printed
> nothing else.
>  => it's not supposed to be in the PATH but in the toml

The quoted string is #1176's own new text, from its
`dependencies.agent_cli_missing_message` — so he ran the PR branch. On main the
same failure appends "Install it from `<url>` and authenticate, then re-run."
from `install_hint`; #1176 deletes `install_hint` and replaces the remedy with a
restatement of the requirement. That is the "printed nothing else".

His second clause was ambiguous between "`cli` should accept a path so PATH is
not required" and "the message should point at the toml". **Resolved by Zach,
2026-11-07: the message is wrong and should name the config that declared
`cli = "claude"`, pointing at the toml as the place to change it.** The
path-accepting reading is rejected. The fix belongs to the sibling ticket,
which carries the full handoff under
`## Nico closed PR #1176 — handoff (2026-11-07, claude, ...)`.

##### `coga/install` was retired — this ticket's context list is stale

`8a88b5ada` ("Retire the coga/install topic", ticket
`v1/26-make-the-readme-install-section-the-only-install-p`) deleted both copies
of `docs/contexts/coga/install/SKILL.md`. The README "Get started" section is
now the only install path, and init's external-CLI install-offer facts moved
into `coga/init`.

Two consequences, both left unfixed in the ticket body above because it is
parked:

- The acceptance criterion "`coga/init` and `coga/install` describe the scan" names a topic that no longer exists. The scan fact now has one home, `coga/init`, plus possibly the README.
- `### Contexts to update in the same PR` lists `coga/install`'s "Prerequisites" bullet and quotes its "Coga provides no agent installer command or URL" sentence. Both are gone from the repo. `coga/init` is where to look for whatever survived.

##### The twin-parity test is green again

See the corrected note above. Nothing to work around, no ticket to file.


#### 2026-11-09 — spec brought current, and the wait on #1176 dropped

Attended session at `review-design`. No code written. The design itself did not
change: the scope is still the scan plus the registry behind it, as cut on
2026-11-06. Four stale facts in the ticket body were fixed, and the one open
design question was answered. Main is at `ce55fcffa`.

##### #1176 was reopened, so the sequencing has a target again

Nico closed it on 2026-11-07, Zach fixed the message he objected to, and it was
reopened the same day. It is **open** at head `ec8ad1bfa`, which merges
`origin/main` into the branch and conflicts with nothing
(`git merge-tree --write-tree origin/main refs/remotes/pr1176` returns a clean
tree). All three claims in `### Sequencing against #1176` were re-verified at
that head and hold; exact anchors are recorded in that section.

Nico's last word is 2026-11-07 21:51Z: "I skimmed through the code and could
find a lot of places. I highlighted two here already but I didn't read further
as it's clearly not there yet." Work continued on the branch after that comment,
but he has not responded since. That PR's `review` step owns the response, not
this ticket. Superseded later the same day: this ticket no longer waits on it —
see the note at the end of this blackboard.

##### The `PATH`-versus-toml question is answered (Zach, 2026-11-09)

#1176's handoff warned that this ticket would be asked why init scans `PATH`
when Nico's rule is that agents come from the toml. Zach's answer: scanning
`PATH` is the right flow, because at init time there is no `coga.toml` to read —
init is what creates it. The messaging #1176 fixed is correct for every command
that runs *after* init; the scan is a different question.

Written into the body as `### Why the scan reads PATH and not coga.toml`, with
three verified supports: the scan prints before `target.mkdir()`, so nothing is
written yet; the only init path where a `coga.toml` already exists is the clone
path, which prints no scan; and the packaged template declares `cli` but no
display name, so deriving rows from the template would still need the registry
for the labels. #1176's own `_installed_agent_clis` docstring already states
the reason and names this ticket as the owner, which is the reply to give Nico.

##### The docs tree was cut over — this is the big one

PR #1190 ("Enforce package-owned definitions after the repository cutover",
merged 2026-11-08) deleted the live `docs/contexts/coga/` tree. `docs/contexts/`
now holds only `coga-dev`, and `coga/init` exists in exactly one place:
`src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md`.
Twin equality was replaced by strict ownership in
`tests/required_package_resources.txt`, and
`test_packaging.py::test_live_and_packaged_copies_stay_identical` no longer
exists.

So the doc work is one file, not four, and every earlier instruction on this
blackboard about editing "both copies" or keeping twins byte-identical is void.
`### The context to update in the same PR` now says so.

##### What was edited in the body

- The doc acceptance criterion dropped `coga/install` and the twin clause.
- `### Contexts to update in the same PR` became
  `### The context to update in the same PR`: one packaged file, no twin, with
  the #1190 cutover recorded.
- `coga/install` references in `### Proposed shape` and `### What already
  exists and should be reused` were re-pointed at `coga/init`, which absorbed
  that topic's agent policy.
- Three Out-of-scope bullets stopped naming Gemini as the owner of a third
  agent — the sibling that owned it was canceled on main at `17a3b37a5`. The
  registry's justification is now stated as Nico's general case: users arrive
  with an off-mainstream agent such as Kimi or Grok Build.
- Two past-tense claims that #1176 "removed" things were corrected to
  "removes"; it has not merged.
- Added `### Why the scan reads PATH and not coga.toml`.

##### Branch state, unchanged

The local branch still points at `4c7751674`, the 34-line pre-design sketch.
`origin/<branch>` still holds all seven pre-re-scope commits (+1730/−493 across
21 files) and was deliberately never force-pushed. Neither is the deliverable;
implement starts from `### Proposed shape`. The archive tag
`archive/v1-20-pre-rescope` is still present locally.

##### The wait on #1176 was dropped — build alongside it (Zach, 2026-11-09)

Reversing the parking decision of 2026-11-06. Zach wants Nico reviewing both
PRs at the same time, so this ticket no longer waits for #1176 to merge. It is
built on current main and its PR targets main, giving Nico two independent
diffs. #1176 merges first and this branch reconciles afterward.

**Why not a stacked PR.** `open_pr.py:684` sets `base = cfg.git_control_branch`,
which is `main` and a repo-wide setting, so coga cannot open a PR against
#1176's branch. Hand-opening one is worse than it looks: `_refresh_body` at
`open_pr.py:591-594` raises "existing PR base differs or is unavailable" on any
later run, so the `open-pr` and `review` steps would refuse to manage the PR
they are supposed to own. The `code/open-pr` skill also forbids routing around
a refusal with a bare `gh pr create`. Stacking would additionally need a rebase
every time #1176's head moves, which it has done repeatedly under Nico's
review.

**The cost, accepted knowingly.** All five files this ticket touches are among
the 25 #1176 changes, so a conflict in every one of them is certain rather than
likely. `### Known reconciliation when #1176 merges` lists the per-file
resolution. Two implementation choices were added to shrink it: extract
`_installed_agent_clis` with #1176's exact name and `list[str]` return so the
overlap resolves by keeping either copy, and leave the "Install an agent CLI"
next-steps step untouched because #1176 deletes it outright.

**Order still matters.** #1176 merges first. If this ticket merged first it
would hand fresh conflicts to the PR that is already struggling in review.

##### Spec rewritten for build-on-main

`### Sequencing against #1176` was replaced by `### Build on current main,
alongside #1176`, which records what main actually has at `ce55fcffa` —
verified, not assumed:

- no `_installed_agent_clis`; the only `PATH` scan is inline at `init.py:595`
- `_offer_agent_cli` still branches three ways at `init.py:581-622`
- `install_hint`, both agent `Dependency` records with `install` URLs and
  `packages`, `Dependency.login` and the `npm` package manager are all present;
  `init.py:51-58` imports `install_hint` and `init.py:32` imports
  `agent_cli_setup.offer_agent_cli`
- the next-steps block has **three** agent readers at `init.py:1581-1592`, not
  two — an "Install an agent CLI" step built from `install_hint('claude')` /
  `install_hint('codex')`, plus the two `_AGENT_LABELS` lookups in the
  `coga build` coax

Three body edits followed: the next-steps acceptance criterion now scopes
itself to the `coga build` coax and excludes the install step; "The other label
readers" was rewritten for main's `default_agent or AGENT_CLIS[0]`; and "Order
of work" gained the helper extraction.

##### Ready to bump

Both evaluator must-fix findings were resolved on 2026-11-06, the open question
was answered the same day, and the spec is current against main at `ce55fcffa`
and #1176 at `ec8ad1bfa`. `review-design` needs no further pass — bump to
`implement` whenever Zach is ready, with no dependency left to wait on.


#### Implement 2026-11-09 (claude, attended)

Built on current main after #1176 merged, so none of the build-alongside
reconciliation applied. One commit, five files, no deviation from
`### Proposed shape` or the chosen rendering.

**Who ran this:** Claude Opus 5 (1M context), attended session with Zach. The
ticket's configured `agent: claude` is not execution evidence; this line is.

##### #1176 merged first, exactly as sequenced

It merged at `3acea3523` and its ticket is `done` on main. That voids
`### Known reconciliation when #1176 merges` and `### Build on current main,
alongside #1176` entirely — the blackboard's own escape clause ("If #1176 has
already merged by the time implement starts, none of this applies") is what
applied. Main already had `_installed_agent_clis` as a `list[str]`, a narrowed
`_offer_agent_cli` with the install branch gone, no `install_hint`, no
`agent_cli_setup.py`, and the "Install an agent CLI" next-steps step replaced
by a no-agent prerequisite line. The certain five-file conflict never happened.

##### What changed

`src/coga/dependencies.py` — added the `AgentCLI` frozen dataclass beside
`Dependency`: `name`, `label = ""`, and the `display` property returning
`label or name`. `AGENT_CLIS` is now `tuple[AgentCLI, ...]` holding
`AgentCLI("claude", "Claude Code")` and `AgentCLI("codex", "Codex")` in the
same order. Added `agent_label(name: str) -> str`, taking a plain string
because its callers hold an agent type that may not be registered. No derived
`tuple[str, ...]` alias, and no install URL or `packages` on the record.

`src/coga/commands/init.py` — deleted `_AGENT_LABELS`. Added public
argument-free `print_agent_scan()`, called from `_do_init` under
`if _interactive():` between `_offer_optional_tools()` and
`_offer_agent_cli(...)`. `_installed_agent_clis` kept #1176's name and
`list[str]` return and now reads `agent.name`; its docstring stopped naming
this ticket as a pending owner and states the resolved `PATH`-versus-toml
answer instead. The `coga build` coax reads `agent_label()` and
`AGENT_CLIS[0].name`.

`.../bootstrap/contexts/coga/init/SKILL.md` — one file, no twin (PR #1190
deleted the live `docs/contexts/coga/` tree). "Fresh repo" records that the
scan is printed and that its rows and the next-steps names come from one
registry; the clone section records that it prints no scan.

`tests/test_init.py` — six scan cases plus three full-init cases.
`tests/test_dependencies.py` — `agent_label` both ways and `display`'s
fallback.

##### Rendering, as executed

    Checking for agent CLIs...

    Agent CLIs coga can drive
    ├── ● Claude Code (claude) — found
    └── ○ Codex (codex) — not found

Matches the tree Zach chose on 2026-11-06. The leading blank line is present
and asserted (`out.startswith("\n")`), which is the fresh-VM `op`-note
collision fixed.

##### Two things done beyond the literal shape, both deliberate

- **#1176's no-agent prerequisite line now reads the registry.** It spelled
  "Claude Code (`claude`) or Codex (`codex`)" as a literal, a third place a new
  agent would need editing. `### Known reconciliation` assigned routing it
  through the registry to the session landing after #1176, and this is that
  session. With two agents the rendered string is byte-identical to before, so
  #1176's own assertions on that line pass unchanged.
- **Fixed a test that records converted would silently pass.**
  `test_agent_clis_have_no_install_metadata` asserted
  `dependency_names.isdisjoint(AGENT_CLIS)`. Against records that is trivially
  true — a `Dependency` name string never equals an `AgentCLI` — so the guard
  would have stopped guarding. It now compares
  `{agent.name for agent in AGENT_CLIS}` and also asserts no record carries an
  `install` attribute.

##### Verification: bounded, not a completed full suite

**Zach's call, 2026-11-09:** bump on bounded evidence and record the gap rather
than spend another hour on chunked runs. Peer-review and open-pr can run the
full suite.

854 tests passed across 10 files. Receipts are in `## PR`. The branch was
rebased twice during the step as main moved; the primary check was re-run at
the final head `b64415d10`, and the three longer receipts name the pre-rebase
head they actually ran at, with `git diff 3113e4f04 b64415d10 -- src tests`
empty as the proof that the tested source is identical. No receipt's OID was
restamped. `python -m pytest` in full **did not complete** in this session:

- Run 1 was killed by me, correctly: main moved mid-run (PR #1189 merged), so
  it was testing a stale tree.
- Run 2 was killed externally at 34% with exactly one `F` near 30% and nothing
  else failing.
- Run 3, a 15-file chunk, exceeded the 9m40s tool ceiling and returned nothing.

The suite is genuinely slow here — `test_launch` + `test_megalaunch` alone is
421 tests in 8m26s — so a full run is roughly an hour. That `F` near 30% is
probably the pre-existing `test_edge_distribution` failure below (file 28 of
87, landing near 30% of the test count, and the only failure known to exist in
that range), but this was **not confirmed**, so treat it as unidentified.

The blast radius was bounded by grep rather than assumed: every module
importing `coga.dependencies` other than `init.py` imports only
`agent_cli_missing_message`, which is untouched, and nothing outside `init.py`
reads `AGENT_CLIS`, `agent_label` or `AgentCLI`. The two importers of
`commands.init` are `cli.py` and `uninstall.py`. All of those modules' test
files were run and pass, so every module that can be affected has been
exercised. No seeded-fixture update was needed: the change touches neither
prompt composition, workflow freezing, config loading nor task creation, and
`coga validate` behaviour is unchanged.

##### A pre-existing test failure, not mine

`tests/test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`
fails with four extra `coga/recurring/_custom-phone-home/ticket.py`-style
paths. Verified pre-existing: it reproduces identically in a detached worktree
of pristine main at `991037866` with none of this branch's edits, in 18.7s. It
concerns legacy recurring-job adoption and touches nothing this ticket
changed. Unowned and unfiled.

##### Two checks still owed, neither done here

- **The fresh-VM render check.** The evaluator's optional recommendation, and
  Zach asked for it. Not done. Both agents are installed on this machine, so
  the not-found rows above came from faking `shutil.which`, not from a machine
  that genuinely lacks them. Glyphs, colour, and separation from the `op` note
  are unverified on a clean VM at this revision.
- **A tier-2 Windows receipt may be owed before merge.** The scan prints new
  non-ASCII — box-drawing glyphs, `●`/`○`, and an em dash.
  `coga-dev/testing`'s tier 2 calls a change platform-sensitive when it touches
  terminal handling or encoding and requires a native Windows full-suite run
  before merge. The ticket forbids *solving* the Windows console question here
  (`v1/31-test-install-on-windows` owns it, and `_print_notification_state`
  already prints `✓` on the same path, so this is not a new exposure), but it
  says nothing about whether the tier-2 receipt is still required. Raised with
  Zach rather than decided here; open-pr or review should settle it.

##### Branch history: origin was force-pushed

The blackboard recorded that `origin/<branch>` deliberately still held the
seven pre-re-scope commits. That is no longer true — this step force-pushed, so
origin now holds the single implement commit. Both recovery points were checked
after the push and survive locally: tag `archive/v1-20-pre-rescope`
(`0156b008e`) holds the full abandoned work, and the pre-reset origin tip
`477a6b175` still resolves.

##### For peer-review

The diff is small and self-contained. The two judgement calls worth attention
are the two "beyond the literal shape" items. The acceptance criterion that a
third agent is one record is enforced by
`test_agent_scan_renders_an_agent_added_to_the_registry`, which patches
`coga.commands.init.AGENT_CLIS` — patching `coga.dependencies.AGENT_CLIS` does
not work, because `init` binds the name at import.


#### Peer review

Direct Codex review **completed** on 2026-11-09 at
`fa36ebd2c13f18494b77a17a6adf1c9f8fe5f0a5`, against merge base
`cb378d532e0f7a34a91753901f47da758524d4b4`. This was independent review of
Claude's implementation. It covered the complete five-path diff, every
`AGENT_CLIS` / `agent_label` reader, fresh-init and clone call ordering, the
package-owned `coga/init` contract, and the new tests. No must-fix code finding
or unresolved design issue was found; no review fix commit was needed.

The human-visible surface was driven in a real PTY, not only through captured
tests. At 80x24, a fresh Git repo with a restricted `PATH` containing neither
agent printed the missing-`op` note, one blank separator, the progress line,
blank line and complete two-row tree; init then completed. At 40x12, a second
run with only `claude` available rendered the Claude row green and the Codex
row uncoloured, with the chosen box-drawing glyphs and no layout defect.

The full supported-version suite passed on Ubuntu 26.04 / WSL2 with Python
3.12.13: 4,719 passed, 33 skipped in 469.26s. Python 3.14.4 produced 4,718
passed, 33 skipped and one failure in 471.01s; the same cyclic-symlink message
expectation fails on pristine `origin/main`, and the exact node passes under
3.12. A first 3.14 run also exposed CRLF bytes in the checkout's packaged
phone-home script despite a clean Git status; normalizing that working-tree
file to the committed LF blob made all four affected trim-log cases pass and
left no diff.

The remaining gate is external to this diff: the new non-ASCII terminal output
makes this platform-sensitive under `coga-dev/testing`, so a native Windows
full-suite receipt is required before merge. No AWS Windows run was authorized
in this session. The PR recommendation is therefore `deep`, not merge-ready.
The branch was unconditionally rebased onto current `origin/main`, re-reviewed,
and force-pushed with lease.


#### PR

```yaml
title: Print a supported-agent-CLI scan during coga init
author: claude
author_evidence: >-
  Implement session 2026-11-09 ran Claude Opus 5 (1M context), attended by
  Zach; see the implement handoff above.
head: fa36ebd2c13f18494b77a17a6adf1c9f8fe5f0a5
base: cb378d532e0f7a34a91753901f47da758524d4b4
depth: deep
rationale: >-
  The bounded implementation is understood and independent review found no
  code defects, but the Unicode terminal surface is platform-sensitive and
  has no required native-Windows full-suite receipt. Inspect the diff and do
  not merge until that receipt exists.
implementation: >-
  Interactive fresh-repo `coga init` now prints a Spec Kit-style tree of
  every agent CLI Coga can drive, with each display name, binary and PATH
  result. `AGENT_CLIS` is now the single record registry for the scan and
  init's next-step labels, with total fallback for label-less entries.
deviations: >-
  Two deliberate additions beyond the literal proposed shape remain: the
  post-#1176 no-agent prerequisite line also reads the registry instead of
  spelling both agents literally, and the installer-metadata regression test
  compares record names so converting strings to records did not make it
  vacuously pass. Review found both changes correct and in scope.
limitations: >-
  No native Windows run was performed; repository policy requires its full
  suite before merge because the scan adds non-ASCII terminal output. The
  fresh-machine case was exercised with a restricted PATH in a real Linux
  PTY, not on a fresh VM. Python 3.14.4 has one unrelated full-suite failure
  in the cyclic-symlink diagnostic test that reproduces on pristine main;
  Python 3.12.13 is fully green.
files:
  src/coga/dependencies.py: >-
    Adds the `AgentCLI` record and `agent_label`, and converts `AGENT_CLIS`
    from binary strings to the registry shared by init's readers.
  src/coga/commands/init.py: >-
    Adds public argument-free `print_agent_scan`, calls it only for
    interactive fresh init before writes, deletes `_AGENT_LABELS`, and routes
    next-step agent names through the registry.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: >-
    Records the interactive fresh-init scan and the clone-path exclusion in
    the sole package-owned `coga/init` topic.
  tests/test_init.py: >-
    Covers every scan state, registry extension, label fallback, empty
    registry, before-write ordering, non-interactive init and clone setup.
  tests/test_dependencies.py: >-
    Covers known and unknown labels, display fallback, and preserves the
    no-agent-installer-metadata guard after the registry conversion.
review:
  reviewer: codex
  kind: independent
  status: passed
  head: fa36ebd2c13f18494b77a17a6adf1c9f8fe5f0a5
  base: cb378d532e0f7a34a91753901f47da758524d4b4
  detail: >-
    Direct Codex review completed on the final rebased diff with no must-fix
    code findings. Real-PTY rendering passed at 80x24 and 40x12. The review
    does not recommend merge without the required native-Windows receipt.
checks:
  - command: TERM=dumb PYTHONPATH=/home/zach2179/dev/coga/src /home/zach2179/coga-review-venv312/bin/python -m pytest
    status: passed
    head: fa36ebd2c13f18494b77a17a6adf1c9f8fe5f0a5
    base: cb378d532e0f7a34a91753901f47da758524d4b4
    detail: >-
      Ubuntu 26.04 LTS under WSL2, Python 3.12.13: 4,719 passed, 33 skipped
      in 469.26s. Full supported-version suite at the final head.
  - command: TERM=dumb PYTHONPATH=/home/zach2179/dev/coga/src /home/zach2179/.venvs/coga/bin/python -m pytest tests/test_init.py tests/test_dependencies.py tests/test_packaging.py
    status: passed
    head: fa36ebd2c13f18494b77a17a6adf1c9f8fe5f0a5
    base: cb378d532e0f7a34a91753901f47da758524d4b4
    detail: >-
      Ubuntu 26.04 LTS under WSL2, Python 3.14.4: 207 passed in 4.45s;
      covers both changed modules and package-resource ownership.
  - command: TERM=xterm-256color PATH=/tmp/coga-scan-review.DOOjqm/bin PYTHONPATH=/home/zach2179/dev/coga/src /home/zach2179/.venvs/coga/bin/python -m coga.cli init /tmp/coga-scan-review.DOOjqm/repo --user tester
    status: passed
    head: fa36ebd2c13f18494b77a17a6adf1c9f8fe5f0a5
    base: cb378d532e0f7a34a91753901f47da758524d4b4
    detail: >-
      Real 80x24 PTY with neither agent on PATH. The missing-op note, leading
      separation, headings, full not-found tree and completed fresh init all
      rendered as designed.
  - command: TERM=xterm-256color PATH=/tmp/coga-scan-review.DOOjqm/bin PYTHONPATH=/home/zach2179/dev/coga/src /home/zach2179/.venvs/coga/bin/python -c 'from coga.commands.init import print_agent_scan; print_agent_scan()'
    status: passed
    head: fa36ebd2c13f18494b77a17a6adf1c9f8fe5f0a5
    base: cb378d532e0f7a34a91753901f47da758524d4b4
    detail: >-
      Real 40x12 PTY with only claude on PATH. The Claude row rendered green,
      Codex stayed uncoloured, and the tree remained legible.
  - command: TERM=dumb PYTHONPATH=/home/zach2179/dev/coga/src /home/zach2179/.venvs/coga/bin/python -m pytest
    status: failed
    head: fa36ebd2c13f18494b77a17a6adf1c9f8fe5f0a5
    base: cb378d532e0f7a34a91753901f47da758524d4b4
    detail: >-
      Ubuntu 26.04 LTS under WSL2, Python 3.14.4: 4,718 passed, 33 skipped,
      1 failed in 471.01s. The sole failure is
      test_config::test_layout_contexts_cyclic_root_rejected; it reproduces
      identically on an exported pristine origin/main tree and its exact node
      passes under Python 3.12.13.
  - command: Native Windows full suite through the Windows AWS harness
    status: not-run
    detail: >-
      Required before merge because this platform-sensitive change adds
      non-ASCII terminal output. No external AWS run was authorized during
      peer review.
  - command: coga validate --json
    status: not-run
    detail: >-
      Validation behavior and config/task schemas are unchanged; the diff is
      init console output, its label registry, tests and owning documentation.
```
