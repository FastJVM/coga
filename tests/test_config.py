from __future__ import annotations

import os
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from coga.config import (
    ConfigError,
    SecretError,
    find_repo_root,
    load_config,
    parse_inline_secrets,
    select_launch_secrets,
)


def _write(path: Path, text: str) -> None:
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [notification]
        channels = ["slack"]

        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"

        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        mode = "local"

        """,
    )
    _write(
        tmp_path / "coga.local.toml",
        """
        user = "marc"
        """,
    )
    return tmp_path


def test_load_basic(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/xxx")
    cfg = load_config(repo)
    assert cfg.current_user == "marc"
    assert cfg.default_status == "draft"
    assert cfg.agents["claude"].cli == "claude"
    assert cfg.slack_webhook.startswith("https://")
    assert cfg.slack_enabled is True
    # The central [secrets] catalog is gone — Config no longer carries it.
    assert not hasattr(cfg, "secrets")


def test_missing_local_toml_fails_loud(repo: Path) -> None:
    """With no coga.local.toml at all, load_config fails loud rather than
    guessing a name — the operator must set `user` explicitly."""
    (repo / "coga.local.toml").unlink()
    with pytest.raises(ConfigError, match="No `user` set in coga.local.toml"):
        load_config(repo)


def test_secrets_table_in_local_toml_rejected(repo: Path) -> None:
    """The central `[secrets]` catalog was removed; a stray `[secrets]` table in
    coga.local.toml now fails config load loud rather than being silently
    honored. Secrets are declared inline per-ticket instead."""
    _write(
        repo / "coga.local.toml",
        """
        user = "marc"

        [secrets]
        stripe_key = "env:STRIPE_SECRET_KEY"
        """,
    )
    # A leftover `[secrets]` table gets the tailored migration error (it runs
    # before the generic unknown-section check) pointing at inline declaration.
    with pytest.raises(
        ConfigError,
        match=r"\[secrets\] in coga.local.toml is no longer supported",
    ):
        load_config(repo)


def test_default_status_defaults_to_draft(tmp_path: Path) -> None:
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    cfg = load_config(tmp_path)
    assert cfg.default_status == "draft"


def test_resolve_agent_type(repo: Path) -> None:
    cfg = load_config(repo)
    agent = cfg.agent_type("claude")
    assert agent.name == "claude"


def test_agent_discussion_template(repo: Path) -> None:
    text = (repo / "coga.toml").read_text()
    (repo / "coga.toml").write_text(
        text + 'discussion = "--append-system-prompt {prompt}"\n'
    )
    cfg = load_config(repo)
    assert cfg.agent_type("claude").discussion == "--append-system-prompt {prompt}"


def test_agent_discussion_template_must_be_string(repo: Path) -> None:
    text = (repo / "coga.toml").read_text()
    (repo / "coga.toml").write_text(text + "discussion = 42\n")
    with pytest.raises(ConfigError, match="agents.claude.discussion must be a string"):
        load_config(repo)


def test_agent_session_id_flag_loads_from_shared_config(repo: Path) -> None:
    text = (repo / "coga.toml").read_text()
    (repo / "coga.toml").write_text(text + 'session_id_flag = "--session-id"\n')
    cfg = load_config(repo)
    assert cfg.agent_type("claude").session_id_flag == "--session-id"


def test_agent_session_id_flag_must_be_string(repo: Path) -> None:
    text = (repo / "coga.toml").read_text()
    (repo / "coga.toml").write_text(text + "session_id_flag = 42\n")
    with pytest.raises(
        ConfigError, match="agents.claude.session_id_flag must be a string"
    ):
        load_config(repo)


def test_agent_skip_keys_rejected_in_shared_toml(repo: Path) -> None:
    text = (repo / "coga.toml").read_text()
    (repo / "coga.toml").write_text(text + 'skip_permissions = "auto"\n')
    with pytest.raises(
        ConfigError, match=r"\[agents.claude\] has unknown key\(s\).*skip_permissions"
    ):
        load_config(repo)


def test_agent_skip_argv_rejected_in_shared_toml(repo: Path) -> None:
    text = (repo / "coga.toml").read_text()
    (repo / "coga.toml").write_text(
        text + 'skip_permissions_argv = "--dangerously-skip-permissions"\n'
    )
    with pytest.raises(
        ConfigError, match=r"\[agents.claude\] has unknown key\(s\).*skip_permissions_argv"
    ):
        load_config(repo)


def test_agent_auto_argv_rejected_in_shared_toml(repo: Path) -> None:
    text = (repo / "coga.toml").read_text()
    (repo / "coga.toml").write_text(text + 'auto = "-p"\n')
    with pytest.raises(
        ConfigError, match=r"\[agents.claude\] has unknown key\(s\).*auto"
    ):
        load_config(repo)


def test_local_agent_overrides_are_rejected(repo: Path) -> None:
    _write(
        repo / "coga.local.toml",
        """
        user = "marc"

        [agents.claude]
        cli = "claude-nightly"
        """,
    )
    with pytest.raises(ConfigError, match="no longer supports"):
        load_config(repo)


def test_unknown_agent_type(repo: Path) -> None:
    cfg = load_config(repo)
    with pytest.raises(ConfigError, match="Agent type 'goat' is not defined"):
        cfg.agent_type("goat")


def test_default_agent_is_first_declared(repo: Path) -> None:
    cfg = load_config(repo)
    default = cfg.default_agent()
    assert default is not None
    assert default.name == "claude"


def test_launch_limits_default_to_none(repo: Path) -> None:
    """No `[launch]` table → both liveness limits are unset (config contributes
    no default; the recurring sweep supplies its own idle default)."""
    cfg = load_config(repo)
    assert cfg.launch_idle_timeout is None
    assert cfg.launch_idle_timeout_present is False
    assert cfg.launch_max_session is None


def test_launch_limits_parsed(repo: Path) -> None:
    """`[launch]` idle_timeout / max_session parse to floats (int accepted)."""
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + "\n[launch]\nidle_timeout = 600\nmax_session = 3600.0\n"
    )
    cfg = load_config(repo)
    assert cfg.launch_idle_timeout == 600.0
    assert cfg.launch_idle_timeout_present is True
    assert cfg.launch_max_session == 3600.0


def test_launch_limits_non_positive_disarm(repo: Path) -> None:
    """A `<= 0` value disarms that limit (None), matching the env override.

    Idle timeout has a built-in recurring default, so the presence bit is
    load-bearing: `idle_timeout = 0` must mean "explicitly disabled", not
    "omitted, fall back to 900s".
    """
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + "\n[launch]\nidle_timeout = 0\nmax_session = -1\n"
    )
    cfg = load_config(repo)
    assert cfg.launch_idle_timeout is None
    assert cfg.launch_idle_timeout_present is True
    assert cfg.launch_max_session is None


def test_launch_limit_non_number_rejected(repo: Path) -> None:
    """A non-numeric limit fails config load loudly (booleans included)."""
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text() + '\n[launch]\nidle_timeout = "soon"\n'
    )
    with pytest.raises(ConfigError, match=r"\[launch\].idle_timeout must be a number"):
        load_config(repo)


def test_launch_worktree_defaults_on(repo: Path) -> None:
    """No `[launch]` table (and an empty one) → worktree isolation is on."""
    cfg = load_config(repo)
    assert cfg.launch_worktree is True
    assert cfg.launch_worktree_path == ".coga/worktrees"
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text() + "\n[launch]\nidle_timeout = 600\n"
    )
    assert load_config(repo).launch_worktree is True


def test_launch_worktree_parsed(repo: Path) -> None:
    """`[launch].worktree = false` turns per-launch isolation off."""
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text() + "\n[launch]\nworktree = false\n"
    )
    assert load_config(repo).launch_worktree is False


def test_launch_worktree_must_be_bool(repo: Path) -> None:
    """A non-boolean `worktree` fails config load loudly."""
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text() + '\n[launch]\nworktree = "yes"\n'
    )
    with pytest.raises(ConfigError, match=r"\[launch\].worktree must be a boolean"):
        load_config(repo)


def test_launch_worktree_path_parsed(repo: Path) -> None:
    """`[launch].worktree_path` overrides where per-launch worktrees live."""
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + '\n[launch]\nworktree_path = "build/wt"\n'
    )
    assert load_config(repo).launch_worktree_path == "build/wt"


def test_launch_worktree_path_must_be_nonempty_string(repo: Path) -> None:
    """A blank or non-string `worktree_path` fails config load loudly."""
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text() + '\n[launch]\nworktree_path = "  "\n'
    )
    with pytest.raises(
        ConfigError, match=r"\[launch\].worktree_path must be a non-empty string"
    ):
        load_config(repo)


def test_legacy_assignees_table_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"

        [assignees.marc]
        agents = {"claude" = "claude"}
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match=r"\[assignees\] is no longer supported"):
        load_config(tmp_path)


# --- unknown-key rejection (fail loud on stray/misspelled config) -------------


def test_unknown_keys_accepts_every_known_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A config exercising every known key at every fixed-schema level loads
    cleanly — the allowlists must not reject anything legitimate."""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/xxx")
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        default_status = "draft"

        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        mode = "local"
        name_flag = "-n"
        session_id_flag = "--session-id"
        discussion = "--append-system-prompt {prompt}"

        [notification]
        channels = ["slack"]

        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        enabled = true

        [notification.slack.gifs]
        done = ["https://example.test/a.gif"]

        [notification.slack.users]
        marc = "U01ABC234"

        [git]
        enabled = true
        remote = "origin"
        control_branch = "main"

        [launch]
        idle_timeout = 600
        max_session = 3600
        worktree = true

        [ticket.fields.docket]
        description = "USPTO docket number"

        [aliases]
        chat = "launch bootstrap/orient"
        """,
    )
    _write(
        tmp_path / "coga.local.toml",
        """
        user = "marc"

        [git]
        enabled = false
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.current_user == "marc"
    assert cfg.git_enabled is False  # local override wins


