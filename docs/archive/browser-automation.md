# Browser automation

> **History, archived 2026-10-13.** Coga removed its browser-automation battery: the
> `bootstrap/browser-automation` launcher, the bundled skills `browser/build-automation`,
> `browser/playwright` and `browser/dochub`, and the bundled contexts `browser/api-first` and
> `browser/dom-backed`. Their text is kept below (frontmatter dropped, headings demoted one
> level); the vendored Playwright skill and its scripts are in Git history only. Not
> instructions: a repo that still attaches one of these refs fails at composition and
> must drop the ref or keep its own local copy.

## bootstrap/browser-automation (launcher ticket)

### Description

Stateless entry point for turning a described browser task into a concrete
automation ticket. Run `coga launch bootstrap/browser-automation`, describe the
task when the agent asks, and let the `browser/build-automation` skill choose
the implementation path and matching workflow handoffs.

### Context

This bootstrap target is orchestration, not standing work. It has no status,
workflow, step, owner, blackboard, or audit lifecycle, and launching it does not
create a generic browser task. Only the concrete automation ticket created
after the task is understood becomes durable Coga work.

`browser/build-automation` owns routing and ticket creation.
`browser/playwright` is the separate lower-level browser runner and is attached
to the concrete ticket only when browser execution is actually required.

## context browser/api-first

*Require an explicit "why not the API?" answer before any browser automation ticket lands. Browser automation is the fallback for workflows that cannot be done via an API or script.*

## API-First For Browser Automation

Browser automation is brittle and expensive to maintain compared to API
or scripted integrations. Before creating a ticket that automates a
real workflow in a real SaaS UI, the ticket author must check whether
an API can do the same job and document the answer.

### Rule

Tickets that propose browser automation against a real site must, in
the ticket body or an attached note, answer all of these:

- Does the target SaaS expose an API (REST, GraphQL, SDK) that covers
  this workflow? Yes / No / Partial.
- If yes or partial: which endpoints, and what specifically is missing
  that forces a browser-based approach?
- If no: link or note the docs page checked, so the next person doesn't
  redo the search.

If the API can do the workflow, write the ticket as a script-or-SDK
ticket, not a browser-automation ticket.

If the API covers part of the workflow, prefer a hybrid where the
script does the API part and a browser pass handles only the
UI-only steps.

### When this context applies

Attach `browser/api-first` to any ticket whose workflow would mutate
or extract data from a real third-party SaaS UI. Read-only DOM
reconnaissance tickets (purely investigative, no mutation, no
data export) may skip it but the API question should still appear
in the blackboard.

### How to apply

- Author: do the API check before the ticket leaves `draft`.
- Reviewer: if the API question is not answered, push back before
  activation rather than after work begins.
- Agent picking up the ticket: if the API answer is missing, surface
  it as a question to the human before starting browser work.

## context browser/dom-backed

*DOM-backed browser automation standard for real SaaS workflows. Attach to browser tasks that should use Playwright snapshots, accessibility-tree refs, and DOM selectors only.*

## DOM-Backed Browser Automation

Use DOM-backed automation as the only browser-control method for tickets
that attach this context.

Two Playwright runners are available: the terminal-driven CLI and the
Playwright MCP server.

**Default to the CLI runner.** It is the one this repo actually equips —
the `browser/playwright` skill ships a wrapper script and a command
reference, and `browser/dochub` is built on top of it. Use MCP when the
ticket names it, or when the CLI genuinely cannot reach the surface the
task needs.

This is a default, not a verdict: no runner has been declared the
permanent primary, and the choice is still open. Treat the CLI as where
you start unless you have a task-specific reason to start elsewhere.

Whichever you pick, pick it once: one runner per task, no switching
mid-task, and the other runner is never an in-run fallback.

### Allowed control surfaces

- Playwright accessibility snapshot output and its fresh element refs, whether surfaced through MCP or CLI.
- Playwright locator behavior when exposed by the selected runner.
- DOM and accessibility-tree inspection through `eval` when it supports diagnosis or structured extraction.
- Screenshots, traces, console output, and network logs as evidence and debugging artifacts.

