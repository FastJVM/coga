"""Shared activity clocks and derived operator cells for task views."""

from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath

from coga.config import Config
from coga.git import last_commit_times
from coga.logfile import last_activity_map
from coga.tasks import TaskRef
from coga.ticket import Ticket


def _git_updated_by_slug(
    refs: list[TaskRef], commit_times: dict[str, datetime]
) -> dict[str, datetime]:
    """Fold `tasks/`-relative commit times onto the task that owns each path.

    A commit under a directory-form task touches `<slug>/ticket.md` (or a
    sibling attachment), never the task directory itself, so
    each path is walked up to the nearest enclosing task. A file-form task is
    its own path. Paths belonging to no live task — a deleted or renamed-away
    ticket — simply have no owner and drop out.

    Resolution is per path rather than per task so the whole fold is one pass
    over the commit map instead of a scan per row.
    """
    owners = {
        (f"{ref.id_slug}.md" if ref.file_form else ref.id_slug): ref.id_slug
        for ref in refs
    }
    out: dict[str, datetime] = {}
    for path, stamp in commit_times.items():
        candidate = PurePosixPath(path)
        for anchor in (candidate, *candidate.parents):
            slug = owners.get(anchor.as_posix())
            if slug is None:
                continue
            # Newest wins: a task dir's files land here in arbitrary order.
            if slug not in out or stamp > out[slug]:
                out[slug] = stamp
            break
    return out

def last_updated_map(cfg: Config, refs: list[TaskRef]) -> dict[str, datetime]:
    """Each task's last-activity timestamp — the `Updated` column's source.

    The primary source is the repo-global log (one pass builds every task's
    last-activity stamp). The log only knows a task by its ref, so it goes
    silent when a task directory is moved (append-only lines keep the old ref)
    or when a ticket reached disk without passing through a logging command;
    git saw both, so one `git log` pass backstops the blanks — see
    `last_commit_times`. Tasks with no stamp from either source are absent.

    Shared by `coga status` and the megalaunch picker so both views read one
    clock.
    """
    activity = last_activity_map(cfg)
    # Only tasks the log is silent on need git's history, and usually there
    # are none or a handful — walking every commit under `tasks/` for them
    # dominated `coga status` on a long-lived repo.
    uncovered = [
        f"{ref.id_slug}.md" if ref.file_form else ref.id_slug
        for ref in refs
        if ref.id_slug not in activity
    ]
    git_updated = _git_updated_by_slug(refs, last_commit_times(cfg, uncovered))
    out: dict[str, datetime] = {}
    for ref in refs:
        stamp = activity.get(ref.id_slug) or git_updated.get(ref.id_slug)
        if stamp is not None:
            out[ref.id_slug] = stamp
    return out

def operator_cell(cfg: Config, ref: TaskRef, ticket: Ticket) -> str:
    """The derived-operator column for one row.

    Never raises and never consults the network: a single ticket with a broken
    frozen workflow must show a visible diagnostic in its own row rather than
    taking down the whole listing. A terminal task shows a dash — it has no
    current operator. A draft that has not chosen an agent shows the one
    activation would select, marked so it does not read as already decided.
    """
    from coga.bump import OperatorResolutionError, resolve_operator

    try:
        operator = resolve_operator(cfg, ref, ticket)
    except OperatorResolutionError:
        try:
            operator = resolve_operator(
                cfg, ref, ticket, allow_prospective_default=True
            )
        except OperatorResolutionError:
            return "(unresolved)"
        return f"{operator.name}?" if operator is not None else "-"
    return operator.name if operator is not None else "-"
