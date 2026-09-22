---
name: coga/internals/claim-recovery
description: How each retained megalaunch claim form is recovered — pending, admitted, and `released:` launch generations — including the ordinary-launch reconciliation of a released witness and the retained evidence megalaunch leaves on refusal or uncertainty.
---

# Launch-claim recovery

Megalaunch ([launch claims](../launch-claims/SKILL.md)) never reclaims its
own claims and never compensates a refused one backward to `active`. What it
leaves on disk is the human-legible reconciliation evidence. Recovery is an
explicit human act through ordinary `coga launch <slug>`
([launch](../../launch/SKILL.md)).

## Claim forms left behind

| Local `launch_generation` | How it arises | What `coga launch` does |
| --- | --- | --- |
| `pending:<uuid>` | an uncertain start publication (no child yet), or a pre-release proof that changed or could not be verified (held child killed) | refuses: "admission is still pending" |
| `released:<uuid>` | the child was released but the admission publish failed or its outcome is unknown; the child was then killed | reconciles, then starts a recovery session |
| plain `<uuid>` | a successfully admitted session that crashed or was torn down | resumes it like any `in_progress` ticket |

Megalaunch itself refuses all three, naming `coga launch <slug>` as the
recovery path for the released and plain forms. The unattended sweep never publishes a released witness.
Step advances and lifecycle transitions that end or park the session remove
the field (`mark` and `bump` pop it), so a finished session leaves nothing.

Other retained evidence: an uncertain activation or start publication keeps
the generated local write; an uncertain dependency-drain activation keeps its
combined activation and blocker answer; a refused or definitely failed one is
restored to its prior bytes with its audit lines retracted.

## Released-witness reconciliation

`_reconcile_released_launch_admission` in `src/coga/commands/launch.py` runs
before any other launch work when the local ticket carries `released:`. The
whole sequence holds `git.state_lock`:

1. Read the local bytes and require them to equal the released bytes read
   just before; require a `released:` generation, Git sync enabled, a Git
   checkout, a configured remote, and the control branch present.
2. Build the matching pending and admitted renderings of the same ticket.
3. `fetch_control` and require control's whole ticket to be one of those two
   exactly. Pending means publication definitely failed; admitted means an
   ambiguous push actually landed. Anything else refuses.
4. Reread the local file. A manual edit made during the network wait refuses
   recovery and is preserved; the lock serializes Coga writers, not ordinary
   editors.
5. Write the admitted rendering and publish it with `expect` pinned to the
   control copy just read.
6. On any failure, write the `released:` witness back so a retry is still
   recognizable.

A failure exits 75 (`git.RETRY_WITHOUT_SWEEP_EXIT_CODE`) with "the
recoverable local witness was retained", and nothing spawns. On success
launch prints "Reconciled released megalaunch admission" and proceeds with
the admitted ticket, which is `in_progress`, so it resumes without another
status flip.

## Pending claims

No command turns `pending:` into another form except megalaunch's own
admission callback while it holds the child it just released. The sources
call a retained pending claim evidence for "explicit reconciliation" but
ship no command for it: a human inspects control and the local copy. While
control carries `pending:`, every task publisher refuses any replacement
other than the identical prefix-stripped ticket, so no ordinary lifecycle
command can overwrite it by accident.
