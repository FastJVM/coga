---
slug: marketing/phase-0-audit
title: Phase 0 audit
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts:
- marketing/plan
skills: []
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: human
  - name: report-to-coga
    skills: []
    assignee: agent
secrets: null
step: 2 (human-owns-and-finishes)
---

## Description

Audit what exists vs what the launch needs, per the phase 0 of
`marketing/plan`: the README top (does it tell the post's story?), the blog
and newsletter state, megalaunch and the blocker queue as narrative material
(real examples to quote in post 1 — non-Coga repos like multiply first),
community surfaces, and anything else the essay series depends on (the full
check list is in `## Context`). Two checks are called out because they are
easy to skip: **run the README quickstart end-to-end on a fresh
repo** (a broken first run burns every converted reader), and **assign the
token-measurement collection** post 3 needs during phases 1-2. Output: the
concrete phase-0 worklist, written to this ticket's blackboard.

## Context

**What this is.** An inventory of what exists versus what post 1 needs — not
a review of the plan or the pitch. `marketing/plan` is settled (fork A
pinned); this ticket checks its phase-0 preconditions against reality and
produces a worklist: what must be true before post 1 ships, who owns each
item. Fixing things is out of scope — that's `marketing/readme-top`,
`marketing/discord`, etc. Record findings, not repairs.

**Workflow shape.** `draft-for-human`: the agent runs every check it can
observe and drafts the worklist (step 1); the owner fills in what only they
can see and makes the two assignments (step 2); the agent records the final
worklist (step 3). The worklist lives on this ticket's blackboard, under a
`## Worklist` heading, one line per item: `[owner] item — status/evidence`.

### Checks the agent runs (step 1)

1. **README top** — read `README.md`. Does the first screen tell the post-1
   story (what it is, for whom, the day-shape: "an hour or two in the
   morning, then I leave")? Note the specific gaps for `marketing/readme-top`.
2. **Quickstart, end-to-end, from PyPI** — the reader's path, no
   substitutions: `uv tool install coga` / `pip install coga` into a fresh
   venv, a scratch git repo under the scratchpad, `coga init --user`, and
   `docs/getting-started.md` (where the README sends readers) as part of the
   path under test. Run `coga build` only as far as the first composed
   prompt / first launch attempt — do not let a nested agent run to
   completion. Record every step where the text and reality diverge.
   **Sequencing:** PyPI has `0.2.0`; this repo is `0.3.1`; the owner decided
   (2026-09-02) the launch release is **`1.0`**, published to PyPI before
   post 1. In step 1, check what PyPI serves: if it is still `0.2.0`, record
   that as the finding, run the rest of the path from this checkout
   (`pip install /home/n/Code/coga`) so the README text still gets tested,
   and mark the check "re-run from PyPI after 1.0". In step 3, after the
   owner has published, re-run the whole check from PyPI 1.0 — that run is
   the one that counts.
3. **Narrative material** — quotable, real examples for post 1, non-Coga
   repos first. Every Coga-run repo on this machine has a `coga/log.md`,
   `coga/tasks/`, and blocker history: `~/Code/multiply` (primary),
   `~/Code/admin`, `~/Code/magicator`, `~/Code/patents`, `~/Code/tablet`,
   `~/Code/xpllm`, `~/Code/coga-hosting-probes`, `~/Code/demo-hackathon`.
   Look for: actual questions agents queued via `coga block`, a real morning's
   answer-review-launch sequence, a megalaunch sweep. Collect 5–10 candidates
   with date + repo + the literal text. Put them on this ticket's blackboard
   under `## Narrative candidates`; `marketing/post-async-megalaunch` reads
   them from there. Read-only — do not modify those repos. `~/Code/admin`
   and `~/Code/patents` are likely confidential: flag any candidate whose
   literal text is not publishable rather than dropping it silently. If the
   non-Coga repos don't yield 5, say so — don't pad from this repo.
4. **Megalaunch state** — is it stable enough to be *described* in present
   tense without lying? Check recent tickets/log entries in this repo for
   megalaunch and watchdog failures. This is a narrative-honesty check, not
   a product review. (From `marketing/positioning`, not attached: comms
   must not promise the felt experience that Slack drops and
   megalaunch/watchdog polish are currently blocking.)
5. **Distribution surfaces** (public, agent fetches and reports):
   - Blog: https://deviantabstraction.com — last post date, newsletter
     signup present?, per-channel URL / analytics feasibility, any existing
     mention of Coga.
   - fastjvm.com — the owner's other venture (YC). Report what the site is
     and whether it has a place a Coga link would fit; audience overlap is
     an owner-only judgment (step 2).
   - HN: user `top256` (karma 213 at ticket authoring, account since 2016;
     `https://hacker-news.firebaseio.com/v0/user/top256.json`). Note recent
     submission pattern and whether the story-submission plan fits the
     account's history.
   - Reddit: `https://www.reddit.com/user/Let047/` — karma, which subreddits
     the owner is already active in (the plan only posts where already a
     member). Reddit often blocks unauthenticated fetches; if so, report
     that and leave it to step 2.
   - Lobste.rs — the owner has an account; username to be supplied by the
     owner in step 2. Check invite/tag fit for a story submission.
   - Community home — does a GitHub Discussions tab or Discord exist yet?
     (`marketing/discord` decides; this ticket just reports the state.)
6. **Token-measurement plan, drafted** — post 3 needs same-task-with-vs-
   without-contexts receipts collected during phases 1–2 (`--prompt-report`,
   schema-2 usage records; see `scripts/human_minutes.py` for the token
   ledger reader). Draft *how* it would be collected and by what mechanism
   (a recurring ticket? a script? manual?), so the owner only has to assign
   it.
7. **Prepared replies** — `marketing/plan` says to write them before post 1
   ships. Do they exist anywhere yet? Report.

### Owner-only items (step 2)

- **Bookface** — login-gated; owner reports standing and whether a pre-HN
  Bookface post is realistic on the planned timeline.
- **Lobste.rs username**, and Reddit/HN nuance the profile doesn't show.
- **fastjvm.com audience overlap** and whether to cross-link.
- **Publish `coga 1.0` to PyPI** before post 1 (decided 2026-09-02; bump
  `pyproject.toml` from 0.3.1 — a separate release ticket if the owner wants
  an agent to do it). Step 3 re-runs the quickstart against it.
- **Assign** the token-measurement collection (who/what, from the drafted
  plan).
- **Phase-1 thresholds** — the private success numbers the retro will be
  scored against (plan: "noted before publishing, privately is fine").

### Out of scope

- Any fix or rewrite (README, docs, quickstart bugs — file findings, and
  create follow-up tickets only if the owner asks in step 2).
- Re-opening fork A / the essay-series decision.
- Anything from the shelved proof-post apparatus.

**Scope decision (authoring, 2026-09-02).** The evaluator flagged checks 2
and 3 as each big enough to be their own ticket. Kept here deliberately —
the plan assigns the quickstart run to this ticket — but bounded: the
quickstart stops at the first launch attempt, and narrative mining is capped
at 5–10 candidates with an honest shortfall report. If either blows past
that, stop and note it on the worklist instead of finishing it here.

<!-- coga:blackboard -->

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
literal text is under `## Narrative candidates` below, which
`marketing/post-async-megalaunch` reads.

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
- **HN (`top256`):** karma 213, since 2016, 101 submissions. Three
  front-page hits in two years, all essay titles: "Why Tech Inevitability
  is Self-Defeating" (87 pts / 58 comments, 2025-10), "My bytecode
  optimizer beats Copilot by 2x" (47 / 35, 2025-07), "Computing Industry
  Doesn't Care about Performance" (32 / 19, 2024-11 — took on resubmission
  four days after a 1-pt first try). Both **Show HN** posts flopped (3 pts
  and 2 pts). The 2026-06-03 essay ("AI Delegation Starts with Inspectable
  Work") got 1 pt. Pattern: submits own essays, replies heavily when one
  hits, otherwise quiet. **The plan's "plain story submission, never Show
  HN" matches the account's history exactly**; the second-chance
  resubmission branch has precedent on this account. Coga has never been
  submitted.
- **Reddit (`Let047`):** every fetch returned 403 or a login wall.
  **Owner-only in step 2:** karma and the subreddits already joined.
- **Lobste.rs:** live site refused TLS from here; rules read from the
  site's open-source templates and tag pages. Invite-only; new accounts
  **cannot use the `show` tag or submit never-seen domains**; self-promo
  should stay under about a quarter of one's activity; the submit form has
  an "I am the author" checkbox; the `ai` tag is for *building* AI —
  AI-usage stories go under **`vibecoding`** (+ `practices`). Fit for a
  first-person essay on agent workflow: plausible but marginal — the site
  lists "personal productivity systems" and "management" as off-topic, so
  the post has to read as engineering practice. Owner supplies the
  username and account age in step 2 (new-user restrictions may apply).
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

## Narrative candidates

Collected 2026-09-03 from the non-Coga repos (read-only). Log format is
`[slug] [agent:X] blocked: <reason>`; human tags vary (`nick`, `nicktoper`,
`zach`).


### 1. 2026-07-20, magicator, queued question (judgment) answered same day
`~/Code/magicator/coga/log.md` lines 350, 355, 365, 367.

```
2026-07-20 11:38 [staticization/capture-and-correlate-generated-classes] [agent:claude] blocked: Peer review: capture is incomplete and fails silently. Measured on the branch's own flags against -Xlog:class+load, a trivial probe generated 32 classes at runtime and definitions.tsv recorded 3 — no capture.failure, exit 0. Three misses are structural to caller-site instrumentation, not fixable by patching: [...] Your 2026-07-19 22:14 resolution made native JVMTI the fallback 'only if a definition path has no instrumentable Java caller' — three such paths are now proven, so I need your call: move interception to JVMTI ClassFileLoadHook, or accept a documented completeness caveat that weakens the closed-world proof. [...] Branch left green and unmodified at 5425220a4.

2026-07-20 14:11 [staticization/capture-and-correlate-generated-classes] [human:nick] unblocked (asks resolved, still in_progress): Decision: pivot the current ticket to exhaustive raw JVM definition capture through a startup native JVMTI ClassFileLoadHook; do not accept a completeness caveat. This ticket will prove that every in-scope class definition is captured, regardless of whether it can yet be classified, correlated, or rewritten. [...] The current caller-site instrumentation is not a capture authority and the existing branch is not mergeable as-is.

2026-07-20 15:08 [staticization/capture-and-correlate-generated-classes] [agent:codex] blocked: Stock HotSpot JDK 21/25 does not emit JVMTI ClassFileLoadHook for hidden classes even with the required all-class and early-class capabilities [...] Need Nick to choose platform-specific JVM_LookupDefineClass interception, a patched HotSpot hook, or explicitly narrow the hidden-class guarantee (the last conflicts with the prior no-caveat decision).

2026-07-20 15:56 [staticization/capture-and-correlate-generated-classes] [human:nick] unblocked (blocked → active): Décision humaine : conserver une JVM HotSpot standard et élargir l'autorité de capture au niveau natif. ClassFileLoadHook reste la source primaire pour les définitions qu'il observe; un proxy JVMTI NativeMethodBind du point terminal ClassLoader.defineClass0/JVM_LookupDefineClass capture les octets des hidden classes avant d'appeler l'implémentation originale. Aucun patch HotSpot ni retour à l'instrumentation de call sites Java. [...]
```

Why: the agent cites the human's own prior ruling, shows its condition is now met, asks a binary product question, and leaves the branch untouched. Four decisions in one day, all in the log, one of them in French.

### 2. 2026-07-18/19, magicator, queued question with a terse answer then launch
`~/Code/magicator/coga/log.md` lines 245, 286, 288, 289, 290.

```
2026-07-18 15:46 [staticization/dynamic-class-identity-key] [agent:codex] blocked: Shape-input proposal ready for review — see '## Proposal — shape inputs' on the blackboard. Derived from JDK 21 source [...]; empirical byte-diffing was impossible because -Djdk.internal.lambda.dumpProxyClasses is a no-op on JDK 21/22/25. Four decisions needed before code: (1) classData is non-null for ORDINARY lambdas (useImplMethodHandle), so 'reject non-null classData' would abort legitimate lambdas — proposal is to instrument LambdaMetafactory above ClassDefiner and reject only unattributed hidden definitions; (2) proxy bytes embed a JVM-global $ProxyN counter so identical inputs give different bytes across runs, which false-positives the same-key/different-artifact integrity check — proposal is a name-only normalization of the proxy's own name, which is a sliver of the rejected canonicalizer and so needs your explicit approval, vs exempting proxies from byte-equality; (3) confirm the per-mechanism field lists in the proposal table; (4) CDS can substitute an archived lambda class — proposal is to pin CDS off for capture runs and assert it. Also FYI, a live defect on main: lambda names have no counter [...] so #804's name-keyed CapturedClassStore collides and silently overwrites.

2026-07-19 12:43 [bootstrap/orient] [human:nick] launched (assignee=claude, agent=claude)
2026-07-19 12:47 [staticization/dynamic-class-identity-key] [human:nick] unblocked (blocked → active): 1) ok but you need to test it extensibley 2) we could canonicalize and link name to class would that fix it? 3) show it to me 4) this didn't really work check the POC result
2026-07-19 12:49 [staticization/dynamic-class-identity-key] [human:nick] started (active → in_progress) via coga launch
2026-07-19 12:49 [staticization/dynamic-class-identity-key] [human:nick] launched (assignee=codex, agent=codex)
```

Why: the agent asks approval for "a sliver of the rejected canonicalizer" rather than assuming. The human orients at 12:43, answers four numbered points with typos at 12:47, launches at 12:49. Answer, review, launch in six minutes.

### 3. 2026-07-30, xpllm, morning sequence with a megalaunch tail
`~/Code/xpllm/coga/log.md` lines 1113 to 1141 (preceding block at line 1107).

```
2026-07-29 17:55 [sliceworldpoc/03-test-luindex-large-slice] [agent:codex] blocked: Manifest-pinned perfo-isolated/home4 is continuously owned by an external multi-cell bench10 campaign (currently bench10-xalan-codeonly-a3n-oc-gpt56-5m); zero Luindex attempts were consumed. Retry after .xp1-runner.lock remains free for at least 20 seconds without changing the frozen home or payload.

2026-07-30 07:50 [sliceworldpoc/04-test-spark-catalyst-codegen-slice] [human:nick] task done — Recorded the Spark Catalyst codegen-slice n=1 outcome.
2026-07-30 07:50 [sliceworldpoc/05-test-sunflow-engine-slice] [megalaunch] started (active → in_progress) via coga megalaunch
2026-07-30 09:16 [sliceworldpoc/05-test-sunflow-engine-slice] [human:nick] task done — Banked the Sunflow V1/V2/V3 n=1 screen.
2026-07-30 09:16 [sliceworldpoc/06-synthesize-the-n-1-results] [megalaunch] started (active → in_progress) via coga megalaunch
2026-07-30 09:17 [sliceworldpoc/06-synthesize-the-n-1-results] [agent:codex] blocked: Waiting on sliceworldpoc/03-test-luindex-large-slice: it remains blocked with zero paid cells consumed and no research/sliceworldpoc/luindex/results-n1.json; complete that workload to a terminal recorded outcome before four-result synthesis.
2026-07-30 10:04 [sliceworldpoc/03-test-luindex-large-slice] [human:nick] unblocked (blocked → active): fixed!
2026-07-30 10:04 [sliceworldpoc/03-test-luindex-large-slice] [human:nick] launched (assignee=codex, agent=codex)
2026-07-30 10:07 [recurring/autoclose-merged] [human:nick] launched (assignee=claude, agent=claude)
2026-07-30 10:08 [recurring/digest] [human:nick] launched (assignee=claude, agent=claude)
2026-07-30 12:19 [sliceworldpoc/03-test-luindex-large-slice] [human:nick] task done — Banked the Luindex V1/V2/V3 n=1 screen.
2026-07-30 12:27 [sliceworldpoc/06-synthesize-the-n-1-results] [human:nick] unblocked (blocked → active): Dependency satisfied: sliceworldpoc/03-test-luindex-large-slice reached a terminal 'done' outcome and research/sliceworldpoc/luindex/results-n1.json now exists. All four workloads have recorded results-n1.json files (xalan, luindex, spark-catalyst, sunflow). Spark Catalyst's is a recorded scorer-casualty outcome with null scores — synthesize it as an invalid/unmeasured cell, do not rerun it.
2026-07-30 15:03 [sliceworldpoc/06-synthesize-the-n-1-results] [human:nick] task done — Synthesized the sliceworldpoc n=1 results and n=5 recommendation.
```

Why: a real morning. The previous afternoon's sweep rolls into 07:50, the synthesis agent refuses to synthesize three of four results, the human writes "fixed!" at 10:04 and relaunches, runs the recurring jobs, and the chain is unblocked by lunch and done by 15:03.

### 4. 2026-07-24, magicator, queued question that refuses to design unattended
`~/Code/magicator/coga/log.md` line 635 (siblings at 628 to 643).

```
2026-07-24 21:30 [magicator/observation-loop-framework] [agent:claude] blocked: Do not launch the agent design step. Owner is designing this loop with the agent in conversation, not via an unattended design run: the open decisions are the probe contract, the typed observation shape replacing the stringly-typed map, convergence semantics, run-loop ownership, and unification of the bytecode and native collector channels. Those are owner architecture calls. Unblock only when the joint design is done and the ticket list is being written.

2026-07-24 21:29 [staticization/replay-named-generated-definitions] [agent:claude] blocked: Blocked behind staticization/inject-and-rewire, which is itself blocked on magicator/observation-loop-framework. This ticket reuses the injector's materializer and layout writer and cannot start before they exist. Do not fork them.
```

Why: the cleanest statement of the thesis. The agent lists five architecture decisions and says they are not its to make. Six sibling tickets self-blocked within four minutes (21:29 to 21:34), one ending "Do not fork them."

### 5. 2026-07-05, xpllm, queued question with a stated default
`~/Code/xpllm/coga/log.md` line 265.

```
2026-07-05 17:33 [benchmark/run-the-benchmark-baseline] [agent:claude] blocked: zxing baseline complete as the reference workload (committed 4da725a: selftest correct ~1.0x, preflight clean, A/A floor n=3 [0.985/0.990/1.011], JFR decode-dominant 100% app-code). Before replicating to the other 4 DaCapo workloads, need 2 decisions (large 4-5x rework cost each; details on blackboard): (1) SHAPE: zxing isolates the decode hot path via a pre-encoded pool because the faithful round-trip profiled ENCODE-dominant — keep 'isolate the profiled hot path' for the rest, or build faithful whole-workload round-trips? (2) SOURCING: I vendored CURRENT upstream zxing 3.5.3, not DaCapo's old bundled version — use current maintained upstream for all 5 (avrora/sunflow are Java-1.4-era & build-hostile in DaCapo form), or must each match DaCapo's exact version for report fidelity? Default if unanswered: current-upstream + isolate-hot-path.
```

Why: research-design judgment with the rework cost and a default named. Answered in an agent-mode session at 19:59 ("launched in agent mode"); ticket done at 21:48 the same night with all five workloads banked.

### 6. 2026-07-16, xpllm, queued question that stops a paid experiment
`~/Code/xpllm/coga/log.md` lines 633 and 648.

```
2026-07-16 17:30 [magicator-llvm/06-run-the-a2-a3-gate-on-llvm-emitted-slices] [agent:claude] blocked: Current LLVM artifact retains 155/157 instructions (98.7%), all user functions, and all globals, so A3 would test whole-program IR prompting rather than useful slicing. Redesign the slicing criterion/semantic summary or use a larger haystack subject that yields material reduction before launching paid Opus/Fable A3 cells.

2026-07-16 18:46 [magicator-llvm/06-run-the-a2-a3-gate-on-llvm-emitted-slices] [human:nick] unblocked (blocked → active): Owner resolved: stop this gate as inconclusive, publish the neutral result, and move the next attempt to a larger program with a material-reduction admission gate.
```

Why: the agent noticed the experiment would be meaningless and declined to spend money. Answered in 76 minutes.

### 7. 2026-07-29, magicator, morning triage where agents queue themselves
`~/Code/magicator/coga/log.md` lines 779 to 800; unblock at 868.

```
2026-07-29 11:20 [observation-loop/rebuild/1-remove-the-legacy-instrumentation-pipeline] [human:nick] created (status=draft)
  (five more rebuild tickets created at 11:20)
2026-07-29 11:31 [observation-loop/1-site-identity-and-the-site-table] [human:nick] canceled (in_progress → canceled): Superseded after closing PR #831; replaced by the ordered observation-loop/rebuild ticket sequence.
2026-07-29 11:33 [observation-loop/2-generic-site-rules] [human:nick] canceled (blocked → canceled): Superseded by observation-loop/rebuild; this ticket depends on the legacy Instrumentor architecture that the rebuild intentionally removes.
  (tickets 3, 4, 5, 6 canceled at 11:35, 11:36, 11:37, 11:39)
2026-07-29 11:41 [observation-loop/rebuild/2-emit-compiler-source-translation-metadata] [human:nick] activated (draft → active) — Queued behind removal of the legacy instrumentation pipeline.
2026-07-29 11:41 [observation-loop/rebuild/2-emit-compiler-source-translation-metadata] [agent:claude] blocked: Sequencing: blocked behind observation-loop/rebuild/1-remove-the-legacy-instrumentation-pipeline.
2026-07-29 11:41 [observation-loop/rebuild/3-build-the-observation-loop-from-scratch] [agent:claude] blocked: Sequencing: blocked behind observation-loop/rebuild/2-emit-compiler-source-translation-metadata.
2026-07-29 11:41 [observation-loop/rebuild/4-add-site-ids-for-instrumented-instructions] [agent:claude] blocked: Sequencing: blocked behind observation-loop/rebuild/3-build-the-observation-loop-from-scratch.
2026-07-29 11:42 [observation-loop/rebuild/5-final-observation-loop-cleanup] [agent:claude] blocked: Sequencing: blocked behind observation-loop/rebuild/4-add-site-ids-for-instrumented-instructions.

2026-07-30 11:58 [observation-loop/rebuild/3-build-the-observation-loop-from-scratch] [human:nick] unblocked (blocked → active): observation-loop/rebuild/2-emit-compiler-source-translation-metadata is done — merged as ed67a63a2 (PR #835) on 2026-07-30 — so the sequencing dependency is satisfied.
```

Why: 22 minutes of human triage (six created, six canceled, four activated), then each activated ticket blocks itself with a one-line reason instead of starting work it cannot do. Unblocks come over the following days, each citing the merged PR.

### 8. 2026-07-22, magicator, megalaunch sweep
`~/Code/magicator/coga/log.md` lines 486 to 521; counterpoint at 1420 to 1422.

```
2026-07-22 21:45 [docs-migration/cluster-b-migrate-slicing-and-heap-soundness-docs] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-07-22 21:45 [docs-migration/cluster-c-migrate-loop-optimization-docs-to-a-new] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-07-22 21:45 [docs-migration/cluster-d-migrate-system-slice-cache-docs-to-a-new] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-07-22 21:45 [docs-migration/cluster-e-migrate-operating-model-docs-into-runboo] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-07-22 21:45 [docs-migration/cluster-f-migrate-benchmark-and-sota-docs-into-ben] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-07-22 21:45 [docs-migration/cluster-g-re-audit-the-source-only-magicator-conte] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-07-22 21:45 [docs-migration/cluster-b-migrate-slicing-and-heap-soundness-docs] [megalaunch] started (active → in_progress) via coga megalaunch
2026-07-22 21:45 [docs-migration/cluster-b-migrate-slicing-and-heap-soundness-docs] [megalaunch] launched via coga megalaunch
2026-07-22 21:52 [docs-migration/cluster-c-migrate-loop-optimization-docs-to-a-new] [megalaunch] started (active → in_progress) via coga megalaunch
2026-07-22 22:00 [docs-migration/cluster-d-migrate-system-slice-cache-docs-to-a-new] [megalaunch] started (active → in_progress) via coga megalaunch
2026-07-22 22:17 [docs-migration/cluster-e-migrate-operating-model-docs-into-runboo] [megalaunch] started (active → in_progress) via coga megalaunch
2026-07-22 22:27 [docs-migration/cluster-f-migrate-benchmark-and-sota-docs-into-ben] [megalaunch] started (active → in_progress) via coga megalaunch
2026-07-22 22:50 [docs-migration/cluster-g-re-audit-the-source-only-magicator-conte] [megalaunch] started (active → in_progress) via coga megalaunch

2026-08-26 11:40 [coga/give-recipe-run-recurring-tasks-a-durable-run-hist] [megalaunch] started (active → in_progress) via coga megalaunch
2026-08-26 11:43 [coga/give-recipe-run-recurring-tasks-a-durable-run-hist] [agent:claude] blocked: Owner-decision ticket on a code workflow: pick option 1-4 under '## Options' on the blackboard. Investigation changed the premise — coga #705 (df1d0602) deleted the recipe-direct dispatch, so no template fires without an agent any more [...] Decision needed: (a) do nothing [...]; (b) new coga/contexts/repo/recurring-runs stating 'log, not blackboard' [...]; (c) standardize a bounded '## Last run' block, which needs upstream coga work this repo cannot do; (d) land the ticket.py shims first and re-ask. Recommend (b) or (d). Also: re-route this ticket to decide/with-owner.
```

Why: six tickets picked in one minute, executed serially over 65 minutes with no human line in between. The 2026-08-26 counterpoint shows a megalaunched ticket blocking three minutes in with a four-option owner question and a recommendation.

### 9. 2026-08-27 and 2026-09-01, admin, megalaunch sweeps. CONFIDENTIALITY: check before publishing
`~/Code/admin/coga/log.md` lines 1278 to 1304 and 1512 to 1642.

```
2026-08-27 09:19 [doc-updates/count-repo-wide-refs-by-matching-both-yaml-frontma] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-08-27 09:20 [admin/decide-whether-the-vendored-browser-and-google-age] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-08-27 09:20 [admin/stop-shipping-one-off-tickets-as-contextless-stubs] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-08-27 09:20 [make/refresh-the-four-inventory-tables-against-shipped] [megalaunch] activated (draft → active) — explicit megalaunch pick
2026-08-27 09:20 [doc-updates/count-repo-wide-refs-by-matching-both-yaml-frontma] [megalaunch] started (active → in_progress) via coga megalaunch
2026-08-27 09:33 [doc-updates/count-repo-wide-refs-by-matching-both-yaml-frontma] [agent:claude] advanced to step 2 (peer-review) → assigned to codex — implement done on branch generate-ref-c
2026-08-27 09:42 [doc-updates/count-repo-wide-refs-by-matching-both-yaml-frontma] [agent:codex] advanced to step 3 (open-pr) → assigned to claude
2026-08-27 09:42 [doc-updates/count-repo-wide-refs-by-matching-both-yaml-frontma] [agent:claude] advanced to step 4 (review) → assigned to zach — PR opened: https://github.com/FastJVM/admin/p[...]
2026-08-27 09:42 [admin/decide-whether-the-vendored-browser-and-google-age] [megalaunch] started (active → in_progress) via coga megalaunch
2026-08-27 09:49 [admin/decide-whether-the-vendored-browser-and-google-age] [agent:claude] advanced to step 2 (peer-review) → assigned to codex
2026-08-27 09:58 [admin/decide-whether-the-vendored-browser-and-google-age] [agent:codex] advanced to step 3 (open-pr) → assigned to claude
2026-08-27 09:59 [admin/decide-whether-the-vendored-browser-and-google-age] [agent:claude] advanced to step 4 (review) → assigned to zach — PR opened: https://github.com/FastJVM/admin/pull/16
2026-08-27 09:59 [admin/stop-shipping-one-off-tickets-as-contextless-stubs] [megalaunch] started (active → in_progress) via coga megalaunch
```

The 2026-09-01 11:26 sweep (lines 1512 to 1523) activated twelve tickets in one minute; the human then ran seven recurring jobs by hand between 11:28 and 11:35 (repo-guards, tm-action-reminder, autoclose-merged, digest, monthly-one-off-review-reminder, supplier-payment-reminder, xero-reconcile) while the first megalaunched ticket went implement (11:26) to peer-review (11:38) to open-pr (11:47) to human review (11:49).

Why: two PRs reach human review in 40 minutes, with implement, peer-review, and open-pr handed agent-to-agent and no human line in between.

Sensitive: this is the company admin repo and the human is `zach`, not the essay's narrator. The 2026-09-01 window sits next to Slack posts naming a trademark office action serial number ("FASTJVM (sn99766075) was served August 28, 2026"), a Xero monthly reconcile, and supplier renewals ("fastjvm.com on February..."). The ticket slugs and step-advance lines quoted above look safe; the Slack lines are not.

### 10. 2026-08-19/20, admin, queued questions where the human overrules the recommendation. CONFIDENTIALITY: check before publishing
`~/Code/admin/coga/log.md` lines 887, 890, 1110, 1125.

```
2026-08-19 14:30 [make/quarterly-password-rotation] [agent:codex] blocked: admin/security-review must settle or explicitly approve the human-login rotation scope before this live reminder can ship; Zach must also confirm or change the proposed 0 9 20 1,4,7,10 * schedule.
2026-08-19 15:01 [make/quarterly-password-rotation] [human:zach] unblocked (blocked → active): Both asks resolved by Zach 2026-08-19 (bootstrap/orient session).

2026-08-20 14:49 [attach-the-four-orphaned-contexts-to-the-tickets-a] [agent:codex] blocked: Implementation already landed directly on origin/main at 7ea9876, and the freshly rebased feature branch has zero commits/diff, so the required open-pr step cannot run. Owner decision needed: close or skip the PR step, and delete accounting/transition (recommended) or retain it unattached.
2026-08-20 15:07 [attach-the-four-orphaned-contexts-to-the-tickets-a] [human:zach] unblocked (blocked → active): Owner decision (zach, 2026-08-20): skip the open-pr step. The change already landed on origin/main at 7ea9876 and the rebased branch is empty, so there is no diff to open a PR from; peer review was completed against the landed commit instead. Keep accounting/transition — do NOT delete it; retained deliberately for now, unattached.
```

Why: "delete (recommended)" answered with "do NOT delete" is exactly why the question was queued instead of guessed. Both answered within 31 and 18 minutes.

Sensitive: password-rotation policy and a security-review ticket name; the nearby Brex block at line 1019 (2026-08-19 16:16) names a Brex integration ID, API endpoints, and month-by-month missing-GL counts and should not be quoted. The blackboard at `~/Code/admin/coga/tasks/admin/stage-the-uncovered-goal-2-obligations-that-have-n.md:239` ("Open questions for Zach — three of the five need a fact I do not have": whether Gusto files Form 940 and W-2/W-3, whether any contractor was paid $600 or more, whether the company is registered with the City of San Francisco, "Jacob files the return") is a good agent-asks-human example but contains payroll and tax detail plus a named accountant.

### 11. Mechanical spares (use only if a credential/infra example is wanted)

- xpllm line 706/707, 2026-07-19 12:42: `blocked: Claude OAuth was revoked during Haiku zxing raw (401, zero tokens). Refresh the host Claude login at /home/n/.claude/.credentials.json, then tell the agent to resume; preserved t1/t2 casualties must be rerun.` Answered 12:50: `Nick refreshed Claude subscription OAuth; bounded exact-Haiku real-token check passed with allowed rate limit and no auth/fallback error.`
- xpllm lines 701/709/712/713, 2026-07-18 to 07-20: `Fable organization monthly usage limit exhausted during sunflow A3 t2; explicit provider reset is 2026-07-19 09:00 PDT.` then `Paused safely at Nick's request before PC sleep. Await explicit restart signal` then `Nick gave the explicit restart signal at 2026-07-20 13:50 PDT; post-sleep process/home/preflight checks are clean.`
- demo-hackathon lines 64 to 77, 2026-07-17 21:08 to 22:15: DNS and read-only-git blocks answered with `network is here` (21:12) and `GitHub access restored` (22:15), each followed by a `[megalaunch] activated (blocked → active) — explicit megalaunch pick` within a minute.
- tablet line 32 and multiply line 151: the recurring resolve-conflicts wrapper blocking because `'coga launch bootstrap/resolve-conflicts' refuses without a TTY`. Tooling anecdote only.
- multiply lines 74 and 77, 2026-08-18: `blocked: Launch gate unmet: spike-the-codex-plugin-lifecycle [...] has not run; its findings on client surfaces, hook timing, and writable plugin state must land and be attached before this design can assume a capture/buffering mechanism. Human chose to park until the spike lands.` Both canceled the next morning at 11:34 during a 24-action pivot (lines 84 to 125: eight tickets canceled, sixteen created in 21 minutes). Weak as a judgment example because the human's decision is recorded as a cancel, not an answer.

### Best picks

- **Best morning sequence:** xpllm 2026-07-30 07:50 to 12:27, `~/Code/xpllm/coga/log.md` lines 1113 to 1141 (candidate 3). Runner-up: magicator 2026-07-19 12:43 to 12:56, lines 286 to 292 (candidate 2): orient at 12:43, four-point answer at 12:47, launch at 12:49 and again at 12:56.
- **Best megalaunch sweep:** magicator 2026-07-22 21:45 to 22:50, `~/Code/magicator/coga/log.md` lines 486 to 521 (candidate 8): six tickets activated in one minute, executed serially over 65 minutes. Runner-up: xpllm 2026-07-29 14:49, lines 1091 to 1118, six sliceworldpoc tickets activated in one minute and executed serially through the next morning (14:49, 15:19, 16:43, 17:56, then 07:50 and 09:16 on 07-30). Largest by count: admin 2026-09-01 11:26, twelve tickets in one minute (confidentiality check needed).

### Shortfall statement

No shortfall. There are ten candidates across the non-Coga repos: eight strong ones with no confidentiality concern (six judgment questions, one morning sequence, one clean sweep, all from magicator and xpllm), plus two admin items that need a confidentiality pass. The weak repos are multiply (three blocks, all "launch gate unmet", canceled the next morning in a pivot), patents (zero block events, one sequential sweep of five tickets on 2026-07-22 15:14 to 16:09), tablet and demo-hackathon (mechanical blocks only). coga-hosting-probes is a duplicate checkout of multiply and adds nothing.

## Worklist

Draft from step 1. `[owner]` is who must act; `[?]` means the owner decides
in step 2 whether it becomes a ticket, who takes it, or whether it is
accepted as-is. Ordered: blockers for post 1 first.

**Blocking post 1**

- [nicktoper] Publish `coga 1.0` to PyPI — PyPI serves 0.2.0 and 0.2.0's `coga init` crashes; 0.3.1's `init` pip-installs its own version from PyPI into the vendored venv, so nothing works from PyPI until 1.0 is there. Release path: GitHub Release → `.github/workflows/release.yml` (Trusted Publishing). Bump `pyproject.toml` from 0.3.1.
- [?] Fix or re-floor Python 3.11 — `coga init` crashes on 3.11 on every version (`src/coga/resources/` lacks `__init__.py` → `MultiplexedPath.joinpath(*parts)` is 3.12+). Either ship the `__init__.py` fix in 1.0 or change `requires-python` and both docs to 3.12+. Must land before 1.0.
- [nicktoper, step 3 agent] Re-run the quickstart from PyPI 1.0 in a real terminal — step 1 run stopped at the TTY gate; the Claude Code spawn itself was not exercised.
- [marketing/discord] Community home — nothing exists: Discussions disabled (404), no Discord link, no repo homepage URL. Decide and create before post 1.
- [marketing/readme-top] README first screen — add the day-shape sentence and the internal-tool envelope; pull "for whom" above the fold; decide whether "Measured on itself" (31 workstreams) moves below the primitives. "Acting as the CPU" is already there.
- [nicktoper] Prepared replies — none exist outside the plan's bullets; write the four out (suggest: `marketing/post-async-megalaunch` blackboard).
- [nicktoper] Confidentiality pass on narrative candidates — confirm `magicator`/`xpllm` lines (research direction) are quotable; rule on admin candidates 9 and 10 (Zach's repo; trademark/Xero/payroll lines nearby).

**Owner-only decisions (step 2)**

- [nicktoper] Assign token-measurement collection — draft mechanism in check 6: one `direct`-workflow ticket `marketing/token-receipts`, 4–6 ticket pairs (`<slug>` vs `<slug>-nocontext` copy with `contexts: []`), receipts from `coga usage --task --json` + `--prompt-report` + first-commit timestamp; no new code needed.
- [nicktoper] Phase-1 thresholds — private success numbers before publishing (subscribers, community joins, referrer split; installs are not the bar).
- [nicktoper] Bookface standing and whether a pre-HN post fits the timeline — login-gated.
- [nicktoper] Lobste.rs username + account age — invite-only; new accounts can't use `show` or submit unseen domains; tag would be `vibecoding` + `practices`, not `ai`; self-promo under ~¼ of activity. Fit is marginal ("productivity systems" is off-topic there).
- [nicktoper] Reddit — profile unreachable unauthenticated; report karma and joined subreddits.
- [nicktoper] fastjvm.com cross-link — single-page research index with GA; no blog/team/about slot; links to `manycore-com` org, not `FastJVM`. Decide yes/no.
- [nicktoper] Blog readiness — WordPress.com, last post 2026-06-02 (three months quiet), Jetpack subscribe block exists, Jetpack Stats shows referrers only (no UTM table). Decide whether referrer-level attribution is enough for the phase decisions.

**Findings for triage (file tickets only if the owner asks)**

- [?] PyPI `0.0.1` placeholder — on a 3.9/3.10 default `python3`, `pip install coga` silently installs the 1 KB placeholder with no `coga` binary. Consider yanking 0.0.1 so pip errors instead, and say in getting-started what the failure looks like.
- [?] `coga init` hard-codes `control_branch = "main"` — on a machine whose `git init` makes `master`, every command prints the control-branch nag 2–3 times. Init should detect the current branch or the docs should say to set it.
- [?] First-run noise — `coga status` in a one-minute-old repo lists six recurring jobs as "due — not created"; `init` installs seven managed skills (incl. `google-agents-cli-*`) and pip-installs gmail/google-calendar deps into a stranger's repo. Decide whether that is the intended first impression.
- [?] Empty-repo `init` crashes with a `ConfigError` traceback when a bare `SLACK_WEBHOOK_URL` is in the environment; the existing-project path handles the same case with a tip. Edge case.
- [?] Megalaunch honesty — describable in present tense (real sweeps 08-26, 09-02 here; 07-22 magicator; 09-01 admin). Open bugs: `megalaunch-activates-picks-before-preflight` (at review), `launch-activates-before-preflight` (in progress). Keep the positioning caveat; no crashes in the last two weeks, failures are DNS/Slack.
- [?] Repo hygiene arrivals will see — 3 stars, 17 open PRs, 0 issues, no `CONTRIBUTING.md` / code of conduct / issue templates, repo description "A blackboard for humans and agents" differs from the README tagline. Optional before post 1.
- [?] HN plan fit — confirmed: three front-page hits were plain essay titles; both Show HNs flopped; a resubmission four days later took once. Nothing to do.
- [?] Demo video (README line 18) — check it still matches current CLI names before it is reused.
