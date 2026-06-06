The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap notes (2026-06-06)

- Attached `workflow: docs/create-google-doc` as a bare string per bootstrap/ticket — first `relay bump` freezes the snapshot and assigns `step:`. `relay validate` confirms only the expected `unfrozen-workflow` warn for this draft; the evaluator's "missing `step:` will block launch" finding (item 6, last bullet) is a false alarm for this shape.
- No `[ticket.fields.*]` extension fields declared in relay.toml — nothing to fill.
- `contexts: []` left as-is pending human's call (see evaluator item 3: attach `relay/principles` only if the doc should fact-check Relay claims rather than carry the author's editorial verbatim).

## Human decisions on evaluator findings (2026-06-06)

1. Verbatim-source instruction → accepted, added to `## Context`.
2. Table vs. narrative → **produce both versions in the first draft** so the human can compare; structure picked in the revise loop. Added to `## Context`.
3. Audience → internal doc, teammate-facing. Added to `## Context`.
4. Drive folder → "Relay Wishlist/ Bucket Comparison" is the **literal name of one folder** (slash is part of the title, not a subfolder path). Added to `## Context`.
5. `contexts: []` stays — doc carries the author's editorial verbatim, no fact-checking against relay/principles.

## Preflight (2026-06-06)

- ✅ Google Drive MCP connection live — `list_recent_files` returned results (read-only proof, no trial uploads).
- ✅ `Google_Drive create_file` exposed; schema matches the known contract (auto-convert only `text/plain`→Doc and `text/csv`→Sheet; HTML lands raw, human converts via "Open with → Google Docs").
- **Target folder resolved as a side effect**: "Relay Wishlist/ Bucket Comparison " exists as a single folder, id `1W3cjsWsmMn_OysmjTYIuaoeEF9RRobat` (parent: My Drive root). Note the actual title has a **trailing space** after "Comparison" — confirms the human's "literal name of one folder" decision; no path resolution needed at draft time. Use this id as `parentId` for the upload.
- Folder already contains a prior pair from another task: `Relay Additions` (text/html + converted Doc) — expect this when listing; not ours to touch.

## Draft-step plan (2026-06-06)

1. Treat the ticket Description as the gathered request (per evaluator item 2) — no re-interview. All prior decisions stand: verbatim source, internal/teammate audience, two versions (table-led + narrative) for comparison, agent picks title.
2. **Open question for human**: one HTML file containing both versions back-to-back (one convert click, side-by-side compare in a single Doc) vs. two separate HTML files (two converts, two Docs, more folder clutter given MCP has no delete). Recommending single file.
3. Proposed title: **"Agent Tool Buckets — Is Relay Better?"** (becomes the Doc title on conversion; trivial to rename in Drive if disliked).
4. Generate HTML: Version A leads with a comparison table across buckets/tools (autonomy axis, failure-handling timing, human intervention, outcome), followed by short per-bucket notes; Version B is pure narrative sections (Bucket 1/2/3 + "Is Relay Better?"). Author's claims and anecdotes carried verbatim in both.
5. Upload via `Google_Drive create_file`, `contentMimeType: text/html`, `parentId: 1W3cjsWsmMn_OysmjTYIuaoeEF9RRobat` (resolved in preflight).
6. Hand the HTML file link to human → they convert via "Open with → Google Docs" → wait for Doc link.
7. Write Doc link here, then `relay bump bucket-comparison-document --message "draft Doc: <link>"`.

## Draft uploads (2026-06-06)