def test_unknown_top_level_shared_section_rejected(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text() + "\n[notifcation]\nchannels = []\n"
    )
    with pytest.raises(ConfigError, match=r"coga.toml has unknown key\(s\) \['notifcation'\]"):
        load_config(repo)


def test_unknown_top_level_local_section_rejected(repo: Path) -> None:
    _write(
        repo / "coga.local.toml",
        """
        user = "marc"
        verison = 1
        """,
    )
    with pytest.raises(ConfigError, match=r"coga.local.toml has unknown key\(s\) \['verison'\]"):
        load_config(repo)


def test_local_ignored_shared_only_key_rejected(repo: Path) -> None:
    """`version` / `default_status` / `launch` are read only from shared; a stray
    copy in coga.local.toml is silently ignored today, which is the footgun.
    Reject it."""
    _write(
        repo / "coga.local.toml",
        """
        user = "marc"
        default_status = "active"
        """,
    )
    with pytest.raises(ConfigError, match=r"coga.local.toml has unknown key\(s\) \['default_status'\]"):
        load_config(repo)


def test_unknown_agent_key_rejected(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text() + 'clii = "claude"\n'
    )
    with pytest.raises(ConfigError, match=r"\[agents.claude\] has unknown key\(s\) \['clii'\]"):
        load_config(repo)


