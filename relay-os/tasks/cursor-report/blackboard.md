The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap notes (2026-06-04)

- Attached `workflow: docs/create-google-doc` (bare string; first `relay bump` freezes the snapshot).
- `contexts: []` left empty deliberately — the Drive MCP contract lives inline in the workflow's preflight/draft bodies, matching the done conductor-report sibling.
- Doc title and destination folder ("Relay Competition Tests") already in `## Context`.

## Preflight (2026-06-04)

- **Connection: live.** Read-only `list_recent_files` (pageSize 5) succeeded against the claude.ai Google Drive MCP server.
- **`create_file`: exposed**, contract matches the known one (auto-converts only `text/plain` → Doc and `text/csv` → Sheet; `text/html` lands raw — that's the expected `draft` artifact; human converts via "Open with → Google Docs").
- Bonus facts resolved for `draft` (no extra lookups needed):
  - Destination folder **"Relay Competition Tests"** exists and is unambiguous: id `1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT`.
  - Sibling **Conductor Report** Doc (structure to mirror) is in that folder: id `1cij60SgQAqeKxNt8QOFJ9R_sChlPS0OayMaOel7wZV4`.
  - Folder also holds done siblings Linear Agent Report, Superset Report, Backlog Report — all native Docs, consistent with the series.
- Preflight passes → bumping to `draft`.

## Draft step (2026-06-04)

- Read the sibling **Conductor Report** Doc (`1cij60SgQAqeKxNt8QOFJ9R_sChlPS0OayMaOel7wZV4`) to capture the structure to mirror:
  1. Title → intro paragraph ("covers three questions" + a "short version" summary sentence)
  2. `## 1. How long did the project take?` — prose, includes a cross-service comparison
  3. `## 2. Strengths of the service` — one-line intro naming the cluster/theme, then bullets with **bold lead-ins**
  4. `## 3. Weaknesses of the service` — one-line intro naming the root cause, then bullets with bold lead-ins
  5. `## Closing thought` — synthesis + cross-service comparison
- Per evaluator review: normalizing typos ("view ability" → "visibility") and splitting the description's comma-run paragraphs into bullets, not transcribing literally.
- Final state confirmed in ticket Context: **the email never sent; project left unfinished after 2.5 hours** — leading with that in the intro and §1, echoing in weaknesses + closing.
- Presented full draft inline to Zach for approval before generating HTML / uploading.
- Zach approved the draft as-is (including the Conductor comparisons in §1/closing and the "strongest of any service so far" closing claim).
- Uploaded HTML to "Relay Competition Tests" (`contentMimeType: text/html`, lands raw as expected): file id `1716K2N7sJPfVZGEIfJTmwpnwnsFeJWon`, link https://drive.google.com/file/d/1716K2N7sJPfVZGEIfJTmwpnwnsFeJWon/view
- Awaiting Zach's "Open with → Google Docs" conversion + the resulting Doc link.
- Zach converted; verified the Doc renders clean (headings, bullets, bold lead-ins all intact; structure matches the Conductor sibling).
- **draft Doc: https://docs.google.com/document/d/1BHT1URqFrCjbFXBtsi3XQl-zCTsexrTNIqqcOrR2dOI/edit** (Doc id `1BHT1URqFrCjbFXBtsi3XQl-zCTsexrTNIqqcOrR2dOI`; the raw HTML file `1716K2N7sJPfVZGEIfJTmwpnwnsFeJWon` still sits alongside it in the folder if cleanup is wanted).
- Draft step complete → bumping.

## Revise step (2026-06-04)

- Handed the draft Doc to Zach for review: https://docs.google.com/document/d/1BHT1URqFrCjbFXBtsi3XQl-zCTsexrTNIqqcOrR2dOI/edit
- Zach reviewed the converted Doc and approved it **as-is** — zero revision rounds needed.
- **Agreed-final Doc: https://docs.google.com/document/d/1BHT1URqFrCjbFXBtsi3XQl-zCTsexrTNIqqcOrR2dOI/edit** (Doc id `1BHT1URqFrCjbFXBtsi3XQl-zCTsexrTNIqqcOrR2dOI`)
- Cleanup note for the human: the raw pre-import HTML file (`1716K2N7sJPfVZGEIfJTmwpnwnsFeJWon`) still sits in "Relay Competition Tests" next to the Doc and can be trashed.
- Revise complete → bumping into `sign-off`.

## Evaluator review

# Ticket Review: cursor-report

## 1. Is the description clear enough to start cold?

Mostly yes — the three-question framing is identical to the proven conductor-report and an author would understand the goal. But several phrases are garbled enough to mislead the document author:

- **"gives easy view ability for which branch you are on"** — "view ability" reads as a typo for "visibility." A literal author might invent a feature called "view ability." Should be "easy visibility into which branch you're on."
- **"frontier models all available on the pro plan"** — parenthetical fragment; the author has to guess this modifies the agent drop-down. Fine, but worth tightening.
- **"lack of workflow upfront seems to push fixing the selectors to when you think you're ready to test the project"** — dense run-on; the causal claim (no upfront workflow → selector fixes deferred to test time) is recoverable but easy to mangle.
- **"Project was said to be done but the live-run of actually sending the email resulted in more tests to find the send button"** — "resulted in more tests to find the send button" is ambiguous. Does it mean *additional test iterations were needed to locate the send button selector*? The author will likely have to infer intent. This is the single most likely phrase to be rendered wrong.
- **Structural note:** items 2 and 3 are each a single comma-spliced paragraph cramming ~6 distinct points. That's the same style as conductor-report (which shipped fine), so it's workable, but the author should expand each into a bulleted list rather than transcribing the comma-run verbatim.

Net: an agent can start, but should be told to **normalize typos and split the comma-runs into bullets**, not transcribe literally.

## 2. Does the docs/create-google-doc workflow fit?

Yes — clean fit. The work is "author a narrative document, put it in Drive as a native Doc, review/revise with the human, sign off." That is exactly what the workflow's preflight → draft → revise → sign-off path does, and conductor-report proves the same workflow on an identical task. No mismatch.

## 3. Are the attached contexts relevant? Is `contexts: []` correct?

`contexts: []` is **correct and matches the proven sibling** (conductor-report also ships empty). The Drive MCP contract — the only world-fact the agent needs — is carried inline in the workflow's `## preflight` and `draft` bodies (the `text/html` no-auto-convert rule, the human-click conversion, no update/delete tools). Nothing important is missing on the context axis. Empty is right.

## 4. Are facts the future agent needs missing from `## Context`?

This is where cursor-report is actually **better than its done sibling** — conductor-report shipped with an empty `## Context`, whereas cursor-report supplies:
- Doc title: **"Cursor Report"**
- Destination: **"Relay Competition Tests" folder** in Drive

Two facts that would help and are currently absent:

- **Series-consistency / mirror structure.** The ticket never says the Cursor Report should mirror the structure of the sibling Conductor Report. Given both live in "Relay Competition Tests" and answer the same three questions, the human almost certainly wants parallel structure for comparison — but the agent has no instruction to go read conductor-report's Doc and match its format. Worth stating explicitly (e.g. "mirror the Conductor Report's section structure for series consistency"). The workflow's draft step says to upload "next to any sibling docs the ticket points at," but the ticket points at no sibling Doc link — so this hook is currently unused.
- **Final state of the unfinished project.** The description says "took me 2.5 hours and I still wasn't able to finish it" and ends with the send-button testing problem, but never states the actual end state (did it ever send? was it abandoned mid-test?). Conductor's version had the same gap. If the human wants an honest "where it ended up" line, the agent will have to ask in the interactive `draft` step — which is fine, but flag it as a known clarification.

Neither is blocking (mode is `interactive`, so the agent can ask), but the mirror-structure point is the most valuable thing to add before launch.

## 5. Is the scope reasonable?

Yes — single document, single workflow run. No bundling. It is one ticket's worth of work and directly parallels a completed sibling.

## 6. Assumptions to question before launch

- **Frozen-workflow shape.** This ticket has `workflow: docs/create-google-doc` as a bare string, whereas the done conductor-report has a **fully inlined `workflow:` snapshot with steps + per-step assignees**, and no top-level `step:` field. Per repo convention, the CLI assigns the frozen snapshot and `step:` together at launch — so leaving it as a bare string and letting `relay launch` populate it is the clean path. Just confirm launch is done via the CLI (not hand-edited), or it won't have a valid `step:`.
- **`assignee` mismatch.** cursor-report has `assignee: claude`; the done conductor-report has `assignee: zach`. The first workflow step (`preflight`) is `assignee: agent`, so `claude` is arguably more correct for the starting step — but verify this is intentional and not a copy drift, since the CLI normally manages `assignee` to track the current step's owner.
- **"Relay Competition Tests" folder is assumed to exist** and be unambiguous in Drive. The preflight only verifies the connection and `create_file`; it does not resolve the destination folder. If the folder name is wrong or duplicated, the agent discovers it only at upload time in `draft`. Low risk, worth a glance.
- **Status is `draft`** — correct for a pre-launch ticket; just noting it must be moved to launch via the CLI.

## Bottom line

Workflow choice, empty contexts, and scope are all correct and match the proven sibling. The ticket is launch-ready with two recommended additions to `## Context`: (a) an explicit instruction to **mirror the Conductor Report's structure** for series consistency, and (b) a note on the **project's actual final state** (or an acknowledgment the agent must ask). Before launch, also clean the description typos ("view ability" → "visibility") and tell the author to **split the comma-run paragraphs into bullets** rather than transcribe them literally.
