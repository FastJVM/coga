"""Human-review PRs for ambiguous lifecycle status conflicts.

When a lifecycle command's preparation (`git.prepare_ticket`) finds that this
checkout and control both changed a ticket's `status:` and the lifecycle
ordering cannot pick a winner, the operation stays unapplied and a human
decides. This module opens (or finds) the PR that asks for that decision:

- The conflict is identified by its ticket path plus the base, local, and
  control blob ids. That key names the review branch, so every checkout
  that meets the same conflict finds the same PR.
- The branch is rooted at the control commit that introduced the shared
  base and carries this checkout's ticket, built in an isolated index and
  pushed by object id. It is pushed only when the remote branch is absent,
  so a human's edits on it are never overwritten.
- The PR targets configured control and has no implementation linkage: no
  `Closes ticket:` footer, and the ticket's `## Dev` is never touched.
- A merged PR is the resolution. `.coga/human-review.json` remembers each PR
  this checkout opened so a later preparation can adopt control's resolved
  copy and merge edits made after the PR was created
  (`git.prepare_ticket(..., review_base=)`).

Every GitHub call goes through `_gh`. Any GitHub, auth, network, or Git
write failure leaves the local refusal standing and is reported as "no
review PR was created". `coga/state-publication` ("Human review of status
conflicts") owns the user contract.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from coga import git
from coga.config import Config

TITLE_PREFIX = "Human Review needed"
BRANCH_PREFIX = "coga/human-review/"
# GitHub rejects PR bodies over 65536 characters; three ticket copies share it.
_VERSION_LIMIT = 18_000
_RECORD_FILE = Path(".coga") / "human-review.json"


class ReviewUnavailable(Exception):
    """GitHub or Git could not create or look up the review PR."""


@dataclass(frozen=True)
class ReviewOutcome:
    """What escalation found or did.

    `state` is `created` (a new PR), `open` (an existing open PR reused),
    `merged` (a human already resolved this exact conflict), `closed` (the
    PR was closed unmerged: refuse without a new one), or `unavailable`
    (no PR exists or was created; `detail` says why).
    """

    state: Literal["created", "open", "merged", "closed", "unavailable"]
    url: str | None = None
    detail: str = ""


def title(slug: str) -> str:
    return f"{TITLE_PREFIX}: {slug} — lifecycle merge conflict"


def is_review_title(text: str) -> bool:
    """Whether a PR title marks a human-review PR automation must leave alone."""
    return text.strip().startswith(TITLE_PREFIX)


def fingerprint(conflict: git.StatusConflict) -> str:
    """The conflict key: ticket path plus base/local/control blob ids."""
    key = "\0".join(
        (conflict.rel, conflict.base_oid, conflict.local_oid, conflict.control_oid)
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def branch_name(slug: str, key: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._/-]+", "-", slug).strip("/-") or "ticket"
    return f"{BRANCH_PREFIX}{safe}-{key[:12]}"


def _gh(args: list[str], *, cwd: Path, stdin: str | None = None) -> str:
    """Run one `gh` command; the only GitHub boundary in this module."""
    try:
        result = subprocess.run(
            ["gh", *args], cwd=cwd, input=stdin, capture_output=True,
            text=True, encoding="utf-8", check=False,
        )
    except FileNotFoundError as exc:
        raise ReviewUnavailable("`gh` not found on PATH") from exc
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "no output"
        raise ReviewUnavailable(
            f"`gh {' '.join(args[:2])}` failed (exit {result.returncode}): {detail}"
        )
    return result.stdout


def _prs_for_branch(root: Path, branch: str) -> list[dict[str, Any]]:
    out = _gh(
        ["pr", "list", "--head", branch, "--state", "all",
         "--json", "number,url,state,title"],
        cwd=root,
    )
    try:
        data = json.loads(out or "[]")
    except json.JSONDecodeError as exc:
        raise ReviewUnavailable(f"`gh pr list --head {branch}` returned non-JSON: {exc}") from exc
    if not isinstance(data, list):
        raise ReviewUnavailable(f"`gh pr list --head {branch}` returned unexpected JSON")
    return [item for item in data if isinstance(item, dict)]


def _pr_state(root: Path, url: str) -> str:
    out = _gh(["pr", "view", url, "--json", "state"], cwd=root)
    try:
        return str(json.loads(out).get("state", "")).upper()
    except (json.JSONDecodeError, AttributeError) as exc:
        raise ReviewUnavailable(f"`gh pr view {url}` returned unexpected JSON") from exc


def _classify(prs: list[dict[str, Any]]) -> ReviewOutcome | None:
    """The outcome an existing PR for this branch dictates, newest state first."""
    by_state: dict[str, dict[str, Any]] = {}
    for pr in prs:
        by_state.setdefault(str(pr.get("state", "")).upper(), pr)
    for state, outcome in (("OPEN", "open"), ("MERGED", "merged"), ("CLOSED", "closed")):
        if state in by_state:
            return ReviewOutcome(outcome, url=str(by_state[state].get("url", "")) or None)
    return None


# --- records ------------------------------------------------------------------


def _load(cfg: Config) -> dict[str, list[dict[str, Any]]]:
    try:
        data = json.loads((cfg.repo_root / _RECORD_FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"[review] note: ignoring unreadable {_RECORD_FILE}: {exc}\n")
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        rel: [entry for entry in entries if isinstance(entry, dict)]
        for rel, entries in data.items() if isinstance(entries, list)
    }


def _save(cfg: Config, records: dict[str, list[dict[str, Any]]]) -> None:
    from coga.atomicio import atomic_write_text

    records = {rel: entries for rel, entries in records.items() if entries}
    path = cfg.repo_root / _RECORD_FILE
    try:
        if not records:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, json.dumps(records, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        sys.stderr.write(f"[review] note: could not record human-review PRs: {exc}\n")


def _remember(cfg: Config, conflict: git.StatusConflict, key: str, url: str) -> None:
    records = _load(cfg)
    entries = [e for e in records.get(conflict.rel, []) if e.get("fingerprint") != key]
    entries.append({
        "fingerprint": key, "url": url,
        "base": conflict.base_oid, "local": conflict.local_oid,
        "control": conflict.control_oid,
    })
    records[conflict.rel] = entries
    _save(cfg, records)


def forget(cfg: Config, rel: str, key: str | None = None) -> None:
    """Drop this checkout's record of one review PR (or all of `rel`'s)."""
    records = _load(cfg)
    if rel not in records:
        return
    records[rel] = [] if key is None else [
        e for e in records[rel] if e.get("fingerprint") != key
    ]
    _save(cfg, records)


def has_records(cfg: Config) -> bool:
    """Whether this checkout remembers any review PR (no Git or GitHub call)."""
    return (cfg.repo_root / _RECORD_FILE).exists()


def recorded(cfg: Config, rel: str) -> list[dict[str, Any]]:
    """This checkout's remembered review PRs for `rel`, oldest first."""
    return list(_load(cfg).get(rel, []))


