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
it found. It scans `PATH` and keeps the result to itself.

Make init print that scan: a heading, then one row per supported agent
carrying its display name, its binary, and whether that binary is on `PATH`.
The list is complete in every state, including when nothing was found.

The model is GitHub Spec Kit's `specify check`, which lists every supported
agent tool with a found / not-found marker. Copy it.

Coga drives Claude Code and Codex today, and the scan lists those two. The
other half of this ticket is making a third cheaper: one record feeds the scan
and init's next-steps labels, with no edit to either. Users commonly arrive
with an off-mainstream agent, so the registry is the part of this with a future.

The scan offers no install and asks no question. An agent that is not on `PATH`
is named with its binary so the user can install it or put it on `PATH`.

### Acceptance criteria

- [ ] Interactive `coga init` on a fresh repo prints a scan of the supported
      agent CLIs: a heading, then one row per agent with its display name, its
      binary, and whether that binary was found on `PATH`.
- [ ] Every supported agent appears in every state, including when none was
      found. A machine with nothing installed reads a complete list, not an
      absence.
- [ ] Nothing in the scan is hardcoded. Rows are built from the supported-agent
      registry, so an agent added there renders with no edit to the scan.
- [ ] Adding an agent is one record for the scan and for init's next-steps
      labels. Today those two readers are split between
      `dependencies.AGENT_CLIS` and `init._AGENT_LABELS`, which sit in
      different layers.
- [ ] A test adds an agent to the registry and asserts it renders, so the
      claim above is enforced rather than asserted.
- [ ] A registry entry with no display name renders under its slug instead of
      raising, in the scan and in init's next-steps strings.
- [ ] The scan is a standalone function taking no init state, so a later
      `coga check` can call it without a refactor.
- [ ] The scan prints on every interactive fresh-repo init, including when
      more than one agent CLI is installed.
- [ ] The scan asks no question and writes nothing. The pre-existing
      default-agent confirm is left exactly as it is.
- [ ] Non-interactive init prints no scan, and the clone path prints no scan.
- [ ] The scan is separated from whatever init printed above it by a blank
      line, so it does not read as another line of the `op` note.
- [ ] The `coga build` coax in `_do_init`'s next steps names agents through
      the registry, not through literals, so the third agent needs no edit
      there either. The "Install an agent CLI" step above it is left alone:
      #1176 deletes it.
- [ ] `coga/init` describes the scan and `python -m pytest` passes.

### Proposed shape

**One record, in `src/coga/dependencies.py`.** Add a frozen dataclass beside
`Dependency`:

    @dataclass(frozen=True)
    class AgentCLI:
        name: str
        label: str = ""

        @property
        def display(self) -> str:
            return self.label or self.name

`name` is both the binary coga scans `PATH` for and the `[agents.*]` type the
shipped `coga.toml` declares — one string, because the packaged template's
`[agents.claude]`/`cli = "claude"` and `[agents.codex]`/`cli = "codex"` make
them equal for every agent coga ships. The `display` property is what makes
the missing-label case total by construction: no caller repeats a `.get`.

`AGENT_CLIS` changes from `tuple[str, ...]` to `tuple[AgentCLI, ...]` holding
`AgentCLI("claude", "Claude Code")` and `AgentCLI("codex", "Codex")`, in the
same order. Keep the name: it still means "the agent CLIs coga can drive",
now as records. Do not add a derived `tuple[str, ...]` alias — two public
names for one list is the split this ticket exists to close.

Delete `init._AGENT_LABELS` and add `dependencies.agent_label(name: str) ->
str`, returning the matching record's `display` and otherwise `name` itself.
It takes a plain string rather than a record because its callers hold an agent
type that may not be in the registry at all — `_do_init`'s `build_agent` comes
from `default_agent`.

The record carries no install URL and no `packages`. Sibling #1176 removes
every agent-installer URL from `dependencies.py` and leaves nothing in Coga
holding one; a URL on the record would put one back.

