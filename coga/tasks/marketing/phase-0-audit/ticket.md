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
   in `narrative-candidates.md` beside this ticket (they were on the
   blackboard until 2026-09-03 and were moved out to keep composed prompts
   small); `marketing/post-async-megalaunch` reads them from there. Note the
   owner has since ruled all of them unpublishable. Read-only — do not modify those repos. `~/Code/admin`
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
   - HN: user `top256` (karma 213, confirmed unchanged by the owner on
    2026-09-03 — flat since ticket authoring, consistent with the quiet
    pattern below; account since 2016;
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

## Findings — moved to attachments

The full step-1 evidence lived here and pushed the blackboard to 58 KiB, all
of which composes into every launch prompt for this task. It is moved, not
deleted:

- **`step-1-findings.md`** — the seven checks in full: README top gaps, the
  quickstart run table with every divergence between the docs and reality,
  megalaunch narrative honesty, the distribution surfaces, the
  token-measurement mechanism draft, and prepared replies. Read it before
  re-running any check.
- **`narrative-candidates.md`** — the ten candidates with literal log text,
  the per-repo table, best picks, and the shortfall statement. **The owner
  ruled every one unpublishable on 2026-09-03**, so this is evidence of the
  practice, not source material for a post.

**Headline results, so this file stands alone.** There is no working first run
from PyPI today: 0.2.0's `coga init` crashes, 3.11 crashes on every version,
and 0.3.1 needs its own version already on PyPI to vendor itself. The README
first screen carries neither the day-shape nor the internal-tool envelope. The
community home does not exist. The prepared replies do not exist. All ten
narrative candidates are confidential. Nine of the resulting fixes are
ticketed under `coga/tasks/cleanup/`.

Everything below is the ticket's actual output and stays here.

## Worklist

Draft from step 1, updated with the owner's step-2 decisions (2026-09-02).
`[owner]` is who must act; `[?]` items are deferred by the owner ("will do
later") and stay open for a later pass. Ordered: blockers for post 1 first.

**Step 2 decisions (owner, 2026-09-02)**

- **A `cleanup/` task directory now holds everything the owner wants done
  before the marketing materials ship** (owner's words, 2026-09-03). Nine
  drafts; see `coga/tasks/cleanup/README.md`. Drain with
  `coga megalaunch cleanup`.
- 1.0 release: ticketed as `cleanup/publish-coga-1-0-to-pypi` (draft,
  `brief-for-human`); the owner will run it later, not as part of this audit.
- Python 3.11 crash: fix, not re-floor. Ticketed as
  `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` (draft,
  `code/with-review`). Must land before the release.
- Narrative candidates: all confidential, none publishable (see ruling above).
  Non-Coga repos therefore yield zero quotable examples; this is the shortfall
  the ticket asked to report honestly.
- Token measurement: accepted as drafted in check 6. Assigned to an agent on
  a `direct`-workflow ticket `marketing/token-receipts`, to be created when
  phase 1 starts.
- Owner-only facts (Lobste.rs, Reddit, Bookface, fastjvm.com, blog analytics)
  and phase-1 thresholds: still open, nothing on record yet.
- Triage findings: all ticketed into `cleanup/` except the two that needed no
  action at the time (megalaunch honesty, HN plan fit). **HN plan fit was
  later superseded** — see its entry below.
- Demo video: checked as far as read-only access allows (see the finding
  below); the 95 seconds of watching are ticketed.

**Blocking post 1**

- [nicktoper] Publish `coga 1.0` to PyPI — ticketed: `cleanup/publish-coga-1-0-to-pypi` (draft). PyPI serves 0.2.0 and 0.2.0's `coga init` crashes; 0.3.1's `init` pip-installs its own version from PyPI into the vendored venv, so nothing works from PyPI until 1.0 is there. Release path: GitHub Release → `.github/workflows/release.yml` (Trusted Publishing); runbook in `docs/releasing.md`.
- [agent] Fix Python 3.11 — ticketed: `cleanup/fix-coga-init-crash-on-python-3-11-by-adding-the-r` (draft). Add `src/coga/resources/__init__.py` (`MultiplexedPath.joinpath(*parts)` is 3.12+). Owner chose the fix over re-flooring. Must land before 1.0.
- [nicktoper, step 3 agent] Re-run the quickstart from PyPI 1.0 in a real terminal — step 1 run stopped at the TTY gate; the Claude Code spawn itself was not exercised.
- [marketing/discord] Community home — nothing exists: Discussions disabled (404), no Discord link, no repo homepage URL. Decide and create before post 1.
- [marketing/readme-top] README first screen — add the day-shape sentence and the internal-tool envelope; pull "for whom" above the fold; decide whether "Measured on itself" (31 workstreams) moves below the primitives. "Acting as the CPU" is already there.
- [nicktoper] Prepared replies — none exist outside the plan's bullets; write the four out (suggest: `marketing/post-async-megalaunch` blackboard).
- [BLOCKS POST 1 — plan premise failed] Narrative material. Owner ruled all ten non-Coga candidates confidential, then concluded (2026-09-03): **"the plan doesn't work; the only thing we can use is coga building coga as evidence, and we don't have a real plan yet."** This is the audit's most consequential finding and it is a *precondition failure*, not a worklist item. See `## Plan premise failure` at the end of this blackboard. `marketing/post-async-megalaunch` cannot be written to the current plan.

**Owner-only decisions (step 2)**

- [agent] Token-measurement collection — assigned (owner accepted check 6 as drafted): one `direct`-workflow ticket `marketing/token-receipts`, 4–6 ticket pairs (`<slug>` vs `<slug>-nocontext` copy with `contexts: []`), receipts from `coga usage --task --json` + `--prompt-report` + first-commit timestamp; no new code. Create the ticket when phase 1 starts.
- [answered 2026-09-03] Lobste.rs — `ntoper`, created 2025-06-05, karma 55, one prior self-authored submission of a `deviantabstraction.com` essay at 26 points / 19 comments. Not a new account; the domain is already seen and well received. Tags: `vibecoding` + `practices`, never `ai` (verified against `/tags.json`). Full detail in check 5 above. Nothing left for the owner here beyond deciding to submit.
- [decided 2026-09-03] fastjvm.com cross-link — **announce the launch there, but treat it as unimportant short term** (owner). So: add a Coga mention or link at launch, do not count fastjvm.com as a phase-1 channel, do not include it in the attribution measurement, and do not let it block post 1. The agent's recommendation had been to skip it entirely on the grounds that a single-page research index has no natural slot and its readers are JVM performance researchers rather than post 1's audience; the owner's call keeps the announcement anyway at near-zero cost, while agreeing it carries no short-term weight.
- [recommendation, owner to confirm] Blog attribution — **recommend accepting referrer-level and not buying analytics.** The phase decision asks which channel sent traffic; HN, Lobsters, Reddit and the newsletter are four distinct referrer domains, so Jetpack Stats separates them cleanly. What it cannot do is split two links posted to the same channel or attribute a subscriber to a channel, and neither changes a phase-1 decision. **One hard prerequisite:** record the pre-publication baseline — current subscriber count and monthly views — before post 1 goes out, or every delta below is unmeasurable.
- [partly answered 2026-09-03] Reddit (`Let047`) — owner supplied: 7,781 karma, 2,609 contributions, 6 years old, 56 followers. Established account, so the cold-account failure mode the plan worried about does not apply. **Outstanding: the joined-subreddit list**, which the public profile does not expose and which decides whether Reddit is in the channel set at all.
- [nicktoper, still owner-only] Bookface standing and whether a pre-HN post fits the timeline — login-gated to YC; no external check is possible.
- [nicktoper, proposed below] Phase-1 thresholds — a grounded proposal is in `## Proposed phase-1 thresholds`; the owner accepts or adjusts. Note this repo is public, so anything recorded here is public too.

**Findings for triage — owner dispositions (2026-09-03)**

Seven of the eight are now drafts under `cleanup/`. Two needed no action.

- [cleanup/yank-the-pypi-0-0-1-placeholder-and-document-the-f] PyPI `0.0.1` placeholder — owner: yes. Yanking survives the 1.0 release: every real release requires >= 3.11, so a 3.9/3.10 interpreter still resolves to the placeholder unless it is yanked.
- [cleanup/add-a-debug-mode-to-init-for-vendoring-from-source] Debug mode, build-from-source vs release — owner's own addition when triaging the init findings. `COGA_REPO_URL` is today's undocumented workaround; make the distinction explicit. `code/design-then-implement`.
- [cleanup/detect-the-current-git-branch-instead-of-hard-codi] `control_branch = "main"` nag on a `master` repo — ticketed.
- [cleanup/quiet-the-first-run-noise-from-recurring-jobs-and] First-run noise (six "due — not created" recurring rows; seven managed skills incl. `google-agents-cli-*` pip-installing gmail/calendar deps) — ticketed with a design step, because "is this the intended first impression?" is a decision before it is a fix.
- [cleanup/handle-a-bare-slack-webhook-url-during-empty-repo] Empty-repo `init` `ConfigError` traceback with a bare `SLACK_WEBHOOK_URL` — ticketed; make it match the existing-project path's tip.
- [cleanup/add-contributing-docs-issue-templates-and-a-repo-d] Repo hygiene — ticketed (owner: "see previous points"). `CONTRIBUTING.md`, code of conduct, issue/PR templates, repo description and homepage URL. Stops short of the community-home decision, which is `marketing/discord`'s.
- [cleanup/check-the-demo-video-against-current-cli-names] Demo video — **checked read-only 2026-09-03.** Uploaded 2026-07-18, 95 s, no captions, no description, so its content cannot be verified without watching it. CLI surface diff from the last pre-upload commit (`0c8eb75e`) to `main`: **`coga project` is the only command from that era that no longer exists** (removed in `8394d3b3`, PR #691; `coga build` was removed in the same commit and restored by #701). `coga open-pr` became an alias for the `coga run open-pr` recipe with the spelling unchanged, so it is still correct on screen. No mention of `coga project` survives in README, docs, or contexts — the video is the last place it could appear. Remaining work: 95 seconds of a human watching for that one name.
- [accepted as-is] Megalaunch honesty — describable in present tense. Real sweeps here on 2026-08-26 and 2026-09-02. Open bugs `megalaunch-activates-picks-before-preflight` (at review) and `launch-activates-before-preflight` (in progress); no crashes in the last two weeks, the log's failures are DNS and Slack. Keep the positioning caveat.
- [SUPERSEDED 2026-09-03 — was "accepted as-is, nothing to do"] HN plan fit. Re-verified against the HN API and the disposition flipped: there *is* something to do. Never Show HN still holds, but "plain story submission" does not — every 30+ point result on this account names an opponent, and one URL scored 1 point descriptively and 32 adversarially four days apart. The plan's "titles are the experience, never the thesis" rule was corrected in `coga/contexts/marketing/plan` on the same date. Owned by `marketing/build-the-launch-plan`.

## Proposed phase-1 thresholds

Drafted 2026-09-03 for the owner to accept or adjust. The plan requires
thresholds noted *before* publishing so the phase-1 retro cannot be post-hoc
rationalization. Every number below is anchored to something this audit
actually measured, rather than picked for feeling ambitious.

**The anchors.** On HN, `top256` has three front-page hits at 87, 47 and 32
points, and its misses sit at 1 to 3 points — including the 2026-06-03 essay
at 1 point. There is almost no middle ground on that account, so a threshold
between the two clusters is meaningful. On Lobsters, the one prior submission
of a `deviantabstraction.com` essay scored 26 points with 19 comments.

| Signal | Proposed bar for post 1 | Why this number |
|---|---|---|
| HN | Front page, >= 30 points | Sits just under the weakest of three real hits (32) and far above every miss (1-3) |
| Lobsters | >= 15 points and >= 5 comments | Prior essay on the same domain took 26 / 19; more than half of that is a real result |
| Blog subscribers | +25 net in the two weeks after post 1 | Softest number here — there is no recorded baseline yet, so record it first and revise this |
| Community home | >= 15 joins in two weeks, and >= 3 people posting something that is not an introduction | Joins alone measure curiosity; the second half measures whether anyone stays |
| Vocabulary taking | >= 1 instance of someone the owner does not know using "you are the CPU" or "batch your judgment" unprompted | The plan's actual success metric — the idea circulating, not the artifact spreading |

**Explicitly not the bar:** installs, stars, and downloads. The plan says the
essay posts convert lightly by construction and that installs are the
long-arc goal, so treat all three as trailing proxies worth recording and not
worth scoring.

**Scoring rule.** Decide before publishing what a miss triggers, or the retro
will negotiate with itself. Suggested: HN missing the front page triggers the
plan's existing second-chance resubmission branch, which has precedent on
this account (the 2024-11 essay took on a resubmission four days after a
1-point first try). Missing the subscriber and community bars while hitting
the HN bar means the post worked and the funnel did not, which is a
landing-page problem for `marketing/readme-top`, not a thesis problem.

## Plan premise failure (owner, 2026-09-03)

The audit's job was to check phase-0 preconditions against reality. One of
them is false, and it is load-bearing.

**What the plan assumed.** `marketing/plan` builds post 1 around real,
quotable examples of the async/megalaunch practice, drawn from **non-Coga
repos first** — explicitly `multiply`, and by extension the other seven
Coga-run repos on this machine. The point of preferring non-Coga repos is to
avoid a post whose only evidence is the tool building itself.

**What is actually true.** Step 1 collected ten candidates and found the
strong ones live in `magicator`, `xpllm`, and `admin`. In step 2 the owner
ruled **all of them confidential**. The supply of non-Coga evidence is
therefore zero, not merely thin. The owner's conclusion: the only usable
evidence is **Coga building Coga**, and **there is no real plan yet**.

**Consequence.** Post 1 cannot be written as specified.
`marketing/post-async-megalaunch` is not startable, and the plan's fork-A
"settled" status now covers a structure whose evidence base does not exist.
This is not a drafting problem a writer can solve in the post; it is a
premise the plan has to be re-decided against.

**One reframe worth weighing before rewriting anything.** The plan treats
"Coga builds Coga" as the weak option, but that ranking may be backwards on
the axis that matters. A quote from a private repo is unverifiable: the
reader cannot check it, and an essay whose receipts cannot be inspected is
asking for trust. `FastJVM/coga` is public, so every claim made from its log
is reproducible by anyone who clones it — which is the same
"recompute it yourself" discipline `docs/velocity-report.md` already applies.
The confidentiality ruling may have removed the *weaker* evidence and left
the stronger. What it does cost is the answer to "does this work on anything
but itself", and that objection is real; the honest handling is one sentence
in the post acknowledging the other repos exist and are private, rather than
pretending the question was not asked.

**Open, and owned by the human.** Whether to re-decide the plan wholesale or
patch its evidence section; whether post 1 keeps its current structure with
Coga-on-Coga evidence; whether the essay series order changes. Nothing below
this line should be written until that is settled.