- Human chose **two separate files** for the version comparison (one convert click each, winner kept as its own Doc).
- Title (agent-chosen per Context): "Agent Tool Buckets — Is Relay Better?" — version suffix in file titles only; h1 inside is suffix-free so the winning Doc needs no edit.
- Uploaded as `text/html` to folder `1W3cjsWsmMn_OysmjTYIuaoeEF9RRobat`:
  - Table Version — HTML file id `1QN5njVmQjcFQzA7b2tipHXSAHdFqsqn5` (bucket comparison table + "problem seen / Relay's answer" table in the Relay section)
  - Narrative Version — HTML file id `1cIW_ZM5Hkd0C7xQuMd8mI0Lc7XY6YqlJ` (pure prose sections, author's wording near-verbatim)
- Awaiting human "Open with → Google Docs" conversion on both; Doc links to be recorded here before bump.

## Draft outcome (2026-06-06)

- Human converted the **Narrative Version**, edited it directly in Docs, and **deleted the table version** (HTML + any Doc). Structure question is settled: narrative won.
- **Draft Doc link**: https://docs.google.com/document/d/1IbQ4qh17rK2SZNFIGrMZVkvc_qSSHHiAFvANs7a60eU/edit
- Human's verdict verbatim: "It's totally good to go" — the doc already reflects their own edits, so the upcoming review/revise step should expect little or no rework. The narrative HTML file (`1cIW_ZM5Hkd0C7xQuMd8mI0Lc7XY6YqlJ`) is now a leftover next to the Doc; human trashes at their discretion.

## Evaluator review

## Review: bucket-comparison-document ticket

### 1. Is the description clear enough to start cold?
Mostly yes on **content**, no on **task framing**. The Description is essentially the finished thought-content of the doc itself — three buckets with named tools and a per-bucket rationale, plus a "Is Relay Better?" argument. A drafting agent could absolutely turn this into prose. But the Description is written in first person as raw source material ("I'm creating a google doc that..."), not as an instruction to the agent. There's no statement of *what the agent should produce*: a comparison table? Narrative sections? How long? The agent has to infer the deliverable's shape from the workflow rather than the ticket. That inference mostly works here, but it's load-bearing and undocumented.

### 2. Does docs/create-google-doc fit?
Yes — strong fit. The work is "author a document, get it into Drive as a Google Doc, iterate with the human." That is exactly this workflow's job (HTML draft → upload as `text/html` → human converts → review/revise loop). `mode: interactive` matches the workflow's expectation that the human is at the keyboard for `draft` and `revise`. No mismatch. One small note: the `draft` step's first instruction is "Gather the request… purpose, content, structure, tone" — but here the content is *already* in the ticket. The agent should treat the ticket body as the gathered request rather than re-interviewing the human from scratch; nothing in the ticket signals that, so expect a redundant "what do you want?" round-trip unless the agent is sharp.

### 3. Are the attached contexts right? Is `contexts: []` correct?
`contexts: []` is defensible but I'd reconsider one. The "Is Relay Better?" section makes substantive claims about Relay's value proposition (no black box, human-in-every-loop, reusable skills/contexts/workflows, variance removal). Those claims are the author's own framing and read fine as opinion — but if the doc is meant to be accurate about what Relay *is*, attaching `relay/principles` or `relay/current-direction` (the canonical contexts named in CLAUDE.md) would let the agent fact-check the Relay characterization against the behavioral contract instead of parroting the Description. If the doc is purely the author's personal editorial, `[]` is fine. The ambiguity itself is worth resolving before launch. No skill is needed.

### 4. Missing facts the agent will wish it had
This is the weakest part of the ticket. The `## Context` body has only two lines, and several facts the workflow will actively need are absent:

- **Drive folder is named, not identified.** "Relay Wishlist/ Bucket Comparison folder" is a human path, not a folder ID. The `preflight`/`draft` steps upload via MCP `create_file`, which wants a parent folder ID. The agent will have to `search_files` to resolve it, and "Relay Wishlist/ Bucket Comparison" is ambiguous (is "Bucket Comparison" a subfolder of "Relay Wishlist"? note the stray space after the slash). Worth pinning the exact folder, or flagging that the agent must resolve and confirm it.
- **Audience / tone unspecified.** Is this an internal memo for the author, a pitch to teammates, something external-facing? The "Is Relay Better?" section reads like advocacy; tone matters and isn't stated. The workflow's `draft` step explicitly lists "tone" as something to gather — it's not in the ticket.
- **Document structure unspecified.** Bucket 1 vs 2 vs 3 is natural prose, but the title says "comparison" — does the author want a comparison *table* (the workflow specifically optimizes for HTML tables) across tools/buckets, or pure narrative? This is the single most likely source of a wasted first draft.
- **Definition of done.** No statement of what "done" looks like beyond the workflow's generic "human approves." Fine, but a one-liner on intended length/format would de-risk the first draft.

### 5. Is the scope reasonable?
Yes — single deliverable, one document, one workflow. It does not bundle multiple tickets. The two-part structure (categorize tools, then answer "Is Relay Better?") is one coherent document, not two tasks. No scope concern.

### 6. Assumptions to question before launch
- **Factual accuracy of tool claims.** The Description makes specific, checkable claims about named third-party products (Linear Agent, Dust, Cursor, Superset, Backlog, Conductor, Paperclip, OpenClaw) and a specific anecdote ("35 failed cycles… Playwright selectors," "OpenClaw completed perfectly the first try"). The agent should treat these as the author's verbatim assertions and *not* embellish, soften, or fact-check them into different claims — but it's worth an explicit instruction, because some of these names are obscure/likely-internal and an agent may be tempted to "correct" them.
- **"create a short and concise title."** The Context says the agent should invent the title. Combined with the workflow's behavior (the converted Doc inherits the HTML file's title), confirm the author actually wants the agent to choose the title vs. having a preferred one — cheap to ask, annoying to redo.
- **Single folder, possible name collision.** The workflow notes each human "convert" click mints a *new* Doc with the same title and the MCP server has no delete/update tools. Across the revise loop this folder will accumulate duplicate HTML files and Docs. The author should expect to do manual trashing — worth knowing going in, though it's the workflow's documented behavior, not a ticket defect.
- **Frontmatter.** `workflow: docs/create-google-doc` is set but there is no `step:` field. Per the canonical shape, a set workflow without `step:` will trip `bad-shape — workflow is set, but step is missing` at validate/launch. Either let the CLI assign both (set `workflow: null` in the draft) or add `step: "1 (preflight)"`. This will block `relay launch` as-is.

**Bottom line:** Content is rich and the workflow choice is right. The gaps are all in the `## Context` block (folder ID, tone, audience, table-vs-narrative) and one frontmatter defect (`step:` missing). Tighten those four context facts and fix the frontmatter before launch, and an agent can run this cleanly.

## Revise outcome — approved (2026-06-06)

- Handed the human the real Doc link at the top of the revise step; explicit approval given in-terminal: "I approve." No changes requested — the Doc already carried the human's own edits from the draft step.
- **Agreed-final Doc**: https://docs.google.com/document/d/1IbQ4qh17rK2SZNFIGrMZVkvc_qSSHHiAFvANs7a60eU/edit ("Agent Tool Buckets — Is Relay Better?", Narrative Version)
- Leftover narrative HTML file (`1cIW_ZM5Hkd0C7xQuMd8mI0Lc7XY6YqlJ`) still in the Drive folder; human trashes at their discretion (MCP has no delete).
- Side fix during this step: resolved a `git stash pop` (autostash) conflict on `relay-os/recurring/digest/blackboard.md` left by the admin-update pull flow — union of both spool sides in timestamp order, no records lost; redundant autostash entry dropped. This was blocking all git commits (incl. `relay mark done`).
