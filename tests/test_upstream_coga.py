"""The `recurring/upstream-coga` processor: `coga/recurring/upstream-coga/ticket.py`.

Ticket-owned deterministic logic, so it is loaded from its sibling path rather
than imported from the package.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from textwrap import dedent
from types import ModuleType

import pytest

from coga.config import load_config
from coga.taskfile import read_blackboard
from coga.tasks import list_tasks, read_ticket

REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_JOB = REPO_ROOT / "coga" / "recurring" / "upstream-coga"


def _load_processor() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "upstream_coga_ticket", LIVE_JOB / "ticket.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before exec: a dataclass under `from __future__ import
    # annotations` resolves its field types through `sys.modules`.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip())


def _entry(title: str, entry_id: str, *, repo: str = "multiply") -> str:
    return dedent(
        f"""
        ## {title}

        - id: {entry_id}
        - repo: {repo}
        - date: {entry_id[:10]}
        - class: drift
        - target: coga/recurring/dream/ticket.md
        - evidence: coga/contexts/{repo}/developer-flow/SKILL.md:44

        The client's developer-flow context says the Dream template names a
        recipe that `coga run` no longer registers.
        """
    )


HEADER = """
# Upstream Coga findings

Append-only. The Coga repo sweeps this file.
"""


@pytest.fixture
def client(tmp_path: Path) -> Path:
    checkout = tmp_path / "clients" / "multiply"
    _write(
        checkout / "coga" / "upstream-coga.md",
        HEADER
        + _entry("Phase 6 names a dead recipe", "2026-09-09-phase-6-names-a-dead-recipe")
        + _entry("Bump flag is undocumented", "2026-09-10-bump-flag-is-undocumented"),
    )
    return checkout


def _company(tmp_path: Path, checkouts: list[Path]) -> Path:
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
    listed = ", ".join(f'"{c}"' for c in checkouts)
    _write(
        company / "coga.local.toml",
        f"""
        user = "marc"
        [upstream]
        checkouts = [{listed}]
        """,
    )
    (company / "tasks").mkdir()
    (company / "recurring" / "upstream-coga").mkdir(parents=True)
    (company / "recurring" / "upstream-coga" / "ticket.md").write_bytes(
        (LIVE_JOB / "ticket.md").read_bytes()
    )
    return company


@pytest.fixture
def company(tmp_path: Path, client: Path) -> Path:
    return _company(tmp_path, [client])


@pytest.fixture
def synced(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, list[Path], str]]:
    calls: list[tuple[Path, list[Path], str]] = []
    monkeypatch.setattr(
        "coga.git.publish",
        lambda cfg, paths, message, **kw: calls.append(
            (list(paths)[0], list(paths), message)
        ),
    )
    return calls


def _run(company: Path) -> tuple[int, str]:
    import io

    out = io.StringIO()
    code = _load_processor().main(load_config(company), out=out)
    return code, out.getvalue()


def _template_cursors(company: Path) -> dict[str, str]:
    module = _load_processor()
    return module.read_cursors(
        read_blackboard(company / "recurring" / "upstream-coga" / "ticket.md")
    )


def test_live_job_is_shaped_like_the_other_script_backed_jobs() -> None:
    """Unpackaged on purpose: twins derive from the packaged tree, so there is
    nothing to register — but the live directory must be a complete job."""
    assert (LIVE_JOB / "ticket.py").is_file()
    text = (LIVE_JOB / "ticket.md").read_text()
    assert "schedule:" in text
    assert "workflow: upstream-coga/run" in text
    assert "## Upstream cursors" in text
    assert (REPO_ROOT / "coga" / "workflows" / "upstream-coga" / "run.md").is_file()
    packaged = REPO_ROOT / "src" / "coga" / "resources" / "templates" / "coga"
    assert not (packaged / "recurring" / "upstream-coga").exists()
    assert not (packaged / "workflows" / "upstream-coga").exists()


def test_parse_entries_reads_fields_then_prose() -> None:
    module = _load_processor()
    entries, problems = module.parse_entries(
        HEADER
        + _entry("Phase 6 names a dead recipe", "2026-09-09-phase-6-names-a-dead-recipe")
        + dedent(
            """
            ## Missing its fields

            - id: 2026-09-11-missing-its-fields

            No repo, date, class, target, or evidence.
            """
        )
    )
    assert [e.id for e in entries] == ["2026-09-09-phase-6-names-a-dead-recipe"]
    entry = entries[0]
    assert entry.title == "Phase 6 names a dead recipe"
    assert entry.repo == "multiply"
    assert entry.cls == "drift"
    assert entry.target == "coga/recurring/dream/ticket.md"
    assert entry.evidence.endswith("SKILL.md:44")
    assert entry.prose.startswith("The client's developer-flow context")
    assert problems == [
        "entry 'Missing its fields' is missing repo, date, class, target, evidence; skipped"
    ]


def test_first_run_files_every_entry_and_second_run_files_none(
    company: Path, client: Path, synced: list
) -> None:
    code, out = _run(company)
    assert code == 0
    cfg = load_config(company)
    refs = sorted(list_tasks(cfg), key=lambda r: r.slug)
    assert [r.slug for r in refs] == [
        "bump-flag-is-undocumented",
        "phase-6-names-a-dead-recipe",
    ]
    ticket = read_ticket(refs[1])
    assert ticket.frontmatter["status"] == "draft"
    assert ticket.frontmatter["workflow"] is None
    assert ticket.frontmatter["title"] == "Phase 6 names a dead recipe"
    body = ticket.body
    assert "- upstream-id: multiply/2026-09-09-phase-6-names-a-dead-recipe" in body
    for line in (
        "- repo: multiply",
        "- date: 2026-09-09",
        "- class: drift",
        "- target: coga/recurring/dream/ticket.md",
        "- evidence: coga/contexts/multiply/developer-flow/SKILL.md:44",
    ):
        assert line in body
    assert "The client's developer-flow context says" in body
    log = (company / "log.md").read_text()
    assert "[recurring/upstream-coga] created (status=draft)" in log
    assert _template_cursors(company) == {
        "multiply": "2026-09-10-bump-flag-is-undocumented"
    }
    # One publication covering the cursor and both tickets it accounts for.
    assert len(synced) == 1
    anchor, paths, message = synced[0]
    assert anchor == company / "recurring" / "upstream-coga" / "ticket.md"
    assert set(paths) == {anchor, *(r.path for r in refs), company / "log.md"}
    assert "2 upstream ticket(s)" in message

    code, out = _run(company)
    assert code == 0
    assert len(list_tasks(cfg)) == 2
    assert "0 ticket(s) filed, 0 entr(ies) seen" in out
    assert len(synced) == 1


def test_new_entries_after_the_cursor_are_filed_on_a_later_run(
    company: Path, client: Path, synced: list
) -> None:
    _run(company)
    with (client / "coga" / "upstream-coga.md").open("a") as f:
        f.write(_entry("Third thing", "2026-09-12-third-thing"))
    code, out = _run(company)
    assert code == 0
    assert "filed third-thing for 2026-09-12-third-thing" in out
    assert len(list_tasks(load_config(company))) == 3
    assert _template_cursors(company) == {"multiply": "2026-09-12-third-thing"}


def test_missing_checkout_and_missing_file_are_notes_not_errors(
    tmp_path: Path, synced: list
) -> None:
    gone = tmp_path / "clients" / "gone"
    bare = tmp_path / "clients" / "bare"
    bare.mkdir(parents=True)
    company = _company(tmp_path, [gone, bare])
    code, out = _run(company)
    assert code == 0
    assert f"gone: checkout {gone} not found; skipped." in out
    assert "bare: no coga/upstream-coga.md; skipped." in out
    assert list_tasks(load_config(company)) == []
    assert synced == []


def test_no_configured_checkouts_is_a_note(tmp_path: Path, synced: list) -> None:
    company = _company(tmp_path, [])
    code, out = _run(company)
    assert code == 0
    assert "no checkouts configured" in out
    assert synced == []


def test_truncated_file_stops_that_checkout_instead_of_refiling(
    company: Path, client: Path, synced: list
) -> None:
    """A cursor id that vanished means the append-only contract was broken;
    re-filing the whole file silently would be the worse failure."""
    _run(company)
    _write(
        client / "coga" / "upstream-coga.md",
        HEADER + _entry("Rewritten from scratch", "2026-09-13-rewritten"),
    )
    code, out = _run(company)
    assert code == 0
    assert "cursor 2026-09-10-bump-flag-is-undocumented is no longer in" in out
    assert "truncated or rewritten" in out
    assert len(list_tasks(load_config(company))) == 2
    assert _template_cursors(company) == {
        "multiply": "2026-09-10-bump-flag-is-undocumented"
    }
    assert len(synced) == 1


def test_interrupted_run_does_not_refile_a_ticket_that_already_exists(
    company: Path, client: Path, synced: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ticket created, cursor never written: the `upstream-id` line on the
    ticket — not the cursor — is what keeps the retry from filing it twice."""
    module = _load_processor()
    monkeypatch.setattr(
        module,
        "write_cursor",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("power cut")),
    )
    with pytest.raises(RuntimeError, match="power cut"):
        module.main(load_config(company))
    cfg = load_config(company)
    assert [r.slug for r in list_tasks(cfg)] == ["phase-6-names-a-dead-recipe"]
    assert _template_cursors(company) == {}

    code, out = _run(company)
    assert code == 0
    assert "2026-09-09-phase-6-names-a-dead-recipe already filed; skipped." in out
    assert sorted(r.slug for r in list_tasks(cfg)) == [
        "bump-flag-is-undocumented",
        "phase-6-names-a-dead-recipe",
    ]
    assert _template_cursors(company) == {
        "multiply": "2026-09-10-bump-flag-is-undocumented"
    }


