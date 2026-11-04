# Migrating an existing repo to package-owned recurring definitions

Operator procedure owned by
[coga/recurring/templates](SKILL.md#selection-and-state). It is optional:
an existing repo keeps working unchanged after upgrading Coga, because local
definitions keep their activation and nothing bundled is enabled without a
`recurring/jobs.toml` entry. Migrate when you want bundled jobs to follow
package upgrades instead of stale local copies. There is no automatic tool;
every step is a reviewed, reversible edit. Run it on a reviewed migration
branch or from a control checkout, one job at a time if you prefer.

## 1. Prepare

1. Upgrade **every** participating checkout and machine to a Coga that
   understands carriers and `jobs.toml` (this release or newer). Older
   clients cannot read a carrier; do not migrate while any remain.
2. Quiesce recurring sweeps, launches and state writers in all checkouts
   (inspect processes; a ticket status is not process evidence). Wait for
   running scripts to exit.
3. Start from a freshly reconciled control branch. Read state from that
   control copy, never from the package's seed.
4. Back up `coga/recurring/` completely (definitions, blackboards, every
   attachment, parked `_name/` directories, `retires.md`) and record the
   current revision:

   ```sh
   git rev-parse HEAD > /tmp/coga-recurring-backup.rev
   tar -C coga -cf /tmp/coga-recurring-backup.tar recurring
   ```

## 2. Inventory and classify

For every directory under `coga/recurring/`, active and parked:

- **Repo-only job** (no bundled job of that name, e.g. `usage-report`): keep
  it exactly as is. It needs no selection entry.
- **Stock copy of a bundled job**: each definition file (`ticket.md` above
  its fence, `ticket.py`, runbooks) is byte-identical to a *known prior
  seed* of the same job, taken from the wheel the repo was initialized or
  last upgraded with. Compare against that old artifact, not just the
  current package: a file that matches neither is not stock.
- **Customized override**: anything else. Keep it as a local definition. It
  stays in force and owns its state; record why in the review.

The blackboard (below the fence) is state for every job, including ones with
no `state_keys`; it is never part of this comparison. Note jobs whose
unfinished or paused period's frozen instructions name a supporting file you
would delete; drain those periods first or defer that job.

## 3. Publish selection first

Write `coga/recurring/jobs.toml` so activation is unchanged: `true` for each
stock job that is currently active, `false` for any you want off. Leave
parked jobs parked (`_name/` keeps parking regardless of selection), and add
no entry for jobs you deleted. Publish it on its own; with equivalent local
definitions still present it changes nothing:

```sh
coga recurring list   # every job still shows its local definition
```

## 4. Convert one stock job at a time

For each stock job, in one guarded state change, replace its definition with
a state-only carrier preserving the whole saved blackboard byte-for-byte, and
remove only the reviewed definition siblings. Keep `retires.md` and other
runtime state:

```sh
name=dream   # the job being converted
python - "$name" <<'PY'
import sys
from pathlib import Path
from coga.recurring_state import render_carrier
from coga.taskfile import read_blackboard
ticket = Path("coga/recurring") / sys.argv[1] / "ticket.md"
ticket.write_text(render_carrier(read_blackboard(ticket)), encoding="utf-8", newline="\n")
PY
git rm coga/recurring/$name/ticket.py coga/recurring/$name/operations.md  # only reviewed stock siblings
coga recurring list   # the job now shows (bundled)
coga validate --json
```

Run this with the upgraded CLI's interpreter. Never leave a carrier beside
orphaned definition siblings at a publication: that is an incomplete fork
and the job errors until repaired. A job with no useful state may instead
have no local ticket at all; its first run creates the carrier from the
package seed. Publish through the ordinary state path and inspect its
receipt; do not exclude paths or bypass guards. Frozen periods, their copied
scripts, worklists, clone ledgers and the shared log are untouched.

## 5. Verify

`coga recurring list` shows each converted job as bundled and each override
as local; `coga validate --json` reports no recurring errors; the next sweep
creates periods from the package and keeps every saved cursor (for
phone-home, the complete `period_state`).

## Rollback

Keep writers quiesced. For each converted job, restore its definition files
from the backup and put the carrier's *current* blackboard back below the
restored ticket's fence (state may have advanced since the backup; do not
restore the old blackboard over it). Restore the previous `jobs.toml` (or
remove it to return to local-only activation). Never replay or recreate a
period to complete a rollback; the serviced-period ledger in `coga/log.md`
already records what ran.
