---
title: Fix coga git sync failures that leave main diverged from origin
status: draft
owner: nicktoper
contexts:
  - coga/sync
  - coga/internals/state-publication
  - coga/internals/git-refresh
workflow: code/design-then-implement
---

## Description

Coga's automatic git sync keeps failing, and when it does it leaves local main with commits that diverge from origin/main. On 2026-09-29 this forced a manual reset. Find the root cause of each failure class and fix it so that sync either succeeds or fails loudly without leaving main diverged. Do not assume the sandbox makes `.git` read-only: on the owner's machine `.git` is read-write, so a "Read-only file system" error comes from whatever sandbox the failing process ran in, and that has to be identified.

Done when:

- The root cause of each failure class in the table under Context is either
  fixed or explicitly accepted, and the reason is written down. If a fix is an
  owner-side `coga.toml` / `coga.local.toml` or CLI-settings change, the
  design names it as an open question for the review-design gate; the owner
  applying it counts as fixed.
- A launched Codex session and a launched Claude session can each finish a
  step in `~/Code/multiply`, with normal network access, without adding a
  `[git] sync failed` line. The PR attaches the relevant `coga/log.md` excerpt.
- A failed sync never leaves `main` diverged when origin already has the same
  content. A regression test in `tests/` simulates a failed publish followed by
  a later sync and asserts that `main` ends up matching origin. Any failure it
  does produce is loud and says what to run.

## Context

### Incident (2026-09-29)

The incident and all log evidence below come from the Multiply checkout
(`~/Code/multiply`, its `coga/log.md`), a consumer repo of this package; the
fix lands here in Coga.

Local `main` was 1 commit ahead of `origin/main` and 5 behind, and it also had
uncommitted edits to `coga/log.md` and the `decide-the-six-title-only-tickets-flagged-by-valid`
ticket. The local commit `94da4bda` and the uncommitted edits had already
reached origin through separate sync commits (`f1f696a8` "Sync coga state",
`6ab1e663`, `f500316f`, `b8953733`, `b37922f7`). The working tree was
byte-identical to `origin/main`. It was fixed by hand with
`git branch backup/main-94da4bda HEAD && git reset origin/main`. Nobody should
have to do that. The `backup/main-94da4bda` branch still exists in
`~/Code/multiply` and can serve as a repro artifact.

### Sync failures recorded in `coga/log.md` (`[git] sync failed`)

| Count | Error | Dates | Status |
| --- | --- | --- | --- |
| 151 | `git fetch` → `Could not resolve host: github.com` | 2026-08-14 → 2026-09-21 21:14 | Session without network access |
| 41 | `git hash-object` → `unable to create temporary file: Read-only file system` / `fatal: Unable to add (null) to database` | 2026-09-22 10:32 → 2026-09-29 | Live; process ran where `.git` was not writable |
| 4 | `git add` → `Unable to create '/home/n/Code/codex/multiply/.git/index.lock': Read-only file system` | 2026-08-26 | Same shape, in the `~/Code/codex/multiply` checkout (still exists) |
| 16 | `could not rebase 'main' onto origin/main: could not apply 1678fe5... Contexts: pivo…` | 2026-08-19 only | Probably obsolete (see below) |
| 2 | Rebase blocked by untracked working-tree files | 2026-09-13 only | Probably obsolete |
| 4 | `could not reapply local changes after rebasing`; pre-sync state restored | 2026-09-17 only | Probably obsolete |

`[coga]` is the slug on 90 of the 218 failures, which makes them repo-wide
state syncs. Every other failure belongs to a ticket-scoped sync.

Findings from the ticket's cold review, to verify rather than trust:

- **The switch from `fetch` to `hash-object` failures tracks a code change.**
  Coga #848 "Simplify git sync" landed 2026-09-21 20:31, between the last
  `Could not resolve host` and the first `hash-object` failure. Once publish
  writes objects before fetching, a restricted session trips on `hash-object`
  first. This may be one cause (a restricted session running sync) seen
  through two code paths.
- **It is not clearly Codex-specific.** Failing entries include bumps logged
  as `[agent:claude] advanced … → codex` (09-22 10:32) and
  `[human:nicktoper] advanced … → codex` (09-29 08:59). Neither repo's
  `[agents.claude]` or `[agents.codex]` sets a sandbox flag, so any
  restriction comes from each CLI's defaults or user-level settings. Check
  both CLIs, and the operator/agent fields around each failure.
- **The rebase/autostash rows predate #848.** Current `git.py` has no rebase
  or autostash sync path. It only prints a `git pull --rebase` hint. Confirm
  and record that as the resolution.
- **The divergence mechanism is likely in `git-refresh`.**
  `fast_forward_control` leaves an ahead-or-diverged `main` alone and prints
  `git pull --rebase`. That is the natural place for "local content already
  matches origin → fast-forward".