def test_same_directory_name_twice_files_nothing_for_either(
    tmp_path: Path, synced: list
) -> None:
    a = tmp_path / "work" / "a" / "product"
    b = tmp_path / "work" / "b" / "product"
    for checkout, entry_id in ((a, "2026-09-09-from-a"), (b, "2026-09-09-from-b")):
        _write(
            checkout / "coga" / "upstream-coga.md",
            HEADER + _entry(f"From {checkout.parent.name}", entry_id),
        )
    company = _company(tmp_path, [a, b])
    code, out = _run(company)
    assert code == 0
    assert "product: ambiguous checkout name shared by" in out
    assert list_tasks(load_config(company)) == []
    assert _template_cursors(company) == {}
    assert synced == []


def test_directory_name_with_whitespace_is_skipped_with_a_note(
    tmp_path: Path, synced: list
) -> None:
    """The cursor line and `upstream-id:` are single tokens: a key with a
    space could be written but never read back, re-filing on every run."""
    checkout = tmp_path / "work" / "my client"
    _write(
        checkout / "coga" / "upstream-coga.md",
        HEADER + _entry("From a spaced directory", "2026-09-09-spaced"),
    )
    company = _company(tmp_path, [checkout])
    code, out = _run(company)
    assert code == 0
    assert f"[upstream] {checkout}: directory name 'my client' contains whitespace" in out
    assert list_tasks(load_config(company)) == []
    assert _template_cursors(company) == {}
    assert synced == []


def test_same_path_listed_twice_is_one_checkout(
    tmp_path: Path, client: Path, synced: list
) -> None:
    company = _company(tmp_path, [client, client])
    code, out = _run(company)
    assert code == 0
    assert "ambiguous" not in out
    assert len(list_tasks(load_config(company))) == 2


def test_malformed_entry_is_reported_and_the_rest_still_file(
    company: Path, client: Path, synced: list
) -> None:
    with (client / "coga" / "upstream-coga.md").open("a") as f:
        f.write("\n## No fields at all\n\nJust prose.\n")
    code, out = _run(company)
    assert code == 0
    assert "entry 'No fields at all' is missing id, repo, date, class, target, evidence; skipped" in out
    assert len(list_tasks(load_config(company))) == 2