Screenshots are not a targeting mechanism. Do not use visual recognition, set-of-mark overlays, OCR, coordinate clicks, or mouse-position guessing for normal task execution.

### Known DOM gaps

Some browser UI renders outside the accessibility tree and is not reachable by Playwright refs. Known examples:

- **Chrome's PDF viewer toolbar.** When a link opens a PDF inline (rather than triggering a native download), the toolbar — including the download button — is browser chrome, not DOM. A `snapshot` of the PDF tab returns an empty tree.
- **Native browser dialogs** (`alert`, `confirm`, `beforeunload`) — handled via the runner's dialog API, not refs.

When the final action is behind one of these gaps, DOM-backed alone cannot complete it. DOM-pure paths out:

- For inline PDFs: read `location.href` of the new tab (via `eval`), then HTTP-fetch the URL. Click is DOM-driven; save is HTTP. The boundary is clean and logged.
- For dialogs: use the runner's dialog handler explicitly.

Set-of-mark (SOM) is the candidate fallback for native-chrome UI because the button is visually present. SOM is not used as an in-run fallback; if a task needs SOM, that's a separate ticket with its own context.

### Standard loop

1. Open the target page in the selected Playwright runner, using a named session/profile when the runner supports it.
2. Take a fresh snapshot.
3. Identify the actionable DOM-backed ref or locator. Trust the action label the DOM exposes (e.g. `link "View"` is not `link "Download"`). If the label disagrees with the plan, the plan is wrong.
4. If the automation cannot continue using DOM-backed evidence, stop and fail loudly.
5. Perform the action by ref or locator.
6. Re-snapshot after navigation, row removal, modal open/close, tab switch, or any substantial DOM change.
7. Record the artifact paths and the exact decision rule in the task blackboard.

### Failure Process

If the DOM-backed method cannot finish the automation, fail loudly.
Do not predict or enumerate failure cases up front, and do not switch
to another automation method inside a DOM-only run.

When failing, write a short blocker entry to the blackboard region of `ticket.md` with:

- current URL
- latest snapshot path
- screenshot or trace path if useful
- intended action
- the exact ref or locator the automation expected to act on (so the
  human reviewing the blocker can verify the fix targets the same
  element after a re-snapshot, since refs are per-snapshot and a new
  snapshot will assign new ones)
- one-sentence reason the automation could not continue
- the smallest next step needed to proceed

### Restart Process

When the human resolves a blocker and restarts the automation:

- Take a fresh snapshot before any ref-based action. Refs from the
  pre-failure snapshot are stale and must not be reused.
- Re-identify the intended element from the new snapshot using the
  ref/locator description recorded in the blocker entry.
- If the element no longer matches the description, fail loudly again
  rather than acting on a guess.

### Artifacts

Minimum per task:

- Screenshot before the first action.
- Screenshot after the last action (or after the failure point).
- One-line failure reason in the blocker entry, if the run failed.

When a ref-based action fires, also save the snapshot text that
drove the decision (e.g. `artifacts/snap-NN.txt`) alongside the
screenshot. The snapshot is what tells a reviewer *why* the agent
picked that ref — screenshots only show the visual outcome and are
the wrong tool for diagnosing a wrong-element click.

Tickets may require additional captures (initial state, post-mutation
state, final state); follow the ticket's acceptance criteria when it
asks for more than the minimum.

### Per-Site Learning

Each real-site task should leave behind reusable observations:

- stable entry URLs and account or entity identifiers
- login and profile-persistence behavior
- DOM signatures for safe actions
- DOM signatures for manual or human-review states
- failure modes and how they should surface
- whether the selected runner was easier or harder than MCP/CLI alternatives for setup, debugging, portability, and future robustness

Promote durable findings into this context or a site-specific skill only after the task has been exercised against the real workflow. Runner comparisons (CLI vs MCP) belong in the task blackboard as an observation, not in every ticket's plan as an open question — the default above already tells you where to start. If a comparison ever turns out to be decisive, change the default in this context in the same PR rather than leaving the decision pending.

