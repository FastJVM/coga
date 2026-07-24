"""``coga run`` — invoke one fixed deterministic recipe."""

from __future__ import annotations

import typer

from coga.config import ConfigError, load_config
from coga.runner import UnknownRecipeError, run_recipe


def run(
    ctx: typer.Context,
    recipe: str = typer.Argument(
        ...,
        metavar="RECIPE",
        help="Registered recipe name.",
    ),
) -> None:
    """Run a registered recipe, forwarding every trailing argument unchanged."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    try:
        code = run_recipe(cfg, recipe, list(ctx.args))
    except UnknownRecipeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    if code:
        raise typer.Exit(code)
