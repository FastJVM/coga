"""Config loading — relay.toml + relay.local.toml.

Stub. Full implementation lands in ticket FJVM-1288.

Expected surface (tentative, will be finalized by FJVM-1288):

    class RelayConfig:
        root: Path                  # repo root (where relay.toml lives)
        shared: dict                # parsed relay.toml
        local: dict                 # parsed relay.local.toml (or {})

        def project(name) -> dict | None
        def project_path(name) -> Path | None
        def agent_type(name) -> dict | None
        def resolve_assignee(nickname) -> dict | None
        def assignee_slack(user) -> str | None
        def secrets_env() -> dict[str, str]
"""