## skill browser/build-automation

*Turn a described browser task into a concrete automation ticket by checking for an API first, matching workflow handoffs to the requested action, attaching browser execution capability only when needed, and launching the resulting work.*

## Build a browser automation

Use this skill as the orchestration layer between a human's description of a
browser task and the concrete Coga ticket that will implement and run it. The
skill does not drive the browser itself; `browser/playwright` is the separate
lower-level execution skill.

The bootstrap launcher carrying this skill is stateless. Do all four phases in
this session, and create durable state only for the concrete automation the
human actually requested. Do not create or preserve a generic router ticket.

### 1. Understand the task

Ask the human to describe the browser task if they have not done so yet. Restate
it as:

- a concrete goal;
- a target site, URL, or system; and
- an explicit success check: what will be observably true when the task is done.

Ask one clarifying question only when the task is genuinely ambiguous.
Otherwise, proceed.

### 2. Choose the approach

Apply the attached `browser/api-first` context. Decide whether an API, SDK, or
ordinary script can perform the task without browser automation.

- If an API or script covers the task, create the concrete ticket for that
  approach and do not attach browser-specific context or skills.
- If coverage is partial, keep the API-backed portion and use a browser only
  for the UI-only remainder.
- If no practical API path exists, choose DOM-backed browser execution and
  attach `browser/dom-backed` to the concrete ticket.

This is a routing decision, not a deep probe. The concrete ticket verifies the
target, credentials, scopes, and feasibility before it acts.

### 3. Choose the workflow

Inspect the available workflows and pick the one whose assignee handoffs match
the requested end action:

- read-only, reversible, or idempotent work → the lightest all-agent workflow
  that fits;
- an irreversible or outward-facing action such as send, submit, pay, post, or
  delete → a workflow with a human or owner gate before that action;
- an action the machine cannot safely perform → a workflow where the human
  performs it and the agent provides read-only support.

Bind to a real workflow ref, not a category label. If none has the right
handoff shape, say so and let the human decide whether the repo needs a new
workflow.

### 4. Create and launch the concrete ticket

Create one ticket named for the actual requested automation and bind it to the
chosen workflow's real ref. Write the goal, target, success check, API-first
decision, and why the workflow's gates fit the requested action into its
`## Description` and `## Context` sections.

Attach browser capability only when the agent will drive a browser:

- When an agent will drive the browser, attach context `browser/dom-backed` and
  ticket-level skill `browser/playwright`.
- For an API/script solution, or a workflow where the human performs the browser
  action, attach neither; the former does not need a browser, and in the latter
  the human drives it while the agent stays read-only.

Browser-specific context and the runner belong on the concrete ticket, selected
here per task rather than baked into a domain-generic workflow.

Launch the concrete ticket after its body and frontmatter are complete. From
that point, its workflow owns the operator handoffs. Put prerequisite checks,
dry runs, and outcome verification in the ticket body when the selected
workflow does not already specify them.

## skill browser/dochub

*"Use when automating DocHub (dochub.com) e-sign or PDF-form workflows from the terminal: placing text annotations on a document, placing a signature field via record-and-replay coordinates, assigning a field to a signer, and sending a sign request. Builds on the browser/playwright CLI substrate."*

## DocHub Automation Skill

Automate DocHub document preparation and sending. This skill is the
site-specific layer on top of two substrates:

- **`browser/playwright`** — the terminal-driven Playwright CLI (how you open,
  snapshot, click, screenshot). Read it first; everything here assumes you are
  driving DocHub through that CLI.
- **`browser/dom-backed`** — the DOM-backed control standard context
  (snapshot → ref → act, fail loud, capture artifacts). This is a Coga
  **context** (ref `browser/dom-backed`), not a loadable skill —
  attach/read it as a context by ref. It resolves from
  `<contexts-dir>/browser/dom-backed/` (the contexts root is `coga/contexts/`
  unless `[layout] contexts` in `coga.toml` relocates it) when one exists and
  otherwise from the installed package's bundled `bootstrap/contexts/` copy;
  a freshly initialized repo has no local copy, so do not look for it at a
  repo path.
  DocHub follows it, with **one sanctioned coordinate exception** documented
  under Technique B.

