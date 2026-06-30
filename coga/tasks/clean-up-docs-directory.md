---
slug: clean-up-docs-directory
title: clean up docs directory
status: done
autonomy: interactive
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow:
  name: dev/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
---

## Description

Prune the `docs/` directory. As the repo has grown, several docs have become
redundant with the `coga/contexts/` blocks (which are the agent-loaded source
of truth) or have gone stale/orphaned. Delete the redundant files outright
(git history preserves them), and where a deleted doc held a useful framing
that isn't captured elsewhere, add a one-line "see also" cross-reference into
the canonical context so nothing of substance is silently lost.

Done looks like: a `docs/` tree that contains only load-bearing, non-duplicative
docs; no dangling references to deleted files anywhere in the repo; and any
preserved framing pointed to from its canonical context.

## Context

Survey already done — this is the disposition, not a re-investigation. The
repo uses a deliberate pattern: a narrative/evidence doc paired with a
distilled, agent-loaded context (e.g. `vision.md`↔`coga/principles`). Those
pairs are NOT redundant — keep both.

**Keep (load-bearing — do NOT delete):**
- `docs/vision.md` — cited by CLAUDE.md, AGENTS.md, README, and `src/coga/__init__.py`; pairs with `coga/principles`.
- `docs/market-thesis.md` — cited by README; source for `marketing/positioning`.
- `docs/cli-extension-audit.md` and `docs/cli-extension-external-surface.md` — evidence/design paired with `coga/extension-model`.
- `docs/migrating-to-coga.md`, `docs/releasing.md` — unique operational docs, no context equivalent.

**Delete (content is redundant with a context or otherwise superseded — the
test is content-uniqueness, not reference count):**
- `docs/design.md` — orphaned M1 design notes; stale CLI syntax, points to a spec file that no longer exists.
- `docs/coga-unique.md` — covered by `coga/principles` + `coga/architecture` + `marketing/positioning`.
- `docs/coga-vs-paperclip.md` — dated 2026-06-06; overlaps `marketing/positioning`.
- `docs/agent-tool-buckets.md` — eval research; the "no black box" point lives in `marketing/positioning`.
- `docs/coga-additions.md` — pre-prioritization wishlist; superseded by `coga/roadmap` + `coga/current-direction`.
- `docs/competition/*.md` (8 reports) — research snapshots exported from Google Docs; themes distilled into `marketing/positioning`.

**Cross-refs:** the human chose "add cross-refs." Where a deleted file held a
distinct framing not already present in the surviving context, add a single
"see also"/pointer line to the canonical context (most likely
`coga/contexts/marketing/positioning/SKILL.md`). Don't bulk-paste content;
one pointer line max per item, and only when the framing is genuinely unique.

**Gotchas / dangling-reference rules:**
- After deleting, grep the whole repo for each removed filename and fix
  dangling links **only in live docs** — README, CLAUDE.md, AGENTS.md,
  surviving `docs/`, and `coga/contexts/`. **Do NOT scrub filenames out of
  historical/completed task notes** under `coga/tasks/` — those are immutable
  records of past work; leave them as-is.
