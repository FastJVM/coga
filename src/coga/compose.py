"""Prompt composition — the core of `coga launch`."""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from coga.oscompat import system_tmpdir
from coga.blackboard import (
    BLOCKER_TS_FORMAT,
    Blocker,
    blackboard_for_prompt,
    parse_blockers_text,
    without_open_blockers,
    without_stock_placeholder,
)
from coga.config import Config, ConfigError
from coga.paths import (
    PackagedResourceMissing,
    RepoResourceUnreadable,
    context_resolution_paths,
    load_resource,
    missing_skill_message,
    repo_context_path,
    resolve_context_path,
    LocalOverrideError,
    resolve_skill_path,
    resolve_workflow_path,
    workflow_path,
)
from coga.taskfile import body_sections, markdown_lines, split_body
from coga.tasks import BootstrapRef, TargetRef
from coga.ticket import Ticket
from coga.workflow import Workflow, WorkflowError, WorkflowNotFoundError


class ComposeError(RuntimeError):
    """A referenced context or skill could not be resolved at compose time.

    Raised rather than silently dropping the layer: a missing context/skill
    means the launched agent would run without knowledge the human expected
    it to have, producing confidently wrong output. `coga launch` catches
    this and refuses to start the task. `coga validate` catches the same
    condition statically.
    """


LaunchContext = Literal["attended", "megalaunch", "recurring"]
"""How this session was invoked. The selector for session conduct.

This is ephemeral launch-invocation state supplied by the caller, never a
ticket field or a config option: how a session executes is a property of the
invocation, not of the task (#545). `coga launch`, `coga chat`, guided
`coga ticket` authoring, and every `--interactive` recurring spelling are
attended; `coga megalaunch` and automatic runner-owned recurring execution are
their respective queues.
"""

SESSION_CONDUCT_RESOURCES: dict[str, str] = {
    "attended": "prompt-attended.md",
    "megalaunch": "prompt-megalaunch.md",
    "recurring": "prompt-queue.md",
}
"""One conduct resource per launch context — selected, never stacked.

Conduct used to be an attended default in `prompt.md` plus a queue block
appended after the task layers, so a queued prompt carried a rule and its
inverse and correctness rode on precedence prose. Exactly one of these is
composed instead, as a reported `session_conduct` layer. The two queue
resources are deliberately complete rather than a shared fragment plus tails:
only one ever reaches an agent, so the repeated wording costs no runtime
tokens, and the highest-consequence policy stays readable as one unit.
"""


OPEN_BLOCKERS_POINTER = (
    '- Open asks are listed under "Resolve the open blocker first" above.'
)
"""Stands where open blocker entries were when the preamble lists them."""

EMPTY_BLACKBOARD_TEXT = "*No state recorded yet.*"
"""Body of a blackboard layer whose region holds only placeholder or nothing."""


@dataclass(frozen=True)
class PromptLayer:
    """One included layer of a composed Coga prompt."""

    layer: str
    title: str
    text: str
    ref: str | None = None
    path: str | None = None
    raw: bool = False

    @property
    def rendered(self) -> str:
        if self.raw:
            return self.text
        return _section(self.title, self.text)

    @property
    def byte_count(self) -> int:
        return len(self.rendered.encode())

    @property
    def char_count(self) -> int:
        return len(self.rendered)

    @property
    def approx_tokens(self) -> int:
        return estimate_tokens(self.rendered)


@dataclass(frozen=True)
class PromptComposition:
    """Composed prompt plus layer metadata for prompt-scope reporting."""

    layers: list[PromptLayer]

    @property
    def prompt(self) -> str:
        return "\n\n---\n\n".join(
            layer.rendered.strip() for layer in self.layers if layer.rendered.strip()
        ) + "\n"

    @property
    def byte_count(self) -> int:
        return len(self.prompt.encode())

    @property
    def char_count(self) -> int:
        return len(self.prompt)

    @property
    def approx_tokens(self) -> int:
        return estimate_tokens(self.prompt)


def estimate_tokens(text: str) -> int:
    """Dependency-free approximation: about one token per four characters."""
    if not text:
        return 0
    return (len(text) + 3) // 4


