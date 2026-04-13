"""relay feed — post an FYI to the shared Slack channel."""
from ..config import Config
from ..logfile import append as log_append
from ..slack import post as slack_post
from ..tasks import find_task


def register(sub):
    p = sub.add_parser("feed", help="Post an FYI to the shared Slack feed")
    p.add_argument("--task", required=True)
    p.add_argument("--message", required=True)
    p.set_defaults(func=run)


def run(args):
    cfg = Config()
    ticket, project = find_task(cfg, args.task)
    actor = ticket.assignee or cfg.user or "unknown"
    slack_post(f"{project} {ticket.id}: {args.message}")
    log_append(
        ticket.dir,
        actor=f"cli:{actor}",
        message=f"feed: {args.message}",
    )
    print("posted to feed")
    return 0
