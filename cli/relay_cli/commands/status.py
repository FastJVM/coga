"""relay status — one-line-per-task view across all projects."""
from ..config import Config
from ..tasks import all_tasks


ACTIVE_STATUSES = {"design", "ready", "active", "paused"}


def register(sub):
    p = sub.add_parser("status", help="Show all active tasks across projects")
    p.add_argument(
        "--all",
        action="store_true",
        help="Include done, canceled, and failed tasks too",
    )
    p.set_defaults(func=run)


def run(args):
    cfg = Config()
    tasks = all_tasks(cfg)
    if not args.all:
        tasks = [(t, p) for t, p in tasks if t.status in ACTIVE_STATUSES]
    if not tasks:
        print("no active tasks")
        return 0

    header = ("project", "id", "title", "status", "assignee", "step", "mode")
    rows = [
        (
            proj,
            t.id,
            (t.title or "")[:40],
            t.status or "",
            t.assignee or "-",
            t.step or "-",
            t.mode or "interactive",
        )
        for t, proj in tasks
    ]
    widths = [
        max(len(str(r[i])) for r in (header,) + tuple(rows))
        for i in range(len(header))
    ]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*header))
    print(fmt.format(*["-" * w for w in widths]))
    for r in rows:
        print(fmt.format(*r))
    return 0