def compose_prompt(
    cfg: Config,
    task_ref: TargetRef,
    ticket: Ticket,
    *,
    include_blocker_preamble: bool = True,
    launch_context: LaunchContext = "attended",
    resolved: ResolvedPromptLayers | None = None,
) -> str:
    """Assemble the composed prompt in spec order (§compose)."""
    return compose_prompt_report(
        cfg,
        task_ref,
        ticket,
        include_blocker_preamble=include_blocker_preamble,
        launch_context=launch_context,
        resolved=resolved,
    ).prompt


@dataclass(frozen=True)
class ResolvedPromptLayers:
    """The file-backed half of one composition, resolved and read once.

    `resolve_prompt_layers` produces it; `compose_prompt_report` renders the
    ticket-derived and runtime layers around it. `selection` records every
    input that chose these files, so a ticket whose contexts, skills, step, or
    workflow differ is never rendered against them: composition re-resolves
    instead. The text is what was read at resolve time.
    """

    selection: tuple[object, ...]
    base: PromptLayer
    ticket_loop: PromptLayer | None
    session_conduct: PromptLayer
    repo_context: PromptLayer | None
    ticket_contexts: tuple[PromptLayer, ...]
    skills: tuple[PromptLayer, ...]
    blocker_template: tuple[str, Path | None] | None


def _layer_selection(
    task_ref: TargetRef,
    ticket: Ticket,
    *,
    include_blocker_preamble: bool,
    launch_context: LaunchContext,
) -> tuple[object, ...]:
    workflow = ticket.workflow
    workflow_name = workflow.get("name") if isinstance(workflow, dict) else None
    return (
        task_ref.id_slug,
        isinstance(task_ref, BootstrapRef),
        launch_context,
        include_blocker_preamble,
        tuple(ticket.contexts),
        tuple(ticket.skills),
        repr(ticket.current_step()),
        workflow_name,
    )


def _prompt_blackboard(cfg: Config, task_ref: TargetRef, ticket: Ticket) -> tuple[str, str | None]:
    """Split the ticket body at the fence and filter the blackboard for prompts.

    Bootstrap tickets legitimately carry no fence, so they are parsed
    leniently (blackboard is then None and the blackboard layer is omitted);
    a normal task ticket missing the fence fails loud.
    """
    body_above, blackboard_text = split_body(
        ticket.body, blackboard_required=not isinstance(task_ref, BootstrapRef)
    )
    # Comments go before section extraction too: a complete comment holding a
    # `## Context` line must neither end a section nor start one. Composition
    # only; the file and `body_sections` callers elsewhere are unchanged.
    body_above = _without_html_comments(body_above)
    if blackboard_text is not None:
        # The stock placeholder goes first, while it is still in place: the
        # archive projection below prepends a pointer line.
        blackboard_text = without_stock_placeholder(
            blackboard_text, cfg=cfg, task_title=ticket.title
        )
        # Filter before every prompt consumer, including the blocker preamble:
        # historical blocker examples must not reappear as current asks.
        blackboard_text = blackboard_for_prompt(blackboard_text, task_ref.ticket_path)
    return body_above, blackboard_text


def _open_asks(
    task_ref: TargetRef,
    blackboard_text: str | None,
    *,
    include_blocker_preamble: bool,
) -> list[Blocker]:
    if not include_blocker_preamble or isinstance(task_ref, BootstrapRef):
        return []
    return [
        b for b in parse_blockers_text(blackboard_text or "") if not b.resolved
    ]


