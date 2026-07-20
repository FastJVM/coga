#!/usr/bin/env bash
set -euo pipefail

exec > >(tee /evidence/transcript.txt) 2>&1

run() {
    printf '\n+ %s\n' "$*"
    "$@"
}

export DEBIAN_FRONTEND=noninteractive
run apt-get update
run apt-get install -y --no-install-recommends git nodejs npm
run python -m pip install --no-cache-dir uv
run bash -c "$COGA_GATE_AGENT_INSTALL"
run command -v "$COGA_GATE_AGENT"

run uv tool install "coga==$COGA_GATE_VERSION"
export PATH="/root/.local/bin:$PATH"
installed_version=$(coga --version)
printf '%s\n' "$installed_version" | grep -F "$COGA_GATE_VERSION"

run mkdir /work
run git -C /work init
run git -C /work config user.name "Coga install gate"
run git -C /work config user.email "install-gate@example.invalid"
printf '# Clean install gate\n' > /work/README.md
run git -C /work add README.md
run git -C /work commit -m "Initial commit"

cd /work
run coga init --user gate
test ! -d coga/.git
test -x coga/.venv/bin/coga
local_version=$(coga/.venv/bin/coga --version)
test "$installed_version" = "$local_version"
test -f coga/bootstrap/workflows/code/with-review.md
test -f coga/bootstrap/skills/code/implement/SKILL.md

run coga create "Verify first launch" --workflow direct/body
ticket=coga/tasks/verify-first-launch.md
sed -i '/<!-- coga:blackboard -->/i\Complete this installation check by running `coga mark done verify-first-launch`, then stop.\' "$ticket"
run git add "$ticket"
run git commit -m "Describe first launch check"
run coga launch verify-first-launch --agent "$COGA_GATE_AGENT"

grep -q '^status: done$' "$ticket"
grep -q 'verify-first-launch' coga/log.md
run coga validate --json
test -z "$(git status --porcelain --untracked-files=all)"

{
    printf 'image=%s\n' "$COGA_GATE_IMAGE"
    printf 'python=%s\n' "$(python --version 2>&1)"
    printf 'git=%s\n' "$(git --version)"
    printf 'agent=%s\n' "$COGA_GATE_AGENT"
    printf 'installed=%s\n' "$installed_version"
    printf 'repo_local=%s\n' "$local_version"
    printf 'head=%s\n' "$(git rev-parse HEAD)"
} | tee /evidence/environment.txt
cp "$ticket" /evidence/task.md
cp coga/log.md /evidence/coga-log.md
git log --oneline --decorate > /evidence/git-log.txt

printf '\nClean-install verification passed. Evidence is in %s\n' /evidence
