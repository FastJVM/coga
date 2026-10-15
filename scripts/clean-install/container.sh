#!/usr/bin/env bash
set -euo pipefail

work_root="$HOME/clean-install"
evidence="$work_root/evidence"
repo="$work_root/repo"

if [[ ${1:-} == release && $# -eq 2 ]]; then
    if [[ ! -f $evidence/init-passed.txt ]]; then
        echo "Run the install/init phase successfully before the release check" >&2
        exit 2
    fi
    # Use the installed tool's interpreter, not the container's base Python.
    tool_python="$(uv tool dir)/coga/bin/python"
    exec "$tool_python" -c "$(cat <<'PYTHON'
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
import re
import shutil
import subprocess
import sys

import yaml

agent, repo_arg, evidence_arg = sys.argv[1:]
repo, evidence = Path(repo_arg), Path(evidence_arg)
slug = "verify-first-launch"


def run(*args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(args), flush=True)
    return subprocess.run(args, cwd=repo, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None)


try:
    if not shutil.which(agent):
        raise RuntimeError(f"Install and authenticate {agent} before the release check")
    candidates = [repo / "coga/tasks" / f"{slug}.md",
                  repo / "coga/tasks" / slug / "ticket.md"]
    if any(path.exists() for path in candidates) or (evidence / "release-passed.txt").exists():
        raise RuntimeError("Release check already attempted; use a fresh install run")
    bundled = files("coga.resources").joinpath("templates/coga/bootstrap")
    for resource in ("workflows/code/with-review.md", "skills/code/implement/SKILL.md"):
        if not bundled.joinpath(resource).is_file():
            raise RuntimeError(f"Installed artifact is missing {resource}")
    for legacy in ("coga/.git", "coga/.coga/.venv", "coga/.coga/bin"):
        if (repo / legacy).exists():
            raise RuntimeError(f"Unexpected legacy installation: {legacy}")
    (evidence / "release-environment.txt").write_text(
        f"installed={version('coga')}\npython={sys.version}\nagent={agent}\n")
    run("coga", "create", "Verify first launch", "--workflow", "direct/body",
        "--description", "Verify this installation by recording success on the blackboard, "
        "then run coga bump verify-first-launch as the final action.")
    ticket = next(path for path in candidates if path.is_file())
    run("git", "add", str(ticket.relative_to(repo)))
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo)
    if staged.returncode == 1:
        run("git", "commit", "-m", "Describe first launch check")
    elif staged.returncode:
        raise RuntimeError("Could not inspect staged install-check ticket")
    log = repo / "coga/log.md"
    log_seen = len(log.read_text().splitlines()) if log.exists() else 0
    # Python's code comes from -c, leaving stdin attached to the real terminal.
    run("coga", "launch", slug, "--agent", agent)
    shutil.copyfile(ticket, evidence / "release-task.md")
    # Save only this task's new audit entries, excluding system usage JSON
    # whose request/outcome fields may contain conversation excerpts.
    audit = [line for line in log.read_text().splitlines()[log_seen:]
             if re.match(r"^[0-9-]+ [0-9:]+ (?:v1 )?\[" + slug + r"\] ", line)
             and not re.match(r"^[^[]*\[" + slug + r"\] \[system\] \{", line)]
    (evidence / "release-log.md").write_text("\n".join(audit) + "\n")
    (evidence / "release-git-log.txt").write_text(
        run("git", "log", "--oneline", capture=True).stdout)
    parts = ticket.read_text().split("---", 2)
    if len(parts) != 3 or not isinstance(metadata := yaml.safe_load(parts[1]), dict):
        raise RuntimeError("Release-check ticket has invalid frontmatter")
    if metadata.get("status") != "done":
        raise RuntimeError("Agent exited without completing the release-check ticket")
    if not audit:
        raise RuntimeError("Release-check task has no audit-log entry")
    run("coga", "validate", "--json")
    if run("git", "status", "--porcelain", "--untracked-files=all", capture=True).stdout.strip():
        raise RuntimeError("Release-check repository is not clean")
    (evidence / "release-passed.txt").write_text("Real-agent first-task verification passed\n")
    print("Release check passed; receipts saved in " + str(evidence))
except (OSError, RuntimeError, subprocess.CalledProcessError, StopIteration, yaml.YAMLError) as exc:
    print(f"Release check failed: {exc}", file=sys.stderr)
    sys.exit(1)
PYTHON
)" "$2" "$repo" "$evidence"
fi

