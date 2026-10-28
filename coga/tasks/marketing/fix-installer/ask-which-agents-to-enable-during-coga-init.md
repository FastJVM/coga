---
title: Ask which agents to enable during coga init
status: draft
owner: zach
workflow: code/design-then-implement
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

Done when: interactive `coga init` on a fresh repo shows every supported agent
with its PATH status, asks which to enable, leaves only the chosen agents
declared in `coga.toml`, offers to install a chosen agent that is missing,
warns when a single-agent selection rules out peer review, keeps the delivered
tickets launchable, and still works on Windows. Non-interactive init and the
clone path keep today's behaviour.

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
- **Init's own next steps contradict the new question.**
  `init._print_next_steps` tells the user to edit `coga.toml` to "set your
  agents", names both Claude Code and Codex as what coga drives, and on an
  empty repo advertises `coga build --agent <other>` for whichever agent is
  not the default — which may no longer be declared, so the command would
  fail. Fix all three strings here. Sibling ticket
  `init-sends-the-user-to-edit-a-toml-nothing-can-ope` already assumes this
  ticket removes the agents half of that edit.

### Open design questions for the design step

- **Delete the unchosen `[agents.*]` table, or comment it out?** The Done-when
  says "leaves only the chosen agents declared", which either satisfies.
  Deleting is cleaner but throws away the only in-repo documentation of
  `name_flag`, `session_id_flag`, `discussion`, `analyze`, and `peer` — and,
  for Codex, the long comment explaining why `launch_args = "--no-daemon"` is
  required. Commenting the table out keeps that template for anyone adding the
  agent back by hand. Decide and record which.
- **How the edit is made.** Removing or commenting a TOML table while
  preserving the surrounding comment blocks is harder than
  `_write_default_agent`'s single-line rewrite. Extend that function's
  pattern — line-level edit plus a `tomllib` parse-back equality check that
  abandons the write on any mismatch — rather than adding a round-tripping
  TOML dependency.
- **How an interactive multi-select gets tested.** `tests/test_init.py`,
  `tests/test_agent_cli_setup.py`, and `tests/test_megalaunch.py` (which
  already exercises `_decode_key` and `_pick_selection`) are the files to
  extend. This is the part a reviewer cannot eyeball, so say how it is covered.
  Run them with `python -m pytest`; `coga-dev/testing` has the fallback
  spellings for when the ambient interpreter is not Coga-capable, and
  `coga-dev/codebase` is the entry point for Coga's own contribution rules.
  Both are cited rather than attached — they are broad, and the implement step
  can open them on demand.

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

### Contexts to update in the same PR

- `coga/init` (`docs/contexts/coga/init/SKILL.md`), "Fresh repo" — states that
  init asks which agent CLI to install only when neither is on PATH, and that
  it writes `default_agent` while leaving the `[agents.*]` tables alone.
- `coga/install` (`docs/contexts/coga/install/SKILL.md`), "Prerequisites" —
  states the same no-agent-on-PATH condition and lists the installer routes.

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

The blackboard is a notepad to be written to often as the human and agent works through a task.
