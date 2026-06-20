---
title: relay-ticket-creates
status: in_progress
mode: interactive
owner: zach
human: zach
agent: claude
assignee: claude
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
step: 1 (design)
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
