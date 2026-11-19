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

### Recipe-backed recurring shims

The releases that moved the blocker-reminders, skill-update and autoclose
jobs to `coga_edge.blocker_reminders`, `coga_edge.skill_update` and
`coga_edge.autoclose` removed the `blocker-reminders`, `skill-update` and
`autoclose` names from `coga run`. The autoclose move also deleted the core
module `coga.autoclose`; its shared `## Dev` parsers and `gh` lookups now live
in `coga.dev_links`. Shims written before these releases reach the old code
in one of these stock shapes, and all stop working once the new wheel is
installed:

- the registry shim (PR 827, `368ae080b`) calls
  `run_recipe(load_config(), "<name>", [])` and then runs `coga bump` itself.
  It now fails with `unknown recipe '<name>'`;
- the autoclose-merged registry shim of PR 898 (`9a7e0dd9a`) additionally
  runs the repository-wide `branch-sweep` recipe
  between autoclose and the bump. It fails the same way;
- the earlier direct shim (PR 705, `df1d06022`) imports
  `coga.blocker_reminders`, `coga.skill_update` or `coga.autoclose`, which no
  longer exist. It now fails with `ModuleNotFoundError`.

Either failure leaves the period `in_progress` and reported by the sweep. It
never runs other code. Copies live wherever recurring creation or a full local
override put them: a full override's `coga/recurring/<name>/ticket.py`, each
outstanding period's `ticket.py`, and parked copies. A package-backed
definition (a state-only carrier) needs no template change: its future periods
copy the new packaged shim. Inventory the callers, including customized ones:

<!-- migration:recipe-shim-callers -->
```sh
rg -l -U --hidden --no-ignore -g '*.py' \
  -e 'coga run (blocker-reminders|skill-update|autoclose)' \
  -e "run_recipe\(\s*(load_config\([^)]*\)|[^,()]+)\s*,\s*(\"|')(blocker-reminders|skill-update|autoclose)(\"|')" \
  -e "(\"|')run(\"|')\s*,\s*(\"|')(blocker-reminders|skill-update|autoclose)(\"|')" \
  -e 'coga\.(blocker_reminders|skill_update|autoclose)' \
  -e 'from coga import (blocker_reminders|skill_update|autoclose)\b' \
  coga/recurring coga/tasks
```

Each stock generation is one exact file per job. Extract every generation
from the retained old wheel
(`coga/resources/templates/coga/recurring/<name>/ticket.py`) or a source
clone, and compare every candidate against each with the `compare` command
above. A candidate matching any is stock:

```sh
git show 368ae080b:src/coga/resources/templates/coga/recurring/blocker-reminders/ticket.py > /tmp/blocker-reminders-827.py
git show df1d06022:src/coga/resources/templates/coga/recurring/blocker-reminders/ticket.py > /tmp/blocker-reminders-705.py
```

The skill-update paths are the same with `skill-update` in place of
`blocker-reminders`. The Git blobs are `035f27cb` (827) and `6f84c384` (705)
for blocker-reminders, and `4cdc7759` (827) and `039a1d5c` (705) for
skill-update. Autoclose's template is `autoclose-merged`, with a third
generation:

```sh
git show 9a7e0dd9a:src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.py > /tmp/autoclose-merged-898.py
git show 368ae080b:src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.py > /tmp/autoclose-merged-827.py
git show df1d06022:src/coga/resources/templates/coga/recurring/autoclose-merged/ticket.py > /tmp/autoclose-merged-705.py
```

Its blobs are `185e3048` (898), `e3e207bd` (827) and `0e81e887` (705). After
installing the new wheel, set `JOB` to the template name and `MODULE` to its
module (`blocker_reminders`, `skill_update`, or `autoclose` for
`autoclose-merged`), then locate the implementation and new shim by
importing, which runs nothing:

<!-- migration:locate-job -->
```sh
"$COGA_PY" - <<'PY'
import importlib
import os
from pathlib import Path
from coga.paths import packaged_template_path
module = importlib.import_module("coga_edge." + os.environ["MODULE"])
print(Path(module.__file__).resolve())
print(packaged_template_path("recurring", os.environ["JOB"], "ticket.py"))
PY
```

Set `NEW_SHIM` to the second printed path, and use the `replace` command above
for each proven stock candidate, once per baseline. It refuses a customized
file. Replacing a stock PR 898 autoclose shim deliberately drops its
repository-wide branch sweep: the clone-scoped `branch-sweep` template owns
that cleanup, and autoclose's own disposal still runs the restricted
owned-branch pass for each ticket it closes. Port a customized shim by hand.
Its old invocation:

```python
code = run_recipe(load_config(), "skill-update", ["--no-pr"])
if code:
    sys.exit(code)
sys.exit(subprocess.run([sys.executable, "-m", "coga.cli", "bump", os.environ["COGA_TASK_SLUG"]], check=False).returncode)
```