def test_unknown_notification_subkey_rejected(repo: Path) -> None:
    """The title footgun: `[notification.slak]` is a stray key in `[notification]`
    that would silently shadow the real Slack config — now it fails loud."""
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + '\n[notification.slak]\nwebhook = "env:SLACK_WEBHOOK_URL"\n'
    )
    with pytest.raises(
        ConfigError,
        match=r"\[notification\] in coga.toml has unknown key\(s\) \['slak'\]",
    ):
        load_config(repo)


def test_unknown_notification_slack_key_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path / "coga.toml",
        """
        version = 1

        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"

        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        webhok = "env:NOPE"
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    with pytest.raises(
        ConfigError,
        match=r"\[notification.slack\] in coga.toml has unknown key\(s\) \['webhok'\]",
    ):
        load_config(tmp_path)


def test_unknown_legacy_slack_key_rejected(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text() + '\n[slack]\nwebhok = "env:NOPE"\n'
    )
    with pytest.raises(
        ConfigError, match=r"\[slack\] in coga.toml has unknown key\(s\) \['webhok'\]"
    ):
        load_config(repo)


def test_unknown_git_key_rejected_shared(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text() + '\n[git]\nremot = "origin"\n'
    )
    with pytest.raises(
        ConfigError, match=r"\[git\] in coga.toml has unknown key\(s\) \['remot'\]"
    ):
        load_config(repo)


def test_unknown_git_key_rejected_local(repo: Path) -> None:
    _write(
        repo / "coga.local.toml",
        """
        user = "marc"

        [git]
        enable = false
        """,
    )
    with pytest.raises(
        ConfigError, match=r"\[git\] in coga.local.toml has unknown key\(s\) \['enable'\]"
    ):
        load_config(repo)


@pytest.mark.parametrize("key", ["remote", "control_branch"])
def test_shared_only_git_keys_rejected_local(repo: Path, key: str) -> None:
    _write(
        repo / "coga.local.toml",
        f"""
        user = "marc"

        [git]
        {key} = "upstream"
        """,
    )
    with pytest.raises(
        ConfigError,
        match=rf"\[git\] in coga.local.toml has unknown key\(s\) \['{key}'\]",
    ):
        load_config(repo)


def test_unknown_launch_key_rejected(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text() + "\n[launch]\nidle_timout = 600\n"
    )
    with pytest.raises(
        ConfigError, match=r"\[launch\] has unknown key\(s\) \['idle_timout'\]"
    ):
        load_config(repo)


def test_unknown_ticket_key_rejected(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text() + "\n[ticket]\nfeilds = {}\n"
    )
    with pytest.raises(
        ConfigError, match=r"\[ticket\] has unknown key\(s\) \['feilds'\]"
    ):
        load_config(repo)


def test_free_form_maps_keep_arbitrary_keys(repo: Path) -> None:
    """Free-form maps (slack gifs/users, aliases) map user-chosen names to
    values — their keys are data and must NOT be rejected."""
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + (
            "\n[notification.slack.gifs]\n"
            'anything_goes = ["https://example.test/x.gif"]\n'
            "\n[notification.slack.users]\n"
            'whoever = "U0XXXXXXX"\n'
        )
    )
    cfg = load_config(repo)
    assert cfg.slack_gifs["anything_goes"] == ["https://example.test/x.gif"]
    assert cfg.slack_users["whoever"] == "U0XXXXXXX"


def test_assignees_dedicated_message_beats_generic(tmp_path: Path) -> None:
    """`[assignees]` is a known-but-rejected key: its tailored migration message
    must win over the generic unknown-key check."""
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"

        [assignees.marc]
        agents = {"claude" = "claude"}
        """,
    )
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match=r"\[assignees\] is no longer supported"):
        load_config(tmp_path)


