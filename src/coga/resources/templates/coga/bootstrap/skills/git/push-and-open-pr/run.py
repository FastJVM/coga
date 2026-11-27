"""Push the ticket branch, open or reuse its PR, and advance the ticket."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from coga_edge.git_workflow import changed_paths, git_output, verify_reviewed_tree
from coga.repl_supervisor import SENTINEL_ENV, deferred_done_marker, emit_done_marker
from coga.blackboard import read_dev_fields, set_dev_fields
from coga.github_source import github_repository_identity
from coga.taskfile import TaskFileError, body_sections, read_blackboard, replace_blackboard, split_body
from coga.ticket import Ticket, TicketError


class OpenPrError(ValueError):
    """The current branch or GitHub PR cannot be used for this ticket."""


_STATUSES = {"passed", "failed", "pending", "not-run"}
_TITLE_LIMIT = 256
_BODY_LIMIT = 65536  # GitHub rejects longer PR bodies.
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
    head = git_output("rev-parse", head_ref, cwd=cwd)
    base = git_output("merge-base", base_ref, head, cwd=cwd)
    fields = git_output("diff", "--name-status", "-z", "--find-renames", base, head, cwd=cwd).split("\x00")
    changes: list[tuple[str, list[str]]] = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        count = 2 if status.startswith(("R", "C")) else 1
        changes.append((status, fields[i + 1:i + count + 1]))
        i += count + 1
    return head, base, changes


def _grouped_file_rows(changes: list[tuple[str, list[str]]]) -> list[str]:
    """One row per parent directory, with per-status counts, for oversized diffs."""
    groups: dict[str, dict[str, int]] = {}
    for status, names in changes:
        for path in names:
            parent = path.rsplit("/", 1)[0] + "/" if "/" in path else "./"
            counts = groups.setdefault(parent, {})
            counts[status] = counts.get(status, 0) + 1
    rows = []
    for parent in sorted(groups):
        counts = groups[parent]
        total = sum(counts.values())
        summary = ", ".join(f"{status}×{n}" for status, n in sorted(counts.items()))
        rows.append(f"| <code>{_cell(parent)}</code> | {total} ({summary}) |")
    return rows


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
    state_paths: tuple[str, ...] = (),
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
            if path not in state_paths and not files.get(path, "").strip():
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
    )

    def assemble(files_section: str) -> str:
        body = _pr_body(
            ticket, above, slug,
            content + files_section + "\n\n## Checks\n\n" + "\n\n".join(check_items),
        )
        marker = f"<!-- coga:pr:v1 title={_digest(title)} body={_digest(body)} -->\n"
        return marker + body + _MANAGED_END + "\n"

    full = assemble(
        "## Changed files\n\n| Path | Change |\n| --- | --- |\n" + "\n".join(file_rows)
    )
    if len(full) <= _BODY_LIMIT:
        return title, full
    # GitHub refuses the whole body past its limit. The per-path table is the
    # only part that grows with the diff and is recoverable from git, so it
    # alone is grouped; the literal ticket snapshot is never shortened.
    grouped = assemble(
        "## Changed files\n\n"
        f"Grouped by directory to fit GitHub's {_BODY_LIMIT}-character body limit; "
        f"`git diff --name-status {base}...{head}` lists every path.\n\n"
        "| Directory | Paths (by change) |\n| --- | --- |\n"
        + "\n".join(_grouped_file_rows(changes))
    )
    if len(grouped) > _BODY_LIMIT:
        raise OpenPrError(
            f"PR presentation: the generated body is {len(grouped)} characters even with "
            f"changed files grouped by directory; GitHub allows {_BODY_LIMIT}. Shorten the "
            "preparation prose or check receipts and rerun."
        )
    return title, grouped


def _digest(value: str) -> str:
    # Web-editor saves may change line endings without changing the prose.
    return hashlib.sha256(value.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _lookup_pr(branch: str, cwd: str, gh_env: dict[str, str]) -> dict | None:
    result = subprocess.run(
        ["gh", "pr", "view", branch, "--json", "url,state,isDraft,baseRefName"],
        cwd=cwd, env=gh_env, text=True, capture_output=True,
    )
    if result.returncode == 1 and not result.stdout.strip() and re.fullmatch(
        r'no pull requests found for branch ".+"', result.stderr.strip(),
    ):
        return None
    if result.returncode:
        raise OpenPrError(result.stderr.strip() or "GitHub PR lookup failed")
    data = json.loads(result.stdout)
    if (
        not isinstance(data, dict)
        or data.get("state") not in {"OPEN", "CLOSED", "MERGED"}
        or not isinstance(data.get("isDraft"), bool)
        or any(not isinstance(data.get(key), str) or not data[key] for key in ("url", "baseRefName"))
    ):
        raise OpenPrError("GitHub returned incomplete PR data")
    return data


def _create_pr(
    cwd: str, base: str, remote: str, branch: str, slug: str, path: Path, state_paths: tuple[str, ...],
    gh_env: dict[str, str],
) -> str:
    ticket = Ticket.parse(path.read_text(encoding="utf-8"))
    above, region = split_body(ticket.body)
    head, merge_base, changes = _publication_diff(cwd, "HEAD", f"refs/remotes/{remote}/{base}")
    prepared_head = _preparation(region, above).get("head")
    if isinstance(prepared_head, str) and prepared_head != head:
        try:
            verify_reviewed_tree(cwd, prepared_head, head, state_paths)
        except ValueError:
            pass  # Render the preparation as stale against the actual PR head.
        else:
            head = prepared_head
    title, body = _pr_presentation(
        ticket, region, above, slug, head=head, base=merge_base, changes=changes,
        state_paths=state_paths,
    )
    with tempfile.TemporaryDirectory(prefix="coga-pr-") as directory:
        body_path = Path(directory) / "body.md"
        body_path.write_text(body, encoding="utf-8", newline="\n")
        return subprocess.check_output(
            ["gh", "pr", "create", "--head", branch, "--base", base, "--title", title, "--body-file", str(body_path)],
            cwd=cwd, env=gh_env, text=True,
        ).strip()


def run() -> int:
    try:
        path = Path(os.environ["COGA_TASK_TICKET"]).resolve()
        slug = os.environ["COGA_TASK_SLUG"]
        coga_root = Path(os.environ["COGA_COGA_OS_ROOT"]).resolve()
        cwd = git_output("rev-parse", "--show-toplevel", cwd=str(path.parent))
        paths = tuple(p.relative_to(cwd).as_posix() for p in (path, coga_root / "log.md"))
        region = read_blackboard(path)
        fields = read_dev_fields(region)
        missing = {"branch", "remote", "base"} - fields.keys()
        if missing:
            raise OpenPrError("Missing ## Dev fields: " + ", ".join(sorted(missing)))
        expected_step = os.environ.get("COGA_TASK_STEP")
        if not expected_step:
            raise OpenPrError("Run this script from the ticket's PR step")
        if Ticket.read(path).step != expected_step and "pr" not in fields:
            raise OpenPrError(f"Expected the ticket at {expected_step} before opening its PR")
        branch, remote, base = (fields[key] for key in ("branch", "remote", "base"))
        current = git_output("branch", "--show-current", cwd=cwd)
        if current != branch:
            raise OpenPrError(f"Current branch {current!r} disagrees with recorded branch {branch!r}")
        # Ticket state lives on the base, never on the code branch: any
        # ticket's edit or the log is not this branch's work.
        tasks_prefix = (coga_root / "tasks").relative_to(cwd).as_posix() + "/"
        dirty = sorted(
            p for p in set(changed_paths(cwd)) - set(paths)
            if not p.startswith(tasks_prefix)
        )
        if dirty:
            raise OpenPrError("Commit your work first: " + ", ".join(dirty))
        push_urls = git_output("remote", "get-url", "--push", "--all", remote, cwd=cwd).splitlines()
        if len(push_urls) != 1:
            raise OpenPrError(f"Expected one push URL for {remote!r}")
        gh_env = dict(os.environ)
        repository = github_repository_identity(push_urls[0])
        if repository is not None:
            gh_env["GH_REPO"] = "/".join(repository)
        push = ["git", "push", "-u", "--", remote, "HEAD"]
        subprocess.run(push, cwd=cwd, check=True)
        existing = _lookup_pr(branch, cwd, gh_env)
        if existing is None:
            if fields.get("pr"):
                raise OpenPrError("Recorded PR was not found for the current branch")
            url = _create_pr(cwd, base, remote, branch, slug, path, paths, gh_env)
        else:
            url = existing["url"]
            if existing["state"] != "OPEN" or existing["baseRefName"] != base:
                raise OpenPrError(f"PR {url} is {existing['state']} with base {existing['baseRefName']!r}. Expected OPEN on {base!r}.")
        if fields.get("pr") and fields["pr"] != url:
            raise OpenPrError(f"PR {url} disagrees with the recorded PR {fields['pr']}")
        updated = set_dev_fields(read_blackboard(path), pr=url)
        if read_dev_fields(updated).get("pr") != url:
            raise OpenPrError(f"Expected a full PR URL, got {url!r}")
        if existing and existing["isDraft"]:
            subprocess.run(["gh", "pr", "ready", url], cwd=cwd, env=gh_env, check=True)
        replace_blackboard(path, updated)
        # Last action: the bump runs the workflow's `exit` script, which
        # switches the checkout to the base and publishes the ticket there.
        if Ticket.read(path).step == expected_step:
            subprocess.run(
                [sys.executable, "-m", "coga.cli", "bump", slug],
                cwd=cwd, env={**os.environ, SENTINEL_ENV: ""}, check=True,
            )
    except subprocess.CalledProcessError as exc:
        return exc.returncode if exc.returncode > 0 else 1
    except (OSError, ValueError, KeyError, TicketError, TaskFileError) as exc:
        print(f"push-and-open-pr: {exc}", file=sys.stderr)
        return 2
    return 0


def main() -> int:
    with deferred_done_marker():
        result = run()
        if result == 0:
            emit_done_marker(session_id=os.environ["COGA_TASK_SLUG"])
        return result


if __name__ == "__main__":
    raise SystemExit(main())