**One scan, in `src/coga/commands/init.py`.** Add a public, argument-free
`print_agent_scan() -> None`. Public and argument-free is the whole point of
the acceptance criterion: a later `coga check` imports and calls it with no
init state to supply. It calls `_installed_agent_clis()` itself, returns early
on an empty registry rather than printing a heading with nothing under it, and
prints with `typer.echo` / `typer.secho` — no `rich`, matching the rest of
init's output. Its first line is an empty `typer.echo("")` — the VM run showed
the scan colliding with the `op` note above it. Rendering (Zach,
2026-11-06 — copy Spec Kit's tree):

        Checking for agent CLIs...

        Agent CLIs coga can drive
        ├── ● Claude Code (claude) — found
        └── ○ Codex (codex) — not found

Spec Kit's two lines are kept as they are: a progress line, a blank, then the
titled tree. The binary rides in parens inside the label, so rows need no
column alignment — only the last row takes `└──`. Green for found, uncolored
for not found; not found is not a warning colour, because having one agent is
the normal case.

The box-drawing glyphs, `●`/`○`, and the em dash are all non-ASCII on a
`requires-python = ">=3.11"` floor, so a Windows console in a legacy code page
could fail to encode them. `_print_notification_state` already prints `✓` on
the same path, so this is not a new exposure, and the Windows console question
belongs to `v1/31-test-install-on-windows`. Do not solve it here; do not
quietly downgrade the glyphs to ASCII either.

It lives in `init.py` rather than `dependencies.py` so the manifest stays
data-only — it imports nothing but `dataclasses` today. A standalone
`src/coga/agent_scan.py` is the alternative, and is a module for twenty lines
right after #1176 deleted `agent_cli_setup.py` to shrink the surface.

**One call site.** In `_do_init`, `if _interactive(): print_agent_scan()`,
placed between `_offer_optional_tools()` and `_offer_agent_cli(...)`. That
position gets all four properties the acceptance criteria ask for: it is
inside no early-returning branch, so every interactive fresh init prints it;
it is before `target.mkdir()`, so it is outside the rollback `try`; it is
after the `op` note, so the blank line is what separates them; and it is
before the "make this the default agent" confirm, which the scan now gives
context to. `print_agent_scan` itself holds no interactivity check, so a
`coga check` that always prints can reuse it.

`_setup_initialized_clone` gets no call — the clone path prints no scan.

**The other label readers.** On main the `coga build` coax is the one that
changes: `_AGENT_LABELS[build_agent]` and `_AGENT_LABELS[other]` become
`agent_label(...)` calls. `build_agent = default_agent or AGENT_CLIS[0]`
becomes `... or AGENT_CLIS[0].name`, and
`next(a.name for a in AGENT_CLIS if a.name != build_agent)` keeps its current
"pick any other" behaviour; redesigning that coax for three agents is not this
ticket. The "Install an agent CLI" step above it keeps its `install_hint`
literals — #1176 deletes that step, so see
`### Build on current main, alongside #1176`.

**Order of work.** Registry first (`dependencies.py` + `agent_label`), then
the `init.py` readers it breaks, then extract `_installed_agent_clis` from
`_offer_agent_cli`, then `print_agent_scan` and its call site, then
`coga/init`, then tests.

**Tests**, in `tests/test_init.py` near the existing agent-offer tests, reusing
the `_agent_picker`-style tty fake:

- No agent on `PATH`: every registry entry renders with its binary and
  "not found". This is the case that matters.
- Both agents on `PATH`: the scan still prints. This is the case that returns
  early inside `_offer_agent_cli` today.
- An agent added to the registry renders with no edit to the scan.
- `AgentCLI("gizmo")` with no label renders as `gizmo`, in the scan and
  through `agent_label`.
- Non-interactive init prints no scan.
- The clone-setup path prints no scan.

In `tests/test_dependencies.py`: `agent_label` returns the label for a known
agent and the input string for an unknown one.

### Out of scope

- **Asking which agents to enable.** The picker, the `coga.toml` rewrite that
  commented unchosen `[agents.*]` tables out, and the `default_agent` move are
  all cut (Zach, 2026-11-06). Init still ships both tables, so the original
  complaint — a Claude-only user commits a config declaring a Codex binary
  they do not have — stays unfixed. It is unfiled; file it if it still matters
  once the scan has run.
- **Changing what init does with `default_agent`.** `_offer_agent_cli` already
  asks a user whose only agent CLI is `codex` whether to make it the default,
  and on a yes uncomments `default_agent = "codex"` in `coga.toml` and rewrites
  the `agent:` field of `coga/tasks/coga-build.md`. This confirm is on `main`
  and predates both this ticket and #1176; #1176 only narrows when it fires by
  deleting the install branch above it. It is untouched here. Zach and Nico
  will discuss what it should be before anyone changes it (Zach, 2026-11-06).
- **The other two places a third agent still needs.**
  `init._AGENT_SKILL_DIRS` carries its own label pairs for
  `_link_skills_for_agents`, and the packaged `coga.toml` declares each
  `[agents.*]` table as shipped text. Neither is folded into the registry
  here, so adding a third agent goes from four edits to three, not to one.
- **Offering to install an agent CLI.** Out now, not ruled out forever (Nico,
  2026-11-04). Sibling `v1/remove-the-agent-cli-install-offer-from-coga-init`
  (PR #1176) removes the existing offer. Do not reintroduce one, and do not
  write a rule anywhere saying coga never will.
- **A standalone `coga check`.** Spec Kit's scan is its own command; coga's is
  init-only for now. The acceptance criteria keep the function callable from
  one later, which is all this ticket owes it.
- **Adding a third agent.** No ticket owns one. The sibling that owned Gemini
  was canceled on main at `17a3b37a5`, so the registry's justification is the
  general case Nico gave: users arrive with an off-mainstream agent such as
  Kimi or Grok Build. This ticket makes room for one and adds none.
- **Unpinning the packaged stateless targets.** `bootstrap/ticket` and
  `bootstrap/orient` keep `agent: claude`. Only the cut selection made
  unpinning necessary.
- **Extracting megalaunch's picker.** There is no picker, so there is nothing
  to extract and `coga.megalaunch` is untouched.
- **Install URLs or packages on the registry record.** #1176 removes every
  agent-installer URL from `dependencies.py`. The record carries a binary and
  a display name, nothing that could install anything.
- **Splitting the agent type from its binary.** `AgentCLI.name` is one field
  serving both because the packaged `coga.toml` declares `cli = "claude"`
  under `[agents.claude]`. Split it when a supported agent's binary first
  differs from its table name.
- **Redesigning the `coga build` coax for three agents.**
  `next(... if a.name != build_agent)` advertises an arbitrary second agent;
  that is pre-existing and stays. Related and still unfiled:
  `bump.resolve_other_agent` infers the peer only at exactly two declared
  agents and raises at three or more, which goes live when a third agent
  lands.

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
  That is why the registry matters more than the two names in it today.
- Zach on 2026-11-06: copy Spec Kit's `specify check`; the scan is the whole
  ticket.

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

Two deliberate departures from it:

- Spec Kit omits the binary name. Coga carries it, because coga's follow-up is
  "put `claude` on your `PATH`" and the binary is what the user acts on.
- Spec Kit's `○ (no CLI required)` marks IDE-based tools. Every agent coga
  drives is a CLI, so coga's markers are found / not found.

### What init does today

`init._offer_agent_cli` holds the only `PATH` scan and shows the user none of
it. Non-interactive returns immediately. More than one agent CLI on `PATH`
returns early. Claude-only is chosen silently. Codex-only reaches a confirm
about `default_agent`. Only the no-agent case prompts, as free text.

After #1176 that last branch is gone and `_offer_agent_cli` handles only the
exactly-one case. Either way, nothing shows the user the supported list — that
absence is what this ticket fixes.

### What already exists and should be reused

- `dependencies.AGENT_CLIS` is the ordered tuple of supported binaries, and
  `init._AGENT_LABELS` maps slug to display name. Merging them is the registry
  work.
- `dependencies.py` already holds the `Dependency` frozen dataclass and its
  module docstring already claims to be the single source of truth for coga's
  external CLIs, so a supported-agent record belongs beside it rather than in
  a command module.
- `coga/init` describes the same set for humans, and absorbed the retired
  `coga/install` topic's agent policy. `dependencies.py`'s docstring says
  keeping the list in one place is what stops the check and the docs drifting;
  the split between `AGENT_CLIS` and `_AGENT_LABELS` is that claim already
  half-broken.

### Constraints that are easy to miss

- **The clone path must not scan.** A clone's `coga.toml` is committed team
  config, and the scan is about this machine. `coga/init` ("Clone of a repo
  that already uses Coga") is where that boundary is written down.
- **`_AGENT_LABELS` has a second reader.** `_do_init`'s next-steps strings
  spell `_AGENT_LABELS[name]` twice, which raises on an agent added without a
  label. The registry should make that lookup total rather than leaving a
  second place to edit.
- **The more-than-one-installed case is the one that returns early.**
  `_offer_agent_cli` does nothing there today, so a scan printed from inside
  it would be skipped for exactly the user who has both.
- **Scan before anything is written.** Init is atomic: `_do_init` removes a
  half-built `coga/` on any exception. Printing before `target.mkdir()` keeps
  the scan out of that rollback.

### Why the scan reads `PATH` and not `coga.toml`

Nico's rule, from his review of #1176: an agent is declared in `coga.toml`, not
required on `PATH`. #1176 applied it to every failure message, which now name
the `[agents.<name>]` table that declared the agent. #1176 deliberately left
init's `PATH` scan alone and recorded that this ticket owns the question, so
expect it to be asked here.

The answer is that the scan reads `PATH` and that is correct (Zach,
2026-11-09). At scan time there is no `coga.toml` to read: init is the command
that creates one, and the scan prints before `target.mkdir()`. The one init
path where a `coga.toml` already exists is the clone path, and that path prints
no scan.

The two questions are different. The scan answers "what can this machine run",
which is a `PATH` question. `coga.toml` answers "what does this repo use",
which is the question the post-init failure messages answer. Nothing in the
scan asserts that an agent must be on `PATH` to be usable, and the not-found
row names a binary rather than stating a requirement.

Reading the packaged `coga.toml` template's `[agents.*]` tables is the nearest
"read the toml" alternative, and it is declined: the template declares `cli`
and carries no display name, so the labels the scan exists to show would still
come from the registry.

### Build on current main, alongside #1176

**Decided by Zach, 2026-11-09.** Do not wait for #1176. Build this on current
main and open its PR against main, so Nico reviews both PRs at the same time as
two independent diffs. #1176 merges first; this branch then reconciles. Coga's
PR publisher pins the base to `cfg.git_control_branch` (`main`), so a stacked
PR based on #1176's branch is not available and must not be hand-opened.

Write against main as it is, not as #1176 leaves it. What main has today, at
`ce55fcffa`:

- **No `_installed_agent_clis`.** That helper is #1176's. Main's only `PATH`
  scan is the inline comprehension inside `_offer_agent_cli` at
  `init.py:595`.
- **`_offer_agent_cli` still branches three ways** (`init.py:581-622`): more
  than one installed returns early, exactly one is chosen, none reaches a
  free-text "Install which agent CLI?" prompt. #1176 deletes the third branch.
- **`dependencies.py` still holds the agent install surface**: `install_hint`,
  both agent `Dependency` records with their `install` URLs and `packages`,
  `Dependency.login`, and the `npm` entry in `PACKAGE_MANAGERS`.
  `init.py:51-58` imports `install_hint` and `init.py:32` imports
  `agent_cli_setup.offer_agent_cli`.
- **The next-steps block has three agent readers, not two**
  (`init.py:1581-1592`): an "Install an agent CLI" step built from
  `install_hint('claude')` / `install_hint('codex')`, then
  `_AGENT_LABELS[build_agent]` and `_AGENT_LABELS[other]` in the `coga build`
  coax.

**Stay additive.** Removing `install_hint`, `agent_cli_setup.py`, the agent
`Dependency` records, or the install-offer branch is #1176's scope. This ticket
converts `AGENT_CLIS` to records, adds `agent_label`, adds the scan and its
call site, and edits the `coga build` coax. The new `AgentCLI` records sit
beside `Dependency` records that still carry install URLs; that is fine and
temporary. The record itself still carries no URL.

**Two deliberate choices that shrink the merge.**

- Extract main's inline comprehension into a module-level
  `_installed_agent_clis() -> list[str]` and have both `_offer_agent_cli` and
  `print_agent_scan` call it. #1176 performs the same extraction with the same
  name and return type, so the overlap resolves by keeping either copy instead
  of reconciling two different helpers. Do not add a second `PATH` walk, and do
  not return a tuple — starting commit `4c7751674` did, which is the shape to
  discard.
- Leave the "Install an agent CLI" next-steps step and its `install_hint`
  literals alone. #1176 deletes that whole step, so editing it would turn a
  clean deletion into a conflict. Only the `coga build` coax goes through
  `agent_label()`. After #1176 merges, its replacement no-agent line is the
  one that needs the registry, and that is reconciliation work, not this
  ticket's.

### Known reconciliation when #1176 merges

Every file this ticket touches is a file #1176 changes, so expect a conflict in
all five and treat resolving them as scheduled work rather than a surprise.
Resolve in favour of #1176 wherever the two disagree about install offers, and
in favour of this ticket wherever they disagree about labels:

- `src/coga/dependencies.py` — keep this ticket's `AgentCLI` / `AGENT_CLIS`
  records and `agent_label`; take #1176's deletion of `install_hint`, the agent
  `Dependency` records, `Dependency.login`, and the `npm` package manager.
- `src/coga/commands/init.py` — keep one `_installed_agent_clis`; take #1176's
  narrowed `_offer_agent_cli` and its deleted install branch and imports; keep
  `print_agent_scan` and its `_do_init` call site; route #1176's new no-agent
  prerequisite line through `agent_label()` / `AGENT_CLIS` so it stops spelling
  both names as a literal.
- `.../bootstrap/contexts/coga/init/SKILL.md` — take #1176's rewritten agent
  paragraphs, then re-apply this ticket's one fact: the scan is printed.
- `tests/test_init.py` — keep both sets; #1176 deletes the install-picker cases
  and this ticket adds the scan cases, which do not overlap in content.
- `tests/test_dependencies.py` — keep both; #1176 pins the absence of installer
  metadata and this ticket pins `agent_label`.

If #1176 has already merged by the time implement starts, none of this applies:
read main directly and follow `### Proposed shape`, which describes the
post-#1176 shape.

### A gotcha that will cost time otherwise

`commands/init.py` does `from coga.dependencies import AGENT_CLIS`, binding
the name into the init module. A test that patches
`coga.dependencies.AGENT_CLIS` will not change what the scan renders — patch
`coga.commands.init.AGENT_CLIS`. This is the same import-binding trap the
`fake_vendor` fixture already falls into with `packaged_template_root`.

### Testing conventions

Run the suite with `python -m pytest`. `coga-dev/testing` has the fallback
spellings for when the ambient interpreter is not Coga-capable, and
`coga-dev/codebase` is the entry point for Coga's own contribution rules.

### The context to update in the same PR

One topic, one file:
`src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md`,
under "Fresh repo".

There is no twin to mirror and no second copy to keep identical. PR #1190
("Enforce package-owned definitions after the repository cutover", merged
2026-11-08) deleted the live `docs/contexts/coga/` tree — `docs/contexts/` now
holds only `coga-dev` — and replaced twin equality with strict ownership in
`tests/required_package_resources.txt`, which names the packaged path above as
the sole owner of `coga/init`.
`test_packaging.py::test_live_and_packaged_copies_stay_identical` no longer
exists, so any instruction below to edit "both copies" is void.

`coga/install` is gone too, retired by `8a88b5ada`. Its agent policy moved into
`coga/init`, which is why the scan fact now has one home.

The edit is that the scan is *printed*: every supported agent CLI with its
binary and whether that binary was found, in an interactive terminal, before
anything is written. Write it as what init does, not as a rule about what coga
will never do — see *Out of scope* on keeping the install question open. #1176
rewrites this topic's agent paragraphs, so edit it as of that merge rather than
as it reads today.

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


## Re-scope 2026-11-06 (Zach, during peer-review)

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

### What happened to the branch

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

### Findings worth keeping from the cut work

- The scan was run on a **fresh macOS VM** at `ff502c154`. The no-agent case
  rendered as two "not found" rows, which was the case that mattered.
- One defect that run surfaced: the scan collided with the `op` paragraph
  above it and read as another line of that block. It needs a leading blank
  line. Not yet fixed in `4c7751674`.
- `_AGENT_LABELS.get(name, name)` rather than `[name]`, so an unlabelled agent
  renders under its slug instead of raising. The registry should make this
  moot rather than repeating the `.get`.


## Design 2026-11-06

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

## Open Questions

None. The one the design raised — flat rows versus Spec Kit's box-drawing
tree — was put to Zach in-session on 2026-11-06 and answered: copy the tree.
The chosen rendering is in `### Proposed shape`.


## Evaluator review

Verdict: not ready for implementation. Two scope contradictions need owner
resolution; the remaining proposed scan shape matches the current code and
PR #1176's head (`3badabee50b3e046ddf9205db0c1ff13c6454855`).

### Must resolve before implementation

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

### Optional recommendations

1. **Repeat the fresh-VM rendering check before handoff.** Zach requested a
   second interactive fresh-repo init run on the fresh VM. Inspect the leading
   separation from the `op` note, heading and blank line, tree branches and
   glyphs, color treatment, binaries, and found/not-found text in the real
   terminal; retain the result as implementation evidence.

### Disposition (Zach, 2026-11-06, review-design)

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

## Parked 2026-11-06 — waiting on #1176

Zach parked this at `review-design` rather than bumping. #1176 has merge
conflicts; the order is: fix #1176, present it to Nico, he merges if he likes
it, then restart this ticket. **Not bumped — `review-design` is still the
current step.** Both evaluator must-fix findings are already resolved in the
ticket text above, so the next session can bump without redoing review.

### #1176's conflicts, verified

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

### What is actually on the branch

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

### When restarting

**Reversed by Zach on 2026-11-09 — build on current main; see the note at the
end of this blackboard.** The two reasons given below are now accepted costs,
not blockers: the helper is extracted here instead of reused, and the
`AgentCLI` records do land beside `Dependency` records #1176 deletes.

~~Base implement on #1176's head, or on main once #1176 merges. Do not
implement against current main: `_installed_agent_clis` does not exist there,
and the `AgentCLI` records would land beside the `Dependency` records #1176
deletes.~~ The fresh-VM render check wants the redesigned scan, so it comes
after implement, not before.

### A referenced sibling went away

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

## Re-check 2026-11-06 (still parked, still waiting on #1176)

### #1176's conflicts are gone

Its head moved to `b9057a89b` (two commits, 22 files, +252/−598) and
`git merge-tree origin/main refs/remotes/pr/1176` now returns a tree with no
conflicted paths, against main at `0309c437a`. The four files recorded as
conflicting above — both copies of `coga/init`, `coga-dev/internals/agent-spawn`,
and `tests/test_init.py` — all merge clean. GitHub still reports
`mergeable: UNKNOWN`, so keep checking locally. The PR is **open**, in front of
Nico; nothing to do here until he merges it.

### The design spec was re-verified against `b9057a89b`

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

### Main's twin-parity test was red — fixed on main 2026-11-07, ignore this

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


## 2026-11-07 — #1176 was closed, and this ticket's sequencing is now void

**Partly superseded by the 2026-11-09 note below: #1176 was reopened, so the
sequencing has a target again. The `coga/install` finding here still stands and
is now fixed in the ticket body.** Kept so the closure is not rediscovered.

Still parked at `review-design`, not bumped. Main moved 79 commits overnight
(`0309c437a` → `3942e54b7`). Three things changed that this ticket depends on.

### #1176 is closed, not merged

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

### `coga/install` was retired — this ticket's context list is stale

`8a88b5ada` ("Retire the coga/install topic", ticket
`v1/26-make-the-readme-install-section-the-only-install-p`) deleted both copies
of `docs/contexts/coga/install/SKILL.md`. The README "Get started" section is
now the only install path, and init's external-CLI install-offer facts moved
into `coga/init`.

Two consequences, both left unfixed in the ticket body above because it is
parked:

- The acceptance criterion "`coga/init` and `coga/install` describe the scan" names a topic that no longer exists. The scan fact now has one home, `coga/init`, plus possibly the README.
- `### Contexts to update in the same PR` lists `coga/install`'s "Prerequisites" bullet and quotes its "Coga provides no agent installer command or URL" sentence. Both are gone from the repo. `coga/init` is where to look for whatever survived.

### The twin-parity test is green again

See the corrected note above. Nothing to work around, no ticket to file.


## 2026-11-09 — spec brought current, and the wait on #1176 dropped

Attended session at `review-design`. No code written. The design itself did not
change: the scope is still the scan plus the registry behind it, as cut on
2026-11-06. Four stale facts in the ticket body were fixed, and the one open
design question was answered. Main is at `ce55fcffa`.

### #1176 was reopened, so the sequencing has a target again

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

### The `PATH`-versus-toml question is answered (Zach, 2026-11-09)

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

### The docs tree was cut over — this is the big one

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

### What was edited in the body

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

### Branch state, unchanged

The local branch still points at `4c7751674`, the 34-line pre-design sketch.
`origin/<branch>` still holds all seven pre-re-scope commits (+1730/−493 across
21 files) and was deliberately never force-pushed. Neither is the deliverable;
implement starts from `### Proposed shape`. The archive tag
`archive/v1-20-pre-rescope` is still present locally.

### The wait on #1176 was dropped — build alongside it (Zach, 2026-11-09)

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

### Spec rewritten for build-on-main

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

### Ready to bump

Both evaluator must-fix findings were resolved on 2026-11-06, the open question
was answered the same day, and the spec is current against main at `ce55fcffa`
and #1176 at `ec8ad1bfa`. `review-design` needs no further pass — bump to
`implement` whenever Zach is ready, with no dependency left to wait on.


## Implement 2026-11-09 (claude, attended)

Built on current main after #1176 merged, so none of the build-alongside
reconciliation applied. One commit, five files, no deviation from
`### Proposed shape` or the chosen rendering.

**Who ran this:** Claude Opus 5 (1M context), attended session with Zach. The
ticket's configured `agent: claude` is not execution evidence; this line is.

### #1176 merged first, exactly as sequenced

It merged at `3acea3523` and its ticket is `done` on main. That voids
`### Known reconciliation when #1176 merges` and `### Build on current main,
alongside #1176` entirely — the blackboard's own escape clause ("If #1176 has
already merged by the time implement starts, none of this applies") is what
applied. Main already had `_installed_agent_clis` as a `list[str]`, a narrowed
`_offer_agent_cli` with the install branch gone, no `install_hint`, no
`agent_cli_setup.py`, and the "Install an agent CLI" next-steps step replaced
by a no-agent prerequisite line. The certain five-file conflict never happened.

### What changed

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

### Rendering, as executed

    Checking for agent CLIs...

    Agent CLIs coga can drive
    ├── ● Claude Code (claude) — found
    └── ○ Codex (codex) — not found

Matches the tree Zach chose on 2026-11-06. The leading blank line is present
and asserted (`out.startswith("\n")`), which is the fresh-VM `op`-note
collision fixed.

### Two things done beyond the literal shape, both deliberate

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

### Verification: bounded, not a completed full suite

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

### A pre-existing test failure, not mine

`tests/test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`
fails with four extra `coga/recurring/_custom-phone-home/ticket.py`-style
paths. Verified pre-existing: it reproduces identically in a detached worktree
of pristine main at `991037866` with none of this branch's edits, in 18.7s. It
concerns legacy recurring-job adoption and touches nothing this ticket
changed. Unowned and unfiled.

### Two checks still owed, neither done here

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

### Branch history: origin was force-pushed

The blackboard recorded that `origin/<branch>` deliberately still held the
seven pre-re-scope commits. That is no longer true — this step force-pushed, so
origin now holds the single implement commit. Both recovery points were checked
after the push and survive locally: tag `archive/v1-20-pre-rescope`
(`0156b008e`) holds the full abandoned work, and the pre-reset origin tip
`477a6b175` still resolves.

### For peer-review

The diff is small and self-contained. The two judgement calls worth attention
are the two "beyond the literal shape" items. The acceptance criterion that a
third agent is one record is enforced by
`test_agent_scan_renders_an_agent_added_to_the_registry`, which patches
`coga.commands.init.AGENT_CLIS` — patching `coga.dependencies.AGENT_CLIS` does
not work, because `init` binds the name at import.


## PR

```yaml
title: Print a supported-agent-CLI scan during coga init
author: claude
author_evidence: >-
  Implement session 2026-11-09 ran Claude Opus 5 (1M context), attended by
  Zach; see the implement handoff above.
head: b64415d107928882fbe3065daac14209a829c96d
base: 5d8ff2f136e0e2c96536e0b7c07b7e7919fedbc7
depth: careful
rationale: >-
  Small diff, but it converts a public manifest constant from strings to
  records and deletes a label map, so every reader has to be confirmed
  converted. Reviewers should also judge the two deliberate extras: routing
  #1176's no-agent next-steps line through the registry, and repairing a
  #1176 test that records would have made vacuously true.
implementation: >-
  Interactive `coga init` now prints a Spec Kit-style tree of every agent CLI
  Coga can drive, with each one's display name, binary, and whether that
  binary is on PATH. Behind it, `AGENT_CLIS` becomes `AgentCLI` records and
  `init._AGENT_LABELS` is replaced by `dependencies.agent_label`, so the scan
  and init's next-steps labels read one registry instead of two.
deviations: >-
  Two additions beyond the literal proposed shape, both assigned to this
  session by the ticket's reconciliation notes: #1176's no-agent next-steps
  line now reads the registry instead of spelling both agent names as a
  literal (rendered output is byte-identical at two agents), and
  `test_agent_clis_have_no_install_metadata` now compares record names
  because `isdisjoint` against records is trivially true and would have
  stopped guarding.
limitations: >-
  No full `python -m pytest` run completed; see the handoff for why and for
  the blast-radius argument that bounds it. No fresh-VM render check, so the
  glyphs and colour are unverified on a clean terminal and the not-found rows
  were produced by faking `shutil.which`. No native Windows run, though the
  scan prints new non-ASCII and tier 2 may require one before merge. The
  pre-existing `test_edge_distribution` legacy-adoption failure is unrelated
  and unfixed.
files:
  src/coga/dependencies.py: >-
    Adds the `AgentCLI` record and `agent_label`, and converts `AGENT_CLIS`
    from binary-name strings to records — the single registry the scan and
    the next-steps labels both read.
  src/coga/commands/init.py: >-
    Adds the public argument-free `print_agent_scan` and its interactive-only
    `_do_init` call site, deletes `_AGENT_LABELS`, and routes the next-steps
    agent names through the registry.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: >-
    Records that interactive fresh init prints the scan and that the clone
    path does not; sole owner of the `coga/init` topic after PR #1190.
  tests/test_init.py: >-
    Covers the scan's rendering in every state, a registry-added agent, a
    label-less record, an empty registry, and the three init paths
    (interactive, non-interactive, clone).
  tests/test_dependencies.py: >-
    Pins `agent_label` for known and unknown types and `AgentCLI.display`'s
    slug fallback, and repairs the install-metadata guard for records.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: >-
    No code review has run. `peer-review` is the next workflow step and will
    refresh this record. The 2026-11-06 design evaluation is not code review.
checks:
  - command: python -m pytest tests/test_init.py tests/test_dependencies.py tests/test_packaging.py
    status: passed
    head: b64415d107928882fbe3065daac14209a829c96d
    base: 5d8ff2f136e0e2c96536e0b7c07b7e7919fedbc7
    detail: >-
      207 passed in 50.39s, re-run at the post-rebase head. Covers both
      changed modules and packaged-resource ownership.
  - command: python -m pytest tests/test_launch.py tests/test_megalaunch.py
    status: passed
    head: 3113e4f04bea15e33c304345fe9cfe1a69fa3a42
    base: b74ec5542ea2145caf2924ace71754ee1ce45ede
    detail: >-
      421 passed in 506.16s. Both import `coga.dependencies`. Run at the
      pre-rebase head; `git diff 3113e4f04 b64415d10 -- src tests` is empty,
      so the tested source and tests are byte-identical to the current head.
      The rebase pulled in only `coga/log.md` and an unrelated ticket file.
  - command: python -m pytest tests/test_ticket.py tests/test_recurring_autofix.py
    status: passed
    head: 3113e4f04bea15e33c304345fe9cfe1a69fa3a42
    base: b74ec5542ea2145caf2924ace71754ee1ce45ede
    detail: >-
      134 passed in 56.43s. Both import `coga.dependencies`. Pre-rebase head;
      see the identical-source note above.
  - command: python -m pytest tests/test_cli.py tests/test_uninstall.py tests/test_edge_distribution.py
    status: failed
    head: 3113e4f04bea15e33c304345fe9cfe1a69fa3a42
    base: b74ec5542ea2145caf2924ace71754ee1ce45ede
    detail: >-
      92 passed, 1 skipped, 1 failed. The failure is
      test_edge_distribution::test_documented_legacy_adoption_preserves_state_and_reconciles_callers,
      verified pre-existing by reproducing it in a detached worktree of
      pristine main at 991037866 with none of this branch's edits.
      `cli.py` and `uninstall.py` are the two importers of `commands.init`.
      Pre-rebase head; see the identical-source note above.
  - command: python -m pytest
    status: not-run
    detail: >-
      Did not complete. One run was killed by me after main moved mid-run
      (PR #1189) made the tree stale; a second was killed externally at 34%,
      showing one unidentified failure near 30% and nothing else; a 15-file
      chunk exceeded the 9m40s tool ceiling. A full run here takes about an
      hour. Zach chose on 2026-11-09 to bump on the bounded evidence above
      and leave the full run to peer-review/open-pr.
  - command: coga validate --json
    status: not-run
    detail: >-
      Validation behaviour is unchanged; the diff touches init's console
      output and a label registry only.
```


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