def merged_record(cfg: Config, rel: str) -> dict[str, Any] | None:
    """The newest remembered review PR for `rel` that a human merged.

    A PR still open or closed stays remembered; an unreachable GitHub is
    reported and treated as "not known to be merged", so preparation runs
    as usual and refuses again if the conflict remains.
    """
    entries = recorded(cfg, rel)
    if not entries:
        return None
    root = git.toplevel(cfg.repo_root)
    if root is None:
        return None
    for entry in reversed(entries):
        url = str(entry.get("url", ""))
        if not url or not entry.get("local"):
            continue
        try:
            state = _pr_state(root, url)
        except ReviewUnavailable as exc:
            sys.stderr.write(f"[review] could not check human-review PR {url}: {exc}\n")
            return None
        if state == "MERGED":
            return entry
    return None


# --- escalation ---------------------------------------------------------------


def escalate(cfg: Config, slug: str, conflict: git.StatusConflict) -> ReviewOutcome:
    """Find or open the human-review PR for `conflict`; never raises."""
    key = fingerprint(conflict)
    branch = branch_name(slug, key)
    try:
        existing = _classify(_prs_for_branch(conflict.root, branch))
        if existing is not None:
            if existing.state == "open" and existing.url:
                _remember(cfg, conflict, key, existing.url)
            return existing
        if conflict.provenance is None:
            raise ReviewUnavailable(
                "no control commit introducing the shared base was found to root the branch"
            )
        if not _remote_branch_exists(cfg, conflict.root, branch):
            _push_review_branch(cfg, conflict, branch, slug)
        url = _gh(
            ["pr", "create", "--base", cfg.git_control_branch, "--head", branch,
             "--title", title(slug), "--body-file", "-"],
            cwd=conflict.root, stdin=pr_body(cfg, slug, conflict, branch),
        ).strip().splitlines()
        if not url:
            raise ReviewUnavailable("`gh pr create` printed no PR URL")
    except (ReviewUnavailable, git.GitError) as exc:
        return ReviewOutcome("unavailable", detail=str(exc))
    _remember(cfg, conflict, key, url[-1].strip())
    return ReviewOutcome("created", url=url[-1].strip())


