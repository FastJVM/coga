"""`coga init` — create a new coga repo.

`coga init` writes everything from scratch into `<path>/coga/` and refuses to
overwrite if it already exists. Templates come from the installed coga package.
It builds the self-contained venv that backs the `coga` console script.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import typer

from coga.agent_skills import refresh_agent_skill_view
from coga.commands.update import (
    _refresh_coga_gitignore,
    clone_upstream,
    copy_fresh_templates,
    ensure_host_gitignore,
    install_venv,
    is_git_repo,
    nearest_existing_dir,
    packaged_template_root,
    refresh_cli,
    resolve_coga_repo_url,
    upstream_sha,
    write_bin_wrapper,
    write_pin,
)
from coga.dependencies import DEPENDENCIES
from coga.managed_skills import (
    ManagedSkillError,
    ManagedSkillSummary,
    install_managed_skills,
)
from coga.skill_manager import GH_SKILL_REQUIRED, SkillResult


LOCAL_TOML_TEMPLATE = """\
# Machine-local config — gitignored. Holds your assignee name and any
# machine-local overrides. Override anything from coga.toml here without
# committing it.
user = ""

# Secrets are declared inline on each ticket's `secrets:` frontmatter
# (`NAME: op://vault/item/field` or `NAME: env:VAR`) — there is no central
# [secrets] catalog here.

