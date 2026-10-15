from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from textwrap import dedent

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/clean-install/container.sh"


def _executable(path: Path, text: str) -> None:
    path.write_text(dedent(text).lstrip())
    path.chmod(0o755)


def _checksum_stub(bin_dir: Path) -> None:
    # The harness runs on Linux; its tests must not need host GNU coreutils.
    _executable(bin_dir / "sha256sum", f"""
        #!{sys.executable}
        import hashlib
        from pathlib import Path
        import sys

        filename = sys.argv[1]
        print(hashlib.sha256(Path(filename).read_bytes()).hexdigest(), "", filename)
    """)


@pytest.fixture
def install_env(tmp_path: Path, monkeypatch) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _checksum_stub(bin_dir)
    # Keep the host's installed coga out of PATH; only installation exposes it.
    for name in ("bash", "cat", "git", "grep", "mkdir", "sed", "tail", "tee", "wc"):
        (bin_dir / name).symlink_to(shutil.which(name))
    # The pinned interpreter reports a version without running a real Python.
    _executable(bin_dir / "python3.11", """
        #!/bin/sh
        printf '%s\\n' "${COGA_TEST_PYTHON_VERSION:-3.11.9}"
    """)
    _executable(bin_dir / "id", "#!/bin/sh\nprintf '1000\\n'\n")
    stub = tmp_path / "coga-stub"
    _executable(stub, """
        #!/bin/sh
        if [ "$1" = "${COGA_TEST_FAIL:-}" ]; then
            echo 'synthetic installed-artifact failure' >&2
            exit 17
        fi
        if [ "$1" = ticket ] || [ "$1" = build ]; then
            [ -t 0 ] && [ -t 1 ] || exit 19
        fi
        # init seeds the onboarding ticket; build bumps its first step.
        if [ "$1" = init ]; then
            mkdir -p coga/tasks
            printf -- '---\nstatus: active\nstep: 1 (gather-and-spec)\n---\nstep: body\n' \
                > coga/tasks/coga-build.md
            echo '2026-10-13 10:00 v1 [coga-build] [human:first-user] created' > coga/log.md
        fi
        if [ "$1" = build ]; then
            printf -- '---\nstatus: in_progress\nstep: 2 (generate-batch)\n---\n' \
                > coga/tasks/coga-build.md
            echo '2026-10-13 10:05 v1 [coga-build] [agent:claude] bumped' >> coga/log.md
            echo '2026-10-13 10:05 v1 [other] [agent:claude] waiting on [coga-build] idea' >> coga/log.md
            echo '2026-10-13 10:05 v1 [coga-build] [system] {"request":"secret idea"}' >> coga/log.md
            echo '2026-10-13 10:06 v1 [coga-build] [system] started via coga launch' >> coga/log.md
        fi
        printf 'coga stub: %s\\n' "$*"
    """)
    _executable(bin_dir / "uv", """
        #!/bin/sh
        if [ "$1 $2" = 'tool dir' ]; then
            printf '%s\\n' "$COGA_TEST_TOOL_DIR"
            exit
        fi
        if [ "$1 $2" = 'python find' ]; then
            [ "$3" = 3.11 ] || exit 21
            printf '%s\\n' "$COGA_TEST_BIN/python3.11"
            exit
        fi
        if [ "$1" = tool ] && [ "$2" = install ]; then
            [ "${COGA_TEST_FAIL:-}" != install ] || exit 17
            /bin/ln -s "$COGA_TEST_STUB" "$COGA_TEST_BIN/coga"
        fi
        printf 'uv stub: %s\\n' "$*"
    """)
    monkeypatch.delenv("COGA_CLEAN_INSTALL_VERSION", raising=False)
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("UV_PYTHON", "3.11")
    monkeypatch.setenv("UV_PYTHON_DOWNLOADS", "never")
    monkeypatch.setenv("COGA_TEST_STUB", str(stub))
    monkeypatch.setenv("COGA_TEST_BIN", str(bin_dir))
    return dict(os.environ)


def _run(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True,
    )


