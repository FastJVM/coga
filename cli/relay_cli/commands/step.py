"""relay step — advance a task to its next workflow step, or mark done."""
from ..config import Config
from ..logfile import append as log_append
from ..slack import post as slack_post
from ..tasks import find_task
from ..ticket import parse_step_field


def register(sub):
    p = sub.add_parser("step", help="Advance to the next workflow step")
    p.add_argument("--task", required=True, help="Task id or dir name")
    p.set_defaults(func=run)


def run(args):
    cfg = Config()
    ticket, project = find_task(cfg, args.task)

    if ticket.status != "active":
        raise SystemExit(
            f"error: task {ticket.id} is '{ticket.status}', not active — "
            f"cannot advance"
        )

    wf = ticket.workflow
    if not wf or not wf.get("steps"):
        raise SystemExit(f"error: task {ticket.id} has no workflow steps")

    steps = wf["steps"]
    current_n, _ = parse_step_field(ticket.step)
    if current_n is None:
        raise SystemExit(
            f"error: task {ticket.id} has invalid step field: {ticket.step!r}"
        )

    actor = cfg.user or "unknown"

    if current_n >= len(steps):
        # Already on the last step — mark done.
        ticket.frontmatter["status"] = "done"
        ticket.save()
        log_append(ticket.dir, actor=f"cli:{actor}", message="task done")
        slack_post(f'{project} {ticket.id} "{ticket.title}" done')
        print(f"task {project}/{ticket.id} marked done")
        return 0

    next_n = current_n + 1
    next_step = steps[next_n - 1]
    next_label = f"{next_n} ({next_step['name']})"
    ticket.frontmatter["step"] = next_label
    ticket.save()
    log_append(
        ticket.dir,
        actor=f"cli:{actor}",
        message=f"advanced to step {next_label}",
    )
    slack_post(
        f'{project} {ticket.id} "{ticket.title}" -> step {next_label}'
    )
    print(f"{project}/{ticket.id}: step {next_label}")
    return 0