- Relevant code: `git.sync_task_state`, `git.publish` and its `hash-object`
  call, and the `[git] sync failed` sites in `git.py`, `mark.py`,
  `recurring_runner.py`, `authoring.py`. `coga/internals/git-regressions` and
  `coga/internals/spool-merge` (under `docs/contexts/`) are cited, not
  attached. Read them only if the fix touches the provenance check or the
  union merge of `log.md`.

### What to find out

1. Which process and environment ran each `hash-object` / `index.lock` /
   `fetch` failure, and why `.git` was unwritable or the network unreachable
   there (`.git` itself is read-write on the owner's machine). Check both the
   Codex and Claude Code CLIs' sandbox defaults, and `[agents.*]` in
   `coga.toml` / `coga.local.toml`. Agents may not edit those files, so
   propose any change to the owner.
2. Why a failed in-session sync ends up as a later local commit that
   duplicates what reached origin another way, rather than being retried
   cleanly.
3. Whether the divergence could be avoided: for example, sync from the
   supervisor (outside any sandbox) after the session exits, or have a
   post-failure sync notice that local content already matches origin and
   fast-forward.
4. Confirm the rebase conflict (`1678fe5`), untracked-file, and autostash
   failures are resolved by #848.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Evaluator review

- **Clarity:** An agent with no prior context can start. The incident, the evidence source (Multiply's `coga/log.md`) and the four questions are concrete. One sentence in the description is biased, though: "mainly a read-only .git inside agent sandboxes" assumes the answer before the investigation.
- **Done criteria:** Mostly checkable. Two gaps:
  - "A launched Codex session and a launched Claude session can each finish a step" doesn't say where or how to prove it. It should name a repo, network conditions and the evidence to attach, such as a log excerpt.
  - "Never leaves main diverged when origin already has the same content" needs a test: a regression test in `tests/` that simulates a failed publish followed by a later sync.
- **Workflow:** `code/design-then-implement` fits. Investigation happens in design, cold review follows, then implementation on a branch. One mismatch: question 1 may end in a `coga.toml [agents.*]` change the agent can't make. The design step should put that proposal under Open Questions for review-design, and the done criteria should say whether an owner config change counts as "fixed."
- **Contexts:**
  - Keep `coga/internals/state-publication` attached. `publish` / `hash-object` (`src/coga/git.py:239`, `:1598`) is exactly where the current failures occur.
  - Add `coga/internals/git-refresh`. `fast_forward_control` is the code path for question 3 ("notice local matches origin and fast-forward"). Its "ahead or diverged → left alone, prints `git pull --rebase`" behaviour is likely the divergence mechanism itself.
  - `git-regressions` and `spool-merge`: cite by path rather than attach. They are relevant only if the fix touches the provenance check or union merge of `log.md`.
  - `coga/sync` is fine to keep.
  - Size: state-publication is ~36% of the prompt, under the 40% threshold. No layer needs trimming, though adding git-refresh (~820 words) will push the total up.
- **Scope:** It bundles three separate problems: (a) sandbox or network environment; (b) divergence after a failed publish; (c) historical rebase conflicts. Recommendation: keep (b) as this ticket, since it is the real product bug. Make (a) a sibling that is mostly an owner decision on config or docs. Drop (c).
- **Assumptions to question before launch:**
  - **The failure classes line up with a code change, not an environment change.** Coga #848 "Simplify git sync" landed 2026-09-21 20:31. The last `Could not resolve host` failure is 09-21 21:14 and the first `hash-object` failure is 09-22 10:32. Once `publish` writes objects before fetching, the sandbox trips on `hash-object` first. This may be one cause (a sandboxed session) seen through two code paths.
  - **Read-only `.git` isn't clearly Codex-specific.** Failing entries are bumps logged as `[agent:claude] advanced … → codex` (09-22 10:32) and `[human:nicktoper] advanced … → codex` (09-29 08:59) — possibly Claude Code's own sandbox, not a Codex session. Neither repo's `[agents.claude]` or `[agents.codex]` sets any sandbox flag, so the constraint comes from each CLI's defaults or user-level settings. Check both CLIs' sandbox defaults and the operator/agent fields around each failure.
  - **Counts:** the `hash-object` row has 41 entries, not 40. `[coga]` appears on 90 failures, not 89. The total of 218 matches.
  - **The rebase and autostash rows are probably obsolete.** `1678fe5` failed only on 2026-08-19, the untracked-file blocks only on 09-13, and "reapply" only on 09-17, all before #848. Current `git.py` has no rebase or autostash sync path; it only prints a `git pull --rebase` hint. Question 4 can likely be answered as "resolved by #848".
  - **Paths and names still exist:** `sync_task_state`, the `[git] sync failed` sites (`git.py`, `mark.py`, `recurring_runner.py`, `authoring.py`), and docs `coga/sync` and `coga/internals/state-publication`. `~/Code/codex/multiply` shows up only in the 08-26 `index.lock` entries; not checked whether it still exists.
  - **The incident is described as fixed by hand.** The ticket should say whether `backup/main-94da4bda` is still around as a repro artifact.
