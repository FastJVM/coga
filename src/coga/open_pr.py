"""Push a code ticket's branch and open (or ready) its PR.

The `open-pr` registered recipe: `coga run open-pr <task>` — which the
`open-pr` default alias spells `coga open-pr <task>` — resolves the target
task, applies the checkout gate, and calls `open_pr()`. The ordinary
agent-owned open-pr step runs that spelling. Every operational refusal raises
`OpenPrError`, which `run_open_pr_recipe` renders as a concise non-zero exit
with nothing on stdout. The workflow's `requires: pr` completion gate is
separate: `coga bump` advances only after this recipe records the PR URL
under `## Dev`.

The contract callers depend on is the **bare PR URL on stdout** (so
`$(coga open-pr <slug>)` captures exactly the URL). The command runs from the
launch checkout on the control branch and checks the recorded branch by name;
only a recorded sandbox clone (`worktree:`, see `dev/checkouts`) is entered.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import sys
import tempfile

import yaml
from pathlib import Path

from coga.autoclose import parse_branch_name, parse_pr_url, parse_worktree_path
from coga.blackboard import update_blackboard_under_barrier
from coga.config import Config
from coga.github_preflight import (
    _remote_host,
    check_branch_contains_control,
    check_git_auth,
    check_git_remote,
    check_gh_auth,
    stranded_task_state_paths,
    stranded_task_state_remediation,
)
from coga.git import GitError
from coga.lifecycle import TERMINAL_STATUSES
from coga.taskfile import body_sections, split_body
from coga.tasks import TaskNotFoundError, read_ticket, resolve_task
from coga.ticket import Ticket


class OpenPrError(Exception):
    """A fail-loud condition in the open-pr recipe (missing state, nothing to
    PR, or a git/gh failure). `run_open_pr_recipe` maps it to a non-zero exit
    so the workflow step does not advance."""


def _run(args: list[str], *, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    # Decode as UTF-8 explicitly rather than through the ambient locale: this
    # reads ticket bodies, and a launch subprocess chain running under `LC_ALL=C`
    # would otherwise raise `UnicodeDecodeError` on the first em dash.
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _git(args: list[str], *, cwd: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", "-C", cwd, *args])


def _git_checkout_root(path: str | Path) -> Path | None:
    """Return the resolved worktree root containing `path`, if it is in Git.

    `--show-toplevel` identifies a checkout rather than only its shared Git
    repository, so linked worktrees remain distinct while nested Coga roots and
    symlinked paths still compare equal to their containing checkout.
    """
    result = _run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"]
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).resolve()


def same_git_checkout(left: str | Path, right: str | Path) -> bool:
    """Return whether two paths are inside the same Git checkout."""
    left_root = _git_checkout_root(left)
    right_root = _git_checkout_root(right)
    return left_root is not None and left_root == right_root


def _live_ticket_relpath(blackboard_path: Path) -> str | None:
    """The live ticket file's path relative to the checkout containing it.

    The live ticket lives in the *primary* checkout, whose toplevel is not the
    recorded feature checkout in the separate-checkout layout. Resolving against
    the checkout that actually contains the file keeps the same relative path
    valid on the feature branch, where a stranded copy would be. `git -C`
    needs a directory, so the lookup starts from the ticket's parent.
    """
    checkout_root = _git_checkout_root(blackboard_path.parent)
    if checkout_root is None:
        return None
    try:
        return blackboard_path.resolve().relative_to(checkout_root).as_posix()
    except ValueError:
        return None


def _dirty_paths(porcelain_z: str) -> list[str]:
    """Paths named by NUL-delimited `git status --porcelain -z` output.

    Mirrors `git._changed_paths_under`: a rename or copy entry carries its
    source path in the following NUL field, and both endpoints are returned so
    a ticket renamed away from its committed path is still recognized.
    """
    fields = porcelain_z.split("\x00")
    paths: list[str] = []
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if not entry:
            continue
        status, path = entry[:2], entry[3:]
        if path:
            paths.append(path)
        if status[0] in ("R", "C") and i < len(fields):
            source = fields[i]
            i += 1
            if source:
                paths.append(source)
    return paths


def _remote_branch_oid(remote: str, branch: str, *, cwd: str) -> str | None:
    """Return the advertised remote branch OID, or None when it does not exist."""
    result = _git(
        ["ls-remote", "--heads", remote, f"refs/heads/{branch}"], cwd=cwd
    )
    if result.returncode != 0:
        hint = check_git_auth(remote).detail
        raise OpenPrError(
            f"`git ls-remote {remote} {branch}` failed: "
            f"{result.stderr.strip() or 'no output'}\n{hint}"
        )
    line = next((line for line in result.stdout.splitlines() if line.strip()), "")
    return line.split(maxsplit=1)[0] if line else None


_PR_LINE_RE = re.compile(r"^(?P<prefix>\s*(?:-\s*)?)pr:.*$", re.MULTILINE)
_DEV_HEADER_RE = re.compile(r"^##\s+Dev\s*$", re.MULTILINE)
_DEV_SECTION_RE = re.compile(r"^##\s+Dev\s*\n(.*?)(?=\n##\s|\Z)", re.MULTILINE | re.DOTALL)


def set_dev_pr(blackboard_text: str, url: str) -> str:
    """Return `blackboard_text` with the `## Dev` `pr:` line set to `url`.

    Updates the line in place when present (preserving any `- ` / indentation),
    inserts one right after the `## Dev` header when the section exists without a
    `pr:` line, and appends a fresh `## Dev` section as a last resort. Mirrors the
    `dev/dev-record` convention: the blackboard records *current* state, so overwrite
    rather than append a second `pr:` line.
    """
    section = _DEV_SECTION_RE.search(blackboard_text)
    if section:
        body = section.group(1)
        if _PR_LINE_RE.search(body):
            new_body = _PR_LINE_RE.sub(
                lambda m: f"{m.group('prefix')}pr: {url}", body, count=1
            )
        else:
            new_body = f"pr: {url}\n{body}" if body else f"pr: {url}\n"
        return blackboard_text[: section.start(1)] + new_body + blackboard_text[section.end(1):]

    header = _DEV_HEADER_RE.search(blackboard_text)
    if header:
        return blackboard_text[: header.end()] + f"\npr: {url}" + blackboard_text[header.end():]

    sep = "" if not blackboard_text or blackboard_text.endswith("\n") else "\n"
    return f"{blackboard_text}{sep}\n## Dev\npr: {url}\n"


def _stranded_ticket_detail(
    overlaps: tuple[str, ...],
    *,
    base: str,
    branch: str,
    head_ref: str,
    cwd: str,
    worktree: str | None,
    blackboard_path: Path,
) -> str | None:
    """Re-word a freshness refusal caused by this ticket's own stranded write.

    Only when the probe's *actual* unsafe overlaps include the live ticket's
    file: a refusal for source drift, a fetch failure, or another ticket's
    state keeps the probe's generic wording, because "rebase" is the right
    advice there and wrong here. The comparison runs against `FETCH_HEAD` in
    the checkout the probe ran in — the tip it just fetched and compared — not
    the local control ref, which a fetch does not advance. When control also carries other unsafe overlaps they are named after the
    ticket remediation so that reason is not hidden; drop the ticket write
    first, then bring control in with a merge rather than a rebase.
    """
    ticket_rel = _live_ticket_relpath(blackboard_path)
    if ticket_rel is None or ticket_rel not in overlaps:
        return None
    stranded = stranded_task_state_paths(
        "FETCH_HEAD", head_ref, [ticket_rel], cwd=cwd
    )
    if stranded is None:
        provenance = ""
    elif ticket_rel in stranded:
        provenance = (
            " Control never received this content, so inspect it before "
            "dropping it."
        )
    else:
        provenance = (
            " Control already absorbed this exact content into its history "
            "and has since moved on, so nothing is lost by dropping the branch "
            "copy."
        )
    others = [path for path in overlaps if path != ticket_rel]
    remediation = stranded_task_state_remediation(
        control_ref="FETCH_HEAD",
        branch_ref=head_ref,
        paths=[ticket_rel],
        checkout=worktree,
    )
    tail = ""
    if others:
        tail = (
            f" The branch also diverges from {base} on: {', '.join(others)}; "
            "after dropping the ticket write, bring control in with "
            "`git merge FETCH_HEAD` (not a rebase) and resolve those."
        )
    return (
        f"Branch {branch!r} has committed changes to this ticket's own file "
        f"({ticket_rel}) that {base} does not contain. This is a stranded "
        "ticket write: the ticket was edited and committed on the feature "
        f"branch while `coga` advanced the same file on {base}. Rebasing "
        f"would replay it and conflict.{provenance} {remediation}{tail}"
    )


def _check_recorded_clone(
    worktree: str, branch: str, *, blackboard_path: Path
) -> None:
    """Refuse a recorded sandbox clone that is missing, off-branch, or dirty.

    The clone is the one checkout open-pr enters, because its branch is not a
    ref of this repository. Uncommitted edits to the ticket file there are a
    duplicate in the making: committing them is what turns the stranded write
    into a merge conflict a step later, so they get their own remediation.
    Attachments and `ticket.py` beside a directory ticket are ordinary
    implementation dirt and keep the commit instruction.
    """
    if not Path(worktree).is_dir():
        raise OpenPrError(
            f"Recorded worktree {worktree!r} does not exist. If the recorded path "
            "has a trailing repository note, delimit the path with backticks "
            "(for example: worktree: `/path` (other repo)), or put the note on "
            "a separate line. A sandbox clone under /tmp does not survive a "
            "reboot: if the branch was pushed, fetch it into this checkout and "
            "drop the `worktree:` line; otherwise `coga block` the ticket."
        )
    head = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=worktree)
    if head.returncode != 0:
        raise OpenPrError(
            f"`git rev-parse` failed in {worktree!r}: {head.stderr.strip() or 'no output'}"
        )
    current_branch = head.stdout.strip()
    if current_branch != branch:
        raise OpenPrError(
            f"Recorded worktree {worktree!r} is on {current_branch!r}, not the "
            f"recorded branch {branch!r}. If the recorded branch has a trailing "
            "repository note, delimit the name with backticks "
            "(for example: branch: `name` (other repo)), or put the note on a "
            "separate line. Otherwise, check it out there before open-pr runs."
        )
    dirty = _git(
        ["status", "--porcelain", "-z", "--untracked-files=all", "--", "."],
        cwd=worktree,
    )
    if dirty.returncode != 0:
        raise OpenPrError(
            f"`git status` failed in {worktree!r}: {dirty.stderr.strip() or 'no output'}"
        )
    if not dirty.stdout.strip("\x00"):
        return
    dirty_paths = _dirty_paths(dirty.stdout)
    ticket_rel = _live_ticket_relpath(blackboard_path)
    ticket_dirt = [path for path in dirty_paths if path == ticket_rel]
    other_dirt = [path for path in dirty_paths if path != ticket_rel]
    if ticket_dirt:
        listed = ", ".join(ticket_dirt)
        if other_dirt:
            lead = (
                f"Commit the implementation dirt ({', '.join(other_dirt)}) "
                f"— but not this ticket's own file ({listed}) unchecked: "
            )
        else:
            lead = (
                f"The dirt is this ticket's own file ({listed}). Do not "
                "commit it here unchecked: "
            )
        # Control has already rewritten this ticket path (branch record,
        # lifecycle transitions), so any commit of it on the branch is an
        # overlapping stranded write the freshness gate refuses. Every
        # wanted change, authored body included, moves to the live copy.
        remediation = (
            f"{lead}the live copy is the primary checkout's, and control has "
            "already rewritten this path, so committing it on this branch "
            "strands an overlapping write that the freshness gate refuses. "
            "Inspect the diff first and move everything still wanted — "
            "blackboard text or an intentional change to the authored ticket "
            "body — into the live ticket in the primary checkout, then "
            "discard the clone's copy "
            f"(`git restore --staged --worktree -- {' '.join(ticket_dirt)}`); "
            "do not commit or stash it just to pass this gate. "
        )
    else:
        remediation = (
            "In a sandbox clone, inspect task/log edits: preserve needed "
            "blackboard text in the primary ticket and verify audit entries in "
            "the authoritative log before discarding only confirmed duplicate "
            "hunks here. Preserve unique audit evidence for reconciliation and "
            "keep intentional ticket or attachment changes that belong to the "
            "implementation. "
        )
    raise OpenPrError(
        f"Recorded worktree {worktree!r} has uncommitted changes. The "
        "implement/peer-review steps must commit implementation work before "
        f"open-pr. {remediation}Then relaunch."
    )


_STATUSES = {"passed", "failed", "pending", "not-run"}
_TITLE_LIMIT = 256
_MANAGED_START = re.compile(
    r"<!-- coga:pr:v1 title=([0-9a-f]{64}) body=([0-9a-f]{64}) -->\r?\n"
)
_MANAGED_END = "<!-- /coga:pr -->"


def _sections(text: str) -> dict[str, str]:
    """Return exact level-two sections, heading line included, by lowercase name.

    Parsed by the shared fence-aware `taskfile.body_sections`, the same one
    compose and validate read, so the PR's request snapshot matches the prompt.
    """
    return {
        s.key: text[s.start:s.end] for s in body_sections(text) if s.heading
    }


def _preparation(blackboard: str, above: str) -> dict:
    content = ""
    for text in (blackboard, above):
        content = _sections(text).get("pr", "").partition("\n")[2].strip()
        if content:
            break
    if not content:
        return {}
    if not content.startswith("```yaml"):
        # Legacy prose is shown as unverified text, never as check/review evidence.
        return {"legacy": content}
    match = re.fullmatch(r"```yaml\s*\n(.*?)\n```", content, re.DOTALL)
    if not match:
        raise OpenPrError("PR presentation: use one complete fenced yaml mapping under ## PR.")
    try:
        data = yaml.safe_load(match[1])
    except yaml.YAMLError as exc:
        raise OpenPrError(f"PR presentation: invalid YAML under ## PR: {exc}") from exc
    if not isinstance(data, dict):
        raise OpenPrError("PR presentation: ## PR YAML must be a mapping.")
    return data


def _text(data: dict, key: str, default: str = "") -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise OpenPrError(f"PR presentation: {key} must be a string.")
    return value.strip()


def _cell(value: str) -> str:
    return html.escape(value).replace("|", "&#124;").replace("\n", "<br>")


def _receipt(data: dict, head: str, base: str) -> tuple[str, str]:
    status = _text(data, "status", "not-run")
    if status not in _STATUSES:
        raise OpenPrError(f"PR presentation: invalid status {status!r}.")
    detail = _text(data, "detail")
    if not detail:
        return "not-run", "Missing result or reason; no usable evidence recorded."
    if status != "not-run" and (data.get("head"), data.get("base")) != (head, base):
        return "stale", (
            f"Historical {status} at head {data.get('head', 'unknown')}, "
            f"base {data.get('base', 'unknown')}: {detail}. "
            "Not verified for the current diff."
        )
    return status, detail


def _publication_diff(cwd: str, head_ref: str, base_ref: str) -> tuple[str, str, list[tuple[str, list[str]]]]:
    def git_value(args: list[str]) -> str:
        result = _git(args, cwd=cwd)
        if result.returncode:
            raise OpenPrError(f"PR presentation: git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.rstrip("\n")

    head = git_value(["rev-parse", head_ref])
    base = git_value(["merge-base", base_ref, head])
    fields = git_value(["diff", "--name-status", "-z", "--find-renames", base, head]).split("\x00")
    changes: list[tuple[str, list[str]]] = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        count = 2 if status.startswith(("R", "C")) else 1
        changes.append((status, fields[i + 1:i + count + 1]))
        i += count + 1
    return head, base, changes


def _pr_body(ticket: Ticket, above: str, slug: str, content: str) -> str:
    """Append the literal request snapshot, never frontmatter or blackboard."""
    sections = _sections(above)
    snapshot = f"# {ticket.title or slug}\n\n" + "".join(
        sections.get(name, "") for name in ("description", "context")
    )
    return (
        f"{content}\n\n<details>\n<summary>Ticket as requested</summary>\n\n"
        f"{snapshot}" + ("" if snapshot.endswith("\n") else "\n")
        + f"\n</details>\n\nCloses ticket: `{slug}`\n"
    )


def _pr_presentation(
    ticket: Ticket, blackboard: str, above: str, slug: str, *,
    head: str, base: str, changes: list[tuple[str, list[str]]],
) -> tuple[str, str]:
    data = _preparation(blackboard, above)
    issues: list[str] = []
    legacy = data.pop("legacy", "")
    if legacy:
        issues.append("Unstructured legacy ## PR prose; shown below as unverified implementation text.")
        data = {"implementation": legacy}
    elif not data:
        issues.append("Missing structured preparation; no implementation, review or check evidence recorded.")
    elif (data.get("head"), data.get("base")) != (head, base):
        issues.append(
            "Stale preparation: its head/base does not describe this diff; explanations "
            "may be outdated and receipts verify only their recorded revisions."
        )
    title = _text(data, "title")
    if not title:
        issues.append("Actual-change title unavailable; using the ticket title.")
        title = ticket.title or slug
    title = " ".join(title.split())
    author = _text(data, "author", "unknown")
    authorship = _text(data, "author_evidence")
    if not authorship or author == "unknown":
        author, authorship = "unknown", "Actual author identity unavailable; no session evidence recorded."
        issues.append(authorship)
    if not re.fullmatch(r"[\w./-]{1,32}", author):
        raise OpenPrError("PR presentation: author must be a compact identity (1–32 letters, digits, ./_-).")
    review = data.get("review", {})
    if not isinstance(review, dict):
        raise OpenPrError("PR presentation: review must be a mapping.")
    kind = _text(review, "kind", "none")
    if kind not in {"independent", "self", "none"}:
        raise OpenPrError("PR presentation: review kind must be independent, self, or none.")
    reviewer = _text(review, "reviewer", "unknown")
    if not re.fullmatch(r"[\w./-]{1,32}", reviewer):
        raise OpenPrError("PR presentation: reviewer must be a compact identity.")
    identified_reviewer = reviewer not in {"unknown", "none"}
    review_status, review_detail = _receipt(review, head, base)
    if kind == "none":
        reviewer = "none" if review else "unknown"
        review_status = "not-run"
        review_detail = "No independent review performed. " + review_detail
    elif kind == "self":
        reviewer += "(self)"
        review_detail = "Self-review; no independent review performed. " + review_detail
    if review_status != "passed" or not identified_reviewer:
        issues.append("No completed, identified review of the current diff.")
    if kind == "independent" and author != "unknown" and reviewer == author:
        kind = "self"
        reviewer += "(self)"
        issues.append("Review marked independent but the reviewer is the author; treated as self-review.")
    checks = data.get("checks", [])
    if not isinstance(checks, list) or any(not isinstance(check, dict) for check in checks):
        raise OpenPrError("PR presentation: checks must be a list of mappings.")
    check_items: list[str] = []
    statuses: list[str] = []
    for check in checks:
        command = _text(check, "command")
        if not command:
            raise OpenPrError("PR presentation: each check needs its actual command.")
        status, detail = _receipt(check, head, base)
        statuses.append(status)
        fence = "`" * max(3, 1 + max((len(m[0]) for m in re.finditer(r"`+", command)), default=0))
        command_block = "\n".join(f"  {line}" for line in command.split("\n"))
        check_items.append(
            f"- **{status}** — {_cell(detail)}\n\n"
            f"  {fence}sh\n{command_block}\n  {fence}"
        )
        if not _text(check, "detail"):
            issues.append("A check has no recorded result or omission reason.")
    if not checks:
        issues.append("Checks not run or not recorded; commands, outcomes and omission reasons unavailable.")
        check_items.append("- **not-run** — No check evidence or omission reason recorded.")
    if any(status in {"failed", "pending", "stale"} for status in statuses):
        issues.append("Checks failed, remain pending, or do not verify this diff.")
    files = data.get("files", {})
    if not isinstance(files, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in files.items()):
        raise OpenPrError("PR presentation: files must map paths to explanations.")
    file_rows: list[str] = []
    paths = {path for _, names in changes for path in names}
    for status, names in changes:
        for path in names:
            if not files.get(path, "").strip():
                issues.append(f"Unexplained path: {path}")
            file_rows.append(f"| <code>{_cell(path)}</code> | {status} |")
    extras = sorted(set(files) - paths)
    if extras:
        issues.append("Prepared paths outside this diff: " + ", ".join(extras))
    prose: dict[str, str] = {}
    for key in ("rationale", "implementation", "deviations", "limitations"):
        prose[key] = _text(data, key)
        if not prose[key]:
            prose[key] = "Not recorded; inspect the diff and request clarification."
            issues.append(f"Missing {key} explanation.")
    depth = _text(data, "depth", "deep")
    if depth not in {"merge", "skim", "deep"}:
        raise OpenPrError("PR presentation: depth must be merge, skim, or deep.")
    if depth == "merge" and (kind != "independent" or "passed" not in statuses):
        issues.append("Merge recommendation requires independent review and a passed applicable check.")
    if issues:
        depth = "deep"
    prefix = f"[{depth} · A:{author} R:{reviewer}] "
    full_change_title = title
    budget = _TITLE_LIMIT - len(prefix)
    shortened = len(title) > budget
    if shortened:
        title = title[:budget - 1].rstrip() + "…"
    title = prefix + title
    content = (
        f"**Recommended review: {depth}** — advisory; the owner decides whether to merge.\n\n"
        f"{prose['rationale']}\n\n"
    )
    if issues:
        content += "Publication evidence gaps:\n" + "\n".join(f"- {issue}" for issue in issues) + "\n\n"
    if shortened:
        content += f"Full change title: {full_change_title}\n\n"
    content += (
        f"Author: **{author}**. {authorship}\n\n"
        f"Review: **{reviewer}** ({kind}, {review_status}). {review_detail}\n\n"
        f"Evidence scope: head `{head}`, diff base `{base}`.\n\n"
        f"## Implementation\n\n{prose['implementation']}\n\n"
        f"## Deviations and limitations\n\n{prose['deviations']}\n\n{prose['limitations']}\n\n"
        "## Changed files\n\n| Path | Change |\n| --- | --- |\n"
        + "\n".join(file_rows)
        + "\n\n## Checks\n\n"
        + "\n\n".join(check_items)
    )
    body = _pr_body(ticket, above, slug, content)
    marker = f"<!-- coga:pr:v1 title={_digest(title)} body={_digest(body)} -->\n"
    return title, marker + body + _MANAGED_END + "\n"


def _digest(value: str) -> str:
    # Web-editor saves may change line endings without changing the prose.
    return hashlib.sha256(value.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _refresh_body(existing: dict, title: str, body: str, base: str, legacy_title: str) -> str:
    """Replace only intact generated content; refuse human conflicts."""
    if existing.get("baseRefName") != base:
        raise OpenPrError("PR presentation: existing PR base differs or is unavailable; reconcile its base first.")
    old_body = existing.get("body") or ""
    old_title = existing.get("title") or ""
    marker = _MANAGED_START.search(old_body)
    if marker is None:
        # A PR from before generated markers: adopt it only when its title is
        # still the old generated ticket title, and keep its whole body as
        # human-owned notes below the new generated region.
        if old_title != legacy_title:
            raise OpenPrError(
                "PR presentation conflict: unmarked existing PR with a human-edited title; "
                f"rename it to {legacy_title!r} to adopt the generated format (its body is kept), "
                "or reconcile with the owner."
            )
        return body.rstrip("\n") + ("\n\n" + old_body if old_body.strip() else "\n")
    # Literal marker examples can occur inside the ticket snapshot. The stored
    # digest identifies the actual end, without interpreting the snapshot.
    ends = [
        match.start() for match in re.finditer(re.escape(_MANAGED_END), old_body)
        if match.start() >= marker.end()
        and _digest(old_body[marker.end():match.start()]) == marker[2]
    ]
    if len(ends) != 1 or _digest(old_title) != marker[1]:
        raise OpenPrError("PR presentation conflict: human edits or malformed generated title/body; preserve edits outside the markers and reconcile preparation before rerunning.")
    end = ends[0]
    old_region = old_body[marker.start():end + len(_MANAGED_END)]
    new_region = body.rstrip("\n")
    if old_region.replace("\r\n", "\n") == new_region.replace("\r\n", "\n"):
        return old_body
    # New body's trailing newline is formatting outside the region, not owned.
    return old_body[:marker.start()] + new_region + old_body[end + len(_MANAGED_END):]


def _write_pr(args: list[str], title: str, body: str, *, cwd: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="coga-pr-") as directory:
        path = Path(directory) / "body.md"
        path.write_text(body, encoding="utf-8")
        return _run([*args, "--title", title, "--body-file", str(path)], cwd=cwd)


def _open_pr_url(branch: str, cwd: str) -> dict | None:
    """Return the open PR, or confirmed absence; refuse lookup failures."""
    result = _run(
        ["gh", "pr", "view", branch, "--json",
         "url,state,isDraft,number,title,body,baseRefName,isCrossRepository"],
        cwd=cwd,
    )
    if result.returncode != 0:
        # gh's branch finder excludes fork heads with the same bare branch name.
        # Only its explicit not-found result proves absence; API/auth errors do not.
        if (result.returncode == 1 and not result.stdout.strip()
                and re.fullmatch(r'no pull requests found for branch ".+"', result.stderr.strip())):
            return None
        raise OpenPrError(f"PR lookup failed: {result.stderr.strip() or 'no output'}; retry before publishing.")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise OpenPrError("PR lookup returned invalid JSON; retry before publishing.") from exc
    if (not isinstance(data, dict) or data.get("state") not in {"OPEN", "CLOSED", "MERGED"}
            or any(not isinstance(data.get(key), str) for key in ("url", "title", "body", "baseRefName"))
            or not data["url"] or not data["baseRefName"] or not isinstance(data.get("isDraft"), bool)
            or not isinstance(data.get("isCrossRepository"), bool)):
        raise OpenPrError("PR lookup returned incomplete presentation data; retry before publishing.")
    if data["isCrossRepository"]:
        raise OpenPrError("PR lookup returned a fork head instead of the published branch; reconcile before publishing.")
    return data if data["state"] == "OPEN" else None


def open_pr(
    cfg: Config,
    *,
    slug: str,
    blackboard_path: Path,
) -> str:
    """Push the feature branch and open (or ready) its PR; return the PR URL.

    Reads `branch:` (plus `worktree:` for a sandbox clone) from `## Dev`
    and structured presentation evidence from `## PR` on the blackboard. Without a
    recorded clone the branch is checked by name in this checkout, which stays
    on the control branch: it must exist locally, be ahead of the base branch,
    and have no material stale drift from `<remote>/<base>`. With a recorded
    clone the same checks run inside it, and it must also be on the branch and
    clean. Then it pushes, opens the PR (`gh pr create`, or `gh pr ready` for
    an existing draft, or reuses an already-open PR), and writes `pr: <url>`
    back under `## Dev`; the CLI exit sweep publishes that write.

    Raises `OpenPrError` on any fail-loud condition — the caller must not
    advance the workflow step when that happens.
    """
    remote = cfg.git_remote
    base = cfg.git_control_branch

    ticket = Ticket.read(blackboard_path)
    if ticket.status in TERMINAL_STATUSES:
        raise OpenPrError(
            f"Cannot open a PR for {slug}: ticket status "
            f"{ticket.status!r} is terminal."
        )
    above, blackboard = split_body(ticket.body)
    blackboard = blackboard or ""

    branch = parse_branch_name(blackboard)
    if not branch or branch.startswith("("):
        raise OpenPrError(
            "No usable `branch:` recorded under `## Dev` on the blackboard. The "
            "implement step must create the feature branch and record it before "
            "open-pr can run. Fix the `## Dev` section, or `coga block "
            f'--task {slug} --reason "..."` if the branch was lost.'
        )

    worktree = parse_worktree_path(blackboard)
    if worktree and same_git_checkout(cfg.repo_root, worktree):
        # Left by the retired single-checkout layout: the branch lives in this
        # checkout, so check it by name like any other.
        worktree = None
    if worktree:
        cwd, head_ref = worktree, "HEAD"
        _check_recorded_clone(worktree, branch, blackboard_path=blackboard_path)
    else:
        root = _git_checkout_root(cfg.repo_root)
        if root is None:
            raise OpenPrError(
                f"Could not resolve the Git checkout containing {str(cfg.repo_root)!r}."
            )
        cwd, head_ref = str(root), f"refs/heads/{branch}"
        if _git(["rev-parse", "--verify", "--quiet", head_ref], cwd=cwd).returncode != 0:
            raise OpenPrError(
                f"Recorded branch {branch!r} does not exist in this checkout. If "
                "the recorded branch has a trailing repository note, delimit the "
                "name with backticks (for example: branch: `name` (other repo)), "
                "or put the note on a separate line. If only the remote has it, "
                f"fetch it (`git fetch {remote} {branch}:{branch}`) and rerun, or "
                f"`coga block --task {slug}`."
            )

    already = parse_pr_url(blackboard)

    # Commits ahead of the base branch. Resolve the base as the local ref first
    # (shared across worktrees), then the remote-tracking ref. Zero commits ahead
    # is the incident's mis-branch case — fail loud instead of opening an empty PR.
    base_ref = base
    if _git(["rev-parse", "--verify", "--quiet", base], cwd=cwd).returncode != 0:
        remote_base = f"{remote}/{base}"
        if _git(["rev-parse", "--verify", "--quiet", remote_base], cwd=cwd).returncode == 0:
            base_ref = remote_base
        else:
            raise OpenPrError(
                f"Base branch {base!r} not found in {cwd!r} (neither {base!r} "
                f"nor {remote}/{base}). Fetch it, or set [git].control_branch."
            )
    ahead = _git(["rev-list", "--count", f"{base_ref}..{head_ref}"], cwd=cwd)
    if ahead.returncode != 0:
        raise OpenPrError(
            f"`git rev-list` failed in {cwd!r}: {ahead.stderr.strip() or 'no output'}"
        )
    if ahead.stdout.strip() == "0":
        raise OpenPrError(
            f"Branch {branch!r} has no commits ahead of {base_ref} — there is "
            "nothing to open a PR for. This is exactly the failure open-pr must "
            "not paper over: implement/peer-review produced no committed change. "
            f"Build the change, or `coga block --task {slug}`."
        )

    # --- refuse material stale-branch drift ---------------------------------
    # Task-step and audit-log sync advances the control branch between agent
    # steps. The shared preflight permits only non-overlapping generated state;
    # any source/docs/config or overlapping drift remains a hard failure.
    freshness = check_branch_contains_control(
        remote,
        base,
        cwd=cwd,
        coga_root=cfg.repo_root,
        head=head_ref,
    )
    if not freshness.ok:
        stranded_detail = _stranded_ticket_detail(
            freshness.overlaps,
            base=base,
            branch=branch,
            head_ref=head_ref,
            cwd=cwd,
            worktree=worktree,
            blackboard_path=blackboard_path,
        )
        if stranded_detail is not None:
            raise OpenPrError(
                f"Branch {branch!r} is not safe to publish. {stranded_detail} "
                f"Reconcile it and relaunch, or `coga block --task {slug}`."
            )
        raise OpenPrError(
            f"Branch {branch!r} is not safe to publish. {freshness.detail} "
            f"Reconcile it and relaunch, or `coga block --task {slug}`."
        )
    if freshness.value == "state-only-drift":
        # Diagnostics go to stderr: stdout is the value channel and must carry
        # the PR URL alone, so `$(coga open-pr <slug>)` stays parsable.
        sys.stderr.write(f"[open-pr] {freshness.detail}\n")

    # `gh` is optional at init, so the PR step owns the point-of-need check.
    # Run it before pushing: a missing or logged-out CLI should produce the
    # actionable preflight hint without leaving a remote branch behind first.
    remote_url = _git(["remote", "get-url", remote], cwd=cwd)
    host = (
        _remote_host(remote_url.stdout.strip())
        if remote_url.returncode == 0
        else None
    )
    gh_auth = check_gh_auth(host)
    if not gh_auth.ok:
        raise OpenPrError(gh_auth.detail)

    head_oid, diff_base, changes = _publication_diff(cwd, head_ref, f"{remote}/{base}")
    title, body = _pr_presentation(
        ticket, blackboard, above, slug, head=head_oid, base=diff_base, changes=changes,
    )
    existing = _open_pr_url(branch, cwd)
    legacy_title = ticket.title or slug
    if existing is not None:
        _refresh_body(existing, title, body, base, legacy_title)  # Refuse conflicts before pushing.

    # --- push ----------------------------------------------------------------
    # A previous open-pr attempt may have pushed before `gh` failed. If the
    # operator then rebases as instructed, an ordinary retry is non-fast-forward.
    # Use an explicit lease against the OID observed immediately before push:
    # rewritten local history is publishable, but concurrent remote updates are
    # still rejected instead of overwritten.
    if _git(["rev-parse", head_ref], cwd=cwd).stdout.strip() != head_oid:
        raise OpenPrError("PR presentation: feature branch changed during preparation; retry.")
    remote_oid = _remote_branch_oid(remote, branch, cwd=cwd)
    push_args = ["push", "-u"]
    if remote_oid:
        push_args.append(
            f"--force-with-lease=refs/heads/{branch}:{remote_oid}"
        )
    push_args.extend([remote, branch])
    push = _git(push_args, cwd=cwd)
    if push.returncode != 0:
        hint = check_git_auth(remote).detail
        rendered = " ".join(push_args)
        raise OpenPrError(
            f"`git {rendered}` failed: "
            f"{push.stderr.strip() or 'no output'}\n{hint}"
        )

    if _git(["rev-parse", head_ref], cwd=cwd).stdout.strip() != head_oid:
        raise OpenPrError("PR presentation: feature branch changed during push; retry before publishing.")

    # --- open or ready the PR ------------------------------------------------
    latest = _open_pr_url(branch, cwd)
    if existing is not None and latest is None:
        raise OpenPrError("PR presentation: existing PR became unavailable after push; retry before publishing.")
    existing = latest
    if existing is not None:
        url = existing["url"]
        refreshed = _refresh_body(existing, title, body, base, legacy_title)
        if (existing.get("title"), existing.get("body")) != (title, refreshed):
            edit = _write_pr(["gh", "pr", "edit", url], title, refreshed, cwd=cwd)
            if edit.returncode:
                raise OpenPrError(f"PR presentation: gh pr edit failed: {edit.stderr.strip() or 'no output'}")
        if existing.get("isDraft"):
            ready = _run(["gh", "pr", "ready", url], cwd=cwd)
            if ready.returncode != 0:
                raise OpenPrError(
                    f"`gh pr ready {url}` failed: {ready.stderr.strip() or 'no output'}"
                )
    else:
        create = _write_pr(
            ["gh", "pr", "create", "--base", base, "--head", branch],
            title, body, cwd=cwd,
        )
        if create.returncode != 0:
            stderr = create.stderr.strip()
            hint = ""
            # Attach the github_preflight setup hint only when it looks like auth.
            if "auth" in stderr.lower() or "logged" in stderr.lower():
                remote_url = check_git_remote(remote).value
                hint = "\n" + check_gh_auth(_remote_host(remote_url)).detail
            raise OpenPrError(f"`gh pr create` failed: {stderr or 'no output'}{hint}")
        url = create.stdout.strip().splitlines()[-1].strip() if create.stdout.strip() else ""
        if not url:
            raise OpenPrError("`gh pr create` succeeded but returned no PR URL to record.")

    # --- record pr: back under ## Dev ---------------------------------------
    # RE-READ the live blackboard region: the step's `coga bump` renders the
    # whole ticket right after we return, so use the barrier-held byte-spliced
    # update: it leaves frontmatter + body untouched and cannot cross child
    # admission.
    try:
        update_blackboard_under_barrier(
            cfg,
            blackboard_path,
            lambda current: (
                None
                if parse_pr_url(current) == url
                else set_dev_pr(current, url)
            ),
        )
    except GitError as exc:
        raise OpenPrError(f"could not serialize the PR record: {exc}") from exc
    if already and already != url:
        # Not an error — record it so a stale link replacement is visible in
        # logs, off the value channel (see the stderr note above).
        sys.stderr.write(
            f"[open-pr] note: replaced a stale pr: line ({already}) with {url}\n"
        )
    return url


def run_open_pr_recipe(cfg: Config, argv: list[str]) -> int:
    """`coga run open-pr <task>` — resolve the target, gate, publish, print URL.

    Resolves the task from ordinary recipe argv, then applies the checkout gate
    before touching git or `gh`: the command runs from the launch checkout on
    the control branch, which holds the authoritative ticket, and pushes the
    `## Dev` branch by name (from inside a recorded sandbox clone when there is
    one). Every code step returns the checkout to the control branch before
    its handoff (`dev/checkouts`), so no feature-branch mode exists.

    Stdout carries the bare PR URL and nothing else; every refusal goes to
    stderr and returns 2, so nothing advances and the open-pr step's
    `requires: pr` bump gate stays unmet.
    """
    if len(argv) != 1 or not argv[0].strip():
        sys.stderr.write(
            "Usage: coga run open-pr <task> (= coga open-pr <task>) — exactly "
            f"one task ref is required (got {len(argv)}).\n"
        )
        return 2
    task = argv[0].strip()

    try:
        ref = resolve_task(cfg, task)
    except TaskNotFoundError as exc:
        return _fail(str(exc))

    # read_ticket validates the ticket resolves before we touch git/gh.
    read_ticket(ref)

    reason = _checkout_mode(cfg)
    if reason is not None:
        return _fail(reason)

    try:
        url = open_pr(cfg, slug=ref.id_slug, blackboard_path=ref.ticket_path)
    except OpenPrError as exc:
        return _fail(str(exc))

    sys.stdout.write(f"{url}\n")
    return 0


def _checkout_mode(cfg: Config) -> str | None:
    """The checkout gate: a refusal unless this checkout is on control.

    Task resolution and the `pr:` write stay on the control branch, where the
    live ticket is; a feature branch's ticket copy is stale by construction.
    """
    result = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=str(cfg.repo_root))
    branch = result.stdout.strip() if result.returncode == 0 else ""
    if branch == cfg.git_control_branch:
        return None
    actual = branch or "<unknown>"
    return (
        "`coga open-pr` must run from the launch checkout on "
        f"{cfg.git_control_branch!r}, not branch {actual!r}. Return to "
        f"{cfg.git_control_branch!r} (`dev/checkouts`, end of step) and rerun "
        "it; the command pushes the recorded feature branch by name."
    )


def _fail(msg: str) -> int:
    sys.stderr.write(f"{msg}\n")
    return 2


__all__ = [
    "OpenPrError",
    "open_pr",
    "run_open_pr_recipe",
    "same_git_checkout",
    "set_dev_pr",
]