def _remote_branch_exists(cfg: Config, root: Path, branch: str) -> bool:
    out = git.run_git(
        root, "ls-remote", "--heads", cfg.git_remote, f"refs/heads/{branch}",
    )
    return bool(out.strip())


def _push_review_branch(
    cfg: Config, conflict: git.StatusConflict, branch: str, slug: str,
) -> str:
    """Commit the local ticket onto the provenance commit and push it."""
    root, rel = conflict.root, conflict.rel
    assert conflict.provenance is not None
    fd, index = tempfile.mkstemp(prefix="coga-review-index-")
    os.close(fd)
    os.unlink(index)
    env = {"GIT_INDEX_FILE": index}
    try:
        git.run_git(root, "read-tree", conflict.provenance, env=env)
        blob = git._hash_blob(root, conflict.local, rel)
        git.run_git(
            root, "update-index", "--add", "--cacheinfo", "100644", blob, rel, env=env,
        )
        tree = git.run_git(root, "write-tree", env=env).strip()
    finally:
        try:
            os.unlink(index)
        except FileNotFoundError:
            pass
    commit = git.run_git(
        root, "commit-tree", tree, "-p", conflict.provenance,
        "-m", f"{title(slug)}\n\nThis checkout's copy of {rel}, rooted at the "
        "last copy it shared with control.",
    ).strip()
    git.run_git(root, "push", "--quiet", cfg.git_remote, f"{commit}:refs/heads/{branch}")
    return commit


def pr_body(cfg: Config, slug: str, conflict: git.StatusConflict, branch: str) -> str:
    control = f"{cfg.git_remote}/{cfg.git_control_branch}"
    lines = [
        f"Coga refused a lifecycle command on `{slug}` (`{conflict.rel}`): this "
        "checkout and control both changed its status, and the lifecycle "
        "ordering cannot say which stands. The command was not applied.",
        "",
        f"This branch (`{branch}`) holds this checkout's copy, rooted at "
        f"`{conflict.provenance}`, the last copy it shared with `{control}`; "
        "merging it into control shows the real conflict.",
        "",
        "**For the human reviewer:** resolve the ticket to the copy that should "
        "stand and merge, or close this PR to keep control's copy. Coga's "
        "conflict-resolution and PR-comment automation leaves this PR alone. "
        "After a merge, the next lifecycle command in the refusing checkout "
        "adopts the resolution and merges any later local edits onto it; after "
        "a close, it keeps refusing until that checkout takes control's copy.",
        "",
        "## Conflicting fields",
        "",
        *[f"- {field}" for field in conflict.fields],
        "",
        f"Conflict key: `{fingerprint(conflict)}` (path plus base `{conflict.base_oid}`, "
        f"local `{conflict.local_oid}`, control `{conflict.control_oid}` at "
        f"`{conflict.revision}`).",
    ]
    for label, data in (
        ("Base (last shared copy)", conflict.base),
        ("Local (this checkout)", conflict.local),
        ("Control", conflict.control),
    ):
        text = data.decode("utf-8", errors="replace")
        note = ""
        if len(text) > _VERSION_LIMIT:
            text = text[:_VERSION_LIMIT]
            note = f"\n_(truncated to {_VERSION_LIMIT} characters)_\n"
        fence = "````"
        while fence in text:
            fence += "`"
        lines += ["", f"## {label}", "", f"{fence}markdown", text.rstrip("\n"), fence + note]
    return "\n".join(lines) + "\n"


def report(outcome: ReviewOutcome) -> str:
    """The operator-facing sentence for an escalation outcome."""
    if outcome.state == "created":
        return f"Opened human-review PR {outcome.url}; a human must resolve it."
    if outcome.state == "open":
        return f"Human-review PR {outcome.url} is still open; a human must resolve it."
    if outcome.state == "closed":
        return (
            f"Human-review PR {outcome.url} was closed unmerged; no new PR was opened. "
            "Take control's copy and redo the edit"
        )
    if outcome.state == "merged":
        return f"Human-review PR {outcome.url} was merged."
    return f"No human-review PR was created: {outcome.detail}"