def resolve_prompt_layers(
    cfg: Config,
    task_ref: TargetRef,
    ticket: Ticket,
    *,
    include_blocker_preamble: bool = True,
    launch_context: LaunchContext = "attended",
) -> ResolvedPromptLayers:
    """Resolve and read every file-backed layer this ticket selects.

    This is where a missing context, skill, or resource raises `ComposeError`
    and a layer file that vanished between resolve and read raises
    `FileNotFoundError`; the ticket's own shape (a missing blackboard fence)
    is checked here too. `coga launch` calls it as its pre-activation refusal
    point and hands the result to the one composition the spawn uses, so a
    launch reads each layer file once and assembles the prompt once.
    """
    _, blackboard_text = _prompt_blackboard(cfg, task_ref, ticket)

    # 1. Base prompt — neutral on conduct. It cross-references the selected
    # layer below rather than carrying a default that a later layer overrides.
    base_text, base_path = _resource(cfg, "prompt.md")
    base = PromptLayer(
        "base_prompt",
        "Coga base prompt",
        _prompt_text(base_text, drop_title=True),
        ref="prompt.md",
        path=_override_path(base_path),
    )

    # 1b. Ticket loop — blackboard, bump, block. Only a task ticket has that
    # lifecycle; a stateless bootstrap target finishes as its own ticket says,
    # so composing these rules there would only be contradicted by it.
    ticket_loop = None
    if not isinstance(task_ref, BootstrapRef):
        loop_text, loop_path = _resource(cfg, "prompt-ticket.md")
        ticket_loop = PromptLayer(
            "ticket_loop",
            "Ticket loop",
            _prompt_text(loop_text, drop_title=True),
            ref="prompt-ticket.md",
            path=_override_path(loop_path),
        )

    # 2. Session conduct, selected by launch context. Exactly one, immediately
    # after the neutral base so the agent reads how to operate before any task
    # material. A missing resource is a ComposeError like any other dropped
    # layer: launch refuses before it publishes `in_progress` or spawns.
    conduct_resource = SESSION_CONDUCT_RESOURCES.get(launch_context)
    if conduct_resource is None:
        raise ComposeError(
            f"Unknown launch context {launch_context!r}. Valid contexts: "
            f"{', '.join(sorted(SESSION_CONDUCT_RESOURCES))}."
        )
    # The resource's own `## Session conduct — <context>` heading becomes the
    # layer title, so the selected context stays visible to the agent instead
    # of being flattened into one generic title.
    conduct_text, conduct_path = _resource(cfg, conduct_resource)
    session_conduct = PromptLayer(
        "session_conduct",
        _leading_heading(conduct_text) or "Session conduct",
        _prompt_text(conduct_text, drop_title=True),
        ref=conduct_resource,
        path=_override_path(conduct_path),
    )

    # 2b. The blocker-resolution template is read only when this ticket has
    # open asks now; a render that finds asks a later ticket gained reads it
    # then (see `compose_prompt_report`).
    blocker_template = None
    if _open_asks(
        task_ref, blackboard_text, include_blocker_preamble=include_blocker_preamble
    ):
        blocker_template = _resource(cfg, "prompt-blocker-resolution.md")

    # 3. repo context.md
    repo_context = None
    pctx = repo_context_path(cfg)
    if pctx.is_file():
        repo_context = PromptLayer(
            "repo_context",
            "Repo context",
            _prompt_text(pctx.read_text(encoding="utf-8"), drop_title=True),
            ref="context.md",
            path=str(pctx),
        )

    # 4. ticket-attached contexts
    ticket_contexts: list[PromptLayer] = []
    for ref in ticket.contexts:
        try:
            cp = resolve_context_path(cfg, ref)
        except ConfigError as exc:
            raise ComposeError(f"Task {task_ref.id_slug!r}: {exc}") from exc
        if cp is None:
            checked = _checked_context_paths(cfg, ref)
            raise ComposeError(
                f"Task {task_ref.id_slug!r} references context {ref!r}, but no "
                f"context file exists for it. Checked: {checked}. Create one of "
                f"those files or remove {ref!r} from the ticket's `contexts:` list."
            )
        ticket_contexts.append(PromptLayer(
            "ticket_context",
            f"Context — {ref}",
            _prompt_text(cp.read_text(encoding="utf-8"), drop_title=True),
            ref=ref,
            path=str(cp),
        ))

    # 5. ticket-level skills + current workflow step
    skills: list[PromptLayer] = []
    for skill_ref in ticket.skills:
        skills.extend(_skill_layers(cfg, skill_ref, slug=task_ref.id_slug))
    skills.extend(_step_layers(cfg, ticket, slug=task_ref.id_slug))

    return ResolvedPromptLayers(
        selection=_layer_selection(
            task_ref,
            ticket,
            include_blocker_preamble=include_blocker_preamble,
            launch_context=launch_context,
        ),
        base=base,
        ticket_loop=ticket_loop,
        session_conduct=session_conduct,
        repo_context=repo_context,
        ticket_contexts=tuple(ticket_contexts),
        skills=tuple(skills),
        blocker_template=blocker_template,
    )


