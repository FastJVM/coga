---
name: coga/tickets/authoring
description: Creating, authoring and showing tickets — `coga create`, the guided `coga ticket` interview, how its authoring agent is chosen, and `coga show`.
---

# Creating, authoring, showing

Part of [coga/tickets](../SKILL.md). Installed `coga <cmd> --help` is the
syntax authority for every flag.

- `coga create "<dir/>Title"` writes a raw `draft` (no Slack, no launch). A
  `/` separates an optional group path (created if missing) from the title
  leaf, which is slugified for the ref and kept verbatim as the title. A
  `_`-prefixed segment makes the target parked
  ([discovery](../discovery/SKILL.md)). A workflow is optional in draft
  ([coga/workflows](../../workflows/SKILL.md)). A supplied description may not
  contain a `##` heading or an own-line blackboard fence; a blank description
  is meant only for parked captures, and `coga validate` warns
  `empty-description` on non-terminal tickets.
- `coga ticket [title|ref]` runs the guided `bootstrap/ticket` interview on a
  new draft or an existing ticket at any status. It chooses workflow, contexts
  and main agent with the human, repairs an out-of-vocabulary status, and
  validates afterwards: a draft left without a workflow is rejected there.
  `bootstrap/ticket` is injected only into that prompt, never persisted in
  `skills:`; a local `coga/skills/bootstrap/ticket/` overrides it. Standard
  `claude`/`codex` receive the prompt as system/developer context
  (`[agents.<type>].discussion` overrides the argv template).
- **Authoring agent.** The same resolution picks who runs the interview for
  `coga ticket` and megalaunch's picked drafts; the first set term wins:
  (1) `--agent`, `coga megalaunch --agent`, or the `--pick-agent` answer;
  (2) `COGA_AUTHORING_AGENT`; (3) `[authoring] agent` in `coga.local.toml`;
  (4) the target ticket's `agent:`; (5) `bootstrap/ticket`'s `agent:`, the
  install-level default; (6) the configured default agent. An unknown name
  from any term fails loud naming that term, never falling through. The
  choice selects the interviewer only and is never written to the ticket.
  `--pick-agent` (TTY only) lists the configured types and marks the would-be
  default; it writes no config. Megalaunch never prompts: an unresolvable
  agent is reported and the draft left.
- `coga show <ref>` renders the ticket and its `coga/log.md` history for
  humans; bootstrap targets show only `ticket.md`. Read files directly for
  scripting.

The interview preserves the ticket's guide comment and supplies only the
authoring process and its metadata-edit exception; readers need no separate
editing skill.
