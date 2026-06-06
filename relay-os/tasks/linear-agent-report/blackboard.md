The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap notes (2026-06-04)

- Attached `workflow: docs/create-google-doc` as a bare string; first `relay bump` freezes the snapshot.
- Enriched `## Context` with facts copied from backlog-report: Drive folder ID for "Relay Competition Tests" (`1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT`), series structure (intro verdict, three numbered sections, closing thought, bolded bullet leads), and time baselines (Conductor 2h, Backlog 2.5h) backing the "3.5 hours was one of the longest" claim.
- `contexts: []` kept empty — everything needed is inlined in `## Context`; the MCP Drive contract lives in the workflow's preflight section.
- `assignee: claude` kept (siblings show `zach` only because they're at/past the owner-owned sign-off step).
- Zach resolved the evaluator's open questions (2026-06-04): Dust baseline is 2 hours (added to `## Context`); keep the exact Playwright flow terms in the doc, no glossing needed. Added an `Answers:` header to fix the Description numbering collision.
- `relay validate` shows only the expected `unfrozen-workflow` warning — snapshot freezes at first launch.

## Evaluator review

## 1. Can an agent start cold?

Mostly yes. The description carries all three answers verbatim, the title is given, and the Drive folder is named with its ID. A cold agent could begin drafting. Two friction points:

- The Description has a **numbering collision**: the three *questions* are numbered 1-3, then the three *answers* restart at 1-3. They line up by order, but it's easy to misread "1. End-to-end the project took..." as a fourth question. The sibling tickets (backlog-report, conductor-report) avoid this by using an explicit `Answers:` header before the second list. Recommend matching that.
- The answers are raw, run-on notes (one 9-line sentence-fragment paragraph for the weaknesses). That's fine as *source material* — the workflow's `draft` step is supposed to shape it — but the agent will have to do real editorial work to hit the "intro verdict / three sections / closing thought" structure. Worth confirming that's the expectation and not a verbatim-paste job.

## 2. Workflow fit

Good fit, no mismatch. This is exactly the shape `docs/create-google-doc` is built for, and it's the same workflow the three sibling reports used successfully (conductor-report is `done`, backlog-report reached `sign-off`). HTML draft → human convert → revise loop → sign-off maps cleanly onto "write a short narrative doc."

One structural note: this ticket stores `workflow: docs/create-google-doc` as a **bare string**, whereas both siblings inline the full `workflow:` snapshot (the four steps + assignees) plus a `step:` field. If this draft is meant to be `relay launch`ed as-is, it has neither the frozen steps nor the `step:` field. Either let the CLI assign both at launch (leave it bare and let `relay launch` populate), or inline the snapshot like the siblings — but the current half-state (named workflow, no steps, no `step:`) is the same shape that has produced `bad-shape` / launch errors before. Worth resolving before launch.

## 3. Are `contexts: []` correct?

Yes, empty is right. Both siblings also run `contexts: []`. Everything the agent needs — the Drive folder ID, the title, the structural template, the time baselines — is already inlined in `## Context`. The MCP Drive contract (the genuinely tricky knowledge) lives in the **workflow's `preflight` section**, not in a context, so nothing is missing. No context needs attaching.

## 4. Any context too broad — should a fact have been copied into `## Context`?

Not applicable here since `contexts: []`. The reverse is worth a glance: the ticket *points* at sibling tasks ("see the conductor-report and backlog-report tasks") for the 2h/2.5h baselines — but it then **also inlines those numbers directly** ("Conductor 2 hours, Backlog 2.5 hours"). That's the right call: the load-bearing fact is copied in, and the task pointer is just provenance. No fix needed.

## 5. Scope

Reasonable and correctly sized — one doc, one report, identical scope to each sibling ticket. Not bundled. No multi-ticket creep.

## 6. Assumptions to question before launch

- **Folder still current.** The ID `1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT` is copied from backlog-report, whose own Context notes a 2026-06-04 caveat: "the reports moved here from parent `0AI38XlSataDrUk9PVA`; Zach confirmed the subfolder is the target." This ticket inherits the ID but **drops that confirmation note**. Since the folder moved recently, preflight should re-verify the folder is correct rather than assume.
- **"One of the longest" claim.** The verdict "3.5 hours — one of the services that took me the longest" is supported only against Conductor (2h) and Backlog (2.5h). The ticket also references a **Dust** report in the series but gives no Dust time. If Dust took longer than 3.5h, the "one of the longest" framing weakens. Worth confirming the full comparison set before the agent writes the intro verdict.
- **Dust audience note.** Backlog-report carried an explicit "audience may not know Pylon — make it standalone" instruction. This ticket's weaknesses reference Playwright internals (`fetchnewestmessage`, "fetch raw source", "send reply", "dry-run") with no reader-context guidance. If the doc's audience isn't deep in the deliverability build, the agent may need to gloss those — flag whether to keep them as-is or generalize.
- **Workflow snapshot** (repeat of #2): confirm whether this launches with a bare `workflow:` string or needs the inlined steps + `step:` field first.

## Preflight (2026-06-04)

- **Connection live.** Read-only `search_files` against the target folder succeeded via the Google Drive MCP server.
- **Folder verified.** `1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT` ("Relay Competition Tests") is correct and current — it contains the four sibling docs as native Google Docs: Dust Report, Conductor Report, Backlog Report, Superset Report. Resolves the evaluator's "folder still current?" assumption.
- **`create_file` exposed.** Schema confirms the known contract: auto-converts only `text/plain`→Doc and `text/csv`→Sheet; HTML uploads land as raw HTML files (expected artifact for `draft`). No update/delete tools on the server, as documented.
- Preflight passes → bumping to the next step.

## Draft (2026-06-04)

Content drafted from the ticket brief, reviewed inline by Zach, then
uploaded **once** to Drive after approval — same single-upload flow as
backlog-report.

- **Draft HTML in Drive (awaiting human convert):**
  https://drive.google.com/file/d/1h9aQ_PzUpFBdy41dw6Caoyuq2DQF4FE4/view
  (`1h9aQ_PzUpFBdy41dw6Caoyuq2DQF4FE4`, `text/html`, title "Linear Agent
  Report", parent `1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT` — Relay Competition
  Tests, next to the Dust/Conductor/Backlog/Superset reports.)
- Local copy: `/tmp/linear-agent-report.html`.
- Structure mirrors `/tmp/backlog-report.html` exactly (intro verdict,
  three numbered h2 sections, closing thought, bolded bullet leads).
- Content decisions:
  - Intro verdict and section 1 name all three baselines (Dust 2h,
    Conductor 2h, Backlog 2.5h) behind the "one of the longest" claim,
    keeping the ticket's "one of the" phrasing (Superset time unknown).
  - Playwright flow terms (fetchnewestmessage, fetch raw source, send
    reply, dry-run) kept verbatim, per ticket Context — no glossing.
  - Strengths render as two bullets (issues-as-tickets, per-issue
    "done" legibility + commit-readiness) — the source material has two
    distinct points, not three; didn't pad to match siblings.
  - "Testing got pushed to the backend" clarified with Zach in-session:
    it means a **false done** — the project presented as complete and
    the testing debt surfaced only after. Drafted accordingly
    ("left under the impression the project was complete...") in the
    third weakness bullet and the closing thought.
- One revision round inline before upload (false-done rewording); no
  duplicate uploads.

Conversion done (Zach, same session, one click — no duplicate Docs):

- ✅ **Draft Doc (the artifact):**
  https://docs.google.com/document/d/1bGjN_EuKrKlt41FqPNVG8UfhsJDqaHQTuHlbO4KU3oM/edit
- The source HTML file (`1h9aQ_PzUpFBdy41dw6Caoyuq2DQF4FE4`) is still in
  the folder — conversion leaves it in place. Trash it after sign-off
  (human task; the MCP server has no delete tool).

Bumping into the next step with the Doc link.

## Revise (2026-06-04)

Zach reviewed the converted Doc and signed off with **zero revision
rounds** — no changes requested.

- ✅ **Agreed-final Doc:**
  https://docs.google.com/document/d/1bGjN_EuKrKlt41FqPNVG8UfhsJDqaHQTuHlbO4KU3oM/edit
- No superseded files from this step (no re-uploads happened). The one
  leftover artifact is still the original source HTML
  (`1h9aQ_PzUpFBdy41dw6Caoyuq2DQF4FE4`) noted in the Draft section —
  trash it after sign-off (human task; MCP server has no delete tool).

Bumping into `sign-off`.
