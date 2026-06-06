The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap notes (2026-06-04)

Ticket filled via bootstrap/ticket interview:

- Attached `workflow: docs/create-google-doc` as a bare string (CLI freezes
  the snapshot and assigns `step:` on first bump — deliberate, cleaner than
  the hand-inlined snapshots on the sibling tickets).
- Fixed "veins" → reworded the Kanban weakness to be standalone; kept the
  Pylon mention as a parenthetical, with a `## Context` note telling the
  drafting agent to generalize it for the doc audience.
- Added the 2-hour Conductor baseline to the timing answer (Zach confirmed
  that's the comparison).
- Filled `## Context`: series convention (match Dust/Conductor report
  structure), target Drive folder `0AI38XlSataDrUk9PVA`, Pylon-audience
  note, baseline provenance.
- Zach confirmed the editing-weakness meaning: tasks are markdown files on
  disk, but hand-editing the files isn't supported — CLI or Kanban board
  are the only edit paths.

Post-evaluator decisions (Zach): added the explicit doc title ("Backlog
Report") and an "Answers:" lead between the two numbered lists; kept the
Pylon parenthetical in the Description as-is (Context note governs how the
doc renders it). `assignee: claude` and the bare-string `workflow:` form
stay as-is, both deliberate.

## Preflight (2026-06-04)

Gate passed:

- **Connection live** — read-only `Google_Drive search_files` calls via the
  claude.ai MCP server succeed.
- **`create_file` exposed** — schema loaded; contract matches the workflow's
  known-contract block (auto-converts only `text/plain`→Doc and
  `text/csv`→Sheet; HTML lands raw; no update/delete tools).
- **Folder discrepancy found and resolved** — the ticket targeted parent
  `0AI38XlSataDrUk9PVA`, but the Dust Report and Conductor Report were moved
  into a subfolder of it: **"Relay Competition Tests"**
  (`1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT`, created 2026-06-03), alongside a new
  "Superset Report". Zach confirmed the Backlog Report should land there too.
  Ticket `## Context` updated with the new ID.

For the draft step: upload the HTML with
`parentId: 1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT`. Sibling docs for structure
reference: Dust Report `1NizIofbDCDzKuMyds9UaAU5BPr1rylUexJ1qQEFWcvs`,
Conductor Report `1cij60SgQAqeKxNt8QOFJ9R_sChlPS0OayMaOel7wZV4`.

## Draft (2026-06-04)

Content drafted from the ticket brief, reviewed inline by Zach, approved
as-is ("upload it as-is") — then uploaded **once** to Drive.

- **Draft HTML in Drive (awaiting human convert):**
  https://drive.google.com/file/d/1GkWNjbFugFNVAWK_6VZmjpPv7tBBylDk/view
  (`1GkWNjbFugFNVAWK_6VZmjpPv7tBBylDk`, `text/html`, title "Backlog
  Report", parent `1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT` — Relay
  Competition Tests, next to the Dust/Conductor/Superset reports.)
- Local copy: `/tmp/backlog-report.html`.
- Structure mirrors `/tmp/conductor-report.html` exactly (intro verdict,
  three numbered h2 sections, closing thought, bolded bullet leads).
- Content decisions: Pylon dropped entirely from the Kanban weakness
  (standalone "organized when sparse, overwhelming when full"), per
  ticket Context. The 30-minutes-over nuance (CLI learning curve +
  project tightening, not tool slowness) preserved in both the intro
  verdict and section 1.
- No duplicate uploads this time — draft was approved inline before the
  single `create_file` call.

Conversion done (Zach, same session, one click — no duplicate Docs):

- ✅ **Draft Doc (the artifact):**
  https://docs.google.com/document/d/14pUD0lC8wpAzK7KqDlemWhCLvqKF0v_yzmxnvpcR7wQ/edit
- The source HTML file (`1GkWNjbFugFNVAWK_6VZmjpPv7tBBylDk`) is still in
  the folder — conversion leaves it in place. Trash it after sign-off
  (human task; the MCP server has no delete tool).

Bumping into `revise` with the Doc link.

## Revise (2026-06-04)

Zach reviewed the converted Doc and approved it with **no changes**
("Good as-is") — zero revision rounds needed.

- ✅ **Agreed-final Doc:**
  https://docs.google.com/document/d/14pUD0lC8wpAzK7KqDlemWhCLvqKF0v_yzmxnvpcR7wQ/edit
- No superseded files/Docs from this step (nothing re-uploaded). The only
  cleanup item remains the original source HTML
  (`1GkWNjbFugFNVAWK_6VZmjpPv7tBBylDk`) — trash after sign-off (human task).

Bumping into `sign-off`.

## Evaluator review

# Critique: backlog-report ticket

## 1. Can an agent start cold? Yes, mostly.
The Description is unusually complete for a draft — it gives the three questions, the actual answers (2.5h vs 2h baseline, named strengths, named weaknesses), and the Context section supplies the structural convention, the target Drive folder, and an audience note. An agent could open `draft` and start generating HTML immediately. This is more "content brief" than "task description," and that's the right shape for this workflow.

One snag: the Description has **two `1.`/`2.`/`3.` lists stacked** (the questions, then the answers) with no header separating them. It reads fine to a human, but an agent generating HTML should be told the second list is the *answer content*, not a second set of questions. Minor — a one-line "answers below" lead would remove all doubt.

## 2. Workflow fit: strong, no mismatch.
`docs/create-google-doc` is exactly right. The deliverable is a Google Doc in a specific Drive folder, the human (zach) is at the keyboard for the convert-and-review loop (`mode: interactive`), and the third sibling in this series (`conductor-report`) ran this exact workflow to completion. The preflight → draft → revise → sign-off shape maps cleanly onto "write report, upload HTML, human converts, iterate, approve." No friction.

## 3. Contexts: `contexts: []` is correct here.
There is no `docs/` context namespace — the only contexts in the repo are `relay/*` and `dev/code`, none relevant to writing a tool-eval Doc. Both sibling tickets (`conductor-report`, `dust-report`) also ship `contexts: []`. The facts an agent needs (folder ID, structure convention, MCP conversion gotcha) live correctly in `## Context` and in the workflow file itself (the preflight contract block). Nothing is missing. Don't add a context.

## 4. Context vs. ticket placement: clean, with one redundancy.
`## Context` is carrying the right things — the Drive folder ID, the series-structure convention, the audience/Pylon note, the baseline provenance. These are facts-about-the-world that vary per ticket, so they belong in the ticket, not the workflow. Good.

The one thing to flag: the **2.5h-vs-2h timing and the Pylon-comparison framing already appear in the Description**, and `## Context` then re-states the baseline ("The 2-hour baseline is the same deliverability project built on Conductor") and re-litigates the Pylon point ("make the Kanban-board point standalone... rather than leaning on the Pylon comparison"). That's not wrong — Context is allowed to *constrain* how Description content is rendered — but note the Pylon guidance is a genuine **contradiction the agent must resolve**: the Description (line 26) explicitly invokes Pylon, and Context (line 32) says strip it. The agent should follow Context. Make sure that precedence is obvious, or just delete the Pylon clause from the Description so there's nothing to reconcile.

## 5. Scope: reasonable, single ticket.
One Doc, three sections, one folder. This is the same scope as the two completed/in-progress siblings. It does not bundle multiple tickets' work. Fine as-is.

## 6. Assumptions to question before launch.

- **Frontmatter shape differs from siblings.** This ticket has `workflow: docs/create-google-doc` as a bare string and **no `step:` field**, whereas `conductor-report` and `dust-report` inline the full `workflow:` snapshot (name + steps array). Per the global rule, leaving `workflow` to be expanded and omitting `step:` is the *cleaner* draft form — the CLI assigns both on `relay launch`. So this is acceptable, but it is **inconsistent with the two siblings**, which hand-inlined the snapshot. Decide deliberately: either let the CLI expand it (current form, fine) or match the siblings. Do not half-inline.

- **`assignee: claude` vs siblings' `assignee: zach`.** Both completed siblings set `assignee: zach`; this one sets `assignee: claude`. Since step 1 (preflight) and step 2 (draft) are agent-assigned, `claude` is arguably more correct as the launch assignee — but the divergence from the established pattern is worth a conscious check, not an accident.

- **Folder ID is stale-checkable, not verified.** The ticket asserts parent `0AI38XlSataDrUk9PVA`. The conductor-report blackboard confirms this is the real shared folder (and that the Dust Report lives there), so it's trustworthy — but the workflow's `preflight` step will re-prove the connection and the agent should confirm the folder still resolves before uploading, rather than trusting the literal ID blind.

- **No explicit title stated.** `dust-report`'s Description said "The title of the document should be Dust Report." This ticket never names the doc — the agent will have to infer "Backlog Report" from the title slug and series convention. Safe inference, but state it (one line in Description) to avoid a converted Doc titled "backlog-report" or similar.

- **The 30-minutes-over nuance.** The Description explains the 2.5h included CLI-learning time and project-tightening, not pure tool slowness. The agent should preserve that nuance in the intro verdict — otherwise the Doc reads as "Backlog was 25% slower," which undersells the tool against the series' fairness bar. Worth a Context line so it doesn't get flattened in drafting.

**Bottom line:** Launch-ready in substance. Before launch, (a) decide the workflow/step frontmatter form deliberately (don't half-inline), (b) resolve the Description-vs-Context Pylon contradiction by deleting it from the Description, and (c) add a one-line doc title. None of these block an agent from producing a good first draft.
