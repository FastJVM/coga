---
title: automerge ticket
status: active
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
- dev/code
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
step: 1 (implement)
---

## Description

Add a new workflow `code/optimistic-merge` that mirrors `code/with-review`
(implement → peer-review by the *other* agent → open-pr) but replaces the
final human `review` step with an **agent** step that merges the PR
optimistically. The premise is speed: most reviewed-and-peer-checked
changes are fine, so an agent merges them without waiting on the human,
and the human stays a post-hoc safety net to catch and revert the rare
mess-up. This is the inverse of the existing `relay automerge` (which only
auto-*bumps a ticket to done* after a human merges); here an agent does the
merging.

## Context

**Mirror, don't reinvent.** Copy the shape of
`relay-os/workflows/code/with-review.md`. Keep steps 1–3 identical:
`implement` (`code/implement`), `peer-review` (`assignee: other-agent`,
flips to the non-coder agent — two agent types `claude`/`codex` are
configured so `other-agent` resolves cleanly), `open-pr` (`code/open-pr`,
which already ensures the PR is mergeable vs `main`). Only the final step
changes.

**New final step = agent merge.** Replace the `review` step
(`assignee: owner`) with an agent step `assignee: agent` (the coder — by
this point `open-pr` has flipped the assignee back to the coder, so the
merging agent is the original author; that's fine). This needs a **new
skill** — create `relay-os/skills/code/merge-pr/SKILL.md` (process
knowledge for the merge), because `code/open-pr` explicitly states deciding
whether to merge is the human's job, so it cannot be reused for this. The
merge skill should: read `pr:` from the blackboard `## Dev` section (the
`dev/code` convention — attached as a context; see also `code/open-pr`),
**require CI to be green before merging** (`gh pr checks` / `gh pr view
--json statusCheckRollup`) and `relay panic` if CI is red or not yet
passing, run `gh pr merge`, then run `relay mark done <slug>` itself.

  Note this step **deliberately overrides** `code/open-pr`'s policy of
  "blackboard the CI failure and bump anyway" — here a red/incomplete CI is
  a hard stop (`panic`), not a note. Don't lean on the existing `relay
  automerge` auto-bump as a backstop: it only fires for a ticket already on
  its *final* step, which the merge step is, so it's redundant here — the
  skill must close the ticket with `relay mark done` directly.

**Human safety net = loud post (+ optional watcher).** The owner is *already*
named and cc'd on every broadcast by virtue of being `owner:`, so the
load-bearing safety mechanism is a **live, urgent** Slack post on merge:
`relay slack --task <slug> --message "merged <pr-url> — revert if wrong"` (the
live path, not a batched digest line) so the owner can review post-hoc and
revert fast. The merge is optimistic; safety is fast visibility, not a
blocking gate. Adding the owner to a `watchers:` list is redundant with the
owner cc and needs no special machinery — if a *second* human should also be
pinged, that's what `watchers:` is for; otherwise skip it. (`watchers` is a
plural list field; `relay slack`/`post` cc only watchers that are mapped in
`[slack.users]`.)

**Decisions already made (don't re-litigate):** name = `code/optimistic-merge`;
CI gate = required (hard stop); safety net = loud live post on merge. Naming
chosen to avoid visual collision with the `relay automerge` command.

**Scope / out of scope.** This is a relay-os markdown change (one workflow
file + one new skill file), plus a short prose section in the workflow body
documenting the optimistic-merge behavior (mirror how `with-review.md`
documents its steps). The `code/` workflow namespace is **not** shipped in
the packaged template (`src/relay/resources/templates/relay-os/`), so no
dual-copy sync is required — but confirm before assuming. No Python/CLI
changes are expected; if the merge step turns out to need new CLI support,
that is a separate ticket — `relay panic` and surface it rather than
expanding scope here. Because the change is markdown-only there are no unit
tests to add — validate with `relay validate --json` and a read-through
rather than expecting `pytest` coverage; the workflow's QA/peer-review steps
will be a light pass.

**Pointers.** `other-agent` resolution and per-step `assignee:` role
rewriting live in `src/relay/bump.py`; the `architecture` context documents
prompt composition, `assignee` role tokens, and the agent-rotation model if
the implementer needs deeper grounding (read it, don't attach it).
