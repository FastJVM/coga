"""relay create — scaffold a new task directory."""
import re
from pathlib import Path

import yaml

from ..blackboard import TEMPLATE as BLACKBOARD_TEMPLATE
from ..config import Config
from ..logfile import append as log_append


def register(sub):
    p = sub.add_parser("create", help="Create a new task")
    p.add_argument("--project", required=True, help="Project name (from relay.toml)")
    p.add_argument("--title", required=True, help="Human-readable task title")
    p.add_argument("--owner", help="Defaults to the user in relay.local.toml")
    p.add_argument("--assignee", help="Assignee nickname (agent) or human name")
    p.add_argument(
        "--mode",
        default="interactive",
        choices=["interactive", "auto", "script"],
        help="How relay launch should run this task (default: interactive)",
    )
    p.add_argument("--workflow", help="Workflow name, e.g. code/with-review")
    p.add_argument(
        "--context",
        action="append",
        default=[],
        metavar="REF",
        help="Context ref to attach (repeatable), e.g. email/payment-flow",
    )
    p.set_defaults(func=run)


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s[:60] or "task"


def _next_id(tasks_dir: Path) -> str:
    if not tasks_dir.exists():
        return "001"
    ids = []
    for d in tasks_dir.iterdir():
        if d.is_dir():
            m = re.match(r"^(\d+)-", d.name)
            if m:
                ids.append(int(m.group(1)))
    n = (max(ids) + 1) if ids else 1
    return f"{n:03d}"


def _load_workflow_snapshot(cfg: Config, name: str | None):
    if not name:
        return None
    path = cfg.root / "workflows" / f"{name}.md"
    if not path.exists():
        raise SystemExit(
            f"error: workflow not found: {name} (looked for {path})"
        )
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        raise SystemExit(f"error: workflow {name} has no YAML frontmatter")
    wf = yaml.safe_load(m.group(1)) or {}
    steps = wf.get("steps") or []
    if not steps:
        raise SystemExit(f"error: workflow {name} has no steps")
    return {"name": wf.get("name", name), "steps": steps}


def _validate_contexts(cfg: Config, refs):
    missing = []
    for ref in refs:
        if not (cfg.root / "contexts" / ref / "SKILL.md").exists():
            missing.append(ref)
    if missing:
        raise SystemExit(
            "error: context references not found:\n  "
            + "\n  ".join(missing)
        )


def run(args):
    cfg = Config()
    project = cfg.project(args.project)
    if not project:
        known = ", ".join((cfg.shared.get("projects") or {}).keys()) or "(none)"
        raise SystemExit(
            f"error: unknown project '{args.project}'. Known: {known}"
        )
    proj_path = cfg.project_path(args.project)
    if not proj_path:
        raise SystemExit(
            f"error: project '{args.project}' has no path configured in "
            f"relay.local.toml [paths]"
        )
    if not proj_path.exists():
        raise SystemExit(
            f"error: project path does not exist: {proj_path}\n"
            f"create it first: mkdir -p {proj_path}"
        )

    _validate_contexts(cfg, args.context)

    workflow = _load_workflow_snapshot(cfg, args.workflow)

    tasks_dir = proj_path / ".relay" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    tid = _next_id(tasks_dir)
    slug = _slugify(args.title)
    task_dir = tasks_dir / f"{tid}-{slug}"
    task_dir.mkdir()

    fm: dict = {
        "title": args.title,
        "status": project.get("default_status", "ready"),
        "mode": args.mode,
    }
    owner = args.owner or cfg.user
    if owner:
        fm["owner"] = owner
    if args.assignee:
        fm["assignee"] = args.assignee
    if workflow:
        fm["workflow"] = workflow
        first = workflow["steps"][0]
        fm["step"] = f"1 ({first['name']})"
    if args.context:
        fm["contexts"] = list(args.context)

    fm_text = yaml.safe_dump(
        fm, sort_keys=False, default_flow_style=False
    ).rstrip()
    ticket_md = (
        f"---\n{fm_text}\n---\n\n"
        f"## Description\n\n{args.title}\n\n"
        f"## Context\n\n<!-- task-specific details — not a reusable context block. -->\n"
    )
    (task_dir / "ticket.md").write_text(ticket_md)
    (task_dir / "log.md").write_text("")
    (task_dir / "blackboard.md").write_text(
        BLACKBOARD_TEMPLATE.format(id=tid, title=args.title)
    )

    log_append(
        task_dir,
        actor=f"cli:{cfg.user or 'unknown'}",
        message=f"created task {tid} in project {args.project}",
    )

    print(f"created {args.project}/{tid}-{slug}")
    print(f"  {task_dir}")
    return 0
