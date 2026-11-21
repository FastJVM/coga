"""Git operations owned by the skill-update recurring script."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from coga.config import Config, load_config
from coga.skill_manager import (
    Runner, SkillManagerError, SkillUpdateSummary, VerificationResult,
    render_update_pr_body, run_subprocess, skills_root, update_skills,
)
from coga.github_source import github_owner_repo


# Dedicated branch the `--pr` flow commits skill updates onto. The flow is
# launched from the control-plane checkout (on `main` during a Dream run), so
# updates must never be committed or pushed on the caller's branch.
SKILL_UPDATE_BRANCH = "coga/skill-update"
# The exact message of the job's own commit on `SKILL_UPDATE_BRANCH`. The
# branch-claim guard recognizes job commits by this whole message (subject,
# empty body): the sweep commits as its operator, so the author cannot tell
# the job from a human. A human writing exactly this message with no body is
# an accepted residual risk.
SKILL_UPDATE_COMMIT_SUBJECT = "Update Coga-managed skills"
# Private refs the guard fetches the push destination's branches into, so the
# remote-tracking refs (and any fetch-URL view of them) are left untouched.
_GUARD_REF_PREFIX = "refs/coga/skill-update-guard"
def run_skill_update_pr_flow(
    cfg: Config,
    summary: SkillUpdateSummary,
    *,
    title: str,
    verification_commands: Sequence[str],
    runner: Runner | None = None,
    branch: str = SKILL_UPDATE_BRANCH,
    expected_remote_oid: str | None = None,
) -> SkillUpdateSummary:
    changed = [result for result in summary.results if result.changed]
    if not changed:
        # `update_skills` wrote nothing to the working tree, so there is nothing
        # to commit. Opening a PR with no diff just fails on `gh pr create`, so
        # leave `pr_url` unset and let the caller report a clean no-op.
        return summary

    run = runner or run_subprocess
    git_cwd = cfg.repo_root.parent
    original_branch = _current_git_branch(run, git_cwd)
    try:
        committed = _commit_skill_updates(
            cfg,
            branch=branch,
            base_branch=original_branch,
            runner=runner,
            cwd=git_cwd,
        )
        if not committed:
            # A `changed=True` result that produced no on-disk diff — e.g. an
            # opaque `gh skill update` that found nothing upstream. Nothing to
            # PR; the `finally` still restores the caller's branch.
            return summary
        for command in verification_commands:
            result = run_command_string(command, runner=runner, cwd=git_cwd)
            summary.verification.append(
                VerificationResult(
                    command=command,
                    returncode=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                )
            )
        body = render_update_pr_body(summary)
        summary.pr_url = open_or_update_pr(
            title,
            body,
            branch=branch,
            remote="origin",
            runner=runner,
            cwd=git_cwd,
            expected_remote_oid=expected_remote_oid,
        )
    finally:
        # Return the checkout to where the caller left it. A Dream run launches
        # this on `main`; it must not be left sitting on the skill-update branch.
        if original_branch and original_branch != branch:
            _checkout(run, git_cwd, original_branch)
    return summary


def assert_skill_update_pr_preflight(
    cfg: Config,
    *,
    runner: Runner | None = None,
    branch: str = SKILL_UPDATE_BRANCH,
) -> None:
    """Refuse `--pr` before any update is applied if the branch trip would fail.

    The PR flow runs `git checkout -B <branch> <control>`, commits only
    `skills_root(cfg)`, then checks out the caller's branch again. Git refuses
    that first checkout when a locally modified tracked path, or an untracked
    path, also differs between `HEAD` and the control branch; an unrelated
    edit that Git would carry over safely does not block. The skills tree
    itself must also match the control branch, because the updates dirty it
    only after this check runs. Pre-existing edits under the skills tree are
    refused too: `git add` would sweep them into the PR commit and the return
    checkout would remove them from the caller's branch.

    Callers must run this before `update_skills`; checking afterwards would
    leave the applied updates in the working tree on refusal.
    """
    run = runner or run_subprocess
    cwd = cfg.repo_root.parent
    control = _current_git_branch(run, cwd)
    _assert_no_unmerged_paths(run, cwd)

    # Compare both sides of the index separately: a staged edit followed by
    # restoring the working file to HEAD disappears from `git diff HEAD`, but
    # it still blocks checkout (and must not be swept into a skill commit).
    dirty = set(_git_paths(run, cwd, ["git", "diff", "--name-only", "--no-renames", "-z"]))
    dirty.update(_git_paths(
        run, cwd, ["git", "diff", "--cached", "--name-only", "--no-renames", "-z", "HEAD"]
    ))
    # `git diff` names paths relative to the checkout root wherever it runs;
    # `ls-files` is cwd-relative unless asked for `--full-name`. In the nested
    # layout (`coga init tools/ops`) `cwd` is not the checkout root, so every
    # path and the skills prefix are compared in checkout-relative coordinates.
    untracked = _git_paths(
        run, cwd, ["git", "ls-files", "--others", "--exclude-standard", "--full-name", "-z"]
    )
    differs = set(
        _git_paths(
            run, cwd, ["git", "diff", "--name-only", "--no-renames", "-z", "HEAD", control]
        )
    )
    toplevel = run(["git", "rev-parse", "--show-toplevel"], cwd)
    if toplevel.returncode != 0:
        raise SkillManagerError((toplevel.stderr or toplevel.stdout).strip())
    checkout_root = Path(toplevel.stdout.strip()).resolve()
    skills_prefix = skills_root(cfg).resolve().relative_to(checkout_root).as_posix() + "/"

    def in_skills(path: str) -> bool:
        return path.startswith(skills_prefix)

    blocking: dict[str, str] = {}
    for path in dirty:
        if in_skills(path):
            blocking[path] = "uncommitted edit in the skills tree"
        elif path in differs:
            blocking[path] = f"uncommitted edit; differs on `{control}`"
    for path in untracked:
        if in_skills(path):
            blocking.setdefault(path, "untracked file in the skills tree")
        elif path in differs:
            blocking.setdefault(path, f"untracked file; tracked on `{control}`")
    if blocking:
        listed = "\n".join(f"  - {path} ({reason})" for path, reason in sorted(blocking.items()))
        raise SkillManagerError(
            f"Cannot open a skill-update PR: switching to `{branch}` from "
            f"`{control}` would overwrite or sweep up local work. Commit or "
            f"stash these paths, then retry:\n{listed}"
        )

    skills_drift = sorted(path for path in differs if in_skills(path))
    if skills_drift:
        listed = "\n".join(f"  - {path}" for path in skills_drift)
        raise SkillManagerError(
            f"Cannot open a skill-update PR: the skills tree on this branch "
            f"differs from `{control}`, so the updated files could not be "
            f"carried onto `{branch}`. Run from `{control}`, or merge the "
            f"skill changes into it first, then retry:\n{listed}"
        )


def _git_paths(run: Runner, cwd: Path, args: list[str]) -> list[str]:
    result = run(args, cwd)
    if result.returncode != 0:
        raise SkillManagerError((result.stderr or result.stdout).strip())
    return [path for path in result.stdout.split("\0") if path]


def _assert_no_unmerged_paths(run: Runner, cwd: Path) -> None:
    """Fail loud before the PR flow if the working tree has unmerged paths.

    The flow runs `git checkout -B <branch> <base>` to carry skill updates onto
    a dedicated branch, and git refuses *any* checkout while an unmerged path
    exists ("error: you need to resolve your current index first"). Detecting it
    up front lets us name the offending files and the fix instead of surfacing a
    raw, context-free git error from deep inside the checkout.
    """
    result = run(["git", "diff", "--name-only", "--diff-filter=U"], cwd)
    if result.returncode != 0:
        raise SkillManagerError((result.stderr or result.stdout).strip())
    unmerged = [line for line in result.stdout.splitlines() if line.strip()]
    if unmerged:
        listed = "\n".join(f"  - {path}" for path in unmerged)
        raise SkillManagerError(
            "Cannot open a skill-update PR while the working tree has unmerged "
            "paths. Resolve the conflict and `git add` these files, then retry:\n"
            f"{listed}"
        )


def _current_git_branch(run: Runner, cwd: Path) -> str:
    result = run(["git", "branch", "--show-current"], cwd)
    if result.returncode != 0:
        raise SkillManagerError("Could not determine current git branch for skill update PR.")
    return result.stdout.strip()


def _checkout(
    run: Runner,
    cwd: Path,
    branch: str,
    *,
    create: bool = False,
    start_point: str | None = None,
) -> None:
    if create:
        args = ["git", "checkout", "-B", branch]
        if start_point:
            args.append(start_point)
    else:
        args = ["git", "checkout", branch]
    result = run(args, cwd)
    if result.returncode != 0:
        raise SkillManagerError((result.stderr or result.stdout).strip())


def _commit_skill_updates(
    cfg: Config,
    *,
    branch: str,
    base_branch: str,
    runner: Runner | None,
    cwd: Path,
) -> bool:
    """Carry the just-applied skill changes onto a dedicated branch and commit.

    `update_skills` has already written the updated files into the working tree
    under `skills_root(cfg)`. `git checkout -B <branch> <base>` carries those
    uncommitted changes onto a dedicated branch based on Coga's configured
    control branch — so the commit never lands on the caller's branch, and the
    PR never inherits unrelated feature commits. We stage and commit only the
    skills tree, preserving any unrelated staged or unstaged work for the
    return checkout.

    Returns `True` when a commit was made, `False` when staging the skills tree
    produced no diff (e.g. an opaque `gh skill update` that changed nothing) so
    the caller can skip the PR instead of failing on an empty commit.
    """
    run = runner or run_subprocess
    _checkout(run, cwd, branch, create=True, start_point=base_branch)
    added = run(["git", "add", "--", str(skills_root(cfg))], cwd)
    if added.returncode != 0:
        raise SkillManagerError((added.stderr or added.stdout).strip())
    staged = run(["git", "diff", "--cached", "--quiet", "--", str(skills_root(cfg))], cwd)
    if staged.returncode == 0:
        return False
    committed = run(
        ["git", "commit", "--only", "-m", SKILL_UPDATE_COMMIT_SUBJECT, "--", str(skills_root(cfg))],
        cwd,
    )
    if committed.returncode != 0:
        raise SkillManagerError((committed.stderr or committed.stdout).strip())
    return True


def run_command_string(
    command: str,
    *,
    runner: Runner | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return (runner or run_subprocess)(shlex.split(command), cwd)


def _remote_push_urls(run: Runner, remote: str, cwd: Path | None) -> list[str]:
    """Return the URLs a `git push <remote>` actually writes to."""
    result = run(["git", "remote", "get-url", "--push", "--all", remote], cwd)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "no output"
        raise SkillManagerError(
            f"`git remote get-url --push --all {remote}` failed: {detail}"
        )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _remote_branch_oid(
    run: Runner, remote: str, branch: str, cwd: Path | None
) -> str | None:
    """Return the OID the push destinations advertise for `branch`, else None.

    Asked live over the wire rather than read from a remote-tracking ref: the
    recurring sweep fetches without `--prune`, so a tracking ref outlives the
    branch GitHub deletes when a PR closes. A lease taken from that stale ref
    names an OID the remote has never heard of and the push is rejected with
    `stale info`. `None` means the branch genuinely does not exist, so there is
    nothing for a lease to protect.

    Resolved per *push URL* rather than by remote name, matching
    `git.remote_branch_oid`: git reads a remote's fetch URL for
    `ls-remote <name>` but writes its `pushurl` values for `push <name>`, so a
    lease taken by name can name a destination the push never touches. Multiple
    push URLs are supported only while they agree about the branch, since git
    can partially update a multi-push remote.
    """
    observed: list[str | None] = []
    for push_url in _remote_push_urls(run, remote, cwd):
        result = run(
            ["git", "ls-remote", "--heads", push_url, f"refs/heads/{branch}"], cwd
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip() or "no output"
            raise SkillManagerError(
                f"`git ls-remote --heads {push_url} refs/heads/{branch}` failed: "
                f"{detail}"
            )
        line = next((line for line in result.stdout.splitlines() if line.strip()), "")
        observed.append(line.split(maxsplit=1)[0] if line else None)
    if len(set(observed)) != 1:
        raise SkillManagerError(
            f"effective push destinations for {remote!r}/{branch} disagree about "
            "the branch tip; refusing to lease a push against one of them."
        )
    return observed[0]


def _run_gh(
    run: Runner, args: Sequence[str], cwd: Path | None
) -> subprocess.CompletedProcess[str]:
    try:
        return run(["gh", *args], cwd)
    except FileNotFoundError as exc:
        raise SkillManagerError(
            "GitHub CLI (`gh`) is required to open a skill-update PR. "
            "Install it from https://cli.github.com, run `gh auth login`, "
            "then retry."
        ) from exc


def _open_pr_url(
    run: Runner, branch: str, cwd: Path | None, *, repo: str | None = None
) -> str:
    """URL of the open PR whose head is `branch`, or "" when there is none."""
    args = ["pr", "list"]
    if repo is not None:
        args += ["--repo", repo]
    args += [
        "--head",
        branch,
        "--state",
        "open",
        "--json",
        "url",
        "--jq",
        '.[0].url // ""',
    ]
    result = _run_gh(run, args, cwd)
    if result.returncode != 0:
        raise SkillManagerError((result.stderr or result.stdout).strip())
    return result.stdout.strip()


def _push_destination_github_repo(
    run: Runner, remote: str, cwd: Path | None
) -> tuple[str, str]:
    """Return (`owner/repo`, push URL) for the repository `git push <remote>` writes.

    The guard must inspect the repository the push would overwrite, not gh's
    default repository or the remote's fetch URL. Every push URL must name the
    same github.com repository; anything else is refused rather than guessed.
    """
    urls = _remote_push_urls(run, remote, cwd)
    repos: dict[str, str] = {}
    for url in urls:
        value = url.strip()
        is_url = "://" in value or value.startswith("git@github.com:")
        repo = github_owner_repo(value) if is_url else None
        if repo is None:
            raise SkillManagerError(
                f"Cannot check {SKILL_UPDATE_BRANCH} for hand-pushed commits: "
                f"push URL {value!r} of remote {remote!r} is not a github.com "
                "repository."
            )
        repos.setdefault(repo.lower(), repo)
    if len(repos) != 1:
        raise SkillManagerError(
            f"Cannot check {SKILL_UPDATE_BRANCH} for hand-pushed commits: push "
            f"URLs of remote {remote!r} name different repositories "
            f"({', '.join(sorted(repos.values())) or 'none'})."
        )
    return next(iter(repos.values())), urls[0]


def _git_checked(run: Runner, args: Sequence[str], cwd: Path | None) -> str:
    result = run(["git", *args], cwd)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "no output"
        raise SkillManagerError(f"`git {' '.join(args)}` failed: {detail}")
    return result.stdout


def _verbatim_patch_ids(
    root: Path, revisions: list[str], *, no_walk: bool = False
) -> dict[str, str] | None:
    """Map non-merge commits to whitespace-sensitive patch IDs; fail closed.

    Keep control exclusions out of the merged-side revisions so normal
    merges retain the same comparison evidence as squash merges. A differing
    context can conservatively prevent a match. Disable external diff and
    text conversion so the proof describes the stored source bytes.
    """
    # Use bytes: text-mode subprocess IO would normalize CRLF in a patch.
    base = ["git", "-C", str(root)]
    patches = subprocess.run(
        [
            *base, "log", "--stdin", *(["--no-walk=unsorted"] if no_walk else []),
            "--no-merges", "--root", "--format=commit %H", "--patch", "--binary",
            "--full-index", "--no-color", "--no-ext-diff", "--no-textconv",
            "--no-renames", "--no-notes", "--no-relative", "--ignore-submodules=none",
            "--submodule=short", "--src-prefix=a/", "--dst-prefix=b/", "--",
        ],
        input=("\n".join(revisions) + "\n").encode("ascii"),
        capture_output=True,
        check=False,
    )
    if patches.returncode != 0:
        return None
    ids = subprocess.run(
        [*base, "patch-id", "--verbatim"], input=patches.stdout,
        capture_output=True, check=False,
    )
    if ids.returncode != 0:
        return None
    result: dict[str, str] = {}
    for line in ids.stdout.decode("ascii").splitlines():
        fields = line.split()
        if len(fields) != 2:
            return None
        patch_id, commit = fields
        result[commit] = patch_id
    return result


def assert_skill_update_branch_unclaimed(
    cfg: Config,
    *,
    runner: Runner | None = None,
    branch: str = SKILL_UPDATE_BRANCH,
) -> str | None:
    """Refuse to rebuild `branch` when its open PR carries hand-pushed commits.

    The `--pr` flow rebuilds `branch` from the control branch every run and
    force-pushes it, which would silently discard a fix someone pushed onto the
    open PR. Run before `update_skills` writes anything, this returns the
    remote tip it verified (for the push lease) or `None` when the branch does
    not exist. It raises `SkillManagerError` listing the foreign commits.

    Deliberate scope: with no *open* PR (merged, closed, or squash-merged with
    the branch left behind) commits are not inspected; merging or closing is
    the human decision. "On control" means the control branch freshly fetched
    from the push destination, compared by ancestry and by patch. Known limit:
    merge commits are skipped (`--no-merges`), so a hand edit hidden in a
    merge's conflict resolution is not detected.
    """
    run = runner or run_subprocess
    cwd = cfg.repo_root.parent
    remote = "origin"
    oid = _remote_branch_oid(run, remote, branch, cwd)
    if oid is None:
        return None
    repo, push_url = _push_destination_github_repo(run, remote, cwd)
    # An owner/repo argument alone still obeys GH_HOST. Bind the hostname as
    # well, or an empty lookup on another host could permit discarding work.
    pr_url = _open_pr_url(run, branch, cwd, repo=f"github.com/{repo}")
    if not pr_url:
        return oid

    control_ref = f"{_GUARD_REF_PREFIX}/control"
    branch_ref = f"{_GUARD_REF_PREFIX}/branch"
    control = _current_git_branch(run, cwd)
    try:
        _git_checked(
            run,
            [
                "fetch",
                "--no-tags",
                push_url,
                f"+refs/heads/{control}:{control_ref}",
                f"+refs/heads/{branch}:{branch_ref}",
            ],
            cwd,
        )
        fetched = _git_checked(run, ["rev-parse", "--verify", branch_ref], cwd).strip()
        if fetched != oid:
            raise SkillManagerError(
                f"{branch} moved while checking it for hand-pushed commits "
                f"(saw {oid[:12]}, then fetched {fetched[:12]}); retry."
            )
        log = _git_checked(
            run,
            [
                "log",
                "--no-merges",
                "--right-only",
                "--format=%H%x00%h%x00%s%x00%B%x1e",
                f"{control_ref}...{oid}",
            ],
            cwd,
        )
        candidates: list[tuple[str, str, str]] = []
        for record in log.split("\x1e"):
            record = record.strip("\n")
            if not record:
                continue
            full, short, subject, message = record.split("\x00", 3)
            if message.strip() == SKILL_UPDATE_COMMIT_SUBJECT:
                continue
            candidates.append((full, short, subject))
        if candidates:
            candidates = _drop_patches_on_control(cwd, control_ref, candidates)
    finally:
        for ref in (control_ref, branch_ref):
            run(["git", "update-ref", "-d", ref], cwd)
    if candidates:
        listed = "\n".join(f"  {short} {subject}" for _, short, subject in candidates)
        raise SkillManagerError(
            f"Refusing to rebuild {branch}: its open PR {pr_url} carries commits "
            f"the skill-update job did not make:\n{listed}\n"
            "Merge the PR, move these commits elsewhere, or close the PR to "
            "discard them deliberately, then retry."
        )
    return oid


def _drop_patches_on_control(
    cwd: Path, control_ref: str, candidates: list[tuple[str, str, str]]
) -> list[tuple[str, str, str]]:
    """Drop candidates whose patch already landed on control.

    Every non-job commit reaches this check: `--cherry-pick` is deliberately
    not used upstream, because ordinary patch IDs ignore whitespace and would
    drop a hand fix differing from a control commit only in whitespace. It
    would also miss a copy that became shared history once control is merged
    into the PR branch. Compare each candidate against control's commits
    since that candidate's parent instead, by whitespace-sensitive patch ID;
    an uncomparable patch stays foreign.
    Keep those ranges separate: a later candidate's parent can already
    contain an earlier candidate's landed copy after a merge of control.
    """
    commits = [full for full, _, _ in candidates]
    comparison_error = (
        f"Could not compare {SKILL_UPDATE_BRANCH} commits against "
        "control by patch; refusing to overwrite them."
    )
    local = _verbatim_patch_ids(cwd, commits, no_walk=True)
    if local is None:
        raise SkillManagerError(comparison_error)
    foreign: list[tuple[str, str, str]] = []
    for candidate in candidates:
        commit = candidate[0]
        landed = _verbatim_patch_ids(cwd, [control_ref, f"^{commit}^"])
        if landed is None:
            raise SkillManagerError(comparison_error)
        if local.get(commit) not in set(landed.values()):
            foreign.append(candidate)
    return foreign


def open_or_update_pr(
    title: str,
    body: str,
    *,
    branch: str | None = None,
    remote: str = "origin",
    runner: Runner | None = None,
    cwd: Path | None = None,
    expected_remote_oid: str | None = None,
) -> str:
    """Push `branch` and open or update its draft PR.

    `expected_remote_oid` is the tip a caller already verified (the
    branch-claim guard). When given, the push leases against it instead of a
    fresh `ls-remote`, so a hand push landing between that check and this push
    fails the lease rather than being overwritten. `None` keeps the fresh
    lookup, with no lease when the branch is absent.
    """
    run = runner or run_subprocess

    def run_gh(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return _run_gh(run, args, cwd)

    if branch is None:
        branch_result = run(["git", "branch", "--show-current"], cwd)
        if branch_result.returncode != 0 or not branch_result.stdout.strip():
            raise SkillManagerError(
                "Could not determine current git branch for skill update PR."
            )
        branch = branch_result.stdout.strip()
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", delete=False) as fh:
        fh.write(body)
        body_file = fh.name
    try:
        # Lease against the tip the push destination advertises right now,
        # matching `open_pr.py`. A bare `--force-with-lease` would instead take
        # its expected value from the remote-tracking ref, which the unpruned
        # sweep leaves pointing at a branch GitHub already deleted.
        remote_oid = (
            expected_remote_oid
            if expected_remote_oid is not None
            else _remote_branch_oid(run, remote, branch, cwd)
        )
        lease = (
            [f"--force-with-lease=refs/heads/{branch}:{remote_oid}"]
            if remote_oid
            else []
        )
        pushed = run(["git", "push", *lease, "-u", remote, branch], cwd)
        if pushed.returncode != 0:
            raise SkillManagerError((pushed.stderr or pushed.stdout).strip())
        existing_url = _open_pr_url(run, branch, cwd)
        if existing_url:
            edited = run_gh(
                [
                    "pr",
                    "edit",
                    existing_url,
                    "--title",
                    title,
                    "--body-file",
                    body_file,
                ]
            )
            if edited.returncode != 0:
                raise SkillManagerError((edited.stderr or edited.stdout).strip())
            return existing_url
        created = run_gh(
            [
                "pr",
                "create",
                "--draft",
                "--title",
                title,
                "--body-file",
                body_file,
            ]
        )
        if created.returncode != 0:
            raise SkillManagerError((created.stderr or created.stdout).strip())
        return created.stdout.strip()
    finally:
        Path(body_file).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-title", default=SKILL_UPDATE_COMMIT_SUBJECT)
    args = parser.parse_args()
    try:
        cfg = load_config()
        assert_skill_update_pr_preflight(cfg)
        expected_remote_oid = assert_skill_update_branch_unclaimed(cfg)
        summary = update_skills(cfg, all_skills=True)
        run_skill_update_pr_flow(
            cfg, summary, title=args.pr_title, verification_commands=["coga validate --json"],
            expected_remote_oid=expected_remote_oid,
        )
    except (SkillManagerError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(summary.to_dict()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
