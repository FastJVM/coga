# improve-readme-and-doc — blackboard

## Investigation (2026-06-08)

Read `README.md` (689 lines), `docs/vision.md`, `docs/design.md`, scanned
`docs/` and cross-checked README's CLI reference against the actual registered
commands in `src/relay/cli.py`. Git remote is `github.com/FastJVM/relay`.

### Concrete findings (objective — these are wrong/stale, not taste)

**README.md**

1. **Missing command reference entries.** README's Commands section claims to be
   "the reference … a one-screen entry per CLI command," but two registered
   built-ins have no entry:
   - `relay digest` — registered in `cli.py:84`; undocumented.
   - `relay validate` — registered in `cli.py:85`, flags `--json`, `--fix`,
     `--check-slack`, `--check`. Mentioned inline in Install / Slack /
     Development but has no `### relay validate` reference entry.
2. **No License section.** Repo ships AGPL-3.0 (`LICENSE`), README never states
   the license.

**docs/vision.md**

3. **Wrong repo URL.** Line 14 links `github.com/relay-dev/relay`. Canonical is
   `github.com/FastJVM/relay` (git remote + README + CLAUDE.md all agree).
4. **Stale "six-command CLI" claim.** Line 22 ("a six-command CLI"). Actual
   built-in command count is ~18 (init, create, draft, ticket, launch, status,
   show, bump, automerge, delete, retire, panic, slack, digest, validate, skill,
   mark, recurring). Either re-count or reframe to "a small CLI."
5. **Unfilled placeholder in the public essay.** Line 246 still contains a
   literal `[FILL IN WITH REAL NUMBERS: …]` TODO bracket — the credibility-anchor
   section the doc itself flags as load-bearing is blank.

### Subjective / structural (surface as options, not auto-fix)

- README intro is ~35 lines of dense positioning before `## Install`. A short
  "what you actually type" quickstart up top could help first-time readers. Taste
  call — owner decides.
- README doubles as the full CLI reference (32KB). Splitting reference into
  `docs/cli.md` is possible but cuts against "one obvious file"; probably leave.

### Open scope question for the human

