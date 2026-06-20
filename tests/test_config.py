from __future__ import annotations

import os
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from relay.config import (
    ConfigError,
    SecretError,
    find_repo_root,
    load_config,
    select_launch_secrets,
)


def _write(path: Path, text: str) -> None:
    path.write_text(dedent(text).lstrip())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [notification]
        channels = ["slack"]

        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"

        """,
    )
    _write(
        tmp_path / "relay.local.toml",
        """
        user = "marc"

        [secrets]
        stripe_key = "env:STRIPE_SECRET_KEY"
        literal = "just-a-value"
        """,
    )
    return tmp_path


def test_load_basic(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/xxx")
    cfg = load_config(repo)
    assert cfg.current_user == "marc"
    assert cfg.default_status == "draft"
    assert cfg.agents["claude"].cli == "claude"
    assert cfg.slack_webhook.startswith("https://")
    assert cfg.slack_enabled is True
    assert cfg.secrets["stripe_key"].value == "sk_test_abc"
    assert cfg.secrets["stripe_key"].env_var == "STRIPE_SECRET_KEY"
    assert cfg.secrets["stripe_key"].missing is False
    assert cfg.secrets["literal"].value == "just-a-value"
    assert cfg.secrets["literal"].env_var is None


def test_default_status_defaults_to_draft(tmp_path: Path) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    cfg = load_config(tmp_path)
    assert cfg.default_status == "draft"


def test_resolve_agent_type(repo: Path) -> None:
    cfg = load_config(repo)
    agent = cfg.agent_type("claude")
    assert agent.name == "claude"


def test_agent_discussion_template(repo: Path) -> None:
    text = (repo / "relay.toml").read_text()
    (repo / "relay.toml").write_text(
        text + 'discussion = "--append-system-prompt {prompt}"\n'
    )
    cfg = load_config(repo)
    assert cfg.agent_type("claude").discussion == "--append-system-prompt {prompt}"


def test_agent_discussion_template_must_be_string(repo: Path) -> None:
    text = (repo / "relay.toml").read_text()
    (repo / "relay.toml").write_text(text + "discussion = 42\n")
    with pytest.raises(ConfigError, match="agents.claude.discussion must be a string"):
        load_config(repo)


def test_agent_skip_policy_defaults_off(repo: Path) -> None:
    cfg = load_config(repo)
    agent = cfg.agent_type("claude")
    assert agent.skip_permissions == ""
    assert agent.skip_permissions_argv == ()


def test_agent_skip_policy_loads_from_local(repo: Path) -> None:
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"

        [agents.claude]
        skip_permissions = "auto"
        skip_permissions_argv = "--permission-mode bypassPermissions"
        """,
    )
    cfg = load_config(repo)
    agent = cfg.agent_type("claude")
    assert agent.skip_permissions == "auto"
    assert agent.skip_permissions_argv == ("--permission-mode", "bypassPermissions")


def test_agent_skip_permissions_false_is_off(repo: Path) -> None:
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"

        [agents.claude]
        skip_permissions = false
        skip_permissions_argv = "--dangerously-skip-permissions"
        """,
    )
    cfg = load_config(repo)
    agent = cfg.agent_type("claude")
    assert agent.skip_permissions == ""
    assert agent.skip_permissions_argv == ("--dangerously-skip-permissions",)


def test_agent_skip_permissions_rejects_bad_value(repo: Path) -> None:
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"

        [agents.claude]
        skip_permissions = "always"
        """,
    )
    with pytest.raises(ConfigError, match=r'must be false or "auto"'):
        load_config(repo)


def test_agent_skip_permissions_rejects_true_boolean(repo: Path) -> None:
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"

        [agents.claude]
        skip_permissions = true
        """,
    )
    with pytest.raises(ConfigError, match=r'must be false or "auto"'):
        load_config(repo)


def test_agent_skip_permissions_argv_rejects_non_string(repo: Path) -> None:
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"

        [agents.claude]
        skip_permissions_argv = ["--dangerously-skip-permissions"]
        """,
    )
    with pytest.raises(ConfigError, match="skip_permissions_argv.*must be a string"):
        load_config(repo)


