The blackboard is a notepad to be written to often as the human and agent works through a task.

## Preflight (2026-06-13) — PASSED

Google Drive MCP connection verified live:

- Read-only probe `list_recent_files` returned real Drive files (e.g. "Relay
  Marketing Plan", "Relay CRM") — connection is authenticated and working.
- `create_file` capability confirmed present:
  `mcp__claude_ai_Google_Drive__create_file`.
- Contract matches the conductor-report learnings: `text/html` is NOT
  auto-converted (lands as a raw HTML file — the correct `draft` artifact);
  only `text/plain`→Doc and `text/csv`→Sheet auto-convert. No update/delete
  tools; HTML→Doc is the human's "Open with → Google Docs" click.

Bumping forward to the content steps.

## Draft (2026-06-13)

Title confirmed by Zach: "Getting Started with Relay — Your First Five
Commands". Content per ticket spec — three-stage framing (set up → plan →
launch), one page, copy-pasteable example per command, Step 0 install
prerequisite. Zach chose: upload straight to Drive (no inline review first).

HTML draft uploaded as raw `text/html` (3425 bytes, lands unconverted, as
expected):

- HTML file: https://drive.google.com/file/d/1wrMTTH_RVtW1j1LppUtc2_TOnmjrtlIS/view?usp=drivesdk

### Correction — install/clone accuracy (Zach flagged)

Zach questioned the "no git clone" claim. Verified against source + README:

- **Repo setup has no user-facing clone** — `relay setup` → `relay init` →
  `_do_init` (`src/relay/commands/init.py:177`) scaffolds `relay-os/` from
  *packaged* templates (`copy_fresh_templates`, line 194). Internal temp
  `clone_upstream` (line 192) only vendors/pins the CLI copy; invisible to
  the user. So "no repo to clone" is correct for setup.
- **CLI install DOES require a clone today** — README Install section
  (`README.md:58`) says "Not yet on PyPI. Bootstrap from the source repo:"
  → `git clone https://github.com/FastJVM/relay && cd relay && pip install -e .`.
  So `pip install relay-os` (ticket-specified) doesn't work yet; the
  `pip install -U relay-os` the ticket cited is the *intended* path, and the
  README contradicts itself (`:191`, `:376` reference it as published).

Decisions: Step 0 → **hybrid** (lead `pip install relay-os`, then "not on
PyPI yet — bootstrap from source" with the git clone block). Stage 1 reworded
"no git clone" → "no repo to clone — `relay setup` scaffolds it for you".

### Corrected upload (supersedes first HTML)

- Old HTML (superseded — Zach to trash): 1wrMTTH_RVtW1j1LppUtc2_TOnmjrtlIS
- **Current HTML draft (3633 bytes):**
  https://drive.google.com/file/d/1BgJwR7V1zp5THQAqOi19U80TthuKq9eS/view?usp=drivesdk

### Correction 2 — `relay project` removed (Zach handed commit 7180288)

Zach pasted commit `7180288` ("relay setup: drop --project, let the interview
collect the goal"). **Note: that commit is NOT on this branch
(`relay-cli-commands`)** — verified via `git merge-base --is-ancestor`. On this
branch `relay project` is still registered (`cli.py:78`) and `relay setup` is
onboarding-only. The diff's branch is ahead; per Zach's direction the doc now
documents the **post-diff** behavior, so the doc is ahead of this branch.

User-facing delta applied (kept minimal — "only add what a new user needs"):

- **No `relay project` command.** Project planning moved into `relay setup`:
  run it again on an already-set-up repo → confirms ("Plan a new project
  now?") → short interview gathers the goal (and any vision doc) → ordered
  draft tickets. No `--project` seed flag.
- Stage 2 "whole project" branch rewritten from `relay project` → "run
  `relay setup` again"; closing line's `relay project` mention fixed.
- Left alone (not touched by this diff): `relay create`, `relay ticket`,
  `relay launch`, Step 0.

### Corrected upload v3 (supersedes v1 + v2)

- Superseded HTML (Zach to trash): 1wrMTTH_RVtW1j1LppUtc2_TOnmjrtlIS,
  1BgJwR7V1zp5THQAqOi19U80TthuKq9eS
- **Current HTML draft (3779 bytes):**
  https://drive.google.com/file/d/1th60EgE1UMGWUSsfvDcojRx0PwAShRjR/view?usp=drivesdk

### Sign-off (2026-06-14)

- `relay create` confirmed by Zach as the command the doc should use (vs.
  `relay draft`) — "what we will ultimately use." No further change.
- Zach reports the doc is converted and saved — "done and saved, good to go."

**Draft Doc (converted, final for this step):**
https://docs.google.com/document/d/1bZyF0D2_FJsf-NCCWm6rlewSkyOmVl6Q9QOLwtamnf0/edit

Bumping draft → revise.

## Revise loop (2026-06-14)

Entered revise step. Current Doc under review (the converted draft above):
https://docs.google.com/document/d/1bZyF0D2_FJsf-NCCWm6rlewSkyOmVl6Q9QOLwtamnf0/edit

Round 1: handed the Doc link to Zach. **Zach approved — "Looks good."** No
change requests. Loop ends here.

### Approved final (2026-06-14)

Agreed-final Google Doc (the deliverable):
https://docs.google.com/document/d/1bZyF0D2_FJsf-NCCWm6rlewSkyOmVl6Q9QOLwtamnf0/edit

HTML files to trash (superseded drafts):
1wrMTTH_RVtW1j1LppUtc2_TOnmjrtlIS, 1BgJwR7V1zp5THQAqOi19U80TthuKq9eS,
1th60EgE1UMGWUSsfvDcojRx0PwAShRjR (the converted Doc above is current).

Marking task done.
