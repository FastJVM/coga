# Adopting and recovering audit retention

Default-on retention is a behavior change: fresh init installs Monday 04:00
maintenance and uses 30 local calendar days. Existing repos acquire the weekly
schedule only through the explicit adoption below. A wheel upgrade alone does
not install a schedule. The [ticket](ticket.md) owns retention and preservation
exceptions; `[log].retention_days = 0` in shared config opts out. Never replace
an existing value during adoption. Full on-disk ticket histories, recurring
state, unread movement and uncertain data can outlive the window. Historical
usage reports query retained records, with no completeness guarantee before
the window and no automatic Git-history read.

## Adoption after the compatible wheel upgrade

Quiesce affected sessions first. Upgrade every participating interpreter and
checkout to the compatible wheel before enabling the repo files. An older
writer neither locks the log nor understands guarded deletion. Use the exact
`COGA_PY` interpreter-resolution command in
[coga/edge-code upgrades](https://github.com/FastJVM/coga/blob/main/docs/contexts/coga/edge-code/edge-code-upgrades.md)
(the `migration:interpreter` block); it preserves the installed environment's
shebang interpreter rather than substituting ambient Python. From the repo:

```sh
"$COGA_PY" -m coga_edge.trim_log --install
```

This bounded installer validates the complete plan before writing. Its only
possible edits, relative to the Coga root, are:

- `recurring/trim-log/ticket.md`, `ticket.py`, and `operations.md`;
- `workflows/trim-log/run.md`;
- `.gitattributes`: replace the known stock `**/log.md merge=union` with
  `/log.md -merge`, preserving the `retires.md` union rule and unrelated bytes.

It verifies the effective attribute, including overriding attributes. Identical
files are no-ops. Custom or symlinked files, `_trim-log` parking and unfamiliar
attributes require review; no partial feature replacement occurs on those
refusals. It never rewrites config, other jobs, periods or full local forks,
launches work, or sends telemetry. Review/publish the named edits using normal
repo practice. Adapt any phone-home full fork to the shared schema-2 cursor
before enabling; preserve its identity, run counter and blackboard. Unknown
origins are review items, never permission to overwrite.

Coga's own code PR stages these live files under `rollout/trim-log/coga/`,
outside swept roots. The package receives the matching files immediately.
After the core PR merges, the operator upgrades all writers, runs the command
above on current control, reviews the exact diff and publishes it. Until that
handoff, the live `.gitattributes` intentionally retains the old rule; the twin
exception is removed once adoption makes the copies identical. The staged
files and package are byte-identical and tested. Do not activate a live shim
before its implementation reaches control. Rollback likewise requires a
compatible wheel/repo pair; do not restore old cursor state or trimmed history.

## Interrupted maintenance

The Git directory's `coga-log-mutation.json` and
`refs/worktree/coga/log-mutation` are a temporary transaction receipt. They pin
its preimage, intended output and attempted commits. They are not a second
archive and contain no distributed tombstones. All Coga publication and
checkout return refuse while this receipt remains. A period-script exit 75
bypasses settlement; later unrelated commands cannot publish the truncation.
Do not delete the receipt, manually restore the short log, or rerun a lifecycle
transition to make it disappear.

After restoring Git access, rerun the same reserved script with its recorded
period environment and the compatible interpreter, from the control checkout:

```sh
COGA_TASK_SLUG=recurring/trim-log \
COGA_TASK_BLACKBOARD=tasks/recurring/trim-log/ticket.md \
COGA_SCRIPT_TASK=tasks/recurring/trim-log \
"$COGA_PY" -m coga_edge.trim_log
```

Run from the Coga root. This is recovery of the existing period, not a new
launch or a separate command mode. Fresh control history proves whether an
attempted commit landed. Accepted-but-unacknowledged output catches up to
control while preserving later local appends. Definitely unpublished output
restores only this attempt's unchanged outputs, log first then cursor, and
replans. A cursor migrated before a crash remains valid on an untrimmed log.
Changed local outputs or unavailable evidence remain retained and fail visibly;
reconcile those exact paths with the receipt before retrying. Corrupt input
records a `coga block` prerequisite; fix the stated input and answer it through
`coga unblock recurring/trim-log --answer "..."`. Never edit lifecycle fields.

## Native Git conflicts

The stock `/log.md -merge` deliberately makes competing native Git log edits
conflict. Coga appends use the event-aware publisher; native Git has no custom
merge driver or hook. On a conflict retain both index stages (`git show
:2:coga/log.md`, `git show :3:coga/log.md`) and the merge base before resolving.
Preserve peer additions, required retained evidence and opaque data, while
honoring proved historical deletions; do not select an entire side blindly or
restore union merging. Abort and publish the append from its source checkout
with the compatible Coga publisher, then redo the native merge, when that
avoids manual reconciliation. Git history retains the removed events.