def test_agent_skip_auto_without_argv_loads(repo: Path) -> None:
    """Config load tolerates "auto" with no argv — `relay launch` is the
    fail-loud point, so a half-written local table doesn't brick every
    other relay command on the machine."""
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"

        [agents.claude]
        skip_permissions = "auto"
        """,
    )
    cfg = load_config(repo)
    agent = cfg.agent_type("claude")
    assert agent.skip_permissions == "auto"
    assert agent.skip_permissions_argv == ()


def test_agent_skip_keys_rejected_in_shared_toml(repo: Path) -> None:
    text = (repo / "relay.toml").read_text()
    (repo / "relay.toml").write_text(text + 'skip_permissions = "auto"\n')
    with pytest.raises(
        ConfigError, match="machine-local policy.*must not be committed"
    ):
        load_config(repo)


def test_agent_skip_argv_rejected_in_shared_toml(repo: Path) -> None:
    text = (repo / "relay.toml").read_text()
    (repo / "relay.toml").write_text(
        text + 'skip_permissions_argv = "--dangerously-skip-permissions"\n'
    )
    with pytest.raises(
        ConfigError, match="machine-local policy.*must not be committed"
    ):
        load_config(repo)


def test_local_agent_override_rejects_unknown_agent(repo: Path) -> None:
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"

        [agents.goat]
        skip_permissions = "auto"
        """,
    )
    with pytest.raises(ConfigError, match="unknown agent"):
        load_config(repo)


def test_local_agent_override_rejects_other_keys(repo: Path) -> None:
    """Local `[agents.<name>]` tables are partial overrides for the skip
    policy only — redefining e.g. `cli` locally must fail loud."""
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"

        [agents.claude]
        cli = "claude-nightly"
        skip_permissions = "auto"
        """,
    )
    with pytest.raises(ConfigError, match="unsupported keys"):
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
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
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
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + "\n[launch]\nidle_timeout = 0\nmax_session = -1\n"
    )
    cfg = load_config(repo)
    assert cfg.launch_idle_timeout is None
    assert cfg.launch_idle_timeout_present is True
    assert cfg.launch_max_session is None


def test_launch_limit_non_number_rejected(repo: Path) -> None:
    """A non-numeric limit fails config load loudly (booleans included)."""
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text() + '\n[launch]\nidle_timeout = "soon"\n'
    )
    with pytest.raises(ConfigError, match=r"\[launch\].idle_timeout must be a number"):
        load_config(repo)


def test_legacy_assignees_table_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"

        [assignees.marc]
        agents = {"claude" = "claude"}
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match=r"\[assignees\] is no longer supported"):
        load_config(tmp_path)


# --- unknown-key rejection (fail loud on stray/misspelled config) -------------


def test_unknown_keys_accepts_every_known_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A config exercising every known key at every fixed-schema level loads
    cleanly — the allowlists must not reject anything legitimate."""
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/xxx")
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"
        name_flag = "-n"
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

        [ticket.fields.docket]
        description = "USPTO docket number"

        [aliases]
        chat = "launch bootstrap/orient"
        """,
    )
    _write(
        tmp_path / "relay.local.toml",
        """
        user = "marc"

        [secrets]
        stripe_key = "env:STRIPE_SECRET_KEY"

        [agents.claude]
        skip_permissions = "auto"
        skip_permissions_argv = "--dangerously-skip-permissions"

        [git]
        enabled = false
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.current_user == "marc"
    assert cfg.git_enabled is False  # local override wins
    assert cfg.agent_type("claude").skip_permissions == "auto"


def test_unknown_top_level_shared_section_rejected(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text() + "\n[notifcation]\nchannels = []\n"
    )
    with pytest.raises(ConfigError, match=r"relay.toml has unknown key\(s\) \['notifcation'\]"):
        load_config(repo)


def test_unknown_top_level_local_section_rejected(repo: Path) -> None:
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"
        verison = 1
        """,
    )
    with pytest.raises(ConfigError, match=r"relay.local.toml has unknown key\(s\) \['verison'\]"):
        load_config(repo)


def test_local_ignored_shared_only_key_rejected(repo: Path) -> None:
    """`version` / `default_status` / `launch` are read only from shared; a stray
    copy in relay.local.toml is silently ignored today, which is the footgun.
    Reject it."""
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"
        default_status = "active"
        """,
    )
    with pytest.raises(ConfigError, match=r"relay.local.toml has unknown key\(s\) \['default_status'\]"):
        load_config(repo)


