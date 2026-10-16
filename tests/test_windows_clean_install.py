from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.name == "nt", reason="The AWS driver runs on a Unix host")
def test_windows_ssh_transports_literal_arguments_and_exit_code(git_repo, tmp_path, monkeypatch):
    script = git_repo.root / "scripts/clean-install/aws-windows.sh"
    script.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts/clean-install/aws-windows.sh", script)
    evidence = git_repo.root / ".coga/clean-install/win1"
    evidence.mkdir(parents=True)
    (evidence / "resources.env").write_text("REGION=us-east-1\nPUBLIC_IP=192.0.2.1\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture = tmp_path / "ssh.json"
    ssh = bin_dir / "ssh"
    ssh.write_text(
        f"#!{sys.executable}\nimport json, sys\n"
        f"open({str(capture)!r}, 'w').write(json.dumps(sys.argv[1:]))\n"
        "sys.exit(23)\n"
    )
    ssh.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("AWS_PROFILE", "test")
    words = ["python", "-c", "import sys; print(sys.argv)", "", "a&b", "a>b", "%PATH%",
             'a"b', "it's literal", "space ", "trailing\\", "line\nend\n", "café"]
    result = subprocess.run(["bash", str(script), "ssh", "win1", *words], capture_output=True, text=True)
    assert result.returncode == 23, result.stdout + result.stderr
    remote = json.loads(capture.read_text())[-1]
    prefix = "powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand "
    assert remote.startswith(prefix)
    encoded = remote.removeprefix(prefix)
    assert re.fullmatch(r"[A-Za-z0-9+/=]+", encoded)
    payload = base64.b64decode(encoded).decode("utf-16-le")
    literals = payload.split("\n$ErrorActionPreference", 1)[0]
    decoded = [value.replace("''", "'") for value in re.findall(r"'((?:[^']|'')*)'", literals)]
    assert decoded == words

    # An encoder failure must not start an empty/default remote command.
    capture.unlink()
    iconv = bin_dir / "iconv"
    iconv.write_text("#!/bin/sh\nexit 29\n")
    iconv.chmod(0o755)
    result = subprocess.run(["bash", str(script), "ssh", "win1", *words], capture_output=True, text=True)
    assert result.returncode == 29
    assert not capture.exists()


@pytest.mark.skipif(os.name != "nt", reason="Requires native Windows PowerShell 5.1")
@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Get-Item 'C:\\coga-definitely-absent\\missing'", 1),
        ("Get-FileHash 'C:\\coga-definitely-absent\\missing.whl'", 1),
        ("& coga_definitely_absent_command", 1),
        ("& cmd.exe /c 'echo diagnostic 1>&2 & exit /b 0'", 0),
        ("& cmd.exe /c 'echo diagnostic 1>&2 & exit /b 23'", 23),
    ],
)
def test_windows_walk_records_first_failure(tmp_path: Path, body: str, expected: int):
    # Load the production functions through the PowerShell AST without running
    # setup or creating users. Exercise real cmdlets and native stderr/exit codes.
    def literal(value: Path) -> str:
        return "'" + str(value).replace("'", "''") + "'"

    source = ROOT / "scripts/clean-install/windows-walk.ps1"
    script = f"""
$ErrorActionPreference = 'Continue'
$tokens = $null; $parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile({literal(source)}, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) {{ throw $parseErrors[0] }}
$functions = $ast.FindAll({{ param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -in @('Log', 'Step')
}}, $true)
foreach ($function in $functions) {{ Invoke-Expression $function.Extent.Text }}
$transcript = {literal(tmp_path / 'transcript.txt')}
$steps = {literal(tmp_path / 'steps.txt')}
Step 'probe' {{ {body} }}
Step 'later' {{ 'continued' }}
"""
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-EncodedCommand", encoded], capture_output=True, text=True,
    )
    assert result.returncode == expected, result.stdout + result.stderr
    lines = (tmp_path / "steps.txt").read_text(encoding="utf-8-sig").splitlines()
    assert lines == ([f"FAIL (exit {expected})\tprobe"] if expected else ["PASS\tprobe", "PASS\tlater"])
