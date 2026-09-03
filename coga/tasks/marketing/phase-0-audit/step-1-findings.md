<!-- Attachment of the `marketing/phase-0-audit` task. Not a ticket; moved out of
the blackboard on 2026-09-03 so composed launch prompts stay small. -->

## Step 1 findings (agent, 2026-09-02)

Inventory only — no fixes made. Each check below ends with what it means
for the worklist. Scratch runs live under this session's scratchpad
(`.../scratchpad/qs/`), not in any real repo.

### 1. README top — does the first screen tell the post-1 story?

Partly. What the first screen (lines 1–15) has and lacks:

- **Has:** what it is ("company OS for small teams"), the tabs→operation
  framing, the queue for questions, git-backed record, `megalaunch`, and the
  vocabulary "acting as the CPU" (line 14) — the post's phrase is already
  here.
- **Lacks the day-shape entirely.** No sentence anywhere in the README
  describes a morning: answer the queue, brief, launch the wave, leave.
  `grep -i "morning|leave|hour"` finds nothing. The post's Requirement 2
  ("but I see where it's going" — files in my git, steer before rather than
  re-correct after) appears only as "The correction loop" much further
  down (line 63).
- **Lacks "for whom" in the post's terms.** "Small teams" is there;
  "founder of a small company who can't afford to be the CPU" is not — the
  "Who it is for" section is at line 88, below the fold.
- **Leads with numbers the plan says not to lead with.** "Measured on
  itself" (line 31) is the third section and carries "31 agent-operated
  workstreams in one week". It is carefully hedged and sourced to
  `docs/velocity-report.md`, so it's not a claim-discipline violation, but
  a post-1 reader arrives from a no-numbers essay and hits a stats section
  above the primitives. `marketing/readme-top` should decide whether it
  moves down.
- **The internal-tool envelope is absent.** Nothing on the first screen
  says "this is the tool we run our own company on and are open-sourcing";
  the closest is "Coga runs the work that builds Coga" at line 33.
- **Demo video is present** (line 18–20, a 95-second YouTube demo) — an
  asset the post can reuse; check it still reflects current CLI names.
- README text mentions `coga pick` (line 148): it exists as an alias for
  `megalaunch --pick`. Fine.

Gaps for `marketing/readme-top`: add the day-shape and the internal-tool
envelope to the first screen; move or shorten "Measured on itself"; pull
"for whom" up. Not a rewrite.

### 2. Quickstart end-to-end — **broken today, from PyPI and from source**

Status: **re-run from PyPI after 1.0**. Findings from the run on
2026-09-02 (fresh venvs under the scratchpad, scratch git repos):