def compose_prompt_report(
    cfg: Config,
    task_ref: TargetRef,
    ticket: Ticket,
    *,
    include_blocker_preamble: bool = True,
    launch_context: LaunchContext = "attended",
    resolved: ResolvedPromptLayers | None = None,
) -> PromptComposition:
    """Assemble the prompt and keep per-layer measurement metadata.

    `launch_context` selects the one composed session-conduct layer. It
    defaults to `"attended"` so any caller that does not know it is draining a
    queue gets the ask-a-present-human contract. `checkout` is the launcher's
    observed checkout result, rendered as a runtime appendix after the ticket;
    without one the appendix says that no preparation was supplied.

    `resolved` is a caller's earlier `resolve_prompt_layers` result. It is
    used only when its selection matches this ticket and these arguments;
    otherwise the file-backed layers are resolved here. Either way the
    header, blocker preamble, ticket regions, and checkout notice are rendered
    from `ticket` and `checkout` as passed.
    """
    selection = _layer_selection(
        task_ref,
        ticket,
        include_blocker_preamble=include_blocker_preamble,
        launch_context=launch_context,
    )
    if resolved is None or resolved.selection != selection:
        resolved = resolve_prompt_layers(
            cfg,
            task_ref,
            ticket,
            include_blocker_preamble=include_blocker_preamble,
            launch_context=launch_context,
        )

    # The ticket body splits at the blackboard fence: the body above feeds the
    # Description / inline-Context layers, the region below is the blackboard.
    body_above, blackboard_text = _prompt_blackboard(cfg, task_ref, ticket)

    layers: list[PromptLayer] = []
    header = (
        f"# Coga task — {task_ref.id_slug}\n\n"
        f"Title: {ticket.title}\n"
        f"Task directory: {_task_path_for_prompt(cfg, task_ref)}"
    )
    if ticket.status:
        header += f"\nStatus: {ticket.status}"
    layers.append(PromptLayer("header", "Header", header, raw=True))

    # 1. Base prompt, 1b. ticket loop, 2. session conduct.
    layers.append(resolved.base)
    if resolved.ticket_loop is not None:
        layers.append(resolved.ticket_loop)
    layers.append(resolved.session_conduct)

    # 2b. Blocker-resolution preamble. An interactive session whose blackboard
    # still carries open asks must resolve-or-re-block before the step's real
    # work — this is how `coga launch` resumes a blocked ticket as a chat
    # (launch reactivates it inline, so by compose time `status:` is already
    # `in_progress`; the open asks are the durable signal). Keying off the
    # blackboard rather than a launch-threaded flag keeps the preamble purely
    # composed state: it reappears if a session dies mid-discussion and
    # disappears once `coga unblock` records the answer.
    open_asks = _open_asks(
        task_ref, blackboard_text, include_blocker_preamble=include_blocker_preamble
    )
    if open_asks:
        template = resolved.blocker_template
        if template is None:
            template = _resource(cfg, "prompt-blocker-resolution.md")
        preamble, preamble_path = _blocker_preamble(
            task_ref.id_slug, open_asks, template
        )
        # The preamble carries the open asks; the blackboard keeps a pointer.
        blackboard_text = without_open_blockers(
            blackboard_text or "", OPEN_BLOCKERS_POINTER
        )
        layers.append(PromptLayer(
            "blocker_preamble",
            "Resolve the open blocker first",
            _prompt_text(preamble, drop_title=True),
            ref="prompt-blocker-resolution.md",
            path=_override_path(preamble_path),
        ))

    # 3. repo context.md, 4. ticket-attached contexts, 5. skills + step.
    if resolved.repo_context is not None:
        layers.append(resolved.repo_context)
    layers.extend(resolved.ticket_contexts)
    layers.extend(resolved.skills)

    # 6. The ticket itself, last and contiguous, in the order it sits on disk:
    # `## Description`, then `## Context`, then the blackboard region below the
    # fence. These were three layers scattered across the prompt back when they
    # were three files (ticket.md / blackboard.md / log.md); #427 collapsed them
    # into one file and the split outlived the reason for it. They stay separate
    # PromptLayers so `--prompt-report` can still size the blackboard on its own
    # — that line is how a bloated blackboard gets noticed — but they compose as
    # one contiguous block, so the agent reads the ticket as written.
    desc = _extract_section(body_above, "Description")
    if desc:
        layers.append(PromptLayer(
            "task_description",
            "Task description",
            _prompt_text(desc, drop_title=False, frontmatter=False),
            ref="ticket.md##Description",
            path=str(task_ref.ticket_path),
        ))

    inline_ctx = _extract_section(body_above, "Context")
    if inline_ctx:
        layers.append(PromptLayer(
            "task_context",
            "Task-specific context",
            _prompt_text(inline_ctx, drop_title=False, frontmatter=False),
            ref="ticket.md##Context",
            path=str(task_ref.ticket_path),
        ))

    if blackboard_text is not None:
        # An existing region always composes: the ticket loop tells the agent
        # the blackboard is in the prompt, so an empty one says so.
        board = _prompt_text(blackboard_text, drop_title=False, frontmatter=False)
        layers.append(PromptLayer(
            "blackboard",
            "Blackboard (current state)",
            board if board.strip() else EMPTY_BLACKBOARD_TEXT,
            ref="ticket.md##blackboard",
            path=str(task_ref.ticket_path),
        ))

    return PromptComposition(layers)