@pytest.mark.parametrize("mode", ["pypi", "wheel"])
def test_clean_install_reaches_init_from_selected_artifact(
    tmp_path: Path, install_env: dict[str, str], mode: str,
) -> None:
    args = [mode, "first-user"]
    if mode == "wheel":
        wheel = tmp_path / "wheel dir" / "coga-1.0-py3-none-any.whl"
        wheel.parent.mkdir()
        wheel.write_bytes(b"artifact")
        args.append(str(wheel))
    result = _run(install_env, *args)
    assert result.returncode == 0, result.stdout + result.stderr
    evidence = Path(install_env["HOME"]) / "clean-install/evidence"
    steps = (evidence / "steps.txt").read_text()
    assert "PASS\tcoga init --user first-user" in steps
    assert "PASS\tcoga --version" in steps
    assert steps.splitlines()[-1] == "PASS\tcoga validate --json "
    assert f"PASS\tcheck_python {install_env['COGA_TEST_BIN']}/python3.11" in steps
    assert "uv tool install --python 3.11 " in steps
    assert ("uv tool install --python 3.11 coga " in steps) == (mode == "pypi")
    assert "Python 3.11.9 at " in (evidence / "transcript.txt").read_text()
    if mode == "wheel":
        assert "coga-1.0-py3-none-any.whl" in steps
        assert "checksum" in steps
    assert "attended coga ticket and coga build have not run" in (evidence / "init-passed.txt").read_text()
    assert not (evidence / "ticket.txt").exists()
    assert not (evidence / "build.txt").exists()


@pytest.mark.parametrize("failed_command", ["install", "--version", "init", "validate"])
def test_clean_install_preserves_failure_and_stops(
    install_env: dict[str, str], failed_command: str,
) -> None:
    install_env["COGA_TEST_FAIL"] = failed_command
    result = _run(install_env, "pypi", "first-user")
    assert result.returncode == 17
    evidence = Path(install_env["HOME"]) / "clean-install/evidence"
    steps = (evidence / "steps.txt").read_text()
    assert "FAIL (exit 17)" in steps
    assert failed_command in steps.splitlines()[-1]
    assert not (evidence / "init-passed.txt").exists()


@pytest.mark.parametrize(
    "unpinned", [{"UV_PYTHON": ""}, {"UV_PYTHON_DOWNLOADS": "automatic"}],
)
def test_clean_install_refuses_unpinned_python(
    install_env: dict[str, str], unpinned: dict[str, str],
) -> None:
    result = _run({**install_env, **unpinned}, "pypi", "first-user")
    assert result.returncode == 2
    assert "Pin uv to Python 3.11" in result.stderr
    assert not (Path(install_env["HOME"]) / "clean-install").exists()


def test_clean_install_refuses_other_python_before_install(
    install_env: dict[str, str],
) -> None:
    # macOS's /usr/bin/python3 after the Command Line Tools install.
    install_env["COGA_TEST_PYTHON_VERSION"] = "3.9.6"
    result = _run(install_env, "pypi", "first-user")
    assert result.returncode == 2
    evidence = Path(install_env["HOME"]) / "clean-install/evidence"
    transcript = (evidence / "transcript.txt").read_text()
    assert "Python 3.9.6 is not the required 3.11" in transcript
    steps = (evidence / "steps.txt").read_text()
    assert steps.splitlines()[-1].startswith("FAIL (exit 2)\tcheck_python ")
    assert "uv tool install" not in steps


def test_clean_install_refuses_reuse(install_env: dict[str, str]) -> None:
    assert _run(install_env, "pypi", "first-user").returncode == 0
    result = _run(install_env, "pypi", "first-user")
    assert result.returncode == 2
    assert "start a new container" in result.stderr


def _run_attended(env: dict[str, str], *args: str) -> int:
    master, slave = os.openpty()
    try:
        result = subprocess.run(
            ["bash", str(SCRIPT), *args],
            env=env, stdin=slave, stdout=slave, stderr=slave,
        )
    finally:
        os.close(slave)
        os.close(master)
    return result.returncode


def test_clean_install_ticket_keeps_terminal_stdio(install_env: dict[str, str]) -> None:
    assert _run(install_env, "pypi", "first-user").returncode == 0
    assert _run_attended(install_env, "ticket", "First task", "--agent", "claude") == 0
    evidence = Path(install_env["HOME"]) / "clean-install/evidence"
    assert "ticket_exit_code=0" in (evidence / "ticket.txt").read_text()


