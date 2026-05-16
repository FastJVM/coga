---
name: bootstrap/ticket
description: Interview the human, fill in a freshly-scaffolded draft ticket (workflow, contexts, assignee, body), create any missing contexts or skills the ticket needs, and run an independent evaluator review before handing back to the human for approval.
---

# Bootstrap a ticket

Your job is to turn a one-line title into a complete `draft` ticket the human
can review and launch. You do **not** start the work itself — you set it up.

The human is at the keyboard (`mode: interactive`). Ask, don't guess. Keep
the interview short — 4–6 questions, not a survey.

## Ticket format — read this first

The canonical ticket shape is `relay-os/tasks/_template/ticket.md`. **Read it
once before you start** — that's the frontmatter fields and body sections
your filled ticket has to match. Two real examples in the same tree to mimic:

- `relay-os/tasks/fix-relay-status-narrow-terminal-table-wrapping/ticket.md`
  — a code-change ticket with `contexts:` + `workflow:` filled in.
- `relay-os/tasks/autotrigger-ticket-type/ticket.md` — a concept-capture
  ticket with no workflow, just description + context body.

Match this shape exactly. Don't invent fields the template doesn't define
(see "YAML discipline" in the base prompt).

## Step 1 — Detect launch shape

Four ways this skill runs:

- **Empty interview** — `relay ticket` or `relay launch bootstrap/ticket`
  with no target. You're inside the stateless shim. Ask the human for a
  one-line title, run `relay draft "<title>"`, then edit the new draft
  directly in this same session.
- **New-title launch** — `relay ticket "<title>"` already scaffolded a draft
  and launched you against it. The current task has a `title:`, `status:
  draft`, and usually an empty `## Description` / `## Context` body.
- **Existing draft/active edit** — `relay ticket <slug>` launched you against
  an existing `draft`, `active`, or `paused` task. Preserve existing useful
  body text and frontmatter; ask only for the missing or ambiguous pieces.
- **Raw draft** — `relay draft "<title>"` only creates bytes on disk and does
  not run this skill. If the human expected the interview, tell them to run
  `relay ticket <slug>`.

## Step 2 — Survey what's available

Before suggesting anything, ground yourself in what actually exists:

- `ls relay-os/workflows/` (and one level deeper) — known workflows.
- `ls relay-os/contexts/*/` — known contexts (path shape:
  `relay-os/contexts/<namespace>/<name>/SKILL.md`; reference shape in
  tickets: `<namespace>/<name>`).
- `ls relay-os/skills/*/` — known skills (same path/reference shape).
- `relay.toml` `[assignees.*]` — known humans and their agent nicknames.

Don't propose a workflow, context, skill, or assignee that isn't in this
list — create it (step 4) or pick from the list.

## Context and skill selection contract

Treat `contexts:` as prompt payload, not labels. Every context attached to the
ticket is inlined into the future launch prompt, so broad context choices are a
token and precision cost.

Rules:

- Attach only context refs whose full body the future launched agent needs to
  do this task correctly.
- Do not attach broad orientation contexts by default. Use contexts like
  `relay/architecture`, `relay/principles`, `relay/current-direction`, or
  `relay/project-stage` only when the task directly depends on that knowledge.
- If the task needs one fact from a broad context, copy that specific fact into
  the ticket's `## Context` body instead of attaching the whole context.
- If the same narrow fact recurs across tickets, create or propose a smaller
  focused context rather than repeatedly attaching a broad one.
- Skills are process knowledge. Select them through the workflow's step
  `skill:` refs, not by putting skill text into `contexts:`. If a relevant
  skill exists but no workflow uses it yet, mention the skill ref in the body
  or propose the workflow change.

## Step 3 — Interview the human

Cover these, in this order, in plain conversation. Stop pulling once you
have enough — don't ask every question if the title already implies the
answer.

1. **Description** — what needs to happen and why, in 2–4 sentences. This
   becomes the `## Description` body.
2. **Context** — what's the agent who picks this up later going to wish they
   knew? Codebase pointers, gotchas, related tickets, out-of-scope notes.
   This becomes the `## Context` body.
3. **Workflow** — does an existing workflow fit? (e.g. `code/with-review`
   for a code change shipped via PR.) If the work is concept-capture or
   one-off discussion with no clear sequence, no workflow is fine — leave
   the field off.
