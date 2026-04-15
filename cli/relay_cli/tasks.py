"""Task discovery — walk project paths and find tickets."""
from .config import Config
from .ticket import Ticket


def _iter_task_dirs(cfg: Config, project_filter=None):
    projects = cfg.shared.get("projects", {}) or {}
    for name in projects:
        if project_filter and name != project_filter:
            continue
        path = cfg.project_path(name)
        if not path:
            continue
        tasks_dir = path / "relay-os" / "tasks"
        if not tasks_dir.exists():
            continue
        for d in sorted(tasks_dir.iterdir()):
            if d.is_dir() and (d / "ticket.md").exists():
                yield name, d


def find_task(cfg: Config, task_ref: str, project_filter=None):
    """Find a task by id prefix or full dir name. Returns (Ticket, project_name).
    Raises SystemExit on no-match or ambiguous-match."""
    matches = []
    for name, d in _iter_task_dirs(cfg, project_filter):
        if d.name == task_ref or d.name.startswith(f"{task_ref}-"):
            matches.append((Ticket(d / "ticket.md"), name))
    if not matches:
        raise SystemExit(f"error: no task found matching '{task_ref}'")
    if len(matches) > 1:
        lines = "\n".join(f"  {name}/{t.slug}" for t, name in matches)
        raise SystemExit(
            f"error: ambiguous task '{task_ref}' — matches:\n{lines}"
        )
    return matches[0]


def all_tasks(cfg: Config):
    out = []
    for name, d in _iter_task_dirs(cfg):
        out.append((Ticket(d / "ticket.md"), name))
    return out
