"""Durable checkout-local intent for guarded audit deletions.

The receipt pins ordinary Git objects under a per-worktree ref. It is neither
an archive nor a distributed tombstone: it exists only until the transaction
is acknowledged or restored. Every publisher/checkout boundary honors it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from coga.atomicio import atomic_write_bytes, atomic_write_text
from coga.config import Config
from coga.logfile import LogMutation
from coga.paths import log_path

REF = "refs/worktree/coga/log-mutation"


def receipt_path(cfg: Config) -> Path | None:
    from coga import git
    root = git.toplevel(cfg.repo_root)
    if root is None:
        return None
    path = Path(git.run_git(root, "rev-parse", "--git-path", "coga-log-mutation.json").strip())
    return path if path.is_absolute() else root / path


def pending(cfg: Config) -> bool:
    path = receipt_path(cfg)
    return path is not None and path.exists()


def read(cfg: Config) -> dict | None:
    from coga import git
    path = receipt_path(cfg)
    if path is None or not path.exists():
        return None
    try:
        record = json.loads(path.read_bytes())
        if not isinstance(record, dict) or set(record) != {"base", "intent", "log", "removed", "paths", "attempts", "endings"}:
            raise ValueError
        revisions = [record["base"], record["intent"]]
        if not isinstance(record["attempts"], list):
            raise ValueError
        revisions.extend(record["attempts"])
        if any(not isinstance(oid, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid) for oid in revisions):
            raise ValueError
        paths = record["paths"]
        if (not isinstance(paths, list) or not paths
                or any(not isinstance(p, str) or Path(p).is_absolute() or ".." in Path(p).parts for p in paths)
                or paths != sorted(set(paths)) or record["log"] not in paths):
            raise ValueError
        removed = record["removed"]
        if (not isinstance(removed, list) or any(type(i) is not int or i < 0 for i in removed)
                or len(set(removed)) != len(removed)):
            raise ValueError
        endings = record["endings"]
        if not isinstance(endings, dict) or set(endings) != set(paths):
            raise ValueError
        for pair in endings.values():
            if not isinstance(pair, list) or len(pair) != 2:
                raise ValueError
            for indices in pair:
                if (not isinstance(indices, list) or any(type(i) is not int or i < 0 for i in indices)
                        or indices != sorted(set(indices))):
                    raise ValueError
        return record
    except (ValueError, TypeError, OSError) as exc:
        raise git.UncertainPublishError("invalid pending audit mutation receipt; preserve it and repair before publishing") from exc


def ensure_clear(cfg: Config, mutation: LogMutation | None = None) -> None:
    from coga import git
    record = read(cfg)
    if record is None:
        return
    root = git.toplevel(cfg.repo_root)
    if mutation is not None and (
        git._clean_bytes(root, mutation.preimage, record["log"]) == git.tree_bytes(root, record["base"], record["log"])
        and list(mutation.removed) == record["removed"]
    ):
        return
    raise git.UncertainPublishError(
        "pending audit mutation: publication and checkout return are withheld; "
        "rerun the trim-log script with the compatible wheel to recover, then retry (exit 75)"
    )


def begin(cfg: Config, base: str, mutation: LogMutation, outputs: dict[Path, bytes], message: str) -> None:
    from coga import git
    with git.state_lock(cfg):
        ensure_clear(cfg)
        root = git.toplevel(cfg.repo_root)
        assert root is not None
        rel = git.relative_to_root(root, log_path(cfg))
        if git.tree_bytes(root, base, rel) != git._clean_bytes(root, mutation.preimage, rel):
            raise git.StateRegressionError("audit preimage is not archived on the pinned control revision")
        working = {git.relative_to_root(root, p): data for p, data in outputs.items()}
        working[rel] = mutation.postimage
        endings = {}
        for name, after in working.items():
            before = (root / name).read_bytes() if (root / name).exists() else b""
            # Native CRLF clean conversion is supported without storing a
            # second copy of the history. Other content filters cannot supply
            # a byte-exact reconstructible receipt and are refused.
            for raw in (before, after):
                if git._clean_bytes(root, raw, name) != raw.replace(b"\r\n", b"\n"):
                    raise git.StateRegressionError(f"{name}: custom clean filter is incompatible with guarded audit replacement")
            endings[name] = [[i for i, line in enumerate(raw.split(b"\n")[:-1]) if line.endswith(b"\r")]
                             for raw in (before, after)]
        tree = git._build_tree(root, base, list(working), working, set(), base, dict(working))
        intent = git.run_git(root, "commit-tree", tree, "-p", base, "-m", message).strip()
        git.run_git(root, "update-ref", REF, intent)
        record = {"base": base, "intent": intent, "log": rel, "removed": list(mutation.removed),
                  "paths": sorted(working), "attempts": [], "endings": endings}
        atomic_write_text(receipt_path(cfg), json.dumps(record) + "\n")


def attempted(cfg: Config, commit: str) -> None:
    from coga import git
    with git.state_lock(cfg):
        record = read(cfg)
        if record is None:
            return
        root = git.toplevel(cfg.repo_root)
        assert root is not None
        previous = git.run_git(root, "rev-parse", REF).strip()
        if commit != previous:
            # A JSON OID is not a Git reachability root. Keep the original
            # intent and every attempted commit reachable before recording
            # an attempt that the publisher may send to the remote.
            tree = git.run_git(root, "rev-parse", f"{record['intent']}^{{tree}}").strip()
            pinned = git.run_git(
                root, "commit-tree", tree, "-p", previous, "-p", commit,
                "-m", "Log: recurring/trim-log — pin publication attempt",
            ).strip()
            git.run_git(root, "update-ref", REF, pinned, previous)
        record["attempts"].append(commit)
        atomic_write_text(receipt_path(cfg), json.dumps(record) + "\n")


def _is_ancestor(root: Path, old: str, new: str) -> bool:
    """A failed inspection cannot authorize rolling back an accepted trim."""
    from coga import git
    result = git._run(["git", "-C", str(root), "merge-base", "--is-ancestor", old, new])
    if result.returncode not in (0, 1):
        raise git.UncertainPublishError(
            "cannot verify audit publication ancestry; preserve the receipt and retry: "
            + git.summarize_git_failure(result.stderr.decode(errors="replace"))
        )
    return result.returncode == 0


def finish(cfg: Config) -> None:
    from coga import git
    path = receipt_path(cfg)
    if path is not None:
        path.unlink(missing_ok=True)
        root = git.toplevel(cfg.repo_root)
        git.run_git(root, "update-ref", "-d", REF)


def recover(cfg: Config) -> str | None:
    """Resolve an interrupted attempt against freshly fetched control.

    Accepted-but-unacknowledged: install current control plus later local
    appends. Definitely unpublished: restore preimages plus those appends.
    Unknown or modified output: preserve the receipt and refuse. Restore log
    first, then cursor; a migrated cursor also works on the untrimmed log.
    """
    from coga import git
    from coga.log_publication import reconcile

    with git.state_lock(cfg):
        record = read(cfg)
        if record is None:
            return None
        root = git.toplevel(cfg.repo_root)
        assert root is not None
        control = git.fetch_control(cfg, root)  # failure leaves all evidence
        if not _is_ancestor(root, record["base"], control):
            raise git.UncertainPublishError("control history changed during audit recovery; preserve the receipt and reconcile")
        accepted = any(_is_ancestor(root, commit, control) for commit in record["attempts"])
        replacements: dict[str, bytes | None] = {}
        for rel in record["paths"]:
            before = git.tree_bytes(root, record["base"], rel)
            after = git.tree_bytes(root, record["intent"], rel)
            def restore_ends(data: bytes | None, indices: list[int]) -> bytes | None:
                if data is None:
                    return None
                parts = data.split(b"\n")
                for i in indices:
                    if i >= len(parts) - 1:
                        raise git.UncertainPublishError("invalid audit receipt line endings")
                    parts[i] += b"\r"
                return b"\n".join(parts)
            before = restore_ends(before, record["endings"][rel][0])
            after = restore_ends(after, record["endings"][rel][1])
            current = (root / rel).read_bytes() if (root / rel).exists() else None
            if rel == record["log"]:
                if current is not None and current.startswith(before or b""):
                    tail = current[len(before or b""):]
                elif current is not None and current.startswith(after or b""):
                    tail = current[len(after or b""):]
                else:
                    raise git.UncertainPublishError("audit output changed during recovery; retain receipt and reconcile the local log")
                if accepted:
                    source = (after or b"") + tail
                    merged = reconcile(cfg, root, control, source)
                    replacements[rel] = (source if git._clean_bytes(root, source, rel) == merged
                                         else merged)
                else:
                    replacements[rel] = (before or b"") + tail
            elif current == before or current == after:
                target = git.tree_bytes(root, control, rel) if accepted else before
                if accepted and after is not None and git._clean_bytes(root, after, rel) == target:
                    target = after
                replacements[rel] = target
            else:
                raise git.UncertainPublishError(f"{rel}: changed during audit recovery; preserve the cursor and reconcile explicitly")
        # Verify every output before changing either file.
        ordered = [record["log"], *(p for p in record["paths"] if p != record["log"])]
        for rel in ordered:
            data = replacements[rel]
            if data is None:
                (root / rel).unlink(missing_ok=True)
            else:
                atomic_write_bytes(root / rel, data)
        finish(cfg)
        return "accepted" if accepted else "restored"
