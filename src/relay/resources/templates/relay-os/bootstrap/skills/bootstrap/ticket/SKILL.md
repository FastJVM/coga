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
your filled ticket has to match. For a real example, browse the same tree:

- `relay-os/tasks/<slug>/ticket.md` — any existing code-change ticket with
  `contexts:` + `workflow:` filled in works as a model to mimic.

A ticket carries a workflow — the ordered steps the work moves through —
everywhere except while it is a `draft`. A ticket with no workflow can't be
activated: `relay mark active` refuses it, and `relay validate` errors on a
workflow-less `active`/`in_progress`/`paused` ticket. Picking the workflow is
part of this interview (step 3), and your default is to hand back a ticket
with one. The one exception is deliberate **concept-capture**: when the human
wants to stash an idea before its shape is settled, a workflow-less *draft* is
a valid end state — it simply stays a draft until someone adds a workflow.
Don't force a workflow onto an idea that isn't ready for one; just make the
tradeoff explicit (it can't be activated yet).

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
- **Existing-ticket edit** — `relay ticket <slug>` launched you against an
  existing task at any status (`draft`, `active`, `in_progress`, `paused`, or
  `done`). Editing leaves the status unchanged. Preserve existing useful body
  text and frontmatter; ask only for the missing or ambiguous pieces. For an
  `in_progress` or `done` ticket, be aware you are revising one already in
  flight or finished — confirm intent if the change looks substantive.
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
- `relay.toml` `[agents.*]` — known agent types (e.g. `claude`, `codex`).

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

The exception is `bootstrap/orient`, which is the orientation shim itself; it
intentionally attaches broad relay contexts so an ad-hoc oriented session has
the operator reference loaded.

## Step 3 — Interview the human

Cover these, in this order, in plain conversation. Stop pulling once you
have enough — don't ask every question if the title already implies the
answer.

1. **Description** — what needs to happen and why, in 2–4 sentences. This
   becomes the `## Description` body.
2. **Context** — what's the agent who picks this up later going to wish they
   knew? Codebase pointers, gotchas, related tickets, out-of-scope notes.
   This becomes the `## Context` body.
3. **Autonomy triage** — before settling the workflow, run the three-question
   test from `relay-os/contexts/autonomy/triage/SKILL.md` against the task as
   described so far. Land on exactly one tier and capture a one-line answer per
   question (you surface all three in the step-7 summary):
   - **fully-automated** — all three questions pass and the failure radius is
     low; the task can run unattended.
   - **assist-only** — Q2 fails: feasible, but conventional output isn't good
     enough, so a human owns the result.
   - **human-verify** — verifiable or bounded, but medium/high failure radius;
     an agent prepares to the brink and a human commits.
   - **human-only** — Q1 fails outright, or the task is unverifiable with high
     failure radius; the human performs it, the agent supports read-only.
   The tier is **advisory input to the workflow choice below** — it is never
   stored in a ticket field or body section (it's read off the chosen
   workflow/assignees). Advisory tier→workflow mapping:
   - `human-only` → `autonomy/human-only`
   - `assist-only` → `autonomy/assist-only`
   - `human-verify` → any workflow with an owner gate before the irreversible
     step (`autonomy/human-verify`, or a `code/*` workflow with an owner
     review step already qualifies)
   - `fully-automated` → an all-agent workflow (`autonomy/fully-automated`, or
     an all-agent `code/*`); you may *suggest* an unattended `mode` (`script`,
     or `auto` = `script` + `claude -p`), but do not set `mode` semantics or
     encode a tier↔mode mapping here — that's a separate ticket.
4. **Workflow** — which workflow fits? `ls relay-os/workflows/` for the
   options (e.g. `code/with-review` for a code change shipped via PR). Let the
   triage tier above advise this choice, but never override a workflow the
   human explicitly picks. Every ticket needs one before activation — a
   workflow-less ticket can't be activated and `relay validate` errors on a
   workflow-less active ticket — so pick the lightest workflow that matches
   the shape of the work. If genuinely nothing fits (e.g. pure
   concept-capture with no sequence of steps), tell the human: either the repo
   needs a new workflow, or the idea stays a deliberate workflow-less *draft*
   (valid, but un-activatable until a workflow is added) until it is ready to
   be a real ticket.
5. **Contexts to attach** — which exact context bodies must be included in the
   future prompt? Keep the list narrow. If only a specific fact is needed, put
   it in `## Context` instead of attaching the whole context.
6. **Assignee** — default to whatever the shim seeded (usually the human's
   primary agent). Confirm if the work clearly fits a different agent or
   needs to go to a human.
7. **Extension fields** — if `relay.toml` declares any `[ticket.fields.<name>]`
   entries, the scaffold seeded each one with its default (or `""`) below
   the `# --- extensions ---` marker. For every declared field that is empty
   on the draft, ask the human for a value — particularly anything marked
   `required = true`, since `relay mark active` refuses to activate a ticket
   with required-but-empty extension values. Fields with declared `values:`
   (enums) must be set to one of the listed values. Write the chosen value
   into the frontmatter below the marker, preserving declaration order.

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

**Before hand-writing a skill, check whether one can be imported.** When the
gap is a *skill* (process knowledge), follow `bootstrap/import` first: search
the external registries for a candidate and decide import / adapt / write. Only
write a local skill from scratch when nothing external fits. Contexts (domain
knowledge) are repo-specific — write those locally as below.

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

- Set `workflow:` to the workflow name you picked (e.g. `code/with-review`).
  This is required — a ticket with no workflow can't be activated. Write it
  as a bare string; the first `relay bump` freezes the snapshot.
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

## Step 7 — Show the summary and ask the human to validate

Before exiting, print a compact summary the human can sanity-check at a
glance. The point is to surface the choices that are easy to get wrong and
hard to spot once the ticket has launched — workflow shape, the skills each
step will run, and the autonomy tier you landed on (so the human validates the
classification before launch).

Read `relay-os/workflows/<name>.md` for the workflow you picked and pull
its step list (each step's `name:` and `skills:`). Then print:

```
<slug> — <title>

Workflow: <name>
  1. <step-name>  →  <skill-ref>, <skill-ref>
  2. <step-name>  →  <skill-ref>
  3. <step-name>  →  (human)

Contexts: <ref>, <ref>          # or "none"
Skills (ticket-level): <ref>    # omit line if empty
Assignee: <agent-or-human>

Autonomy tier: <tier>  (advisory — expressed via the workflow/assignees above)
  Q1 documented:           <one line>
  Q2 conventional enough:  <one line>
  Q3 verifiable/bounded:   <one line>

Summary
  <2–3 sentences in your own words: what this ticket is, what done looks
  like, anything you flagged as a gap or assumption.>

Evaluator review: see blackboard.md ## Evaluator review
```

Then ask the human directly: "Does this look right, or anything to change
before you launch?" Wait for their reply. If they redirect — swap the
workflow, drop a context, reword the description, fix an extension field —
make the edit and reprint the relevant part of the summary. Only move on
once they explicitly confirm.

After confirmation, print one closing line. For a draft:

```
Filled <slug>. Run `relay mark active <slug>` and `relay launch <slug>`
when ready.
```

For an already-active ticket:

```
Updated <slug>. Run `relay launch <slug>` when ready to start work.
```

Optionally `relay slack --task <slug> --message "<short>"` if the ticket
warrants a heads-up to the channel (a new context was created, an assignee
changed, etc.). Skip the Slack post for routine fill-ins.

Then exit.
