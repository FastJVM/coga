"""`relay init` — scaffold a new relay repo, or refresh an existing one.

Default mode (`relay init`) writes everything from scratch into `<path>/relay-os/`
and refuses to overwrite if it already exists. Templates come from the installed
relay package; `--update` mode refreshes the vendored CLI in `.relay/` plus
package-owned template scaffolds, leaving user-edited config (`relay.toml`,
`rules.md`, etc.) untouched. Both modes (re)build the self-contained venv that
backs the `relay` console script.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import typer

from relay.agent_skills import refresh_agent_skill_view
from relay.commands.update import (
    RELAY_REPO_URL,
    _refresh_relay_gitignore,
    clone_upstream,
    copy_fresh_templates,
    ensure_host_gitignore,
    install_venv,
    is_relay_source_checkout,
    packaged_template_root,
    prune_obsolete,
    refresh_cli,
    refresh_templates,
    running_cli_location,
    upgrade_global_cli,
    upstream_sha,
    write_bin_wrapper,
    write_pin,
)
from relay.config import ConfigError, find_repo_root, load_config
from relay.retrofit import backfill_role_fields


LOCAL_TOML_TEMPLATE = """\
# Machine-local config — gitignored. Holds your assignee name and secrets.
# Override anything from relay.toml here without committing it.
user = ""

# [secrets]
# stripe_key = "env:STRIPE_SECRET_KEY"
"""


# Orientation file dropped at the host repo root for agent CLIs that look for
# it there (Claude Code reads CLAUDE.md, Codex reads AGENTS.md, and recent
# Claude Code also picks up AGENTS.md). Identical content in both — three
# similar lines beats a clever symlink that breaks on Windows. Created only
# when missing; user edits are preserved across `relay init --update`.
AGENT_GUIDE_TEMPLATE = """\
# Agent guide

This repo uses [relay](https://github.com/FastJVM/relay) to coordinate shared
task and context state between humans and agents. Everything coordinated lives
under `relay-os/`.

## Start here

Run `relay launch bootstrap/orient` to drop into a relay-aware session — the
canonical contexts get composed into the prompt automatically. For ticket-bound
work, prefer `relay launch <slug>` so the ticket's own contexts and current
workflow step are loaded too.

## Common commands

- `relay status` — triage view of all tasks
- `relay ticket "<title>"` — guided task authoring
- `relay draft "<title>"` — raw draft scaffold
- `relay dream` — run the Relay cleanup pass now
- `relay mark active <slug>` — activate a draft before launch
- `relay launch <slug>` — start or resume a task (any unique prefix works)
- `relay show <slug>` — read a task's ticket / blackboard / log
- `relay bump <slug>` — advance one workflow step
- `relay mark done <slug>` — finish active or in-progress work
- `relay panic --task <slug> --reason "..."` — escalate when blocked
- `relay --help` — full CLI surface

## Mental model

The canonical contexts live in `relay-os/contexts/relay/` — read in order:

- `principles/SKILL.md` — non-negotiables (markdown-first, fail-loud, classical mode)
- `architecture/SKILL.md` — primitives, planes, prompt composition, locking
- `cli/SKILL.md` — full command reference

These are the exact files composed into every launched ticket; if they
disagree with anything else in the repo, they win.

## Don't

- Don't hand-edit `status` / `step` / `workflow` in ticket frontmatter — the
  CLI manages them. Use `relay bump` / `relay panic` instead.
- Don't write to `log.md` — also CLI-managed.
- Don't commit secrets. Use `relay.local.toml` (gitignored) for machine-local
  values, and `env:VAR_NAME` references in `relay.toml` for shared ones.
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
        help="Refresh vendored CLI + package templates in the current relay-os/. Leaves user config alone.",
    ),
) -> None:
    """Scaffold `relay-os/` from package templates, or refresh it with --update."""
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
        template_root = packaged_template_root()
        copy_fresh_templates(template_root, relay_os)
        # `.gitignore` shipped verbatim by copytree; wrap it in the
        # relay-managed marker block so `init --update` later only touches
        # the fenced region and leaves user additions alone.
        _refresh_relay_gitignore(template_root, relay_os)
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
    hook_status, hook_blocker = _install_post_merge_hook(target, relay_os)
    host_gitignore_changed = ensure_host_gitignore(target)
    written_guides = _write_agent_guides(target)
    commit_sha = _git_commit_relay_os(
        target, relay_os, host_gitignore_changed, written_guides
    )

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
    _print_post_merge_status(hook_status, hook_blocker, target)
    if host_gitignore_changed:
        typer.echo(f"Updated {target / '.gitignore'} (relay-managed block).")
    if written_guides:
        typer.echo(
            f"Wrote {', '.join(written_guides)} (agent orientation — Claude Code / Codex)."
        )
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
    steps.append(f"Edit {relay_os}/relay.toml — set your agents, Slack, and aliases.")
    steps.append(f"Set `user` in {local_toml} to your name.")
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
        "  sync point — bump/slack/panic/launch will refuse to run until you export it.\n"
        "  To opt out (solo runs, dev/test), add to "
        f"{local_toml}:\n"
        "      [slack]\n"
        "      enabled = false",
        fg=typer.colors.YELLOW,
    )


