"""`relay init` — scaffold a new relay repo, or refresh an existing one.

Default mode (`relay init`) writes everything from scratch into `<path>/relay-os/`
and refuses to overwrite if it already exists. `--update` mode refreshes the
vendored CLI in `.relay/` and any `_*` template scaffolds, leaving user-edited
config (`relay.toml`, `rules.md`, etc.) untouched. Both modes (re)build the
self-contained venv that backs the `relay` console script.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import typer

from relay.commands.update import (
    TEMPLATE_SUBPATH,
    _refresh_relay_gitignore,
    clone_upstream,
    ensure_host_gitignore,
    install_venv,
    prune_obsolete,
    refresh_cli,
    refresh_templates,
    upstream_sha,
    write_bin_wrapper,
    write_pin,
)
from relay.config import find_repo_root


LOCAL_TOML_TEMPLATE = """\
# Machine-local config — gitignored. Holds your assignee name and secrets.
# Override anything from relay.toml here without committing it.
user = ""

# [secrets]
# stripe_key = "env:STRIPE_SECRET_KEY"
"""


def init(
    path: Path = typer.Argument(
        Path("."),
        help=(
            "Target dir for fresh init (created if missing). "
            "Ignored under --update — refreshes the current relay-os/."
        ),
    ),
    update: bool = typer.Option(
        False,
        "--update",
        help="Refresh vendored CLI + `_*` templates in the current relay-os/. Leaves user config alone.",
    ),
) -> None:
    """Scaffold `relay-os/` from upstream, or refresh it with --update."""
    if update:
        _do_update()
    else:
        _do_init(path)


def _do_init(path: Path) -> None:
    target = path.resolve()
    relay_os = target / "relay-os"

    if relay_os.exists():
        typer.secho(
            f"{relay_os} already exists — use `relay init --update` to refresh.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    target.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="relay-init-") as tmp:
        clone_dir = clone_upstream(Path(tmp) / "repo")

        upstream_templates = clone_dir / TEMPLATE_SUBPATH
        if not upstream_templates.is_dir():
            typer.secho(
                f"Upstream layout changed — {TEMPLATE_SUBPATH} not found in clone.",
                fg=typer.colors.RED,
                err=True,
            )
            sys.exit(2)

        shutil.copytree(upstream_templates, relay_os)
        # `.gitignore` shipped verbatim by copytree; wrap it in the
        # relay-managed marker block so `init --update` later only touches
        # the fenced region and leaves user additions alone.
        _refresh_relay_gitignore(upstream_templates, relay_os)
        refresh_cli(clone_dir, relay_os)
        sha = upstream_sha(clone_dir)

    install_venv(relay_os)
    write_bin_wrapper(relay_os / ".relay" / "bin")
    write_pin(relay_os, sha)

    local_toml = relay_os / "relay.local.toml"
    local_toml.write_text(LOCAL_TOML_TEMPLATE)

    bin_dir = relay_os / ".relay" / "bin"
    shim = _try_install_shim(bin_dir / "relay")
    wired_agents, blocked_agents = _link_skills_for_agents(target, relay_os)
    host_gitignore_changed = ensure_host_gitignore(target)
    commit_sha = _git_commit_relay_os(target, relay_os, host_gitignore_changed)

    typer.echo("")
    typer.echo(f"Initialized relay repo at {relay_os}")
    typer.echo(f"Wrote {local_toml} (set `user` to your assignee name).")
    if sha is not None:
        typer.echo(f"Pinned to upstream {sha[:12]}.")
    if wired_agents:
        names = ", ".join(wired_agents)
        typer.echo(f"Wired skill discovery for {names} (symlinked into their skill dirs).")
    for label, path in blocked_agents:
        typer.secho(
            f"Skipped {label} skill wiring — {path} exists but isn't a directory. "
            f"Remove or convert it, then rerun `relay init --update`.",
            fg=typer.colors.YELLOW,
        )
    if host_gitignore_changed:
        typer.echo(f"Updated {target / '.gitignore'} (relay-managed block).")
    if commit_sha is not None:
        typer.echo(f"Committed relay-os/ as {commit_sha[:12]} (push when ready).")

    # Whether the user already has a working `relay` they can run as-is.
    # `shutil.which` honors the executable bit, so a stale non-executable
    # file at `~/.local/bin/relay` won't fool us.
    existing = shutil.which("relay")
    if shim is not None:
        typer.echo(f"`relay` is on your PATH via {shim}.")
    elif existing:
        typer.echo(f"`relay` is already on your PATH at {existing}.")

    steps: list[str] = []
    if shim is None and not existing:
        steps.append(
            "Add the bin dir to your PATH so `relay` runs:\n"
            f"       export PATH=\"{bin_dir}:$PATH\""
        )
    steps.append(f"Edit {relay_os}/relay.toml — set your agents, assignees, channels.")
    steps.append(f"Set `user` in {local_toml} to match an [assignees.x] in relay.toml.")
    steps.append("Run `relay --help` to see what's available.")

    typer.echo("")
    typer.echo("Next steps:")
    for i, step in enumerate(steps, 1):
        typer.echo(f"  {i}. {step}")

    _print_slack_state(local_toml)


def _print_slack_state(local_toml: Path) -> None:
    """End-of-init line on Slack — set ✓, unset ⚠. Doesn't gate the init."""
    typer.echo("")
    if os.environ.get("SLACK_WEBHOOK_URL"):
        typer.secho("✓ Slack: $SLACK_WEBHOOK_URL is set — relay will post.", fg=typer.colors.GREEN)
        return
    typer.secho(
        "⚠ Slack: $SLACK_WEBHOOK_URL is not set. Relay requires it for the team\n"
        "  sync point — bump/feed/panic/launch will refuse to run until you export it.\n"
        "  To opt out (solo runs, dev/test), add to "
        f"{local_toml}:\n"
        "      [slack]\n"
        "      enabled = false",
        fg=typer.colors.YELLOW,
    )


