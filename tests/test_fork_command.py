"""`coga fork` / `coga fork-copy`: the packaged `bootstrap/fork` script ticket.

Resolution, reporting and copying run in-process against copies of the seeded
`tests/fixtures/seeded-repo/` fixture; alias dispatch and the read-only
boundary run through the real CLI. Installed-wheel cases live in
`tests/test_edge_distribution.py`.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coga.cli import app
from coga.config import load_config
from coga.paths import packaged_template_path
from coga.recurring import resolve_template_source
from coga.recurring_state import render_carrier
from coga.repl_supervisor import ReplOutcome
from coga.taskfile import read_blackboard

from conftest import windows_skip


ROOT = Path(__file__).resolve().parents[1]
SEEDED_REPO = ROOT / "tests" / "fixtures" / "seeded-repo"
FORK_SCRIPT = ROOT / "src/coga/resources/templates/coga/bootstrap/fork/ticket.py"
PACKAGED = ROOT / "src/coga/resources/templates/coga"


def _load_fork_script():
    """Import the packaged script; its `__main__` guard keeps loading inert."""
    spec = importlib.util.spec_from_file_location("coga_bootstrap_fork", FORK_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through it
    spec.loader.exec_module(module)
    return module


fork = _load_fork_script()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    shutil.copytree(SEEDED_REPO, tmp_path / "repo", ignore=shutil.ignore_patterns("__pycache__"))
    coga_os = tmp_path / "repo" / "coga"
    monkeypatch.chdir(coga_os)
    return coga_os


def _run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = fork.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def _inspect_json(capsys, target: str) -> tuple[int, dict]:  # type: ignore[no-untyped-def]
    code, out, _ = _run(capsys, "inspect", target, "--json")
    return code, json.loads(out)


def _record(payload: dict, typed: str) -> dict:
    return next(r for r in payload["records"] if r["typed_ref"] == typed)


def _tree(root: Path) -> dict[Path, bytes]:
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


# --- ticket.py classification (ast only) ---------------------------------------


@pytest.mark.parametrize(("template", "module"), [
    ("phone-home", "coga_edge.phone_home"),
    ("trim-log", "coga_edge.trim_log"),
])
def test_shipped_edge_shims_lead_to_completely_forkable_modules(template: str, module: str) -> None:
    info = fork.describe_script(PACKAGED / "recurring" / template / "ticket.py")
    assert info["kind"] == "edge shim" and info["module"] == module
    assert Path(info["implementation"]).name == module.split(".")[1] + ".py"
    assert info["forkable"] is True and info["causes"] == []
    assert "coga.config" in info["core_dependencies"]


@pytest.mark.parametrize(("template", "recipe"), [
    ("skill-update", "skill-update"),
    ("autoclose-merged", "autoclose"),
    ("blocker-reminders", "blocker-reminders"),
    ("branch-sweep", "branch-sweep"),
])
def test_recipe_adapters_name_their_kernel_recipe(template: str, recipe: str) -> None:
    info = fork.describe_script(PACKAGED / "recurring" / template / "ticket.py")
    assert info["kind"] == "recipe adapter" and info["recipe"] == recipe
    assert info["forkable"] is False


def test_other_scripts_are_full_scripts_and_never_imported(tmp_path: Path) -> None:
    assert fork.classify_script(PACKAGED / "bootstrap/retire/ticket.py")["kind"] == "full script"
    # Running this file would fail loudly; classification only parses it.
    bomb = tmp_path / "ticket.py"
    bomb.write_text("raise SystemExit('imported')\nfrom coga_edge.x import main\n", encoding="utf-8")
    assert fork.classify_script(bomb)["kind"] == "full script"


@pytest.mark.parametrize("guard", [
    "if __name__ == '__main__':\n    print('custom behavior')\n",
    "if __name__ == '__main__':\n    main()\n    print('extra')\n",
    "if __name__ != '__main__':\n    main()\n",
    "if __name__ == '__main__':\n    main()\nelse:\n    print('extra')\n",
    "if __name__ == '__main__':\n    main('custom argument')\n",
])
def test_custom_guard_is_a_full_script(tmp_path: Path, guard: str) -> None:
    script = tmp_path / "ticket.py"
    script.write_text("from coga_edge.trim_log import main\n" + guard, encoding="utf-8")
    assert fork.classify_script(script)["kind"] == "full script"


@pytest.mark.parametrize(("source", "cause"), [
    ("from . import helper\nif __name__ == '__main__':\n    pass\n", "relative import"),
    ("from coga_edge.other import x\nif __name__ == '__main__':\n    pass\n", "imports coga_edge.other"),
    ("import coga.config\ndef main():\n    return 0\n", "__main__"),
])
def test_edge_module_that_is_not_self_contained_names_the_cause(tmp_path: Path, source: str, cause: str) -> None:
    module = tmp_path / "edge.py"
    module.write_text(source, encoding="utf-8")
    info = fork.inspect_edge_module(module)
    assert info["forkable"] is False
    assert any(cause in c for c in info["causes"]), info["causes"]


# --- discovery -------------------------------------------------------------------


def test_untyped_word_resolves_alias_then_builtin_then_task_then_definition(repo: Path, capsys) -> None:
    code, out, _ = _run(capsys, "inspect", "fork")
    assert code == 0
    assert "alias fork = 'launch --read-only bootstrap/fork -- inspect' (default alias)" in out
    assert "bootstrap: fork" in out and "full script" in out

    code, out, _ = _run(capsys, "inspect", "status")
    assert code == 0
    assert "built-in command status" in out
    assert "kernel primitive (not an editable ticket)" in out
    assert "commands/status.py" in out and "customize:" not in out

    code, out, _ = _run(capsys, "inspect", "declined-dream")
    assert code == 0 and "task: declined-dream-finding" in out

    code, out, _ = _run(capsys, "inspect", "code/with-review")
    assert code == 0 and "  workflow code/with-review" in out


def test_alias_to_kernel_recipe_is_reported_not_forkable(repo: Path, capsys) -> None:
    code, payload = _inspect_json(capsys, "open-pr")
    assert code == 0
    [record] = payload["records"]
    assert record["kind"] == "recipe" and record["state"] == fork.KERNEL
    assert record["details"]["module"] == "coga.open_pr"
    code, _, err = _run(capsys, "copy", "open-pr")
    assert code == 1 and "kernel primitive" in err


def test_user_alias_overrides_a_default_alias(repo: Path, capsys) -> None:
    config = repo / "coga.toml"
    config.write_text(config.read_text(encoding="utf-8").replace(
        'chat = "launch bootstrap/orient"', 'chat = "recurring launch dream"'), encoding="utf-8")
    code, out, _ = _run(capsys, "inspect", "chat")
    assert code == 0
    assert "alias chat = 'recurring launch dream' (coga.toml [aliases]) -> recurring job dream" in out
    assert "recurring: dream" in out


def test_unknown_and_ambiguous_targets_exit_1_listing_what_was_checked(repo: Path, capsys) -> None:
    code, out, err = _run(capsys, "inspect", "no-such-thing")
    assert code == 1 and out == ""
    assert "unknown target 'no-such-thing'" in err
    for checked in ("alias", "built-in command", "task ref", "workflow", "skill", "context",
                    "bootstrap", "recurring", "resource"):
        assert f"checked {checked}" in err
    # `direct/body` is both a workflow and a skill.
    code, _, err = _run(capsys, "inspect", "direct/body")
    assert code == 1 and "ambiguous target" in err
    assert "workflow:direct/body" in err and "skill:direct/body" in err


def test_report_records_and_references(repo: Path, capsys) -> None:
    code, payload = _inspect_json(capsys, "recurring:phone-home")
    assert code == 0 and payload["broken"] is False
    job = _record(payload, "recurring:phone-home")
    assert set(job) == {
        "kind", "ref", "typed_ref", "state", "origin", "selected", "packaged", "override",
        "details", "references", "script", "return_to_stock", "broken",
    }
    assert job["state"] == "stock" and job["origin"] == "package"
    assert job["override"] == str(repo / "recurring" / "phone-home")
    # No jobs.toml entry: the bundled job is available but unselected.
    assert job["details"]["selection"] == "unselected"
    assert job["details"]["state carrier"] == str(repo / "recurring/phone-home/ticket.md")
    assert job["script"]["kind"] == "edge shim"
    assert job["references"] == ["workflow:phone-home/run"]
    workflow = _record(payload, "workflow:phone-home/run")
    assert workflow["details"]["steps"][0]["checkout"] == "manual"


def test_workflow_lists_step_skills_with_their_checkout(repo: Path, capsys) -> None:
    (repo / "workflows/code/with-review.md").unlink()
    code, payload = _inspect_json(capsys, "workflow:code/with-review")
    assert code == 0
    steps = {s["name"]: s for s in _record(payload, "workflow:code/with-review")["details"]["steps"]}
    assert steps["peer-review"]["checkout"] == "reuse-required"
    assert steps["peer-review"]["skills"] == ["code/peer-review"]
    assert _record(payload, "skill:code/peer-review")["state"] == "stock"


def test_local_precedence_and_fork_states(repo: Path, capsys) -> None:
    code, payload = _inspect_json(capsys, "workflow:code/with-review")
    record = _record(payload, "workflow:code/with-review")
    assert record["origin"] == "local" and record["selected"] == record["override"]
    assert record["state"] == fork.MODIFIED
    assert record["return_to_stock"] == [f"delete {record['override']}"]

    code, payload = _inspect_json(capsys, "workflow:deterministic/check")
    assert _record(payload, "workflow:deterministic/check")["state"] == fork.LOCAL_ONLY

    shutil.copytree(PACKAGED / "bootstrap/skills/code/peer-review", repo / "skills/code/peer-review")
    code, payload = _inspect_json(capsys, "skill:code/peer-review")
    assert _record(payload, "skill:code/peer-review")["state"] == fork.IDENTICAL
    skill = repo / "skills/code/peer-review/SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "\nLocal note.\n", encoding="utf-8")
    code, payload = _inspect_json(capsys, "skill:code/peer-review")
    assert _record(payload, "skill:code/peer-review")["state"] == fork.MODIFIED


def _break(repo: Path, kind: str) -> str:
    if kind == "workflow":
        (repo / "workflows/code/with-review.md").unlink()
        (repo / "workflows/code/with-review.md").mkdir()
        return "workflow:code/with-review"
    if kind == "skill":
        (repo / "skills/code/peer-review").mkdir(parents=True)
        (repo / "skills/code/peer-review/notes.md").write_text("orphan\n", encoding="utf-8")
        return "skill:code/peer-review"
    if kind == "bootstrap":
        (repo / "bootstrap/retire").mkdir(parents=True)
        (repo / "bootstrap/retire/ticket.py").write_text("print('x')\n", encoding="utf-8")
        return "bootstrap/retire"
    if kind == "recurring":
        parent = repo / "recurring/phone-home"
        parent.mkdir(parents=True)
        (parent / "ticket.md").write_text(render_carrier("\n"), encoding="utf-8")
        (parent / "ticket.py").write_text("print('stray')\n", encoding="utf-8")
        return "recurring:phone-home"
    if kind == "resource":
        (repo / "resources/prompt.md").mkdir(parents=True)
        return "resource:prompt.md"
    assert kind == "context"
    (repo / "contexts/coga/edge-code").mkdir(parents=True)
    (repo / "contexts/coga/edge-code/SKILL.md").symlink_to(repo / "context.md")
    return "context:coga/edge-code"


@pytest.mark.parametrize("kind", ["workflow", "skill", "bootstrap", "recurring", "resource",
                                  pytest.param("context", marks=windows_skip("symlink fixture"))])
def test_broken_override_is_reported_never_package_fallback(repo: Path, capsys, kind: str) -> None:
    target = _break(repo, kind)
    code, out, err = _run(capsys, "inspect", target, "--json")
    assert code == 1
    record = _record(json.loads(out), target if ":" in target else "bootstrap:retire")
    assert record["broken"] and record["state"].startswith("broken: ")
    assert record["selected"] == record["override"] or kind == "recurring"
    assert record["selected"] != record["packaged"]
    assert "is broken: " in err
    code, _, err = _run(capsys, "copy", target)
    assert code == 1 and "refused" in err


def test_custom_contexts_root_is_the_override_destination(repo: Path, capsys) -> None:
    config = repo / "coga.toml"
    config.write_text(config.read_text(encoding="utf-8") + '\n[layout]\ncontexts = "docs/contexts"\n',
                      encoding="utf-8")
    (repo.parent / "docs/contexts").mkdir(parents=True)
    (repo.parent / "docs/contexts/.gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo.parent, check=True)
    cfg = load_config(repo)
    code, payload = _inspect_json(capsys, "context:coga/edge-code")
    record = _record(payload, "context:coga/edge-code")
    assert record["override"] == str(cfg.contexts_root / "coga/edge-code")
    code, out, _ = _run(capsys, "copy", "context:coga/edge-code")
    assert code == 0
    assert (cfg.contexts_root / "coga/edge-code/SKILL.md").read_bytes() == \
        (PACKAGED / "bootstrap/contexts/coga/edge-code/SKILL.md").read_bytes()
    # Nested contexts are separate refs and are not copied with their parent.
    assert not (cfg.contexts_root / "coga/edge-code/edge-code-upgrades").exists()
    assert (cfg.contexts_root / "coga/edge-code/edge-code-upgrades.md").is_file()
    code, payload = _inspect_json(capsys, "context:coga/edge-code")
    assert _record(payload, "context:coga/edge-code")["state"] == fork.IDENTICAL


def test_task_separates_frozen_snapshot_from_live_resolution(repo: Path, capsys) -> None:
    code, payload = _inspect_json(capsys, "task:auto/deterministic-repo-check")
    assert code == 0
    task = payload["records"][0]
    assert task["kind"] == "task"
    assert "frozen workflow" in task["details"]
    assert "(not used by this ticket's frozen snapshot)" in task["details"]["live workflow file"]
    assert task["script"]["kind"] == "full script"
    code, payload = _inspect_json(capsys, "task:declined-dream-finding")
    task = payload["records"][0]
    assert task["details"]["frozen workflow"] == "code/with-review"
    assert [s["name"] for s in task["details"]["frozen steps"]][:2] == ["implement", "pr"]
    assert "skill:infra/testing-conventions" in task["references"]
    assert _record(payload, "skill:infra/testing-conventions")["origin"] == "local"
    code, _, err = _run(capsys, "copy", "task:declined-dream-finding")
    assert code == 1 and "only packaged definitions" in err


# --- copying ---------------------------------------------------------------------


def test_malformed_bootstrap_is_reported_as_broken(repo: Path, capsys) -> None:
    parent = repo / "bootstrap/retire"
    parent.mkdir(parents=True)
    (parent / "ticket.md").write_text("---\ntitle: [\n---\n", encoding="utf-8")
    code, out, err = _run(capsys, "inspect", "bootstrap:retire", "--json")
    assert code == 1
    record = _record(json.loads(out), "bootstrap:retire")
    assert record["broken"] and "Invalid YAML" in record["state"]
    assert "is broken:" in err


@windows_skip("POSIX executable permission bits; Windows uses interpreter dispatch")
def test_forked_skill_preserves_executable_attachments(repo: Path, capsys) -> None:
    code, out, err = _run(capsys, "copy", "skill:coga/gmail")
    assert code == 0, out + err
    script = repo / "skills/coga/gmail/gmail.py"
    source = PACKAGED / "bootstrap/skills/coga/gmail/gmail.py"
    assert script.stat().st_mode & 0o111 == source.stat().st_mode & 0o111
    assert os.access(script, os.X_OK)
    assert script.read_bytes() == source.read_bytes()


@pytest.mark.parametrize(("target", "dest", "definition"), [
    ("workflow:docs/with-review", "workflows/docs/with-review.md", None),
    ("skill:code/peer-review", "skills/code/peer-review", "SKILL.md"),
    ("bootstrap:retire", "bootstrap/retire", "ticket.md"),
    ("resource:retire.md", "resources/retire.md", None),
])
def test_copy_writes_the_packaged_artifact_definition_last(
    repo: Path, capsys, monkeypatch: pytest.MonkeyPatch, target: str, dest: str, definition: str | None,
) -> None:
    kind, ref = target.split(":")
    packaged = {
        "workflow": PACKAGED / f"bootstrap/workflows/{ref}.md",
        "skill": PACKAGED / f"bootstrap/skills/{ref}",
        "bootstrap": PACKAGED / f"bootstrap/{ref}",
        "resource": ROOT / f"src/coga/resources/{ref}",
    }[kind]
    written: list[Path] = []
    real = fork.atomic_write_bytes
    monkeypatch.setattr(fork, "atomic_write_bytes", lambda p, d: (written.append(p), real(p, d)))
    tasks = _tree(repo / "tasks")
    code, out, _ = _run(capsys, "copy", target)
    assert code == 0, out
    destination = repo / dest
    assert written[-1] == (destination / definition if definition else destination)
    if definition:
        expected = {p.relative_to(packaged): p.read_bytes() for p in packaged.rglob("*")
                    if p.is_file() and "__pycache__" not in p.parts}
        assert {p.relative_to(destination): d for p, d in _tree(destination).items()} == expected
    else:
        assert destination.read_bytes() == packaged.read_bytes()
    assert f"Forked {target} to {destination}" in out
    assert "return to stock:" in out
    assert _tree(repo / "tasks") == tasks
    code, payload = _inspect_json(capsys, target)
    assert _record(payload, target)["state"] == fork.IDENTICAL


def test_copy_refuses_existing_local_and_conflicting_entries_before_writing(repo: Path, capsys) -> None:
    code, _, err = _run(capsys, "copy", "workflow:code/with-review")
    assert code == 1
    assert f"already a local override at {repo / 'workflows/code/with-review.md'}" in err

    (repo / "bootstrap/retire").mkdir(parents=True)
    (repo / "bootstrap/retire/ticket.md").write_text("---\ntitle: x\n---\n", encoding="utf-8")
    code, _, err = _run(capsys, "copy", "bootstrap:retire")
    assert code == 1 and "already a local override" in err

    # Files beside a nested ref are a broken override; conflicts list them.
    before = _tree(repo)
    code, _, err = _run(capsys, "copy", "context:missing-in-package")
    assert code == 1
    assert _tree(repo) == before


def test_copy_lists_every_conflicting_destination_entry(repo: Path, capsys) -> None:
    parent = repo / "recurring/phone-home"
    parent.mkdir(parents=True)
    (parent / "operations.md").write_text("mine\n", encoding="utf-8")
    (parent / "ticket.py").write_text("mine\n", encoding="utf-8")
    before = _tree(repo)
    code, _, err = _run(capsys, "copy", "recurring:phone-home")
    assert code == 1
    # Definition files with no ticket.md are an incomplete parent.
    assert "no ticket.md" in err or "operations.md" in err
    assert _tree(repo) == before

    shutil.rmtree(parent)

    # Ordinary conflicts: every existing destination entry is listed and
    # nothing is written. A plain file where a directory belongs conflicts too.
    record = fork.definition_record(load_config(repo), "bootstrap", "retire")
    destination = repo / "bootstrap/retire"
    destination.mkdir(parents=True)
    record.origin = "package"  # the stray files would otherwise read as broken
    record.state = "stock"
    (destination / "ticket.py").write_text("mine\n", encoding="utf-8")
    before = _tree(repo)
    with pytest.raises(fork.CopyRefused) as refused:
        fork.copy_definition(load_config(repo), record)
    assert str(destination / "ticket.py") in str(refused.value)
    assert _tree(repo) == before

    record = fork.definition_record(load_config(repo), "workflow", "docs/with-review")
    (repo / "workflows/docs").write_text("not a directory\n", encoding="utf-8")
    with pytest.raises(fork.CopyRefused) as refused:
        fork.copy_definition(load_config(repo), record)
    assert str(repo / "workflows/docs") in str(refused.value)


def test_interrupted_copy_is_visible_as_a_broken_override(repo: Path, capsys, monkeypatch) -> None:
    real = fork.atomic_write_bytes

    def crash(path: Path, data: bytes) -> None:
        if path.name == "ticket.md":
            raise OSError("disk full")
        real(path, data)

    monkeypatch.setattr(fork, "atomic_write_bytes", crash)
    with pytest.raises(OSError):
        fork.main(["copy", "bootstrap:retire"])
    capsys.readouterr()
    monkeypatch.setattr(fork, "atomic_write_bytes", real)
    code, payload = _inspect_json(capsys, "bootstrap:retire")
    assert code == 1 and _record(payload, "bootstrap:retire")["broken"]


def test_recurring_edge_shim_fork_is_the_real_implementation(repo: Path, capsys) -> None:
    import coga_edge.phone_home as phone_home

    code, out, _ = _run(capsys, "copy", "recurring:phone-home")
    assert code == 0
    local = repo / "recurring/phone-home"
    assert (local / "ticket.py").read_bytes() == Path(phone_home.__file__).read_bytes()
    assert (local / "ticket.md").read_bytes() == (PACKAGED / "recurring/phone-home/ticket.md").read_bytes()
    assert "ticket.py is the implementation, copied from" in out
    # A local definition with no jobs.toml entry is selected.
    assert "selection: recurring/phone-home is now enabled" in out
    assert "add `phone-home = false` under [jobs]" in out
    assert "coga fork-copy workflow:phone-home/run" in out
    source = resolve_template_source(load_config(repo), "phone-home")
    assert source.origin == "local" and source.enabled
    code, payload = _inspect_json(capsys, "recurring:phone-home")
    job = _record(payload, "recurring:phone-home")
    assert job["state"] == fork.IDENTICAL and job["script"]["kind"] == "full script"


def test_disabled_recurring_fork_stays_disabled(repo: Path, capsys) -> None:
    (repo / "recurring/jobs.toml").write_text("[jobs]\nphone-home = false\n", encoding="utf-8")
    code, out, _ = _run(capsys, "copy", "recurring:phone-home")
    assert code == 0
    assert "is now disabled" in out and "to keep it off" not in out
    assert (repo / "recurring/jobs.toml").read_text(encoding="utf-8") == "[jobs]\nphone-home = false\n"


def test_recipe_adapter_is_copied_unchanged_and_says_so(repo: Path, capsys) -> None:
    code, out, _ = _run(capsys, "copy", "recurring:skill-update")
    assert code == 0
    assert (repo / "recurring/skill-update/ticket.py").read_bytes() == \
        (PACKAGED / "recurring/skill-update/ticket.py").read_bytes()
    assert "implementation not forked: kernel recipe skill-update" in out


def _carrier(repo: Path, name: str) -> tuple[Path, str]:
    parent = repo / "recurring" / name
    parent.mkdir(parents=True)
    region = "\n\n## Saved state\n\nperiod_state: 2026-W45\n"
    (parent / "ticket.md").write_text(render_carrier(region), encoding="utf-8", newline="\n")
    (parent / "retires.md").write_text("- old-slug\n", encoding="utf-8", newline="\n")
    return parent, region


def test_carrier_converts_to_a_full_definition_and_returns_to_stock(repo: Path, capsys) -> None:
    parent, region = _carrier(repo, "phone-home")
    code, payload = _inspect_json(capsys, "recurring:phone-home")
    assert _record(payload, "recurring:phone-home")["details"]["state kind"] == "carrier"

    code, out, _ = _run(capsys, "copy", "recurring:phone-home")
    assert code == 0 and "converted the state-only carrier" in out
    packaged = (PACKAGED / "recurring/phone-home/ticket.md").read_text(encoding="utf-8")
    text = (parent / "ticket.md").read_text(encoding="utf-8")
    assert text.endswith("<!-- coga:blackboard -->" + region)
    assert text.split("<!-- coga:blackboard -->")[0] == packaged.split("<!-- coga:blackboard -->")[0]
    assert (parent / "retires.md").read_text(encoding="utf-8") == "- old-slug\n"
    code, payload = _inspect_json(capsys, "recurring:phone-home")
    job = _record(payload, "recurring:phone-home")
    assert job["origin"] == "local" and job["state"] == fork.IDENTICAL

    # The documented return-to-stock procedure, step by step.
    ticket = parent / "ticket.md"
    blackboard = read_blackboard(ticket)
    ticket.write_text(render_carrier(blackboard), encoding="utf-8", newline="\n")
    for child in parent.iterdir():
        if child.name not in {"ticket.md", "retires.md"}:
            child.unlink()
    assert read_blackboard(ticket).encode() == region.encode()
    source = resolve_template_source(load_config(repo), "phone-home")
    assert source.origin == "package" and source.error is None
    assert (parent / "retires.md").is_file()


@pytest.mark.parametrize("shape", ["parked", "incomplete"])
def test_recurring_copy_refuses_parked_or_incomplete_parents(repo: Path, capsys, shape: str) -> None:
    if shape == "parked":
        (repo / "recurring/_phone-home").mkdir(parents=True)
        (repo / "recurring/_phone-home/retires.md").write_text("", encoding="utf-8")
    else:
        _carrier(repo, "phone-home")
        (repo / "recurring/phone-home/operations.md").write_text("mine\n", encoding="utf-8")
    before = _tree(repo)
    code, _, err = _run(capsys, "copy", "recurring:phone-home")
    assert code == 1 and "refused" in err
    assert _tree(repo) == before


@pytest.mark.parametrize("kind", ["workflow", "skill"])
def test_return_to_stock_by_deletion_resolves_the_package(repo: Path, capsys, kind: str) -> None:
    target = {"workflow": "workflow:docs/with-review", "skill": "skill:code/peer-review"}[kind]
    assert _run(capsys, "copy", target)[0] == 0
    code, payload = _inspect_json(capsys, target)
    record = _record(payload, target)
    path = Path(record["override"])
    shutil.rmtree(path) if path.is_dir() else path.unlink()
    code, payload = _inspect_json(capsys, target)
    record = _record(payload, target)
    assert record["origin"] == "package" and record["state"] == "stock"
    assert record["selected"] == record["packaged"]


# --- through the real CLI --------------------------------------------------------


def _cli(coga_os: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("COGA_") and k != "SLACK_WEBHOOK_URL"}
    env.update(PYTHONPATH=str(ROOT / "src"), PYTHONIOENCODING="utf-8", PATH="/agents-absent"
               if os.name != "nt" else str(Path(shutil.which("git")).parent))
    return subprocess.run([sys.executable, "-m", "coga.cli", *argv], cwd=coga_os, env=env,
                          capture_output=True, text=True, encoding="utf-8", timeout=60)


def test_fork_alias_is_read_only_with_no_user_and_dirty_files(repo: Path) -> None:
    root = repo.parent
    local = repo / "coga.local.toml"
    local.write_text(local.read_text(encoding="utf-8").replace('user = "marc"', ""), encoding="utf-8")
    shared = repo / "coga.toml"
    shared.write_text(shared.read_text(encoding="utf-8") + "\n[git]\nenabled = true\n", encoding="utf-8")
    for args in (["init", "-b", "main"], ["add", "."],
                 ["-c", "user.name=T", "-c", "user.email=t@example.test", "commit", "-qm", "seed"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    (repo / "workflows/code/with-review.md").write_text("dirty\n", encoding="utf-8")
    before = _tree(root)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True).stdout

    result = _cli(repo, "fork", "code/with-review")
    assert result.returncode == 1  # the dirty local workflow is broken
    assert "workflow: code/with-review" in result.stdout
    assert "state: broken: " in result.stdout
    assert "is broken" in result.stderr and "→ coga launch --read-only" in result.stderr

    result = _cli(repo, "fork", "recurring:trim-log", "--json")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["records"][0]["state"] == fork.MODIFIED

    result = _cli(repo, "fork", "--help")
    assert result.returncode == 0 and "usage: coga fork inspect" in result.stdout
    result = _cli(repo, "fork")
    assert result.returncode == 2
    assert _tree(root) == before
    assert subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True).stdout == status


def test_fork_copy_alias_writes_through_ordinary_launch(repo: Path) -> None:
    local = repo / "coga.local.toml"
    local.write_text(local.read_text(encoding="utf-8") + "\n[git]\nenabled = false\n", encoding="utf-8")
    result = _cli(repo, "fork-copy", "skill:code/peer-review")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "→ coga launch bootstrap/fork -- copy skill:code/peer-review" in result.stderr
    assert (repo / "skills/code/peer-review/SKILL.md").is_file()
    assert result.stdout.startswith(f"Forked skill:code/peer-review to {repo / 'skills/code/peer-review'}")


# --- the first acceptance case, launched ----------------------------------------


def test_forked_single_agent_peer_review_reuses_the_recorded_branch(
    git_repo, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:  # type: ignore[no-untyped-def]
    from coga import git as coga_git
    from coga.checkout_policy import select_checkout_policy
    from coga.create import create_task
    from coga.taskfile import join_task_body
    from coga.tasks import read_ticket, resolve_task

    coga_os = git_repo.coga_os
    assert fork.main(["copy", "workflow:code/with-review"]) == 0
    out = capsys.readouterr().out
    assert "coga fork-copy skill:code/peer-review" in out
    assert fork.main(["copy", "skill:code/peer-review"]) == 0
    capsys.readouterr()
    workflow = coga_os / "workflows/code/with-review.md"
    text = workflow.read_text(encoding="utf-8")
    head, _, tail = text.partition("- name: peer-review")
    step, sep, rest = tail.partition("- name:")
    workflow.write_text(head + "- name: peer-review" + step.replace("other-agent", "agent") + sep + rest,
                        encoding="utf-8", newline="\n")
    skill = coga_os / "skills/code/peer-review/SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "\nSINGLE-AGENT REVIEW MARKER\n",
                     encoding="utf-8", newline="\n")

    cfg = load_config(coga_os)
    created = create_task(cfg=cfg, title="Single agent review", workflow_name="code/with-review",
                          contexts=[], owner="marc", agent="claude", status="in_progress")
    ref = resolve_task(cfg, created["slug"])
    ticket = read_ticket(ref)
    review = next(s for s in ticket.workflow["steps"] if s["name"] == "peer-review")
    assert review["checkout"] == "reuse-required" and review["assignee"] == "agent"
    ticket.frontmatter["step"] = "2 (peer-review)"
    ticket.body = join_task_body("## Description\n\nReview.\n", "## Dev\n\nbranch: feature/review\n")
    ticket.write(ref.ticket_path)
    assert select_checkout_policy(cfg, read_ticket(ref)).kind == "reuse-required"
    coga_git.sync_coga_state(cfg)
    git_repo.git("branch", "feature/review")

    seen: list[tuple[str, str]] = []

    def agent(cmd, env, **_kwargs):  # type: ignore[no-untyped-def]
        branch = git_repo.git("rev-parse", "--abbrev-ref", "HEAD").strip()
        seen.append((branch, "\n".join(cmd)))
        return ReplOutcome(0, "done", done_signalled=True)

    monkeypatch.setattr("coga.launch._interactive_stdio_has_tty", lambda: True)
    monkeypatch.setattr("coga.launch.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("coga.launch._preflight_push_auth", lambda *a, **k: None)
    monkeypatch.setattr("coga.launch.usage_tracking.capture_session", lambda **kwargs: None)
    monkeypatch.setattr("coga.launch.run_with_done_marker", agent)
    result = CliRunner().invoke(app, ["launch", ref.id_slug])
    assert seen, result.output
    branch, prompt = seen[0]
    assert result.exit_code == 0, result.output
    assert branch == "feature/review"
    # The customized local skill text is what the agent works from, under the
    # declared policy rather than a hidden package-twin check.
    assert "SINGLE-AGENT REVIEW MARKER" in prompt
    assert "declares checkout: reuse-required" in result.output