DocHub is the chosen e-sign target (v7). Use this skill when a ticket attaches
it for placing annotations, placing a signature, and sending for signature.

### Why the browser, not the API

Tickets using this workflow should attach `browser/api-first` and cite this
dated check as their API answer.

**Answer (checked 2026-09-16): No usable public API found for this workflow.**
The check found no documented endpoints for document upload, annotation or
signature-field placement, signer assignment, or sending sign requests.
Continue using the browser for those operations. This is a finding from the
sources below, not proof that DocHub has no API of any kind.

**Sources checked on 2026-09-16:**

- DocHub Support's [“Automatically Filling Forms via API” answer](https://support-backend.usrsprt.com/support/dochub/community-forum/question/c91a6950-fa12-401f-93e5-cbc88a6db133)
  (public help-center thread record, answered 2024-04-11) says the API was
  still in development and directs users to the browser. Its age limits what
  it establishes about current availability.
- The [help center](https://help.dochub.com/) API search, [pricing](https://dochub.com/pricing),
  and [integrations](https://www.dochub.com/en/integrations) did not yield a
  public API reference for this workflow. Search hits about Google APIs and
  SSO do not document these document-preparation and e-sign operations.
- The [PandaDoc API pricing comparison](https://www.dochub.com/compare/dochub-vs-pandadocs-api-pricing)
  claims a DocHub REST API, SDKs, an OpenAPI specification, and a sandbox plan,
  but supplies no link to their reference or developer dashboard. This
  conflicting claim alone is insufficient to build an API integration.

Keep the scriptable part local: pre-fill AcroForm text, radio, and checkbox
values with pypdf before upload, as described below. The browser then handles
the remaining document preparation and sending.

Re-check for a different workflow, new API documentation or access, or when
this check is more than a year old. If documented endpoints become available,
update this section and use them for the operations they cover. Revisit
Technique B if field placement can move to the API.

### Before you start: pre-fill the PDF (AcroForm)

If the document is a fillable AcroForm PDF, set its **text / radio / checkbox**
values *before* uploading to DocHub. DocHub's in-browser preparation mode
cannot reliably pre-fill radios and checkboxes; pre-filling with pypdf bypasses
that. The browser flow below then only adds the **signature** and **sends** — it
is not where you fill form fields.

> **GAP — recipe unavailable.** The concrete pypdf pre-fill recipe was only ever
> held in an external agent memory store (`project_acroform_prefill_pattern`)
> that this repo does not have, and its content is lost. Coga keeps state
> legible and in-repo, so there is no pointer to follow. Treat this step as
> **not yet documented**: derive the pre-fill with pypdf yourself for the
> document at hand, and write the working recipe back into this file (or a
> sibling `references/` note) so the next run has it.

### Technique A — Text annotations (fully agent-driven)

Placing a short text mark on a document (e.g. `D/W` or `KP` on a DE-9C) is
fully DOM-backed — no coordinates needed.

1. Open the editor in the Playwright CLI (`--headed` for any interactive or
   first-time flow).
2. Take a fresh snapshot.
3. Locate the text/annotation tool in the toolbar by its DOM ref, activate it,
   then place the text at the target location. Trust the label the DOM exposes;
   if it disagrees with the plan, the plan is wrong (per dom-backed).
4. Re-snapshot after the toolbar mode changes or the annotation lands.
5. Verify the text is present in the document, then screenshot.

This is the reliable, repeatable case: the agent does the whole thing with no
human in the loop and no coordinates.

### Technique B — Signature placement via record-and-replay

A signature field sits on a **rendered PDF page**, which has no element ref —
so DOM-backed alone cannot target it. The sanctioned path is to record the
placement once with a human, then replay it by coordinate on later runs of the
same document.

#### Why coordinates are allowed here

Coordinate placement is the **one** sanctioned exception to dom-backed's
no-coordinate rule, because the signature field on a rendered PDF page has no
accessibility ref to target. A **recorded** coordinate — measured from a real
human placement on a known document — is per-site learning, not a blind visual
guess. SOM, OCR, and mouse-position guessing are still out.

#### The placement mechanic (non-negotiable)

Position on DocHub is set by **where the field is click-placed** — DocHub
anchors the field's **bottom edge to the click point**. Consequences:

- Use a **real** `page.mouse.click` (or click/drag) at the measured point.
  Synthetic `el.click()` no-ops on DocHub's placement controls.
- **Never** set position via `style.transform`. It is cosmetic only and
  **reverts on send** — the field snaps back to its model position and your
  visual placement is lost.

> **GAP — supporting detail unavailable.** The longer write-up of this failure
> mode lived in an external memory store (`project_dochub_signature_placement`)
> this repo does not have, and its content is lost. The rule above and the
> dry-run guardrail below are the whole of what survives; there is nothing
> further to look up.

#### Record (first run — human in the loop)

1. Human click-places the signature field once on the target page.
2. Agent measures the placed field **relative to the rendered page**, not the
   viewport: `x_pct`, `y_pct`, `w_pct`, `h_pct` as percentages of the rendered
   page box, plus the **click-anchor y** (the y of the field *bottom*, since
   that is what DocHub anchors to the click).
3. Persist to the coords file (see convention below).

#### Replay (later runs — fully agent-driven)

1. Open the same document / template in the editor; take a fresh snapshot.
2. Convert the recorded percentages back to page-box pixels using the current
   rendered page size.
3. Place the signature field with a real `page.mouse.click` at the recorded
   click-anchor point. No human needed.

### Dry-run before trust (guardrail)

Never send on an unverified placement. After a replay places the field:

1. **Reload the editor** and accept the `beforeunload` dialog (via the runner's
   dialog handler — see dom-backed "Known DOM gaps").
2. Re-measure the field. If it survives the reload at the recorded position, it
   is committed to the document model and will survive send. If it moved or
   disappeared, the placement did not take — fail loud and do not send.

This catches the `style.transform` cosmetic-only failure mode before it reaches
the signer.

### Assign-to-signer gotcha

A signature field placed through the **Manage Fields** detour can land
orphaned — unassigned to any signer — which leaves **Send Request disabled**.
To enable sending: click the field, then choose **"Assign to '<signer>'"**.
(Precedent: the Huntington lease e-sign flow.) Re-check that Send Request is
enabled before attempting to send.

### Coords record convention

Persist recorded placements in-repo so they travel with the skill and are
versioned:

```
coga/skills/browser/dochub/coords/<template>.json
```

```json
{
  "page": 17,
  "x_pct": 6.7,
  "y_pct": 3.0,
  "w_pct": 24.5,
  "h_pct": 3.8,
  "click_anchor_y_pct": 6.8
}
```

`page` is 1-based. All `*_pct` values are percentages of the rendered page box.
`click_anchor_y_pct` is the y of the field bottom (the click point), distinct
from `y_pct` (the field top). New placements go in the in-repo coords file.

> **GAP — precedent values unavailable.** The recorded Huntington-lease
> coordinates lived in an external memory store
> (`project_huntington_lease_esign_coords`) this repo does not have, and their
> content is lost. The JSON above is a **shape example, not real recorded
> data** — do not replay it. Any document, Huntington included, needs its
> placement re-recorded (Technique B) into
> `coga/skills/browser/dochub/coords/<template>.json`.

### Failure & artifacts

Follow `browser/dom-backed` for failure handling (fail loud, blocker entry with
URL / snapshot path / intended ref). Minimum captures per document:

- Screenshot before the first placement action.
- Screenshot after the post-reload re-measure (the dry-run verification).
- The recorded coords file (Technique B).

For annotations (Technique A), also save the snapshot text that drove the ref
choice, per dom-backed's artifact rule.