| # | Step from README / getting-started | Result |
|---|---|---|
| a | PyPI state | Serves **0.2.0** (plus a 1 KB `0.0.1` placeholder). Repo is 0.3.1. Tag `v0.2.0` is the last tag; release goes through `.github/workflows/release.yml` on a GitHub Release (Trusted Publishing). |
| b | `python3 -m venv && pip install coga` on a machine whose `python3` is 3.9 (this machine's default; common) | pip **silently installs the 0.0.1 placeholder** (no `coga` binary at all) because 0.2.0 requires ≥3.11. No error, no hint. Getting-started says "Python 3.11+" but neither doc says what the failure looks like. |
| c | `uv venv --python 3.11` + `uv pip install coga` (0.2.0) → `coga --help` | Works. |
| d | `coga init --user tester` on **0.2.0** | **Crashes** with a traceback: `TypeError: MultiplexedPath.joinpath() takes 2 positional arguments but 3 were given` (`packaged_template_root`). |
| e | Same `coga init` from **this checkout (0.3.1) on Python 3.11** | **Same crash.** Cause: `src/coga/resources/` has no `__init__.py`, so `importlib.resources.files("coga.resources")` returns a `MultiplexedPath`, whose multi-argument `joinpath(*parts)` only exists from Python 3.12. The documented floor (3.11) does not work; the owner's own install runs on 3.12 (uv tool python). Every test/CI run presumably uses 3.12 too. |
| f | `coga init` from this checkout on **Python 3.12** | Init creates `coga/.coga/.venv` and runs `pip install coga==0.3.1` **from PyPI** — which doesn't exist → init fails cleanly and rolls back. Consequence for launch day: **1.0 must be on PyPI before `init` from a PyPI-installed 1.0 can succeed** (it re-downloads its own version into the vendored venv). Worked around here with `COGA_REPO_URL=/home/n/Code/coga`. |
| g | `coga init` in an existing project (3.12, checkout source) | Succeeds. Installs 7 managed skills, including `google-agents-cli-*` (7 skills) and pip-installs `gmail` / `google-calendar` requirements into the venv — needs network, takes a while, and looks odd in a stranger's repo. Commits `coga/`, writes CLAUDE.md/AGENTS.md, prints "Skipped the onboarding ticket (this dir already has a project)" — matches README text. |
| h | `coga init` in an empty repo | Seeds `coga/tasks/coga-build.md` and prints "Run `coga build`…" — matches README text. **But** with a bare `SLACK_WEBHOOK_URL` in the environment it crashes with a `ConfigError` traceback (the existing-project path handles the same env var with a friendly tip). Edge case, only bites people who already have that variable. |
| i | Git default branch | This machine's `git init` creates `master`; `coga init` hard-codes `control_branch = "main"` and **every subsequent command prints the "control branch 'main' does not exist (you are on 'master')" nag 2–3 times**. Anyone without `init.defaultBranch=main` hits this on every command of the quickstart. |
| j | `coga create "Add a health-check endpoint" --workflow code/with-review` | Creates `coga/tasks/add-a-health-check-endpoint.md` — matches getting-started. |
| k | `coga validate`, `coga status` | Validate: "All good (1 tasks checked)". Status shows six recurring jobs as "due — not created" in a repo that is one minute old — noise on first run. |
| l | `coga launch <slug> --prompt-report` | Works; 6 layers, ~3.9k tokens. Matches getting-started's description. |
| m | First launch attempt (`coga launch <slug>`, non-TTY, 20 s cap) | Activates the draft, composes, then stops at the TTY gate ("an agent launch requires a TTY"). That is as far as this session can go without a real terminal; **the actual Claude Code spawn was not exercised here** — owner should run it once in a real shell after 1.0. |
| n | `coga build --prompt-report` and `coga build` in the empty repo | Compose works (~2.5k tokens); launch stops at the same TTY gate. |

Bottom line: a reader following the README today gets either a silent
placeholder install (3.9), a traceback at `coga init` (3.11 on any
version), or, on 3.12 with 0.2.0, the same traceback. **There is no working
first run from PyPI right now.** The 1.0 release fixes (a), (d), (f) by
construction; (b), (e), (g), (i), (k) are separate findings for the owner
to triage (see worklist).

### 3. Narrative material — non-Coga repos

Yielded **10 candidates, no shortfall**: eight strong ones with no
confidentiality concern (six queued judgment questions, one morning
sequence, one clean megalaunch sweep — all from `magicator` and `xpllm`),
plus two from `admin` that need the owner's confidentiality pass. Full
literal text is in `narrative-candidates.md` beside the ticket, which
`marketing/post-async-megalaunch` reads. The owner has since ruled every
candidate unpublishable — see the ticket's worklist.

Per-repo size of practice (read-only; `coga-hosting-probes` is a second
checkout of `multiply` and adds nothing):

| Repo | log lines | tasks | span | agent `blocked:` | `[megalaunch]` lines |
|---|---|---|---|---|---|
| multiply | 735 | 32 | 06-17 → 09-02 | 3 (all "launch gate unmet") | 10 |
| magicator | 1580 | 23 | 05-28 → 08-28 | ~45 (+32 unblocks) | 74 |
| xpllm | 1291 | 55 | 06-05 → 09-02 | 17 (+12 unblocks) | 29 |
| admin | 1775 | 13 | 07-21 → 09-02 | 8 (+6 unblocks) | 228 |
| patents | 550 | 20 | 04-29 → 07-24 | 0 | 24 |
| tablet | 52 | 5 | 06-17 → 07-29 | 1 (mechanical) | 0 |
| demo-hackathon | 140 | 4 | 05-28 → 07-20 | 4 (mechanical) | 12 |

Two things the owner should know before quoting:

- **The ticket assumed `multiply` first; it is the weakest source.** Its
  three blocks are all sequencing gates canceled the next morning in a
  pivot. The story lives in `magicator` and `xpllm` — the owner's JVM /
  LLM research repos. Quoting their slugs and block reasons reveals
  research direction (JVMTI hidden-class capture, LLVM slice gates,
  DaCapo benchmark sourcing). **Owner to confirm those repos, or the
  quoted lines, are publishable** — not flagged as confidential in the
  ticket, but they are not public repos as far as this audit can tell.
- **Admin candidates 9 and 10** come from the company admin repo where
  the human is `zach`, not the essay's narrator, and sit next to Slack
  lines naming a trademark serial, Xero reconciles, payroll/tax questions
  and a named accountant. The step-advance lines quoted are probably safe;
  the surrounding lines are not.

### 4. Megalaunch state — can post 1 describe it in present tense?

Yes, with the plan's existing caveat, and the log backs it:

- The log has 534 `megalaunch`/`watchdog` lines. Real sweeps exist and
  are recent: 2026-08-26 21:29 (three tickets picked, started, launched
  within 30 minutes), 2026-09-02 13:44 (three tickets picked, two
  launched within 10 minutes). These are quotable from *this* repo if
  needed, but the plan prefers non-Coga repos.
- Open bugs touching the felt experience: `megalaunch-activates-picks-
  before-preflight` (in_progress, PR at review), `launch-activates-before-
  preflight` (in_progress), `verify-the-pr-review-comment-loop-once-the-
  review` (blocked since 08-20 on a precondition gate). Nothing in the
  last two weeks reads as a megalaunch *crash*; the recurring failures in
  the log are `[git] sync failed` / `[slack] post failed` on DNS outages
  (08-21, 08-25, 08-26, 08-27, 09-02) — infrastructure, not the scheduler.
- `watchdog` appears once in the log; the liveness watchdog is in
  `repl_supervisor.py` / `recurring_runner.py` and isn't producing failure
  lines.

Narrative-honesty verdict: "you launch the wave and you leave" is true as
a *practice* the owner performs; the positioning caveat still applies —
don't promise Slack-grade responsiveness or unattended perfection. The
"first days feel like setup" caveat in the plan is, per check 2, an
understatement until 1.0 ships.

### 5. Distribution surfaces (fetched 2026-09-02/03)

- **Blog (deviantabstraction.com):** WordPress.com with Jetpack Stats and
  a Jetpack email-subscribe block already wired, so "newsletter day 0" is
  possible with no new setup. Last post **2026-06-02** ("Audit, Test,
  Automate: How We Decide What AI Can Own") — three months quiet; before
  that a mix of JVM/perf/AI essays and French/English poetry. **Zero Coga
  mentions** on the site or in search. Analytics: Jetpack Stats only (no
  Plausible/GA); it reports referrers, so **per-channel URLs will show up
  as referrers but not as a UTM breakdown** — good enough for the plan's
  "which channel sent traffic" question, not for fine attribution. Adding
  a third-party analytics script depends on the WordPress.com plan (owner
  knows).
- **fastjvm.com:** a single-page Next.js "Research Index" for FastJVM
  (JVM performance research), with Google Analytics. It has no blog, team,
  tools, or about section — the only slots are the "Our research" link list
  and the contact footer. GitHub link points at `manycore-com`, not the
  `FastJVM` org that hosts Coga. No Coga mention. Whether to cross-link is
  the owner's call (step 2); structurally there is no natural place.
- **HN (`top256`):** karma 213, since 2016. **Corrected 2026-09-03** against
  the public HN search API; three figures in the original step-1 finding were
  wrong. It is **26 stories**, not 101 submissions — that count included
  comments. There are **four** results at 30+ points, not three: the step-1
  pass missed "VC and the marginal-dollar problem" (52 pts, 2017-10).
  And the six **Show HN** attempts scored 1–6 points, not the "3 and 2"
  recorded; the conclusion that they flop is unchanged.
  The named hits are right: "Why Tech Inevitability is Self-Defeating"
  (87 / 58, 2025-10), "My bytecode optimizer beats Copilot by 2x" (47 / 35,
  2025-07), "Computing Industry Doesn't Care about Performance" (32 / 19,
  2024-11). The API records points, not placement, so **"front page" is an
  inference** — near-certain at 87, merely likely at 32.
  The 2026-06-03 essay ("AI Delegation Starts with Inspectable Work") got
  1 pt; the owner confirms it was written for himself and his team and was
  never a launch attempt, so it is not evidence that the category fails.
  Pattern: submits own essays, replies heavily when one hits, otherwise quiet.
  Coga has never been submitted.
  **What the step-1 pass concluded here was wrong** — it read the record as
  "plain story submission matches the account's history exactly". The Show HN
  half holds; the "plain story" half does not. See the corrected reading in
  `marketing/build-the-launch-plan`: every hit names an opponent, and the same
  URL scored 1 point with a descriptive title and 32 with an adversarial one
  four days later. That also reframes the second-chance branch — the
  resubmission worked because the *title changed*, not because it was
  resubmitted.
- **Reddit (`Let047`) — supplied by the owner 2026-09-03** (every
  unauthenticated fetch returned 403 or a JavaScript wall, on `www`,
  `old.reddit.com`, and `about.json`). **7,781 karma, 2,609 contributions,
  6-year-old account, 56 followers**, 0 gold. This is a substantially stronger
  account than the audit assumed: it is not a cold account and will not trip
  new-account or low-karma spam filters, which are what usually make cold
  self-promotion fail on Reddit.
  **Still missing: the list of subreddits.** The profile's "active in" panel
  shows none, so it reveals nothing about membership. The plan's rule is to
  post only where already a member, so that list is what decides whether
  Reddit is in the channel set and which subreddits. It has to come from the
  owner's own joined-communities sidebar.
- **Lobste.rs — answered from the API on 2026-09-03** (the step-1 run could
  not reach the site; a retry succeeded). Username **`ntoper`**, created
  **2025-06-05** (15 months old), karma **55**, invited by `skeptrune`, empty
  "about". **Exactly one submission ever:** 2025-10-01, "is tech inevitable",
  pointing at `deviantabstraction.com`, **26 points / 19 comments**, tagged
  `philosophy`, submitted with "I am the author". That is the same essay that
  took the HN front page at 87 points.
  Three consequences, all favorable: the account is long past any new-user
  window, so those restrictions do not apply; **`deviantabstraction.com` is
  already a seen domain there and did well**, which was the audit's main
  worry; and the one prior submission proves self-authored essays land on
  this account. The one genuine risk is ratio — every story `ntoper` has ever
  submitted is his own, so a second self-authored link is 2 for 2. Volume is
  low enough (one story in 15 months) that it reads as occasional rather than
  as a promotion channel, but a comment or two on other people's stories
  before submitting would cost nothing.
  **Tags confirmed against `/tags.json`, not inferred:** `ai` reads
  "Developing artificial intelligence, machine learning. Tag AI usage only
  with `vibecoding`", and `vibecoding` reads "Using AI/LLM, coding tools.
  Don't also tag with `ai`." So post 1 is **`vibecoding` + `practices`**, and
  explicitly not `ai`. "Personal productivity systems" and "management" are
  off-topic there, so the post has to read as engineering practice.
- **Community home:** `FastJVM/coga` is public (AGPL-3.0), 3 stars,
  0 forks, 0 open issues, 17 open PRs, **Discussions disabled** (404),
  **no Discord link anywhere**, one release (`v0.2.0`, 2026-06-27), no
  homepage URL set on the repo. Nothing exists yet; `marketing/discord`
  decides. Repo description reads "A blackboard for humans and agents".

### 6. Token-measurement plan (draft for the owner to assign)

What post 3 needs: same task, with vs without contexts — tokens and
time-to-first-edit. What exists:

- **Per-session usage records** are already written to `coga/log.md` as
  schema-2 JSON on every launch (input/output/cache tokens, elapsed
  seconds, agent turns, model, step). `coga usage --task <slug> --json`
  aggregates them; `scripts/human_minutes.py` reads the same records.
- **`coga launch <slug> --prompt-report`** prints per-layer bytes/tokens,
  so the "contexts cost" of a prompt is measurable without launching.
- **There is no `--no-contexts` launch flag.** The only lever is the
  ticket's `contexts:` list, which agents and humans may edit.

Proposed mechanism (cheapest that yields receipts):

1. **Pick 4–6 real tickets during phases 1–2** (mix of this repo and
   multiply; code tickets with an `implement` step). Ownership: the owner
   picks; the tag is a line on this blackboard or a `marketing/token-
   receipts` ticket.
2. **A/B on the implement step only.** For each ticket: run implement once
   with `contexts: []` on a throwaway branch, `coga mark`-reset is not
   available, so use a *copy* of the ticket (`<slug>-nocontext`) rather
   than rewinding; then run the real ticket normally. Record both slugs.
3. **Collect with existing tools, no new code:** `coga usage --task <slug>
   --json` (tokens, elapsed, turns), `coga launch <slug> --prompt-report`
   (prompt size with/without contexts), and time-to-first-edit from the
   first commit timestamp on each branch minus `started_at` in the usage
   record.
4. **Store the receipts** as a markdown table in `docs/` or on the
   `marketing/post-doc-as-cache` blackboard, with the log line and commit
   SHA per row — same "recompute it yourself" discipline as the velocity
   report, at a fraction of its cost.
5. **Mechanism choice:** manual protocol (owner or an agent on a `direct`
   workflow) is enough for 4–6 pairs; a recurring ticket is overkill and a
   `ticket.py` cannot launch agents. Recommend: one `direct`-workflow
   ticket, `marketing/token-receipts`, assigned to an agent, run once per
   chosen pair.

Weak spot: the A arm (no contexts) also drops the repo `context.md`
layer? No — `--prompt-report` shows `repo_context` is a separate layer
from ticket contexts, so `contexts: []` removes only the attached
contexts. Fine for the claim post 3 makes.

### 7. Prepared replies — do they exist?

**No.** The four prepared replies exist only as bullets in
`coga/contexts/marketing/plan/SKILL.md` ("Prepared replies" section).
Nothing under `docs/`, no marketing ticket carries drafted text, and
`marketing/post-async-megalaunch` has an empty blackboard. They need to be
written out before post 1 ships (owner to say where: probably the post-1
ticket's blackboard).

Community/OSS hygiene noticed along the way: no `CONTRIBUTING.md`, no
`CODE_OF_CONDUCT.md`, `.github/` has only the release workflow — no issue
or PR templates. Not blocking, but arrivals will notice.
