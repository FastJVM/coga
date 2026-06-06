---
title: doc-create-workflow
status: done
mode: interactive
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow: null
---

## Description

Create a workflow (that lives in relay-os/workflows) as a .md file that explains a workflow for using relay to create a Google Doc

Workflow: Create a Google Doc
Precondition — Google connection. Verify the Google connection (via MCP) is live before starting. Confirm the server exposes Drive's HTML upload-and-convert, since the document creation step depends on it. If the connection fails, stop here and surface the error — don't proceed into the content steps.
1. Gather the request. Get the human's input on what they want in the document: purpose, content, structure, tone, any must-haves.
2. Clarify if needed. If the ask is vague or underspecified, ask targeted questions and confirm scope before generating anything. Resolving ambiguity here is cheaper than discovering it after a full draft. Skip if the request is already clear.
3. Generate the document as HTML. Build the document in HTML regardless of whether it contains tables — one code path for everything. HTML handles headings, lists, and tables cleanly, and importing it avoids the pain of constructing tables through the Docs API directly.
4. Import into Google Docs. Upload the HTML and convert it to a native Google Doc via Drive's upload-and-convert. The Google Doc — not the HTML — is the artifact everything downstream operates on.
5. Hand off for review. Give the human the actual Google Doc to review. Because conversion can introduce minor rendering drift, they need to see the real imported result, not the pre-import HTML.
6. Capture requested changes. If the human wants changes, record their specific feedback explicitly. This becomes input to the next step.
7. Revise. Produce an updated version from (current document + requested changes) — not from the original request. This preserves prior edits and applies the new feedback on top, rather than regenerating from scratch. Re-import the revised HTML (return to step 4).
8. Repeat until sign-off. Loop steps 5–7 as many times as needed.
9. Done. The workflow is complete when the human signs off on the document.

## Context

