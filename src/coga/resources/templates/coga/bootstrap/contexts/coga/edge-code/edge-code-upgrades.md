# Adopting wheel-owned edge code

This is the operator procedure owned by [coga/edge-code](SKILL.md), not an
installer, launch hook or recurring updater. Work in a reviewed migration
branch in the host Git root. Use the actual configured recurring/tasks roots
below if the repository changes the default layout. This includes parked,
paused and blocked copies, not just the active recurring task.

1. Inventory first. These commands deliberately include hidden and ignored
   files; inspect each candidate's contents and provenance, not just its name.
   Narrow the resulting list by reviewed evidence of the affected job. A
   familiar slug or a clean Git tree does not prove upstream ownership.

<!-- migration:inventory -->
```sh
rg --files --hidden --no-ignore -g '*.py' coga/recurring coga/tasks | LC_ALL=C sort
```

For a release removing recipe targets, also inventory their exact callers in
Python shims and markdown, including Dream Phase 1/5 in templates and all
outstanding/parked period bodies. Search names even when callers are customized.
The removed names so far are `validate-drift` and `cleanup-orphan-markers`:

<!-- migration:callers -->
```sh
rg -n --hidden --no-ignore -g '*.md' -g '*.py' 'coga run (validate-drift|cleanup-orphan-markers)' coga/recurring coga/tasks
```

2. Quiesce affected launches and sweeps in **all participating checkouts**.
   Inspect the operator's sessions and processes (for example `ps -eo
   pid,ppid,args`), wait for scripts and private workers to exit, or explicitly
   stop their owning sessions. A ticket status alone is not process evidence.
   Keep executing code and frozen instructions untouched while a run exists;
   do not install the replacement wheel until those runs have stopped.
   A process listing taken inside a sandboxed agent session shows only that
   sandbox's processes: it is not host-wide evidence and cannot rule out cron,
   other users or hosts, agent-app schedulers, or other clones. When the
   session cannot see them, the owner records which writers participate,
   which are excluded, and who stops them. An observed editable install or a
   fresh import is not upgrade evidence and does not prove a running
   supervisor reloaded the code; record the reviewed wheel's hash as
   step 4 requires.

3. Retain the old wheel and its hash, and extract its source without running
   the job. Set `OLD_SOURCE` to that exact old shipped implementation. For
   unreleased installs record the source commit/blob too: phone-home's original
   full script was introduced by PR 880 (`ac14d63fc`), after version 0.3.2 was
   stamped. That version alone cannot establish a baseline. In a source clone
   with the verified commit available, extract it with:

```sh
git show ac14d63fc:coga/recurring/phone-home/ticket.py > /tmp/phone-home-old.py
git rev-parse ac14d63fc:coga/recurring/phone-home/ticket.py
```

For a wheel baseline, use `python -m zipfile -e /path/to/old.whl
/tmp/old-wheel` and inspect its resource tree. Keep unknown origins and byte
differences as review items. Repeat this comparison with `CANDIDATE` set to each
inventoried source, including committed customizations:

<!-- migration:compare -->
```sh
if test -f "$OLD_SOURCE" && cmp -s "$OLD_SOURCE" "$CANDIDATE"; then
    printf 'stock: %s\n' "$CANDIDATE"
else
    printf 'review: %s\n' "$CANDIDATE"
fi
```

4. Install the new wheel in the existing Coga environment. Resolve its actual
   interpreter from the console script's shebang. A user install's scripts
   directory need not contain Python; for a uv/pipx environment, keep the
   shebang's interpreter path without resolving its symlinks out of the venv:

<!-- migration:interpreter -->
```sh
COGA_PY=$(python3 - <<'PY'
import os
from pathlib import Path
from shutil import which

script = which("coga")
if script is None:
    raise SystemExit("coga is not on PATH")
with Path(script).open() as stream:
    line = stream.readline().rstrip("\r\n")
interpreter = line[2:] if line.startswith("#!") else ""
path = Path(interpreter)
if (not path.is_absolute() or any(c.isspace() for c in interpreter)
        or not path.name.startswith("python") or not path.is_file()
        or not os.access(path, os.X_OK)):
    raise SystemExit("No direct Python shebang: inspect the launcher and use its environment manager to identify the interpreter")
print(interpreter)
PY
) &&
"$COGA_PY" -c 'import sys; print(sys.executable)'
```

Stop if resolution fails. For an `env` shebang or shell wrapper, inspect the
launcher and its owning environment manager, set `COGA_PY` to that
installation's Python, and verify it with `"$COGA_PY" -c 'import sys;
print(sys.executable)'` before proceeding. Do not substitute an unrelated
ambient Python. Then upgrade that installation:

