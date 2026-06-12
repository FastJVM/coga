The blackboard is a notepad to be written to often as the human and agent works through a task.

## Brief delivered at step 1 (brief-and-hand-off), 2026-06-11

**Goal.** A Google Sheet named "Relay CRM" giving visibility into external
adoption: who said they'd use relay, who actually used it, who's still
using it. Zach builds it by hand; all updates after creation are manual
(no telemetry — "still using" is conversational evidence).

**Ordered steps for Zach (human-executes):**

1. Create a new Google Sheet named **Relay CRM** anywhere in Drive
   (location is your choice; no required folder).
2. Rename the first tab **Tracker** and add the header row:
   `Name | Email | Source | Status | Committed | First used | Last confirmed use | Notes`.
3. Put a dropdown (data validation) on the **Status** column with exactly
   four options: `Committed / Tried / Active / Churned`.
4. Add a second tab named **Touchpoints** with the header row:
   `Date | Person | Channel | What we learned`.
5. Fill Tracker rows from your existing list of people. (Agent does not
   seed data.)
6. Run `relay bump relay-crm` to hand back for verification.

**Irreversible action:** none. The only live action is creating one new
Sheet, recoverable via Drive trash. Nothing is shared, deleted, or
overwritten.

**Done check (verify-read-only, step 3):** agent reads the sheet via the
Drive MCP. Per the `docs/gdrive-mcp` contract this can confirm only Tab 1
("Tracker") columns — reads return the first tab only, and dropdowns
never show in exports. Tab 2 and the Status dropdown rest on Zach's
report, which the workflow accepts ("if the result can't be observed,
the human's report stands").

**Decisions/notes:**
- Feasibility was settled at triage; not re-assessed here. No live action
  taken this step.
- Usage semantics on Tracker: blank "First used" = committed but never
  followed through; recent "Last confirmed use" = still using. "Last
  confirmed use" is a manual rollup of the latest relevant Touchpoints row.
