The blackboard is a notepad to be written to often as the human and agent works through a task.

## Plan

Local `post-merge` git hook + `relay status` opportunistic fallback. No
GitHub Action in v1 — the local-first posture covers ~all merges in a
small team.

### Code shape

1. Extract `commands/bump.py`'s core into `src/relay/bump.py` as
   `bump_task(cfg, ref, *, message=None, suffix=None, actor=None)`.
   Returns the new state for the caller's stdout. `commands/bump.py`
   becomes a thin Typer wrapper.
2. New `src/relay/automerge.py`:
   - `parse_pr_url(blackboard_text)` — read `pr:` line under `## Dev`.
   - `pr_state(url)` — `gh pr view <url> --json state` → "MERGED"/etc.
   - `auto_bump_merged(cfg, *, quiet=False)` — walk active tickets,
     find ones on final step (or no workflow) with merged PRs, call
     `bump_task` with `suffix="auto-bumped on PR merge of #N"`.
3. New `commands/automerge.py` — thin Typer wrapper over the scanner.
   Registered as `relay automerge` (added to `_BUILTIN_COMMANDS`).
4. `commands/status.py` calls `auto_bump_merged(cfg, quiet=True)`
   before rendering. `gh`-missing or unauthed swallowed silently
   (don't break the fast command). The explicit `relay automerge`
   path surfaces errors normally.
5. Ship `relay-os/hooks/post-merge` (single line: `relay automerge || true`).
   `relay init` and `relay init --update` set `core.hooksPath` on the
   host repo.

### Decisions (confirmed with nick)

- **Slack message:** distinct — `🎉 auto-bumped *<slug>* on merge of
  PR #N`. Log gets a matching distinct line.
- **Attribution:** `human:<current_user>` (whoever's machine triggered
  the hook or ran status).
- **Scope:** active + on final step OR no workflow. Mid-workflow merges
  stay alone.
- **Hook install:** auto-wire from `relay init` (and `init --update`).
- **CLI surface:** dedicated `relay automerge` command. Future cleanup
  tools (mentioned by nick) will compose with it.

### Idempotency

`auto_bump_merged` re-reads each ticket inside the loop. If status is
no longer `active` (someone else bumped first) or the step moved off
the final step, skip. Two callers (hook + status) racing won't
double-bump.

### Out of scope here

- GitHub Action (still deferred unless hook+status proves to have a
  gap).
- Auto-bumping intermediate steps on PR open — that's the agent's
  job at `code/open-pr` time.
- Bot-identity attribution.

## Dev

branch: auto-bump-on-pr-merge
pr: https://github.com/FastJVM/relay/pull/76

## Retro

status: processed
skill: retro/done-ticket
result: no-new-durable-knowledge
title: No new durable knowledge for auto-bump-tickets-when-their-pr-merges
