---
name: bootstrap/ticket
description: Interview the human, fill in a freshly-scaffolded draft ticket (workflow, contexts, assignee, body), create any missing contexts or skills the ticket needs, and run an independent evaluator review before handing back to the human for approval.
---

# Bootstrap a ticket

Your job is to turn a one-line title into a complete `draft` ticket the human
can review and launch. You do **not** start the work itself — you set it up.

The human is at the keyboard in a `mode: agent` launch. Ask, don't guess. Keep
the interview short — 4–6 questions, not a survey.

## Ticket format — read this first

The canonical ticket shape is `coga/tasks/_template/ticket.md`. **Read it
once before you start** — that's the frontmatter fields and body sections
your filled ticket has to match. For a real example, browse the same tree:

- `coga/tasks/<slug>/ticket.md` — any existing code-change ticket with
  `contexts:` + `workflow:` filled in works as a model to mimic.

A ticket carries a workflow — the ordered steps the work moves through —
everywhere except while it is a `draft`. A ticket with no workflow can't be
activated: `coga mark active` refuses it, and `coga validate` errors on a
workflow-less `active`/`in_progress`/`paused` ticket. Picking the workflow is
part of this interview (step 3), and your default is to hand back a ticket
with one. The one exception is deliberate **concept-capture**: when the human
wants to stash an idea before its shape is settled, a workflow-less *draft* is
a valid end state — it simply stays a draft until someone adds a workflow.
Don't force a workflow onto an idea that isn't ready for one; just make the
tradeoff explicit (it can't be activated yet).

Match this shape exactly. Don't invent fields the template doesn't define
(see "YAML discipline" in the base prompt).

## Step 1 — Identify the launch shape and open with the matching greeting

This session is greet-first: open the conversation yourself rather than waiting
for the human to type first. Your **first reply** must greet the human in the
way that matches how this skill was launched.

Your first user turn is a **kickoff token** that `coga ticket` set to tell you
the launch shape — read it, not the ticket body, to pick the greeting:

- `Begin (new ticket)` → **New-title launch**.
- `Begin (editing existing ticket)` → **Existing-ticket edit**.
- bare `Begin` → **Empty interview** (also recognisable structurally: a
  `bootstrap/ticket` header id-slug with no `Status:` line).

The token is authoritative because `coga ticket` already resolved create-vs-edit
before launching you: a freshly-scaffolded draft and a pre-existing draft both
start with an empty body, so body-emptiness can't tell them apart — the token
can. Only if the token is somehow absent, fall back to the header/body cues in
the shapes below:

- **Empty interview** — kickoff bare `Begin`; the header id-slug is
`bootstrap/ticket`, there is **no `Status:` line**, and the Description is the
"Persistent launch target" text. You're inside the stateless bootstrap ticket
with no target. Open with:
> "You ran `coga ticket` without naming a ticket, so: are you starting a
> **new** ticket, or editing an **existing** one?"
Keep the greeting command-light: refer to it as `coga ticket`, not the
underlying `coga launch bootstrap/ticket` plumbing, and don't name the
`coga create` command when you describe the New path — "I'll create the
draft" carries the point. `coga status` is the exception: it's a genuinely
useful hint, so do offer it by name.
  - New → ask for a one-line title, then create the draft (run `coga create
    "<title>"` under the hood — don't surface the command to the human) and edit
    it directly in this same session.
  - Existing → ask which slug (offer `coga status` to list them), then read and
    edit that ticket's files directly — or tell them `coga ticket <slug>`
    re-launches you straight onto it.

- **New-title launch** — kickoff `Begin (new ticket)`; a real `tasks/<slug>`
with `Status: draft`. `coga ticket "<title>"` just scaffolded this draft and
launched you against it. Its body is still empty — that's expected, not a
signal of anything. Open with:
> "Your `<slug>` ticket has been created (draft). What should it do, and why?
> I'll turn your answer into the ticket."

- **Existing-ticket edit** — kickoff `Begin (editing existing ticket)`; a real
`tasks/<slug>` at any status (`draft`, `active`, `in_progress`, `paused`, or
`done`). You're revising a ticket that already exists — **even if its body is
still empty**, which is exactly the state of a draft batch-created with `coga
create` and then opened here. Open with:
> "You're editing `<slug>` (status: `<status>`). What would you like to change?"

  Preserve existing useful body text and frontmatter; ask only about the parts
  they want to change. If the body is empty there's nothing to preserve, so
  greet as an edit but pivot straight to filling it ("…it's empty right now, so:
  what should it do, and why?") — never announce it "has been created". For an
  `in_progress` or `done` ticket, note you are revising one already in flight or
  finished — confirm intent if the change looks substantive.

New-title and existing-*draft* tickets both show `Status: draft` with an empty
body — the kickoff token is what separates them, not the body, so trust it. In
the rare case the token is missing and you genuinely can't tell, just ask which
one they meant.

Note: `coga create "<title>"` (the replacement for the deprecated `coga
draft`) only writes the draft bytes to disk and does **not** run this skill. If
the human expected the interview, point them at `coga ticket <slug>`.

## Step 2 — Survey what's available

Before suggesting anything, ground yourself in what actually exists:

- `ls coga/workflows/ coga/bootstrap/workflows/` (and one level
  deeper) — known workflows. Repo-local workflows live under
  `coga/workflows/`; bundled batteries (e.g. `code/with-review`) under
  `coga/bootstrap/workflows/`. A local file overrides a bundled one
  with the same ref.
- `ls coga/contexts/*/` — known contexts (path shape:
  `coga/contexts/<namespace>/<name>/SKILL.md`; reference shape in
  tickets: `<namespace>/<name>`).
- `ls coga/skills/*/` — known skills (same path/reference shape).
- `coga.toml` `[agents.*]` — known agent types (e.g. `claude`, `codex`).

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
  `coga/architecture`, `coga/principles`, `coga/current-direction`, or
  `coga/project-stage` only when the task directly depends on that knowledge.
- If the task needs one fact from a broad context, copy that specific fact into
  the ticket's `## Context` body instead of attaching the whole context.
- If the same narrow fact recurs across tickets, create or propose a smaller
  focused context rather than repeatedly attaching a broad one.
- Skills are process knowledge. Select them through the workflow's step
  `skill:` refs, not by putting skill text into `contexts:`. If a relevant
  skill exists but no workflow uses it yet, mention the skill ref in the body
  or propose the workflow change.

The exception is `bootstrap/orient`, which is the orientation ticket itself; it
intentionally attaches broad coga contexts so an ad-hoc oriented session has
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
   test from `coga/contexts/autonomy/triage/SKILL.md` against the task as
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
     an all-agent `code/*`). Do not encode a tier↔mode mapping; `mode` remains
     the execution substance (`agent` or `script`), not the autonomy tier.
4. **Workflow** — which workflow fits? `ls coga/workflows/
   coga/bootstrap/workflows/` for the options (e.g. `code/with-review`
   for a code change shipped via PR — a bundled `bootstrap/workflows/`
   battery). Let the
   triage tier above advise this choice, but never override a workflow the
   human explicitly picks. Every ticket needs one before activation — a
   workflow-less ticket can't be activated and `coga validate` errors on a
   workflow-less active ticket — so pick the lightest workflow that matches
   the shape of the work. If genuinely nothing fits (e.g. pure
   concept-capture with no sequence of steps), tell the human: either the repo
   needs a new workflow, or the idea stays a deliberate workflow-less *draft*
   (valid, but un-activatable until a workflow is added) until it is ready to
   be a real ticket.
5. **Contexts to attach** — which exact context bodies must be included in the
   future prompt? Keep the list narrow. If only a specific fact is needed, put
   it in `## Context` instead of attaching the whole context.
6. **Assignee** — default to whatever the bootstrap ticket seeded (usually the human's
   primary agent). Confirm if the work clearly fits a different agent or
   needs to go to a human.
7. **Extension fields** — if `coga.toml` declares any `[ticket.fields.<name>]`
   entries, the scaffold seeded each one with its default (or `""`) below
   the `# --- extensions ---` marker. For every declared field that is empty
   on the draft, ask the human for a value — particularly anything marked
   `required = true`, since `coga mark active` refuses to activate a ticket
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

- New context: `coga/contexts/<namespace>/<name>/SKILL.md` with
  frontmatter `name: <namespace>/<name>` and a one-sentence `description:`.
  Body is domain knowledge — facts, edge cases, what's out of scope. No
  process.
- New skill: `coga/skills/<namespace>/<name>/SKILL.md` with the same
  frontmatter shape. Body is process knowledge — how to do the thing,
  attached to a workflow step. No domain facts.

Confirm the namespace and name with the human before writing. Once created,
add the new context to the ticket's `contexts:` list (or, for a new skill,
note it in the body so the human can wire it into a workflow on review).

If a gap is too speculative to commit to a file, write it to
the ticket's blackboard region under a **Proposals** section instead — same shape as the
`bootstrap/dream` skill uses. The human accepts or rejects on review.

## Step 5 — Write the ticket

Edit `ticket.md` in place. YAML discipline (from the base prompt) applies:

- Set `workflow:` to the workflow name you picked (e.g. `code/with-review`).
  This is required — a ticket with no workflow can't be activated. Write it
  as a bare string; the first `coga bump` freezes the snapshot.
- Add `contexts:` as a YAML list (one item per line with `- `).
- Do not add a context just because it is generally related. If in doubt, leave
  it out and write the one needed fact into `## Context`.
- Update `assignee:` only if it changed.
- If the target file actually has `skill: bootstrap/ticket` in frontmatter
  from an older seeded flow, remove it. Modern `coga ticket` injects this
  skill only into the prompt; it should not persist on normal tasks.
- Preserve the current `status:`. You do not activate or start the ticket —
  the human starts it later with `coga launch`, or queues it without starting
  via `coga mark active`.
- Fill the `## Description` and `## Context` body sections from the
  interview.

Do not call `coga bump`. There's no workflow running yet.

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

Write the evaluator's response to the ticket's blackboard region under a top-level
**## Evaluator review** section, verbatim. Don't summarize — the human reads
it directly.

## Step 7 — Show the summary and ask the human to validate

Before exiting, print a compact summary the human can sanity-check at a
glance. The point is to surface the choices that are easy to get wrong and
hard to spot once the ticket has launched — workflow shape, the skills each
step will run, and the autonomy tier you landed on (so the human validates the
classification before launch).

Read `coga/workflows/<name>.md` (or
`coga/bootstrap/workflows/<name>.md` for a bundled battery) for the
workflow you picked and pull its step list (each step's `name:` and
`skills:`). Then print:

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

Durable review notes: <1-2 lines with durable evaluator findings, or "none">
```

Then ask the human directly: "Does this look right, or anything to change
before you launch?" Wait for their reply. If they redirect — swap the
workflow, drop a context, reword the description, fix an extension field —
make the edit and reprint the relevant part of the summary. Only move on
once they explicitly confirm.

After confirmation, do one final cleanup pass before printing the closing line:

1. Re-read the blackboard authoring sections: `## Evaluator review`,
   `## Proposals`, and `## Ticket authoring notes` if present.
2. Fold the durable substance into the ticket body, usually `## Context` or the
   section where a future implementer will need it. Preserve concrete review
   findings, risks, constraints, and out-of-scope decisions; do not dump the
   whole review verbatim.
3. If the ticket is still `status: draft`, reset the blackboard region to the
   stock placeholder for this ticket title. Do not leave empty authoring
   headings behind.
4. If editing an existing non-draft ticket (`active`, `in_progress`, `paused`,
   or `done`), preserve unrelated blackboard content such as blockers, dev
   notes, production notes, and handoff notes; remove only the authoring
   sections you used.
5. Re-read the ticket and verify the durable notes now live above the
   blackboard fence and the blackboard cleanup matches the ticket status.

Once that cleanup is complete, print one closing line. For a draft:

```
Filled <slug>. Run `coga launch <slug>` when ready. Use `coga mark active <slug>` only to approve it without launching.
```

For an already-active ticket:

```
Updated <slug>. Run `coga launch <slug>` when ready to start work.
```

Optionally `coga slack --task <slug> --message "<short>"` if the ticket
warrants a heads-up to the channel (a new context was created, an assignee
changed, etc.). Skip the Slack post for routine fill-ins.

Then exit.
