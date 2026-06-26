---
name: docs/create-google-doc
description: Author a document as HTML, upload it to Drive (MCP), have the human convert it to a native Google Doc, then loop human review and revision against the real Doc until the human signs off.
steps:
  - name: preflight
    assignee: agent
  - name: draft
    assignee: agent
  - name: revise
    assignee: agent
---

## Why HTML, and why the Doc is the artifact

The document is built in **HTML for every case**, tables or not — one code
path. HTML expresses headings, lists, and tables cleanly, and importing it
sidesteps the pain of constructing tables through the Docs API directly.
The import is split between the two of you: the **agent uploads the HTML
to Drive as `text/html`**, and the **human converts it** by opening the
file with "Open with → Google Docs" — the MCP server has no server-side
HTML→Doc conversion (see preflight). Once converted, the **native Google
Doc — not the HTML — is the artifact** everything downstream operates on.
Conversion can introduce minor rendering drift, so the human always
reviews the real converted Doc, never the pre-import HTML.

## preflight

A connection gate. Before any content work, **verify the Google connection
(via MCP) is live** and confirm the server exposes `Google_Drive
create_file` for uploading the HTML — the workflow depends on it. A quick
read-only call (e.g. list recent Drive files) is enough to prove the
connection.

Known contract of the MCP Drive server (learned on the conductor-report
task — do not rediscover it by trial uploads):

- `create_file` auto-converts **only** `text/plain` → Doc and
  `text/csv` → Sheet. **`text/html` is not converted** — it lands as a
  raw HTML file. That raw file is the expected, correct artifact for
  `draft`.
- Do **not** force `contentMimeType: application/vnd.google-apps.document`
  on HTML or docx content: you get a native Doc containing the literal
  markup (or binary garbage) as text.
- The HTML→Doc conversion is the **human's click** ("Open with → Google
  Docs" in Drive), not an API call. The tool description's conversion
  claims do not apply to HTML.
- That click does **not** convert in place: it leaves the HTML file
  untouched and creates a **new Doc with the same title** next to it —
  which looks like "nothing happened." One click is enough; verify by
  listing the folder for a new `application/vnd.google-apps.document`
  rather than clicking again (each click mints another duplicate Doc).
- The server has **no update or delete tools** — superseded files are
  trashed by the human.

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
4. **Upload the HTML to Drive** with `contentMimeType: text/html`, next
   to any sibling docs the ticket points at. No conversion happens here —
   the upload lands as a raw HTML file, and that's correct.
5. **Hand the file link to the human to convert.** The human opens it in
   Drive with "Open with → Google Docs", which performs the
   formatting-preserving HTML→Doc conversion. Wait for their confirmation
   and the resulting Doc link.

Write the resulting **Doc** link (not the HTML file link) to the
blackboard and finish the step with
`relay bump <slug> --message "draft Doc: <link>"`. If the upload errors
or the converted Doc comes out wrong, capture the details on the
blackboard and `relay panic`.

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
   scratch. Upload the revised HTML as a **new** file the same way `draft`
   did (the MCP server cannot replace a Doc's contents), and have the
   human convert it via "Open with → Google Docs". The new Doc becomes
   current; note superseded files/Docs on the blackboard for the human
   to trash.
4. **Repeat** 1–3 as many times as needed.

The loop ends with the human's explicit approval of the real Google Doc —
not merely an absence of further feedback. On approval, note the
agreed-final Doc link on the blackboard and `relay mark done <slug>`. (If
the human walks away mid-loop, leave the latest Doc link and current
feedback on the blackboard so a relaunched session can resume cleanly.)
