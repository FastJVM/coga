#!/usr/bin/env python3
"""Run the retro done-ticket Dream extraction skill."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from relay.config import Config, ConfigError, find_repo_root, load_config
from relay.slack import post
from relay.tasks import TaskNotFoundError, TaskRef, resolve_task
from relay.ticket import Ticket, TicketError


REQUIRED_TASK_FILES = ("ticket.md", "blackboard.md", "log.md")
MAX_EVIDENCE_ITEMS = 16
MAX_CONTEXT_ITEMS = 10
MARKER_PREFIX = "relay-retro"
MAIN_BRANCHES = {"main", "master"}


@dataclass(frozen=True)
class RetroInput:
    ref: TaskRef
    ticket: Ticket
    ticket_text: str
    blackboard_text: str
    log_text: str
    relay_root: Path
    git_root: Path
    task_rel_path: str
    source_ref: str

    @property
    def slug(self) -> str:
        return self.ref.slug

    @property
    def marker(self) -> str:
        return f"{MARKER_PREFIX}:{self.slug}"


@dataclass(frozen=True)
class EvidenceItem:
    source: str
    text: str

    def render(self) -> str:
        return f"{self.source}: {self.text}"


@dataclass(frozen=True)
class ExtractionArtifact:
    kind: str
    target: str
    content: str
    state: str


@dataclass(frozen=True)
class RetroResult:
    slug: str
    status: str
    source_ref: str
    report: str
    pr_body: str
    artifacts: list[ExtractionArtifact]
    git_result: str | None
    pr_url: str | None


def load_worker_config(cwd: Path | None) -> Config:
    if cwd is None:
        return load_config()
    return load_config(find_repo_root(cwd))


def read_retro_input(cfg: Config, task_arg: str) -> RetroInput:
    try:
        ref = resolve_task(cfg, task_arg)
    except TaskNotFoundError as exc:
        raise RuntimeError(str(exc)) from exc
    if ref.slug != task_arg:
        raise RuntimeError(
            "retro-done-ticket requires an exact task slug; "
            f"`{task_arg}` resolved to `{ref.slug}`"
        )

    missing = [name for name in REQUIRED_TASK_FILES if not (ref.path / name).is_file()]
    if missing:
        raise RuntimeError(
            f"task `{ref.slug}` is missing required retro input files: "
            + ", ".join(missing)
        )

    ticket_text = (ref.path / "ticket.md").read_text()
    try:
        ticket = Ticket.parse(ticket_text)
    except TicketError as exc:
        raise RuntimeError(f"cannot parse `{ref.slug}` ticket.md: {exc}") from exc

    git_root = find_git_root(cfg)
    task_rel_path = relative_to_git_root(ref.path, git_root)
    head = current_git_head(git_root)
    source_ref = f"{head}:{task_rel_path}/"
    return RetroInput(
        ref=ref,
        ticket=ticket,
        ticket_text=ticket_text,
        blackboard_text=(ref.path / "blackboard.md").read_text(),
        log_text=(ref.path / "log.md").read_text(),
        relay_root=cfg.repo_root,
        git_root=git_root,
        task_rel_path=task_rel_path,
        source_ref=source_ref,
    )


def find_git_root(cfg: Config) -> Path:
    start = cfg.repo_root.parent if cfg.repo_root.name == "relay-os" else cfg.repo_root
    return Path(_run_git(["rev-parse", "--show-toplevel"], cwd=start).strip())


def current_git_head(git_root: Path) -> str:
    return _run_git(["rev-parse", "--short=12", "HEAD"], cwd=git_root).strip()


def relative_to_git_root(path: Path, git_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(git_root.resolve()))
    except ValueError as exc:
        raise RuntimeError(f"path is outside git root: {path}") from exc


def extract_evidence(retro: RetroInput) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    seen: set[str] = set()
    for source, text in (
        ("ticket.md", retro.ticket.body),
        ("blackboard.md", retro.blackboard_text),
        ("log.md", retro.log_text),
    ):
        for line in candidate_lines(text):
            key = f"{source}: {line}"
            if key not in seen:
                evidence.append(EvidenceItem(source=source, text=line))
                seen.add(key)
            if len(evidence) >= MAX_EVIDENCE_ITEMS:
                return evidence
    return evidence


def candidate_lines(text: str) -> list[str]:
    markers = (
        "acceptance",
        "because",
        "blocker",
        "blocked",
        "command",
        "decision",
        "decided",
        "failed",
        "failure",
        "follow-up",
        "followup",
        "lesson",
        "must",
        "panic",
        "prefer",
        "review",
        "run ",
        "should",
        "test",
        "verified",
        "workflow",
    )
    out: list[str] = []
    for raw in text.splitlines():
        line = " ".join(raw.strip().split())
        if not line:
            continue
        normalized = line.lstrip("#-*0123456789. ").strip()
        if not normalized:
            continue
        lower = normalized.lower()
        interesting = raw.lstrip().startswith(("#", "- ")) or any(
            marker in lower for marker in markers
        )
        if not interesting:
            continue
        if len(normalized) > 240:
            normalized = normalized[:237].rstrip() + "..."
        out.append(normalized)
    return out


def context_evidence_items(evidence: list[EvidenceItem]) -> list[EvidenceItem]:
    out: list[EvidenceItem] = []
    for item in evidence:
        if is_context_worthy(item.text):
            out.append(item)
        if len(out) >= MAX_CONTEXT_ITEMS:
            break
    return out


def is_context_worthy(line: str) -> bool:
    lower = line.lower()
    routine_prefixes = (
        "branch:",
        "pr:",
        "command:",
        "generated:",
        "source task:",
        "source ref:",
        "status:",
        "result:",
        "files changed:",
        "git:",
    )
    if lower.startswith(routine_prefixes):
        return False
    routine_exact = {
        "acceptance criteria",
        "description",
        "dev",
        "implementation notes",
        "plan",
        "pr body snippet",
        "review",
        "test plan",
    }
    if lower in routine_exact:
        return False
    markers = (
        "because",
        "blocked",
        "blocker",
        "decision",
        "decided",
        "do not",
        "failed",
        "failure",
        "follow-up",
        "followup",
        "lesson",
        "must",
        "never",
        "prefer",
        "should",
        "verified",
        "warranted",
    )
    return any(marker in lower for marker in markers)


def skill_evidence_items(evidence: list[EvidenceItem]) -> list[EvidenceItem]:
    out: list[EvidenceItem] = []
    for item in evidence:
        lower = item.text.lower()
        if "skill" not in lower:
            continue
        if any(marker in lower for marker in ("repeatable", "process", "run ", "command")):
            out.append(item)
    return out[:MAX_CONTEXT_ITEMS]


def build_artifacts(retro: RetroInput, *, dry_run: bool) -> list[ExtractionArtifact]:
    evidence = extract_evidence(retro)
    artifacts: list[ExtractionArtifact] = []

    context_items = context_evidence_items(evidence)
    if context_items:
        artifacts.extend(build_context_artifacts(retro, context_items, dry_run=dry_run))

    skill_items = skill_evidence_items(evidence)
    if skill_items:
        artifacts.append(build_skill_artifact(retro, skill_items, dry_run=dry_run))

    return artifacts


def build_context_artifacts(
    retro: RetroInput,
    items: list[EvidenceItem],
    *,
    dry_run: bool,
) -> list[ExtractionArtifact]:
    contexts = retro.ticket.contexts
    if not contexts:
        target_path = retro.relay_root / "contexts" / "retro" / retro.slug / "SKILL.md"
        content = render_new_context(retro, items)
        state = write_new_file(target_path, content, retro.marker, dry_run=dry_run)
        return [
            ExtractionArtifact(
                kind="context",
                target=relative_to_git_root(target_path, retro.git_root),
                content=content,
                state=state,
            )
        ]

    artifacts: list[ExtractionArtifact] = []
    for context in contexts:
        target_path = safe_context_path(retro, context)
        content = render_context_block(retro, items)
        if target_path is None:
            target = f"relay-os/contexts/{context}/SKILL.md"
            artifacts.append(
                ExtractionArtifact(
                    kind="context",
                    target=target,
                    content=content,
                    state="skipped unsafe context path",
                )
            )
            continue
        if target_path.is_file():
            state = append_once(target_path, content, retro.marker, dry_run=dry_run)
        else:
            content = render_new_context(retro, items, name=context)
            state = write_new_file(target_path, content, retro.marker, dry_run=dry_run)
        artifacts.append(
            ExtractionArtifact(
                kind="context",
                target=relative_to_git_root(target_path, retro.git_root),
                content=content,
                state=state,
            )
        )
    return artifacts


def build_skill_artifact(
    retro: RetroInput,
    items: list[EvidenceItem],
    *,
    dry_run: bool,
) -> ExtractionArtifact:
    target_path = retro.relay_root / "skills" / "retro" / retro.slug / "SKILL.md"
    content = render_new_skill(retro, items)
    state = write_new_file(target_path, content, retro.marker, dry_run=dry_run)
    return ExtractionArtifact(
        kind="skill",
        target=relative_to_git_root(target_path, retro.git_root),
        content=content,
        state=state,
    )


def safe_context_path(retro: RetroInput, context: str) -> Path | None:
    contexts_root = (retro.relay_root / "contexts").resolve()
    target_path = (contexts_root / context / "SKILL.md").resolve()
    try:
        target_path.relative_to(contexts_root)
    except ValueError:
        return None
    return target_path


def render_context_block(retro: RetroInput, items: list[EvidenceItem]) -> str:
    title = retro.ticket.title or retro.slug
    lines = [
        f"<!-- {retro.marker} -->",
        f"## Retro: {title}",
        "",
        f"Source: `{retro.source_ref}`.",
        "",
    ]
    for item in items[:MAX_CONTEXT_ITEMS]:
        lines.append(f"- {item.text} (`{item.source}`)")
    return "\n".join(lines).rstrip() + "\n"


def render_new_context(
    retro: RetroInput,
    items: list[EvidenceItem],
    *,
    name: str | None = None,
) -> str:
    context_name = name or f"retro/{retro.slug}"
    title = retro.ticket.title or retro.slug
    description = f"Durable lessons extracted from done ticket {retro.slug}."
    lines = [
        "---",
        f"name: {context_name}",
        f"description: {description}",
        "---",
        "",
        f"# Retro: {title}",
        "",
        f"<!-- {retro.marker} -->",
        f"Source: `{retro.source_ref}`.",
        "",
    ]
    for item in items[:MAX_CONTEXT_ITEMS]:
        lines.append(f"- {item.text} (`{item.source}`)")
    return "\n".join(lines).rstrip() + "\n"


def render_new_skill(retro: RetroInput, items: list[EvidenceItem]) -> str:
    title = retro.ticket.title or retro.slug
    lines = [
        "---",
        f"name: retro/{retro.slug}",
        f"description: Process lessons extracted from done ticket {retro.slug}.",
        "---",
        "",
        f"# Retro Skill: {title}",
        "",
        f"<!-- {retro.marker} -->",
        f"Source: `{retro.source_ref}`.",
        "",
        "Use this only if the extracted notes describe a repeatable process.",
        "",
    ]
    for item in items[:MAX_CONTEXT_ITEMS]:
        lines.append(f"- {item.text} (`{item.source}`)")
    return "\n".join(lines).rstrip() + "\n"


def append_once(path: Path, content: str, marker: str, *, dry_run: bool) -> str:
    existing = path.read_text() if path.is_file() else ""
    if marker in existing:
        return "already present"
    if dry_run:
        return "would append"
    separator = "\n\n" if existing.rstrip() else ""
    path.write_text(existing.rstrip() + separator + content)
    return "written"


def write_new_file(path: Path, content: str, marker: str, *, dry_run: bool) -> str:
    if path.is_file():
        existing = path.read_text()
        if marker in existing:
            return "already present"
        return "exists, not overwritten"
    if dry_run:
        return "would create"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return "written"


def render_pr_body(retro: RetroInput, artifacts: list[ExtractionArtifact]) -> str:
    if artifacts:
        artifact_summary = [f"- `{artifact.target}` ({artifact.kind}, {artifact.state})" for artifact in artifacts]
    else:
        artifact_summary = ["- No context or skill extraction was warranted."]
    return "\n".join(
        [
            "## Summary",
            "",
            f"- Extracted durable knowledge from done ticket `{retro.slug}`.",
            "- Left the ticket directory and any task branches untouched.",
            "",
            "## Extraction Artifacts",
            "",
            *artifact_summary,
            "",
            "## Source Archive",
            "",
            f"- Source task: `{retro.slug}`",
            f"- Source ref: `{retro.source_ref}`",
            "",
            "## Test Plan",
            "",
            "- Reviewed the Dream retro extraction report.",
        ]
    )


def render_report(
    retro: RetroInput,
    *,
    generated_at: str,
    command: list[str],
    artifacts: list[ExtractionArtifact],
    evidence: list[EvidenceItem],
    pr_body: str,
    git_result: str | None = None,
    pr_url: str | None = None,
) -> str:
    lines = [
        "## Dream Worker: retro-done-ticket",
        "",
        f"Generated: {generated_at}",
        f"Command: `{shlex.join(command)}`",
        f"Source task: `{retro.slug}`",
        f"Source ref: `{retro.source_ref}`",
        f"Status: `{retro.ticket.status}`",
        "",
    ]

    if retro.ticket.status != "done":
        lines.extend(
            [
                f"Result: no-op. Target status is `{retro.ticket.status}`, not `done`.",
                "Files changed: none.",
            ]
        )
        return "\n".join(lines) + "\n"

    if artifacts:
        lines.append(f"Result: extracted {len(artifacts)} artifact(s).")
    else:
        lines.append("Result: no context or skill extraction warranted.")
    if git_result:
        lines.append(f"Git: {git_result}")
    if pr_url:
        lines.append(f"PR: {pr_url}")
    lines.append("")

    lines.append("### Extraction Artifacts")
    lines.append("")
    if artifacts:
        for artifact in artifacts:
            lines.append(f"#### {artifact.target}")
            lines.append("")
            lines.append(f"Kind: {artifact.kind}")
            lines.append(f"State: {artifact.state}")
            lines.append("")
            lines.append("```markdown")
            lines.append(artifact.content.rstrip())
            lines.append("```")
            lines.append("")
    else:
        lines.append("No durable context or skill block was extracted from the ticket evidence.")
        lines.append("")

    lines.append("### Evidence Read")
    lines.append("")
    lines.append(f"- `ticket.md`: {len(retro.ticket_text)} bytes")
    lines.append(f"- `blackboard.md`: {len(retro.blackboard_text)} bytes")
    lines.append(f"- `log.md`: {len(retro.log_text)} bytes")
    lines.append("")

    if evidence:
        lines.append("### Evidence Highlights")
        lines.append("")
        for item in evidence:
            lines.append(f"- {item.render()}")
        lines.append("")

    lines.append("### Explicitly Not Done")
    lines.append("")
    lines.append("- The source ticket directory is not deleted by this skill.")
    lines.append("- Task branch cleanup belongs to separate Dream branch-cleanup skills.")
    lines.append("- Skill files are generated only when process evidence explicitly warrants them.")
    lines.append("")

    lines.append("### PR Body Snippet")
    lines.append("")
    lines.append("```markdown")
    lines.append(pr_body)
    lines.append("```")
    return "\n".join(lines).rstrip() + "\n"


def run_retro(
    cfg: Config,
    *,
    task_arg: str,
    command: list[str],
    blackboard: Path | None = None,
    dry_run: bool = False,
    commit_and_push: bool = False,
    create_pr: bool = False,
    pr_base: str = "main",
    pr_title: str | None = None,
    commit_message: str | None = None,
    allow_main_push: bool = False,
) -> RetroResult:
    retro = read_retro_input(cfg, task_arg)
    if create_pr and not commit_and_push:
        raise RuntimeError("--create-pr requires --commit-and-push")
    if commit_and_push and dry_run:
        raise RuntimeError("--commit-and-push cannot be used with --dry-run")

    artifacts: list[ExtractionArtifact] = []
    git_result = None
    pr_url = None
    if retro.ticket.status == "done":
        artifacts = build_artifacts(retro, dry_run=dry_run)

    evidence = extract_evidence(retro)
    pr_body = render_pr_body(retro, artifacts)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if blackboard:
        report = render_report(
            retro,
            generated_at=generated_at,
            command=command,
            artifacts=artifacts,
            evidence=evidence,
            pr_body=pr_body,
        )
        append_report(blackboard, report)

    if commit_and_push and retro.ticket.status == "done":
        git_result = commit_and_push_changes(
            retro,
            blackboard=blackboard,
            artifacts=artifacts,
            message=commit_message or f"Dream: extract retro knowledge from {retro.slug}",
            allow_main_push=allow_main_push,
        )
        if create_pr and git_result:
            pr_url = ensure_pr(
                retro,
                title=pr_title or f"Dream retro extraction: {retro.slug}",
                body=pr_body,
                base=pr_base,
            )

    report = render_report(
        retro,
        generated_at=generated_at,
        command=command,
        artifacts=artifacts,
        evidence=evidence,
        pr_body=pr_body,
        git_result=git_result,
        pr_url=pr_url,
    )

    return RetroResult(
        slug=retro.slug,
        status=retro.ticket.status,
        source_ref=retro.source_ref,
        report=report,
        pr_body=pr_body,
        artifacts=artifacts,
        git_result=git_result,
        pr_url=pr_url,
    )


def append_report(blackboard: Path, report: str) -> None:
    if not blackboard.parent.is_dir():
        raise RuntimeError(f"Blackboard parent does not exist: {blackboard.parent}")
    existing = blackboard.read_text() if blackboard.is_file() else ""
    if not existing or existing.endswith("\n\n"):
        separator = ""
    elif existing.endswith("\n"):
        separator = "\n"
    else:
        separator = "\n\n"
    blackboard.write_text(existing + separator + report)


def preflight_commit_and_push(git_root: Path, *, allow_main_push: bool) -> None:
    branch = current_branch(git_root)
    if not branch:
        raise RuntimeError("refusing to commit retro extraction from detached HEAD")
    if branch in MAIN_BRANCHES and not allow_main_push:
        raise RuntimeError(
            "refusing to push retro extraction directly from main; "
            "create a Dream extraction branch or pass --allow-main-push"
        )
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=git_root)
    if staged.returncode not in (0, 1):
        raise RuntimeError("could not inspect staged git changes")
    if staged.returncode == 1:
        raise RuntimeError("refusing to commit with pre-existing staged changes")


def commit_and_push_changes(
    retro: RetroInput,
    *,
    blackboard: Path | None,
    artifacts: list[ExtractionArtifact],
    message: str,
    allow_main_push: bool = False,
) -> str | None:
    preflight_commit_and_push(retro.git_root, allow_main_push=allow_main_push)
    rel_paths = [artifact.target for artifact in artifacts if artifact.state == "written"]
    if blackboard is not None:
        try:
            rel_paths.append(relative_to_git_root(blackboard, retro.git_root))
        except RuntimeError:
            pass
    if not rel_paths:
        return None

    _run_git(["add", "-A", "--", *rel_paths], cwd=retro.git_root)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=retro.git_root)
    if staged.returncode == 0:
        return None
    if staged.returncode != 1:
        raise RuntimeError("could not inspect staged git changes")

    _run_git(["commit", "-m", message], cwd=retro.git_root)
    upstream = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=retro.git_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if upstream.returncode == 0:
        _run_git(["push"], cwd=retro.git_root)
    else:
        _run_git(["push", "-u", "origin", "HEAD"], cwd=retro.git_root)
    return f"committed and pushed `{current_branch(retro.git_root)}`"


def ensure_pr(retro: RetroInput, *, title: str, body: str, base: str) -> str:
    existing = subprocess.run(
        ["gh", "pr", "view", "--json", "url", "--jq", ".url"],
        cwd=retro.git_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if existing.returncode == 0 and existing.stdout.strip():
        return existing.stdout.strip()

    body_file = retro.git_root / ".git" / "relay-retro-pr-body.md"
    body_file.write_text(body)
    try:
        return _run_gh(
            [
                "pr",
                "create",
                "--base",
                base,
                "--title",
                title,
                "--body-file",
                str(body_file),
            ],
            cwd=retro.git_root,
        ).strip()
    finally:
        body_file.unlink(missing_ok=True)


def current_branch(git_root: Path) -> str:
    return _run_git(["branch", "--show-current"], cwd=git_root).strip()


def build_slack_summary(result: RetroResult) -> str:
    if result.status != "done":
        return (
            f"Dream retro-done-ticket: `{result.slug}` no-op "
            f"(status `{result.status}`)"
        )
    pr_part = f"; PR {result.pr_url}" if result.pr_url else ""
    return (
        f"Dream retro-done-ticket: `{result.slug}` extracted "
        f"{len(result.artifacts)} artifact(s){pr_part}; source `{result.source_ref}`"
    )


def post_slack_summary(cfg: Config, task_slug: str, summary: str) -> None:
    try:
        ref = resolve_task(cfg, task_slug)
    except TaskNotFoundError as exc:
        raise RuntimeError(str(exc)) from exc
    post(cfg, summary, task_path=ref.path)


def _run_git(args: list[str], *, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise RuntimeError(f"`git {shlex.join(args)}` failed: {detail}")
    return result.stdout


def _run_gh(args: list[str], *, cwd: Path) -> str:
    result = subprocess.run(
        ["gh", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise RuntimeError(f"`gh {shlex.join(args)}` failed: {detail}")
    return result.stdout


def main(argv: list[str] | None = None) -> int:
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(
        description="Run retro extraction for exactly one done Relay task."
    )
    parser.add_argument("task", help="Done task slug to extract from.")
    parser.add_argument(
        "--cwd",
        type=Path,
        help="Run from this repo directory. Defaults to the current directory.",
    )
    parser.add_argument(
        "--blackboard",
        type=Path,
        help="Append the worker result to this Dream run blackboard.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render the extraction report without writing context or skill files.",
    )
    parser.add_argument(
        "--slack-task",
        help="Post the worker summary to Slack against this task slug.",
    )
    parser.add_argument(
        "--commit-and-push",
        action="store_true",
        help="Commit extracted artifacts/report and push the current non-main branch.",
    )
    parser.add_argument(
        "--create-pr",
        action="store_true",
        help="Create or reuse a pull request for the pushed extraction branch.",
    )
    parser.add_argument(
        "--pr-base",
        default="main",
        help="Base branch for --create-pr. Defaults to main.",
    )
    parser.add_argument(
        "--pr-title",
        help="Pull request title used with --create-pr.",
    )
    parser.add_argument(
        "--allow-main-push",
        action="store_true",
        help="Allow --commit-and-push while on main/master.",
    )
    parser.add_argument(
        "--commit-message",
        help="Commit subject used with --commit-and-push.",
    )
    args = parser.parse_args(raw_args)

    command = [sys.executable, __file__, *raw_args]
    try:
        cfg = load_worker_config(args.cwd)
        result = run_retro(
            cfg,
            task_arg=args.task,
            command=command,
            blackboard=args.blackboard,
            dry_run=args.dry_run,
            commit_and_push=args.commit_and_push,
            create_pr=args.create_pr,
            pr_base=args.pr_base,
            pr_title=args.pr_title,
            commit_message=args.commit_message,
            allow_main_push=args.allow_main_push,
        )
        if args.blackboard is None:
            sys.stdout.write(result.report)
        if args.slack_task:
            post_slack_summary(cfg, args.slack_task, build_slack_summary(result))
    except (ConfigError, RuntimeError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
