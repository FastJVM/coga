---
name: coga/prompt-composition
description: How `coga launch` builds an agent prompt — the exact layer order, what each layer reads, the three-region ticket extract, the blocker preamble and authoring projection, failure on missing refs, what never composes, `--prompt-report`, and oversized-prompt delivery.
---

# Prompt composition

When an agent phase remains after any `ticket.py` phase
([coga/script-tickets](../script-tickets/SKILL.md)), launch builds one prompt
with `src/coga/compose.py` `compose_prompt_report` and writes it to a temp
file (`write_prompt_file`). The prompt is a pure function of the files on disk
at that moment: nothing carries over from an earlier session, so a corrected
file takes full effect on the next launch. There is no follow-up loading.

## Layer order

Each layer is a `PromptLayer`; in order:

1. **Header**: task ref, title, exact task directory, status.
2. **Base prompt** (package resource `prompt.md`): the operating loop; neutral
   on conduct.
3. **Session conduct**: exactly one resource chosen by launch context
   ([coga/session-conduct](../session-conduct/SKILL.md)).
4. **Blocker preamble** (`prompt-blocker-resolution.md`), only when the
   filtered blackboard has open `## Blockers` asks; see below.
5. **Repo context**: `<coga root>/context.md`, if present.
6. **Ticket contexts**: each `contexts:` ref, in list order.
7. **Skills**: each ticket-level `skills:` ref, then the current step's
   skills, or, for a skill-less step, its inline section from the live
   workflow definition ([coga/workflows](../workflows/SKILL.md)).
8. **The ticket**, last and contiguous in on-disk order: `## Description`,
   then `## Context`, then the live blackboard.

After the task layers, launch appends a `## Launch arguments` JSON block only
when positional launch arguments were given ([coga/launch](../launch/SKILL.md)).
Conduct is never appended there.

## What each layer reads

- Contexts and skills resolve local-first, then the package bootstrap copy
  (`paths.resolve_context_path`, `resolve_skill_path`), and are read **whole**:
  `SKILL.md` frontmatter (`name`, `description`) is included in the prompt.
- Markdown links inside a context or skill are not followed; only attached
  refs compose ([coga/knowledge](../knowledge/SKILL.md)).
- A missing context, skill, or packaged resource raises `ComposeError` naming
  the paths checked, before launch publishes `in_progress` or spawns. A
  deleted workflow definition does not raise here; it composes a placeholder
  and is caught by validation instead.

## The ticket is a three-region extract

`_extract_section` takes one `##` heading (case-insensitive) up to the next
`##`. Composition carries only `## Description`, `## Context`, and the
blackboard region. Every other `##` section above the fence is dropped with no
warning and no report line. `blackboard_for_prompt` replaces the exact
`## Superseded designs` content with a short pointer to the ticket file and
archive heading; the stored ticket is unchanged. The same projection feeds the
blocker preamble, the report's blackboard size, and the size warning.

## Blocker preamble versus authoring

The preamble is derived from state, not a flag: it appears while unresolved
asks exist and disappears once `coga unblock` records an answer, so it
survives a session that dies mid-discussion. It lists open asks verbatim and
makes resolve-or-re-block the session's first job.

Guided `coga ticket` authoring composes an ephemeral projection
(`commands/ticket.py` `_authoring_ticket`): `skills:` becomes only
`bootstrap/ticket`, `step:` is removed so no step layer composes, and the
blocker preamble is off (`include_blocker_preamble=False`). Blocker text still
appears in the blackboard layer, so authoring a blocked ticket neither runs
its step, resolves its asks, nor reactivates it. The stored ticket keeps its
workflow position.

## What never composes

- `coga/log.md`: repo-global, append-only, never a layer, so it can grow
  without bound. Only the blackboard carries state forward.
- Ticket attachments and superseded-design text (pointer only).
- Unattached contexts, docs pages, and anything reached by a link.

## Measuring

`coga launch <ref> --prompt-report` prints one line per layer (layer id, ref,
bytes, `approx_tokens` = ceil(chars/4)) and the total; the `session_conduct`
line names the selected resource, and the ticket's regions stay separate lines so an oversized blackboard is visible. It
works on drafts but runs the normal state sweep; for a read-only comparison
call `compose_prompt_report` on an in-memory ticket copy.

## Delivery

The prompt rides the agent CLI's argv, and Linux caps one argument at
128 KiB. Above `commands/launch.py` `_MAX_PROMPT_ARG_BYTES` (120,000 bytes)
launch passes a short pointer telling the agent to read the prompt file,
which stays on disk for the session; content is unchanged. Such a size usually
means context bloat. The session's done signal is a side-channel sentinel
file, so nothing in the prompt text can end a session and the prompt is
passed verbatim ([coga/internals/agent-spawn](../internals/agent-spawn/SKILL.md)).
