---
slug: marketing/relay-ticket-creates
title: relay-ticket-creates
status: in_progress
mode: agent
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
step: 2 (review-design)
---

## Description

A `relay ticket` discussion session currently launches **silently** — the
composed Relay prompt rides as a *system* prompt (`--append-system-prompt
{prompt}`) with no initial *user* message, so `claude` starts and waits for the
human to type first. This ticket makes the session **greet-first**: the agent
opens by greeting the human and asking what they want, with the opening line
*tailored to the launch shape* it detects (empty interview / new-title launch /
existing-ticket edit). Two coupled template changes deliver it — a rewrite of
**Step 1** of the `bootstrap/ticket` skill (pairs each launch shape with its
exact opening line) and a `"Begin"` kickoff arg on the `claude` agent's
`discussion` invocation (gives `claude` the first user turn the greeting speaks
into). Ship both or neither — the skill tells the agent to greet first, the
kickoff is what actually triggers it.

This supersedes the ticket's original framing of "one scripted question for
everyone." The intent+why question survives as the *new-title* greeting; the
validated design (prototyped in `relay-ticket-test`) is shape-specific greet-first.

## Context

`relay ticket` already create-or-edits at the command layer
(`_resolve_or_create_target` in `src/relay/commands/ticket.py`): `relay ticket
<new>` scaffolds a draft and launches the interview, `relay ticket <existing>`
re-enters authoring, bare `relay ticket` opens an empty interview. The remaining
work is **SKILL-side** — make that create-or-edit capability legible through the
opener. `relay create` stays as the quick stub; removing the redundant `relay
draft` is split out to `marketing/remove-relay-draft`. 

Mechanism (verified): the `discussion` command template is parsed with
`shlex.split` (`config.py:80-83`, `commands/launch.py:656`), so
`'--append-system-prompt {prompt} "Begin"'` tokenizes to `[--append-system-prompt,
<prompt>, Begin]` and `Begin` lands as `claude`'s first positional (user)
message. Single-quote the TOML value so the inner `"Begin"` stays a literal
double-quoted CLI arg. The `codex` `discussion = "-c developer_instructions=
{prompt}"` mechanism has no positional-prompt equivalent — leave it untouched.

