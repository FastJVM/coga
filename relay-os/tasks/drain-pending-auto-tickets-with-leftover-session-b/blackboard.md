The blackboard is a notepad to be written to often as the human and agent works through a task.

## Pre-launch decisions with Nick (2026-06-20)

Three design inputs locked before launching the design step (full text now in
ticket.md `## Context` → "Decisions locked with Nick"):

1. Budget: read remaining usage from the **server** per agent type
   (Anthropic/OpenAI), not CLI `/usage` scraping. Design must *prove the
   endpoint works* (go/no-go) and confirm it's the subscription usage window,
   not per-minute rate-limit headers. Unreadable → skip drain for that agent.
2. Threshold: a **`relay.toml` config key** (min % remaining, optional max
   cap), not hardcoded. Design names key + default + re-probe cadence.
3. Ordering: **oldest-first by first `log.md` timestamp** via a new
   `first_activity()` helper (mirror of `last_activity()`). Committed content
   → survives clone (file mtime does not). Bonus consistency add:
   `relay status --order-by created` on the same helper.

## Open Questions (for review-design / Nick)

1. **`drain_enabled` default.** Spec sets it to `false` (opt-in) so existing
   repos see no behavior change until they flip it on. The feature's whole
   point is "just drain after the sweep", which argues for `true`. Picked the
   conservative default — confirm or flip.
2. **`drain_min_remaining_percent` default = 20.0.** Pure heuristic (ticket
   cost varies wildly). Applied to BOTH the 5h and weekly windows. Sane
   starting value? Want a max-tickets cap default too (currently 0 =
   unlimited)?
3. **Codex throwaway cost.** Priming codex costs one tiny `codex exec` per
   drain (~17k input tokens, mostly cached; 27 output) and only fires if a
   codex-assigned auto ticket exists. Acceptable, or prefer skipping codex
   entirely until a real endpoint exists?
4. **Summary channel.** Spec posts a live `post()` one-liner. Alternative: spool
   into the daily digest (`notify`). Live was chosen for immediacy on an
   unattended cron run — confirm.
5. **Config location.** `[recurring.drain]` chosen (the drain is a recurring-
   sweep tail). Alternatives: top-level `[drain]` or fold into `[launch]`.

## Budget-probe go/no-go (2026-06-20, design step) — REAL probes run

Decision #1 required a real endpoint probe, not docs. Done. Results:

### Claude — GO (clean, fresh, free) ✅
- Endpoint: `GET https://api.anthropic.com/api/oauth/usage`
- Auth: `Authorization: Bearer <token>` is the ONLY required header
  (verified: token-only → HTTP 200; beta header not needed; no auth → 429).
- Token source (Linux/headless): `~/.claude/.credentials.json` →
  `.claudeAiOauth.accessToken` (also carries `.subscriptionType` = "max",
  `.expiresAt`, `.scopes`). NOTE macOS stores creds in Keychain, not this
  file — cron target is Linux so file path is the realistic one; note the
  caveat for the implementer.
- Body confirms the SUBSCRIPTION USAGE WINDOW (not per-minute rate headers):
  `five_hour.utilization` (e.g. 2.0 = percent used) + `resets_at`;
  `seven_day.utilization` (4.0) + `resets_at`; plus a structured `limits[]`
  array (`kind`: session/weekly_all/weekly_scoped, `percent`, `severity`,
  `resets_at`, `is_active`). remaining% = 100 − utilization.

### Codex — NO clean standalone GET ⚠️ (skip-or-stale)
- ChatGPT-backend GETs are Cloudflare-blocked: `chatgpt.com/backend-api/
  codex/usage|rate_limits|account|me` all → HTTP 403 (HTML bot page), with
  and without codex client headers.
- `api.openai.com/v1/me` → 200 but identity only, NO window/usage data.
- Codex auth: `~/.codex/auth.json` (auth_mode="chatgpt", `.tokens.access_token`,
  `.tokens.account_id`).