def test_clean_install_build_records_onboarding_outcome(install_env: dict[str, str]) -> None:
    assert _run(install_env, "pypi", "first-user").returncode == 0
    assert _run_attended(install_env, "build", "--agent", "claude") == 0
    evidence = Path(install_env["HOME"]) / "clean-install/evidence"
    assert (evidence / "build.txt").read_text().splitlines() == [
        "+ coga build --agent claude",
        "before_status=active",
        "before_step=1 (gather-and-spec)",
        "after_status=in_progress",
        "after_step=2 (generate-batch)",
        "log:",
        "2026-10-13 10:05 v1 [coga-build] [agent:claude] bumped",
        "2026-10-13 10:06 v1 [coga-build] [system] started via coga launch",
        "build_exit_code=0",
    ]
    assert "idea" not in (evidence / "build.txt").read_text()


def test_clean_install_build_records_failure_and_removed_ticket(
    install_env: dict[str, str],
) -> None:
    assert _run(install_env, "pypi", "first-user").returncode == 0
    (Path(install_env["HOME"]) / "clean-install/repo/coga/tasks/coga-build.md").unlink()
    install_env["COGA_TEST_FAIL"] = "build"
    assert _run_attended(install_env, "build") == 17
    record = (Path(install_env["HOME"]) / "clean-install/evidence/build.txt").read_text()
    assert record.startswith("+ coga build\nbefore_ticket=absent\n")
    assert "before_ticket=absent\nafter_ticket=absent\n" in record
    assert record.endswith("build_exit_code=17\n")


def test_clean_install_build_needs_init(install_env: dict[str, str]) -> None:
    result = _run(install_env, "build", "--agent", "claude")
    assert result.returncode == 2
    assert "before the attended build step" in result.stderr


