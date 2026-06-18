"""Git/GitHub auth preflight probes for `relay validate --check-github`.

Opt-in only: nothing here runs unless the explicit `--check-github` flag is
passed. The probes shell out to the standard tools the operator already uses —
`git` (with their configured remote, `ssh-agent`, and credential helpers) and
the `gh` CLI (with their `gh auth login` state). Relay does **not** read
`GITHUB_TOKEN`, store a GitHub PAT, run an OAuth flow, or reimplement GitHub
auth. The point is narrow: turn a raw tool failure that would otherwise
surprise an agent at PR time into an actionable setup hint a new operator can
act on before launch.

Each probe returns a structured `CheckResult`; `relay.validate` maps the
failures into report `Issue`s. The reachability probe runs non-interactively
(`GIT_TERMINAL_PROMPT=0` plus ssh `BatchMode=yes`) so a missing credential can
never hang the check on a hidden password prompt.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

# Wall-clock ceiling for any single probe. The reachability probe talks to the
# network; the rest are local, but a uniform timeout keeps a wedged subprocess
# from stalling the whole check.
_PROBE_TIMEOUT = 20.0


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
            f"`git remote add {remote} <url>`, or point Relay at the right "
            f"remote via [git].remote in relay.toml.",
        )
    return CheckResult("git-remote", True, f"remote {remote!r} → {_first_line(out)}")


def check_git_auth(remote: str) -> CheckResult:
    """Probe reachability/auth for the configured remote, transport-neutral.

    Uses `git ls-remote --heads <remote>` so it exercises whatever transport
    the remote is configured with (SSH or HTTPS) through the operator's normal
    `ssh-agent` / credential-helper setup. Runs non-interactively so a missing
    credential fails fast instead of blocking on a prompt.
    """
    rc, out, err = _run(
        ["git", "ls-remote", "--heads", remote],
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
            f"could not reach/authenticate remote {remote!r} "
            f"(`git ls-remote {remote}` failed: {_first_line(err) or 'no output'}). "
            "Check that you are online and that the remote's transport is set "
            "up: for SSH, that your key is loaded (`ssh-add -l`) and authorized; "
            "for HTTPS, that a git credential helper has valid credentials.",
        )
    return CheckResult("git-auth", True, f"remote {remote!r} reachable and authenticated")


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


def check_gh_auth() -> CheckResult:
    """Verify `gh` is authenticated via `gh auth status`."""
    rc, out, err = _run(["gh", "auth", "status"])
    if rc is None:
        return CheckResult(
            "gh-auth",
            False,
            "`gh` (GitHub CLI) is not installed — install it and run "
            "`gh auth login`.",
        )
    if rc != 0:
        # `gh auth status` writes its report to stderr.
        return CheckResult(
            "gh-auth",
            False,
            "`gh` is not authenticated — run `gh auth login`. "
            f"({_first_line(err) or _first_line(out) or 'gh auth status failed'})",
        )
    return CheckResult("gh-auth", True, "gh authenticated")


def run_preflight(remote: str) -> list[CheckResult]:
    """Run the full preflight against the configured remote.

    Skips probes that can't be meaningful: reachability only runs when the
    remote exists, and gh auth only runs when gh is installed — so a missing
    remote or missing `gh` produces one clear hint, not a cascade.
    """
    results: list[CheckResult] = []

    remote_result = check_git_remote(remote)
    results.append(remote_result)
    if remote_result.ok:
        results.append(check_git_auth(remote))

    gh_installed = check_gh_installed()
    results.append(gh_installed)
    if gh_installed.ok:
        results.append(check_gh_auth())

    return results