Opener rationale (nick, 2026-06-19): the intent+why phrasing ("What are you
trying to do, and why?") was chosen by testing three openers against a held-constant
task — it pulled the fullest first answer (deliverable + outcomes + quality bars +
the why) where "what do you want done?" missed the why and an outcome frame
dropped the deliverable. It survives as the new-title greeting in the rewritten
Step 1.

Prototyped and validated in the `relay-ticket-test` repo; this ticket ports that
working state into the canonical packaged templates. **Two source copies must
stay in sync** (project CLAUDE.md): the packaged template under
`src/relay/resources/templates/relay-os/` and the live repo copy under
`relay-os/`. The `relay-os/.relay/` install is gitignored — never commit edits
there.

## Acceptance Criteria

- [ ] Step 1 of the `bootstrap/ticket` skill is rewritten to greet-first with a
      shape-specific opening line per launch shape (empty interview / new-title /
      existing-edit), matching the verbatim payload in Proposed Shape.
- [ ] The rewrite lands **byte-identical** in both source copies:
      `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md`
      and `relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md`.
- [ ] Only Step 1 changes — everything from `## Step 1` up to (not including)
      `## Step 2 — Survey what's available` is replaced; Steps 2–7 are untouched.
- [ ] The new Step 1 refers to `relay create` (not the deprecated `relay draft`)
      for the New / empty-interview path.
- [ ] `[agents.claude].discussion` becomes `'--append-system-prompt {prompt} "Begin"'`
      (single-quoted TOML) in all three copies: the packaged template, `relay-os/relay.toml`,
      and `example/relay-os/relay.toml`.
- [ ] `[agents.codex].discussion` is unchanged in every copy.
- [ ] All three `relay.toml` files still parse as valid TOML.
- [ ] Smoke — `relay ticket "<title>"` opens with the new-title greeting (not
      silence); bare `relay ticket` opens with the new/existing branch question;
      `relay ticket <slug>` on a filled ticket opens with the edit greeting.
- [ ] `grep` of the skill tree shows no stray `relay draft` references that should
      be `relay create` (Step 1 was the in-scope one; flag any others, don't fix
      out of scope).
- [ ] `relay-os/.relay/` (gitignored vendored install) is not part of the committed diff.

## Proposed Shape

Two coupled edits, mirrored across the source copies. Order: skill first, then
relay.toml, then smoke-test.

**Edit 1 — `bootstrap/ticket` Step 1 rewrite (both source SKILL.md copies).**
Replace only the `## Step 1 — Detect launch shape` section (header through the
line just before `## Step 2 — Survey what's available`) with the validated text
below. Apply identically to both copies so they stay byte-identical.

> Canonical implementer payload lives on `blackboard.md` under **## Implementer
> payload** — if this block and the blackboard ever disagree, the blackboard wins.

```markdown
## Step 1 — Identify the launch shape and open with the matching greeting

Your relay.toml opening turn has already prompted you to speak first. Your
**first reply** must greet the human in the way that matches how this skill was
launched. Read the prompt header and ticket body to tell which of these you're
in:

- **Empty interview** — the header id-slug is `bootstrap/ticket`, there is **no
`Status:` line**, and the Description is the "Persistent launch shim" text.
You're inside the stateless shim with no target. Open with:
> "You ran `relay ticket` without naming a ticket, so: are you starting a
> **new** ticket, or editing an **existing** one?"
Keep the greeting command-light: refer to it as `relay ticket`, not the
underlying `relay launch bootstrap/ticket` plumbing, and don't name the
`relay create` command when you describe the New path — "I'll scaffold the
draft" carries the point. `relay status` is the exception: it's a genuinely
useful hint, so do offer it by name.
  - New → ask for a one-line title, then scaffold the draft (run `relay create
    "<title>"` under the hood — don't surface the command to the human) and edit
    it directly in this same session.
  - Existing → ask which slug (offer `relay status` to list them), then read and
    edit that ticket's files directly — or tell them `relay ticket <slug>`
    re-launches you straight onto it.

- **New-title launch** — a real `tasks/<slug>` with `Status: draft` and an empty
`## Description` / `## Context` body. `relay ticket "<title>"` already
scaffolded this draft and launched you against it. Open with:
> "Your `<slug>` ticket has been created (draft). What should it do, and why?
> I'll turn your answer into the ticket."

- **Existing-ticket edit** — a real `tasks/<slug>` whose body already has
content, at any status (`draft`, `active`, `in_progress`, `paused`, or
`done`). You're revising an existing ticket; editing leaves its status
unchanged. Open with:
> "You're editing `<slug>` (status: `<status>`). What would you like to change?"

  Preserve existing useful body text and frontmatter; ask only about the parts
  they want to change. For an `in_progress` or `done` ticket, note you are
  revising one already in flight or finished — confirm intent if the change
  looks substantive.

New-title and existing-*draft* tickets both show `Status: draft`; an **empty**
`## Description`/`## Context` body means new, a **filled** body means existing.
If it's genuinely ambiguous, just ask which one they meant.

Note: `relay create "<title>"` (the replacement for the deprecated `relay
draft`) only writes the draft bytes to disk and does **not** run this skill. If
the human expected the interview, point them at `relay ticket <slug>`.
```

**Edit 2 — `claude` discussion kickoff (three relay.toml copies).**
In the `[agents.claude]` block only:

```
- before:  discussion = "--append-system-prompt {prompt}"
+ after:   discussion = '--append-system-prompt {prompt} "Begin"'
```

Apply to: `src/relay/resources/templates/relay-os/relay.toml`,
`relay-os/relay.toml`, and `example/relay-os/relay.toml`. Note the two source
copies already differ in surrounding comments — edit only the `discussion` line,
do not whole-file sync. Leave `[agents.codex]` alone in every copy.

**Then** smoke-test (see Acceptance Criteria) and grep the skill tree for stray
`relay draft` references.

## Out of Scope

- Removing the `relay draft` command — sibling ticket `marketing/remove-relay-draft`.
- A codex `discussion` kickoff — `-c developer_instructions={prompt}` has no
  positional-prompt equivalent; flagged as an open question, not done here.
- Editing `DEFAULT_DISCUSSION_TEMPLATES["claude"]` in `commands/launch.py:66`
  (the built-in fallback) — open question on the blackboard; not decided in this
  ticket unless the owner folds it in.
- Steps 2–7 of the `bootstrap/ticket` skill — untouched.
- The prototype's `.gitignore` change — local scaffolding, nothing to port.
- Committing edits into the gitignored `relay-os/.relay/` install — local
  smoke-test only.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

> **Handoff status (2026-06-19): DESIGN COMPLETE & human-approved (zach).** The
> ticket has all four required `code/design` sections (Description, Acceptance
> Criteria, Proposed Shape, Out of Scope); this blackboard has the implementer
> payload + open questions. The step's work is DONE — it only needs `relay bump
> marketing/relay-ticket-creates` to advance to `review-design`. The bump was
> rejected because the ticket is still `active`: this was a bare session, never
> `relay launch`ed into `in_progress`. **To advance:** a human runs `relay launch
> marketing/relay-ticket-creates` (flips it to `in_progress` and runs the design
> step). If you are the relaunched design agent — do NOT rewrite the approved
> spec; verify the four sections are present, then run `relay bump
> marketing/relay-ticket-creates`.

# Design step — log

Validated design handed over by zach (prototyped + tested in the
`relay-ticket-test` repo). Two coupled template changes make a `relay ticket`
discussion session greet-first instead of launching silently. Spec written to
`ticket.md` (Description / Acceptance Criteria / Proposed Shape / Out of Scope).

Decisions made with zach this session:
- Rewrite lands in **both** source copies of the skill (packaged + live repo) —
  byte-identical (project CLAUDE.md sync rule).
- The `discussion` change also goes into `example/relay-os/relay.toml` (seeded
  fixture stays representative) — zach said yes.
- Verbatim implementer payload kept in **both** the ticket Proposed Shape and
  this blackboard (zach's call). **This blackboard copy is canonical** — if the
  two drift (e.g. owner edits one during review-design), this wins.
- `relay-os/.relay/` is gitignored (vendored install) → never committed; staging
  edits there for a local smoke-test is optional.

Investigation confirmed:
- Both source SKILL.md copies are byte-identical today and their current Step 1
  matches the "replace this" block exactly.
- Both source relay.toml copies carry `discussion = "--append-system-prompt
  {prompt}"` identically (they differ only in surrounding comments).
- `discussion` is tokenized via `shlex.split` (`config.py:80-83`,
  `commands/launch.py:656`) → `"Begin"` lands as claude's first positional/user
  message. Mechanism verified.

## Implementer payload

**CANONICAL.** Apply exactly as written.

### Payload A — new Step 1 of `bootstrap/ticket` SKILL.md

Replace the whole `## Step 1 — Detect launch shape` section (header through the
line just before `## Step 2 — Survey what's available`) with this, in BOTH
source copies, byte-identical:

```markdown
## Step 1 — Identify the launch shape and open with the matching greeting

Your relay.toml opening turn has already prompted you to speak first. Your
**first reply** must greet the human in the way that matches how this skill was
launched. Read the prompt header and ticket body to tell which of these you're
in:

- **Empty interview** — the header id-slug is `bootstrap/ticket`, there is **no
`Status:` line**, and the Description is the "Persistent launch shim" text.
You're inside the stateless shim with no target. Open with:
> "You ran `relay ticket` without naming a ticket, so: are you starting a
> **new** ticket, or editing an **existing** one?"
Keep the greeting command-light: refer to it as `relay ticket`, not the
underlying `relay launch bootstrap/ticket` plumbing, and don't name the
`relay create` command when you describe the New path — "I'll scaffold the
draft" carries the point. `relay status` is the exception: it's a genuinely
useful hint, so do offer it by name.
  - New → ask for a one-line title, then scaffold the draft (run `relay create
    "<title>"` under the hood — don't surface the command to the human) and edit
    it directly in this same session.
  - Existing → ask which slug (offer `relay status` to list them), then read and
    edit that ticket's files directly — or tell them `relay ticket <slug>`
    re-launches you straight onto it.

- **New-title launch** — a real `tasks/<slug>` with `Status: draft` and an empty
`## Description` / `## Context` body. `relay ticket "<title>"` already
scaffolded this draft and launched you against it. Open with:
> "Your `<slug>` ticket has been created (draft). What should it do, and why?
> I'll turn your answer into the ticket."

- **Existing-ticket edit** — a real `tasks/<slug>` whose body already has
content, at any status (`draft`, `active`, `in_progress`, `paused`, or
`done`). You're revising an existing ticket; editing leaves its status
unchanged. Open with:
> "You're editing `<slug>` (status: `<status>`). What would you like to change?"

  Preserve existing useful body text and frontmatter; ask only about the parts
  they want to change. For an `in_progress` or `done` ticket, note you are
  revising one already in flight or finished — confirm intent if the change
  looks substantive.

New-title and existing-*draft* tickets both show `Status: draft`; an **empty**
`## Description`/`## Context` body means new, a **filled** body means existing.
If it's genuinely ambiguous, just ask which one they meant.

Note: `relay create "<title>"` (the replacement for the deprecated `relay
draft`) only writes the draft bytes to disk and does **not** run this skill. If
the human expected the interview, point them at `relay ticket <slug>`.
```

### Payload B — `claude` discussion kickoff

In the `[agents.claude]` block of all three relay.toml copies
(`src/relay/resources/templates/relay-os/relay.toml`, `relay-os/relay.toml`,
`example/relay-os/relay.toml`):

```
- before:  discussion = "--append-system-prompt {prompt}"
+ after:   discussion = '--append-system-prompt {prompt} "Begin"'
```

Edit only the `discussion` line (the two source copies differ in surrounding
comments — do not whole-file sync). Leave `[agents.codex]` alone everywhere.

## Open Questions

1. **Built-in fallback (`commands/launch.py:66`).** `DEFAULT_DISCUSSION_TEMPLATES
   ["claude"]` is still `"--append-system-prompt {prompt}"` (no `"Begin"`).
   `_discussion_template()` (`launch.py:707`) uses the relay.toml value when
   present, else this fallback — so a repo whose `relay.toml` omits a claude
   `discussion` line would still launch silently. Fold `"Begin"` into the
   built-in default too (universal greet-first), or keep this ticket
   template-only? Recommend folding in for consistency; small code change but
   adds test surface. **Owner call.**

2. **Codex kickoff.** `codex`'s `-c developer_instructions={prompt}` has no
   positional-prompt equivalent, so codex discussion sessions stay
   silent-launch. Track as a separate ticket, or accept the asymmetry?

3. **`.relay/` smoke-test.** Optional: the implement step can stage these edits
   into the gitignored `relay-os/.relay/` install to exercise the real `relay
   ticket` flow before/after, without committing them. Worth doing, or rely on
   the e2e `example/` fixture path?

# Implement step — log (2026-06-19)

All three Open Questions above are resolved by the ticket's **Out of Scope**
section — built-in fallback (Q1), codex kickoff (Q2), and `.relay/` commits (Q3)
are all explicitly excluded. Implementing exactly Payload A + Payload B.

## Dev

- branch: `greet-first-ticket`
- worktree: `/Users/zach2179/Desktop/relay-greet-first-ticket`
- pr: https://github.com/FastJVM/relay/pull/417

### open-pr step (2026-06-19)
Pushed `greet-first-ticket` → `origin` and opened PR #417 against `main`
(`gh auth status` clean — `lilfedor`, `repo`+`workflow` scopes). PR title is the
descriptive commit subject ("Make `relay ticket` discussion sessions greet-first")
rather than the bare slug; body carries `Closes ticket: marketing/relay-ticket-creates`,
summary, and test plan. **CI:** `gh pr checks 417` → "no checks reported" — this
repo has no CI workflow on the branch, so there is nothing to go green/red; the
local `python -m pytest` run (822 passed, 1 skipped) is the verification of record.

### Changes applied
- Payload A — replace Step 1 of `bootstrap/ticket` SKILL.md (header through the
  line before `## Step 2`). See premise correction below.
- Payload B — `[agents.claude].discussion` → `'--append-system-prompt {prompt} "Begin"'`
  in all three copies: packaged template, `relay-os/relay.toml`,
  `example/relay-os/relay.toml`. `[agents.codex]` left untouched everywhere.

### ⚠ Premise correction — `relay-os/bootstrap/` is gitignored (BLOCKER on Payload A)

The ticket Acceptance Criteria treat
`relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md` as a committable second
"source copy" that must land byte-identical in the diff. It is **not** committable:

- `relay-os/.gitignore` ignores `bootstrap/` — comment: *"Single relay-vendored
  umbrella. Everything inside is upstream-managed and overwritten on every
  `relay init --update` — your edits will be lost."*
- `git ls-files relay-os/bootstrap/` → 0 tracked files. The path is absent from
  the feature worktree (worktrees only carry tracked files), which is why the
  worktree read failed.
- It's the same class of artifact as `relay-os/.relay/`, which the ticket's last
  AC already excludes from the diff. The design caught `.relay/` but missed that
  `relay-os/bootstrap/` is the same kind of vendored install.

So the **single committable source of truth** for the bootstrap/ticket skill is
the packaged template `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md`.
The `relay-os/bootstrap/...` copy is regenerated from that template by
`relay init --update`; hand-editing it is throwaway (overwritten on update) and
never enters git.

By contrast, Payload B's three `relay.toml` copies are **all tracked**
(`relay-os/relay.toml`, `example/relay-os/relay.toml`, packaged template), so
Payload B is unaffected — apply as written.

**Resolution (zach confirmed 2026-06-19):** commit Payload A to the packaged
template only; the local install refreshes via `relay init --update`. Behavior
and PR-visibility unchanged — the only difference is Payload A lands in one
tracked file instead of two (the second was never git-tracked).

### What actually landed (committed on branch `greet-first-ticket`)

4 tracked files changed:
- `src/relay/resources/templates/relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md`
  — Payload A (Step 1 rewrite). **This is the single committable source copy**;
  `tests/test_bootstrap_ticket_skill_template.py` reads exactly this path,
  confirming it's the suite's source of truth.
- `relay-os/relay.toml`, `example/relay-os/relay.toml`,
  `src/relay/resources/templates/relay-os/relay.toml` — Payload B (`"Begin"`
  kickoff). `[agents.codex]` untouched in all three.
- `tests/test_bootstrap_ticket_skill_template.py` — updated two content-guard
  assertions that pinned the old Step 1 wording (`relay draft "<title>"` line +
  `relay ticket <slug> launched you against`) to the new Step 1 equivalents
  (the `relay create` note + the bare-`relay ticket` new/existing greeting).

### Verification
- `python -m pytest` → **822 passed, 1 skipped** (the 1 pre-existing failure was
  the stale content-guard above; now updated).
- All three `relay.toml` parse as valid TOML (`tomllib`); `claude.discussion`
  carries `"Begin"`, `codex.discussion` unchanged.
- `shlex.split('--append-system-prompt <prompt> "Begin"')` →
  `['--append-system-prompt', '<prompt>', 'Begin']` — `Begin` is the first
  positional (claude's first user turn). Mechanism confirmed.
- `git diff` carries no `.relay/` paths.

### Not done in this step (human/interactive)
- **Live greeting smoke** (AC: `relay ticket "<title>"` / bare `relay ticket` /
  `relay ticket <slug>` open with their greetings). This spawns an interactive
  `claude` session and can't be driven headlessly from inside this agent session
  (base prompt forbids launching another agent session from here). Mechanism is
  verified above; the greeting text itself is zach's validated `relay-ticket-test`
  prototype. Live confirm is a human check — best run by zach, or at review.
- Refreshing this repo's local `relay-os/bootstrap/` install — happens via
  `relay init --update` after merge; out of the committed diff by design.

### Wording follow-up (zach, 2026-06-19)
Per zach's standing preference (boss dislikes "scaffold" in prose), swapped the
three "scaffold"/"scaffolded" uses in the **new Step 1** to "create" — amended
into the same commit (now `6fe191c1`). Two pre-existing "scaffold" mentions
elsewhere in the file (frontmatter description, Step 7 extension-fields line)
left untouched — not part of this change. Test still green.

### Review revision (PR #417, per Nico, 2026-06-20)
Nico's review superseded the Payload A/B approach above. Two comments:
- *relay.toml:26 — "that won't work (you start all prompt not only ticket)"*:
  the `"Begin"` kickoff was folded into the shared `[agents.claude].discussion`
  arg, which `relay chat` / `relay project` also consume — so every discussion
  session greeted, not just `relay ticket`.
- *SKILL.md Step 1 — "Your relay.toml opening turn has already prompted you to
  speak first. what is that?"*: opaque reference to relay.toml internals.

Revised mechanism (commit `3f6a6287`, branch `greet-first-ticket`):
- New per-agent `discussion_kickoff` key (config.py). `claude.discussion` is back
  to `--append-system-prompt {prompt}` (no inline `"Begin"`); the kickoff token
  is appended only on the `relay ticket` path via
  `build_agent_command(..., kickoff=True)` (ticket.py). chat/project stay silent.
- **Resolves Open Question 2** ("Codex kickoff"): `codex [OPTIONS] [PROMPT]`
  *does* take a positional initial prompt, so `discussion_kickoff = "Begin"` is
  set on `[agents.codex]` too — ticket authoring is now greet-first for codex.
- Step 1 reworded to "This session is greet-first: open the conversation
  yourself…" with no relay.toml reference.
- `python -m pytest` → 830 passed, 1 skipped. Live greeting smoke confirmed by
  zach in an isolated sandbox: `relay ticket` greets first for both claude and
  codex; `relay chat --agent codex` stays silent.
