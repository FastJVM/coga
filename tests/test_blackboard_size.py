"""The bundled `blackboard-size` recurring job and the stale-note cleanup rule.

The job is a wheel-owned edge module (`coga_edge.blackboard_size`, selected by
the packaged `recurring/blackboard-size/ticket.py` shim) that reports
`coga validate --json`'s `large-blackboard` findings. It runs here end to end against a copy of the seeded fixture, selected through
`recurring/jobs.toml` exactly as a repo would select it.
"""

from __future__ import annotations

import shutil
from importlib.resources import files
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coga.blackboard import BLACKBOARD_WARN_BYTES, blackboard_size_warning
from coga.cli import app
from coga.compose import compose_prompt
from coga.config import load_config
from coga.create import create_task
from coga.recurring import create_named
from coga.taskfile import read_blackboard, replace_blackboard
from coga.tasks import read_ticket, resolve_task
from coga_edge import blackboard_size


REPO_ROOT = Path(__file__).resolve().parents[1]
SEEDED_REPO = REPO_ROOT / "tests" / "fixtures" / "seeded-repo"
PACKAGED = REPO_ROOT / "src" / "coga" / "resources" / "templates" / "coga"
TOPIC = PACKAGED / "bootstrap" / "contexts" / "coga" / "blackboard" / "SKILL.md"


@pytest.fixture
def seeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway copy of the seeded fixture repo with the job selected."""
    dest = tmp_path / "example"
    shutil.copytree(
        SEEDED_REPO,
        dest,
        ignore=shutil.ignore_patterns(".claude", ".codex", ".git", ".venv*", "venv"),
        ignore_dangling_symlinks=True,
    )
    (dest / "coga" / "recurring" / "jobs.toml").write_text(
        "[jobs]\nblackboard-size = true\n", encoding="utf-8", newline="\n"
    )
    monkeypatch.chdir(dest / "coga")
    return dest / "coga"


def _task_with_notes(coga_root: Path, title: str, notes_bytes: int) -> str:
    cfg = load_config(coga_root)
    slug = create_task(
        cfg=cfg, title=title, workflow_name=None, contexts=[],
        owner="marc", status="draft",
    )["slug"]
    ref = resolve_task(cfg, slug)
    replace_blackboard(ref.ticket_path, "\n## Notes\n\n" + "n" * notes_bytes + "\n")
    return ref.id_slug


def test_period_reports_only_the_oversized_blackboard(seeded: Path) -> None:
    """Fixture: one blackboard above the threshold, one below it."""
    big = _task_with_notes(seeded, "Big notes", BLACKBOARD_WARN_BYTES + 4 * 1024)
    small = _task_with_notes(seeded, "Small notes", 2 * 1024)
    cfg = load_config(seeded)
    ref = create_named(cfg, "blackboard-size").ref

    result = CliRunner().invoke(app, ["launch", ref.id_slug])

    assert result.exit_code == 0, result.output
    # The alert is informational: the period closes, nothing is blocked.
    assert read_ticket(ref).status == "done"
    assert read_ticket(resolve_task(cfg, big)).status == "draft"
    report = read_blackboard(ref.ticket_path)
    assert "## Oversized blackboards" in report
    assert "Threshold: 32.0 KiB" in report
    assert f"- `{big}` — 36.0 KiB" in report
    assert small not in report


def test_report_with_no_oversized_blackboard_says_so() -> None:
    assert "No ticket blackboard exceeds the 32.0 KiB threshold." in (
        blackboard_size.render_report([])
    )


def test_reads_size_from_the_validator_warning(tmp_path: Path) -> None:
    """Pins the message format the script parses back out of the finding."""
    ticket = tmp_path / "ticket.md"
    ticket.write_text(
        "---\ntitle: T\n---\n\n<!-- coga:blackboard -->\n\n" + "x" * 2000 + "\n",
        encoding="utf-8", newline="\n",
    )
    message = blackboard_size_warning(ticket, max_bytes=1024)
    assert message is not None
    found = blackboard_size.oversized_blackboards({"issues": [
        {"kind": "large-blackboard", "task": "t", "message": message, "severity": "warn"},
        {"kind": "missing-file", "task": "u", "message": "missing ticket.md", "severity": "error"},
    ]})

    assert [(item.task, item.size) for item in found] == [("t", "2.0 KiB")]


def test_unreadable_finding_fails_rather_than_dropping_it() -> None:
    with pytest.raises(ValueError, match="cannot read the size"):
        blackboard_size.oversized_blackboards({"issues": [
            {"kind": "large-blackboard", "task": "t", "message": "reworded"},
        ]})


def test_ticket_prompt_carries_the_stale_note_cleanup_pass(seeded: Path) -> None:
    """The ordinary ticket loop tells the agent to clean as it reads."""
    cfg = load_config(seeded)
    slug = create_task(
        cfg=cfg, title="Resume me", workflow_name="code/with-review",
        contexts=[], owner="marc", agent="claude", status="active",
    )["slug"]
    ref = resolve_task(cfg, slug)
    prompt = " ".join(compose_prompt(cfg, ref, read_ticket(ref)).split())

    for clause in (
        "whether the ticket is new to you or resumed, delete notes that clearly "
        "no longer help the work",
        "Age only prompts the check.",
        "Keep current decisions and their reasons, open blockers, the worklist, "
        "and verification evidence the handoff still needs.",
        "This light pass needs no separate review; if unsure, keep the note.",
        "`coga/blackboard` (\"Stale-note cleanup\") owns this policy.",
    ):
        assert clause in prompt, clause


def test_ticket_layer_and_owning_topic_agree() -> None:
    layer = files("coga.resources").joinpath("prompt-ticket.md").read_text(encoding="utf-8")
    topic = TOPIC.read_text(encoding="utf-8")
    assert "## Stale-note cleanup" in topic
    for kept in (
        "## Dev", "## Blockers", "## Blocker reminders", "## Recipe Failure", "## PR",
        "## Superseded designs", "## Evaluator review", "## Production notes",
    ):
        assert kept in layer and kept in topic, kept
    assert "`blackboard-size` recurring job" in topic
