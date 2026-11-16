---
name: coga-dev/internals/compose
description: How `src/coga/compose.py` implements prompt composition — prompt files, `PromptLayer`, the launch marker, resource-override errors and validate codes, section extraction, blackboard projections, layer normalization, the authoring projection, conduct selection, and argv delivery of large prompts.
---

# Prompt composition internals

The user contract (layer order, what each layer reads, conduct selection) is
[coga/prompt-composition](../../../../../src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md). This
page holds what a change to `src/coga/compose.py` or its launch callers must
not break.

## Prompt files

Launch builds one prompt with `compose.compose_prompt_report` and writes it
with `write_prompt_file`. Each file is exclusively created with a unique name
and UTF-8 contents in the system temporary directory (or the caller's
supplied directory). The task ref is a readable filename prefix, not its
identity: simultaneous launches of the same ref, including from different
repositories, have independent files. The file remains available until its
own agent session cleans it up.

Each layer is a `PromptLayer`. A fixed layer read from a repo override carries
the override file as its `PromptLayer.path` (unset means packaged), which is
how `--prompt-report` lists `Repo resource overrides:`. The checkout notice
is built from `compose.CheckoutNotice`; composition runs no Git and infers
nothing from the workflow, so callers that pass no notice (bare
`compose_prompt_report`, megalaunch, recurring) get the "no preparation was
supplied" text.

## Launch marker

The very last line of every spawned prompt is `coga-launch: <uuid>`, a fresh
`uuid4` minted by `launch.py` `spawn_agent_session` for that spawn (after any
`## Launch arguments` block and after a preflighted prompt). It is not a
layer: `--prompt-report` and `compose_prompt` never show it. It sits at the
end so everything before it stays a byte-stable prompt-cache prefix across
launches; a unique line near the top would break that. Usage capture uses it
to tell a launch's transcript from a concurrent one in the same cwd
([activity capture](../activity-capture/SKILL.md)). The oversized-prompt
pointer (below) repeats the line so it still reaches the transcript.

## Resource overrides

`paths.load_resource` reads `<coga root>/resources/<name>` (the directory
`cfg.repo_root` names) before the packaged `src/coga/resources/<name>`; the
overridable names are `paths.RESOURCE_NAMES`. `retire.md` is rendered with
`str.format(slug=...)`, so a literal brace is doubled; `ticket.md` replaces
exactly one literal `{description}`.

An override that exists but cannot be read, or a `retire.md` or `ticket.md`
override that is not a valid template, raises `RepoResourceUnreadable` naming
the repo file, never a silent fallback; broken symlinks and non-file entries
at known names also refuse. Compose reports it as a `ComposeError`. Task
creation reads the blackboard before allocating its destination so repairing
an override permits retry; recurring creation reports the error per template
and continues the sweep. `coga validate` warns (`unknown-resource-override`)
on a file in `resources/` that matches no resource name, ignoring `README.md`
and dotfiles, and errors (`unreadable-resource-override`) on an unreadable
override or an existing `resources` root that cannot be inspected or listed
as a directory. A missing root is allowed; a broken symlink is an error.

Contexts and skills resolve through `paths.resolve_context_path` and
`resolve_skill_path`. A missing context, skill, or packaged resource raises
`ComposeError` naming the paths checked. A deleted workflow definition
composes a placeholder and is caught by validation instead; an existing
inline workflow definition with invalid YAML, an invalid schema, or a read
failure raises `ComposeError` with its path and cause. Only genuine absence
selects the placeholder; unexpected programming errors are not swallowed.

## Ticket extraction and projections

`compose_prompt_report` first runs `_without_html_comments` over the body
above the fence, so a complete comment holding `##` lines cannot end or start
a section. `_extract_section` then takes one `##` heading (case-insensitive)
up to the next `##`, using the shared fence-aware `taskfile.body_sections`,
so a `##` line inside a code fence does not end a section. The stripped body
is composition-only: `taskfile.body_sections` callers, validation and the
file see the comment.

The blackboard region passes through, in order:
`blackboard.without_stock_placeholder` (before the archive pointer exists, so
a placeholder leading the stored region is still recognized; candidates come
from `_stock_templates`, shared with `_is_stock_blackboard`);
`blackboard_for_prompt`, which replaces the exact `## Superseded designs`
content with a pointer and feeds the blocker preamble; then, only when the
preamble layer composes, `blackboard.without_open_blockers`, which removes
the entry lines `_scan_blockers` reports open (the same scan as
`parse_blockers_text`) and puts `compose.OPEN_BLOCKERS_POINTER` once in their
place. `blackboard_size_warning` still measures `blackboard_for_prompt`
alone; readiness still uses `_is_stock_blackboard` on the whole region.

## Layer normalization

Every `PromptLayer` except the header (raw) and the checkout notice is built
from `_prompt_text(text, drop_title=..., frontmatter=...)`, so `text`,
`rendered`, the report and the prompt agree. Steps, line-based over
`taskfile.markdown_lines` so fenced lines are untouched: strip a leading
`_FRONTMATTER_RE` block (whole-file layers only; ticket regions and inline
workflow sections pass `frontmatter=False`, because a leading `---` there is a
rule, not frontmatter); `_without_html_comments` (a non-fenced line starting
with `<!--` through the first `-->`, which must end its line, plus one
following blank line; an unterminated opener stays); with `drop_title`, drop
the first non-blank line when it is the body's single shallowest ATX heading;
demote every remaining ATX heading so the shallowest is level 3, never
promoting, clamped at 6. `drop_title` is true for fixed resources,
`context.md`, contexts and skills, and false for inline workflow sections,
the ticket regions and the blackboard, whose first heading is content. The
conduct layer's title is `_leading_heading` of its resource.

Guided `coga ticket` authoring composes `commands/ticket.py`
`_authoring_ticket`: `skills:` becomes only `bootstrap/ticket`, `step:` is
removed, and `include_blocker_preamble=False`.

## Conduct selection

`compose.SESSION_CONDUCT_RESOURCES` maps the ephemeral `LaunchContext`
passed to `compose_prompt` / `compose_prompt_report` as `launch_context`;
`recurring_runner._recurring_launch_context` picks the recurring one. An
unknown context or a missing resource is a `ComposeError` at the same
preflight boundary as any missing layer.

The two queue resources are deliberately complete documents rather than a
shared fragment plus tails: only one ever reaches an agent, so repetition
costs no runtime tokens and the highest-consequence policy reads as one unit.

## Delivery

The prompt rides the agent CLI's argv, and Linux caps one argument at
128 KiB. Above `launch.py` `_MAX_PROMPT_ARG_BYTES` (120,000 bytes) launch
passes a short pointer telling the agent to read the prompt file, which stays
on disk for the session; content is unchanged. The session's done signal is a
side-channel sentinel file, so nothing in the prompt text can end a session
and the prompt is passed verbatim ([agent spawn](../agent-spawn/SKILL.md)).