def test_extra_local_field_retired(repo: Path) -> None:
    """The dead `extra_local` field (written, never read) is gone."""
    cfg = load_config(repo)
    assert not hasattr(cfg, "extra_local")


def test_missing_user_fails_loud(tmp_path: Path) -> None:
    """A missing/empty `user` is a hard error on every command — coga reads the
    operator's name from config and never guesses it. The message points at the
    existing-repo edit remedy."""
    _write(
        tmp_path / "coga.toml",
        """
        version = 1
        [agents.claude]
        cli = "claude"
        file = "CLAUDE.md"
        """,
    )
    _write(tmp_path / "coga.local.toml", "")
    with pytest.raises(ConfigError) as excinfo:
        load_config(tmp_path)
    message = str(excinfo.value)
    assert 'Add `user = "<name>"`' in message
    assert "coga.local.toml" in message
    assert "fresh repo" in message


def test_find_repo_root(repo: Path) -> None:
    nested = repo / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert find_repo_root(nested) == repo


def test_find_repo_root_not_found(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="No coga.toml found"):
        find_repo_root(tmp_path)


def test_find_repo_root_nested_coga_only_from_inside_subtree(tmp_path: Path) -> None:
    """A coga/ nested in a monorepo subdir (`coga init tools/ops`) is found
    from anywhere inside its subtree, but discovery never descends more than
    one level — the host repo's root doesn't see it."""
    nested = tmp_path / "tools" / "ops" / "coga"
    nested.mkdir(parents=True)
    (nested / "coga.toml").write_text("version = 1\n")
    inside = tmp_path / "tools" / "ops" / "src" / "deep"
    inside.mkdir(parents=True)

    assert find_repo_root(inside) == nested
    assert find_repo_root(tmp_path / "tools" / "ops") == nested
    with pytest.raises(ConfigError, match="No coga.toml found"):
        find_repo_root(tmp_path)


