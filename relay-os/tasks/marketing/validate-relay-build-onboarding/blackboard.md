# validate-relay-build-onboarding — blackboard

## Step 1: prepare-fixtures — COMPLETE (pending bump)

Parent dir for all throwaway fixtures: `/Users/zach2179/Desktop/relay-build-fixtures/`
**Delete the whole dir when the dry run is done.**

### Design: single known target, varied repo state
All three legs use **GoldRatio** (`~/Desktop/side-projects/stock-screener`) as the
target — a finished Streamlit value-investing screener Zach knows cold. Holding the
target constant lets Zach score every leg against the same known "done" state.
(Earlier synthetic "Pulse" repo was scrapped: with a fabricated repo Zach has no
real answer to "what do you want to build," so intent/recall scores would be hollow.
barrel-to-busbar was also considered but dropped — Zach doesn't know its "done.")

### Fixtures
- **empty** — `/Users/zach2179/Desktop/relay-build-fixtures/empty`
  Fresh `relay init`, no repo content. The "GoldRatio-ness" comes from Zach's
  *spoken* intent during the dry run. Tests: does question-only head toward the
  real GoldRatio?
- **filled** (no CLAUDE.md) — `/Users/zach2179/Desktop/relay-build-fixtures/filled`
  GoldRatio content, no agent guide. Tests: what does the scan recover?
- **filled-claude** (with CLAUDE.md) — `/Users/zach2179/Desktop/relay-build-fixtures/filled-claude`
  Same GoldRatio content + an **authored** representative `CLAUDE.md` (repo has
  none of its own — see note). Tests: does a guide add recall over the scan?

All three: `relay.local.toml` → `user = "zach"`, `[notification.slack] enabled = false`.
Starter tasks (`relay-setup`, `browser-automation`) removed; only `_template` remains.
Auto-generated root CLAUDE.md/AGENTS.md stripped (filled-claude keeps the authored one).
`relay status` = "(no tasks)" in all three. `relay draft` smoke-tested in `filled`:
works offline, git sync skipped (non-git), no Slack post.

### Copy fidelity (GoldRatio → filled / filled-claude)
Copied via rsync, ~1.7MB each. **Excluded:** `.env` (live API keys — FMP/FRED/EIA/
TRADIER/ANTHROPIC), `secrets.toml`, `.claude/`, `__pycache__`, and the heavy
`data/cache|transcripts|outputs` (the 784MB). Kept: `streamlit_app.py` (312KB
monolith), `src/` (clients + analyzers), `config/universes` (143 CSVs), `scripts/`,
`README.md`, `IMPROVEMENTS.md` (Zach's real roadmap w/ a "Suggested Build Order" —
useful ground truth for scoring direction), small `data/` artifacts (screens,
portfolio.json, watchlist.json).

### NOTE for Zach — sanity-check the authored CLAUDE.md
GoldRatio has no CLAUDE.md, so the filled-claude leg uses one I wrote from the real
README/IMPROVEMENTS/plan.md/src structure. The ±CLAUDE.md comparison is only valid
if it's representative. File: `filled-claude/CLAUDE.md`. Verify before scoring.

### Findings during fixture setup (durable)
- **$SLACK_WEBHOOK_URL is set in this env.** Without `[notification.slack]
  enabled = false`, the fixtures' create/launch/bump would post to the REAL team
  channel. The slack-disable step is load-bearing, not just an offline nicety.
- **`relay init` ships starter tasks** (`relay-setup` active, `browser-automation`
  draft) + `_template` (the scaffold `relay create` copies — must NOT be deleted).
  Cleared the two starter tasks for a clean dry-run baseline.
- **`relay init` auto-writes root CLAUDE.md + AGENTS.md** (relay orientation, not
  repo-describing). Stripped to keep the ±CLAUDE.md axis clean.
- **`gh skill` warnings during init are a pre-existing machine issue** (installed
  `gh` lacks the `skill` subcommand). Init completes exit=0; only optional managed
  skills are skipped — irrelevant to this dry run.
- **relay tolerates non-git fixtures**: git sync is skipped, no error.

## Step 2: dry-run-and-score — NOT STARTED
For each fixture (empty → filled → filled-claude): role-play `relay build`, ask
"What do you want to build?", follow-up chat, scan, draft a short spec, **create a
3–6 ticket starter batch in that fixture**, invite Zach to launch one or two, then
record his rubric answers under `## Scores — <fixture>`.