def _do_update() -> None:
    relay_os = find_repo_root()
    source_checkout = is_relay_source_checkout(relay_os)

    with tempfile.TemporaryDirectory(prefix="relay-init-update-") as tmp:
        clone_dir = clone_upstream(Path(tmp) / "repo")
        refresh_cli(clone_dir, relay_os)
        if source_checkout:
            copied, pruned_templates = [], []
        else:
            copied, pruned_templates = refresh_templates(relay_os)
        sha = upstream_sha(clone_dir)

    if source_checkout:
        pruned = []
    else:
        pruned = prune_obsolete(relay_os) + pruned_templates
    install_venv(relay_os)
    write_bin_wrapper(relay_os / ".relay" / "bin")
    write_pin(relay_os, sha)
    wired_agents, blocked_agents = _link_skills_for_agents(relay_os.parent, relay_os)
    hook_status, hook_blocker = _install_post_merge_hook(relay_os.parent, relay_os)
    host_gitignore_changed = ensure_host_gitignore(relay_os.parent)
    written_guides = _write_agent_guides(relay_os.parent)
    retrofitted = _run_retrofits(relay_os)
    cli_kind, cli_venv = running_cli_location(relay_os)
    cli_status, cli_detail = upgrade_global_cli(cli_kind)

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
    _print_post_merge_status(hook_status, hook_blocker, relay_os.parent)
    if copied:
        typer.echo(f"Refreshed {len(copied)} template file(s):")
        for rel in copied:
            typer.echo(f"  {rel}")
    if source_checkout:
        typer.echo(
            "Skipped relay-os template refresh/prune in Relay source checkout "
            "(source files are managed by git)."
        )
    if pruned:
        typer.echo(f"Pruned {len(pruned)} obsolete path(s):")
        for rel in pruned:
            typer.echo(f"  {rel}")
    if host_gitignore_changed:
        typer.echo(f"Updated {relay_os.parent / '.gitignore'} (relay-managed block).")
    if written_guides:
        typer.echo(
            f"Wrote {', '.join(written_guides)} (agent orientation — Claude Code / Codex)."
        )
    if retrofitted:
        typer.echo(f"Backfilled canonical ticket fields on {len(retrofitted)} ticket(s):")
        for slug in retrofitted:
            typer.echo(f"  {slug}")
    _print_global_cli_status(cli_status, cli_detail, cli_venv)


