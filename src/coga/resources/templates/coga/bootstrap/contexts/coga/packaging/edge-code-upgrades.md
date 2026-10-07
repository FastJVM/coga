# Adopting wheel-owned edge code

This is the operator procedure owned by [coga/packaging](SKILL.md), not an
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

### Instruction reconciliation for the later recipe-removal release

`gigantic-refactor-move-recurring-recipes-out-of-co` must use this same adoption
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
do not ship recipe removal as an unattended wheel-only upgrade. This release
only tests representative instruction reconciliation in fixtures: it removes
no recipes, edits no shipped Dream passages, and implements no Dream workers.

5. Review `git diff --check` and the precise file diff; merge through normal
   repo practice. In a scratch copy, verify with CI/pytest suppression and fake
   transport, never production phone-home merely to inspect code. The automated
   receipts are `tests/test_edge_distribution.py`: commands above are executed
   against stock/edited/parked legacy copies and representative Dream passages,
   with state and unrelated text checked byte-for-byte.

Ensure every executing checkout and interpreter has the corresponding reviewed
repo/wheel pair before resuming sweeps. For rollback, stop affected sessions
again, restore a compatible retained wheel and the reviewed executable and
instruction edits together. **Never roll back telemetry state, task lifecycle
state or audit history.** No external repository rollout is authorized by the
implementation of this procedure.
