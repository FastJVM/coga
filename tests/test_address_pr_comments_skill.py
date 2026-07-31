from __future__ import annotations

from pathlib import Path


def test_address_pr_comments_skill_preserves_the_owner_gate() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    skill = (
        repo_root
        / "coga"
        / "skills"
        / "code"
        / "address-pr-comments"
        / "SKILL.md"
    ).read_text()

    assert "gh api graphql" in skill
    assert "reviewThreads" in skill
    assert "addPullRequestReviewThreadReply" in skill
    assert "headRefOid" in skill
    assert "headRepositoryOwner" in skill
    assert "[git].remote" in skill
    assert "git remote get-url --push --all <configured-remote>" in skill
    assert "Require exactly one" in skill
    assert "multi-push remote" in skill
    assert "<verified-push-url>" in skill
    assert "`(status, step, assignee)`" in skill
    assert "`coga block`" in skill
    assert "python -m pytest" in skill
    assert "git push --force-with-lease=refs/heads/<branch-name>:" in skill
    assert "git merge-base --is-ancestor <verified-remote-oid> HEAD" in skill
    assert "require the PR to remain open" in skill
    assert "not permission to rewrite history" in skill
    assert "git push origin" not in skill
    assert "Every thread is already satisfied" in skill
    assert "Do not manufacture a commit and do not" in skill
    assert "`FETCH_HEAD`, that reported OID" in skill
    assert "applicable post-push or no-change proof" in skill
    assert "trailing usage-log commit" in skill
    assert "publishes that log-only commit" in skill
    assert "Do not merge" in skill
    assert "Do not resolve" in skill
    assert "Do not run `coga bump`" in skill
    assert "Do not run `coga mark done`" in skill
    assert "Do not use `coga slack` as a completion signal" in skill
