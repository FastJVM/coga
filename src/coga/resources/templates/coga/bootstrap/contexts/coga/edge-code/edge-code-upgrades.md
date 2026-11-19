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
outstanding/parked period bodies. Search names even when callers are customized:

<!-- migration:callers -->
```sh
rg -n --hidden --no-ignore -g '*.md' -g '*.py' 'coga run (validate-drift|cleanup-orphan-markers|delete-task)' coga/recurring coga/tasks
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

The release that moved the blocker-reminders and skill-update jobs to
`coga_edge.blocker_reminders` and `coga_edge.skill_update` removed both names
from `coga run`. Shims written before it reach the old code in one of two
stock shapes, and both stop working once the new wheel is installed:

- the registry shim (PR 827, `368ae080b`) calls
  `run_recipe(load_config(), "<name>", [])` and then runs `coga bump` itself.
  It now fails with `unknown recipe '<name>'`;
- the earlier direct shim (PR 705, `df1d06022`) imports
  `coga.blocker_reminders` or `coga.skill_update`, which no longer exist. It
  now fails with `ModuleNotFoundError`.

Either failure leaves the period `in_progress` and reported by the sweep. It
never runs other code. Copies live wherever recurring creation or a full local
override put them: a full override's `coga/recurring/<name>/ticket.py`, each
outstanding period's `ticket.py`, and parked copies. A package-backed
definition (a state-only carrier) needs no template change: its future periods
copy the new packaged shim. Inventory the callers, including customized ones:

<!-- migration:recipe-shim-callers -->
```sh
rg -n --hidden --no-ignore -g '*.py' -e 'coga run (blocker-reminders|skill-update)' -e 'run_recipe\(.*(blocker-reminders|skill-update)' -e 'coga\.(blocker_reminders|skill_update)' coga/recurring coga/tasks
```

Each stock generation is one exact file per job. Extract both from the
retained old wheel (`coga/resources/templates/coga/recurring/<name>/ticket.py`)
or a source clone, and compare every candidate against both with the
`compare` command above. A candidate matching either is stock:

```sh
git show 368ae080b:src/coga/resources/templates/coga/recurring/blocker-reminders/ticket.py > /tmp/blocker-reminders-827.py
git show df1d06022:src/coga/resources/templates/coga/recurring/blocker-reminders/ticket.py > /tmp/blocker-reminders-705.py
```

The skill-update paths are the same with `skill-update` in place of
`blocker-reminders`. The Git blobs are `035f27cb` (827) and `6f84c384` (705)
for blocker-reminders, and `4cdc7759` (827) and `039a1d5c` (705) for
skill-update. After installing the new wheel, set `JOB` to the job name and
locate its implementation and new shim by importing, which runs nothing:

<!-- migration:locate-job -->
```sh
"$COGA_PY" - <<'PY'
import importlib
import os
from pathlib import Path
from coga.paths import packaged_template_path
job = os.environ["JOB"]
module = importlib.import_module("coga_edge." + job.replace("-", "_"))
print(Path(module.__file__).resolve())
print(packaged_template_path("recurring", job, "ticket.py"))
PY
```

Set `NEW_SHIM` to the second printed path, and use the `replace` command above
for each proven stock candidate, once per baseline. It refuses a customized
file. Port a customized shim by hand. Its old invocation:

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
job = os.environ["JOB"]
module = importlib.import_module("coga_edge." + job.replace("-", "_"))
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
change no state: frontmatter, blackboards, `period_state`, generation and
frozen workflows stay byte-for-byte.

### Instruction reconciliation for the later recipe-removal release

`_v2/gigantic-refactor-move-recurring-recipes-out-of-co` must use this same adoption
policy for old shims **and** old Dream Phase 1/5 instructions before deleting
registry targets. That release supplies reviewed old/new passages from its
artifacts; use `OLD_PASSAGE` and `NEW_PASSAGE` text files for each exact passage,
and `CANDIDATE` for each selected template or period markdown. After reviewing
the diff, this bounded edit preserves all bytes outside that passage and fails
on missing or ambiguous matches:

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

Export these variables for the Python command. Customized callers of removed
symbols require reconciliation; preserving their bytes does not ensure they
will run. Inventory again and review each remaining caller before removing its
target. Record tester adoption before upgrading them to a contracting wheel;
do not ship recipe removal as an unattended wheel-only upgrade. The current migration removes the blocker-reminders and skill-update names.
Dream passages and workers are outside this migration; the fixtures exercise
representative instruction reconciliation for the later release.

5. Review `git diff --check` and the precise file diff; merge through normal
   repo practice. In a scratch copy, verify with CI/pytest suppression and fake
   transport, never production phone-home merely to inspect code. The automated
   receipts are `tests/test_edge_distribution.py`: commands above are executed
   against stock/edited/parked legacy copies, representative Dream passages and
   the blocker-reminders and skill-update shims, whose replaced or forked
   periods then run against a read-only installed wheel, with state and
   unrelated text checked byte-for-byte.

Ensure every executing checkout and interpreter has the corresponding reviewed
repo/wheel pair before resuming sweeps. For rollback, stop affected sessions
again, restore a compatible retained wheel and the reviewed executable and
instruction edits together. **Never roll back telemetry state, task lifecycle
state or audit history.** No external repository rollout is authorized by the
implementation of this procedure.