```sh
"$COGA_PY" -m pip install --upgrade /path/to/reviewed-coga.whl
```

For a tool environment without pip use its existing environment manager to
replace that same installation. Record the wheel hash (`sha256sum
/path/to/reviewed-coga.whl`), not just `importlib.metadata.version("coga")`.
Locate the new files by importing, which does not execute `main` or deliver:

<!-- migration:locate -->
```sh
"$COGA_PY" -c 'from pathlib import Path; import coga_edge.phone_home as job; from coga.paths import packaged_template_path; print(Path(job.__file__).resolve()); print(packaged_template_path("recurring", "phone-home", "ticket.py"))'
```

Set `NEW_SHIM` to the second printed path. Review old/new artifact diffs.
For each **proven stock** candidate selected for continued execution, prepare
this guarded replacement (with `OLD_SOURCE`, `CANDIDATE`, `NEW_SHIM` set to
absolute paths). It refuses unknown/edited files rather than overwriting them:

<!-- migration:replace -->
```sh
cmp -s "$OLD_SOURCE" "$CANDIDATE" && cp "$NEW_SHIM" "$CANDIDATE"
```

For a package-backed parent, do not copy a shim beside its state carrier:
upgrade the package instead. A carrier plus local executable is an incomplete
fork. The replacement procedure above applies to existing full local definitions
and already-frozen period scripts; it never materializes a missing definition.

Select both the template and outstanding periods, including parked ones that
may resume. Do not regenerate periods, reset parent markers, or complete/cancel
tasks to obtain new code. Preserve frontmatter, blackboards, `period_state`,
generation, frozen workflows and unrelated attachments byte-for-byte.

For each edited file, explicitly choose a manual port to the new implementation
or retention as a full local fork, and review compatibility with the new shared
core. Unknown baselines stay unchanged until reviewed. To create a fresh full
fork after adoption, inspect the first located path (`IMPLEMENTATION`), then:

```sh
less "$IMPLEMENTATION"
cp "$IMPLEMENTATION" "$CANDIDATE"
git diff -- "$CANDIDATE"
```

Retain any previous customized source in Git before replacement. Restore the
stock shim to rejoin upstream implementation updates.

### Dream Phase 1/5 reconciliation (recipe removal)

The release that moved Dream's workers to `coga_edge` removed the
`validate-drift` and `cleanup-orphan-markers` recipe names; `coga run` now
refuses both with exit 2. Dream bodies written before it still name them: a
local Dream override's `ticket.md`, outstanding and parked Dream periods, and
customized copies. A stale passage fails its phase loudly; it never runs other
code. Reconcile each selected markdown file after installing the new wheel and
before resuming Dream. Write each passage below to a text file, without its
fence lines and without a trailing newline, and set `OLD_PASSAGE` to the old
passage and `NEW_PASSAGE` to the replacement.

Phase 1, as shipped before the move:

