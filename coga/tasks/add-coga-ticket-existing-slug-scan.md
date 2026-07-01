---
slug: add-coga-ticket-existing-slug-scan
title: add-coga-ticket-existing-slug-scan
status: in_progress
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
secrets: null
script: null
step: 4 (review)
---

## Description

`coga ticket <slug>` on an existing ticket should greet the human as an
**edit**, but it greets as a **create** whenever the ticket's
`## Description`/`## Context` body is empty — which is the exact state of
drafts made in a batch with `coga create` and then opened for authoring.
The `bootstrap/ticket` skill decides create-vs-edit from body-emptiness,
even though `coga ticket` itself already resolved create-vs-edit
definitively before launch. Drive the opening greeting off the CLI's actual
resolve-vs-create outcome instead of body content, so a pre-existing (even
empty) draft is recognized as an edit. Also fix the related nested-ticket
case: a nested existing ticket addressed by its bare leaf fails to resolve
and silently spawns a duplicate top-level draft. Keep both fixes scoped to
the `coga ticket` path for the least possible blast radius — do not change
the shared `resolve_task` semantics that `coga launch` and `coga status`
also depend on.

## Context

- **Where the decision actually lives:** `src/coga/commands/ticket.py` →
  `_resolve_or_create_target()`. `resolve_task()` succeeding = edit (returns
  the existing ticket); `TaskNotFoundError` = `create_draft()` = new. The
  outcome is known here but is never passed into the launched authoring
  session (`spawn_agent_session(..., kickoff="Begin")`).
- **The buggy heuristic:** the `bootstrap/ticket` skill, "Step 1 — Identify
  the launch shape", classifies new-vs-existing from "empty
  `## Description`/`## Context` body means new, a filled body means existing."
  That misfires for `coga create`d empty drafts.
  **Pinned mechanism (least blast radius):** the CLI already computes the
  answer in `_resolve_or_create_target` — thread that create-vs-edit boolean
  down to `_run_authoring_session` and vary the `kickoff` token (currently the
  hardcoded `"Begin"` at ticket.py:184) so the skill greets off the token
  rather than body content. This only adds information flow on the
  `coga ticket` path; no shared function changes.
- **Why "skill scans all slugs" is not enough on its own:** by the time the
  skill runs, the ticket file always exists on disk in *both* cases — a new
  one was just written by `create_draft` moments earlier — so a filesystem
  scan cannot distinguish "just created" from "pre-existing". The reliable
  signal is the CLI's resolve-vs-create branch, not a scan.
- **"Existing but empty" edit path:** when an existing draft has an empty
  body there is nothing to preserve, so it should still fill from scratch —
  it must just greet as an edit, not announce "has been created".
- **Nested/subdirectory case:** `resolve_task()` in `src/coga/tasks.py`
  (~line 259) matches a nested task only by full path (`<dir>/<slug>`) —
  "a nested task's bare leaf does not resolve." So `coga ticket <bare-leaf>`
  for a nested ticket falls through to `create_draft` and creates a duplicate
  top-level draft.
  **Pinned mechanism (least blast radius):** do not touch `resolve_task`.
  Instead, in `_resolve_or_create_target`, when `resolve_task` raises the
  `No task matches` form (the `Ambiguous task ref` form still bails as today),
  fall back to a bare-leaf scan of `list_tasks` (`t.slug == target`). Exactly
  one leaf match → treat it as an existing edit (resolve to that ref). More
  than one → bail as ambiguous, listing the full `<dir>/<slug>` paths so the
  user re-runs with the qualified slug. Zero → genuinely new, `create_draft`
  as today. This leaves `resolve_task`'s global semantics — and every other
  caller (`coga launch`, status) — untouched.
- **Keep both skill copies in sync** (per CLAUDE.md): live
  `coga/bootstrap/skills/bootstrap/ticket/SKILL.md` and packaged
  `src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md`.
  Note: the two copies have already diverged in wording (the packaged copy
  uses `<package-bootstrap>` path forms), so apply the same *logical* edit to
  each by hand — a byte-for-byte copy would clobber the package-path wording.
- **Also check the no-target greeting:** the empty-interview path
  (`target is None`, no create-vs-edit signal exists) must keep working when
  the greeting stops keying off body-emptiness — confirm, don't rediscover.
- **Tests / verification:** `tests/test_ticket.py` covers the command;
  `tests/test_bootstrap_ticket_skill_template.py` covers the shipped skill
  template. Run `python -m pytest` and `coga validate` after changes.
- **Out of scope:** redesigning the bootstrap interview itself, and changing
  `coga create` batch behavior.

<!-- coga:blackboard -->
## Dev

branch: ticket-existing-slug-greeting
worktree: /Users/zach2179/dev/coga-ticket-greeting
commit: 83a8be41
pr: https://github.com/FastJVM/coga/pull/486
ci: no checks configured on the repo (`gh pr checks` reports none) — nothing to be red against.