def test_clean_install_main_builds_fetched_commit_not_working_tree(
    git_repo, tmp_path: Path, monkeypatch,
) -> None:
    script = git_repo.root / "scripts/clean-install/run.sh"
    script.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts/clean-install/run.sh", script)
    source = git_repo.root / "package.txt"
    source.write_text("committed main\n")
    git_repo.git("add", "package.txt")
    git_repo.git("commit", "-m", "Package on main")
    git_repo.git("push", "origin", "main")
    main_sha = git_repo.git("rev-parse", "HEAD").strip()
    git_repo.checkout_branch("feature")
    source.write_text("uncommitted feature\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _checksum_stub(bin_dir)
    _executable(bin_dir / "docker", """
        #!/bin/sh
        [ "$1 $2" != 'container inspect' ] || exit 1
        printf 'docker stub: %s\\n' "$*"
    """)
    _executable(bin_dir / "uv", """
        #!/bin/sh
        # uv build --wheel --no-sources --out-dir OUTPUT SOURCE
        mkdir -p "$5"
        cp "$6/package.txt" "$5/coga-1.0-py3-none-any.whl"
    """)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    monkeypatch.delenv("COGA_CLEAN_INSTALL_IMAGE", raising=False)
    monkeypatch.setenv("COGA_CLEAN_INSTALL_NETWORK", "host")
    result = subprocess.run(
        ["bash", str(script), "main", "clean-main"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    evidence = git_repo.root / ".coga/clean-install/clean-main"
    assert (evidence / "source.txt").read_text() == f"origin/main={main_sha}\n"
    wheel = evidence / "wheels/coga-1.0-py3-none-any.whl"
    assert wheel.read_text() == "committed main\n"
    assert source.read_text() == "uncommitted feature\n"
    assert "docker build --pull --network host -t coga-clean-install:py311" in result.stdout
    assert "docker create --network host --name clean-main" in result.stdout
    assert "network=host" in (evidence / "result.txt").read_text()
    assert git_repo.git("branch", "--show-current").strip() == "feature"


@pytest.fixture
def aws_mac(git_repo, tmp_path: Path, monkeypatch):
    script = git_repo.root / "scripts/clean-install/aws-mac.sh"
    script.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts/clean-install/aws-mac.sh", script)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls.txt"
    # Canned text output per AWS operation; release-hosts can be refused.
    _executable(bin_dir / "aws", f"""
        #!{sys.executable}
        import os
        import sys

        args = sys.argv[1:]
        with open({str(calls)!r}, "a") as log:
            log.write("aws " + " ".join(args) + "\\n")
        op = args[args.index("--region") + 3]
        if op == os.environ.get("COGA_TEST_AWS_FAIL"):
            sys.exit(23)
        release = os.environ.get("COGA_TEST_RELEASE", "None")
        print({{
            "get-caller-identity": "arn:aws:sts::123:assumed-role/dev",
            "describe-images": "ami-1\\tamzn-ec2-macos-15.6",
            "describe-subnets": "subnet-1\\tvpc-1",
            "create-key-pair": "PRIVATE KEY",
            "create-security-group": "sg-1",
            "allocate-hosts": "h-1",
            "run-instances": "i-1",
            "describe-instances": "203.0.113.5",
            "release-hosts": release,
        }}.get(op, ""))
    """)
    for name in ("ssh", "scp"):
        _executable(bin_dir / name, f"""
            #!/bin/sh
            echo "{name} $*" >> {calls}
        """)
    _executable(bin_dir / "curl", "#!/bin/sh\necho 198.51.100.7\n")
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("AWS_PROFILE", "dev-sso")
    monkeypatch.setenv("COGA_MAC_SSH_WAIT", "0")
    monkeypatch.delenv("COGA_CLEAN_INSTALL_ALLOCATE", raising=False)

    def run(*args: str, **env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(script), *args], env={**os.environ, **env},
            capture_output=True, text=True,
        )

    return run, calls, git_repo.root / ".coga/clean-install/mac1"


def test_aws_mac_provision_needs_cost_approval(aws_mac) -> None:
    run, calls, evidence = aws_mac
    result = run("provision", "mac1", "us-east-1", "us-east-1a")
    assert result.returncode == 2
    assert "24 hours" in result.stderr
    assert not calls.exists()
    assert not evidence.exists()


def test_aws_mac_records_every_resource_and_tears_down(aws_mac) -> None:
    run, calls, evidence = aws_mac
    result = run(
        "provision", "mac1", "us-east-1", "us-east-1a",
        COGA_CLEAN_INSTALL_ALLOCATE="yes",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    resources = (evidence / "resources.env").read_text()
    for line in ("KEY_NAME=coga-clean-install-mac1", "SG_ID=sg-1", "HOST_ID=h-1",
                 "INSTANCE_ID=i-1", "PUBLIC_IP=203.0.113.5", "SSH_FROM=198.51.100.7/32"):
        assert line in resources
    assert (evidence / "key.pem").stat().st_mode & 0o777 == 0o600
    aws_calls = [c for c in calls.read_text().splitlines() if c.startswith("aws ")]
    assert all("--profile dev-sso --region us-east-1" in c for c in aws_calls)
    assert "--placement Tenancy=host,HostId=h-1" in calls.read_text()
    assert "--port 22 --cidr 198.51.100.7/32" in calls.read_text()
    assert "macos-walk.sh reset" in calls.read_text()

    # Inside 24 hours AWS refuses the release; everything else is still removed.
    result = run("teardown", "mac1", COGA_TEST_RELEASE="Too early to release")
    assert result.returncode == 1
    assert "h-1 NOT released: Too early to release" in result.stdout
    resources = (evidence / "resources.env").read_text()
    assert "INSTANCE_TERMINATED=" in resources and "SG_DELETED=" in resources
    assert "KEY_DELETED=" in resources and "HOST_RELEASED=" not in resources
    ops = [c.split()[6] for c in calls.read_text().splitlines() if c.startswith("aws ")]
    teardown = ops[ops.index("terminate-instances"):]
    assert teardown == ["terminate-instances", "wait", "delete-security-group",
                        "delete-key-pair", "release-hosts"]

    assert run("release", "mac1").returncode == 0
    assert "HOST_RELEASED=" in (evidence / "resources.env").read_text()
    assert run("teardown", "mac1").returncode == 0
    assert calls.read_text().count("terminate-instances") == 1


@pytest.mark.parametrize(
    ("operation", "missing_key", "forbidden_operation"),
    [
        ("get-caller-identity", "CALLER", "create-key-pair"),
        ("create-security-group", "SG_ID", "allocate-hosts"),
        ("allocate-hosts", "HOST_ID", "run-instances"),
        ("run-instances", "INSTANCE_ID", "wait"),
    ],
)
def test_aws_mac_stops_on_failed_resource_capture(
    aws_mac, operation: str, missing_key: str, forbidden_operation: str,
) -> None:
    run, calls, evidence = aws_mac
    result = run(
        "provision", "mac1", "us-east-1", "us-east-1a",
        COGA_CLEAN_INSTALL_ALLOCATE="yes", COGA_TEST_AWS_FAIL=operation,
    )
    assert result.returncode == 23, result.stdout + result.stderr
    assert f"{missing_key}=" not in (evidence / "resources.env").read_text()
    ops = [c.split()[6] for c in calls.read_text().splitlines() if c.startswith("aws ")]
    assert forbidden_operation not in ops
    # Every successfully recorded resource remains available to teardown.
    assert run("teardown", "mac1").returncode == 0


def test_aws_mac_passwords_stay_out_of_logs(aws_mac) -> None:
    run, calls, evidence = aws_mac
    assert run(
        "provision", "mac1", "us-east-1", "us-east-1a",
        COGA_CLEAN_INSTALL_ALLOCATE="yes",
    ).returncode == 0
    for args, password_path in (
        (("walk", "mac1", "pypi", "walk1"), evidence / "walks/walk1/password.txt"),
        (("vnc", "mac1"), evidence / "vnc-password.txt"),
    ):
        result = run(*args)
        assert result.returncode == 0, result.stdout + result.stderr
        password = password_path.read_text().strip()
        assert password and password in calls.read_text()  # delivered to SSH
        assert password not in result.stdout + result.stderr
        assert password not in (evidence / "host.txt").read_text()
        assert password_path.stat().st_mode & 0o777 == 0o600
    assert (evidence / "host.txt").stat().st_mode & 0o777 == 0o600


def test_aws_mac_walk_quotes_remote_argv(aws_mac, tmp_path: Path) -> None:
    run, calls, evidence = aws_mac
    assert run(
        "provision", "mac1", "us-east-1", "us-east-1a",
        COGA_CLEAN_INSTALL_ALLOCATE="yes",
    ).returncode == 0
    remote = tmp_path / "remote.txt"
    # Record only the remote command string, exactly as the remote shell sees it.
    _executable(tmp_path / "bin/ssh", f"""
        #!/bin/sh
        for arg; do last=$arg; done
        printf '%s\\n' "$last" >> {remote}
    """)
    operator = "Alice Smith; touch pwned"
    result = run("walk", "mac1", "pypi", "walk1", operator)
    assert result.returncode == 0, result.stdout + result.stderr
    password = (evidence / "walks/walk1/password.txt").read_text().strip()
    walk = next(line for line in remote.read_text().splitlines() if "macos-walk.sh" in line)
    assert shlex.split(walk) == [
        "bash", "/tmp/coga-clean-install/macos-walk.sh", "walk",
        "pypi", operator, "walk1", password,
    ]


def test_aws_mac_main_walk_without_gnu_checksum(
    aws_mac, git_repo, tmp_path: Path, monkeypatch,
) -> None:
    run, calls, evidence = aws_mac
    assert run(
        "provision", "mac1", "us-east-1", "us-east-1a",
        COGA_CLEAN_INSTALL_ALLOCATE="yes",
    ).returncode == 0
    git_repo.git("push", "origin", "main")
    # A host tool path with shasum, but deliberately no sha256sum.
    bin_dir = tmp_path / "portable-bin"
    bin_dir.mkdir()
    for name in ("bash", "git", "dirname", "tee", "date", "mkdir", "openssl",
                 "mktemp", "tar", "rm", "basename", "ssh", "scp"):
        (bin_dir / name).symlink_to(shutil.which(name))
    _executable(bin_dir / "uv", """
        #!/bin/sh
        mkdir -p "$5"
        echo wheel > "$5/coga-1.0-py3-none-any.whl"
    """)
    _executable(bin_dir / "shasum", """
        #!/bin/sh
        [ "$1 $2" = '-a 256' ] || exit 18
        echo "portable-checksum $3"
    """)
    monkeypatch.setenv("PATH", str(bin_dir))
    result = run("walk", "mac1", "main", "walk1")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "portable-checksum" in result.stdout
    assert "macos-walk.sh walk wheel" in calls.read_text()
    assert "origin/main=" in (evidence / "walks/walk1/source.txt").read_text()


def test_macos_walk_provisions_and_pins_python_311(tmp_path: Path, monkeypatch) -> None:
    walk_dir = tmp_path / "coga-clean-install"
    walk_dir.mkdir()
    shutil.copyfile(ROOT / "scripts/clean-install/macos-walk.sh", walk_dir / "macos-walk.sh")
    calls = tmp_path / "calls.txt"
    # Stand-in for the shared walk: record the interpreter pins it receives.
    _executable(walk_dir / "container.sh", f"""
        #!/bin/sh
        echo "container.sh $* UV_PYTHON=$UV_PYTHON UV_PYTHON_DOWNLOADS=$UV_PYTHON_DOWNLOADS" >> {calls}
    """)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("bash", "dirname", "sh", "touch"):
        (bin_dir / name).symlink_to(shutil.which(name))
    created = tmp_path / "user-created"
    _executable(bin_dir / "id", f"#!/bin/sh\n[ -e {created} ]\n")
    _executable(bin_dir / "sysadminctl", f"#!/bin/sh\ntouch {created}\n")
    _executable(bin_dir / "createhomedir", "#!/bin/sh\n")
    # sudo -H -u USER /bin/zsh -lc SCRIPT ARGS... runs SCRIPT in bash here.
    _executable(bin_dir / "sudo", """
        #!/bin/sh
        if [ "$1" = -H ]; then
            shift 5
            exec bash -c "$@"
        fi
        exec "$@"
    """)
    _executable(bin_dir / "curl", "#!/bin/sh\necho true\n")
    _executable(bin_dir / "uv", f"""
        #!/bin/sh
        echo "uv $* UV_PYTHON=${{UV_PYTHON:-}}" >> {calls}
    """)
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    monkeypatch.delenv("UV_PYTHON", raising=False)
    monkeypatch.delenv("UV_PYTHON_DOWNLOADS", raising=False)
    result = subprocess.run(
        ["bash", str(walk_dir / "macos-walk.sh"), "walk", "pypi", "installer", "walk1", "pw"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls.read_text().splitlines() == [
        "uv python install 3.11 UV_PYTHON=",
        "container.sh pypi installer UV_PYTHON=3.11 UV_PYTHON_DOWNLOADS=never",
    ]


def test_clean_install_can_pin_a_pypi_release(install_env: dict[str, str]) -> None:
    install_env["COGA_CLEAN_INSTALL_VERSION"] = "0.4.0"
    result = _run(install_env, "pypi", "installer")
    assert result.returncode == 0, result.stdout + result.stderr
    steps = (Path(install_env["HOME"]) / "clean-install/evidence/steps.txt").read_text()
    assert "uv tool install --python 3.11 coga==0.4.0" in steps


@pytest.fixture
def release_env(install_env: dict[str, str], tmp_path: Path) -> dict[str, str]:
    assert _run(install_env, "pypi", "installer").returncode == 0
    tool_dir = tmp_path / "tools"
    python = tool_dir / "coga/bin/python"
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    install_env["COGA_TEST_TOOL_DIR"] = str(tool_dir)
    metadata_root = tmp_path / "metadata"
    metadata = metadata_root / "coga-0.4.0.dist-info/METADATA"
    metadata.parent.mkdir(parents=True)
    metadata.write_text("Metadata-Version: 2.1\nName: coga\nVersion: 0.4.0\n")
    install_env["PYTHONPATH"] = os.pathsep.join((str(metadata_root), str(ROOT / "src")))
    _executable(Path(install_env["COGA_TEST_BIN"]) / "claude", "#!/bin/sh\nexit 0\n")
    _executable(Path(install_env["COGA_TEST_STUB"]), f'''
        #!{sys.executable}
        import os
        from pathlib import Path
        import subprocess
        import sys

        command = sys.argv[1]
        failure = os.environ.get("COGA_TEST_RELEASE_FAIL")
        ticket = Path("coga/tasks/verify-first-launch/ticket.md")
        log = Path("coga/log.md")
        if command == "create":
            ticket.parent.mkdir(parents=True)
            ticket.write_text("---\\nstatus: draft\\n---\\n")
        elif command == "launch":
            assert os.isatty(0) and os.isatty(1), "agent lost terminal"
            if failure == "launch":
                sys.exit(17)
            status = "blocked" if failure == "incomplete" else "done"
            ticket.write_text("---\\nstatus: " + status + "\\n---\\n")
            entry = ("2026-10-14 12:00 [other] [installer] mentions [verify-first-launch]\\n"
                     if failure == "log" else
                     "2026-10-14 12:00 v1 [verify-first-launch] [installer] task done\\n")
            log.write_text(log.read_text() + entry +
                           '2026-10-14 12:00 v1 [verify-first-launch] [system] {{"request":"secret idea"}}\\n')
            subprocess.run(["git", "add", "coga"], check=True)
            subprocess.run(["git", "commit", "-m", "Complete first task"], check=True)
            if failure == "dirty":
                Path("uncommitted.txt").write_text("dirty")
        elif command == "validate" and failure == "validate":
            sys.exit(17)
    ''')
    return install_env


def _release(env: dict[str, str]) -> int:
    master, slave = os.openpty()
    try:
        result = subprocess.run(
            ["bash", str(SCRIPT), "release", "claude"], env=env,
            stdin=slave, stdout=slave, stderr=slave,
        )
        if result.returncode:
            print(os.read(master, 65536).decode())
        return result.returncode
    finally:
        os.close(slave)
        os.close(master)


def test_release_check_requires_completed_logged_clean_task(release_env) -> None:
    assert _release(release_env) == 0
    evidence = Path(release_env["HOME"]) / "clean-install/evidence"
    assert (evidence / "release-passed.txt").is_file()
    assert "status: done" in (evidence / "release-task.md").read_text()
    audit = (evidence / "release-log.md").read_text()
    assert "[verify-first-launch]" in audit
    assert "[coga-build]" not in audit
    assert "secret idea" not in audit
    assert "installed=" in (evidence / "release-environment.txt").read_text()
    assert "Complete first task" in (evidence / "release-git-log.txt").read_text()
    assert _release(release_env) != 0  # Existing success cannot pass as a new run.


@pytest.mark.parametrize("failure", ["launch", "incomplete", "log", "dirty", "validate"])
def test_release_check_does_not_claim_success_after_failure(release_env, failure) -> None:
    release_env["COGA_TEST_RELEASE_FAIL"] = failure
    assert _release(release_env) != 0
    evidence = Path(release_env["HOME"]) / "clean-install/evidence"
    assert not (evidence / "release-passed.txt").exists()


def test_release_check_requires_successful_init(install_env) -> None:
    result = _run(install_env, "release", "claude")
    assert result.returncode == 2
    assert "Run the install/init phase" in result.stderr


@pytest.mark.parametrize("mode", ["pypi", "main"])
def test_clean_install_host_applies_release_pin_only_to_pypi(
    git_repo, tmp_path: Path, monkeypatch, mode: str,
) -> None:
    script = git_repo.root / "scripts/clean-install/run.sh"
    script.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts/clean-install/run.sh", script)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _executable(bin_dir / "docker", """
        #!/bin/sh
        [ "$1 $2" != 'container inspect' ] || exit 1
        printf 'docker stub: %s\\n' "$*"
    """)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("COGA_CLEAN_INSTALL_VERSION", "0.4.0")
    monkeypatch.setenv("COGA_CLEAN_INSTALL_IMAGE", "test-image")
    result = subprocess.run(
        ["bash", str(script), mode, "release-040"], capture_output=True, text=True,
    )
    if mode == "main":
        assert result.returncode == 2
        assert "applies only to pypi mode" in result.stderr
        assert not (git_repo.root / ".coga/clean-install/release-040").exists()
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        assert "docker stub: exec -e COGA_CLEAN_INSTALL_VERSION=0.4.0 release-040 coga-clean-install pypi installer" in result.stdout
