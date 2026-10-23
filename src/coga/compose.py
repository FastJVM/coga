"""Prompt composition — the core of `coga launch`."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from coga.blackboard import (
    BLOCKER_TS_FORMAT,
    Blocker,
    blackboard_for_prompt,
    parse_blockers_text,
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
    resolve_skill_path,
    resolve_workflow_path,
    workflow_path,
)
from coga.taskfile import body_sections, split_body
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


@dataclass(frozen=True)
class CheckoutNotice:
    """What launch observed and did to the session's checkout.

    Supplied by the caller that prepared it; composition performs no Git and
    never infers a branch from a workflow or the environment. `summary` is the
    observed state and outcome, `projected` an entry-dirt path launch wrote
    (the current ticket, unstaged), `return_owner` who returns the checkout,
    and `prepare_command` the exact chat invocation, when one is available.
    """

    summary: str
    return_owner: str
    projected: str | None = None
    prepare_command: str | None = None

    def render(self) -> str:
        lines = [self.summary]
        if self.projected:
            lines.append(
                f"The only entry dirt is `{self.projected}`: control's current "
                "copy of this ticket, projected unstaged. Write your handoff "
                "there; never stage or commit it, and do not restore it from "
                "another revision. Every other path started clean."
            )
        if self.prepare_command:
            lines.append(
                "Discussion needs no branch. Before editing any file, read "
                "`coga/checkouts` and run exactly "
                f"`{self.prepare_command}`; it creates or reuses this chat's "
                "one branch and is safe to repeat."
            )
        lines.append(self.return_owner)
        lines.append(
            "The full start/work/handoff/end procedure is `coga/checkouts`."
        )
        return "\n\n".join(lines)


UNSUPPLIED_CHECKOUT_NOTICE = (
    "No checkout preparation was supplied for this prompt: nothing here claims "
    "that a branch was prepared or that this checkout will be returned. Before "
    "editing, follow `coga/checkouts` (\"Start, work, end\") yourself."
)


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
    checkout: CheckoutNotice | None = None,
) -> str:
    """Assemble the composed prompt in spec order (§compose)."""
    return compose_prompt_report(
        cfg,
        task_ref,
        ticket,
        include_blocker_preamble=include_blocker_preamble,
        launch_context=launch_context,
        checkout=checkout,
    ).prompt


def compose_prompt_report(
    cfg: Config,
    task_ref: TargetRef,
    ticket: Ticket,
    *,
    include_blocker_preamble: bool = True,
    launch_context: LaunchContext = "attended",
    checkout: CheckoutNotice | None = None,
) -> PromptComposition:
    """Assemble the prompt and keep per-layer measurement metadata.

    `launch_context` selects the one composed session-conduct layer. It
    defaults to `"attended"` so any caller that does not know it is draining a
    queue gets the ask-a-present-human contract. `checkout` is the launcher's
    observed checkout result, rendered as a runtime appendix after the ticket;
    without one the appendix says that no preparation was supplied.
    """
    layers: list[PromptLayer] = []

    # Split the single-file ticket body at the blackboard fence: the body above
    # feeds the Description / inline-Context layers, the region below is the
    # blackboard layer. Bootstrap tickets legitimately carry no fence, so they are
    # parsed leniently (blackboard is then None and the blackboard layer is
    # omitted); a normal task ticket missing the fence fails loud.
    body_above, blackboard_text = split_body(
        ticket.body, blackboard_required=not isinstance(task_ref, BootstrapRef)
    )
    if blackboard_text is not None:
        # Filter before every prompt consumer, including the blocker preamble:
        # historical blocker examples must not reappear as current asks.
        blackboard_text = blackboard_for_prompt(blackboard_text, task_ref.ticket_path)

    header = (
        f"# Coga task — {task_ref.id_slug}\n\n"
        f"Title: {ticket.title}\n"
        f"Task directory: {_task_path_for_prompt(cfg, task_ref)}"
    )
    if ticket.status:
        header += f"\nStatus: {ticket.status}"
    layers.append(PromptLayer("header", "Header", header, raw=True))

    # 1. Base prompt — neutral on conduct. It cross-references the selected
    # layer below rather than carrying a default that a later layer overrides.
    base_text, base_path = _resource(cfg, "prompt.md")
    layers.append(PromptLayer(
        "base_prompt",
        "Coga base prompt",
        base_text,
        ref="prompt.md",
        path=_override_path(base_path),
    ))

    # 1b. Ticket loop — blackboard, bump, block. Only a task ticket has that
    # lifecycle; a stateless bootstrap target finishes as its own ticket says,
    # so composing these rules there would only be contradicted by it.
    if not isinstance(task_ref, BootstrapRef):
        loop_text, loop_path = _resource(cfg, "prompt-ticket.md")
        layers.append(PromptLayer(
            "ticket_loop",
            "Ticket loop",
            loop_text,
            ref="prompt-ticket.md",
            path=_override_path(loop_path),
        ))

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
    # `raw` so the resource's own `## Session conduct — <context>` heading is
    # the section heading: the selected context stays visible to the agent
    # instead of being flattened into one generic title.
    conduct_text, conduct_path = _resource(cfg, conduct_resource)
    layers.append(PromptLayer(
        "session_conduct",
        "Session conduct",
        conduct_text,
        ref=conduct_resource,
        path=_override_path(conduct_path),
        raw=True,
    ))

    # 2b. Blocker-resolution preamble. An interactive session whose blackboard
    # still carries open asks must resolve-or-re-block before the step's real
    # work — this is how `coga launch` resumes a blocked ticket as a chat
    # (launch reactivates it inline, so by compose time `status:` is already
    # `in_progress`; the open asks are the durable signal). Keying off the
    # blackboard rather than a launch-threaded flag keeps the preamble purely
    # composed state: it reappears if a session dies mid-discussion and
    # disappears once `coga unblock` records the answer.
    if include_blocker_preamble and not isinstance(task_ref, BootstrapRef):
        open_asks = [
            b
            for b in parse_blockers_text(blackboard_text or "")
            if not b.resolved
        ]
        if open_asks:
            preamble, preamble_path = _blocker_preamble(
                cfg, task_ref.id_slug, open_asks
            )
            layers.append(PromptLayer(
                "blocker_preamble",
                "Resolve the open blocker first",
                preamble,
                ref="prompt-blocker-resolution.md",
                path=_override_path(preamble_path),
            ))

    # 3. repo context.md
    pctx = repo_context_path(cfg)
    if pctx.is_file():
        layers.append(PromptLayer(
            "repo_context",
            "Repo context",
            pctx.read_text(encoding="utf-8"),
            ref="context.md",
            path=str(pctx),
        ))

    # 4. ticket-attached contexts
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
        layers.append(PromptLayer(
            "ticket_context",
            f"Context — {ref}",
            cp.read_text(encoding="utf-8"),
            ref=ref,
            path=str(cp),
        ))

    # 5. ticket-level skills + current workflow step
    for skill_ref in ticket.skills:
        layers.extend(_skill_layers(cfg, skill_ref, slug=task_ref.id_slug))
    layers.extend(_step_layers(cfg, ticket, slug=task_ref.id_slug))

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
            desc,
            ref="ticket.md##Description",
            path=str(task_ref.ticket_path),
        ))

    inline_ctx = _extract_section(body_above, "Context")
    if inline_ctx:
        layers.append(PromptLayer(
            "task_context",
            "Task-specific context",
            inline_ctx,
            ref="ticket.md##Context",
            path=str(task_ref.ticket_path),
        ))

    if blackboard_text and blackboard_text.strip():
        layers.append(PromptLayer(
            "blackboard",
            "Blackboard (current state)",
            blackboard_text,
            ref="ticket.md##blackboard",
            path=str(task_ref.ticket_path),
        ))

    # 7. Runtime checkout notice, after the contiguous ticket and before any
    # launch arguments the caller appends. Generated, never a resource, so a
    # repo's old base-prompt override cannot misstate what launch did.
    layers.append(PromptLayer(
        "checkout_notice",
        "Checkout (runtime)",
        checkout.render() if checkout is not None else UNSUPPLIED_CHECKOUT_NOTICE,
    ))

    return PromptComposition(layers)


def write_prompt_file(prompt: str, task_ref: TargetRef, dest_dir: Path | None = None) -> Path:
    """Exclusively create a UTF-8 prompt file that survives until session cleanup."""
    safe_slug = task_ref.id_slug.replace("/", "-")
    prompt_file = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", prefix=f"coga-{safe_slug}-", suffix=".md",
        dir=dest_dir, delete=False,
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
    cfg: Config, slug: str, open_asks: list[Blocker]
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
    template, path = _resource(cfg, "prompt-blocker-resolution.md")
    rendered = template.replace("{slug}", slug).replace("{blockers}", "\n".join(lines))
    return rendered, path


def _section(title: str, body: str) -> str:
    body = body.strip()
    return f"## {title}\n\n{body}"


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
    sp = resolve_skill_path(cfg, skill_ref)
    if sp is None:
        raise ComposeError(_missing_skill_message(cfg, skill_ref, slug))
    return [PromptLayer(
        "top_level_skill",
        f"Skill: {skill_ref}",
        sp.read_text(encoding="utf-8"),
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
            sp = resolve_skill_path(cfg, skill_ref)
            if sp is None:
                raise ComposeError(_missing_skill_message(cfg, skill_ref, slug))
            out.append(PromptLayer(
                "workflow_skill",
                f"Current step: {name} (skill: {skill_ref})",
                sp.read_text(encoding="utf-8"),
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
    inline = wf.inline_instructions.get(name)
    if inline:
        return [PromptLayer(
            "workflow_inline",
            f"Current step: {name}",
            inline,
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


def _missing_skill_message(cfg: Config, skill_ref: str, slug: str) -> str:
    message = missing_skill_message(cfg, skill_ref, source=f"Task {slug!r}")
    if skill_ref == "coga/megalaunch/run":
        return message
    return (
        f"{message} Create one of those files or remove {skill_ref!r} from "
        "the workflow step / ticket `skills:` list."
    )


__all__ = [
    "CheckoutNotice",
    "ComposeError",
    "LaunchContext",
    "SESSION_CONDUCT_RESOURCES",
    "PromptComposition",
    "PromptLayer",
    "compose_prompt",
    "compose_prompt_report",
    "estimate_tokens",
    "write_prompt_file",
]