- Codex DOES expose the identical window data, but only as a `rate_limits`
  snapshot **attached to a `responses` API call**, persisted into
  `~/.codex/sessions/<Y>/<M>/<D>/rollout-*.jsonl`. Structure verified:
  `{primary:{used_percent,window_minutes:300,resets_at}, secondary:
  {used_percent,window_minutes:10080,resets_at}, plan_type:"pro"}`.
  → primary = 5h window, secondary = weekly window. Same family as Claude.
- Consequence: the only no-extra-cost codex read is the LAST persisted
  rollout snapshot — which is only as fresh as the last codex run (could be
  hours/days stale). There is no free fresh probe. Per decision #1's
  "unreadable → conservatively skip", codex's branch is either (a) read the
  newest rollout snapshot iff within a freshness bound, else skip; or
  (b) skip codex drains entirely for v1. ← surfaced to Nick as the one fork.

### Implication for the interface
One `UsageProbe` interface, one impl per agent type. Claude impl is the
live GET. Codex impl is the rollout-snapshot read (or a no-op skip). Probe
must fail SOFT (any error/timeout/unreadable → treat as "no budget signal"
→ skip that agent's drain), never crash the sweep.

### Nick's call (2026-06-20): codex = "fire one throwaway at beginning"
Chose option 3, minimized to a SINGLE priming probe. VERIFIED it works:
- `codex exec --json -s read-only --skip-git-repo-check "Reply with exactly:
  ok" </dev/null` → exit 0, replied "ok", usage 16952 input / 27 output
  tokens (cached 4992) — tiny cost against the window.
- Immediately after, newest `~/.codex/sessions/<Y>/<M>/<D>/rollout-*.jsonl`
  (13s old) carried a FRESH `rate_limits`: primary{used_percent 1.0,
  window_minutes 300}, secondary{used_percent 6.0, window_minutes 10080},
  plan_type "pro". `resets_at` = unix epoch seconds.
- GOTCHAS for implementer: (1) MUST redirect stdin `</dev/null` or codex
  blocks on "Reading additional input from stdin..."; (2) the `--json`
  experimental event stream does NOT include rate_limits — read it from the
  rollout file, not stdout; (3) read-only sandbox + --skip-git-repo-check
  keeps the throwaway safe/contained.
- Mechanism: prime codex ONCE per drain (lazily, only if codex-eligible
  tickets exist), then read newest rollout snapshot. After the first codex
  drain launch, the snapshot self-refreshes (each codex launch rewrites it),
  so per-ticket re-reads stay fresh for free.

## Bootstrap interview notes (2026-06-11)

- Origin: Nick's one-liner — after a recurring launch sweep, if auto tickets
  are pending and the session has token budget left, run them.
- Budget signal: initially leaned "let design decide", then Nick clarified
  that usage limits ARE readable — Claude Code, Codex, and other agents
  report how much of the current usage window remains. Ticket now states
  the mechanism (read per-agent usage limits) and leaves only the exact
  invocation + threshold to the design step.
- Eligibility: status active + mode auto + assignee is a configured agent
  type, oldest first.
- Drain policy: drain until budget runs out; stop on first failure /
  unfinished non-interactive launch (mirrors existing sweep behavior).
- Workflow: code/design-then-implement — chosen because the usage-reading
  mechanism per agent still needs verification before implementing.
- First draft slug started with `recurring-` (the period-task identity
  prefix) — deleted and re-drafted to avoid colliding with
  `_RECURRING_PREFIX` matching.
- Nick approved the ticket as written. The older overlapping draft
  `token-budget-aware-idle-execution-of-low-priority` (agent-side end-of-
  session idle-pick shape) was deleted as superseded by this ticket.
  `autoroute-agent-based-on-remaining-usage` is a related-but-distinct
  empty draft (which agent to route to by remaining usage) and was left
  in place.

## Evaluator review

## Ticket Review: drain-pending-auto-tickets-with-leftover-session-b

### 1. Description clarity — good, with two underspecified details

The description is strong for a cold start: clear trigger (after a bare `relay recurring` sweep), precise selection criteria (`status: active`, `mode: auto`, assignee is a configured agent type), ordering, stop condition, and where the budget signal comes from. The ## Context section correctly anchors the code (`src/relay/commands/recurring.py` run loop, `src/relay/recurring.py`) and correctly states there is no budget tracking in relay today — I verified both.

Two things an agent will have to guess:
- **"Oldest first" by what clock?** Tickets are plain directories; frontmatter has no created-date field. Git history, directory mtime, and slug ordering all give different answers. This should be pinned in the ticket or explicitly delegated to design.
- **"The sweep's existing Slack summary" doesn't quite exist.** Slack output is per-event `notify()` calls in `_broadcast_scan()` (which fires *before* launches), not an end-of-sweep summary. The drain report will need a new notification point, not an edit to an existing summary. Minor, but the agent will trip on the framing.

### 2. Workflow fit — correct choice

`code/design-then-implement` fits well. This is exactly the "thin ticket with a genuinely open design question" shape the workflow exists for: the per-agent usage-probe mechanism is unverified, and the workflow's `review-design` gate puts a human between that investigation and implementation. An `implement`-only workflow would have been a mistake here.

### 3. Context relevance — relevant set; one candidate missing

- `relay/recurring` — clearly right; explains the sweep semantics, stop-on-unfinished behavior, and the `recurring-` prefix distinction the ticket leans on.
- `relay/codebase` — justified for any ticket editing `src/relay/` (it carries test/fixture expectations).
- `dev/code` — justified; the workflow produces a branch and PR, which is exactly this context's attach condition.
- **Possibly missing: `relay/sync`.** The `relay/recurring` context explicitly says Slack posting mechanics are out of its scope and live in `relay/sync`, and this ticket has a Slack-observability requirement. `notify()` is simple enough that this is borderline, but it's the one defensible addition.

### 4. Broad contexts vs. copied facts — handled well

The ticket already copied the load-bearing facts into ## Context (where the sweep lives, no existing budget tracking, the `recurring-` prefix rule, the conservative skip-on-unreadable default). `relay/codebase` is the broadest attachment (~165 lines, including wheel-packaging gotchas irrelevant here), but it's the conventional attachment for relay-source work and carries the test/fixture rules the implement step genuinely needs. No attachment exists solely to deliver one fact. Acceptable.

### 5. Scope — one feature, but with a detachable risky core

This is one coherent feature, not an obvious bundle. However, it contains three pieces of unequal risk: (a) a per-agent usage-probe capability (new, external-facing, unverified), (b) the drain loop itself (straightforward, mirrors existing sweep logic), and (c) Slack observability (small). The usage probe is the part that could blow up; if it proves infeasible the whole ticket's shape changes. The design step absorbs this, but the ticket should explicitly permit the design step to come back with "no stable programmatic usage interface exists; here are fallbacks (time-box, N-tickets cap, skip feature)" rather than treating the probe as a settled premise.

### 6. Assumptions to question before launch

- **"Claude Code and Codex both expose how much of the current usage window remains" — stated as fact, not verified.** Both expose usage *interactively* (`/usage`, `/status`), but a stable *programmatic/headless* interface is exactly the part the ticket itself admits "needs verifying." The description asserts the capability; the context hedges it. The hedge should win: the assertion in ## Description should be softened, or the design step's first deliverable should be a go/no-go on the probe mechanism. This is the single biggest pre-launch risk.
- **"Enough budget to start a ticket" may be unknowable.** Ticket cost varies wildly; any threshold is a heuristic. Fine to delegate to design, but the owner should expect a crude answer (e.g., "drain only if >X% of window remains") and decide whether that's acceptable.
- **Re-check cadence is implicit.** "Until the budget runs out" implies re-probing between launches, but probing mid-sweep may itself be slow or rate-limited. Design detail, but worth a line.
- **Interaction with the sweep's stop conditions.** If the recurring sweep itself stopped early on an unfinished launch, does the drain still run? The description says "after a bare sweep finishes its scheduled work" — ambiguous when the sweep aborted. Should be pinned.

### Verdict

Launchable as-is given the design step exists, but I'd make three edits first: pin (or explicitly delegate) the "oldest first" ordering source, soften the usage-reporting assertion to match the context's hedge and authorize a no-go outcome from design, and consider attaching `relay/sync` for the Slack requirement.