def test_unknown_agent_key_rejected(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text() + 'clii = "claude"\n'
    )
    with pytest.raises(ConfigError, match=r"\[agents.claude\] has unknown key\(s\) \['clii'\]"):
        load_config(repo)


def test_unknown_notification_subkey_rejected(repo: Path) -> None:
    """The title footgun: `[notification.slak]` is a stray key in `[notification]`
    that would silently shadow the real Slack config — now it fails loud."""
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[notification.slak]\nwebhook = "env:SLACK_WEBHOOK_URL"\n'
    )
    with pytest.raises(
        ConfigError,
        match=r"\[notification\] in relay.toml has unknown key\(s\) \['slak'\]",
    ):
        load_config(repo)


def test_unknown_notification_slack_key_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"

        [notification.slack]
        webhook = "env:SLACK_WEBHOOK_URL"
        webhok = "env:NOPE"
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    with pytest.raises(
        ConfigError,
        match=r"\[notification.slack\] in relay.toml has unknown key\(s\) \['webhok'\]",
    ):
        load_config(tmp_path)


def test_unknown_legacy_slack_key_rejected(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text() + '\n[slack]\nwebhok = "env:NOPE"\n'
    )
    with pytest.raises(
        ConfigError, match=r"\[slack\] in relay.toml has unknown key\(s\) \['webhok'\]"
    ):
        load_config(repo)


def test_unknown_git_key_rejected_shared(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text() + '\n[git]\nremot = "origin"\n'
    )
    with pytest.raises(
        ConfigError, match=r"\[git\] in relay.toml has unknown key\(s\) \['remot'\]"
    ):
        load_config(repo)


def test_unknown_git_key_rejected_local(repo: Path) -> None:
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"

        [git]
        enable = false
        """,
    )
    with pytest.raises(
        ConfigError, match=r"\[git\] in relay.local.toml has unknown key\(s\) \['enable'\]"
    ):
        load_config(repo)


def test_unknown_launch_key_rejected(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text() + "\n[launch]\nidle_timout = 600\n"
    )
    with pytest.raises(
        ConfigError, match=r"\[launch\] has unknown key\(s\) \['idle_timout'\]"
    ):
        load_config(repo)


def test_unknown_ticket_key_rejected(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text() + "\n[ticket]\nfeilds = {}\n"
    )
    with pytest.raises(
        ConfigError, match=r"\[ticket\] has unknown key\(s\) \['feilds'\]"
    ):
        load_config(repo)


def test_free_form_maps_keep_arbitrary_keys(repo: Path) -> None:
    """Free-form maps (secrets, slack gifs/users, aliases) map user-chosen names
    to values — their keys are data and must NOT be rejected."""
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[notification.slack.gifs]\n"
            'anything_goes = ["https://example.test/x.gif"]\n'
            "\n[notification.slack.users]\n"
            'whoever = "U0XXXXXXX"\n'
        )
    )
    _write(
        repo / "relay.local.toml",
        """
        user = "marc"

        [secrets]
        some_made_up_name = "literal"
        """,
    )
    cfg = load_config(repo)
    assert cfg.slack_gifs["anything_goes"] == ["https://example.test/x.gif"]
    assert cfg.slack_users["whoever"] == "U0XXXXXXX"
    assert cfg.secrets["some_made_up_name"].value == "literal"


def test_assignees_dedicated_message_beats_generic(tmp_path: Path) -> None:
    """`[assignees]` is a known-but-rejected key: its tailored migration message
    must win over the generic unknown-key check."""
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"

        [assignees.marc]
        agents = {"claude" = "claude"}
        """,
    )
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match=r"\[assignees\] is no longer supported"):
        load_config(tmp_path)


def test_extra_local_field_retired(repo: Path) -> None:
    """The dead `extra_local` field (written, never read) is gone."""
    cfg = load_config(repo)
    assert not hasattr(cfg, "extra_local")


