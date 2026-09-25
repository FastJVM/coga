"""Git/GitHub auth preflight probes for `coga validate --check-github`.

Opt-in only: nothing here runs unless the explicit `--check-github` flag is
passed. The probes shell out to the standard tools the operator already uses —
`git` (with their configured remote, `ssh-agent`, and credential helpers) and
the `gh` CLI (with their `gh auth login` state). Coga does **not** read
`GITHUB_TOKEN`, store a GitHub PAT, run an OAuth flow, or reimplement GitHub
auth. The point is narrow: turn a raw tool failure that would otherwise
surprise an agent at PR time into an actionable setup hint a new operator can
act on before launch.

Each probe returns a structured `CheckResult`; `coga.validate` maps the
failures into report `Issue`s. The push probe is a non-mutating dry run and
runs non-interactively (`GIT_TERMINAL_PROMPT=0` plus ssh `BatchMode=yes`) so a
missing credential can never hang the check on a hidden password prompt. The
branch-freshness probe deliberately runs in the same explicit preflight. It
rejects missing material control-branch changes while accepting visible,
non-overlapping task/log state drift that Coga itself generates between steps.

This module also owns the one other branch-versus-control comparison Coga
makes: `stranded_task_state_paths`, which tells a ticket write committed on a
feature branch that control never received apart from ordinary staleness.
`coga open-pr` uses it to word its freshness refusal correctly and `coga bump`
to warn one step earlier; both read the same three-state answer.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

# Wall-clock ceiling for any single probe. The push probe talks to the network;
# the rest are local, but a uniform timeout keeps a wedged subprocess
# from stalling the whole check.
_PROBE_TIMEOUT = 20.0
_PREFLIGHT_BRANCH = "refs/heads/coga-preflight-auth-check"


@dataclass
class CheckResult:
    """Outcome of one preflight probe.

    `name` is a stable kind tag (`git-remote`, `git-auth`, `gh-installed`,
    `gh-auth`); `ok` is the pass/fail; `detail` is a human-readable success
    note or an actionable setup hint. `overlaps` is filled only by the
    branch-freshness probe: the paths changed on both sides of the fork that it
    refused as unsafe, so a caller can tell a refusal caused by its own ticket
    file from ordinary source drift without re-deriving the comparison.
    """

    name: str
    ok: bool
    detail: str
    value: str | None = None
    overlaps: tuple[str, ...] = ()


def _run(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
) -> tuple[int | None, str, str]:
    """Run a subprocess capturing output.

    Returns `(returncode, stdout, stderr)`. `returncode` is `None` when the
    binary is missing or the probe timed out (with the reason in stderr), so
    callers can distinguish "tool absent" from "tool ran and failed".
    """
    run_env = {**os.environ, **env} if env else None
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
            timeout=_PROBE_TIMEOUT,
            env=run_env,
            cwd=cwd,
        )
    except FileNotFoundError:
        return None, "", "not found on PATH"
    except subprocess.TimeoutExpired:
        return None, "", f"timed out after {_PROBE_TIMEOUT:.0f}s"
    return proc.returncode, proc.stdout, proc.stderr


def _first_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def check_git_remote(remote: str) -> CheckResult:
    """Verify the configured git remote exists via `git remote get-url`."""
    rc, out, err = _run(["git", "remote", "get-url", remote])
    if rc is None:
        return CheckResult(
            "git-remote",
            False,
            f"`git` is not usable ({_first_line(err) or 'unknown error'}) — install git.",
        )
    if rc != 0:
        return CheckResult(
            "git-remote",
            False,
            f"git remote {remote!r} is not configured "
            f"(`git remote get-url {remote}` failed). Add it with "
            f"`git remote add {remote} <url>`, or point Coga at the right "
            f"remote via [git].remote in coga.toml.",
        )
    remote_url = _first_line(out)
    return CheckResult("git-remote", True, f"remote {remote!r} -> {remote_url}", remote_url)


def check_git_auth(remote: str) -> CheckResult:
    """Probe push auth for the configured remote, transport-neutral.

    Uses `git push --dry-run <remote>` so it exercises whatever transport
    the remote is configured with (SSH or HTTPS) through the operator's normal
    `ssh-agent` / credential-helper setup. Runs non-interactively so a missing
    credential fails fast instead of blocking on a prompt.
    """
    refspec = f"HEAD:{_PREFLIGHT_BRANCH}"
    rc, _out, err = _run(
        ["git", "push", "--dry-run", remote, refspec],
        env={
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o ConnectTimeout=10",
        },
    )
    if rc is None:
        return CheckResult(
            "git-auth",
            False,
            f"could not run the remote probe ({_first_line(err) or 'unknown error'}).",
        )
    if rc != 0:
        return CheckResult(
            "git-auth",
            False,
            f"could not authenticate push access for remote {remote!r} "
            f"(`git push --dry-run {remote} HEAD:{_PREFLIGHT_BRANCH}` failed: "
            f"{_first_line(err) or 'no output'}). "
            "Check that you are online and that the remote's transport is set "
            "up: for SSH, that your key is loaded (`ssh-add -l`) and authorized; "
            "for HTTPS, that a git credential helper has valid credentials; and "
            "that your GitHub account can push branches to this repository.",
        )
    return CheckResult("git-auth", True, f"remote {remote!r} push access authenticated")


def coga_root_prefix(coga_root: str | Path) -> tuple[str | None, str]:
    """Return the active Coga OS root relative to its git toplevel.

    Shared with the branch sweep, which classifies a branch's post-merge
    commits with the same generated-state carve-out this preflight applies to
    control-branch drift.
    """
    rc, out, err = _run(
        ["git", "rev-parse", "--show-prefix"], cwd=coga_root
    )
    if rc != 0:
        return None, _first_line(err) or "no output"
    return out.strip().strip("/"), ""


def is_coga_state_path(path: str, *, coga_prefix: str) -> bool:
    """True for task/audit state under the configured Coga OS root.

    This is the one definition of "generated Coga state" — `tasks/**` and the
    repo-global `log.md` — that both this preflight and the branch sweep read.
    """
    tasks = f"{coga_prefix}/tasks/" if coga_prefix else "tasks/"
    log = f"{coga_prefix}/log.md" if coga_prefix else "log.md"
    return path == log or path.startswith(tasks)


def _changed_paths(
    ref_a: str,
    ref_b: str,
    *,
    cwd: str | Path | None,
    paths: Iterable[str] = (),
) -> tuple[set[str] | None, str]:
    # Disable rename detection so both endpoints remain visible. Otherwise a
    # control-side task rename can look disjoint from a feature-side edit of
    # the old path and incorrectly pass the non-overlap gate.
    args = ["git", "diff", "--no-renames", "--name-only", ref_a, ref_b]
    selected = list(paths)
    if selected:
        args.extend(["--", *selected])
    rc, out, err = _run(args, cwd=cwd)
    if rc != 0:
        return None, _first_line(err) or "no output"
    return {line.strip() for line in out.splitlines() if line.strip()}, ""


def check_branch_contains_control(
    remote: str,
    control_branch: str,
    *,
    cwd: str | Path | None = None,
    coga_root: str | Path,
    head: str = "HEAD",
) -> CheckResult:
    """Verify `head` contains material control changes.

    Coga advances the control branch for task and audit-log state between agent
    steps. Missing only that generated state is safe when the feature branch did
    not touch the same files; source, documentation, config, mixed, or
    overlapping drift is a hard failure. `head` defaults to the checked-out
    branch; `coga open-pr` passes a fully qualified branch ref so it can check
    a branch by name from the control checkout.
    """
    # Fetch into the remote-tracking ref and read that, never the checkout-wide
    # `FETCH_HEAD` a concurrent Coga process may replace between the two steps.
    control_ref = f"refs/remotes/{remote}/{control_branch}"
    branch_label = "current branch" if head == "HEAD" else head
    rc, _out, err = _run(
        [
            "git",
            "fetch",
            remote,
            f"+refs/heads/{control_branch}:{control_ref}",
        ],
        cwd=cwd,
    )
    if rc is None:
        return CheckResult(
            "git-branch-current",
            False,
            f"could not fetch {remote}/{control_branch} "
            f"({_first_line(err) or 'unknown error'}).",
        )
    if rc != 0:
        return CheckResult(
            "git-branch-current",
            False,
            f"could not fetch {remote}/{control_branch} "
            f"(`git fetch {remote} {control_branch}` failed: "
            f"{_first_line(err) or 'no output'}).",
        )

    rc, _out, err = _run(
        ["git", "merge-base", "--is-ancestor", control_ref, head], cwd=cwd
    )
    if rc is None:
        return CheckResult(
            "git-branch-current",
            False,
            f"could not compare {head} with {remote}/{control_branch} "
            f"({_first_line(err) or 'unknown error'}).",
        )
    if rc == 0:
        return CheckResult(
            "git-branch-current",
            True,
            f"{head} contains latest {remote}/{control_branch}",
        )
    if rc != 1:
        return CheckResult(
            "git-branch-current",
            False,
            f"could not compare {head} with {remote}/{control_branch} "
            f"(`git merge-base --is-ancestor {control_ref} {head}` failed: "
            f"{_first_line(err) or 'no output'}).",
        )

    rc, out, err = _run(["git", "merge-base", control_ref, head], cwd=cwd)
    merge_base = _first_line(out)
    if rc != 0 or not merge_base:
        return CheckResult(
            "git-branch-current",
            False,
            f"could not find the merge base with {remote}/{control_branch} "
            f"({_first_line(err) or 'no output'}).",
        )

    control_paths, path_error = _changed_paths(merge_base, control_ref, cwd=cwd)
    if control_paths is None:
        return CheckResult(
            "git-branch-current",
            False,
            f"could not inspect changes on {remote}/{control_branch} ({path_error}).",
        )
    feature_paths, path_error = _changed_paths(merge_base, head, cwd=cwd)
    if feature_paths is None:
        return CheckResult(
            "git-branch-current",
            False,
            f"could not inspect changes on {branch_label} ({path_error}).",
        )

    coga_prefix, path_error = coga_root_prefix(coga_root)
    if coga_prefix is None:
        return CheckResult(
            "git-branch-current",
            False,
            f"could not locate the configured Coga OS in git ({path_error}).",
        )

    unsafe_overlaps = control_paths & feature_paths
    if (
        all(
            is_coga_state_path(path, coga_prefix=coga_prefix)
            for path in control_paths
        )
        and not unsafe_overlaps
    ):
        return CheckResult(
            "git-branch-current",
            True,
            f"{remote}/{control_branch} advanced only through non-overlapping "
            "Coga task/log state; branch is safe to publish",
            value="state-only-drift",
        )

    reason = ""
    if unsafe_overlaps:
        reason = f" Overlapping paths: {', '.join(sorted(unsafe_overlaps))}."
    return CheckResult(
        "git-branch-current",
        False,
        f"{branch_label} does not contain latest {remote}/{control_branch}. "
        f"Rebase or merge before opening a PR, e.g. "
        f"`git fetch {remote} {control_branch}` then `git rebase {remote}/{control_branch}`."
        f"{reason}",
        overlaps=tuple(sorted(unsafe_overlaps)),
    )


def _tree_blob(
    ref: str, path: str, *, cwd: str | Path | None
) -> tuple[str | None, bool]:
    """Return `(blob_oid, ok)` for `path` at `ref`; `(None, True)` when absent."""
    rc, out, _err = _run(["git", "ls-tree", ref, "--", path], cwd=cwd)
    if rc != 0:
        return None, False
    line = _first_line(out)
    if not line:
        return None, True
    fields = line.split(None, 3)
    if len(fields) < 3:
        return None, False
    return fields[2], True


def stranded_task_state_paths(
    control_ref: str,
    branch_ref: str,
    paths: Iterable[str],
    *,
    cwd: str | Path | None = None,
) -> tuple[str, ...] | None:
    """Return the `paths` whose committed branch content control never received.

    `paths` are task-state files relative to the checkout toplevel, and `cwd`
    must be that toplevel: git resolves a pathspec against the working
    directory, so a nested Coga OS root as `cwd` would silently match nothing.
    Both callers pass the ticket file of the task they are acting on, never
    all of `tasks/**`, because a branch may legitimately edit *other* tickets
    as implementation work. A
    path is stranded when the branch changed it since its merge base with
    `control_ref` and no commit on control's side of the fork ever carried the
    branch tip's exact blob at that path — the rule
    `git._refresh_committed_divergence_reason` applies before overlaying
    control state onto a feature checkout. That second conjunct is what
    separates a stranded write from supported staleness: a bump run from the
    feature checkout commits the ticket there *and* lands identical bytes on
    control, after which control advances past the branch copy. The branch is
    then behind, not carrying content control lacks, and this returns nothing
    for it. A path the branch deleted is stranded while control still has it.

    Returns `None` when the question could not be answered — a missing ref,
    an unusable `git`, a failed probe. Callers must treat that as unknown and
    stay silent, never read it as "nothing stranded" (the
    `git._worktree_holding_branch` / `_WORKTREES_UNKNOWN` precedent).

    Cost: one `merge-base`, one `diff --name-only`, then at most two probes per
    surviving path (`ls-tree` and a `log --find-object` over control's side of
    the fork) — 2 + 2·N subprocess calls, where both current callers pass N = 1.
    """
    candidates = [path for path in dict.fromkeys(paths) if path]
    if not candidates:
        return ()
    rc, out, _err = _run(["git", "merge-base", control_ref, branch_ref], cwd=cwd)
    merge_base = _first_line(out)
    if rc != 0 or not merge_base:
        return None
    changed, _error = _changed_paths(
        merge_base, branch_ref, cwd=cwd, paths=candidates
    )
    if changed is None:
        return None
    stranded: list[str] = []
    for path in candidates:
        if path not in changed:
            continue
        branch_blob, ok = _tree_blob(branch_ref, path, cwd=cwd)
        if not ok:
            return None
        if branch_blob is None:
            control_blob, ok = _tree_blob(control_ref, path, cwd=cwd)
            if not ok:
                return None
            if control_blob is not None:
                stranded.append(path)
            continue
        rc, out, _err = _run(
            [
                "git", "log", "--format=%H", "-1",
                f"--find-object={branch_blob}",
                f"{merge_base}..{control_ref}", "--", path,
            ],
            cwd=cwd,
        )
        if rc != 0:
            return None
        if not _first_line(out):
            stranded.append(path)
    return tuple(stranded)


def stranded_task_state_remediation(
    *,
    control_ref: str,
    branch_ref: str,
    paths: Iterable[str],
    checkout: str | None = None,
) -> str:
    """The one remediation both `open-pr` and `bump` print for a stranded write.

    The branch must stop carrying the ticket, and it must do so by restoring
    the *merge base's* copy, not control's: control keeps rewriting the ticket
    at every later transition, so a branch pinned to any control snapshot is
    stale again before the PR merges, whereas a branch that contributes no
    change to the path merges cleanly whatever control does next. A rebase is
    the wrong fix — replaying the stranded commit onto control is exactly the
    conflict this message exists to prevent.
    """
    listed = " ".join(sorted(paths))
    where = f" in {checkout}" if checkout else ""
    return (
        f"Inspect what the branch added{where} with "
        f"`git diff {control_ref} {branch_ref} -- {listed}` and preserve "
        "anything still needed in the primary checkout's ticket copy (the live "
        "one). Then drop the branch's copy by restoring the merge base's version "
        "and committing: "
        f"`git restore --staged --worktree --source=$(git merge-base "
        f"{control_ref} {branch_ref}) -- {listed} && git commit -m 'Drop "
        "stranded ticket write'`. Do not rebase "
        f"to fix this — replaying the stranded commit onto {control_ref} "
        "reproduces the conflict."
    )


def _remote_host(remote_url: str | None) -> str | None:
    """Return a hostname from common git remote URL forms."""
    if not remote_url:
        return None
    text = remote_url.strip()
    if "://" in text:
        parsed = urlparse(text)
        return parsed.hostname

    # SCP-like SSH remotes: git@github.com:org/repo.git or github.com:org/repo.git.
    left, sep, right = text.partition(":")
    if sep and "/" in right and "/" not in left:
        host = left.rsplit("@", 1)[-1].strip()
        return host or None

    return None


def check_gh_installed() -> CheckResult:
    """Verify the `gh` CLI is installed via `gh --version`."""
    rc, out, err = _run(["gh", "--version"])
    if rc is None:
        return CheckResult(
            "gh-installed",
            False,
            "`gh` (GitHub CLI) is not installed — install it from "
            "https://cli.github.com and run `gh auth login`.",
        )
    if rc != 0:
        return CheckResult(
            "gh-installed",
            False,
            f"`gh --version` failed ({_first_line(err) or _first_line(out) or 'no output'}) "
            "— reinstall the GitHub CLI.",
        )
    return CheckResult("gh-installed", True, _first_line(out) or "gh installed")


def check_gh_auth(host: str | None = None) -> CheckResult:
    """Verify `gh` is authenticated for the configured remote host."""
    args = ["gh", "auth", "status"]
    if host:
        args.extend(["--hostname", host])
    rc, out, err = _run(args)
    if rc is None:
        return CheckResult(
            "gh-auth",
            False,
            "`gh` (GitHub CLI) is not installed — install it and run "
            "`gh auth login`.",
        )
    if rc != 0:
        # `gh auth status` writes its report to stderr.
        login_hint = f"`gh auth login --hostname {host}`" if host else "`gh auth login`"
        target = f" for {host}" if host else ""
        return CheckResult(
            "gh-auth",
            False,
            f"`gh` is not authenticated{target} — run {login_hint}. "
            f"({_first_line(err) or _first_line(out) or 'gh auth status failed'})",
        )
    target = f" for {host}" if host else ""
    return CheckResult("gh-auth", True, f"gh authenticated{target}")


def run_preflight(
    remote: str,
    *,
    control_branch: str = "main",
    cwd: str | Path | None = None,
    coga_root: str | Path,
) -> list[CheckResult]:
    """Run the full preflight against the configured remote.

    Skips probes that can't be meaningful: reachability only runs when the
    remote exists, and gh auth only runs when gh is installed — so a missing
    remote or missing `gh` produces one clear hint, not a cascade.
    """
    results: list[CheckResult] = []

    remote_result = check_git_remote(remote)
    results.append(remote_result)
    if remote_result.ok:
        auth = check_git_auth(remote)
        results.append(auth)
        if auth.ok:
            results.append(
                check_branch_contains_control(
                    remote,
                    control_branch,
                    cwd=cwd,
                    coga_root=coga_root,
                )
            )

    gh_installed = check_gh_installed()
    results.append(gh_installed)
    if gh_installed.ok:
        results.append(check_gh_auth(_remote_host(remote_result.value)))

    return results