"doc" in the title is ambiguous — does it mean `docs/vision.md` specifically, or
all of `docs/` (design.md, market-thesis.md, competition/*)? Findings above cover
README + vision.md. market-thesis.md and competition reports look like living
strategy notes I'd leave alone unless asked.

**Resolved (human, 2026-06-08):** scope = README + vision.md only. Depth = full
editorial pass (objective fixes + readability/structure review).

**Real-numbers anchor (human, 2026-06-08):** ~3x productivity gain since running
FastJVM on Relay — across PR count, "task units," and cost — but data is
confidential / hard to extract precisely. Decision: fill vision.md:246 as an
honest *directional* claim (~3x across PR throughput / task units / cost,
upfront that exact figures aren't published), NOT a fabricated metrics table.
Baked into ticket finding 5.

## Evaluator review

All findings verified. Here is my assessment.

---

**Evaluation: `improve-readme-and-doc` ticket**

**1. Clarity for a cold-start agent — strong.** The Description states the two target files, the two goals (objective fixes + readability), and an explicit out-of-scope list. An agent with no prior context could start immediately. Each of the 5 objective findings names the file, line, and exact wrong value, so they're independently checkable. This is well above the usual bar.

**2. Workflow fit — acceptable but slightly heavy.** `code/with-review` is a code-implement → peer-review → open-pr → human-review chain. The peer-review step's instructions are framed around running `/code-review` or `codex review` on a *code* diff and re-running `python -m pytest` — neither maps cleanly to a docs-only prose edit. The peer review will still function (it reviews any branch diff), but a reviewer agent may waste effort looking for code-correctness issues or trying to run a test suite that can't validate prose. A lighter doc/with-review workflow (if one exists) or a plain implement→pr→review shape would fit better. Not a blocker — the chain is harmless here — but it's a mild mismatch worth noting. The big upside is that peer review *is* genuinely valuable for editorial drift, so I'd keep review; it's just the code-specific framing that's off.

**3. Attached context relevance — correct and sufficient.** `relay/principles` is exactly the right attachment: the ticket's whole purpose is to correct narrative drift without re-pitching the product, and principles is declared canon when README/vision diverge. The ticket even includes a closing note explaining *why* it's attached, which is good practice. Nothing critical is missing. One could argue `current-direction`/`project-stage` matter for the "six-command → ~18" reframe (stage-specific posture lives there), but it's not needed — the fix is a factual recount, not a posture call.

**4. Context broad enough to inline instead — minor.** `principles/SKILL.md` is ~150 lines and is genuinely needed in full as the canon reference for the voice/claims check, so attaching rather than excerpting is right here. No single load-bearing fact needed copying into `## Context`. Good — the ticket already inlined the truly load-bearing facts (exact line numbers, the canonical URL, the command count) rather than relying on the agent to rediscover them.

**5. Scope — reasonable, single ticket.** Two files, a bounded list of objective fixes, plus a judgment-based editorial tidy with explicit guardrails. It does not bundle the other docs (`design.md`, `market-thesis.md`, `competition/*` are explicitly excluded) and explicitly forbids the one scope-creep risk (splitting the CLI reference into a separate file). This is one ticket's worth of work.

**6. The 5 findings — all verified accurate, none stale:**
- **Repo URL (finding 3):** Confirmed. `docs/vision.md:14` reads `github.com/relay-dev/relay`. Git remote is `github.com/FastJVM/relay.git`; README and CLAUDE.md agree on FastJVM. Wrong as claimed.
- **Six-command claim (finding 4):** Confirmed at `docs/vision.md:22` ("a six-command CLI"). Actual registered count is 19 command registrations in `src/relay/cli.py` (15 `app.command` + `skill`/`mark`/`recurring` typers + the version callback) — so "~18 built-ins" is a fair characterization. **One correction:** the ticket says "check the 'six commands' framing isn't relied on elsewhere." It is — line 36 ("Six months ago"), line 110 ("Six months in"), line 206/210/220 all use "six" but refer to *months of operation*, not commands. Only line 22 is the command claim. The agent must not blanket-edit "six"; the ticket's instruction to "check" is right, but worth flagging that the word recurs innocently 6+ times so a careless find-replace would corrupt the doc.
- **Placeholder (finding 5):** Confirmed at `docs/vision.md:246`, a literal `[FILL IN WITH REAL NUMBERS: …]` bracket in the `## Status` credibility-anchor section. The ticket's handling — fill with owner-supplied real numbers or flag back, do not fabricate — is correct and matches the doc's own note that the section is load-bearing.
- **Missing README entries (finding 1):** Confirmed. No `### relay digest` or `### relay validate` heading exists in README.md, yet both are registered (`cli.py:84`, `cli.py:85`) and the Commands section promises "one-screen entry per CLI command." `validate` appears inline (Install/Slack/Development) but has no reference entry. Accurate.
- **No License section (finding 2):** Confirmed. `LICENSE` is AGPL-3.0; README has zero occurrences of "license." Accurate.

**7. Assumptions to question before launch:**
- **Owner-supplied numbers (finding 5) are a hard dependency.** The ticket is `mode: interactive` with `human: nick`, so the agent can ask — good — but if launched unattended this step stalls. Make sure Nick is ready to hand over the FastJVM operating figures, or the agent will correctly panic/flag and the ticket parks at that point.
- **The "~18" / "six-command" recount needs a definitional decision the agent shouldn't make alone:** do subcommands (`mark active/paused/done`, `recurring launch`, `skill install/update/...`) count as separate commands? The ticket's suggested reframe ("a small CLI") sidesteps this nicely and is the safer instruction — I'd lean on that phrasing rather than committing to a specific integer in the essay, since any exact count will drift again.
- **"Don't blanket-replace 'six'"** (per finding above) — worth one line in the ticket so the agent treats line 22 surgically.
- **The README quickstart suggestion** ("what you actually type" near the top) is editorial judgment, but note the README intro is deliberately thesis-first per the principles/vision framing; a quickstart that front-runs the "read the principles first" message would cut against the doc's intent. The agent should weigh this against principle-driven framing, which the ticket does ask it to preserve.

**Bottom line:** Launch-ready. All 5 objective findings are real and unfixed. The only substantive caveats are (a) the code-review workflow is mildly over-fit for a docs change, and (b) the "six" recount touches a word that recurs innocently — add a one-line guard so the agent edits line 22 surgically and prefers a non-numeric reframe. The owner-numbers dependency is real but already handled by interactive mode plus the explicit "flag back, don't fabricate" instruction.

**Author note:** Incorporated the line-22 surgical-edit guard into finding 4. Kept `code/with-review` — peer review of editorial drift is worth the mild code-framing mismatch; no docs-specific review workflow exists.