<!-- migration:dream-phase-1-old -->
```text
Read `bootstrap/dream/tasks/validate-drift`, then run
`coga run validate-drift`. The recipe runs the same deterministic surface as
`coga validate --json`, classifies every issue, and appends
`## Dream Skill: validate-drift` to this task's blackboard.
```

Phase 1 for a package-backed Dream (the shipped body):

<!-- migration:dream-phase-1-new -->
```text
Read `bootstrap/dream/tasks/validate-drift`, then run
`python -m coga_edge.validate_drift`. The worker runs the same deterministic
surface as `coga validate --json`, classifies every issue, and appends
`## Dream Skill: validate-drift` to this task's blackboard.
```

Phase 1 for a full local Dream fork that runs its own copy:

<!-- migration:dream-phase-1-fork -->
```text
Read `bootstrap/dream/tasks/validate-drift`, then run
`python "$COGA_COGA_OS_ROOT/recurring/dream/validate_drift.py"`. The worker
runs the same deterministic surface as `coga validate --json`, classifies
every issue, and appends `## Dream Skill: validate-drift` to this task's
blackboard.
```

Phase 5, as shipped before the move:

<!-- migration:dream-phase-5-old -->
```text
Read `bootstrap/dream/tasks/cleanup-orphan-markers`, then run
`coga run cleanup-orphan-markers`. The recipe detects cleanup candidates and
gates deletion through `bootstrap/delete-task` (`coga run delete-task`). That
delete surface ships, but until its cleanup PR-dispatch wiring is finished the
recipe reports `human-needed` and deletes nothing.
```

Phase 5 for a package-backed Dream (the shipped body):

<!-- migration:dream-phase-5-new -->
```text
Read `bootstrap/dream/tasks/cleanup-orphan-markers`, then run
`python -m coga_edge.cleanup_orphan_markers`. The worker detects cleanup
candidates and gates deletion through `bootstrap/delete-task`
(`coga run delete-task`). That delete surface ships, but until its cleanup
PR-dispatch wiring is finished the worker reports `human-needed` and deletes
nothing.
```

Phase 5 for a full local Dream fork that runs its own copy:

<!-- migration:dream-phase-5-fork -->
```text
Read `bootstrap/dream/tasks/cleanup-orphan-markers`, then run
`python "$COGA_COGA_OS_ROOT/recurring/dream/cleanup_orphan_markers.py"`. The
worker detects cleanup candidates and gates deletion through
`bootstrap/delete-task` (`coga run delete-task`). That delete surface ships,
but until its cleanup PR-dispatch wiring is finished the worker reports
`human-needed` and deletes nothing.
```

Choose the fork passages only for a full local Dream override (its own
`coga/recurring/dream/ticket.md` definition, not a state-only carrier) that
should keep running a reviewed copy instead of following wheel updates, and
for that override's periods. The fork path assumes the default
`coga/recurring/` layout; adjust it to the configured recurring root. Copy the
installed workers beside the override's ticket first, with `DREAM_DIR` set to
that directory. The copy refuses to overwrite an existing file:

<!-- migration:dream-fork-copy -->
```sh
"$COGA_PY" - <<'PY'
import os
import shutil
from pathlib import Path
import coga_edge.cleanup_orphan_markers
import coga_edge.validate_drift
destination = Path(os.environ["DREAM_DIR"])
for module in (coga_edge.validate_drift, coga_edge.cleanup_orphan_markers):
    target = destination / Path(module.__file__).name
    assert not target.exists(), f"review existing {target}"
    shutil.copyfile(module.__file__, target)
    print(target)
PY
```

Recurring creation copies only `ticket.py`, so the fork's periods run the
copies beside the override's ticket. A copied worker imports nothing from
`coga_edge` and stops receiving wheel fixes; restoring the
package-backed passages rejoins them.

After reviewing the diff, this bounded edit preserves all bytes outside the
selected passage and fails on missing or ambiguous matches:

<!-- migration:reconcile -->
```sh
"$COGA_PY" - <<'PY'
import os
from pathlib import Path
path = Path(os.environ["CANDIDATE"])
old = Path(os.environ["OLD_PASSAGE"]).read_bytes()
new = Path(os.environ["NEW_PASSAGE"]).read_bytes()
raw = path.read_bytes()
assert old and raw.count(old) == 1, "review customized or ambiguous passage"
path.write_bytes(raw.replace(old, new, 1))
PY
```

Export these variables for the Python command. A refusal means a customized,
missing or ambiguous passage: port that copy by hand to one of the new
commands, keeping its other text. Preserving its bytes does not ensure it will
run. Inventory callers again and review each remaining one; the command
finding none (exit 1) is the expected result. Frontmatter, frozen workflows,
`period_generation` and blackboards stay untouched. Record tester adoption
before upgrading them to a contracting wheel; do not ship recipe removal as an
unattended wheel-only upgrade.

5. Review `git diff --check` and the precise file diff; merge through normal
   repo practice. In a scratch copy, verify with CI/pytest suppression and fake
   transport, never production phone-home merely to inspect code. The automated
   receipts are `tests/test_edge_distribution.py`: commands above are executed
   against stock/edited/parked legacy copies and the shipped Dream passages,
   whose reconciled commands then run against the installed wheel and a full
   local fork, with state and unrelated text checked byte-for-byte.

Ensure every executing checkout and interpreter has the corresponding reviewed
repo/wheel pair before resuming sweeps. For rollback, stop affected sessions
again, restore a compatible retained wheel and the reviewed executable and
instruction edits together. **Never roll back telemetry state, task lifecycle
state or audit history.** No external repository rollout is authorized by the
implementation of this procedure.
