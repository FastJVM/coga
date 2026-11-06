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
step: 3 (review-design)
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
other half of this ticket is making a third cheap: one record in one place,
with no edit to the scan. Users commonly arrive with an off-mainstream agent,
so the registry is the part of this with a future.

Init offers no install and asks no question. An agent that is not on `PATH` is
named with its binary so the user can install it or put it on `PATH`.

### Acceptance criteria

- [ ] Interactive `coga init` on a fresh repo prints a scan of the supported
      agent CLIs: a heading, then one row per agent with its display name, its
      binary, and whether that binary was found on `PATH`.
- [ ] Every supported agent appears in every state, including when none was
      found. A machine with nothing installed reads a complete list, not an
      absence.
- [ ] Nothing in the scan is hardcoded. Rows are built from the supported-agent
      registry, so an agent added there renders with no edit to the scan.
- [ ] Adding an agent is one record in one module. Today the list is split
      between `dependencies.AGENT_CLIS` and `init._AGENT_LABELS`, which sit in
      different layers.
- [ ] A test adds an agent to the registry and asserts it renders, so the
      claim above is enforced rather than asserted.
- [ ] A registry entry with no display name renders under its slug instead of
      raising, in the scan and in every other reader of the labels.
- [ ] The scan is a standalone function taking no init state, so a later
      `coga check` can call it without a refactor.
- [ ] The scan prints on every interactive fresh-repo init, including when
      more than one agent CLI is installed.
- [ ] Init asks no question about agents and writes no `[agents.*]` or
      `default_agent` change.
- [ ] Non-interactive init prints no scan, and the clone path prints no scan.
- [ ] The scan is separated from whatever init printed above it by a blank
      line, so it does not read as another line of the `op` note.
- [ ] `_do_init`'s next-steps strings name agents through the registry, not
      through literals, so the third agent needs no edit there either.
- [ ] `coga/init` and `coga/install` describe the scan, each context's bundled
      twin matches, and `python -m pytest` passes.

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

The record carries no install URL and no `packages`. Sibling #1176 removed
every agent-installer URL from `dependencies.py` and wrote "Coga provides no
agent installer command or URL" into `coga/install`; a URL on the record would
put one back.

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

**The other label readers.** `_do_init`'s next-steps strings go through
`agent_label()`: the `coga build` coax (`_AGENT_LABELS[build_agent]`,
`_AGENT_LABELS[other]`) and, post-#1176, the no-agent-found prerequisite line
that spells "Claude Code (`claude`) or Codex (`codex`)" as a literal — build
its list from `AGENT_CLIS`. `build_agent = AGENT_CLIS[0]` becomes
`AGENT_CLIS[0].name`, and `next(a for a in AGENT_CLIS if a.name != build_agent)`
keeps its current "pick any other" behaviour; redesigning that coax for three
agents is not this ticket.

**Order of work.** Registry first (`dependencies.py` + `agent_label`), then
the `init.py` readers it breaks, then `print_agent_scan` and its call site,
then the two contexts and their bundled twins, then tests.

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
- **Offering to install an agent CLI.** Out now, not ruled out forever (Nico,
  2026-11-04). Sibling `v1/remove-the-agent-cli-install-offer-from-coga-init`
  (PR #1176) removes the existing offer. Do not reintroduce one, and do not
  write a rule anywhere saying coga never will.
- **A standalone `coga check`.** Spec Kit's scan is its own command; coga's is
  init-only for now. The acceptance criteria keep the function callable from
  one later, which is all this ticket owes it.
- **Adding a third agent.** Gemini belongs to sibling
  `marketing/fix-installer/add-gemini-as-an-agent-coga-can-drive`. This ticket
  makes room for it and adds nothing.
- **Unpinning the packaged stateless targets.** `bootstrap/ticket` and
  `bootstrap/orient` keep `agent: claude`. Only the cut selection made
  unpinning necessary.
- **Extracting megalaunch's picker.** There is no picker, so there is nothing
  to extract and `coga.megalaunch` is untouched.
- **Install URLs or packages on the registry record.** #1176 removed every
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
  agents and raises at three or more, which goes live when the Gemini sibling
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
- `coga/install` describes the same set for humans. `dependencies.py`'s
  docstring says keeping the list in one place is what stops the check and the
  docs drifting; the split between `AGENT_CLIS` and `_AGENT_LABELS` is that
  claim already half-broken.

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

### Sequencing against #1176

Read as of 2026-11-06 against the open PR, not from the earlier description of
it. Three corrections:

- **#1176 does not delete `_offer_agent_cli`.** It narrows it to the
  exactly-one case: `installed = _installed_agent_clis()` then
  `if len(installed) != 1: return None`. Both the no-agent prompt and the
  `>1` early return are gone, so *every* count other than one returns before
  anything prints. That is still the reason to print from `_do_init` rather
  than from inside it.
- **#1176 adds `init._installed_agent_clis()`**, "the `AGENT_CLIS` on PATH, in
  stable supported order". Reuse it; do not add a second `PATH` walk. Starting
  commit `4c7751674` added its own tuple-returning copy of the same helper —
  resolve that conflict in favour of #1176's.
- **#1176 deletes `dependencies.install_hint` and the `claude` / `codex`
  `Dependency` entries**, along with `Dependency.login` and the `npm` entry in
  `PACKAGE_MANAGERS`. After it, `AGENT_CLIS` is the only trace of an agent in
  `dependencies.py` and nothing anywhere holds an agent install URL. The
  registry is therefore built fresh, not grown from the deleted records.

**Base this branch on main after #1176 merges.** Landing first would leave the
new `AgentCLI` records sitting beside the `Dependency` records #1176 deletes,
and #1176's merge would have to be hand-resolved to keep them. If #1176 is
still open at implement time, say so and ask rather than guessing the order.

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

### Contexts to update in the same PR

- `coga/init` (`docs/contexts/coga/init/SKILL.md`), "Fresh repo" — add that
  init prints the scan.
- `coga/install` (`docs/contexts/coga/install/SKILL.md`), "Prerequisites" —
  add that init scans for the supported agent CLIs and shows what it found.

Each has a bundled twin under
`src/coga/resources/templates/coga/bootstrap/contexts/`. #1176 edits both
copies of both topics; read them as of the merge, not as described here.
`test_packaging.py::test_live_and_packaged_copies_stay_identical` enforces
byte-identical twins, so apply each edit to both copies verbatim.

Post-#1176, `coga/init`'s "Fresh repo" already says "Init only scans `PATH`
for them" — the edit is that the scan is *printed*: every supported agent CLI
with its binary and whether that binary was found, in an interactive terminal,
before anything is written. `coga/install`'s "Prerequisites" bullet for the
agent CLI gains the same fact in one clause.

Write both updates as what init does, not as a rule about what coga will never
do — see *Out of scope* on keeping the install question open.

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

The post-#1176 helper and control-flow claims were verified: that PR is still
open, it defines `_installed_agent_clis`, the proposed fresh-init call site is
before `target.mkdir`, and `_setup_initialized_clone` is a separate path. The
ticket's explicit wait-for-#1176 sequencing handles the open PR.


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
