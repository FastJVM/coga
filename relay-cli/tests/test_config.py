"""Tests for relay_os.config.

Covers:
- Loading — full config, minimal config, missing files.
- Schema validation — invalid TOML, wrong types, bad literals, missing required.
- Cross-reference validation — bad nicknames, bad paths.
- Accessors — project, project_path, agent, resolve_assignee, slack_user.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from relay_os.config import (
    AgentSpec,
    AssigneeSpec,
    ConfigError,
    LocalConfig,
    ProjectSpec,
    RelayConfig,
    SharedConfig,
    _validate_cross_references,
    find_repo_root,
)


# --------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------


@pytest.fixture
def shared_toml() -> str:
    """A full shared config mirroring the repo's actual relay.toml."""
    return dedent("""\
        version = 1

        [projects.demo]
        type = "local"
        default_status = "ready"

        [projects.admin]
        type = "local"

        [agents.claude]
        cli = "claude"
        interactive = "--append-system-prompt-file"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"

        [agents.codex]
        cli = "codex"
        interactive = "exec"
        auto = "exec"
        file = "AGENTS.md"

        [assignees.zach]
        agents = { "claude1" = "claude", "claude2" = "claude" }
        slack = "U12345"

        [slack]
    """)


@pytest.fixture
def local_toml() -> str:
    """A full local config mirroring the repo's relay.local.toml.example."""
    return dedent("""\
        user = "zach"

        [paths]
        demo = "./projects/demo"
        admin = "./projects/admin"
    """)


@pytest.fixture
def repo(tmp_path: Path, shared_toml: str, local_toml: str) -> Path:
    """A tmp_path with both config files written."""
    (tmp_path / "relay.toml").write_text(shared_toml)
    (tmp_path / "relay.local.toml").write_text(local_toml)
    return tmp_path


# --------------------------------------------------------------------
# Loading — happy paths
# --------------------------------------------------------------------


def test_load_full_config(repo: Path) -> None:
    cfg = RelayConfig.load(start=repo)
    assert cfg.current_user == "zach"
    assert cfg.root == repo


def test_load_minimal_shared_only(tmp_path: Path, monkeypatch) -> None:
    """relay.local.toml is optional — `user` falls back to $USER."""
    (tmp_path / "relay.toml").write_text('version = 1\n')
    monkeypatch.setenv("USER", "alice")
    cfg = RelayConfig.load(start=tmp_path)
    assert cfg.current_user == "alice"
    assert cfg.shared.projects == {}