def test_missing_user(tmp_path: Path) -> None:
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        """,
    )
    _write(tmp_path / "relay.local.toml", "")
    with pytest.raises(ConfigError, match="user` is missing"):
        load_config(tmp_path)


def test_find_repo_root(repo: Path) -> None:
    nested = repo / "a" / "b" / "c"
    nested.mkdir(parents=True)
    assert find_repo_root(nested) == repo


def test_find_repo_root_not_found(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="No relay.toml found"):
        find_repo_root(tmp_path)


def test_missing_env_secret_resolves_to_none_not_empty(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An unset env:VAR keeps provenance and resolves to value=None (not ""),
    # so launch can fail loud instead of injecting a silent empty secret.
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    cfg = load_config(repo)
    sv = cfg.secrets["stripe_key"]
    assert sv.value is None
    assert sv.env_var == "STRIPE_SECRET_KEY"
    assert sv.missing is True


def test_select_launch_secrets_blanket_when_absent(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Absent/null `secrets:` (passed as None) keeps legacy blanket-inject of
    # every resolvable secret, but never injects an unset env: secret as "".
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    cfg = load_config(repo)
    env = select_launch_secrets(cfg, None)
    assert env == {"stripe_key": "sk_test_abc", "literal": "just-a-value"}


def test_select_launch_secrets_blanket_skips_unset_env(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    cfg = load_config(repo)
    env = select_launch_secrets(cfg, None)
    # Unset env: secret is omitted entirely — never injected as "".
    assert env == {"literal": "just-a-value"}


def test_select_launch_secrets_empty_list_injects_nothing(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    cfg = load_config(repo)
    assert select_launch_secrets(cfg, []) == {}


def test_select_launch_secrets_least_privilege(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    cfg = load_config(repo)
    # Only the declared key is injected; the undeclared `literal` is withheld.
    assert select_launch_secrets(cfg, ["stripe_key"]) == {"stripe_key": "sk_test_abc"}


def test_select_launch_secrets_fails_on_unset_env(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    cfg = load_config(repo)
    with pytest.raises(SecretError) as exc:
        select_launch_secrets(cfg, ["stripe_key"])
    # Message names both the secret key and the missing env var.
    assert "stripe_key" in str(exc.value)
    assert "STRIPE_SECRET_KEY" in str(exc.value)


def test_select_launch_secrets_fails_on_undeclared_key(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    cfg = load_config(repo)
    with pytest.raises(SecretError, match="not defined in"):
        select_launch_secrets(cfg, ["nonexistent_key"])


def test_select_launch_secrets_rejects_non_list(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    cfg = load_config(repo)
    with pytest.raises(SecretError, match="must be a list"):
        select_launch_secrets(cfg, "stripe_key")


# --- 1Password `op://` references ---------------------------------------------


@pytest.fixture
def op_repo(tmp_path: Path) -> Path:
    """A repo whose `[secrets]` carries a 1Password `op://` reference."""
    _write(
        tmp_path / "relay.toml",
        """
        version = 1
        default_status = "draft"

        [agents.claude]
        cli = "claude"
        auto = "-p"
        file = "CLAUDE.md"
        mode = "local"
        """,
    )
    _write(
        tmp_path / "relay.local.toml",
        """
        user = "marc"

        [secrets]
        stripe_key = "op://vault/stripe/key"
        literal = "just-a-value"
        """,
    )
    return tmp_path


def test_op_reference_loads_deferred_not_resolved(
    op_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Loading config records the op reference but never shells out — a config
    # load must not prompt 1Password.
    def _boom(*args, **kwargs):  # pragma: no cover — must not be called
        raise AssertionError("config load must not invoke `op`")

    monkeypatch.setattr("relay.config.subprocess.run", _boom)
    cfg = load_config(op_repo)
    sv = cfg.secrets["stripe_key"]
    assert sv.op_ref == "op://vault/stripe/key"
    assert sv.value is None
    assert sv.env_var is None
    assert sv.missing is False  # deferred, not env-unset


def test_select_launch_secrets_blanket_skips_op(
    op_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Legacy blanket mode (declared is None) must not resolve op references —
    # an unselected op secret is skipped, never prompted for.
    def _boom(*args, **kwargs):  # pragma: no cover — must not be called
        raise AssertionError("blanket mode must not invoke `op`")

    monkeypatch.setattr("relay.config.subprocess.run", _boom)
    cfg = load_config(op_repo)
    env = select_launch_secrets(cfg, None)
    assert env == {"literal": "just-a-value"}


def test_select_launch_secrets_resolves_op_when_declared(
    op_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        # `op read` prints the secret followed by a trailing newline.
        return subprocess.CompletedProcess(argv, 0, stdout="sk_op_secret\n", stderr="")

    monkeypatch.setattr("relay.config.subprocess.run", fake_run)
    cfg = load_config(op_repo)
    env = select_launch_secrets(cfg, ["stripe_key"])
    # Only the declared op key; trailing newline stripped, value untransformed.
    assert env == {"stripe_key": "sk_op_secret"}
    assert calls == [["op", "read", "op://vault/stripe/key"]]


def test_select_launch_secrets_op_missing_binary(
    op_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(argv, **kwargs):
        raise FileNotFoundError("op")

    monkeypatch.setattr("relay.config.subprocess.run", fake_run)
    cfg = load_config(op_repo)
    with pytest.raises(SecretError) as exc:
        select_launch_secrets(cfg, ["stripe_key"])
    msg = str(exc.value)
    # Names the key and reference; never a secret value (there is none).
    assert "stripe_key" in msg
    assert "op://vault/stripe/key" in msg
    assert "not installed" in msg


def test_select_launch_secrets_op_read_nonzero(
    op_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(
            argv, 1, stdout="", stderr="[ERROR] not signed in"
        )

    monkeypatch.setattr("relay.config.subprocess.run", fake_run)
    cfg = load_config(op_repo)
    with pytest.raises(SecretError) as exc:
        select_launch_secrets(cfg, ["stripe_key"])
    msg = str(exc.value)
    assert "stripe_key" in msg
    assert "op://vault/stripe/key" in msg
    assert "not signed in" in msg


def test_unsupported_version(tmp_path: Path) -> None:
    _write(tmp_path / "relay.toml", "version = 99\n")
    _write(tmp_path / "relay.local.toml", 'user = "marc"\n')
    with pytest.raises(ConfigError, match="Unsupported relay.toml version"):
        load_config(tmp_path)


def test_aliases_load_and_strip(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[aliases]\nchat = "  launch bootstrap/orient  "\n'
    )
    cfg = load_config(repo)
    assert cfg.aliases == {"chat": "launch bootstrap/orient"}


def test_aliases_default_empty(repo: Path) -> None:
    cfg = load_config(repo)
    assert cfg.aliases == {}


def test_aliases_reject_non_string(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text() + "\n[aliases]\nchat = 42\n"
    )
    with pytest.raises(ConfigError, match="aliases.chat must be a string"):
        load_config(repo)


def test_aliases_reject_empty_string(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text() + '\n[aliases]\nchat = "   "\n'
    )
    with pytest.raises(ConfigError, match="aliases.chat is empty"):
        load_config(repo)


# --- [ticket.fields.*] -------------------------------------------------------


def test_ticket_fields_load_minimal(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
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
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
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
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
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
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + '\n[ticket.fields.status]\ndescription = "x"\n'
    )
    with pytest.raises(ConfigError, match="canonical ticket frontmatter key"):
        load_config(repo)


def test_ticket_fields_reject_unsupported_key(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[ticket.fields.docket]\n"
            'description = "d"\n'
            'kind = "string"\n'
        )
    )
    with pytest.raises(ConfigError, match="unsupported keys"):
        load_config(repo)


def test_ticket_fields_require_description(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text() + "\n[ticket.fields.docket]\n"
    )
    with pytest.raises(ConfigError, match="description must be a non-empty string"):
        load_config(repo)


def test_ticket_fields_reject_empty_values_list(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[ticket.fields.priority]\n"
            'description = "p"\n'
            "values = []\n"
        )
    )
    with pytest.raises(ConfigError, match="values must not be empty"):
        load_config(repo)


def test_ticket_fields_default_must_match_values(repo: Path) -> None:
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
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
    (repo / "relay.toml").write_text(
        (repo / "relay.toml").read_text()
        + (
            "\n[ticket.fields.docket]\n"
            'description = "d"\n'
            'required = "yes"\n'
        )
    )
    with pytest.raises(ConfigError, match="required must be a boolean"):
        load_config(repo)
