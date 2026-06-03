---
name: docs/create-google-doc
description: Author a document as HTML, import-and-convert it into a native Google Doc via Drive (MCP), then loop human review and revision against the real Doc until the human signs off.
steps:
  - name: preflight
    assignee: agent
  - name: draft
    assignee: agent
  - name: revise
    assignee: agent
  - name: sign-off
    assignee: owner
---

## Why HTML, and why the Doc is the artifact

The document is built in **HTML for every case**, tables or not — one code
path. HTML expresses headings, lists, and tables cleanly, and importing it
sidesteps the pain of constructing tables through the Docs API directly.
Once imported, the **native Google Doc — not the HTML — is the artifact**
everything downstream operates on. Conversion can introduce minor rendering
drift, so the human always reviews the real imported Doc, never the
pre-import HTML.

## preflight

A connection gate. Before any content work, **verify the Google connection
(via MCP) is live** and confirm the server exposes Drive's HTML
upload-and-convert (the `Google_Drive` create/convert tools) — the entire
workflow depends on it. A quick read-only call (e.g. list recent Drive
files) is enough to prove the connection.

If the connection fails or the convert capability is missing, **stop here**:
write what failed to the blackboard and `relay panic` with a specific
reason. Do **not** bump forward into the content steps against a dead
connection. If the check passes, note it on the blackboard and
`relay bump <slug>`.

## draft

Produce the first Google Doc.

1. **Gather the request.** Get the human's input on what they want: purpose,
   content, structure, tone, any must-haves. (Interactive — the human is at
   the keyboard.)
2. **Clarify if needed.** If the ask is vague or underspecified, ask
   targeted questions and confirm scope *before* generating anything.
   Resolving ambiguity here is cheaper than discovering it after a full
   draft. Skip if the request is already clear.
3. **Generate the document as HTML** — headings, lists, and any tables, all
   in HTML.
4. **Import into Google Docs.** Upload the HTML and convert it to a native
   Google Doc via Drive's upload-and-convert.

Write the Doc link to the blackboard and finish the step with
`relay bump <slug> --message "draft Doc: <link>"`. If the import fails,
capture the error on the blackboard and `relay panic`.

## revise

Review-and-revise loop, run with the human present. This step owns the
iteration — relay bumps forward only, so the loop lives here rather than
as backward bumps.

1. **Hand off for review.** Give the human the actual Google Doc (the link),
   not the pre-import HTML, since conversion can drift.
2. **Capture requested changes.** If the human wants changes, record their
   specific feedback explicitly on the blackboard. This is the input to the
   revision — be precise.
3. **Revise.** Produce an updated version from **(current Doc + requested
   changes)**, not from the original request — this preserves prior edits
   and applies the new feedback on top rather than regenerating from
   scratch. Re-import the revised HTML the same way `draft` did, replacing
   the Doc's contents.
4. **Repeat** 1–3 as many times as needed.

When the human has no further changes, note the agreed-final Doc link on the
blackboard and `relay bump <slug>` into `sign-off`. (If the human walks away
mid-loop, leave the latest Doc link and current feedback on the blackboard
so a relaunched session can resume cleanly.)

## sign-off

Human's explicit final approval on the real Google Doc. The workflow is
complete only when the human signs off. On approval, `relay mark done
<slug>`. If the human surfaces more changes here instead of approving, that
belongs back in `revise` — `relay panic` with the requested changes so the
owner can rewind to the revision step.