becomes this, keeping its own argv and other customizations:

```python
from coga_edge.skill_update import main

raise SystemExit(main(["--no-pr"], scheduled=True))
```

`main(..., scheduled=True)` completes the step itself, so delete the shim's own `coga bump`; a
second bump would advance the next step. It also writes the shared
`## Recipe Failure` report and publishes the job's state on exit.

An autoclose shim ports the same way. Its old invocation:

```python
code = run_recipe(load_config(), "autoclose", [])
if code:
    sys.exit(code)
sys.exit(subprocess.run([sys.executable, "-m", "coga.cli", "bump", os.environ["COGA_TASK_SLUG"]], check=False).returncode)
```

becomes this, keeping its other customizations:

```python
from coga_edge.autoclose import main

raise SystemExit(main([], scheduled=True))
```

Drop a PR 898 `branch-sweep` call rather than porting it.

To keep a reviewed copy instead of following wheel updates, copy the installed
module over a stock new shim. Do this for a full local override's
`ticket.py` (never beside a state-only carrier) or a single period's. The copy
refuses any other existing file:

<!-- migration:job-fork-copy -->
```sh
"$COGA_PY" - <<'PY'
import importlib
import os
import shutil
from pathlib import Path
module = importlib.import_module("coga_edge." + os.environ["MODULE"])
target = Path(os.environ["CANDIDATE"])
stock = Path(os.environ["NEW_SHIM"]).read_bytes()
assert not target.exists() or target.read_bytes() == stock, f"review existing {target}"
shutil.copyfile(module.__file__, target)
print(target)
PY
```

The copy imports only shared `coga` modules and completes its own step.
Restoring the stock shim rejoins wheel updates. Inventory the callers again:
finding none (exit 1) is the expected result. Replacement and the fork copy
change no state: frontmatter, blackboards, `period_state`, generation,
`retires.md` and frozen workflows stay byte-for-byte.

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

If the body also contains the old dispatch paragraph, reconcile it separately
with the same command. This updates the interpreter instructions for either
package-backed or forked phases.

<!-- migration:dream-dispatch-old -->
```text
The two deterministic phases (1 and 5) run registered recipes directly from
this Dream task. Before each run, read the matching skill's
`## Known Skill Contract`, keep reads and writes inside its declared scope,
then invoke the exact `coga run` command below. The recipe inherits this
task's `COGA_TASK_*` context and writes its `## Dream Skill: <name>` section
directly to this task's blackboard. Do not create child worker tasks.
```

<!-- migration:dream-dispatch-new -->
```text
The two deterministic phases (1 and 5) run Python workers directly from
this Dream task. Before each run, read the matching skill's
`## Known Skill Contract`, keep reads and writes inside its declared scope,
then invoke the exact command below with the Python interpreter that runs
`coga`. The worker inherits this task's `COGA_TASK_*` context, writes its
`## Dream Skill: <name>` section directly to this task's blackboard, publishes
eligible Coga state on exit, and never advances this task. An interpreter that
cannot import the worker is a failed phase, not permission to substitute
another command. Do not create child worker tasks.
```

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

After reviewing the diff, this bounded edit replaces one exact match in the
ticket body and preserves all other bytes:

<!-- migration:reconcile -->
```sh
"$COGA_PY" - <<'PY'
import os
import re
from pathlib import Path
path = Path(os.environ["CANDIDATE"])
old = Path(os.environ["OLD_PASSAGE"]).read_bytes()
new = Path(os.environ["NEW_PASSAGE"]).read_bytes()
raw = path.read_bytes()
frontmatter = re.match(rb"\A---\r?\n.*?^---\r?\n", raw, re.MULTILINE | re.DOTALL)
assert frontmatter, "review missing frontmatter"
fences = list(re.finditer(rb"^<!-- coga:blackboard -->[ \t]*\r?$", raw, re.MULTILINE))
assert len(fences) == 1 and frontmatter.end() <= fences[0].start(), "review ticket fence"
start, end = frontmatter.end(), fences[0].start()
body = raw[start:end]
assert old and body.count(old) == 1, "review customized or ambiguous passage"
path.write_bytes(raw[:start] + body.replace(old, new, 1) + raw[end:])
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
   against stock/edited/parked legacy copies, the shipped Dream passages and
   the blocker-reminders, skill-update and autoclose shims; the reconciled commands and
   the replaced or forked periods then run against the installed wheel (and,
   for Dream, a full local fork), with state and unrelated text checked
   byte-for-byte.

Ensure every executing checkout and interpreter has the corresponding reviewed
repo/wheel pair before resuming sweeps. For rollback, stop affected sessions
again, restore a compatible retained wheel and the reviewed executable and
instruction edits together. **Never roll back telemetry state, task lifecycle
state or audit history.** No external repository rollout is authorized by the
implementation of this procedure.
