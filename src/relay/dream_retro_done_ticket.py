"""Retro done-ticket Dream worker.

The worker consumes exactly one Relay task. If the task is done, it summarizes
the durable knowledge candidates from `ticket.md`, `blackboard.md`, and
`log.md`, then can delete the task directory for a reviewable cleanup PR.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
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
MAX_EVIDENCE_ITEMS = 12


@dataclass(frozen=True)
class RetroInput:
    ref: TaskRef
    ticket: Ticket
    ticket_text: str
    blackboard_text: str
    log_text: str
    git_root: Path
    task_rel_path: str
    source_ref: str

    @property
    def slug(self) -> str:
        return self.ref.slug


@dataclass(frozen=True)
class KnowledgeProposal:
    kind: str
    target: str
    reason: str


@dataclass(frozen=True)
class RetroResult:
    slug: str
    status: str
    source_ref: str
    report: str
    pr_body: str
    deleted: bool
    proposals: list[KnowledgeProposal]


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


def build_knowledge_proposals(retro: RetroInput) -> list[KnowledgeProposal]:
    proposals: list[KnowledgeProposal] = []

    contexts = retro.ticket.contexts
    if contexts:
        for context in contexts:
            proposals.append(
                KnowledgeProposal(
                    kind="context",
                    target=f"relay-os/contexts/{context}/SKILL.md",
                    reason=(
                        "Ticket loaded this context; review the evidence highlights "
                        "for facts or conventions that should outlive the task."
                    ),
                )
            )
    else:
        proposals.append(
            KnowledgeProposal(
                kind="context",
                target="relay-os/contexts/<domain>/<name>/SKILL.md",
                reason=(
                    "Ticket had no context refs. If the evidence repeats in future "
                    "work, lift it into a focused context instead of preserving the task."
                ),
            )
        )

    skills = workflow_skills(retro.ticket)
    if skills:
        for skill in skills:
            proposals.append(
                KnowledgeProposal(
                    kind="skill",
                    target=f"relay-os/skills/{skill}/SKILL.md",
                    reason=(
                        "Ticket used this skill; review the evidence for process "
                        "instructions, gotchas, or verification steps the next worker "
                        "should inherit."
                    ),
                )
            )
    else:
        proposals.append(
            KnowledgeProposal(
                kind="skill",
                target="relay-os/skills/<domain>/<name>/SKILL.md",
                reason=(
                    "No step skill was attached. If the task invented a repeatable "
                    "process, capture it as a skill before relying on git history."
                ),
            )
        )

    workflow = workflow_name(retro.ticket)
    if workflow:
        proposals.append(
            KnowledgeProposal(
                kind="workflow",
                target=f"relay-os/workflows/{workflow}.md",
                reason=(
                    "Ticket used this workflow; compare the log/blackboard against "
                    "the frozen steps and adjust only if the workflow repeatedly "
                    "misroutes work."
                ),
            )
        )
    else:
        proposals.append(
            KnowledgeProposal(
                kind="workflow",
                target="relay-os/workflows/<domain>/<name>.md",
                reason=(
                    "Ticket had no workflow. If the same ad-hoc sequence appears "
                    "again, propose a workflow rather than preserving one-off task state."
                ),
            )
        )

    return proposals


def workflow_name(ticket: Ticket) -> str | None:
    workflow = ticket.workflow
    if isinstance(workflow, dict):
        value = workflow.get("name")
        return str(value) if value else None
    if isinstance(workflow, str):
        return workflow
    return None


def workflow_skills(ticket: Ticket) -> list[str]:
    out: list[str] = []
    if ticket.skill:
        out.append(ticket.skill)
    workflow = ticket.workflow
    if isinstance(workflow, dict):
        for step in workflow.get("steps", []):
            if not isinstance(step, dict):
                continue
            skill = step.get("skill")
            if skill:
                out.append(str(skill))
    return sorted(set(out))


def extract_evidence(retro: RetroInput) -> list[str]:
    evidence: list[str] = []
    for source, text in (
        ("ticket.md", retro.ticket.body),
        ("blackboard.md", retro.blackboard_text),
        ("log.md", retro.log_text),
    ):
        for line in candidate_lines(text):
            item = f"{source}: {line}"
            if item not in evidence:
                evidence.append(item)
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
        "pr ",
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
        if len(normalized) > 220:
            normalized = normalized[:217].rstrip() + "..."
        out.append(normalized)
    return out


def render_pr_body(retro: RetroInput, proposals: list[KnowledgeProposal]) -> str:
    kinds = sorted({proposal.kind for proposal in proposals})
    return "\n".join(
        [
            "## Summary",
            "",
            f"- Retro extracted durable knowledge candidates from `{retro.slug}`.",
            f"- Deleted `relay-os/tasks/{retro.slug}/` after reviewable extraction.",
            f"- Proposed update kinds: {', '.join(kinds)}.",
            "",
            "## Source Archive",
            "",
            f"- Source task: `{retro.slug}`",
            f"- Source ref: `{retro.source_ref}`",
            "- The deletion diff in this PR also contains the removed task files.",
            "",
            "## Test Plan",
            "",
            "- Reviewed the Dream retro summary on the Dream run blackboard.",
        ]
    )


def render_report(
    retro: RetroInput,
    *,
    generated_at: str,
    command: list[str],
    apply: bool,
    deleted: bool,
    proposals: list[KnowledgeProposal],
    evidence: list[str],
    pr_body: str,
    git_result: str | None = None,
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

    action = "deleted" if deleted else "planned"
    lines.extend(
        [
            f"Result: {action} `{retro.task_rel_path}/`.",
            f"Apply mode: {'yes' if apply else 'no'}",
        ]
    )
    if git_result:
        lines.append(f"Git: {git_result}")
    lines.append("")

    lines.append("### Proposed Knowledge Updates")
    lines.append("")
    for proposal in proposals:
        lines.append(f"- **{proposal.kind}** `{proposal.target}`")
        lines.append(f"  Reason: {proposal.reason}")
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
            lines.append(f"- {item}")
        lines.append("")

    lines.append("### Intentionally Dropped")
    lines.append("")
    lines.append(
        "- Routine lifecycle noise stays in git history and the PR deletion diff; "
        "only durable lessons should move into contexts, skills, or workflows."
    )
    lines.append(
        "- One-off implementation details stay archived unless the review identifies "
        "a reusable convention."
    )
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
    apply: bool,
    command: list[str],
    blackboard: Path | None = None,
    commit_and_push: bool = False,
    allow_main_push: bool = False,
    commit_message: str | None = None,
) -> RetroResult:
    retro = read_retro_input(cfg, task_arg)
    if commit_and_push and not apply:
        raise RuntimeError("--commit-and-push requires --apply")
    if commit_and_push and retro.ticket.status == "done":
        preflight_commit_and_push(retro.git_root, allow_main_push=allow_main_push)

    deleted = False
    git_result = None
    proposals = build_knowledge_proposals(retro)
    evidence = extract_evidence(retro)
    pr_body = render_pr_body(retro, proposals)

    if retro.ticket.status == "done" and apply:
        ensure_report_survives_deletion(blackboard, retro.ref.path)
        ensure_task_clean(retro)
        shutil.rmtree(retro.ref.path)
        deleted = True

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report = render_report(
        retro,
        generated_at=generated_at,
        command=command,
        apply=apply,
        deleted=deleted,
        proposals=proposals,
        evidence=evidence,
        pr_body=pr_body,
    )

    if blackboard:
        append_report(blackboard, report)

    if commit_and_push and retro.ticket.status == "done":
        git_result = commit_and_push_changes(
            retro,
            blackboard=blackboard,
            message=commit_message or f"Dream: retro done ticket {retro.slug}",
            allow_main_push=allow_main_push,
        )
        if git_result:
            report = render_report(
                retro,
                generated_at=generated_at,
                command=command,
                apply=apply,
                deleted=deleted,
                proposals=proposals,
                evidence=evidence,
                pr_body=pr_body,
                git_result=git_result,
            )

    return RetroResult(
        slug=retro.slug,
        status=retro.ticket.status,
        source_ref=retro.source_ref,
        report=report,
        pr_body=pr_body,
        deleted=deleted,
        proposals=proposals,
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


def ensure_report_survives_deletion(blackboard: Path | None, task_path: Path) -> None:
    if blackboard is None:
        return
    try:
        blackboard.resolve().relative_to(task_path.resolve())
    except ValueError:
        return
    raise RuntimeError(
        "refusing to write the retro report inside the task directory being deleted"
    )


def ensure_task_clean(retro: RetroInput) -> None:
    status = _run_git(
        ["status", "--porcelain", "--", retro.task_rel_path],
        cwd=retro.git_root,
    ).strip()
    if status:
        raise RuntimeError(
            f"refusing to delete `{retro.task_rel_path}` with uncommitted changes:\n"
            f"{status}"
        )


def preflight_commit_and_push(git_root: Path, *, allow_main_push: bool) -> None:
    branch = current_branch(git_root)
    if not branch:
        raise RuntimeError("refusing to commit retro cleanup from detached HEAD")
    if branch in {"main", "master"} and not allow_main_push:
        raise RuntimeError(
            "refusing to push retro cleanup directly from main; "
            "create a Dream cleanup branch or pass --allow-main-push"
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
    message: str,
    allow_main_push: bool = False,
) -> str | None:
    preflight_commit_and_push(retro.git_root, allow_main_push=allow_main_push)
    rel_paths = [retro.task_rel_path]
    if blackboard is not None:
        try:
            rel_paths.append(relative_to_git_root(blackboard, retro.git_root))
        except RuntimeError:
            pass

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


def current_branch(git_root: Path) -> str:
    return _run_git(["branch", "--show-current"], cwd=git_root).strip()


def build_slack_summary(result: RetroResult) -> str:
    if result.status != "done":
        return (
            f"Dream retro-done-ticket: `{result.slug}` no-op "
            f"(status `{result.status}`)"
        )
    action = "deleted" if result.deleted else "planned"
    return (
        f"Dream retro-done-ticket: `{result.slug}` {action}; "
        f"{len(result.proposals)} proposal(s); source `{result.source_ref}`"
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


def main(argv: list[str] | None = None) -> int:
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(
        description="Run the retro done-ticket Dream worker on exactly one task."
    )
    parser.add_argument("task", help="Done task slug to retro.")
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
        "--apply",
        action="store_true",
        help="Delete the done task directory after writing the retro summary.",
    )
    parser.add_argument(
        "--slack-task",
        help="Post the worker summary to Slack against this task slug.",
    )
    parser.add_argument(
        "--commit-and-push",
        action="store_true",
        help="Commit the deletion/report and push the current non-main branch.",
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

    command = [sys.executable, "-m", "relay.dream_retro_done_ticket", *raw_args]
    try:
        cfg = load_worker_config(args.cwd)
        result = run_retro(
            cfg,
            task_arg=args.task,
            apply=args.apply,
            command=command,
            blackboard=args.blackboard,
            commit_and_push=args.commit_and_push,
            allow_main_push=args.allow_main_push,
            commit_message=args.commit_message,
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
