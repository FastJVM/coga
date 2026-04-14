# Relay — Work Plan

A running plan for how we'll put Relay into real use at FastJVM. Living
document — update it as we learn. Order of steps reflects current
priority; reorder when reality disagrees.

---

## Step 1 — Use Relay for our Next Real Task

Before migrating automations, adding teammates, or building new features,
we need at least one real task to flow through Relay end-to-end. The
whole bet is that context blocks compound over time — and we can't test
that bet by moving existing scripts around. We test it by doing new
work inside the system.

### What this looks like in practice

Pick the next real thing coming up — a coding change, a customer
investigation, a content post, a process question — and run it through
Relay instead of opening Claude Code (or Cursor, or a blank Slack
thread) directly.

The motion for the first task:

1. **Create the ticket.**
   ```bash
   relay create --project demo --title "..." --workflow <workflow> --assignee claude1
   ```
   If no existing workflow fits, create the task without one and manage
   it by status transitions alone.

2. **Build the context block that supports it.**
   This is the step we'd normally skip. Don't skip it.

   Before launching the agent, ask: what does the agent need to know
   about this domain that isn't derivable from the code? Examples:
   - For a deliverability task: "SPF must be set up before DKIM, DKIM
     before DMARC. Never jump straight to DMARC reject."
   - For a Stripe task: the conventions already in
     `contexts/email/payment-flow/SKILL.md`.
   - For a customer-support task: the tiers, what each tier gets, when
     to escalate.

   Write that knowledge as a new context block under
   `contexts/<path>/SKILL.md`, or attach an existing one if it already
   covers the domain. Frontmatter:
   ```markdown
   ---
   name: <path>
   description: One-line — when to attach this.
   ---
   ```

3. **Attach the context to the ticket.**
   Either re-create the task with `--context <path>` or edit the
   ticket's `contexts:` frontmatter list directly.

4. **Activate and launch.**
   Flip `status: ready` → `status: active`, then:
   ```bash
   relay launch --task <id> --dry-run   # inspect the composed prompt first
   relay launch --task <id>             # real launch when the prompt looks right
   ```

5. **Let the agent work. Watch the blackboard.**
   The agent writes findings and decisions as it goes. If something
   feels off, edit the context block — the next launch picks up the
   change.

6. **When the task is done, review.**
   Ask: did the agent know what it needed? If not, what's missing
   from the context? Edit the context block so the next task gets it
   right without us having to re-explain.

### What "success" looks like for Step 1

- One ticket created, one context block written (or at least one
  existing context attached with intent), one task walked to `done`.
- Honest note in the task's blackboard under Decisions: what went
  well, what was missing, what we'd change next time.
- **The goal is not productivity. The goal is one real data point
  about whether the workflow holds up for our actual work.**

### When to move to Step 2

After at least 2-3 real tasks have flowed through Relay — enough cycles
that we can say "yes, the context blocks are earning their keep" or
"no, and here's why." If it's the latter, Step 2 shouldn't be "migrate
automations," it should be "figure out what's wrong with the bet."

---

## Step 2 — (TBD, after Step 1 produces data)

Placeholder. Likely candidates once Step 1 has generated real usage:

- Onboard Pierre as the second user.
- Fix rough edges surfaced by Step 1 (quality-of-life CLI commands like
  `relay activate`, `relay delete`; clearer error messages).
- Migrate the first automation (Xero, since it's already stubbed).
- Write `GETTING_STARTED.md` for teammates.

We'll pick from this list based on what Step 1 teaches us.

---

## Notes on sequencing

- **Migration is not the first step.** The four existing automations
  (RD tax, Brex, Xero, SF forms) continue to run under their current
  launchd jobs. We don't move them until we've validated that the rest
  of Relay is worth committing to.
- **Don't build features speculatively.** No dashboard, no Slack bot,
  no `relay sync`, no custom UI — until friction from real use forces
  it. The spec is deliberately minimal.
- **Context blocks are the asset.** If we end Phase 1 with a repo full
  of well-curated context blocks that new tasks attach to naturally,
  Relay is working. If we end with an empty `contexts/` folder, it's
  not — and adding more CLI commands won't fix that.