# Attended continuations keep both descriptors on the terminal: coga ticket
# and coga build require a real TTY. Login and agent conversation are
# deliberately outside the evidence; only the command and outcome are kept.
attended() {
    local name=$1 record=$evidence/$1.txt status=0
    shift
    if [[ ! -f $evidence/init-passed.txt ]]; then
        echo "Run the install/init phase successfully before the attended $name step" >&2
        exit 2
    fi
    cd "$repo"
    printf '+ coga %s' "$name" | tee -a "$record"
    (($# == 0)) || printf ' %q' "$@" | tee -a "$record"
    printf '\n' | tee -a "$record"
    [[ $name != build ]] || build_state before
    coga "$name" "$@" || status=$?
    [[ $name != build ]] || build_state after
    printf '%s_exit_code=%s\n' "$name" "$status" | tee -a "$record"
    exit "$status"
}

# Where the seeded onboarding ticket stands, and the audit-log lines this
# launch appended; an exit code alone does not show whether coga build bumped
# a step.
build_state() {
    local ticket=coga/tasks/coga-build.md
    if [[ -f $ticket ]]; then
        # Frontmatter only; portable to the macOS walk's BSD sed.
        sed -n -e "2,/^---\$/s/^status: /$1_status=/p" \
            -e "2,/^---\$/s/^step: /$1_step=/p" "$ticket"
    else
        printf '%s_ticket=absent\n' "$1"
    fi | tee -a "$evidence/build.txt"
    if [[ $1 == before ]]; then
        log_seen=0
        [[ ! -f coga/log.md ]] || log_seen=$(wc -l < coga/log.md)
    elif [[ -f coga/log.md ]]; then
        printf 'log:\n' | tee -a "$evidence/build.txt"
        # Match the ref field, not a mention. System usage records (a JSON
        # message) embed request/outcome excerpts of the conversation.
        tail -n "+$((log_seen + 1))" coga/log.md \
            | grep -E '^[0-9-]+ [0-9:]+ (v1 )?\[coga-build\] ' \
            | grep -vE '^[^[]*\[coga-build\] \[system\] \{' \
            | tee -a "$evidence/build.txt" || true
    fi
}

if [[ ${1:-} == ticket && $# -ge 2 ]]; then
    shift
    attended ticket "$@"
fi
if [[ ${1:-} == build ]]; then
    shift
    attended build "$@"
fi

if [[ $# -lt 2 || $# -gt 3 || ! $1 =~ ^(pypi|wheel)$ ]]; then
    echo "usage: coga-clean-install pypi USER | wheel USER WHEEL | ticket TITLE [--agent NAME] | build [--agent NAME] | release AGENT" >&2
    exit 2
fi
mode=$1
operator=$2
if [[ ($mode == wheel && ($# -ne 3 || ! -f $3)) || ($mode == pypi && $# -ne 2) ]]; then
    echo "Supply one existing wheel for wheel mode; no wheel for PyPI mode" >&2
    exit 2
fi
if [[ $(id -u) -eq 0 ]]; then
    echo "Run as the image's fresh non-root coga user" >&2
    exit 2
fi
if [[ -e $work_root ]] || command -v coga >/dev/null 2>&1; then
    echo "This is not a clean install; start a new container" >&2
    exit 2
fi
# Both harnesses test the declared Python floor: the Linux image and the macOS
# walk pin uv to 3.11. Refuse any other interpreter rather than record a walk
# that silently ran on it.
required_python=3.11
if [[ -z ${UV_PYTHON:-} || ${UV_PYTHON_DOWNLOADS:-} != never ]]; then
    echo "Pin uv to Python $required_python: set UV_PYTHON and UV_PYTHON_DOWNLOADS=never" >&2
    exit 2
fi
mkdir -p "$evidence" "$repo"

run() {
    local command status
    printf -v command '%q ' "$@"
    printf '\n+ %s\n' "$command" | tee -a "$evidence/transcript.txt"
    if "$@" 2>&1 | tee -a "$evidence/transcript.txt"; then
        printf 'PASS\t%s\n' "$command" >> "$evidence/steps.txt"
    else
        status=$?
        printf 'FAIL (exit %s)\t%s\n' "$status" "$command" | tee -a "$evidence/steps.txt"
        exit "$status"
    fi
}

checksum() {
    # GNU coreutils on Linux; macOS ships shasum.
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1"; else shasum -a 256 "$1"; fi
}

check_python() {
    local version
    version=$("$1" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')
    echo "Python $version at $1"
    if [[ $version != "$required_python".* ]]; then
        echo "Python $version is not the required $required_python" >&2
        return 2
    fi
}

run id
# On a fresh Mac, this first git call is where the Command Line Tools prompt appears.
run git --version
run uv --version
run uv python find "$UV_PYTHON"
run check_python "$(uv python find "$UV_PYTHON")"
if [[ $mode == pypi ]]; then
    requirement=coga
    if [[ -n ${COGA_CLEAN_INSTALL_VERSION:-} ]]; then
        requirement="coga==$COGA_CLEAN_INSTALL_VERSION"
    fi
    run uv tool install --python "$UV_PYTHON" "$requirement"
else
    run checksum "$3"
    run uv tool install --python "$UV_PYTHON" "$3"
fi
run coga --version
run uv tool list
cd "$repo"
run git init -b main
run git config --local user.name "Coga install harness"
run git config --local user.email "install-harness@example.invalid"
run coga init --user "$operator"
run coga validate --json
printf 'coga init passed; attended coga ticket and coga build have not run\n' | tee "$evidence/init-passed.txt"
echo 'Install and authenticate an agent in this container, then run either:'
echo '  coga-clean-install build --agent claude'
echo '  coga-clean-install ticket "Write a hello-world script" --agent claude'