# Per-agent permission-skip policy from older installs is removed. Current
# launch rejects those keys as unknown config because Coga no longer has a
# ticket-level unattended execution axis.
"""


def _clean_user_name(raw: str) -> str | None:
    """Strip `raw` and return it if it's a valid `user` value, else None.

    Valid = non-empty after stripping, no `"` or `\\` (both would break the
    `user = "..."` line in `coga.local.toml`). The single source of truth for
    what counts as a usable name, used by the `coga init --user` parameter.
    """
    name = raw.strip()
    if name and '"' not in name and "\\" not in name:
        return name
    return None


def _require_user_name(user: str | None) -> str:
    """Resolve the `--user` value for a direct `coga init`.

    `coga init` takes the operator's name as a parameter rather than prompting,
    so init stays scriptable. `--user NAME` is required and coga never guesses:
    a guessed name (git `user.name`, OS username) can disagree with the `owner`
    tokens written into tickets, so init fails loud when it is omitted rather
    than deriving one. `coga init --user NAME` is the one blessed way to set the
    name, and because init writes `user` before anything reads config it still
    works on a bare clone. An invalid `--user` value is also a hard error.
    """
    if user is None:
        typer.secho(
            "`coga init` needs your name: pass `--user NAME` (e.g. `coga init "
            "--user marc`). This is the name tickets you create are owned by "
            "and attributed to; coga does not guess it.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    name = _clean_user_name(user)
    if name is None:
        typer.secho(
            "`--user NAME` must be non-empty and contain no quotes or "
            "backslashes (they would break the `user` line in coga.local.toml).",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)
    return name


def render_local_toml(name: str) -> str:
    """`LOCAL_TOML_TEMPLATE` with the captured name substituted into `user`.

    `name` is the validated `--user` value (via `_require_user_name`), so it
    carries no `"`/`\\` and is safe to interpolate into the quoted TOML value.
    """
    return LOCAL_TOML_TEMPLATE.replace('user = ""', f'user = "{name}"', 1)


# Files/dirs that don't count as pre-existing user content when deciding
# whether a target dir is "empty" — `.git`/`.DS_Store` plus everything init
# itself creates. Anything else present before init runs marks the repo as
# already-filled (a real project), which suppresses onboarding-ticket seeding.
_INIT_IGNORE: frozenset[str] = frozenset(
    {".git", ".DS_Store", "coga", "CLAUDE.md", "AGENTS.md", ".claude", ".codex", ".gitignore"}
)


def _repo_is_empty(target: Path) -> bool:
    """True when `target` holds no pre-existing user content.

    Evaluated against the directory's pristine contents — call it before init
    writes any of its own files. A missing dir is empty; otherwise any entry
    outside `_INIT_IGNORE` means the repo is already a real project.
    """
    if not target.exists():
        return True
    return all(entry.name in _INIT_IGNORE for entry in target.iterdir())


def _enclosing_coga_root(target: Path) -> Path | None:
    """Nearest dir at/above `target` that holds a `coga.toml`, or None.

    Guards `coga init` against scaffolding a `coga/` inside an existing coga
    OS tree — `find_repo_root` walks up, so the enclosing repo would claim the
    new one's subtree and the layout can't work sanely. Mirrors that discovery:
    at each candidate check both a direct `coga.toml` and a sibling `coga/`
    subdir (the common layout — a git repo whose coga lives at `<repo>/coga/`),
    since `find_repo_root` resolves the target through either. The first `.git`
    boundary stops the walk: an outer coga repo beyond the host repo's boundary
    is a different project and no conflict.
    """
    for candidate in [target, *target.parents]:
        if (candidate / "coga.toml").is_file():
            return candidate
        nested = candidate / "coga"
        if (nested / "coga.toml").is_file():
            return nested
        if (candidate / ".git").exists():
            return None
    return None


def _host_ignores_coga(target: Path) -> bool:
    """True when the host repo's ignore rules would exclude the coga/ dir we're
    about to create at `target`.

    `git add` refuses ignored paths, so if the host repo gitignores the target
    subtree (e.g. `coga init build/ops` where `build/` is ignored) we'd write
    coga/ to disk and then silently skip the commit — the very silent-skip the
    up-front git check exists to prevent. Detected here so `coga init` can fail
    loud before writing anything. `target` may not exist yet, so run
    `git check-ignore` from the nearest existing ancestor.
    """
    probe = nearest_existing_dir(target)
    if probe is None:
        return False
    try:
        result = subprocess.run(
            ["git", "-C", str(probe), "check-ignore", "-q", str(target / "coga")],
            capture_output=True,
        )
    except OSError:
        return False
    return result.returncode == 0


# Delivered onboarding ticket, pruned from the copied tree on a filled repo
# (a real project doesn't want the bootstrap interview seeded for it).
_ONBOARDING_TICKET_DIRS: tuple[str, ...] = ("coga-build",)


def _prune_onboarding_tickets(coga_os: Path) -> list[str]:
    """Remove the delivered onboarding ticket dir(s) from a freshly copied tree.

    Returns the names removed (for the caller's report). Used on filled repos,
    where the bootstrap interview should not be seeded.
    """
    pruned: list[str] = []
    tasks = coga_os / "tasks"
    for name in _ONBOARDING_TICKET_DIRS:
        # A delivered onboarding task may be file-form (`tasks/<name>.md`) or
        # directory-form (`tasks/<name>/`).
        ticket_dir = tasks / name
        ticket_file = tasks / f"{name}.md"
        if ticket_dir.is_dir():
            shutil.rmtree(ticket_dir)
            pruned.append(name)
        elif ticket_file.is_file():
            ticket_file.unlink()
            pruned.append(name)
    return pruned


# Matches an owner/human/assignee line whose value is exactly the `new-user`
# placeholder. Deliberately does NOT match `replace-with-human-name` (the
# `_template`/recurring token, owned by `create_task`/recurring) — only the
# placeholder that would otherwise ship as a live value.
_NEW_USER_LINE = re.compile(r"^(owner|human|assignee):[ \t]*new-user[ \t]*$", re.M)


def _stamp_user_into_delivered_tickets(coga_os: Path, name: str) -> list[str]:
    """Replace the `new-user` placeholder with `name` in every delivered ticket.

    Rewrites `owner:`/`human:`/`assignee:` lines that read `new-user` across
    every delivered task ticket — both file-form `tasks/<slug>.md` and
    directory-form `tasks/**/ticket.md` — so the placeholder never ships as a
    live owner. Returns the slugs that were stamped.
    """
    stamped: list[str] = []
    tasks = coga_os / "tasks"
    if not tasks.is_dir():
        return stamped
    # `**/*.md` covers both shapes: a file-form `<slug>.md` and a directory-form
    # `<dir>/ticket.md` (both end in `.md`).
    for ticket in sorted(tasks.glob("**/*.md")):
        text = ticket.read_text()
        new_text, count = _NEW_USER_LINE.subn(rf"\1: {name}", text)
        if count:
            ticket.write_text(new_text)
            stamped.append(
                ticket.parent.name if ticket.name == "ticket.md" else ticket.stem
            )
    return stamped


# Orientation file dropped at the host repo root for agent CLIs that look for
# it there (Claude Code reads CLAUDE.md, Codex reads AGENTS.md, and recent
# Claude Code also picks up AGENTS.md). Identical content in both — three
# similar lines beats a clever symlink that breaks on Windows. Created only
# when missing; a user's hand-edited guide is never overwritten.
AGENT_GUIDE_TEMPLATE = """\
# Agent guide

This repo uses [coga](https://github.com/FastJVM/coga) to coordinate shared
task and context state between humans and agents. Everything coordinated lives
under `coga/`.

## Start here

Run `coga launch bootstrap/orient` to drop into a coga-aware session — the
canonical contexts get composed into the prompt automatically. For ticket-bound
work, prefer `coga launch <slug>` so the ticket's own contexts and current
workflow step are loaded too.

## Common commands

- `coga status` — triage view of all tasks
- `coga ticket "<title>"` — guided task authoring
- `coga create "<title>"` — raw draft create
- `coga dream` — run the Coga cleanup pass now
- `coga mark active <slug>` — activate a draft without launching it (launch activates inline on its own)
- `coga launch <slug>` — start or resume a task (any unique prefix works)
- `coga show <slug>` — read a task's ticket / blackboard / log
- `coga bump <slug>` — advance one workflow step
- `coga mark done <slug>` — finish active or in-progress work
- `coga block --task <slug> --reason "..."` — stop for a concrete answer
- `coga unblock <slug> --answer "..."` — record the answer and resume
- `coga --help` — full CLI surface

## Mental model

The canonical contexts are package-backed and composed automatically; a repo can
override them with local files under `coga/contexts/coga/`. Read in order:

- `principles/SKILL.md` — non-negotiables (markdown-first, fail-loud, classical mode)
- `architecture/SKILL.md` — primitives, planes, prompt composition, locking
- `cli/SKILL.md` — full command reference

These are the exact context refs composed into every launched ticket; if they
disagree with anything else in the repo, they win.

## Don't

- Don't hand-edit `status` / `step` / `workflow` in ticket frontmatter — the
  CLI manages them. Use `coga bump` / `coga block` instead.
- Don't write to the repo-global `coga/log.md` — also CLI-managed.
  Working notes go in the blackboard region of `ticket.md`.
- Don't commit secrets. Use `coga.local.toml` (gitignored) for machine-local
  values, and `env:VAR_NAME` references in `coga.toml` for shared ones.
"""


def _check_external_dependencies() -> None:
    """Fail loud if an external CLI coga *requires at init* is not on PATH.

    Enforces only the `required_at_init` dependencies in the `coga.dependencies`
    manifest — just `git` — at the start of every `coga init` invocation
    (fresh, update, update-all). `gh` and `op` are deliberately not enforced
    here: each is enforced at its point of need (`gh` by managed-skill
    installs, the open-pr step, and the autoclose sweep; `op` by a launch
    that resolves an `op://` secret), and each failure there is loud with its
    own install hint — so a missing `gh`/`op` never blocks init on a machine
    that doesn't use those features. The per-tool rationale lives on each
    manifest entry. Missing tools are reported together, each with an install
    hint.
    """
    missing = [
        dep
        for dep in DEPENDENCIES
        if dep.required_at_init and shutil.which(dep.name) is None
    ]
    if not missing:
        return
    lines = [
        "coga needs these external command-line tools, but they are not on "
        "PATH:",
        *(f"  - {dep.name}: install from {dep.install}" for dep in missing),
        "Install the missing tool(s), then re-run `coga init`.",
    ]
    typer.secho("\n".join(lines), fg=typer.colors.RED, err=True)
    sys.exit(2)


def init(
    path: Path | None = typer.Argument(
        None,
        help=(
            "Target dir for coga/ (created if missing) — a git repo root or "
            "any subdir inside one (e.g. `coga init tools/ops` in a monorepo). "
            "Defaults to the current dir."
        ),
    ),
    user: str | None = typer.Option(
        None,
        "--user",
        help=(
            "Your name — becomes `user` in coga.local.toml, the name tickets "
            "and agents refer to you by (e.g. marc)."
        ),
    ),
) -> None:
    """Create `coga/` from package templates."""
    _check_external_dependencies()
    _do_init(path or Path("."), user=user)


def _do_init(path: Path, *, user: str | None = None) -> None:
    target = path.resolve()
    coga_os = target / "coga"

    if coga_os.exists():
        typer.secho(
            f"{coga_os} already exists.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    # A coga/ nested inside an existing coga OS tree can't work — discovery
    # walks up and the enclosing repo claims the subtree. Fail loud before
    # anything is written.
    enclosing = _enclosing_coga_root(target)
    if enclosing is not None:
        typer.secho(
            f"{target} is inside an existing coga repo ({enclosing / 'coga.toml'}) "
            f"— a coga/ nested inside another coga/ can't work: discovery walks "
            f"up and resolves the enclosing repo.\n"
            f"Run `coga init` outside {enclosing}, or use that repo directly.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    # Require the operator's name up front (before the slow clone/venv) so
    # `current_user` is valid from the first moment after init, and a bad
    # invocation leaves nothing on disk.
    name = _require_user_name(user)

    # Coga is git-backed: `coga init` commits coga/ into the host repo.
    # If the target isn't inside a git work tree, fail loud (principle 6)
    # instead of writing coga/ and silently skipping the commit further down.
    # The target itself doesn't have to be the git root — `coga init tools/ops`
    # inside a monorepo scaffolds a nested coga/ committed into the host repo.
    # We don't run `git init` ourselves — the user does, which keeps branch
    # naming in their hands. Checked here, before any writes, so a bad
    # invocation leaves nothing behind and we fail before the slow clone/venv.
    if not is_git_repo(target):
        typer.secho(
            f"{target} is not inside a git repository — coga is git-backed and "
            f"`coga init` commits coga/ into your repo.\n"
            f"Run `git init` in {target} (or an ancestor) first, then re-run "
            f"`coga init`.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    # The host repo must actually be able to track coga/. If its ignore rules
    # exclude the target, `git add` refuses the path and the commit is silently
    # skipped — same silent-skip the git check above guards against. Fail loud
    # up front (still before any writes) so nothing is left behind.
    if _host_ignores_coga(target):
        typer.secho(
            f"{target / 'coga'} is gitignored by the host repo — coga is "
            f"git-backed and `coga init` must commit coga/ into your repo, but "
            f"git refuses to track an ignored path.\n"
            f"Remove the ignore rule covering {target}, or pick a target the "
            f"repo tracks, then re-run `coga init`.",
            fg=typer.colors.RED,
            err=True,
        )
        sys.exit(2)

    # Decide empty-vs-filled against the pristine dir, before init writes
    # anything of its own — a filled repo skips onboarding-ticket seeding.
    # A target without its own `.git` is a nested init below an established
    # host repo's root: always treat it as filled, even when the subdir itself
    # is empty — the onboarding interview is for genuinely new repos.
    nested = not (target / ".git").exists()
    is_empty = _repo_is_empty(target) and not nested

    target.mkdir(parents=True, exist_ok=True)

    # Init is atomic. The check above guarantees coga/ did not exist before
    # this run, so if any step below fails — clone, template copy, venv build, a
    # Ctrl-C, even a sys.exit — we remove the half-built coga/ and re-raise.
    # A partial init must never survive: it is the dead end where a re-run of
    # `coga init` refuses ("already exists") yet the leftover coga/ has a broken
    # venv / missing user (the re-init wedge).
    try:
        with tempfile.TemporaryDirectory(prefix="coga-init-") as tmp:
            repo_url = resolve_coga_repo_url()
            clone_dir = clone_upstream(Path(tmp) / "repo", repo_url=repo_url)
            template_root = packaged_template_root()
            copy_fresh_templates(template_root, coga_os)
            # `.gitignore` shipped verbatim by copytree; wrap it in the
            # coga-managed marker block so the fenced region stays distinct
            # from user additions.
            _refresh_coga_gitignore(template_root, coga_os)
            refresh_cli(clone_dir, coga_os)
            sha = upstream_sha(clone_dir)

        # On a filled repo, drop the onboarding ticket(s) the template ships — a
        # real project doesn't want the bootstrap interview seeded for it.
        pruned_onboarding = (
            _prune_onboarding_tickets(coga_os) if not is_empty else []
        )
        # Stamp the captured name over the `new-user` placeholder in whatever
        # tickets remain, so the placeholder never ships as a live owner.
        _stamp_user_into_delivered_tickets(coga_os, name)

        managed_skills = _install_managed_skills_or_exit(coga_os)
        install_venv(coga_os)
        write_bin_wrapper(coga_os / ".coga" / "bin")
        write_pin(coga_os, sha, repo_url=repo_url)

        local_toml = coga_os / "coga.local.toml"
        local_toml.write_text(render_local_toml(name))

        bin_dir = coga_os / ".coga" / "bin"
        shim = _try_install_shim(bin_dir / "coga")
        wired_agents, blocked_agents = _link_skills_for_agents(target, coga_os)
        host_gitignore_changed = ensure_host_gitignore(target)
        written_guides = _write_agent_guides(target)
        commit_sha = _git_commit_coga_os(
            target, coga_os, host_gitignore_changed, written_guides
        )
    except BaseException:
        # Roll back the partial coga/ this run created (only this run — a
        # pre-existing one is refused far above and never reaches here), then
        # re-raise so the original error / exit code / Ctrl-C is preserved.
        if coga_os.exists():
            shutil.rmtree(coga_os, ignore_errors=True)
            typer.secho(
                f"init failed — removed the partial {coga_os}; "
                f"fix the cause and re-run `coga init`.",
                fg=typer.colors.YELLOW,
                err=True,
            )
        raise

    typer.echo("")
    typer.echo(f"Initialized coga repo at {coga_os}")
    _print_managed_skill_summary(managed_skills)
    typer.echo(
        f'Wrote {local_toml} (machine-local config — gitignored) with user = "{name}".'
    )
    if pruned_onboarding:
        typer.echo(
            "Skipped the onboarding ticket (this dir already has a project) — "
            "create tasks with `coga ticket` when you're ready."
        )
    if sha is not None:
        typer.echo(f"Pinned to upstream {sha[:12]}.")
    if wired_agents:
        names = ", ".join(wired_agents)
        typer.echo(f"Wired skill discovery for {names} (symlinked into their skill dirs).")
    for label, path in blocked_agents:
        typer.secho(
            f"Skipped {label} skill wiring — {path} exists but isn't a directory. "
            f"Remove or convert it so skill wiring can complete.",
            fg=typer.colors.YELLOW,
        )
    if host_gitignore_changed:
        typer.echo(f"Updated {target / '.gitignore'} (coga-managed block).")
    if written_guides:
        typer.echo(
            f"Wrote {', '.join(written_guides)} (agent orientation — Claude Code / Codex)."
        )
    if commit_sha is not None:
        typer.echo(f"Committed coga/ as {commit_sha[:12]} (push when ready).")

    # Whether the user already has a working `coga` they can run as-is.
    # `shutil.which` honors the executable bit, so a stale non-executable
    # file at `~/.local/bin/coga` won't fool us.
    existing = shutil.which("coga")
    if shim is not None:
        typer.echo(f"`coga` is on your PATH via {shim}.")
    elif existing:
        typer.echo(f"`coga` is already on your PATH at {existing}.")

    steps: list[str] = []
    if shim is None and not existing:
        steps.append(
            "Add the bin dir to your PATH so `coga` runs:\n"
            f"       export PATH=\"{bin_dir}:$PATH\""
        )
    steps.append(
        f"Edit {coga_os}/coga.toml — set your agents, notification channels, "
        "and aliases."
    )
    if is_empty:
        steps.append(
            "Run `coga build` — it launches the coga-build onboarding: one "
            "question about what you want to build, then an agent-led chat that "
            "ends in a short vision you sign off on and a flat batch of starter "
            "tickets you can immediately `coga launch`."
        )
    else:
        steps.append(
            'Run `coga ticket "<title>"` to author your first task — the '
            "guided author turns a one-line title into a ready ticket."
        )
    steps.append("Run `coga --help` to see what's available.")

    typer.echo("")
    typer.echo("Next steps:")
    for i, step in enumerate(steps, 1):
        typer.echo(f"  {i}. {step}")

    _print_notification_state()


def _print_notification_state() -> None:
    """End-of-init line on notifications — optional on first run, Slack opt-in."""
    typer.echo("")
    if os.environ.get("SLACK_WEBHOOK_URL"):
        typer.secho(
            "✓ Notifications: optional on first run — Coga runs without them. "
            "$SLACK_WEBHOOK_URL is already set, so opting in is one step: add "
            'channels = ["slack"] under [notification] and '
            '[notification.slack].webhook = "env:SLACK_WEBHOOK_URL" in coga.toml.',
            fg=typer.colors.GREEN,
        )
        return
    typer.secho(
        "✓ Notifications: optional on first run — bump/slack/block/launch run\n"
        "  without them. To turn on team notifications later, select the Slack\n"
        "  channel and point it at a webhook in coga.toml:\n"
        "      [notification]\n"
        '      channels = ["slack"]\n'
        "      [notification.slack]\n"
        '      webhook = "env:SLACK_WEBHOOK_URL"\n'
        "  then export SLACK_WEBHOOK_URL. Once Slack is selected it is fail-loud.",
        fg=typer.colors.GREEN,
    )


def _install_managed_skills_or_exit(coga_os: Path) -> ManagedSkillSummary:
    try:
        return install_managed_skills(coga_os)
    except ManagedSkillError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        sys.exit(2)


def _print_managed_skill_summary(summary: ManagedSkillSummary) -> None:
    if not summary.results:
        return
    counts = summary.counts()
    rendered = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
    typer.echo(f"Managed skills: {rendered}")
    skipped_old_gh = [r for r in summary.results if r.status == "skipped-old-gh"]
    if skipped_old_gh:
        count = len(skipped_old_gh)
        noun = "skill" if count == 1 else "skills"
        typer.secho(
            f"Warning: skipped {count} optional managed {noun} — {GH_SKILL_REQUIRED}",
            fg=typer.colors.YELLOW,
            err=True,
        )
        typer.secho(
            "  Skipped: " + ", ".join(result.name for result in skipped_old_gh),
            fg=typer.colors.YELLOW,
            err=True,
        )
    _print_no_access_skill_notes(summary)
    for result in summary.results:
        if result.status != "failed":
            continue
        source = result.details.get("source")
        remediation = result.details.get("remediation")
        source_note = f" from {source}" if source else ""
        typer.secho(
            f"Warning: optional managed skill `{result.name}` failed{source_note}: "
            f"{result.message}",
            fg=typer.colors.YELLOW,
            err=True,
        )
        if remediation:
            typer.secho(f"  Remediation: {remediation}", fg=typer.colors.YELLOW, err=True)


def _print_no_access_skill_notes(summary: ManagedSkillSummary) -> None:
    """One consolidated note per unreachable source, not one warning per skill.

    A user outside the source repo's org (the default for anyone onboarding)
    would otherwise see every optional skill from that repo reported as its own
    failure. Coga is fully functional without these skills, so say that once,
    with how to get them later.
    """
    by_source: dict[str, list[SkillResult]] = {}
    for result in summary.results:
        if result.status != "skipped-no-access":
            continue
        by_source.setdefault(str(result.details.get("source")), []).append(result)
    for source, results in by_source.items():
        reason = str(results[0].details.get("reason"))
        remediation = results[0].details.get("remediation")
        count = len(results)
        plural = "s" if count != 1 else ""
        missing_gh = (
            "`gh`" in reason and "is not installed" in reason
        ) or "github cli 2.90.0+" in reason.casefold()
        if missing_gh:
            next_step = (
                "Install GitHub CLI 2.90.0+ from https://cli.github.com, "
                f"authenticate with `gh auth login`, then run e.g. `{remediation}`."
            )
        else:
            next_step = (
                f"Get access to {source} (or authenticate with `gh auth login`), "
                f"then run e.g. `{remediation}`."
            )
        typer.secho(
            f"Note: skipped {count} optional managed skill{plural} from {source} — "
            f"that repo isn't accessible with your GitHub credentials ({reason}). "
            f"Coga works without them. To install later, {next_step}",
            fg=typer.colors.YELLOW,
        )



# Agents we wire skill discovery for. Each entry is the project-level dir
# that the agent's CLI scans for skills (e.g. Claude Code reads `.claude/skills/`,
# Codex reads `.codex/skills/`). We symlink `<agent>/skills/coga` ->
# `coga/.agent-skills`, a generated merged view of local skills plus
# bundled bootstrap batteries. Other agents (OpenCode etc.) need manual wiring.
_AGENT_SKILL_DIRS: tuple[tuple[str, str], ...] = (
    ("Claude Code", ".claude"),
    ("Codex", ".codex"),
)


def _link_skills_for_agents(
    target: Path, coga_os: Path
) -> tuple[list[str], list[tuple[str, Path]]]:
    """Symlink the generated Coga skill view into known agent skill paths.

    Creates `<target>/<agent-dir>/skills/coga` ->
    `<target>/coga/.agent-skills` for Claude Code and Codex. Idempotent:
    refreshes the generated view and leaves a correct link alone,
    if the agent dir is something we shouldn't touch (e.g. a non-directory
    marker file), or if the OS doesn't support symlinks.

    Returns `(wired, blocked)` where `wired` is the list of human-readable
    agent names that ended up with a working link, and `blocked` is a list
    of `(name, path)` pairs we skipped because something non-directory was
    sitting in the way.
    """
    skills_src = refresh_agent_skill_view(coga_os).view_dir

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
        link = skills_dir / "coga"
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


def _try_install_shim(wrapper: Path) -> Path | None:
    """Symlink `~/.local/bin/coga` -> wrapper if that dir is on PATH and unclaimed.

    Returns the symlink path on success, None if we skipped (dir not on PATH,
    target already exists, or symlink failed).
    """
    target_dir = Path.home() / ".local" / "bin"
    if not _on_path(target_dir):
        return None
    target = target_dir / "coga"
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


def _git_commit_coga_os(
    target: Path,
    coga_os: Path,
    include_host_gitignore: bool,
    extra_host_paths: list[str] | None = None,
) -> str | None:
    """If `target` is a git repo, stage coga/ (+ host .gitignore + extras) and commit.

    Returns the new commit SHA on success, None if we skipped (not a git repo,
    nothing to stage, or git invocation failed). Never raises. `target` may sit
    below the git root (nested init) — `git -C <target>` resolves pathspecs
    relative to `target`, and the commit lands in the host repo. The commit is
    scoped to the staged coga paths, so any unrelated changes the user already
    had staged in the host repo are left staged, not swept in.
    """
    if not is_git_repo(target):
        return None
    try:
        paths = ["coga"]
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
        # Anything actually staged *among our paths*? Scope the check (and the
        # commit below) to `paths`: a nested init runs inside a live host repo
        # where the user may already have unrelated files staged, and an
        # unscoped commit would sweep them into the "Create coga" commit.
        diff = subprocess.run(
            ["git", "-C", str(target), "diff", "--cached", "--quiet", "--", *paths],
            capture_output=True,
        )
        if diff.returncode == 0:
            return None
        subprocess.run(
            [
                "git", "-C", str(target),
                "commit", "-m", "Create coga via `coga init`", "--", *paths,
            ],
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