def write_prompt_file(prompt: str, task_ref: TargetRef, dest_dir: Path | None = None) -> Path:
    """Exclusively create a UTF-8 prompt file that survives until session cleanup."""
    safe_slug = task_ref.id_slug.replace("/", "-")
    prompt_file = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", prefix=f"coga-{safe_slug}-", suffix=".md",
        dir=system_tmpdir() if dest_dir is None else dest_dir, delete=False,
    )
    path = Path(prompt_file.name)
    try:
        with prompt_file:
            prompt_file.write(prompt)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


# --- helpers ------------------------------------------------------------------


def _resource(cfg: Config, name: str) -> tuple[str, Path | None]:
    """Read a fixed prompt layer, as a ComposeError when it can't be read.

    The repo's `resources/<name>` override wins over the packaged copy; the
    returned path is that override, or `None` for the packaged text. Same
    shape as a missing context or skill: the layer the human expected is
    absent, so refuse rather than compose a prompt without it. Sharing
    `ComposeError` also keeps it inside the per-task `except` that `coga
    launch` and the megalaunch sweep already have, so one unreadable resource
    fails that task instead of unwinding the whole queue.
    """
    try:
        return load_resource(cfg, name)
    except (PackagedResourceMissing, RepoResourceUnreadable) as exc:
        raise ComposeError(str(exc)) from exc


def _override_path(path: Path | None) -> str | None:
    return str(path) if path is not None else None


def _task_path_for_prompt(cfg: Config, task_ref: TargetRef) -> str:
    if isinstance(task_ref, BootstrapRef):
        return task_ref.id_slug
    path = task_ref.path.resolve(strict=False)
    try:
        rel = path.relative_to(cfg.repo_root.resolve(strict=False))
    except ValueError:
        return str(path)
    return str(Path(cfg.repo_root.name) / rel)


def _blocker_preamble(
    slug: str, open_asks: list[Blocker], template: tuple[str, Path | None]
) -> tuple[str, Path | None]:
    """Render the resolve-or-re-block preamble for a ticket with open asks.

    The asks are listed verbatim (stale and junk ones included) so the human
    can clear them in the session.
    """
    lines = []
    for blocker in open_asks:
        ts = (
            blocker.created_at.strftime(BLOCKER_TS_FORMAT)
            if blocker.created_at
            else "unknown time"
        )
        lines.append(f"- [{ts}] [{blocker.actor}] {blocker.reason}")
    text, path = template
    rendered = text.replace("{slug}", slug).replace("{blockers}", "\n".join(lines))
    return rendered, path


