---
name: coga/tickets/authoring
description: Creating, authoring and showing tickets — `coga create`, the guided `coga ticket` interview, how its authoring agent is chosen, and `coga show`.
---

# Creating, authoring, showing

Part of [coga/tickets](../SKILL.md).

- `coga create "<dir/>Title"` writes a raw `draft` (no Slack, no launch). A
  `/` separates an optional sub-directory prefix (created if missing) from
  the title leaf, which is slugified for the ref and kept verbatim as the
  title. It fails on `..`, nesting inside an existing task, or a non-slug-like
  prefix component (a literal slash in a title); a `_`-prefixed segment makes
  the target parked.
  `--workflow` is optional in draft ([coga/workflows](../../workflows/SKILL.md)).
  `--description` fills `## Description` and rejects a `##` line outside a
  code fence or an own-line fence (`create_task` applies the same guard for
  every programmatic caller); blank capture is intended only in a parked directory, and
  `coga validate` warns `empty-description` on non-terminal tickets. `--owner` overrides the local
  `user`; empty fails.
- `coga ticket [title|ref]` runs the guided `bootstrap/ticket` interview on a
  new draft or an existing ticket at any status. It chooses workflow, contexts
  and main agent with the human, repairs an out-of-vocabulary status, and
  validates afterwards: a draft left without a workflow is rejected there.
  `bootstrap/ticket` is injected only into that prompt, never persisted in
  `skills:`; a local `coga/skills/bootstrap/ticket/` overrides it. Standard
  `claude`/`codex` receive the prompt as system/developer context
  (`[agents.<type>].discussion` overrides the argv template).
- **Authoring agent.** `authoring.resolve_authoring_agent` picks who runs
  the interview, for `coga ticket` and megalaunch's picked drafts alike;
  the first set term wins: (1) `--agent`, `coga megalaunch --agent`, or the
  `--pick-agent` answer; (2) `COGA_AUTHORING_AGENT`; (3) `[authoring] agent`
  in `coga.local.toml`; (4) the target ticket's `agent:`; (5)
  `bootstrap/ticket`'s `agent:`, the install-level default; (6)
  `Config.default_agent()` (the `default_agent` key, else the first-declared
  type). An unknown name from any term fails loud naming
  that term, never falling through. The choice selects the interviewer only
  and is never written to the ticket. `coga ticket --pick-agent` (TTY only;
  refused with `--agent`) lists the configured types in declaration order,
  marks the would-be default, and takes Enter for it; with no valid default,
  Enter re-prompts. One configured type is used without asking; none fails.
  It prints how to make the choice stick and writes no config. Megalaunch
  never prompts: an unresolvable agent is reported and the draft left.
- `coga show <ref>` renders the ticket and its `coga/log.md` history for
  humans; bootstrap targets show only `ticket.md`. Read files directly for
  scripting.

Installed `coga <cmd> --help` is the syntax authority.