# --- inline per-ticket `secrets:` ---------------------------------------------
# Secrets are no longer a central catalog; each ticket declares them inline as
# `secrets:` frontmatter — a list of single-key `NAME: <ref>` maps where <ref>
# is `op://vault/item/field` or `env:VAR`. `select_launch_secrets(cfg, declared)`
# resolves that inline list at launch (cfg is unused). Coverage below mirrors the
# old catalog tests' intent against the inline model.


def test_parse_inline_secrets_none_and_empty_are_no_secrets() -> None:
    # Absent/null and an empty list both mean "no secrets".
    assert parse_inline_secrets(None) == []
    assert parse_inline_secrets([]) == []


def test_parse_inline_secrets_returns_name_ref_pairs() -> None:
    declared = [
        {"STRIPE_KEY": "env:STRIPE_SECRET_KEY"},
        {"OP_KEY": "op://vault/stripe/key"},
    ]
    assert parse_inline_secrets(declared) == [
        ("STRIPE_KEY", "env:STRIPE_SECRET_KEY"),
        ("OP_KEY", "op://vault/stripe/key"),
    ]


def test_parse_inline_secrets_rejects_bare_string() -> None:
    # A bare string is the removed catalog-key form — rejected.
    with pytest.raises(SecretError, match="bare string"):
        parse_inline_secrets(["stripe_key"])


def test_parse_inline_secrets_rejects_raw_literal() -> None:
    # A raw literal value may not live in a git-committed ticket.
    with pytest.raises(SecretError, match="literal value cannot live"):
        parse_inline_secrets([{"STRIPE_KEY": "just-a-value"}])


def test_parse_inline_secrets_rejects_non_list() -> None:
    with pytest.raises(SecretError, match="must be null or a list"):
        parse_inline_secrets("stripe_key")


def test_parse_inline_secrets_rejects_duplicate_name() -> None:
    with pytest.raises(SecretError, match="more than once"):
        parse_inline_secrets(
            [{"STRIPE_KEY": "env:A"}, {"STRIPE_KEY": "env:B"}]
        )


def test_select_launch_secrets_none_and_empty_inject_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    # cfg is unused by the catalog-free resolver; None is accepted.
    assert select_launch_secrets(None, None) == {}
    assert select_launch_secrets(None, []) == {}