def _do_update() -> None:
    relay_os = find_repo_root()

    with tempfile.TemporaryDirectory(prefix="relay-init-update-") as tmp:
        clone_dir = clone_upstream(Path(tmp) / "repo")
        refresh_cli(clone_dir, relay_os)
        copied, pruned_templates = refresh_templates(clone_dir, relay_os)
        sha = upstream_sha(clone_dir)

    pruned = prune_obsolete(relay_os) + pruned_templates
    install_venv(relay_os)
    write_bin_wrapper(relay_os / ".relay" / "bin")
    write_pin(relay_os, sha)
    wired_agents, blocked_agents = _link_skills_for_agents(relay_os.parent, relay_os)
    host_gitignore_changed = ensure_host_gitignore(relay_os.parent)

    typer.echo("")
    typer.echo(f"Refreshed CLI at {relay_os / '.relay'}")
    if sha is not None:
        typer.echo(f"Pinned to upstream {sha[:12]}.")
    if wired_agents:
        names = ", ".join(wired_agents)
        typer.echo(f"Wired skill discovery for {names}.")
    for label, path in blocked_agents:
        typer.secho(
            f"Skipped {label} skill wiring — {path} isn't a directory. "
            f"Remove or convert it, then rerun this command.",
            fg=typer.colors.YELLOW,
        )
    if copied:
        typer.echo(f"Refreshed {len(copied)} template file(s):")
        for rel in copied:
            typer.echo(f"  {rel}")
    if pruned:
        typer.echo(f"Pruned {len(pruned)} obsolete path(s):")
        for rel in pruned:
            typer.echo(f"  {rel}")
    if host_gitignore_changed:
        typer.echo(f"Updated {relay_os.parent / '.gitignore'} (relay-managed block).")


