The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap notes (2026-06-06)

- Set `workflow: docs/create-google-doc` (bare string; first `relay bump` freezes the snapshot).
- `contexts: []` left empty intentionally — the workflow's `preflight` section embeds the Drive MCP contract, and nothing in `relay-os/contexts/` is relevant to authoring a Drive doc. Matches all 8 sibling `*-report` tickets.
- Evaluator review run; verbatim output below. Headline gaps: `## Context` is missing the Drive folder ID, a committed categorization/structure, an audience, and a "don't re-interview" line; the 8-tool header vs. items a–o only crediting ~5 tools needs reconciling.

## Decisions (2026-06-06, with Zach)

- **Two docs, two tickets, sequenced.** This ticket ships the team/Nico-facing "Relay Additions" wishlist doc only. A second draft ticket `relay-additions-spec` ("Relay Additions — Ticket Specs") launches after this one is done, so the specs reflect team feedback rather than spec'ing all 15 items blind.
- **Audience for this doc:** Relay team / Nico — readers know Relay but not the evaluated tools; each item explained enough to stand alone as a feature proposal.
- **Drive folder:** "Relay Wishlist/ Bucket Comparison", ID `1W3cjsWsmMn_OysmjTYIuaoeEF9RRobat` (pre-existing, verified via Drive search). Not Relay Competition Tests.
- **Structure:** agent proposes a categorization, Zach approves/adjusts in the revise loop.
- **Tool coverage:** intentional — the 8 tools are what was evaluated; items a–o are what's worth keeping. List is final.
- Evaluator's `## Context` gaps all addressed in the ticket rewrite (folder ID, audience, structure delegation, don't-re-interview line, `*-report` pointer); Description's vestigial numbering cleaned up, items a–o unchanged.

## Preflight (2026-06-06) — PASSED

- Google Drive MCP connection live: verified with read-only calls (no trial uploads).
- `Google_Drive create_file` is exposed; its schema matches the known contract (auto-converts only text/plain→Doc and text/csv→Sheet; HTML lands as a raw file — expected artifact for `draft`).
- Target folder verified via `get_file_metadata`: "Relay Wishlist/ Bucket Comparison " (note trailing space in actual title), ID `1W3cjsWsmMn_OysmjTYIuaoeEF9RRobat`, owner zach@fastjvm.com, `canAddChildren: true`. Folder is currently empty (parentId search returned no files) — so any file appearing there later is ours.
- Bumping to `draft`.

## Draft step (2026-06-06) — structure approved

- Proposed 5-section categorization inline; Zach approved with one change: **drop the a–o letters, number items per section (numbering restarts each section)**.
- Sections: 1. Conversation & workspace UI (a, e, j, k) · 2. From vision to running work (c, d) · 3. Task lifecycle automation (b, l) · 4. Status visibility & unblocking (m, n, o) · 5. CLI & onboarding (f, g, h, i).
- Judgment calls accepted as proposed: (o) agent-to-agent filed under visibility/unblocking (its stated value is knowing who has unblocking details); (i) skip-permissions filed under CLI & onboarding as friction removal. No standalone one-item sections.
- Per-item format: bold feature name + source tool → 1–2 sentences of observed behavior (unembellished, from the Description) → one "In Relay: …" synthesis sentence so each item stands alone as a feature proposal.
- Doc skeleton: intro (names all 8 evaluated tools, notes not every tool contributed an item, forward-looking wishlist not a report summary) → five H2 sections with `<ol>` lists → one closing line deferring "what to build first" to the follow-up spec ticket.
- HTML uploaded to "Relay Wishlist/ Bucket Comparison": file ID `1cTcxUSglHYsp2tNAyvI1yFYqpGVFFY9P` (raw HTML, as expected — superseded by the converted Doc below).
- Zach converted via Open with → Google Docs and confirmed it looks great.
- **Draft Doc: https://docs.google.com/document/d/17dZmEwnjLpKpv9lIpr2hFydcKGK0OhQlJR-vQo9_Qc8/edit**

## Revise step (2026-06-06) — approved with no changes