- `docs/design.md` is the one delete-file with real inbound references, and
  they are all in historical task notes (e.g. `rename-relay-to-coga.md`,
  `make-recurring-all-a-real-full-run-drop-the-debug.md`,
  `marketing/readme-and-docs.md`). Per the rule above, leave those untouched.
  Verify `design.md` is not linked from any *live* doc before deleting (it
  isn't, as of authoring).
- Beware grep false positives on the competition reports: a search for e.g.
  `conductor-report` hits `coga/contexts/docs/gdrive-mcp/SKILL.md` and
  `coga/workflows/docs/create-google-doc.md`, but those refer to a *Google
  Doc* of that name, not `docs/competition/conductor-report.md`. Do NOT
  "fix" those — they aren't dangling links to the deleted files.
- No packaged-copy concern: `docs/` is NOT duplicated under
  `src/coga/resources/`, so there is no live↔packaged sync to do here.
- This is docs-only; no code or tests change, but still run `python -m pytest`
  as a smoke check per the workflow before opening the PR.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

- branch: `docs-cleanup`
- worktree: `/home/n/Code/claude/coga-docs-cleanup`
- pr: https://github.com/FastJVM/coga/pull/470

### pr step — done

Pushed `docs-cleanup` to origin and opened PR #470 (base `main`). Auth probed
clean (`gh auth status` → nicktoper, `repo` scope). No CI checks are configured
on this repo (`gh pr checks` → "no checks reported"), so there's no green/red to
report — the PR is open and awaiting human review.

### implement step — done

**Deleted (13 files):** `docs/design.md`, `coga-unique.md`, `coga-vs-paperclip.md`,
`agent-tool-buckets.md`, `coga-additions.md`, and all 8 `docs/competition/*.md`
reports (the now-empty `competition/` dir went with them). Remaining `docs/` =
the keep list exactly: `cli-extension-audit`, `cli-extension-external-surface`,
`market-thesis`, `migrating-to-coga`, `releasing`, `vision`.

**Dangling refs:** none in live docs. Repo-wide grep hit only (a) historical
task notes under `coga/tasks/` (left untouched per the immutability rule) and
(b) the two `conductor-report` mentions in `coga/contexts/docs/gdrive-mcp/SKILL.md`
and `coga/workflows/docs/create-google-doc.md` — the documented false positives
(a Google Doc, not `docs/competition/`). Left untouched.

**Cross-ref:** investigated each deleted framing; almost all already captured
(no-black-box, repo-as-record, wishlist→roadmap) and the Paperclip contrast is
absent from positioning's source-of-truth docs (market-thesis/vision). Surfaced
to human → chose "add Paperclip line." Added one bullet to the competitive-framing
section of `coga/contexts/marketing/positioning/SKILL.md`. No packaged copy of
that context exists under `src/coga/resources/` → no sync needed.

**Tests:** `python3.12 -m pytest` → 906 passed, 1 skipped. (Default `python` is
3.9 here and trips Coga's version guard at collection — env-only, unrelated to
this change.)

## Self-QA

**`/code-review` — no findings.** Diff is docs-only (13 markdown deletions + a
3-line cross-ref bullet), so the only real defect class is dangling references
to deleted files. Independently re-grepped the repo for every deleted basename
as both `docs/<name>.md` and relative `](…name.md)` links, plus any mention of
the now-removed `competition/` dir. All `.md` path references are confined to
immutable `coga/tasks/` notes (left untouched per rule); **zero** hits in
README, CLAUDE.md, AGENTS.md, surviving `docs/`, `coga/contexts/`, or `src/`.
The added Paperclip bullet is well-formed and consistent with its list.

**`/simplify` — no findings.** No code changed; the only non-deleted content is
3 lines of markdown prose. Reuse / simplification / efficiency / altitude don't
apply to a documentation bullet — nothing to apply.

**Tests:** `python3.12 -m pytest` → 906 passed, 1 skipped. Clean working tree;
both passes came back clean, so no QA-fix commit was needed.

## Evaluator review

**Clarity — strong.** A cold agent can start immediately. The ticket gives an explicit keep/delete list with per-file rationale, a concrete "done looks like," cross-ref guidance, and a gotchas block. The disposition framing ("survey already done — this is the disposition, not a re-investigation") correctly stops the agent from re-litigating what to cut.

**Workflow fit — appropriate.** `dev/with-self-review` is a reasonable choice: the work is mostly deletion plus a few cross-ref edits, benefits from a self-review pass over the dangling-link cleanup, runs `pytest` as a smoke check, and ends at a human PR gate — which matches the human's `autonomy: interactive`. It's marginally heavy for "delete some markdown," but the grep-and-fix cleanup plus judgment calls on cross-refs justify it. No real mismatch.

**Contexts — inlining is the right call.** `contexts: []` is correct here. The keep/delete disposition is task-specific data, not reusable behavioral contract, so it belongs in `## Context`, not in an attached SKILL. Nothing important is missing. (Optionally `marketing/positioning` could be attached since that's where cross-refs land, but inlining the pointer to it is sufficient.)

**Scope — reasonable, single coherent unit.** ~5 top-level deletes + 8 competition reports + a few cross-ref lines + repo-wide dangling-link cleanup. This is one ticket's worth of work, not several.

**Assumptions to question before launch — a few real ones:**

1. **"Delete … nothing references them" is false for `design.md`.** It is referenced in roughly six task files. The agent needs a decision up front: leave historical task notes untouched (treat them as immutable records) vs. edit them. `design.md` is the one delete-file with meaningful inbound references, so the blanket claim should not be trusted for it. [Resolved in ticket: leave historical task notes untouched; fix only live docs.]

2. **Competition reports — watch for false positives.** Grepping `conductor-report` will hit `coga/contexts/docs/gdrive-mcp/SKILL.md` and `coga/workflows/docs/create-google-doc.md` — those refer to a *Google Doc* named conductor-report, not `docs/competition/conductor-report.md`. The agent must not "fix" these. [Resolved in ticket gotchas.]

3. **The "cross-link each other" gotcha is inaccurate (but harmless).** `docs/coga-vs-paperclip.md` does not link the two cli-extension docs. The disposition is still correct; just don't go hunting for a cross-link that isn't there. [Resolved: gotcha reworded.]

4. **Minor rationale inconsistency.** `migrating-to-coga.md` is KEEP yet has zero inbound references, while `coga-additions.md` is DELETE also with zero references. The real criterion is content uniqueness, not reference count. [Resolved: delete-header reworded to say the test is content-uniqueness.]

**Verified as correct:** All KEEP claims hold — `vision.md` (CLAUDE.md, AGENTS.md, README, `src/coga/__init__.py`), `market-thesis.md` (README + `marketing/positioning` + `principles`), both cli-extension docs (`coga/extension-model`), `releasing.md` (`.github/workflows/release.yml`). `marketing/positioning/SKILL.md` exists as the cross-ref target. The four delete files `coga-unique`, `coga-vs-paperclip`, `agent-tool-buckets`, `coga-additions` have genuinely zero inbound references. The "no packaged-copy sync" note is correct.

Bottom line: ready to launch once the `design.md`-in-task-notes question (flag #1) is answered — now resolved in the ticket's gotchas.

## Usage

{"agent":"claude","cache_creation_input_tokens":142351,"cache_read_input_tokens":2198850,"cli":"claude","input_tokens":16326,"model":"claude-opus-4-8","output_tokens":35249,"provider":"anthropic","schema":1,"session_id":"e28f3c74-41ae-49a8-99f9-c9d67f5c40dc","slug":"clean-up-docs-directory","step":"implement","title":"clean up docs directory","ts":"2026-06-29T19:50:31.457293Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":120476,"cache_read_input_tokens":1290365,"cli":"claude","input_tokens":14265,"model":"claude-opus-4-8","output_tokens":19810,"provider":"anthropic","schema":1,"session_id":"b02fa137-4a39-401a-accd-a46fc8fbec4a","slug":"clean-up-docs-directory","step":"self-qa","title":"clean up docs directory","ts":"2026-06-29T19:53:02.755521Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":85694,"cache_read_input_tokens":852493,"cli":"claude","input_tokens":13995,"model":"claude-opus-4-8","output_tokens":9320,"provider":"anthropic","schema":1,"session_id":"f317a726-adfd-4015-9357-146c6b7aab61","slug":"clean-up-docs-directory","step":"pr","title":"clean up docs directory","ts":"2026-06-29T19:54:36.639796Z","usage_status":"ok"}