def test_select_launch_secrets_least_privilege(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    monkeypatch.setenv("OTHER_SECRET", "nope")
    # Only the declared key is injected under its scoped name; an undeclared
    # env var is never leaked.
    env = select_launch_secrets(None, [{"STRIPE_KEY": "env:STRIPE_SECRET_KEY"}])
    assert env == {"STRIPE_KEY": "sk_test_abc"}


def test_select_launch_secrets_fails_on_unset_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    with pytest.raises(SecretError) as exc:
        select_launch_secrets(None, [{"STRIPE_KEY": "env:STRIPE_SECRET_KEY"}])
    # Message names both the scoped secret name and the missing env var.
    assert "STRIPE_KEY" in str(exc.value)
    assert "STRIPE_SECRET_KEY" in str(exc.value)


def test_select_launch_secrets_rejects_non_list() -> None:
    with pytest.raises(SecretError, match="must be null or a list"):
        select_launch_secrets(None, "stripe_key")


# --- 1Password `op://` references (inline) ------------------------------------


def test_select_launch_secrets_resolves_op_when_declared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        # `op read` prints the secret followed by a trailing newline.
        return subprocess.CompletedProcess(argv, 0, stdout="sk_op_secret\n", stderr="")

    monkeypatch.setattr("coga.config.subprocess.run", fake_run)
    env = select_launch_secrets(None, [{"STRIPE_KEY": "op://vault/stripe/key"}])
    # Trailing newline stripped, value otherwise untransformed.
    assert env == {"STRIPE_KEY": "sk_op_secret"}
    assert calls == [["op", "read", "op://vault/stripe/key"]]


def test_select_launch_secrets_op_missing_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(argv, **kwargs):
        raise FileNotFoundError("op")

    monkeypatch.setattr("coga.config.subprocess.run", fake_run)
    with pytest.raises(SecretError) as exc:
        select_launch_secrets(None, [{"STRIPE_KEY": "op://vault/stripe/key"}])
    msg = str(exc.value)
    # Names the key and reference; never a secret value (there is none).
    assert "STRIPE_KEY" in msg
    assert "op://vault/stripe/key" in msg
    assert "not installed" in msg


def test_select_launch_secrets_op_read_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(
            argv, 1, stdout="", stderr="[ERROR] not signed in"
        )

    monkeypatch.setattr("coga.config.subprocess.run", fake_run)
    with pytest.raises(SecretError) as exc:
        select_launch_secrets(None, [{"STRIPE_KEY": "op://vault/stripe/key"}])
    msg = str(exc.value)
    assert "STRIPE_KEY" in msg
    assert "op://vault/stripe/key" in msg
    assert "not signed in" in msg


def test_unsupported_version(tmp_path: Path) -> None:
    _write(tmp_path / "coga.toml", "version = 99\n")
    _write(tmp_path / "coga.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match="Unsupported coga.toml version"):
        load_config(tmp_path)


def test_aliases_load_and_strip(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + '\n[aliases]\nchat = "  launch bootstrap/orient  "\n'
    )
    cfg = load_config(repo)
    assert cfg.aliases == {"chat": "launch bootstrap/orient"}


def test_aliases_default_empty(repo: Path) -> None:
    cfg = load_config(repo)
    assert cfg.aliases == {}


def test_aliases_reject_non_string(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text() + "\n[aliases]\nchat = 42\n"
    )
    with pytest.raises(ConfigError, match="aliases.chat must be a string"):
        load_config(repo)


def test_aliases_reject_empty_string(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text() + '\n[aliases]\nchat = "   "\n'
    )
    with pytest.raises(ConfigError, match="aliases.chat is empty"):
        load_config(repo)


# --- [ticket.fields.*] -------------------------------------------------------


def test_ticket_fields_load_minimal(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + '\n[ticket.fields.docket]\ndescription = "USPTO docket number"\n'
    )
    cfg = load_config(repo)
    assert "docket" in cfg.ticket_fields
    field = cfg.ticket_fields["docket"]
    assert field.description == "USPTO docket number"
    assert field.values is None
    assert field.default == ""
    assert field.required is False


def test_ticket_fields_preserve_declaration_order(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + (
            "\n[ticket.fields.docket]\ndescription = \"d\"\n"
            "\n[ticket.fields.application_number]\ndescription = \"a\"\n"
            "\n[ticket.fields.priority]\ndescription = \"p\"\n"
        )
    )
    cfg = load_config(repo)
    assert list(cfg.ticket_fields) == ["docket", "application_number", "priority"]


def test_ticket_fields_default_empty(repo: Path) -> None:
    cfg = load_config(repo)
    assert cfg.ticket_fields == {}


def test_ticket_fields_full_shape(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + (
            "\n[ticket.fields.priority]\n"
            'description = "triage tier"\n'
            'values = ["P0", "P1", "P2"]\n'
            'default = "P2"\n'
            "required = true\n"
        )
    )
    cfg = load_config(repo)
    field = cfg.ticket_fields["priority"]
    assert field.values == ("P0", "P1", "P2")
    assert field.default == "P2"
    assert field.required is True


def test_ticket_fields_reject_reserved_name(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + '\n[ticket.fields.status]\ndescription = "x"\n'
    )
    with pytest.raises(ConfigError, match="canonical ticket frontmatter key"):
        load_config(repo)


def test_ticket_fields_reject_unsupported_key(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + (
            "\n[ticket.fields.docket]\n"
            'description = "d"\n'
            'kind = "string"\n'
        )
    )
    with pytest.raises(ConfigError, match="unsupported keys"):
        load_config(repo)


def test_ticket_fields_require_description(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text() + "\n[ticket.fields.docket]\n"
    )
    with pytest.raises(ConfigError, match="description must be a non-empty string"):
        load_config(repo)


def test_ticket_fields_reject_empty_values_list(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + (
            "\n[ticket.fields.priority]\n"
            'description = "p"\n'
            "values = []\n"
        )
    )
    with pytest.raises(ConfigError, match="values must not be empty"):
        load_config(repo)


def test_ticket_fields_default_must_match_values(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + (
            "\n[ticket.fields.priority]\n"
            'description = "p"\n'
            'values = ["P0", "P1"]\n'
            'default = "P9"\n'
        )
    )
    with pytest.raises(ConfigError, match="not in declared values"):
        load_config(repo)


def test_ticket_fields_required_must_be_bool(repo: Path) -> None:
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + (
            "\n[ticket.fields.docket]\n"
            'description = "d"\n'
            'required = "yes"\n'
        )
    )
    with pytest.raises(ConfigError, match="required must be a boolean"):
        load_config(repo)


def test_extensions_freeform_passthrough(repo: Path) -> None:
    """`[extensions]` is a repo-owned namespace coga accepts verbatim — nested
    tables and arbitrary scalars pass through to `Config.extensions`."""
    (repo / "coga.toml").write_text(
        (repo / "coga.toml").read_text()
        + (
            "\n[extensions]\n"
            "feature_flag = true\n"
            "\n[extensions.patent]\n"
            'calendar_id = "abc123@group.calendar.google.com"\n'
        )
    )
    cfg = load_config(repo)
    assert cfg.extensions["feature_flag"] is True
    assert (
        cfg.extensions["patent"]["calendar_id"]
        == "abc123@group.calendar.google.com"
    )


def test_extensions_absent_defaults_empty(repo: Path) -> None:
    assert load_config(repo).extensions == {}


def test_extensions_non_table_rejected(repo: Path) -> None:
    # insert as a top-level scalar (before any table header) so it's the
    # `[extensions]` section, not a key inside the trailing [agents.*] table
    text = (repo / "coga.toml").read_text().replace(
        "version = 1", 'version = 1\nextensions = "nope"', 1
    )
    (repo / "coga.toml").write_text(text)
    with pytest.raises(ConfigError, match=r"\[extensions\] must be a table"):
        load_config(repo)


def test_megalaunch_usage_reserve_keys_load(repo: Path) -> None:
    with (repo / "coga.toml").open("a") as f:
        f.write(
            "[megalaunch]\n"
            "min_session_remaining_percent = 10\n"
            "min_weekly_remaining_percent = 8.5\n"
            "weekly_final_window_hours = 12\n"
        )

    cfg = load_config(repo)

    assert cfg.megalaunch.min_session_remaining_percent == 10.0
    assert cfg.megalaunch.min_weekly_remaining_percent == 8.5
    assert cfg.megalaunch.weekly_final_window_hours == 12.0


def test_megalaunch_reserve_percent_rejects_out_of_range(repo: Path) -> None:
    with (repo / "coga.toml").open("a") as f:
        f.write("[megalaunch]\nmin_session_remaining_percent = 250\n")

    with pytest.raises(ConfigError, match="between 0 and 100"):
        load_config(repo)


def test_megalaunch_deprecated_token_keys_still_load(repo: Path) -> None:
    """Live configs still set the replaced token-budget keys; they must parse."""
    with (repo / "coga.toml").open("a") as f:
        f.write("[megalaunch]\ndefault_token_budget = 20_000_000\n")

    cfg = load_config(repo)

    assert cfg.megalaunch.default_token_budget == 20_000_000
