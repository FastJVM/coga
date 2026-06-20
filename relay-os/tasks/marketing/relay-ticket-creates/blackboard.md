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
