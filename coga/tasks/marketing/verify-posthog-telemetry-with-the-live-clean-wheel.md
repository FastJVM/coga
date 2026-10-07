---
title: Verify PostHog telemetry with the live clean-wheel proof
status: in_progress
owner: nicktoper
contexts:
- coga/telemetry/operations
workflow:
  name: brief-for-human
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: owner
  - name: verify-read-only
    skills: []
    assignee: agent
step: 2 (human-executes)
agent: claude
---

## Description

Run the owner-only live clean-wheel proof for the weekly PostHog snapshot that
merged in PR #880 without it. On 2026-09-22 the owner deferred this proof
("assume it works; owner will test later"), so no real `coga_weekly_snapshot`
row has been queried yet. The V1 plan (`marketing/plan`) makes this
verification a launch gate that marketing simplification does not waive, and
`marketing/build-the-launch-plan` needs its evidence before Show HN.

Build the wheel from `main` at a recorded commit (PR #880 is merged, so there
is no separate review checkout). Record the evidence on this ticket's blackboard,
as the procedure directs. Done means the blackboard records all of the following:

- The commit, the wheel version and the wheel hash (`sha256sum`).
- The UTC run windows, the prepared payload values from the Slack receipt, the
  period report and the exact qualifying audit lines.
- The exact query text and results for three observations:
  1. The first sweep produces one row with the minted repo UUID and zero
     movement, and it matches the receipt's prepared envelope.
  2. After a known forward advance or completion, a later run produces another
     row with the same UUID and the expected movement count.
  3. After setting `[telemetry] enabled = false`, a run produces zero rows in
     the post-disable window, paired with the automated no-worker/no-HTTP checks.
- The property keys are checked: no IP, GeoIP or other unexpected enrichment.
  Unexpected fields block acceptance until they are explained.

At `human-executes`, the owner runs the proof, pastes the results and updates
the PostHog readiness line on `marketing/build-the-launch-plan`'s blackboard.
The owner may ask the attended agent to write it. At `verify-read-only`, the
agent checks the pasted evidence against the procedure. It runs no
`posthog-cli`, capture or deletion commands itself.

## Context

The procedure is the attached `coga/telemetry/operations` topic, section
"Clean installed-wheel proof". Follow it exactly, including
its project-check and credential rules. Its disable, deletion and rotation
sections are not part of this task. Two topics are cited rather than attached:

- The parent `coga/telemetry` (`docs/contexts/coga/telemetry/SKILL.md`). Read
  "Admission and configuration" for why the proof must run outside every Coga
  source tree with no pytest or CI environment.
- `coga/notifications` (`docs/contexts/coga/notifications/SKILL.md`) for
  enabling Slack in the scratch repo before the first sweep. Fresh init has no
  notification channels.

Other notes:

- The implementing ticket is `marketing/add-telemetry` (done). See its blackboard
  "Owner review decision — 2026-09-22" for the deferral.
- Out of scope: changing telemetry code, rotating the key, and editing the
  Multiply repo. If the proof fails, record the failure and open a fix ticket
  instead of patching here.

<!-- coga:blackboard -->

## Verify PostHog telemetry with the live clean-wheel proof

### Brief (step 1, 2026-10-07, agent; no live action taken)

**Goal.** Prove that a real installed wheel delivers `coga_weekly_snapshot` to
PostHog project 606347 with the right UUID, movement and properties, and that
`[telemetry] enabled = false` stops delivery. This is a launch gate for
`marketing/build-the-launch-plan`. The procedure is `coga/telemetry/operations`
§ "Clean installed-wheel proof". Run it from an ordinary shell with no
`PYTEST_CURRENT_TEST` or `CI` set. Stay outside every Coga source tree and do
not use an editable install.

**Steps (owner, in order):**
1. Record `git rev-parse HEAD` on an up-to-date `main` (it was `992ac36fc` at
   brief time). Build the wheel into a fresh `/tmp/coga-telemetry-wheel`.
   Exactly one wheel should be there. Record `sha256sum` and the installed
   version (`importlib.metadata.version("coga")`).
2. Create a fresh venv at `/tmp/coga-telemetry-release` and install the wheel.
   Run `git init -b main` in a fresh `/tmp/coga-telemetry-proof`, then
   `coga init . --user nicktoper` and `cd coga`.
3. **Before the first sweep**, enable Slack in the scratch repo's `coga.toml`
   (`coga/notifications`): `channels = ["slack"]` and
   `[notification.slack] webhook = "env:SLACK_WEBHOOK_URL"`. Use `env:` refs
   only and export the variable in the shell.
4. Note the UTC start time and run `coga recurring launch phone-home`. Save the
   Slack receipt, which holds the prepared keyless envelope. A failed receipt
   is not proof. Read `repo_id` from `recurring/phone-home/ticket.md`
   blackboard and note the period report.
5. Run `posthog-cli api call --json project-get '{}'` and **stop unless the ID
   is 606347**. Then run the `execute-sql` query from the topic with the UUID.
   **Obs 1:** expect one row with that UUID, movement 0, and values matching
   the receipt.
6. Make a known forward advance or completion on a non-recurring work ticket
   in the scratch repo with the normal CLI. Copy the exact audit lines from
   `coga/log.md`. Run `python recurring/phone-home/ticket.py` from `coga/`
   with the venv python. Re-check `project-get`, then re-query. **Obs 2:** expect
   a second row with the same UUID and the expected movement count.
7. Set `[telemetry] enabled = false` in the scratch `coga.local.toml`. Note the
   UTC time and run the recipe again. Re-check `project-get`, then run the
   `count()` query with `timestamp >=` that time. **Obs 3:** expect 0. Pair it
   with the automated no-worker/no-HTTP tests, e.g. `tests/test_telemetry.py::test_disabled_has_no_identity_worker_or_receipt_and_reenable_counts_gap`.
8. For each row, check `property_keys` against the context allowlist. There
   should be no `$ip`, `$geoip_*` or other unexpected enrichment. List
   service-owned routing metadata separately. Any unexplained field blocks
   acceptance.
9. Paste all of this below, either yourself or by asking the attended agent:
   commit, version, hash, UTC windows, receipt payloads, period report, audit
   lines, and the exact query text and results ×3. Update the PostHog readiness
   line on `marketing/build-the-launch-plan`'s blackboard.

**Credential rules.** Do not read or copy `~/.posthog/credentials.json`. Do
not echo the capture key or pass it as an argument. The scratch repo must not
commit a literal webhook.

**Irreversible / outward-facing.** Step 4 onward sends real events into the
shared Multiply/Coga PostHog project. They cannot be un-sent, and removing them
needs the irreversible `persons-bulk-delete`, which is out of scope here.
Every `posthog-cli` call must follow a `project-get` that confirms 606347. The
Slack receipt posts to a real channel.

**Done check (verify-read-only step).** The agent checks the pasted evidence
against the list above and the ticket's "Done means" criteria. It runs no
`posthog-cli`, capture or deletion command. If the proof fails, record the
failure here and open a fix ticket. Do not patch telemetry in this task.

### Evidence (owner to paste)

_Pending._
