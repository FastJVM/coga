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

## Step 2: dry-run-and-score — IN PROGRESS
For each fixture (empty → filled → filled-claude): role-play `relay build`, ask
"What do you want to build?", follow-up chat, scan, draft a short spec, **create a
3–6 ticket starter batch in that fixture**, invite Zach to launch one or two, then
record his rubric answers under `## Scores — <fixture>`.

### Leg 1 — empty (words-only) — batch created, awaiting score

**Q: "What do you want to build?" — Zach's intent (verbatim):**
> Goldratio is a private-use value investing research tool. My vision is that it
> will be connected (and pull in data) from both free and paid sources (ones that
> can provide me with company information, financial ratios) of companies separated
> by industry. I'd like there to be a search tool that searches entire industries,
> putting financial ratios front and center, and also a search tool where you can
> input single-tickers to look more deeply into an individual company. My vision
> includes having the individual search tool to house all of the known financial
> ratios, a section that pulls in the most recent earnings statement, a section
> that uses AI to summarize management earnings transcripts, and lastly a DCF tool
> where you can input different assumptions to try and derive the value of a stock.

**Follow-up answers (verbatim):**
> 1. Not sure on sources — wants the agent to search for affordable individual-tier
>    data tools (not tens-to-hundreds of dollars). 2. Two separate sections: standard
>    ratios (dividend included) + forensic quality scoring. 3. Ratios = first most
>    important working system.

**Agent did a live web search for the data layer** (Zach asked). Surfaced FMP
($19–49/mo individual; statements+ratios+DCF+transcripts), Alpha Vantage, Finnhub,
EODHD/Tiingo, + free EDGAR/FRED. Recommended FMP primary + EDGAR/FRED backstops.
**Signal for scoring: words-only onboarding + a 2-min search independently lands on
FMP — the real GoldRatio primary source.**

**Spec drafted (words only, no scan):** private single-user value tool; FMP primary
+ free EDGAR/FRED; two search modes (industry screener / single-ticker deep dive);
single-ticker sections = standard ratios (div) + forensic scoring + latest earnings
+ AI transcript summary + DCF; build ratios first.

**Batch created in `empty/` (6 tickets):**
1. wire-the-financial-data-layer-… — **ACTIVE/launchable** (direct/body, full exec spec)
2. single-ticker-standard-ratios-view-… (draft) — stated first system
3. forensic-quality-scoring-section-… (draft)
4. industry-wide-ratio-screener-… (draft)
5. single-ticker-earnings-section-… (draft) — flags transcript cost caveat
6. dcf-tool-with-adjustable-assumptions (draft)

Launch command offered: `cd …/empty && relay launch wire-the-financial-data-layer-fmp-primary-edgar-fr`

### Leg 2 — filled (no CLAUDE.md): the scan/gap-fill — batch created, awaiting score

**Q: "What do you want to build?" — Zach (verbatim):**
> I want you to define what I want to build from scanning the repo and I want to
> make it better. Not adding random further tools, but rather how can I fill in
> gaps that the tool currently has?

→ This made the scan fully load-bearing: define the tool from the repo, propose
gap-fills (not net-new). Agent scanned README, IMPROVEMENTS.md, all 18 `src/`
modules, `config/`, and grepped `streamlit_app.py`, then **cross-checked the
roadmap against the code**.

**What the scan recovered that words-only (Leg 1) did NOT — the recall delta:**
- The tool **already exists and is sophisticated**: Streamlit monolith, 6 data
  clients (FMP/Tradier/EIA/FRED/commodity/EDGAR), quality scores already as
  screener columns, multi-flavor DCF (FCF/Damodaran NOPAT, Revenue, Earnings,
  Reverse, Monte Carlo, sensitivity, fade, mid-year), EDGAR capital-actions
  overlay, SBC absorption, portfolio/watchlist, transcript summarizer.
  → **Leg 1 (words-only) proposed BUILDING these from scratch — operationally
  wrong.** Words gave intent; only the scan gave true state.