# Agents we wire skill discovery for. Each entry is the project-level dir
# that the agent's CLI scans for skills (e.g. Claude Code reads `.claude/skills/`,
# Codex reads `.codex/skills/`). We symlink `<agent>/skills/relay` -> `relay-os/skills`
# so the existing SKILL.md standard "just works" without polluting the agent's
# own skills tree. Other agents (OpenCode etc.) need manual wiring.
_AGENT_SKILL_DIRS: tuple[tuple[str, str], ...] = (
    ("Claude Code", ".claude"),
    ("Codex", ".codex"),
)


def _link_skills_for_agents(
    target: Path, relay_os: Path
) -> tuple[list[str], list[tuple[str, Path]]]:
    """Symlink relay-os/skills into each known agent's skill discovery path.

    Creates `<target>/<agent-dir>/skills/relay` -> `<target>/relay-os/skills`
    for Claude Code and Codex. Idempotent: skips if the link already exists,
    if the agent dir is something we shouldn't touch (e.g. a non-directory
    marker file), or if the OS doesn't support symlinks.

    Returns `(wired, blocked)` where `wired` is the list of human-readable
    agent names that ended up with a working link, and `blocked` is a list
    of `(name, path)` pairs we skipped because something non-directory was
    sitting in the way.
    """
    skills_src = relay_os / "skills"
    if not skills_src.is_dir():
        return [], []

    wired: list[str] = []
    blocked: list[tuple[str, Path]] = []
    for label, dirname in _AGENT_SKILL_DIRS:
        agent_dir = target / dirname
        # Some agents leave a marker file (e.g. an empty `.codex` sentinel).
        # Don't clobber it — surface it to the caller so the human decides.
        if agent_dir.exists() and not agent_dir.is_dir():
            blocked.append((label, agent_dir))
            continue

        skills_dir = agent_dir / "skills"
        link = skills_dir / "relay"
        try:
            if link.is_symlink() or link.exists():
                wired.append(label)
                continue
            skills_dir.mkdir(parents=True, exist_ok=True)
            rel_target = Path(os.path.relpath(skills_src, skills_dir))
            link.symlink_to(rel_target, target_is_directory=True)
        except OSError:
            continue
        wired.append(label)
    return wired, blocked


def _try_install_shim(wrapper: Path) -> Path | None:
    """Symlink `~/.local/bin/relay` -> wrapper if that dir is on PATH and unclaimed.

    Returns the symlink path on success, None if we skipped (dir not on PATH,
    target already exists, or symlink failed).
    """
    target_dir = Path.home() / ".local" / "bin"
    if not _on_path(target_dir):
        return None
    target = target_dir / "relay"
    if target.exists() or target.is_symlink():
        return None
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target.symlink_to(wrapper)
    except OSError:
        return None
    return target


def _git_commit_relay_os(
    target: Path, relay_os: Path, include_host_gitignore: bool
) -> str | None:
    """If `target` is a git repo, stage relay-os/ (+ host .gitignore) and commit.

    Returns the new commit SHA on success, None if we skipped (not a git repo,
    nothing to stage, or git invocation failed). Never raises.
    """
    if not (target / ".git").exists():
        return None
    try:
        paths = ["relay-os"]
        if include_host_gitignore and (target / ".gitignore").is_file():
            paths.append(".gitignore")
        subprocess.run(
            ["git", "-C", str(target), "add", "--", *paths],
            check=True,
            capture_output=True,
            text=True,
        )
        # Anything actually staged?
        diff = subprocess.run(
            ["git", "-C", str(target), "diff", "--cached", "--quiet"],
            capture_output=True,
        )
        if diff.returncode == 0:
            return None
        subprocess.run(
            ["git", "-C", str(target), "commit", "-m", "Scaffold relay-os via `relay init`"],
            check=True,
            capture_output=True,
            text=True,
        )
        rev = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return rev.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _on_path(directory: Path) -> bool:
    resolved = directory.resolve() if directory.exists() else directory
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        try:
            if Path(entry).resolve() == resolved:
                return True
        except OSError:
            continue
    return False