def _section(title: str, body: str) -> str:
    body = body.strip()
    return f"## {title}\n\n{body}"


_FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(?:.*?\r?\n)?---[ \t]*(?:\r?\n|\Z)", re.DOTALL
)
_ATX_HEADING_RE = re.compile(r"^( {0,3})(#{1,6})(?=[ \t\r\n]|$)")
_COMMENT_OPEN_RE = re.compile(r"^ {0,3}<!--")
_LAYER_BODY_MIN_LEVEL = 3


def _prompt_text(text: str, *, drop_title: bool, frontmatter: bool = True) -> str:
    """Normalize one file-backed layer body for the prompt.

    In order: drop a leading YAML frontmatter block (whole-file layers only),
    drop HTML comment blocks, drop the document title when `drop_title` and
    the body opens with its one shallowest heading, then demote ATX headings
    so the shallowest sits at level 3 under the `##` layer heading. Fenced
    lines are never touched, and setext headings are left alone because
    blackboards use `---` as a separator.
    """
    if frontmatter:
        text = _FRONTMATTER_RE.sub("", text, count=1)
    lines = list(markdown_lines(_without_html_comments(text)))
    headings = [
        (index, len(match.group(2)))
        for index, (line, fenced) in enumerate(lines)
        if not fenced and (match := _ATX_HEADING_RE.match(line))
    ]
    if drop_title and headings:
        first = next(i for i, (line, _) in enumerate(lines) if line.strip())
        top = min(level for _, level in headings)
        index, level = headings[0]
        if index == first and level == top and sum(
            1 for _, other in headings if other == top
        ) == 1:
            lines[index] = ("", False)
            headings = headings[1:]
    shift = 0
    if headings:
        shift = max(0, _LAYER_BODY_MIN_LEVEL - min(level for _, level in headings))
    out: list[str] = []
    heading_lines = {index for index, _ in headings}
    for index, (line, _) in enumerate(lines):
        match = _ATX_HEADING_RE.match(line) if index in heading_lines else None
        if shift and match:
            level = min(6, len(match.group(2)) + shift)
            line = match.group(1) + "#" * level + line[match.end():]
        out.append(line)
    return "".join(out)


def _leading_heading(text: str) -> str | None:
    """The text of a resource's leading ATX heading, if it opens with one."""
    text = _without_html_comments(_FRONTMATTER_RE.sub("", text, count=1))
    for line, fenced in markdown_lines(text):
        if not line.strip():
            continue
        if fenced or not _ATX_HEADING_RE.match(line):
            return None
        title = line.strip().lstrip("#").strip()
        return re.sub(r"(?:^|[ \t]+)#+$", "", title).strip() or None
    return None


def _without_html_comments(text: str) -> str:
    """Remove whole-line HTML comment blocks outside code fences.

    A block starts on a line whose content (after up to three spaces) opens
    with `<!--` and runs through the first `-->`, which must end its line.
    An unterminated opener, or a block with text after its `-->`, is kept as
    written; inline comments mid-line are prose. One blank line after a
    removed block goes with it.
    """
    lines = list(markdown_lines(text))
    out: list[str] = []
    index = 0
    while index < len(lines):
        line, fenced = lines[index]
        end = None if fenced or not _COMMENT_OPEN_RE.match(line) else _comment_end(
            lines, index
        )
        if end is None:
            out.append(line)
            index += 1
            continue
        index = end + 1
        if index < len(lines) and not lines[index][0].strip():
            index += 1
    return "".join(out)


def _comment_end(lines: list[tuple[str, bool]], start: int) -> int | None:
    """Index of the line closing the comment opened at `start`, if clean."""
    for index in range(start, len(lines)):
        line = lines[index][0]
        if index == start:
            line = line[line.index("<!--") + 4:]
        close = line.find("-->")
        if close != -1:
            return index if not line[close + 3:].strip() else None
    return None


