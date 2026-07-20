from __future__ import annotations

from pathlib import Path


def test_clean_install_gate_covers_public_first_install_contract() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    wrapper = (repo_root / "scripts" / "verify-clean-install.sh").read_text()
    container = (
        repo_root / "scripts" / "verify-clean-install-container.sh"
    ).read_text()

    assert 'uv tool install "coga==$COGA_GATE_VERSION"' in container
    assert "coga init --user gate" in container
    assert "coga/.coga/bin/coga --version" in container
    assert 'files("coga.resources").joinpath("templates/coga/bootstrap")' in container
    assert 'root.joinpath("workflows/code/with-review.md").is_file()' in container
    assert 'root.joinpath("skills/code/implement/SKILL.md").is_file()' in container
    assert 'coga launch verify-first-launch --agent "$COGA_GATE_AGENT"' in container
    assert "grep -q '^status: done$'" in container
    assert "coga validate --json" in container
    assert "git status --porcelain" in container
    assert "transcript.txt" in container
    assert "environment.txt" in container
    assert '"$@"' in wrapper


def test_clean_install_gate_requires_explicit_agent_install() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    wrapper = (repo_root / "scripts" / "verify-clean-install.sh").read_text()

    assert 'if [ -z "${COGA_GATE_AGENT_INSTALL:-}" ]' in wrapper
    assert "authenticated" in wrapper
