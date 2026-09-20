from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from coga import retire_worklist as rw
from coga.config import load_config


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    company = tmp_path / "coga"
    _write(
        company / "coga.toml",
        """
        version = 1
        default_status = "draft"
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(company / "coga.local.toml", 'user = "marc"\n')
    monkeypatch.chdir(company)
    return company


def _seed_template(repo: Path, name: str = "autoclose-merged") -> Path:
    """A recurring template directory, the durable home a worklist sits beside."""
    template = repo / "recurring" / name
    template.mkdir(parents=True, exist_ok=True)
    (template / "ticket.md").write_text("template\n")
    return template


def _entry(
    slug: str,
    *,
    branch: str = "feature-x",
    worktree: str = "/nowhere/coga-feature-x",
    recorded: str = "2026-09-04",
) -> rw.RetireFollowUp:
    return rw.RetireFollowUp(
        slug=slug, branch=branch, worktree=worktree, recorded=recorded
    )


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _git_repo_with_branch(root: Path, branch: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "Tester")
    _git(root, "commit", "-q", "--allow-empty", "-m", "root")
    _git(root, "branch", branch)
    return root


def _linked_worktree(root: Path, path: Path, branch: str) -> Path:
    """A real linked worktree of `root` — the one checkout retire disposes of."""
    _git(root, "worktree", "add", "-q", "-b", branch, str(path), "main")
    return path


# --- parse / render --------------------------------------------------------


def test_parse_reads_the_documented_line_shape_byte_for_byte() -> None:
    # The shape a consuming repo's hand-seeded worklist already uses; a
    # parser change here is a format change for every existing file.
    text = (
        "# Stranded `coga retire` follow-ups\n\nprose\n\n"
        f"{rw.RETIRE_WORKLIST_HEADING}\n\n"
        "- `v1/persistent-codex-m-managed-checkout` — branch "
        "`codex-m-persistent-managed`, worktree "
        "`/tmp/coga-persistent-codex-m-managed`, recorded `2026-09-04`\n"
    )

    header, entries = rw.parse_worklist(text)

    assert header.endswith(rw.RETIRE_WORKLIST_HEADING + "\n")
    assert entries == [
        rw.RetireFollowUp(
            slug="v1/persistent-codex-m-managed-checkout",
            branch="codex-m-persistent-managed",
            worktree="/tmp/coga-persistent-codex-m-managed",
            recorded="2026-09-04",
        )
    ]
    assert rw.render_worklist(header, entries) == text


def test_render_sorts_entries_by_slug_and_ends_with_a_newline() -> None:
    rendered = rw.render_worklist(
        rw.RETIRE_WORKLIST_HEADER, [_entry("zeta"), _entry("alpha")]
    )

    body = rendered.split(rw.RETIRE_WORKLIST_HEADING + "\n", 1)[1]
    assert body.splitlines() == [
        "",
        _entry("alpha").render(),
        _entry("zeta").render(),
    ]
    assert rendered.endswith("\n")


def test_parse_collapses_a_union_merged_duplicate_keeping_the_first_date() -> None:
    # `retires.md` is `merge=union`: the same slug recorded on two branches
    # arrives as two lines. The later line wins the checkout, the first
    # sighting keeps the date — the same rule a re-record applies.
    text = rw.RETIRE_WORKLIST_HEADER + "\n" + "\n".join(
        [
            _entry("dup", branch="old", recorded="2026-09-01").render(),
            _entry("dup", branch="new", recorded="2026-09-05").render(),
        ]
    ) + "\n"

    _, entries = rw.parse_worklist(text)

    assert entries == [_entry("dup", branch="new", recorded="2026-09-01")]


def test_parse_normalizes_a_missing_trailing_newline_instead_of_doubling() -> None:
    header, entries = rw.parse_worklist(f"# Worklist\n\n{rw.RETIRE_WORKLIST_HEADING}")

    assert header.count(rw.RETIRE_WORKLIST_HEADING) == 1
    assert entries == []


def test_parse_fails_loudly_on_a_foreign_file() -> None:
    with pytest.raises(rw.RetireWorklistError, match="has no"):
        rw.parse_worklist("# Someone else's notes\n")


def test_parse_fails_loudly_on_an_unparsable_line() -> None:
    text = rw.RETIRE_WORKLIST_HEADER + "\n- not a follow-up\n"
    with pytest.raises(rw.RetireWorklistError, match="unparsable"):
        rw.parse_worklist(text)


@pytest.mark.parametrize(
    "value",
    [
        "`leading-and-trailing`",
        "embedded`backtick",
        "%60-is-literal",
        "space and é",
        "line\nbreak",
        "carriage\rreturn",
        "unicode\u2028separator",
        r"C:\work\path",
    ],
)
def test_worklist_fields_round_trip_without_breaking_entry_lines(value: str) -> None:
    entry = rw.RetireFollowUp(value, value, value, value)
    rendered = rw.render_worklist(rw.RETIRE_WORKLIST_HEADER, [entry])

    _, entries = rw.parse_worklist(rendered)

    assert entries == [entry]
    body = rendered.partition(rw.RETIRE_WORKLIST_HEADING + "\n")[2]
    assert len(body.splitlines()) == 2


def test_reconcile_preserves_distinct_backtick_and_percent_paths(
    repo: Path, tmp_path: Path
) -> None:
    path = _seed_template(repo) / rw.RETIRE_WORKLIST_FILENAME
    cfg = load_config(repo)
    tick = tmp_path / "feature`tree"
    percent = tmp_path / "feature%60tree"
    tick.mkdir()
    percent.mkdir()
    pending = [
        _entry("tick", branch="", worktree=str(tick)),
        _entry("percent", branch="", worktree=str(percent)),
    ]
    rw.reconcile_worklist(cfg, path, root=tmp_path, pending=pending)
    first = path.read_bytes()

    change = rw.reconcile_worklist(cfg, path, root=tmp_path)

    assert not change.written
    assert path.read_bytes() == first
    assert set(change.open) == set(pending)

    tick.rmdir()
    change = rw.reconcile_worklist(cfg, path, root=tmp_path)

    assert change.dropped == [pending[0]]
    assert change.open == [pending[1]]


# --- the discharge rule ----------------------------------------------------


def test_a_live_worktree_directory_keeps_the_entry(tmp_path: Path) -> None:
    worktree = tmp_path / "live"
    worktree.mkdir()
    entry = _entry("x", branch="gone", worktree=str(worktree))

    assert not rw.is_discharged(entry, root=tmp_path, branches=frozenset())


def test_a_live_branch_keeps_the_entry(tmp_path: Path) -> None:
    entry = _entry("x", branch="alive", worktree=str(tmp_path / "absent"))

    assert not rw.is_discharged(entry, root=tmp_path, branches=frozenset({"alive"}))


def test_worktree_and_branch_both_gone_discharges_the_entry(tmp_path: Path) -> None:
    entry = _entry("x", branch="gone", worktree=str(tmp_path / "absent"))

    assert rw.is_discharged(entry, root=tmp_path, branches=frozenset({"other"}))


def test_an_entry_without_a_worktree_is_judged_on_its_branch_alone(
    tmp_path: Path,
) -> None:
    assert rw.is_discharged(
        _entry("x", branch="gone", worktree=""), root=tmp_path, branches=frozenset()
    )
    assert not rw.is_discharged(
        _entry("x", branch="alive", worktree=""),
        root=tmp_path,
        branches=frozenset({"alive"}),
    )


def test_an_unknown_branch_list_keeps_every_entry_with_a_branch(tmp_path: Path) -> None:
    # Fail closed on debt: a probe that could not run must not read as "no
    # branches exist".
    entry = _entry("x", branch="maybe", worktree=str(tmp_path / "absent"))

    assert not rw.is_discharged(entry, root=tmp_path, branches=None)
    assert rw.is_discharged(
        _entry("y", branch="", worktree=str(tmp_path / "absent")),
        root=tmp_path,
        branches=None,
    )


def test_an_unknown_git_root_keeps_every_entry(tmp_path: Path) -> None:
    # A relative worktree cannot be judged without the root it is relative to,
    # and guessing one could discharge a checkout that still exists.
    entry = _entry("x", branch="", worktree="checkouts/feature")

    assert not rw.is_discharged(entry, root=None, branches=frozenset())


def test_a_relative_worktree_resolves_against_the_root_not_the_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    (root / "checkouts" / "feature").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    entry = _entry("x", branch="", worktree="checkouts/feature")

    assert not rw.is_discharged(entry, root=root, branches=frozenset())
    assert rw.is_discharged(entry, root=elsewhere, branches=frozenset())


def test_a_worktree_that_is_the_primary_checkout_never_holds_the_entry(
    tmp_path: Path,
) -> None:
    # A ticket worked in the single-checkout layout records the primary
    # checkout as its own `worktree:`. Retire will never remove it, so counting
    # it as outstanding listed the entry forever: the primary checkout is
    # always a directory. The branch half still has to clear on its own.
    root = _git_repo_with_branch(tmp_path / "repo", "feature-x")
    entry = _entry("x", branch="feature-x", worktree=str(root))

    assert not rw.is_discharged(entry, root=root, branches=frozenset({"feature-x"}))
    assert rw.is_discharged(entry, root=root, branches=frozenset())


def test_a_live_linked_worktree_still_holds_the_entry(tmp_path: Path) -> None:
    # The debt this worklist exists for: a checkout `coga retire` really will
    # dispose of keeps its entry even after the branch is gone.
    root = _git_repo_with_branch(tmp_path / "repo", "unused")
    worktree = _linked_worktree(root, tmp_path / "coga-feature-x", "feature-x")
    entry = _entry("x", branch="", worktree=str(worktree))

    assert not rw.is_discharged(entry, root=root, branches=frozenset())


def test_an_independent_clone_does_not_hold_the_entry(tmp_path: Path) -> None:
    # The `dev/code` sandbox fallback checkout. Retire preserves it exactly as
    # it preserves the primary checkout, so it is not debt retire can discharge.
    root = _git_repo_with_branch(tmp_path / "repo", "feature-x")
    clone = tmp_path / "clone"
    _git(root, "clone", "--no-hardlinks", "-q", str(root), str(clone))
    entry = _entry("x", branch="", worktree=str(clone))

    assert rw.is_discharged(entry, root=root, branches=frozenset())


def test_a_checkout_git_cannot_classify_holds_the_entry(tmp_path: Path) -> None:
    # Fail closed on debt, as everywhere else here: a probe with no answer must
    # not read as "not a worktree" and silently forget a live checkout.
    root = tmp_path / "not-a-repo"
    worktree = root / "live"
    worktree.mkdir(parents=True)
    entry = _entry("x", branch="", worktree=str(worktree))

    assert not rw.is_discharged(entry, root=root, branches=frozenset())


def test_local_branches_lists_heads_and_is_none_outside_a_repo(tmp_path: Path) -> None:
    repo = _git_repo_with_branch(tmp_path / "repo", "feature-x")

    assert rw.local_branches(repo) == frozenset({"main", "feature-x"})
    assert rw.local_branches(tmp_path / "not-a-repo") is None


def test_local_branches_is_not_shadowed_by_a_tag_of_the_same_name(tmp_path: Path) -> None:
    """`%(refname:short)` would report `heads/feature-x` here and read as gone."""
    repo = _git_repo_with_branch(tmp_path / "repo", "feature-x")
    _git(repo, "tag", "feature-x")

    assert rw.local_branches(repo) == frozenset({"main", "feature-x"})


# --- reconcile -------------------------------------------------------------


def test_reconcile_creates_the_worklist_with_the_documented_header(repo: Path) -> None:
    path = rw.template_worklist_path(load_config(repo), "autoclose-merged")

    change = rw.reconcile_worklist(
        load_config(repo),
        path,
        root=repo,
        pending=[_entry("stranded")],
        branches=frozenset(),
    )

    assert change.written and change.added == [_entry("stranded")]
    text = path.read_text()
    assert text.startswith("# Stranded `coga retire` follow-ups")
    assert rw.parse_worklist(text) == (rw.RETIRE_WORKLIST_HEADER, [_entry("stranded")])


def test_reconcile_does_not_mint_an_empty_worklist_on_a_quiet_run(repo: Path) -> None:
    path = rw.template_worklist_path(load_config(repo), "autoclose-merged")

    change = rw.reconcile_worklist(load_config(repo), path, root=repo, branches=frozenset())

    assert not change.written and not path.exists()


def test_reconcile_is_idempotent_by_slug_and_keeps_the_first_date(repo: Path) -> None:
    cfg = load_config(repo)
    path = rw.template_worklist_path(cfg, "autoclose-merged")
    rw.reconcile_worklist(
        cfg, path, root=repo, pending=[_entry("s", recorded="2026-09-04")]
    )
    first = path.read_bytes()

    change = rw.reconcile_worklist(
        cfg, path, root=repo, pending=[_entry("s", recorded="2026-09-05")]
    )

    assert not change.written
    assert not (change.added or change.refreshed or change.dropped)
    assert path.read_bytes() == first
    assert path.read_text().count("`s`") == 1


def test_reconcile_refreshes_a_moved_checkout_and_preserves_unrelated_entries(
    repo: Path,
) -> None:
    cfg = load_config(repo)
    path = rw.template_worklist_path(cfg, "autoclose-merged")
    rw.reconcile_worklist(
        cfg, path, root=repo, pending=[_entry("s", branch="old"), _entry("other")]
    )

    change = rw.reconcile_worklist(
        cfg, path, root=repo, pending=[_entry("s", branch="new", recorded="2026-09-09")]
    )

    assert change.refreshed == [_entry("s", branch="new")]
    _, entries = rw.parse_worklist(path.read_text())
    assert entries == [_entry("other"), _entry("s", branch="new")]


def test_reconcile_drops_discharged_entries_and_keeps_live_debt(
    repo: Path, tmp_path: Path
) -> None:
    cfg = load_config(repo)
    path = rw.template_worklist_path(cfg, "autoclose-merged")
    live_dir = tmp_path / "still-here"
    live_dir.mkdir()
    rw.reconcile_worklist(
        cfg,
        path,
        root=repo,
        pending=[
            _entry("done", branch="gone", worktree=str(tmp_path / "absent")),
            _entry("dir-lives", branch="gone", worktree=str(live_dir)),
            _entry("branch-lives", branch="alive", worktree=str(tmp_path / "absent")),
        ],
        branches=frozenset({"gone", "alive"}),
    )

    change = rw.reconcile_worklist(
        cfg, path, root=repo, branches=frozenset({"alive"})
    )

    assert [e.slug for e in change.dropped] == ["done"]
    assert [e.slug for e in change.open] == ["branch-lives", "dir-lives"]
    assert "`done`" not in path.read_text()


def test_reconcile_drains_a_primary_checkout_entry_once_its_branch_is_gone(
    repo: Path, tmp_path: Path
) -> None:
    # The stranded-entry case end to end: an entry already written against the
    # primary checkout clears on an ordinary sweep, with no hand edit of
    # `retires.md`, while a real linked worktree beside it stays listed.
    cfg = load_config(repo)
    root = _git_repo_with_branch(tmp_path / "repo", "in-place")
    worktree = _linked_worktree(root, tmp_path / "coga-real", "real")
    path = rw.template_worklist_path(cfg, "autoclose-merged")
    rw.reconcile_worklist(
        cfg,
        path,
        root=root,
        pending=[
            _entry("in-place", branch="in-place", worktree=str(root)),
            _entry("real", branch="real", worktree=str(worktree)),
        ],
        branches=frozenset({"in-place", "real"}),
    )
    _git(root, "branch", "-D", "in-place")

    change = rw.reconcile_worklist(cfg, path, root=root)

    assert [e.slug for e in change.dropped] == ["in-place"]
    assert [e.slug for e in change.open] == ["real"]
    assert "`in-place`" not in path.read_text()


def test_reconcile_refuses_when_the_file_moved_underneath_it(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = load_config(repo)
    path = rw.template_worklist_path(cfg, "autoclose-merged")
    rw.reconcile_worklist(cfg, path, root=repo, pending=[_entry("s")])
    before = path.read_bytes()

    # Simulate a writer landing between the parse and the replace.
    original = rw.parse_worklist

    def racing_parse(text: str):  # type: ignore[no-untyped-def]
        path.write_bytes(before + _entry("late").render().encode() + b"\n")
        return original(text)

    monkeypatch.setattr(rw, "parse_worklist", racing_parse)
    with pytest.raises(rw.RetireWorklistError, match="changed underneath"):
        rw.reconcile_worklist(cfg, path, root=repo, pending=[_entry("t")])

    # The racing writer's bytes survive; nothing was overwritten.
    assert b"`late`" in path.read_bytes()
    assert b"`t`" not in path.read_bytes()


def test_reconcile_uses_the_real_branch_list_by_default(repo: Path, tmp_path: Path) -> None:
    cfg = load_config(repo)
    root = _git_repo_with_branch(tmp_path / "git-root", "feature-x")
    path = rw.template_worklist_path(cfg, "autoclose-merged")
    rw.reconcile_worklist(
        cfg,
        path,
        root=root,
        pending=[
            _entry("kept", branch="feature-x", worktree=str(tmp_path / "absent")),
            _entry("dropped", branch="deleted", worktree=str(tmp_path / "absent")),
        ],
        branches=frozenset({"feature-x", "deleted"}),
    )

    change = rw.reconcile_worklist(cfg, path, root=root)

    assert [e.slug for e in change.dropped] == ["dropped"]
    assert [e.slug for e in change.open] == ["kept"]


# --- which worklist ------------------------------------------------------------


def test_a_period_task_blackboard_names_its_template_worklist(repo: Path) -> None:
    _seed_template(repo, "autoclose-merged")
    period = repo / "tasks" / "recurring" / "autoclose-merged" / "ticket.md"
    period.parent.mkdir(parents=True)
    period.write_text("period\n")

    assert rw.worklist_for_period_task(load_config(repo), period) == (
        repo / "recurring" / "autoclose-merged" / rw.RETIRE_WORKLIST_FILENAME
    )


def test_the_template_is_resolved_from_the_period_task_not_hardcoded(repo: Path) -> None:
    _seed_template(repo, "nightly-close")
    period = repo / "tasks" / "recurring" / "nightly-close" / "ticket.md"
    period.parent.mkdir(parents=True)
    period.write_text("period\n")

    assert rw.worklist_for_period_task(load_config(repo), period) == (
        repo / "recurring" / "nightly-close" / rw.RETIRE_WORKLIST_FILENAME
    )


@pytest.mark.parametrize(
    "relative",
    [
        "tasks/autoclose-merged/ticket.md",  # an ordinary task
        "tasks/recurring/nested/deeper/ticket.md",  # not a period task shape
        "tasks/recurring/autoclose-merged.md",  # file-form, no template dir
    ],
)
def test_a_non_period_task_has_no_durable_worklist(repo: Path, relative: str) -> None:
    _seed_template(repo, "autoclose-merged")
    blackboard = repo / relative
    blackboard.parent.mkdir(parents=True, exist_ok=True)
    blackboard.write_text("x\n")

    assert rw.worklist_for_period_task(load_config(repo), blackboard) is None


def test_no_blackboard_means_no_worklist(repo: Path) -> None:
    assert rw.worklist_for_period_task(load_config(repo), None) is None


def test_a_period_task_whose_template_is_gone_has_no_worklist(repo: Path) -> None:
    period = repo / "tasks" / "recurring" / "removed" / "ticket.md"
    period.parent.mkdir(parents=True)
    period.write_text("period\n")

    assert rw.worklist_for_period_task(load_config(repo), period) is None


def test_all_worklists_skips_parked_templates(repo: Path) -> None:
    cfg = load_config(repo)
    for name in ("autoclose-merged", "_parked", "other"):
        _seed_template(repo, name)
        (repo / "recurring" / name / rw.RETIRE_WORKLIST_FILENAME).write_text(
            rw.RETIRE_WORKLIST_HEADER
        )

    assert [p.parent.name for p in rw.all_worklists(cfg)] == ["autoclose-merged", "other"]


# --- retire's hook -------------------------------------------------------------


def test_discharge_slug_drops_only_a_discharged_entry(repo: Path, tmp_path: Path) -> None:
    cfg = load_config(repo)
    _seed_template(repo)
    path = rw.template_worklist_path(cfg, "autoclose-merged")
    live_dir = tmp_path / "preserved"
    live_dir.mkdir()
    rw.reconcile_worklist(
        cfg,
        path,
        root=repo,
        pending=[
            _entry("retired", branch="", worktree=str(tmp_path / "absent")),
            _entry("preserved", branch="", worktree=str(live_dir)),
        ],
    )

    assert rw.discharge_slug(cfg, "retired", root=repo) == [path]
    _, entries = rw.parse_worklist(path.read_text())
    assert [e.slug for e in entries] == ["preserved"]

    # A preserved checkout keeps its line, and the return value names only
    # the worklists the *requested* slug left.
    assert rw.discharge_slug(cfg, "preserved", root=repo) == []
    _, entries = rw.parse_worklist(path.read_text())
    assert [e.slug for e in entries] == ["preserved"]


def test_discharge_slug_leaves_a_worklist_that_never_named_the_slug_alone(
    repo: Path,
) -> None:
    cfg = load_config(repo)
    _seed_template(repo)
    path = rw.template_worklist_path(cfg, "autoclose-merged")
    path.write_text(rw.RETIRE_WORKLIST_HEADER + "\n" + _entry("other").render() + "\n")
    before = path.read_bytes()

    assert rw.discharge_slug(cfg, "unknown", root=repo) == []
    assert path.read_bytes() == before
