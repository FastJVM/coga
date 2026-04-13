"""relay panic — agent is stuck. Record blocker, @mention owner, stop."""
from datetime import datetime

from ..config import Config
from ..logfile import append as log_append
from ..slack import post as slack_post
from ..tasks import find_task


def register(sub):
    p = sub.add_parser("panic", help="Agent is stuck — escalate to the task owner")
    p.add_argument("--task", required=True)
    p.add_argument("--reason", required=True, help="Short, concrete reason")
    p.set_defaults(func=run)


def _write_blocker(bb_path, actor, reason):
    bb = bb_path.read_text()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"- [{ts}] [{actor}] {reason}\n"

    marker = "## Blockers"
    if marker not in bb:
        # No blockers section — append one.
        bb = bb.rstrip() + f"\n\n{marker}\n\n{entry}"
        bb_path.write_text(bb)
        return

    lines = bb.splitlines(keepends=True)
    out = []
    i = 0
    while i < len(lines):
        out.append(lines[i])
        if lines[i].rstrip() == marker:
            # Skip past any blank lines and HTML-style comment hints.
            i += 1
            while i < len(lines) and (
                lines[i].strip() == ""
                or lines[i].lstrip().startswith("<!--")
            ):
                out.append(lines[i])
                i += 1
            # Insert entry here.
            out.append(entry)
            # Copy remaining lines verbatim.
            out.extend(lines[i:])
            break
        i += 1
    bb_path.write_text("".join(out))


def run(args):
    cfg = Config()
    ticket, project = find_task(cfg, args.task)

    actor = ticket.assignee or cfg.user or "unknown"
    _write_blocker(ticket.dir / "blackboard.md", actor, args.reason)
    log_append(
        ticket.dir,
        actor=f"agent:{actor}" if ticket.assignee else f"cli:{actor}",
        message=f"panic: {args.reason}",
    )

    owner = ticket.owner
    slack_id = cfg.assignee_slack(owner) if owner else None
    slack_post(
        f'{project} {ticket.id} "{ticket.title}" — agent stuck: "{args.reason}"',
        mention_user_id=slack_id,
    )

    print(f"panic recorded on {project}/{ticket.id}")
    return 0
