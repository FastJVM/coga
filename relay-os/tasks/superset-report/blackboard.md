The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap (2026-06-04)

Ticket filled via bootstrap/ticket against the existing draft, with Zach
at the keyboard:

- **Workflow** set to `docs/create-google-doc` (bare string; the first
  `relay bump` freezes the snapshot). Same workflow dust-report and
  conductor-report ran.
- **Description reviewed with Zach.** Answer 3 (weaknesses) was rewritten
  for clarity — comma splices removed and the point made explicit: the
  project went smoothly because of Claude Code, not Superset, which is why
  the paid tier felt like it added nothing. Tone decision (Zach's call):
  soften "I felt completely ripped off" to "the paid tier didn't justify
  its cost for this project" — the doc workflow will add prose on top of
  these raw notes anyway.
- Minor fixes to answers 1–2: clearer phrasing of "done better than when I
  used any other service", restructured the dangerously-skip-permissions
  sentence, "less" → "fewer", Claude Code capitalization.
- **## Context filled** with the two facts the future draft step needs,
  copied from the conductor-report blackboard (per the context-selection
  contract — copy the fact, don't attach a broad context): sibling report
  Docs live in Drive folder `0AI38XlSataDrUk9PVA`, and the agreed report
  structure is intro verdict / three numbered sections / closing thought /
  bolded bullet leads.
- `contexts: []` left empty deliberately.
- **Doc title confirmed by Zach: "Superset Report"** (evaluator caught the
  omission vs. the dust-report pattern); added to the description.
- `relay validate` on the filled ticket: only `unfrozen-workflow` (warn),
  the expected state for a bare-string workflow draft awaiting first
  launch. Zach confirmed the summary — ticket is launch-ready.

## Evaluator review

**Verdict: Launch-ready with one factual flag to resolve — the ticket is well-formed and the workflow fits cleanly.**

**1. Description clarity.** Strong. The three answers are fully written out, so the agent has the actual content to draft from — not just a brief. An agent with no prior context could start immediately. The numbered-answer structure matches both sibling tickets exactly.

**2. Workflow fit.** Correct choice. This is the third instance of the same author-a-Doc-from-prose pattern that conductor-report and dust-report already ran to completion. No mismatch.

**3. Attached contexts (`contexts: []`).** Matches both siblings, which also ran with `contexts: []` successfully. The workflow file itself carries the MCP Drive gotchas in its preflight, so nothing critical is missing. Acceptable as-is.

**4. Context body vs. attached context.** Well-balanced. The Drive folder ID `0AI38XlSataDrUk9PVA`, the prior-doc titles, and the structural template are all task-specific *facts*, correctly inlined rather than over-promoted to a shared context. Good discipline. The pointer to the conductor-report blackboard for HTML→Doc gotchas is slightly redundant (those gotchas are already in the workflow's preflight), but harmless.

**5. Scope.** Single ticket, single deliverable. Reasonable, not bundled.

**6. Assumptions to question before launch:**
- **Title.** dust-report explicitly specified "The title of the document should be Dust Report." This ticket never states a title. Infer "Superset Report" from the series, but confirm — it's the one omission vs. the sibling pattern.
- **Frontmatter shape.** This ticket has a bare `workflow: docs/create-google-doc` string and **no `step:` field**, whereas both siblings carry an expanded `workflow:` snapshot (name + steps). If launched via `relay launch` rather than the CLI assigning these, this risks the `bad-shape — workflow is set, but step is missing` error noted in your standing prefs. Let the CLI populate both, or inline the full snapshot + quoted `step:` as the siblings do.
- **Folder claim.** Verify `0AI38XlSataDrUk9PVA` is the live folder holding both prior reports — the whole point is keeping the set together.

## Preflight (2026-06-04)

**Check passed.** Google Drive MCP connection is live and
`Google_Drive create_file` is exposed.

- Read-only proof: `list_recent_files` returned real data (Conductor
  Report and Dust Report among the most recent files).
- `create_file` contract matches what conductor-report learned: only
  `text/plain` → Doc and `text/csv` → Sheet auto-convert; HTML uploads
  land as raw HTML files. No update/delete tools.
- **Folder claim resolved — the ticket's Context is outdated.** The
  evaluator's flag was right: both sibling reports were moved out of
  `0AI38XlSataDrUk9PVA` into a subfolder of it, **"Relay Competition
  Tests"** (`1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT`, created 2026-06-03).
  Verified by searching `parentId = '0AI38XlSataDrUk9PVA'` (no report
  Docs directly there) and by the siblings' `parentId` in the recents
  listing.
- **Zach's decision: upload the Superset Report HTML to the "Relay
  Competition Tests" subfolder** (`1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT`),
  not the parent folder named in the ticket Context — keeping the set
  together is the intent. Draft/upload steps: use this folder ID.

## Draft step (2026-06-04)

- Steps 1–2 of the workflow (gather/clarify) were already satisfied by
  the bootstrap: content, title, tone, structure, and destination folder
  all resolved on this blackboard. No re-interview needed.
- **Draft reviewed inline and approved by Zach** before upload. Structure
  mirrors the siblings: intro verdict ("fastest, cleanest run — but the
  credit belongs to Claude Code, not Superset"), three numbered sections
  (time, strengths, weaknesses), closing thought, bolded bullet leads.
  Softened paid-tier phrasing per the bootstrap tone decision.
- **HTML uploaded** via `Google_Drive create_file`,
  `contentMimeType: text/html`, into "Relay Competition Tests"
  (`1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT`). Landed as raw HTML as expected.
  - File ID: `1IzufHDNyPw1cPmnIFHGlT_4odzBEJGRH`
  - File link: https://drive.google.com/file/d/1IzufHDNyPw1cPmnIFHGlT_4odzBEJGRH/view
- **Conversion done — Zach confirmed the Doc looks great.**
  - **Draft Doc link:**
    https://docs.google.com/document/d/1Q51IBIMgoctpoiMQtrmKAGRIwqrjqPr-R_siUnKqq1Y/edit
  - The raw HTML file (`1IzufHDNyPw1cPmnIFHGlT_4odzBEJGRH`) still sits
    alongside it in the folder; MCP has no delete tool, so cleanup (if
    wanted) is manual.
- Step finished with
  `relay bump superset-report --message "draft Doc: <link>"`.

## Revise step (2026-06-04)

- Doc link handed to Zach for review at the top of the step.
- **Zach: no changes.** Zero revision rounds needed.
- **Agreed-final Doc:**
  https://docs.google.com/document/d/1Q51IBIMgoctpoiMQtrmKAGRIwqrjqPr-R_siUnKqq1Y/edit
- Reminder for cleanup: the pre-import HTML file
  (`1IzufHDNyPw1cPmnIFHGlT_4odzBEJGRH`) is still in the folder; trash
  manually if wanted (MCP has no delete tool).
- Bumping into `sign-off`.
