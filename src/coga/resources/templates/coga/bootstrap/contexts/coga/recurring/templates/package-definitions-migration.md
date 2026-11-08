# Migrating an existing repo to package-owned definitions

Operator procedure owned by [coga/recurring/templates](SKILL.md#selection-and-state)
and linked from [init](../../init/SKILL.md). Existing repos keep working after an
upgrade: local definitions retain their activation and package-only jobs remain
disabled without selection. Migration is optional and manual. Every edit is
reviewed and reversible; use a migration branch or current control.

## 1. Prepare

1. Upgrade **every** participating checkout and machine to a Coga that
   understands carriers and `jobs.toml` (this release or newer). Older clients
   cannot read a carrier. Keep compatible clients after migration or rollback.
2. Quiesce recurring sweeps, launches and state writers in all checkouts.
   Inspect processes; ticket status is not process evidence. Wait for running
   scripts to exit, and check for pending log-retention receipts before editing.
3. Reconcile with fresh control. Read state from that copy, never the package
   seed. Record the control revision and the clients in use.
4. Back up every local definition being considered, with supporting files.
   Save `coga/recurring/` completely: full blackboards, attachments, parked
   `_name/` directories, `retires.md`, and the prior `jobs.toml` or its absence.
   Also save frozen `coga/tasks/recurring/` periods, `coga/log.md`, and each
   clone's `coga/.coga/recurring-clone/` ledgers/logs. Keep verified backups
   outside published roots. For example, with `backup_dir` set to durable
   backup storage:

   ```sh
   git rev-parse HEAD > "$backup_dir/control.rev"
   tar -C coga -cf "$backup_dir/recurring.tar" recurring tasks/recurring log.md
   ```

   Include ignored state and attachments, not just tracked files. Compare
   copied bytes and record hashes before deleting anything.

## 2. Inventory and classify

Inventory active, parked, disabled and deleted jobs. For every local directory:

- **Repo-only job**, such as `usage-report` or `upstream-coga`: keep it and all
  attachments unchanged. It needs no selection entry.
- **Stock copy of a bundled job**: compare each definition file separately
  against a *known prior seed* from the wheel/version that supplied it.
  Compare `ticket.md` only above its fence, and siblings in full. Matching a
  filename or differing from the current package proves nothing about origin.
- **Customized or ambiguous override**: retain the full local definition and
  attachments, record the reason, and let its owner decide. Never silently
  delete unknown work or mix a local body with a packaged script.

The entire blackboard is state, including notes/worklists without `state_keys`
and phone-home's complete `period_state`. It is excluded from definition
comparison. Check unfinished and paused periods for frozen instructions that
require attachments you would remove. Drain those periods or defer the job;
never rewrite a frozen workflow or discard a period to finish migration.
Retained custom attachments need a documented full local override.

## 3. Publish selection first

Write `coga/recurring/jobs.toml` with `true` for stock jobs currently active,
`false` for explicitly disabled jobs. Keep parked jobs parked, and add no entry
for deleted jobs. An absent `trim-log` stays unselected. With equivalent local
definitions still present, this does not change activation:

```sh
coga recurring list
coga run publish-state coga/recurring/jobs.toml
```

Require a successful receipt and verify selection on control before removing
any dependent definition.

## 4. Convert reviewed parents

For each approved stock parent, preserve its whole current blackboard
byte-for-byte in a carrier and remove its reviewed definition siblings in one
guarded change. Keep runtime state such as `retires.md`. Reconcile freshly and
compare the planned preimages with the verified backup before this example:

```sh
name=phone-home   # example: both named siblings have been reviewed as stock
python - "$name" ticket.py operations.md <<'PY'
import sys
from coga.config import load_config
from coga.git import state_lock
from coga.log_transaction import ensure_clear
from coga.paths import recurring_dir
from coga.recurring_state import CARRIER, CARRIER_PREFIX, inspect_parent_dir
cfg = load_config()
parent = recurring_dir(cfg) / sys.argv[1]
ticket = parent / "ticket.md"
with state_lock(cfg):
    ensure_clear(cfg)
    original = ticket.read_bytes()
    fence = b"<!-- coga:blackboard -->"
    assert original.count(fence) == 1
    saved = original.split(fence, 1)[1]
    siblings = [parent / name for name in sys.argv[2:]]
    assert all(path.parent == parent and path.is_file() for path in siblings)
    ticket.write_bytes(CARRIER_PREFIX.encode("utf-8") + saved)
    for path in siblings:
        path.unlink()
    assert inspect_parent_dir(parent).kind == CARRIER
    assert ticket.read_bytes().split(fence, 1)[1] == saved
PY
coga run publish-state   # no path operands: include reviewed deletions
coga recurring list
coga validate --json
```

Use the upgraded CLI's interpreter. Never publish a carrier beside orphaned
definition siblings. A parent with no useful state may have no local ticket
until first use. Named publication operands must exist: verify removed paths
separately in the resulting control tree. Do not exclude paths or bypass
publication guards. On conflict preserve both sides and reconcile newer state
before retrying. Frozen periods, copied scripts, worklists, shared log and
clone ledgers stay intact.

## 5. Other reusable definitions

Apply the same provenance review to local contexts, skills, workflows,
bootstrap tickets and prompt overrides. Remove only verified stock copies and
their reviewed siblings. Resolve logical refs from the package; keep ambiguous
or customized directories as complete local overrides until their owner decides.
Retain repo-only topics and skills, real configuration/context, physical ignore
and attribute scaffolds, and ignored authoring starters. Starter materializations
must remain untracked. Repair live navigation to the owning package file;
never add forwarding files or symlinks. Frozen period history stays intact.

## 6. Verify

The effective catalog shows converted jobs as bundled and overrides as local,
with unchanged selection/parking. Validate recurring definitions and compare
saved blackboards, worklists, frozen periods and clone ledgers. Freshen all
participating checkouts before resuming writers so stale local definitions
cannot be republished.

In Coga's source repo, run control's own packaging, navigation and representative
runtime checks after selection, after the first conversion/deletion, and after
full removal. Use that tree's imports, not the feature checkout's editable
installation. Only then enable strict ownership tests in the code PR. No
intermediate control commit may require unmerged runtime support.

## Rollback

Keep writers quiesced. Restore each converted definition and reviewed sibling
from verified backups, placing the carrier's **current** blackboard below the
restored ticket's fence. State may have advanced: never overwrite it with backup
state. Restore previous selection (or its absence) through the ordinary guarded
publication path. Retain current worklists, frozen periods, audit history and
all clone ledgers. Never replay or recreate periods; the ledger already records
what ran. Compare restored definitions against the backup, blackboards against
their pre-rollback bytes, and the effective catalog before resuming writers.
Rehearse this while writers remain paused; rollback still requires compatible
clients and never restores trimmed history or old cursors.
