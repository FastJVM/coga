---
name: "dochub"
description: "Use when automating DocHub (dochub.com) e-sign or PDF-form workflows from the terminal: placing text annotations on a document, placing a signature field via record-and-replay coordinates, assigning a field to a signer, and sending a sign request. Builds on the browser/playwright CLI substrate."
---

# DocHub Automation Skill

Automate DocHub document preparation and sending. This skill is the
site-specific layer on top of two substrates:

- **`browser/playwright`** — the terminal-driven Playwright CLI (how you open,
  snapshot, click, screenshot). Read it first; everything here assumes you are
  driving DocHub through that CLI.
- **`browser/dom-backed`** — the DOM-backed control standard context
  (snapshot → ref → act, fail loud, capture artifacts). This is a Relay
  **context** (`relay-os/contexts/browser/dom-backed/`), not a loadable
  skill — attach/read it as a context. DocHub follows it, with **one
  sanctioned coordinate exception** documented under Technique B.

DocHub is the chosen e-sign target (v7). Use this skill when a ticket attaches
it for placing annotations, placing a signature, and sending for signature.

## Before you start: pre-fill the PDF (AcroForm)

If the document is a fillable AcroForm PDF, set its **text / radio / checkbox**
values *before* uploading to DocHub. DocHub's in-browser preparation mode
cannot reliably pre-fill radios and checkboxes; pre-filling with pypdf bypasses
that. See memory `project_acroform_prefill_pattern` for the recipe. The browser
flow below then only adds the **signature** and **sends** — it is not where you
fill form fields.

## Technique A — Text annotations (fully agent-driven)

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

## Technique B — Signature placement via record-and-replay

A signature field sits on a **rendered PDF page**, which has no element ref —
so DOM-backed alone cannot target it. The sanctioned path is to record the
placement once with a human, then replay it by coordinate on later runs of the
same document.

### Why coordinates are allowed here

Coordinate placement is the **one** sanctioned exception to dom-backed's
no-coordinate rule, because the signature field on a rendered PDF page has no
accessibility ref to target. A **recorded** coordinate — measured from a real
human placement on a known document — is per-site learning, not a blind visual
guess. SOM, OCR, and mouse-position guessing are still out.

### The placement mechanic (non-negotiable)

Position on DocHub is set by **where the field is click-placed** — DocHub
anchors the field's **bottom edge to the click point**. Consequences:

- Use a **real** `page.mouse.click` (or click/drag) at the measured point.
  Synthetic `el.click()` no-ops on DocHub's placement controls.
- **Never** set position via `style.transform`. It is cosmetic only and
  **reverts on send** — the field snaps back to its model position and your
  visual placement is lost. See memory `project_dochub_signature_placement`.

### Record (first run — human in the loop)

1. Human click-places the signature field once on the target page.
2. Agent measures the placed field **relative to the rendered page**, not the
   viewport: `x_pct`, `y_pct`, `w_pct`, `h_pct` as percentages of the rendered
   page box, plus the **click-anchor y** (the y of the field *bottom*, since
   that is what DocHub anchors to the click).
3. Persist to the coords file (see convention below).

### Replay (later runs — fully agent-driven)

1. Open the same document / template in the editor; take a fresh snapshot.
2. Convert the recorded percentages back to page-box pixels using the current
   rendered page size.
3. Place the signature field with a real `page.mouse.click` at the recorded
   click-anchor point. No human needed.

## Dry-run before trust (guardrail)

Never send on an unverified placement. After a replay places the field:

1. **Reload the editor** and accept the `beforeunload` dialog (via the runner's
   dialog handler — see dom-backed "Known DOM gaps").
2. Re-measure the field. If it survives the reload at the recorded position, it
   is committed to the document model and will survive send. If it moved or
   disappeared, the placement did not take — fail loud and do not send.

This catches the `style.transform` cosmetic-only failure mode before it reaches
the signer.

## Assign-to-signer gotcha

A signature field placed through the **Manage Fields** detour can land
orphaned — unassigned to any signer — which leaves **Send Request disabled**.
To enable sending: click the field, then choose **"Assign to '<signer>'"**.
(Precedent: the Huntington lease e-sign flow.) Re-check that Send Request is
enabled before attempting to send.

## Coords record convention

Persist recorded placements in-repo so they travel with the skill and are
versioned:

```
relay-os/skills/browser/dochub/coords/<template>.json
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
from `y_pct` (the field top). The legacy precedent for these exact Huntington
values lives in memory `project_huntington_lease_esign_coords`; new placements
go in the in-repo coords file, not memory.

## Failure & artifacts

Follow `browser/dom-backed` for failure handling (fail loud, blocker entry with
URL / snapshot path / intended ref). Minimum captures per document:

- Screenshot before the first placement action.
- Screenshot after the post-reload re-measure (the dry-run verification).
- The recorded coords file (Technique B).

For annotations (Technique A), also save the snapshot text that drove the ref
choice, per dom-backed's artifact rule.