def _print_global_cli_status(status: str, detail: str | None, venv: Path) -> None:
    """Surface what `--update` did (or didn't) about the running `relay` itself.

    `init --update` always refreshes the vendored copy in `.relay/`, but the
    `relay` on the user's PATH is usually a separate install (pipx is the
    macOS default; pip-editable on Linux). Silently leaving that one stale
    is the bug colleagues actually hit.
    """
    if status == "vendored":
        return
    if status == "pipx-upgraded":
        typer.secho(
            "Upgraded global `relay` (pipx).",
            fg=typer.colors.GREEN,
        )
        if detail:
            typer.echo(detail)
        return
    if status == "pipx-failed":
        typer.secho(
            "Tried to upgrade your pipx-installed `relay` but it failed:\n"
            f"{detail or '(no output)'}\n"
            "Try `pipx upgrade relay` (or `pipx reinstall relay`) by hand.",
            fg=typer.colors.YELLOW,
        )
        return
    if status == "pipx-missing":
        typer.secho(
            f"Your `relay` looks pipx-installed (venv at {venv}), but `pipx`\n"
            f"isn't on PATH so we can't upgrade it. Install pipx and run\n"
            f"`pipx upgrade relay`.",
            fg=typer.colors.YELLOW,
        )
        return
    typer.secho(
        f"Heads-up: your `relay` on PATH lives in {venv}, not the vendored\n"
        f"copy this command just refreshed. The vendored .relay/ is up-to-date,\n"
        f"but the binary you actually run isn't. Upgrade it however you\n"
        f"installed it — e.g.\n"
        f"  pipx upgrade relay\n"
        f"  cd <your relay source clone> && git pull && pip install -e .\n"
        f"  pip install --upgrade git+{RELAY_REPO_URL}",
        fg=typer.colors.YELLOW,
    )


# Agents we wire skill discovery for. Each entry is the project-level dir
# that the agent's CLI scans for skills (e.g. Claude Code reads `.claude/skills/`,
# Codex reads `.codex/skills/`). We symlink `<agent>/skills/relay` ->
# `relay-os/.agent-skills`, a generated merged view of local skills plus
# bundled bootstrap batteries. Other agents (OpenCode etc.) need manual wiring.
_AGENT_SKILL_DIRS: tuple[tuple[str, str], ...] = (
    ("Claude Code", ".claude"),
    ("Codex", ".codex"),
)


def _link_skills_for_agents(
    target: Path, relay_os: Path
) -> tuple[list[str], list[tuple[str, Path]]]:
    """Symlink the generated Relay skill view into known agent skill paths.

    Creates `<target>/<agent-dir>/skills/relay` ->
    `<target>/relay-os/.agent-skills` for Claude Code and Codex. Idempotent:
    refreshes the generated view and leaves a correct link alone,
    if the agent dir is something we shouldn't touch (e.g. a non-directory
    marker file), or if the OS doesn't support symlinks.

    Returns `(wired, blocked)` where `wired` is the list of human-readable
    agent names that ended up with a working link, and `blocked` is a list
    of `(name, path)` pairs we skipped because something non-directory was
    sitting in the way.
    """
    skills_src = refresh_agent_skill_view(relay_os).view_dir

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
            rel_target = Path(os.path.relpath(skills_src, skills_dir))
            if link.is_symlink():
                try:
                    if Path(os.readlink(link)) == rel_target:
                        wired.append(label)
                        continue
                except OSError:
                    blocked.append((label, link))
                    continue
                link.unlink()
            elif link.exists():
                blocked.append((label, link))
                continue

            skills_dir.mkdir(parents=True, exist_ok=True)
            link.symlink_to(rel_target, target_is_directory=True)
        except OSError:
            if (label, link) not in blocked:
                blocked.append((label, link))
            continue
        wired.append(label)
    return wired, blocked


def _find_git_dir(start: Path) -> Path | None:
    """Walk up from `start` looking for a `.git` directory. Worktrees
    (where `.git` is a file) and bare repos aren't supported here — the
    hook install just no-ops, and `relay status` covers the gap.
    """
    cur = start.resolve()
    for candidate in [cur, *cur.parents]:
        gd = candidate / ".git"
        if gd.is_dir():
            return gd
    return None


