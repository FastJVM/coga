"""Tier-2 shim around-hook (`relay/extension-model`, Pass 2).

A `[shims.<name>]` entry is the single fixed shape `arg -> create-draft ->
launch`. `cli.main()` routes a shim-named command here instead of through
Typer, so the command's logic lives as config + a markdown launch target
rather than bespoke Python.

`run_shim` is the *around*-hook: it does work *before* the launch (resolve the
arg, create a draft if the shim says so) and *after* it (validate, sync) — the
"after" is why this can't be a plain alias that just rewrites argv and lets
Typer's `app()` (which exits) run the launch.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import typer

from relay import git
from relay.commands.create import create_draft
from relay.config import Config, Shim
from relay.tasks import TaskNotFoundError, TaskRef, resolve_task
from relay.validate import format_task_issues, validate_task_dir


@dataclass(frozen=True)
class ShimResolution:
    """What a shim's positional arg resolved to, before launch."""

    target: str  # the string handed to `launch` (a task id-slug or a bootstrap ref)
    kind: str  # "bare" | "existing" | "new"
    task_ref: TaskRef | None  # the real task for new/existing; None for bare


def resolve_shim_target(cfg: Config, shim: Shim, arg: str | None) -> ShimResolution:
    """Resolve a shim's positional arg into a launch target.

    - no arg        -> **bare**:     launch the shim's `launch` target (a shim).
    - existing slug -> **existing**:  launch that task.
    - unknown arg   -> **new**:       create a draft from it (if `draft_if_missing`),
                                      then launch that draft.

    The deterministic shape is exactly the kernel boundary in action: this
    function decides *which* draft/target, but the actual ticket-creation is the
    kernel `create` primitive and the spawn is the kernel `launch`.
    """
    if arg is None:
        return ShimResolution(target=shim.launch, kind="bare", task_ref=None)

    try:
        ref = resolve_task(cfg, arg)
    except TaskNotFoundError as exc:
        # An ambiguous prefix is a real error, not a "create a new one" signal.
        if str(exc).startswith("Ambiguous task ref"):
            raise
        if not shim.draft_if_missing:
            raise TaskNotFoundError(
                f"{arg!r} is not an existing task and shim {shim.name!r} does not "
                "create drafts (draft_if_missing = false)."
            )
        result = create_draft(title=arg, mode="interactive")
        new_ref = TaskRef(slug=str(result["slug"]), path=result["path"])
        return ShimResolution(target=new_ref.id_slug, kind="new", task_ref=new_ref)

    return ShimResolution(target=ref.id_slug, kind="existing", task_ref=ref)


def run_shim(cfg: Config, shim: Shim, args: list[str]) -> int:
    """The around-hook: resolve -> (draft) -> launch -> validate -> sync.

    Returns a process exit code.
    """
    if shim.require_tty and not _has_tty():
        typer.secho(
            f"`relay {shim.name}` needs an interactive terminal (require_tty).",
            fg=typer.colors.RED,
            err=True,
        )
        return 2

    try:
        res = resolve_shim_target(cfg, shim, _positional(args))
    except TaskNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        return 2

    typer.echo(f"Shim {shim.name}: {res.kind} -> launching {res.target}")

    # Lazy import mirrors `commands/retire.py` — avoids importing the heavy
    # launch module (and a potential cycle through cli) until dispatch time.
    from relay.commands.launch import launch

    launch(
        res.target,
        agent_override=None,
        prompt_report=False,
        mode_override=None,
        idle_timeout=None,
        max_session=None,
        return_timeout=False,
    )

    # The "after": only real tasks (new/existing) have files to check/commit;
    # a bare launch targets a stateless shim, so there is nothing to validate.
    if res.task_ref is not None:
        if shim.validate_after:
            errors = [
                i for i in validate_task_dir(cfg, res.task_ref) if i.severity == "error"
            ]
            if errors:
                typer.secho(
                    f"Shim {shim.name}: validation failed for "
                    f"{res.task_ref.id_slug}:\n" + format_task_issues(errors),
                    fg=typer.colors.RED,
                    err=True,
                )
                return 2
        if shim.sync:
            git.sync_paths(
                cfg,
                res.task_ref.path,
                [res.task_ref.path],
                message=f"Shim {shim.name}: {res.task_ref.id_slug}",
            )

    return 0


def _positional(args: list[str]) -> str | None:
    """First non-flag token, or None.

    First cut: flags (e.g. `--agent`) are not yet forwarded to `launch`; the
    positional arg is the bare/new/existing discriminator the shim shape needs.
    """
    for a in args:
        if not a.startswith("-"):
            return a
    return None


def _has_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()
