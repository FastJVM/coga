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
    for name in ("bash", "git", "mkdir", "tee"):
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
        if [ "$1" = ticket ]; then
            [ -t 0 ] && [ -t 1 ] || exit 19
        fi
        printf 'coga stub: %s\\n' "$*"
    """)
    _executable(bin_dir / "uv", """
        #!/bin/sh
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
    assert "attended coga ticket has not run" in (evidence / "init-passed.txt").read_text()
    assert not (evidence / "ticket.txt").exists()


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


def test_clean_install_ticket_keeps_terminal_stdio(install_env: dict[str, str]) -> None:
    assert _run(install_env, "pypi", "first-user").returncode == 0
    master, slave = os.openpty()
    try:
        result = subprocess.run(
            ["bash", str(SCRIPT), "ticket", "First task", "--agent", "claude"],
            env=install_env, stdin=slave, stdout=slave, stderr=slave,
        )
    finally:
        os.close(slave)
        os.close(master)
    assert result.returncode == 0
    evidence = Path(install_env["HOME"]) / "clean-install/evidence"
    assert "ticket_exit_code=0" in (evidence / "ticket.txt").read_text()


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