def _install_post_merge_hook(
    host_repo: Path, relay_os: Path
) -> tuple[str, Path | None]:
    """Symlink `<host>/.git/hooks/post-merge` → `relay-os/bootstrap/hooks/post-merge`.

    Returns `(status, blocker)`:
      - `("installed", None)` — newly created.
      - `("present", None)` — symlink already correct (idempotent re-run).
      - `("not-a-git-repo", None)` — host has no `.git/`. Nothing to do.
      - `("no-hook-template", None)` — bootstrap/hooks/post-merge missing.
      - `("blocked", path)` — something else lives at the target. We don't
        clobber user hooks.
      - `("failed", None)` — the symlink call itself failed (e.g. Windows
        without symlink permission).

    Idempotent. Never raises.
    """
    git_dir = _find_git_dir(host_repo)
    if git_dir is None:
        return ("not-a-git-repo", None)
    src = relay_os / "bootstrap" / "hooks" / "post-merge"
    if not src.is_file():
        return ("no-hook-template", None)
    # Mode bits don't always survive `shutil.copytree` cleanly across
    # filesystems, and a non-executable hook is a silent no-op. Re-chmod.
    try:
        src.chmod(0o755)
    except OSError:
        pass
    hooks_dir = git_dir / "hooks"
    try:
        hooks_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return ("failed", None)
    link = hooks_dir / "post-merge"

    if link.is_symlink():
        try:
            current = link.resolve(strict=False)
        except OSError:
            return ("blocked", link)
        if current == src.resolve():
            return ("present", None)
        return ("blocked", link)
    if link.exists():
        return ("blocked", link)

    try:
        rel_target = Path(os.path.relpath(src, hooks_dir))
        link.symlink_to(rel_target)
    except OSError:
        return ("failed", None)
    return ("installed", None)


def _run_retrofits(relay_os: Path) -> list[str]:
    """Best-effort migrations on existing tickets. Skip silently if config can't load."""
    try:
        cfg = load_config(relay_os)
    except ConfigError:
        return []
    return backfill_role_fields(cfg)


def _print_post_merge_status(
    status: str, blocker: Path | None, host_repo: Path
) -> None:
    if status == "installed":
        typer.echo(
            "Installed post-merge hook (auto-bumps tickets whose PR has merged)."
        )
    elif status == "blocked" and blocker is not None:
        typer.secho(
            f"Skipped post-merge hook — {blocker} already exists. "
            f"Remove it (or chain a `relay automerge` call into it) and rerun "
            f"`relay init --update` to enable auto-bump on PR merge.",
            fg=typer.colors.YELLOW,
        )
    elif status == "failed":
        typer.secho(
            f"Could not install post-merge hook in {host_repo / '.git' / 'hooks'} "
            f"(symlink failed). `relay status` will still catch up auto-bumps.",
            fg=typer.colors.YELLOW,
        )
    # "present", "not-a-git-repo", "no-hook-template" — silent.


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


_AGENT_GUIDE_FILES: tuple[str, ...] = ("CLAUDE.md", "AGENTS.md")


def _write_agent_guides(target: Path) -> list[str]:
    """Drop CLAUDE.md and AGENTS.md at the host repo root if either is missing.

    Both files get the same content. We never overwrite an existing one — a
    user's hand-edited orientation always wins. Returns the basenames we wrote
    so the caller can echo and stage them.
    """
    written: list[str] = []
    for name in _AGENT_GUIDE_FILES:
        path = target / name
        if path.exists():
            continue
        try:
            path.write_text(AGENT_GUIDE_TEMPLATE)
        except OSError:
            continue
        written.append(name)
    return written


def _git_commit_relay_os(
    target: Path,
    relay_os: Path,
    include_host_gitignore: bool,
    extra_host_paths: list[str] | None = None,
) -> str | None:
    """If `target` is a git repo, stage relay-os/ (+ host .gitignore + extras) and commit.

    Returns the new commit SHA on success, None if we skipped (not a git repo,
    nothing to stage, or git invocation failed). Never raises.
    """
    if not (target / ".git").exists():
        return None
    try:
        paths = ["relay-os"]
        if include_host_gitignore and (target / ".gitignore").is_file():
            paths.append(".gitignore")
        for extra in extra_host_paths or []:
            if (target / extra).is_file():
                paths.append(extra)
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