def test_find_repo_root_walks_up(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text("version = 1\n")
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert find_repo_root(start=nested) == tmp_path


def test_find_repo_root_defaults_to_cwd(tmp_path: Path, monkeypatch) -> None:
    """Called with no argument, find_repo_root uses the current working
    directory. This is the path CLI commands take — user runs `relay` from
    inside a Relay repo and everything works without --root flags."""
    (tmp_path / "relay.toml").write_text("version = 1\n")
    nested = tmp_path / "subdir"
    nested.mkdir()
    monkeypatch.chdir(nested)
    assert find_repo_root() == tmp_path


# --------------------------------------------------------------------
# Loading — error paths
# --------------------------------------------------------------------


def test_no_relay_toml_found(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not inside a Relay repo"):
        RelayConfig.load(start=tmp_path)


def test_invalid_toml_syntax(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text("[projects.demo\ntype = \"local\"\n")
    with pytest.raises(ConfigError, match="invalid TOML"):
        RelayConfig.load(start=tmp_path)


def test_invalid_project_type_literal(tmp_path: Path) -> None:
    """Literal type catches typos like type='lcoal'."""
    (tmp_path / "relay.toml").write_text(dedent("""
        [projects.demo]
        type = "lcoal"
    """))
    with pytest.raises(ConfigError, match="invalid relay.toml"):
        RelayConfig.load(start=tmp_path)


def test_invalid_status_literal(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text(dedent("""
        [projects.demo]
        type = "local"
        default_status = "not-a-status"
    """))
    with pytest.raises(ConfigError, match="invalid relay.toml"):
        RelayConfig.load(start=tmp_path)


def test_missing_required_agent_field(tmp_path: Path) -> None:
    """Agents require cli/interactive/auto/file — missing any should fail."""
    (tmp_path / "relay.toml").write_text(dedent("""
        [agents.claude]
        cli = "claude"
    """))
    with pytest.raises(ConfigError, match="invalid relay.toml"):
        RelayConfig.load(start=tmp_path)


def test_missing_required_local_user(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text("version = 1\n")
    (tmp_path / "relay.local.toml").write_text("[paths]\ndemo = \"x\"\n")
    with pytest.raises(ConfigError, match="invalid relay.local.toml"):
        RelayConfig.load(start=tmp_path)


# --------------------------------------------------------------------
# Cross-reference validation
# --------------------------------------------------------------------


def test_bad_nickname_agent_type(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text(dedent("""
        [agents.claude]
        cli = "claude"
        interactive = "x"
        auto = "y"
        file = "f"

        [assignees.zach]
        agents = { "claude1" = "nonexistent" }
    """))
    (tmp_path / "relay.local.toml").write_text('user = "zach"\n')
    with pytest.raises(ConfigError, match="no such agent type"):
        RelayConfig.load(start=tmp_path)


def test_bad_path_project(tmp_path: Path, shared_toml: str) -> None:
    (tmp_path / "relay.toml").write_text(shared_toml)
    (tmp_path / "relay.local.toml").write_text(dedent("""
        user = "zach"
        [paths]
        bogus-project = "./nowhere"
    """))
    with pytest.raises(ConfigError, match="no project named"):
        RelayConfig.load(start=tmp_path)


# --------------------------------------------------------------------
# Accessors
# --------------------------------------------------------------------


def test_project_accessor(repo: Path) -> None:
    cfg = RelayConfig.load(start=repo)
    demo = cfg.project("demo")
    assert demo is not None
    assert demo.type == "local"
    assert demo.default_status == "ready"
    assert cfg.project("not-a-project") is None


def test_project_path_relative_resolves_to_root(repo: Path) -> None:
    cfg = RelayConfig.load(start=repo)
    p = cfg.project_path("demo")
    assert p == (repo / "projects" / "demo").resolve()


def test_project_path_unmapped(repo: Path) -> None:
    cfg = RelayConfig.load(start=repo)
    # admin is mapped; pretend we ask for an unmapped project.
    assert cfg.project_path("not-in-paths") is None


def test_project_path_expands_tilde(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text(dedent("""
        [projects.home-proj]
        type = "local"
    """))
    (tmp_path / "relay.local.toml").write_text(dedent("""
        user = "zach"
        [paths]
        home-proj = "~/somewhere"
    """))
    cfg = RelayConfig.load(start=tmp_path)
    p = cfg.project_path("home-proj")
    assert p is not None
    assert not str(p).startswith("~")
    assert p.is_absolute()


def test_agent_accessor(repo: Path) -> None:
    cfg = RelayConfig.load(start=repo)
    claude = cfg.agent("claude")
    assert claude is not None
    assert claude.cli == "claude"
    assert cfg.agent("not-an-agent") is None


def test_resolve_assignee_current_user(repo: Path) -> None:
    cfg = RelayConfig.load(start=repo)
    agent = cfg.resolve_assignee("claude1")
    assert agent is not None
    assert agent.cli == "claude"


def test_resolve_assignee_unknown_nickname(repo: Path) -> None:
    cfg = RelayConfig.load(start=repo)
    assert cfg.resolve_assignee("bogus-nickname") is None


def test_resolve_assignee_no_assignee_block(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text("version = 1\n")
    (tmp_path / "relay.local.toml").write_text('user = "nobody"\n')
    cfg = RelayConfig.load(start=tmp_path)
    assert cfg.resolve_assignee("claude1") is None


def test_slack_user_accessor(repo: Path) -> None:
    cfg = RelayConfig.load(start=repo)
    assert cfg.slack_user("zach") == "U12345"
    assert cfg.slack_user("not-a-user") is None


def test_slack_user_empty_returns_none(tmp_path: Path) -> None:
    (tmp_path / "relay.toml").write_text(dedent("""
        [assignees.zach]
        agents = {}
        slack = ""
    """))
    (tmp_path / "relay.local.toml").write_text('user = "zach"\n')
    cfg = RelayConfig.load(start=tmp_path)
    assert cfg.slack_user("zach") is None


# --------------------------------------------------------------------
# Template files — schema drift guards
# --------------------------------------------------------------------
#
# The template files at the repo root (`relay.toml.empty`,
# `relay.toml.example`, `relay.local.toml.empty`, `relay.local.toml.example`)
# are the canonical schema reference. If someone adds a new pydantic
# field without updating these templates, or adds a field to the
# templates that the pydantic models don't recognize, these tests
# fail — which is the desired coupling.


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_empty_templates_load(tmp_path: Path) -> None:
    """Both `.empty` templates copied into place load without error."""
    import shutil

    shutil.copy(REPO_ROOT / "relay.toml.empty", tmp_path / "relay.toml")
    shutil.copy(
        REPO_ROOT / "relay.local.toml.empty", tmp_path / "relay.local.toml"
    )
    cfg = RelayConfig.load(start=tmp_path)
    assert cfg.shared.projects == {}
    assert cfg.shared.agents == {}


def test_example_templates_load(tmp_path: Path) -> None:
    """Both `.example` templates copied into place load without error,
    and the example pair is internally consistent (paths line up with
    projects, nicknames line up with agents)."""
    import shutil

    shutil.copy(REPO_ROOT / "relay.toml.example", tmp_path / "relay.toml")
    shutil.copy(
        REPO_ROOT / "relay.local.toml.example", tmp_path / "relay.local.toml"
    )
    cfg = RelayConfig.load(start=tmp_path)
    # The example demonstrates at least one project and one agent type;
    # exact names are not asserted so examples can evolve.
    assert cfg.shared.projects, "example should demonstrate at least one project"
    assert cfg.shared.agents, "example should demonstrate at least one agent type"


# --------------------------------------------------------------------
# Schema version
# --------------------------------------------------------------------


def test_version_default_is_1(tmp_path: Path) -> None:
    """Omitted version field defaults to 1."""
    (tmp_path / "relay.toml").write_text("[projects.demo]\ntype = \"local\"\n")
    cfg = RelayConfig.load(start=tmp_path)
    assert cfg.shared.version == 1


def test_version_invalid_rejected(tmp_path: Path) -> None:
    """Any version other than 1 is a clear load-time error — no silent
    acceptance of a newer schema the code doesn't understand."""
    (tmp_path / "relay.toml").write_text("version = 2\n")
    with pytest.raises(ConfigError, match="invalid relay.toml"):
        RelayConfig.load(start=tmp_path)