def _extract_section(body: str, heading: str) -> str:
    """Extract the contents of `## <heading>` from a markdown body.

    Sections come from the shared fence-aware `taskfile.body_sections`, so a
    `##` line inside a fenced example does not end the section.
    """
    for section in body_sections(body):
        if section.key == heading.lower():
            return body[section.content_start:section.end].strip()
    return ""


def _skill_layers(cfg: Config, skill_ref: str, *, slug: str) -> list[PromptLayer]:
    sp = _resolve_skill(cfg, skill_ref)
    if sp is None:
        raise ComposeError(_missing_skill_message(cfg, skill_ref, slug))
    return [PromptLayer(
        "top_level_skill",
        f"Skill: {skill_ref}",
        _prompt_text(sp.read_text(encoding="utf-8"), drop_title=True),
        ref=skill_ref,
        path=str(sp),
    )]


def _step_layers(cfg: Config, ticket: Ticket, *, slug: str) -> list[PromptLayer]:
    current = ticket.current_step()
    if not current:
        return []

    name = current["name"]
    skill_refs = list(current.get("skills") or [])

    if skill_refs:
        out: list[PromptLayer] = []
        for skill_ref in skill_refs:
            sp = _resolve_skill(cfg, skill_ref)
            if sp is None:
                raise ComposeError(_missing_skill_message(cfg, skill_ref, slug))
            out.append(PromptLayer(
                "workflow_skill",
                f"Current step: {name} (skill: {skill_ref})",
                _prompt_text(sp.read_text(encoding="utf-8"), drop_title=True),
                ref=skill_ref,
                path=str(sp),
            ))
        return out

    # Inline: load workflow, pull the matching heading
    wf_name = (ticket.workflow or {}).get("name")
    if not wf_name:
        return []
    wp = workflow_path(cfg, wf_name)
    try:
        wp = resolve_workflow_path(cfg, wf_name)
        wf = Workflow.load(wp)
    except WorkflowNotFoundError:  # a definition deleted after ticket creation
        return [PromptLayer(
            "workflow_inline",
            f"Current step: {name}",
            "*Workflow definition not found; using frozen snapshot only.*",
            ref=wf_name,
            path=str(wp),
        )]
    except (WorkflowError, OSError, UnicodeError) as exc:
        raise ComposeError(
            f"Task {slug!r}: cannot load workflow {wf_name!r} at {wp}: {exc}"
        ) from exc
    inline = wf.instructions_for(name)
    if inline:
        return [PromptLayer(
            "workflow_inline",
            f"Current step: {name}",
            _prompt_text(inline, drop_title=False, frontmatter=False),
            ref=wf_name,
            path=str(wp),
        )]
    return [PromptLayer(
        "workflow_inline",
        f"Current step: {name}",
        "*No instructions attached to this step.*",
        ref=wf_name,
        path=str(wp),
    )]


def _checked_context_paths(cfg: Config, ref: str) -> str:
    return ", ".join(str(path) for path in context_resolution_paths(cfg, ref))


def _resolve_skill(cfg: Config, skill_ref: str) -> Path | None:
    """Resolve a skill, reporting an invalid local override as unresolved."""
    try:
        return resolve_skill_path(cfg, skill_ref)
    except LocalOverrideError:
        return None


def _missing_skill_message(cfg: Config, skill_ref: str, slug: str) -> str:
    message = missing_skill_message(cfg, skill_ref, source=f"Task {slug!r}")
    if skill_ref == "coga/megalaunch/run":
        return message
    return (
        f"{message} Create one of those files or remove {skill_ref!r} from "
        "the workflow step / ticket `skills:` list."
    )


__all__ = [
    "ComposeError",
    "LaunchContext",
    "SESSION_CONDUCT_RESOURCES",
    "PromptComposition",
    "PromptLayer",
    "ResolvedPromptLayers",
    "compose_prompt",
    "compose_prompt_report",
    "estimate_tokens",
    "resolve_prompt_layers",
    "write_prompt_file",
]