4. **Contexts to attach** — which exact context bodies must be included in the
   future prompt? Keep the list narrow. If only a specific fact is needed, put
   it in `## Context` instead of attaching the whole context.
5. **Assignee** — default to whatever the shim seeded (usually the human's
   primary agent). Confirm if the work clearly fits a different agent or
   needs to go to a human.

While interviewing, watch for **gaps** — domain knowledge that recurs across
recent tickets but isn't captured anywhere, or process steps that workflows
keep needing inline. Surface them in step 4.

For existing `active` or `paused` tickets, treat this as refinement of an
approved ticket, not a new ticket. Preserve the current intent unless the
human explicitly changes it. Do not change `status:`, `step:`, or an existing
frozen workflow snapshot.

## Step 4 — Create missing contexts and skills

If the interview reveals a gap that should be a reusable context or skill,
create the file inline rather than leaving it as a TODO. Bias toward small,
focused files — under a page each. Use the `_template/` directories as the
shape:

- New context: `relay-os/contexts/<namespace>/<name>/SKILL.md` with
  frontmatter `name: <namespace>/<name>` and a one-sentence `description:`.
  Body is domain knowledge — facts, edge cases, what's out of scope. No
  process.
- New skill: `relay-os/skills/<namespace>/<name>/SKILL.md` with the same
  frontmatter shape. Body is process knowledge — how to do the thing,
  attached to a workflow step. No domain facts.

Confirm the namespace and name with the human before writing. Once created,
add the new context to the ticket's `contexts:` list (or, for a new skill,
note it in the body so the human can wire it into a workflow on review).

If a gap is too speculative to commit to a file, write it to
`blackboard.md` under a **Proposals** section instead — same shape as the
`bootstrap/dream` skill uses. The human accepts or rejects on review.

## Step 5 — Write the ticket

Edit `ticket.md` in place. YAML discipline (from the base prompt) applies:

- Add `workflow:` if you picked one — use the workflow name (e.g.
  `code/with-review`); `relay bump` will freeze the snapshot when the human
  launches.
- Add `contexts:` as a YAML list (one item per line with `- `).
- Do not add a context just because it is generally related. If in doubt, leave
  it out and write the one needed fact into `## Context`.
- Update `assignee:` only if it changed.
- If the target file actually has `skill: bootstrap/ticket` in frontmatter
  from an older seeded flow, remove it. Modern `relay ticket` injects this
  skill only into the prompt; it should not persist on normal tasks.
- Preserve the current `status:`. You do not activate or start the ticket —
  the human does that with `relay mark active` / `relay launch`.
- Fill the `## Description` and `## Context` body sections from the
  interview.

Do not call `relay bump`. There's no workflow running yet.

## Step 6 — Run the evaluator review

Spawn an independent fresh session to read the filled ticket cold and
critique it. The evaluator should not have seen your interview — it's
checking the ticket as a future agent picking it up would.

For Claude Code: use the `Agent` tool with `subagent_type: general-purpose`.
For Codex or other agents: use whatever sub-session primitive is available
(e.g. `codex exec`).

Hand the evaluator the path to the ticket and ask it to assess:

- Is the description clear enough that an agent with no prior context could
  start work?
- Does the chosen workflow fit the shape of the work? Any obvious mismatch?
- Are the attached contexts relevant? Anything important missing?
- Are any attached contexts broad enough that the needed fact should have been
  copied into `## Context` instead?
- Is the scope reasonable, or does it bundle multiple tickets' worth of
  work?
- Any assumptions that should be questioned before launch?

Write the evaluator's response to `blackboard.md` under a top-level
**## Evaluator review** section, verbatim. Don't summarize — the human reads
it directly.

## Step 7 — Hand back to the human

Print a one-line summary of what you did and what's next. For a draft ticket:

```
Filled <slug>. Evaluator review on blackboard. Review the draft, then run
`relay mark active <slug>` and `relay launch <slug>` when ready.
```

For an already-active ticket, say:

```
Updated <slug>. Evaluator review on blackboard. Run `relay launch <slug>` when
ready to start work.
```

Optionally `relay feed --task <slug> --message "<short>"` if the ticket
warrants a heads-up to the channel (a new context was created, an assignee
changed, etc.). Skip the feed for routine fill-ins.

Then exit. The human reviews `ticket.md` + `blackboard.md`, edits anything
they want to change, and runs `relay launch <slug>` when satisfied.