## Implement — done

Landed exactly the pinned mechanism (kickoff token, no `resolve_task` change):

1. `src/coga/commands/ticket.py` — added kickoff constants
   (`AUTHORING_KICKOFF` = `"Begin"`, `..._NEW` = `"Begin (new ticket)"`,
   `..._EDIT` = `"Begin (editing existing ticket)"`).
   `_resolve_or_create_target` now returns `(ref, ticket, created)`; `ticket()`
   maps `created` → the token and threads it into `_run_authoring_session`
   (replaced the hardcoded `"Begin"`). Nested-leaf fix: on the non-ambiguous
   `TaskNotFoundError`, scan `list_tasks` for `t.slug == target` — 1 → edit
   (via new `_resolve_existing` helper), >1 → ambiguous bail listing full
   `<dir>/<slug>`, 0 → `create_draft` as before. `resolve_task` untouched, so
   `coga launch` / `coga status` are unaffected.
2. Both `bootstrap/ticket` SKILL.md copies (live + packaged) — Step 1 rewritten
   to greet off the kickoff token, header/body only as fallback; existing-but-
   empty greets as an edit and fills from scratch. Step 1 region is byte-
   identical across the two copies; the pre-existing `<package-bootstrap>`
   divergences (Step 2/4/7) were left intact.
3. Tests: updated the two create-path `"Begin"` assertions in
   `tests/test_ticket.py`; added existing-empty-draft-edits-as-edit,
   nested-bare-leaf-edits-not-duplicate, and ambiguous-bare-leaf-bails cases;
   added a kickoff-token regression to `test_bootstrap_ticket_skill_template.py`.

Verification: `python -m pytest` → 940 passed. `coga validate --json` on
`example/coga` → ok_count 1, no issues.

## Peer review — done

Ran `codex review --base main` from `/Users/zach2179/dev/coga-ticket-greeting`
after rerunning unsandboxed for the known app-server permission failure. Review
returned no must-fix findings: "The changes correctly propagate an explicit
authoring kickoff token and handle bare-leaf nested ticket resolution without
introducing clear regressions."

No code changes were needed in peer review, so no peer-review commit was
created. Verification run:

- `python -m pytest` from feature worktree → 940 passed, 1 `.pytest_cache`
  write warning.
- `coga validate` from feature worktree → failed on pre-existing unrelated
  dogfood task drift (`install/*` malformed tickets, missing-step tickets,
  unknown-assignee/stuck warnings).
- `coga validate --task add-coga-ticket-existing-slug-scan` from feature
  worktree and primary checkout → all good (1 task checked).
- `coga validate --json` from `example/coga` in feature worktree → ok_count 1,
  no issues.

## Production notes

This blackboard is for active-work handoff notes. Authoring scratch was cleared at activation; durable requirements belong in the ticket body.

## Usage

{"agent":"claude","cache_creation_input_tokens":526610,"cache_read_input_tokens":15310002,"cli":"claude","input_tokens":47271,"model":"claude-opus-4-8","output_tokens":208577,"provider":"anthropic","schema":1,"session_id":"526302eb-aac9-4855-bd98-3ee666e70c4b","slug":"add-coga-ticket-existing-slug-scan","step":"implement","title":"add-coga-ticket-existing-slug-scan","ts":"2026-07-01T00:32:06.993135Z","usage_status":"ok"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":null,"cli":"codex","input_tokens":null,"model":null,"output_tokens":null,"provider":"openai","schema":1,"session_id":"019f1b75-d534-76d1-b13a-4774a74bc13b","slug":"add-coga-ticket-existing-slug-scan","step":"peer-review","title":"add-coga-ticket-existing-slug-scan","ts":"2026-07-01T02:16:59.510637Z","usage_status":"unknown"}

{"agent":"codex","cache_creation_input_tokens":null,"cache_read_input_tokens":3193728,"cli":"codex","input_tokens":194944,"model":"gpt-5.5","output_tokens":7527,"provider":"openai","schema":1,"session_id":"019f1b93-6290-7e72-a707-5281302d256f","slug":"add-coga-ticket-existing-slug-scan","step":"peer-review","title":"add-coga-ticket-existing-slug-scan","ts":"2026-07-01T03:22:11.638171Z","usage_status":"ok"}

{"agent":"claude","cache_creation_input_tokens":123101,"cache_read_input_tokens":918189,"cli":"claude","input_tokens":35474,"model":"claude-opus-4-8","output_tokens":15630,"provider":"anthropic","schema":1,"session_id":"8c927c6c-bccd-45fe-9895-7b58f49a7613","slug":"add-coga-ticket-existing-slug-scan","step":"open-pr","title":"add-coga-ticket-existing-slug-scan","ts":"2026-07-01T03:34:50.066494Z","usage_status":"ok"}
