The blackboard is a notepad to be written to often as the human and agent works through a task.

## Preflight (2026-06-03)

Google connection check: **PASS**.

- Read-only probe `Google_Drive list_recent_files` succeeded — returned 3
  recent docs (account `zach@fastjvm.com`), including the prior "Dust
  Report" doc, so the MCP connection is live.
- HTML upload-and-convert capability confirmed: the server exposes
  `Google_Drive create_file`, which accepts `textContent` +
  `contentMimeType` and converts uploads to
  `application/vnd.google-apps.document` (conversion on by default;
  `disableConversionToGoogleType` exists to opt out). This is the
  create/convert path the workflow depends on.

Useful for later steps: the existing "Dust Report" doc
(id `1NizIofbDCDzKuMyds9UaAU5BPr1rylUexJ1qQEFWcvs`) lives in parent folder
`0AI38XlSataDrUk9PVA` — likely the right `parentId` for the Conductor
report so the two land side by side.

## Draft (2026-06-03)

**Correction to the preflight note above:** the MCP server does **not**
convert HTML server-side. Its auto-convert map covers only
`text/plain` → Doc and `text/csv` → Sheet. Every agent-side attempt to
force conversion failed:

- `contentMimeType: text/html` → raw HTML file in Drive (no conversion).
- HTML (text or base64) + `contentMimeType: application/vnd.google-apps.document`
  → native Doc containing the **literal markup as plain text**.
- docx upload as docx → stays `.docx` (not in the conversion map).
- docx bytes + Doc target type → Doc full of binary garbage.

**The working flow (per Zach):** the agent uploads the HTML as
`text/html`; the **human opens the file in Drive with "Open with →
Google Docs"** — that click performs the real, formatting-preserving
HTML→Doc conversion. The agent then records the resulting Doc link.
Same issue reportedly hit the dust-report task. Workflow file
`relay-os/workflows/docs/create-google-doc.md` is being updated on this
branch to encode this.

**Content decisions:** report mirrors the Dust Report's structure
(intro verdict, three numbered sections, closing thought, bolded bullet
leads) — Zach picked this over a plain Q&A layout. Key facts: 2 hours
end to end (vs Dust's 3); 2x faster than Dust through the Playwright
selector work; strengths cluster on git ergonomics (in-UI PRs, Opus
access, merge awareness, auto branch/worktree, built-in terminal);
weaknesses share one root — no robust workflows, less granular than
Dust, testing pushed to the back end.

**File inventory** (all titled "Conductor Report", parent
`0AI38XlSataDrUk9PVA`):

- ✅ KEEPER (draft HTML, awaiting human open-with-Docs):
  `1QXZxzK5bgFY_hteCP9SVjOB13CrkbTbj`
- 🗑 trash: `1XnHrEOYESlAu1wZwtKqQzZDqTvUGSmYO` (dup HTML),
  `1iZkYoOVRpt0PyVyx0oXlc5wO6fie5_cDdbqimmwFqN0` (literal-markup Doc),
  `17KyHuoHEVyeyaZBvYV70NeDCwFYe8xhZsRNR--M4A8w` (literal-markup Doc),
  `1j9KrEgAyY6zt0MuMNqANC6kAEeLZu2ic` (.docx),
  `169VDYKDxTd4MMKyWiLfbwZr9LEuMtwXHItW_vuxyqwg` (garbage Doc).
  MCP server has no delete tool — human trashes these.

Local copy of the draft HTML: `/tmp/conductor-report.html` (also
`/tmp/conductor-report.docx`).

## Conversion resolved (2026-06-03)

Zach's "Open with → Google Docs" clicks **were converting** — the click
creates a *new* Doc with the same title and leaves the HTML file in
place, so it looked like nothing happened. Six identical Docs got minted
before we spotted it. Verified the newest one renders correctly
(headings, bullets, bold leads — mirrors the Dust Report).

- ✅ **Draft Doc (the artifact):**
  https://docs.google.com/document/d/1cij60SgQAqeKxNt8QOFJ9R_sChlPS0OayMaOel7wZV4/edit
- 🗑 To trash: 5 duplicate Docs (`1ckcWsbsXy6PgNkT5m8nEsyCKQ79mpiks9DT0dRoW_Qk`,
  `1KBV8nUvabBzT-AD1n1e6zamHV1nSRdOeAFN2eSeHcbs`,
  `1-3DJeJQxD9R_A-6VvpS7y6-fl-or93CkwS85rXI4xbg`,
  `1iqJXeB1HoVNQplHfOGlxJarFXWZ_146FxN2GBWtqQ9E`,
  `1QgKfX30zffvTvuwxLKKHE570d9ccmCzw02U9DVgBm08`) and both HTML files
  (`1QXZxzK5bgFY_hteCP9SVjOB13CrkbTbj`,
  `1XnHrEOYESlAu1wZwtKqQzZDqTvUGSmYO`).
- The four earlier strays (literal-markup Docs, docx, garbage Doc) are
  already trashed.

Workflow file updated with the not-in-place conversion gotcha
(preflight contract block).

## Revise (2026-06-03)

Zach reviewed the draft Doc and approved it **as-is** — zero revision
rounds needed.

- ✅ **Agreed-final Doc:**
  https://docs.google.com/document/d/1cij60SgQAqeKxNt8QOFJ9R_sChlPS0OayMaOel7wZV4/edit
- Outstanding cleanup (human, no agent delete tool): the 5 duplicate
  Docs and 2 HTML files listed in the "Conversion resolved" section
  above are still pending trash.

Bumping into `sign-off`.

## Sign-off (2026-06-03)

Zach gave explicit final approval on the converted Google Doc in this
session ("I sign off on the document").

- ✅ **Signed-off final Doc:**
  https://docs.google.com/document/d/1cij60SgQAqeKxNt8QOFJ9R_sChlPS0OayMaOel7wZV4/edit
- Remaining human cleanup (unchanged): trash the 5 duplicate Docs and
  2 HTML files listed under "Conversion resolved" above.

Marking the task done.