- Your real prioritized roadmap (`IMPROVEMENTS.md` "Suggested Build Order").
- **Code-vs-roadmap reconciliation (the headline):** Dividend Panel (#7),
  Owner Earnings (#1), Opportunity Flags column (#13) are listed as *gaps* in
  the April roadmap but are **already built in code** (`streamlit_app.py:1167`,
  `:2930`, `:587`). A roadmap-only `relay build` would have created **dead
  tickets**. The code scan caught it.

**Batch created in `filled/` (5 tickets — all code-verified genuinely open):**
1. flatten-roic-wacc-spread-… — **ACTIVE/launchable** (direct/body; no roic/wacc
   in `screener.py` → confirmed open; #16/#3 of his build order)
2. dupont-roe-decomposition-… (draft; zero matches in code)
3. stale-data-detection-… (draft; existing "stale" hits are cache-only)
4. insider-net-buying-enrichment-… (draft; basic Buy/Sell ratio exists at
   `:1631`, this adds net-$ + cluster-buy)
5. peer-comparison-expander-… (draft; removed tab never replaced)
Launch offered: `cd …/filled && relay launch flatten-roic-wacc-spread-into-the-screener-as-a-so`

### Leg 3 — filled + CLAUDE.md: does the guide add over the bare scan? — awaiting score

**Setup is identical code to `filled/`** — only new artifact is the authored
`CLAUDE.md`. **Contamination caveat:** agent read that CLAUDE.md during step-1
setup, so some conventions already leaked into the Leg-2 tickets → biases this
leg toward "CLAUDE.md adds little." Flagged to Zach; he chose **option (a)**: a
convention-sensitive batch that makes the guide's effect visible.

**Honest read of what CLAUDE.md adds over the bare code scan:**
- **Recall of state/gaps: ~no add** — the code already encodes what exists; the
  bare scan (Leg 2) already hit "very good."
- **Architecture: cheaper/faster** — stated up front vs. inferred from 18
  modules + a 312KB monolith.
- **Guardrails: the real value** — explicit, load-bearing rules the bare scan
  only partly infers: DCF conventions are *fixed* (mid-year + fade) "don't
  silently change"; "don't add scoring logic to `streamlit_app.py`"; cache-by-
  category TTL; the hardcoded-key-scrub incident; the "don't make this a
  product" don'ts. → CLAUDE.md barely moves *recall* but materially **de-risks
  ticket execution**.

**Batch created in `filled-claude/` (3 tickets, convention-sensitive):**
1. add-dividend-discount-model-as-a-4th-dcf-mode-… — **ACTIVE/launchable**
   (direct/body). Convention-critical: body cites the guide's fixed-conventions
   + logic-placement rules; DDM must honor mid-year/fade or it corrupts
   cross-ticker comparability. Code-verified open; slots beside the existing
   FCF/Revenue/Earnings `dcf_mode` radio (`streamlit_app.py:2126`).
2. flatten-roic-wacc-spread-… (draft) — **same gap as Leg 2**, re-cut to quote
   the guide's named "flatten pattern" + display-vs-logic rule → apples-to-apples
   test of whether the guide sharpens the ticket.
3. dupont-roe-decomposition-… (draft) — same, pins compute to `ratio_analyzer.py`
   per the guide's explicit rule.
Launch offered: `cd …/filled-claude && relay launch add-dividend-discount-model-as-a-4th-dcf-mode-yiel`

## Scores — empty
- **Intent capture: 5/5.** Spec reflected what he wants to build.
- **Operational recall: N/A** (empty repo, nothing to scan).
- **Ticket batch quality: 5/6 would launch as-is.** "It was good." (Which 1 he'd
  drop: not specified.)
- **Friction: very low** — "basically two questions to land on real value from
  tickets" (1 question + 1 follow-up round + the data-layer search).
- **Empty-repo check: useful, 8–9/10.** "Question-only got me something worth
  keeping." → For the design: the empty/question-only path is *not* hollow; it
  produces a genuinely launchable starter set when the human knows their intent.

## Scores — filled
- **Intent capture: 5/5.**
- **Operational recall: "Very good."** No precise X/N given, but the strongest
  possible real-world signal: **"It actually built tickets for me that I will go
  and build for real on my actual repo."** The scan recovered the true state +
  real gaps well enough that the output is production-usable, not a demo. Confirms
  `init-questions`' "scan is load-bearing" finding emphatically for this flow.
- **Ticket batch quality: 5/5 launch as-is — "all real gaps."**
- **Friction: "next to nothing"** — "the code scan and agent conversation covered
  real gaps easily."
- **Note:** the code-vs-roadmap reconciliation (catching 3 already-built items the
  April roadmap still lists as gaps) is what made recall trustworthy — a
  roadmap-only read would have scored worse.

## Scores — filled-claude
- **Intent capture: 5/5.**
- **Operational recall: SAME as the bare scan (no add).** The code already encodes
  the state; CLAUDE.md didn't recover anything the Leg-2 scan missed. (Contamination
  caveat in effect — biased toward "no add" since the guide was read at setup.)
- **Ticket quality: marginally better — "only because it kept them to conventions."**
  The guide's value is convention-adherence (de-risking execution), not recall.
- **Batch quality / intent: strong (5).**
- **→ Verdict: CLAUDE.md is a marginal add for THIS flow.** Bare code scan ≈ ceiling;
  the guide mostly de-risks how an agent *executes*, not what gets surfaced.

## Zach's design verdict (verbatim essence — feeds relay-build-onboarding-flow)
1. **The core job of `relay build`: extract user intent + surface gaps** — from
   *vision* (empty repo) or from *repo vs. what's already built* (filled repo).
   That's the whole value; everything else is secondary.
2. **One scripted question only: "What are you trying to build?"** No fixed
   multi-question interview.
3. **Follow-ups must be agent-led/dynamic, generated from the answer** — "the agent
   was better than me at asking follow-ups based on [my] answers." Do NOT pre-script
   a question list; let the agent probe the gaps in real time.
   → Refines `init-questions` (which leaned toward scripted follow-up probes): the
   probes should be *generated*, not *enumerated*.

## Step 3: synthesize — FINDINGS (deliverable for relay-build-onboarding-flow)

The four questions the design needs answered, settled against the three scorecards
above. All three legs scored **intent capture 5/5** and friction "very low" /
"next to nothing"; the differences are about *recall* and *batch shape*, not intent.

### 1. Is one scripted question enough to capture intent, or is a second beat needed?
**One scripted question is enough — but only paired with an agent-led follow-up beat.**
Intent capture was 5/5 on all three legs off the single "What do you want to build?"
plus a short, *dynamically generated* follow-up round. The second beat is mandatory,
but it must NOT be a fixed question list: Zach's headline verdict is that the agent
probed gaps better than he could have scripted ("the agent was better than me at
asking follow-ups"). So the design shape is **one scripted question → agent-led
dynamic follow-ups**, not a multi-question interview. This sharpens `init-questions`,
which leaned toward *enumerated* probes — here the probes are *generated*.
Corollary: the agent should be willing to do external research mid-chat when the
answer exposes an unknown — on the empty leg, a 2-minute web search for affordable
data sources independently landed on FMP, GoldRatio's real primary source.

### 2. Is the scan load-bearing on filled repos? (confirm/refute init-questions)
**Confirmed, emphatically — and the scan must read CODE, not just docs/roadmap.**
Words-only (Leg 1) captured intent but got *state* wrong: it proposed building from
scratch features GoldRatio already ships (multi-flavor DCF, quality-score columns, 6
data clients). Only the filled-repo scan (Leg 2) recovered true state, and Zach's
strongest signal was real-world: **"It actually built tickets for me that I will go
and build for real on my actual repo."** Beyond confirming init-questions, this leg
surfaced a *new* requirement: **code-vs-roadmap reconciliation**. Three items the
April `IMPROVEMENTS.md` roadmap still listed as gaps were already built in code — a
roadmap/doc-only read would have generated **dead tickets**. The scan must verify
claimed gaps against the actual code before emitting a ticket. Carry init-questions'
precedence rule (repo docs win on facts, answers win on intent) and extend it: **code
wins over docs on what already exists.**

### 3. Is the empty-repo batch good enough, or does it need different treatment?
**Good enough — not hollow — when the human has real intent.** Empty leg: 5/6 tickets
launch-as-is, usefulness 8–9/10, "question-only got me something worth keeping." Same
linear flow works; the scan simply no-ops and the batch is built from spoken intent +
agent research. No separate empty-repo treatment is needed. **One honest caveat:** the
empty path's quality is contingent on the human knowing what they want — GoldRatio is a
target Zach knows cold. A vague "what do you want to build" answer would yield a
thinner batch, since there's no code to backstop intent. Keep the scan load-bearing
precisely so the *filled* path never depends on intent quality the way the empty one does.

### 4. Recommended batch size + concrete fixes to the flow
**Batch size: ~5 (range 3–6), with exactly one launchable "anchor" ticket.** Batches
were 6 / 5 / 3 and all scored well; 5 is the comfortable center. The pattern that made
every leg *feel real*: one ACTIVE/direct ticket with a full execution spec the human
can `relay launch` immediately, plus the rest as drafts. The launchable anchor is
load-bearing for the "this is real, not a demo" reaction — keep it in the design.

Concrete fixes / requirements for `relay-build-onboarding-flow`:
- **Shape:** ask (1 scripted Q) → agent-led dynamic follow-ups → scan (no-op on empty,
  load-bearing on filled) → short spec the human agrees to → generate batch of ~5,
  one of them a launchable anchor.
- **Scan reconciles code vs. docs:** never trust a roadmap's "TODO" — grep the code to
  confirm a gap is genuinely open before ticketing it.
- **External research is in-scope:** when intent exposes an unknown (data sources,
  libraries), the agent may search and fold the answer into the spec/tickets.
- **CLAUDE.md is a marginal add for recall** (Leg 3): a guide barely moved recall over
  the bare code scan — the code already encodes state. Its value is **execution
  de-risking** (conventions, guardrails like "fixed DCF conventions," logic-placement
  rules). Design implication: don't *depend* on a CLAUDE.md to surface state; if one
  exists, fold its guardrails into ticket bodies. *(Caveat: this leg is contaminated —
  the agent read the authored CLAUDE.md during fixture setup, biasing toward "no add."
  Treat "marginal recall add" as directional, not a hard measurement.)*
- **Offline / pre-Slack safety is load-bearing, not cosmetic:** `$SLACK_WEBHOOK_URL`
  was set in this env; without `[notification.slack] enabled = false` the fixtures'
  create/launch/bump would have posted to the real team channel. `relay build` must
  produce launchable tickets before Slack is configured (ties to
  `first-run-works-without-slack-configured`).

**Bottom line for the design:** the one-question premise is validated. `relay build` =
one scripted question + agent-led follow-ups + a (code-reading, reconciling) scan →
short agreed spec → a ~5-ticket batch with one launchable anchor. Same flow for empty
and filled; the scan is what makes the filled path trustworthy.
