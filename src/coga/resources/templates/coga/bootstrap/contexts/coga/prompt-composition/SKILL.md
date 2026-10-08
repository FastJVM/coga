---
name: coga/prompt-composition
description: How `coga launch` builds an agent prompt — the exact layer order, what each layer reads (including repo overrides of the fixed text resources), the three-region ticket extract, the blocker preamble and authoring projection, failure on missing refs, what never composes, `--prompt-report`, and oversized-prompt delivery.
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
2. **Base prompt** (resource `prompt.md`): the operating loop; neutral on
   conduct.
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

### Launch marker

The very last line of every spawned prompt is `coga-launch: <uuid>`, a fresh
`uuid4` minted by `commands/launch.py` `spawn_agent_session` for that spawn
(after any `## Launch arguments` block and after a preflighted prompt). It is
not a layer: `--prompt-report` and `compose_prompt` never show it. It sits at
the end so everything before it stays a byte-stable prompt-cache prefix across
launches; a unique line near the top would break that. Usage capture uses it
to tell a launch's transcript from a concurrent one in the same cwd
([activity capture](../internals/activity-capture/SKILL.md)). The
oversized-prompt pointer (Delivery, below) repeats the line so it still
reaches the transcript.

## What each layer reads

- The fixed text layers read top-level resources, repo override first
  (`paths.load_resource`): `<coga root>/resources/<name>` (the directory
  `cfg.repo_root` names, `coga/resources/` by default) wholly replaces the
  packaged `src/coga/resources/<name>`; otherwise the packaged copy is read.
  The overridable names are `paths.RESOURCE_NAMES`: `prompt.md`, the three
  conduct resources, `prompt-blocker-resolution.md`, and two non-prompt
  resources rendered by other commands, `blackboard.md` (the stock placeholder
  `coga create` writes; [coga/blackboard](../blackboard/SKILL.md)) and
  `retire.md` (the `coga retire` task body, rendered with `str.format(slug=...)`,
  so a literal brace is doubled). Bootstrap launches use the same overrides.
  Override is **replace-only**: there is no append or patch mode, so an
  overridden file stops receiving upstream edits until someone merges them by
  hand. `templates/` is not part of this rule; it has its own local-override
  paths ([coga/packaging](../packaging/SKILL.md)). An override that exists but
  cannot be read, or a `retire.md` override that is not a valid template,
  raises `RepoResourceUnreadable` naming the repo file, never a silent
  fallback; compose reports it as a `ComposeError`. `coga validate` warns
  (`unknown-resource-override`) on a file in `resources/` that matches no
  resource name, ignoring `README.md` and dotfiles, so a typo cannot silently
  do nothing, and errors on an unreadable override.
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
`##`, using the shared fence-aware `taskfile.body_sections`, so a `##` line
inside a code fence does not end a section. Composition carries only
`## Description`, `## Context`, and the blackboard region. Every other `##`
section above the fence is uncomposed: it reaches no layer, but launch and
`--prompt-report` print an `uncomposed-section` warning naming it, as
`coga validate` does. Where that material belongs is owned by
[coga/tickets](../tickets/SKILL.md) (Body regions). `blackboard_for_prompt` replaces the exact
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
line names the selected resource, and the ticket's regions stay separate lines so an oversized blackboard is visible.
A fixed layer read from a repo override carries the override file as its
`PromptLayer.path` (unset means packaged), and the report lists those layers
under `Repo resource overrides:`. It
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