- Handed Zach the converted Doc for review; verdict: "Good as-is." Zero revision rounds needed.
- **Agreed-final Doc: https://docs.google.com/document/d/17dZmEwnjLpKpv9lIpr2hFydcKGK0OhQlJR-vQo9_Qc8/edit**
- Superseded artifact for Zach to trash: the raw pre-conversion HTML file, ID `1cTcxUSglHYsp2tNAyvI1yFYqpGVFFY9P`, in "Relay Wishlist/ Bucket Comparison".
- Bumping to `sign-off`.

## Evaluator review

# Review: relay-additions ticket

## 1. Description clarity

**Mostly clear, with one structural gap.** An agent can tell what the deliverable is: a Google Doc titled "Relay Additions" listing which features from 8 tools Zach wants in Relay. The 15 feature items (a–o) are concrete and self-describing — each names the source tool and what the behavior was (e.g. "Conductor's flow: Auto-created a new branch once a task was completed and merged"). That's good raw material.

But the framing scaffolding is half-built and will confuse a cold reader:

- The Description sets up a numbered list of goals ("The goal of this document is to: 1. Describe which aspects...") but there is only **one** goal, so the "1." is a list of one. Then "Answers:" starts another "1." whose only child is "a." through "o.". The double/triple numbering is vestigial — it reads like a template that was meant to have multiple goals but collapsed to one. An agent will read it fine, but the structure signals "unfinished."
- **The 8-tool list in the Description and the 15 feature items don't fully reconcile.** The numbered tool list includes **Linear Agent, Dust, Superset, and Cursor**, but none of items a–o attributes a feature to those four. Conversely the items credit Conductor, Paperclip (heavily — 7 of 15), Backlog, OpenClaw, and "multiple services." So the doc as specified would name 8 tools up front but only draw features from 4–5 of them. The agent should know whether that's intentional (the list is "tools I evaluated," the features are "what I'd keep") or whether Dust/Superset/Cursor/Linear-Agent contributions are missing. This is the single most likely thing to stall a draft.

## 2. Workflow fit

**The workflow mechanically fits but is shaped for a different deliverable.** `docs/create-google-doc` is exactly right for the produce-HTML → upload → human-converts → review-loop → sign-off mechanics, and it's the same workflow all 8 `*-report` siblings ran to completion. No issue with the steps themselves.

The friction is that `draft` step 1 ("Gather the request… purpose, content, structure, tone, must-haves") and step 2 ("Clarify if needed") are written for a from-scratch doc. Every sibling report ticket neutralized this with an explicit line in `## Context`: *"The Description already contains the full answers — the draft step should shape that raw material into the doc, not re-interview for it."* **This ticket is missing that line.** Without it, an agent following the workflow literally will re-interview Zach about purpose/structure/tone — which is wasted motion since the content is already here. Add the "don't re-interview" instruction, or the `draft` step's gather/clarify sub-steps will fire.

Also unlike the reports, this doc has **no template to mirror.** The reports all say "match the structure of the prior reports (intro verdict, three numbered sections, closing thought)." A feature-wishlist doc has no sibling exemplar in the folder. The `## Context` line "possibly additions split up by their categorization?" is the only structural guidance and it's a tentative question, not a spec (see Q4).

## 3. Contexts relevance (`contexts: []`)

**Empty is correct and consistent.** All 8 completed/in-flight siblings ran with `contexts: []`. The two load-bearing facts the workflow needs — the Drive MCP contract (text/html is not auto-converted, human-click conversion, no update/delete tools) and the target folder — live in the workflow's `preflight` section and (should live) in `## Context`. Nothing in `relay-os/contexts/` is relevant here: the tree is `_template`, `dev/code`, and `relay/*` (architecture, codebase, principles, etc.) — all about Relay's own internals, not about authoring a Drive doc. No context is missing.

## 4. Missing facts in `## Context`

This is the **weakest part of the ticket.** The `## Context` body is two lines, one of which is a question:

> The title of the document should be "Relay Additions"
> This Google Doc is to have its own structure, possibly additions split up by their categorization?

Compared to every sibling, the following load-bearing facts are **absent**:

- **No Drive folder / target location.** Every report ticket specifies the "Relay Competition Tests" folder, ID `1xWhoMrvyA0AluD4iItJ16UCmIrglFUZT` (verified, corrects the stale `0AI38XlSataDrUk9PVA` root ID that the older siblings cite). This ticket says nothing about where the doc lands. The agent will either ask, guess, or upload to the wrong place. **Add the folder ID.** Note: this is a *different kind* of doc — it may or may not belong in "Relay Competition Tests" alongside the per-tool reports. That's a decision the ticket should make, not leave to the agent.
- **"Categorization" is undefined.** `## Context` floats "possibly additions split up by their categorization?" as a question to itself. What are the categories? The features cluster naturally — UI/conversation (a, e, j, k), task lifecycle/automation (b, c, d, l, m, n), CLI/onboarding (f, g, h), permissions (i), agent-to-agent (o) — but the ticket doesn't commit to any grouping. The agent has to invent a taxonomy. Either specify the categories or explicitly delegate ("agent proposes a grouping, human approves in revise").
- **No "don't re-interview" instruction** (see Q2).
- **No audience stated.** The reports needed this (one flagged "the audience may not know Pylon"). Here the audience matters more: is this an internal note to Zach himself, a doc for the Relay team, or a spec that will seed future tickets? That changes how much each item needs explaining vs. just listing.
- **No structural exemplar.** Unlike the reports, there's no prior doc to mirror. If a structure is wanted, the ticket should sketch it (e.g. "one H2 per category, bullet per feature, each bullet = source tool + behavior + why it fits Relay").

## 5. Scope

**Borderline but defensible as one ticket.** It's a single deliverable (one Doc), which argues for one ticket. The 15 items are a list to write up, not 15 units of work. However, this is meaningfully **larger and fuzzier** than any sibling report: the reports answered 3 fixed questions about 1 tool from supplied prose; this synthesizes 15 cross-tool features into an invented structure with no template. The volume is fine for one ticket; the **open structural decision** (categorization) is the thing that could balloon it. As long as the structure question is resolved in `## Context` (or explicitly punted to the human-present `draft`/`revise` loop), it's one ticket's worth. It does not need splitting into per-tool tickets — that's what the `*-report` series already is.

## 6. Assumptions to question before launch

- **Should this reference the 8 `*-report` tasks as source material?** This is the biggest open question. The sibling directories (`conductor-report`, `paperclip-report`, etc.) contain rich blackboards and finished Google Docs evaluating each tool — and the `relay-additions` items are clearly distilled from those same experiences (e.g. item d "Automatic agent assignment (Paperclip)" maps directly to the paperclip-report strength "Agents get auto-assigned to open issues"). **A cold agent reading only this ticket would not know those reports exist or where to find them.** That said — the ticket's items a–o are already self-contained (each names the tool and the behavior), so the underlying research isn't strictly *needed* to write the doc. The reports are useful corroboration/detail, not a dependency. Recommendation: add a one-line pointer ("the per-tool detail behind these lives in the sibling `*-report` tasks and their Google Docs in the Relay Competition Tests folder") so the connection is discoverable, but don't make the doc a summary of the reports — it's a forward-looking wishlist, a genuinely different artifact.
- **Is "Relay Additions" going into the same Drive folder as the competition reports?** Unstated and non-obvious (see Q4). A feature wishlist is a different category from per-tool evaluations.
- **Are Dust / Superset / Cursor / Linear-Agent supposed to contribute features?** They're in the 8-tool header but absent from items a–o (see Q1). Confirm before draft, or the doc will list 8 tools and feature 4.
- **Is the a–o list final, or a working set?** Several items hedge ("I'm not sure it added value but...", "which are blocked by other dependencies?"). Treat the list as complete-as-is unless told otherwise, matching how the reports handled their trailing/uncertain answers.
- **`workflow: docs/create-google-doc` is a bare string** (not an inlined snapshot, no top-level `step:`). Per the repo's frontmatter discipline this is the *correct* draft form — let `relay launch` freeze the snapshot and assign `step:` together. Don't hand-add a `step:`. The completed siblings show the expanded post-launch shape, so the bare string will freeze fine.

---

**Bottom line:** Not launch-ready as-is, but close. The content (items a–o) is solid raw material. Two gaps will stall an agent: (1) **`## Context` is missing the Drive folder ID and a committed structure/categorization** — it currently asks itself a question instead of answering it; and (2) **no "don't re-interview" line**, so the workflow's `draft` step will re-litigate purpose/structure that's already decided. Also reconcile the 8-tools-named-vs-5-tools-featured mismatch and add a discoverability pointer to the sibling `*-report` tasks. Fix the `## Context` body (folder, structure, audience, no-re-interview) and the rest is a normal run of the proven workflow.
