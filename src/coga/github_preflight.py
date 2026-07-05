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
branch-freshness probe deliberately runs in the same explicit preflight: opening
a PR from a branch that predates the control branch can leave ticket state stale
even when auth is fine.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
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
    note or an actionable setup hint.
    """

    name: str
    ok: bool
    detail: str
    value: str | None = None


def _run(args: list[str], *, env: dict[str, str] | None = None) -> tuple[int | None, str, str]:
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


def check_branch_contains_control(remote: str, control_branch: str) -> CheckResult:
    """Verify the current branch contains the latest configured control branch."""
    rc, _out, err = _run(["git", "fetch", remote, control_branch])
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

    rc, _out, err = _run(["git", "merge-base", "--is-ancestor", "FETCH_HEAD", "HEAD"])
    if rc is None:
        return CheckResult(
            "git-branch-current",
            False,
            f"could not compare HEAD with {remote}/{control_branch} "
            f"({_first_line(err) or 'unknown error'}).",
        )
    if rc == 0:
        return CheckResult(
            "git-branch-current",
            True,
            f"HEAD contains latest {remote}/{control_branch}",
        )
    if rc == 1:
        return CheckResult(
            "git-branch-current",
            False,
            f"current branch does not contain latest {remote}/{control_branch}. "
            f"Rebase or merge before opening a PR, e.g. "
            f"`git fetch {remote} {control_branch}` then `git rebase FETCH_HEAD`.",
        )
    return CheckResult(
        "git-branch-current",
        False,
        f"could not compare HEAD with {remote}/{control_branch} "
        f"(`git merge-base --is-ancestor FETCH_HEAD HEAD` failed: "
        f"{_first_line(err) or 'no output'}).",
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


def run_preflight(remote: str, *, control_branch: str = "main") -> list[CheckResult]:
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
            results.append(check_branch_contains_control(remote, control_branch))

    gh_installed = check_gh_installed()
    results.append(gh_installed)
    if gh_installed.ok:
        results.append(check_gh_auth(_remote_host(remote_result.value)))

    return results
