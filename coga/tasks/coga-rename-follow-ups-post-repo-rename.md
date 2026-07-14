---
slug: coga-rename-follow-ups-post-repo-rename
title: Coga rename follow-ups (post repo-rename)
status: done
owner: zach
human: zach
agent: claude
assignee: claude
contexts: []
skills: []
workflow:
  name: code/with-self-review
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

Finish the Relay→Coga rename in code once the boss-owned ops land: the GitHub
repo rename `FastJVM/relay` → `FastJVM/coga` and the PyPI trusted-publisher
repoint. Flip the deliberately-preserved `FastJVM/relay` URLs to `FastJVM/coga`,
drop the stopgap README clone target, settle the migrate-tooling decisions the
rename PR left open, and publish `coga 0.2.0` via trusted publishing.

## Context

The rename PR (branch `rename/relay-to-coga`, commit `cc2f6843` + self-qa
`5893b1ad`) deliberately kept every `FastJVM/relay` URL working via GitHub's
redirect, because the actual repo rename and PyPI trusted-publisher update are
sequenced separately and owned by the boss (rename-PR decision C). This ticket
holds the code changes that become correct only *after* those ops land — they
were intentionally NOT made in the rename PR. See that PR's blackboard
"Follow-up — flip repo URLs" and "Structural decisions C/D".

<!-- coga:blackboard -->

## Production notes

The checklists below are the run's work plan — intentionally part of the
launch, not authoring scratch.

## 2026-07-03 implement run — everything already landed; blocked for closure

Went to implement and found every gated item was already delivered by other
merged work while this ticket sat. No code change remains, so no branch or
worktree was created (`## Dev` intentionally absent) and the
self-qa → pr → review steps have nothing to operate on. Evidence per item is
inline below; blocked for the owner to mark done (or redirect) rather than
bumping into a PR step with an empty diff.

Also verified while checking: the `relay-os/` tree that PR #455 accidentally(?)
committed is gone from current `main` (`git ls-tree HEAD` has no `relay-os/`),
and `coga-cli-cutover` is still `status: draft` — its fan-out step covers
in-flight sibling *branches*, not the Desktop repos, so it doesn't overlap the
tracking ticket created below.

## Pending items (gated on the repo rename)

**Prerequisites — boss-owned ops, gate everything below:**
- [x] Rename GitHub repo `FastJVM/relay` → `FastJVM/coga` — verified 2026-07-03: this checkout's `origin` is already `https://github.com/FastJVM/coga/`
- [x] Repoint the PyPI trusted publisher — verified indirectly 2026-07-03: release run `28296440460` (tag `v0.2.0`, 2026-06-27) published to PyPI via trusted publishing and succeeded, which is impossible with a stale repo field; `coga 0.2.0` is live on PyPI (uploaded 2026-06-27T17:26Z).

**Flip the preserved URLs `FastJVM/relay` → `FastJVM/coga`** — all landed in merged PR #455 (`bdc18b2a`, "Finish coga rename: sweep task-data fence + refs, flip repo URLs", 2026-06-26); `grep -r FastJVM/relay` over code/tests/docs is clean (only historical task notes + the intentional before/after row in `docs/migrating-to-coga.md` remain):
- [x] `docs/vision.md`
- [x] `README.md` — stopgap clone target also dropped: line is plain `git clone https://github.com/FastJVM/coga` (no explicit `coga` target)
- [x] `src/coga/commands/init.py`
- [x] `src/coga/commands/update.py` — `COGA_REPO_URL = "https://github.com/FastJVM/coga"`
- [x] `tests/test_init.py` — all fixtures now `FastJVM/coga`
- [x] `tests/test_skill_manager.py` — all fixtures now `FastJVM/coga`

**Host-repo migration (manual; no script):**
- [x] Keep `docs/migrating-to-coga.md` as the migration path — confirmed present and current: manual `git mv relay-os coga` (bare, per the boss's `8e7b3f76` reversal), `relay.toml`→`coga.toml`, `relay.local.toml`→`coga.local.toml`, `RELAY_REPO_URL`→`COGA_REPO_URL`, plus verification checklist and rollback notes.
- [x] Reconcile `update.py` `_LEGACY_COGA_GITIGNORE_ENTRIES` — verified consistent: entries are `skills/coga`, `contexts/coga/{architecture,principles,cli}` (post-rename spellings), matching the checklist's inner-namespace renames; nothing to change.
- [x] Single tracking ticket for the ~8–10 Desktop relay repos — created this run: **`migrate-desktop-relay-repos-to-coga-tracking`** (draft, workflow-less), with the per-repo migration steps from `docs/migrating-to-coga.md` and a placeholder repo checklist. The actual repo list must be filled in by the owner — the repos live on the boss's Desktop and aren't enumerable from this checkout (`~/Desktop` here is empty).

**Publish:**
- [x] Publish `coga 0.2.0` — done 2026-06-27: GitHub release `v0.2.0` triggered `.github/workflows/release.yml` (run `28296440460`, success); PyPI shows `coga 0.2.0` as latest (releases: 0.0.1, 0.2.0). `pyproject.toml` matches (`name = "coga"`, `version = "0.2.0"`).
- [x] Switch the README install to PyPI — done in merged PR #466 (`ee2b61f6`, "README: PyPI install + upgrade guidance"): step-1 block now leads with `pip install coga` / `pipx install coga`, upgrade note present, clone+editable demoted to the source-checkout/dev path. Done as `coga` directly, not by reviving closed PR #453 — as planned.

## Post-merge cutover → tracked separately

The *immediate* post-merge cutover (reinstall `relay`→`coga` everywhere, verify no
`relay-os/` resurrects, fan out to the sibling branches) moved to its own launchable
ticket: **`coga-cli-cutover`** (workflow `coga/cutover`, 3 steps). Launch it right
after PR #454 merges. This ticket holds only the *repo-rename-gated* follow-ups above.
Note 2026-07-03: `coga-cli-cutover` is still `draft` even though the rename merged
and v0.2.0 shipped — worth a look at whether it's now moot too or should be launched.

---

## Blockers

- [x] [2026-07-03 12:03] [agent:claude] id=20260703T120332 Nothing left to implement: every checklist item already landed while this ticket sat — URL flips + README clone target via merged PR #455 (bdc18b2a), PyPI trusted publisher repointed + coga 0.2.0 published 2026-06-27 (release run 28296440460), README PyPI install via PR #466 (ee2b61f6); update.py legacy gitignore entries verified consistent. I created the last open item as ticket migrate-desktop-relay-repos-to-coga-tracking (needs your Desktop repo list filled in). No diff exists for self-qa/pr steps, so: please mark this ticket done (and fill the repo list / decide whether draft coga-cli-cutover is also moot), or tell me if any part should still produce a PR.
  resolved: [2026-07-03 16:13] [human:nicktoper] Confirmed: everything already landed (PR #455 URL flips, coga 0.2.0 on PyPI 2026-06-27, README PyPI install PR #466). No diff to produce. Marking done; Desktop repo list tracked in migrate-desktop-relay-repos-to-coga-tracking.

## Usage

{"agent":"claude","cache_creation_input_tokens":174479,"cache_read_input_tokens":2541076,"cli":"claude","input_tokens":16193,"model":"claude-fable-5","output_tokens":46969,"provider":"anthropic","schema":1,"session_id":"7d387b29-8109-42c5-bd6b-75113361457e","slug":"coga-rename-follow-ups-post-repo-rename","step":"implement","title":"Coga rename follow-ups (post repo-rename)","ts":"2026-07-03T19:03:36.082505Z","usage_status":"ok"}
