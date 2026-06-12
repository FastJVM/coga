The blackboard is a notepad to be written to often as the human and agent works through a task.

## Pre-implementation dry run (2026-06-11)

Zach + Claude are dry-running the two-phase design before implementation,
to validate the four interview questions and the artifact-generation step.
Feature is NOT yet built (no interview logic in `src/relay/commands/init.py`).

Test structure (round-trip eval):

- **Leg A (scan + answers):** `~/Desktop/admin-init-test` — admin's
  relay-os knowledge flattened by a subagent into 5 organic founder-notes
  files (README, docs/company-finances-overview.md, docs/monthly-close.md,
  docs/taxes.md, docs/insurance.md), all relay vocabulary/structure
  stripped, committed as baseline. A fresh agent scans this + Zach's
  interview answers and generates contexts/rules/workflows/recurring.
  Output is scored against admin's REAL relay-os (the answer key).
- **Leg B (answers only):** `~/Desktop/admin-fresh` — empty git repo,
  same interview answers, no scan. Delta vs Leg A isolates the scan's
  contribution.
- **Known bias:** flattened files descend from the answer key, so Leg A
  recall reads optimistic vs organic notes. Unbiased follow-up candidate:
  `barrel-to-busbar` (405 substantive files outside relay-os).
- **Early finding:** ops repos can be nearly empty outside relay-os
  (admin = 3 files once relay-os/AGENTS.md/CLAUDE.md are stripped). The
  setup-ticket scan step must degrade gracefully to answers-only even for
  non-empty repos.

### Scoring key — 20 ground-truth facts embedded in the Leg A fixture

(From the flattening agent; each fact traces to a real admin relay-os
artifact. Grade generated artifacts on recall of these + precision/no
invented junk.)

1. Cash-based, asset-free by policy, accounting deliberately simple (owner-manual)
2. Books reset after bookkeeper's inconsistent asset/charge mapping; losses slightly understated (accounting/transition)
3. Systems of record: Xero, Gusto, Brex (every employee carded), Stripe (legacy invoices), Chase, Clerky (owner-manual)
4. Five bank feeds into Xero; Stripe revenue → Chase → auto-maps to 4000 Sales (owner-manual + tax-process-guide)
5. Monthly close: Brex "Missing GL Account" filter → custom rule or suspense (brex-missing-gl)
6. Personal reimbursements never to 4000 Sales / 4715 Other Income — Payroll-6001 (tax-process-guide)
7. Monthly receipt sweep: Brex charges > $40 missing receipts, month just closed, exclude refunds/declined (check-receipts-in-brex)
8. Brex API: legacy host 401s; api.brex.com/v3/accounting/records; empty receipts array = missing; posted_at bucketing (check-receipts blackboard)
9. Xero reconcile monthly; count never hits 0; done = human's say-so (xero-reconcile-reminder)
10. Payroll alternate Wednesdays; Gusto bill → Xero AP ~2 days pre-payday; GUSTO - NET + GUSTO - TAX; no bank rule; 9-step manual match; Remove & Redo gotcha (biweekly-payroll-bill-reconciliation)
11. January tax download: 941 ×4, 940 (Line 12), DE-9 ×4 = nine PDFs (gusto-tax-forms-download)
12. Drive tax folder named by FILING year; accountant pulls from it; Q4 retry later in January (gusto-tax-forms-download)
13. Playwright scraper abandoned — Gusto API doesn't expose tax-form PDFs (gusto-tax-forms-download)
14. Annual master checklist: 9 forms, Xero statements, RxDC (Kaiser), R&D credit, 401k credit, CA SOI, DE Franchise $850 (annual-tax-checklist)
15. R&D credit §41: per-employee table, hourly = salary/2080, projects from daily_updates Slack, four qualification questions (tax-process-guide)
16. 401k credit: Gusto prefills Form 8881 but doesn't file — send to CPA (tax-process-guide)
17. Patents: Jan 1 reminders from Patent Maintenance spreadsheet; fees.uspto.gov; GL 6300 (tax-process-guide)
18. May insurance: Vouch/Corix BOP+EPLI, July 14 start, ~$3,206, State National, policy #s (insurance-payment-reminder)
19. Hartford workers comp via AP Intego; renewal ~1.5mo ahead, 2-week change window ~end of May (insurance-payment-reminder)
20. NEXT ~$13–15/mo ACH from Brex; retired carriers not to re-add; declined coverages to revisit; Kaiser via Gusto, don't double-count (insurance-payment-reminder)

### Zach's interview answers (2026-06-11, verbatim — reuse for the real test)

1. *Repo purpose / success:* "This repo is for organizing and building our
   admin processes. Keeping track of bills, insurance payments, account
   transactions, expense reports. Success is measured by our ability to not
   miss any payment or filing-related task."
2. *Outsider-invisible knowledge:* "We are a small company who's currently
   focused on research. We have an owner's manual and an accounting and tax
   process document that explains the systems we use and our financial
   processes. Also, we had a prior bookkeeper who made a lot of mistakes on
   our books. Those mistakes work against us and not the government, so
   we're choosing to start from a clean slate and do things correctly now."
3. *Always-rules:* "never touch real financial data without asking. We use
   api's for a few of our services (namely brex) and use it to make sure we
   aren't missing receipts. Any financial related outcome/ tax credit/
   transaction reconciliation, should always have a human in the loop to
   review."
4. *Recurring work:* "Handling Xero-reconciliations come up repeatedly and
   we'd like them to be flagged for us monthly. Missing receipts/ memos for
   our expenses are a recurring issue for us and we would also like these
   flagged monthly for us. We have a few year end processes that are
   recurring. Every year we will need to gather tax documents from Gusto
   such as form 940's and 941's. This gathering should happen on the 1st of
   every year. We have a payroll issue that surfaces in xero bi-weekly where
   we need to unreconcile it, and reconcile it against the actual bill."

### Results (2026-06-11, scored by independent grader agent)

**Recall against the 20-fact key:**
- Leg A (scan + answers): **20 captured / 0 partial / 0 missing**
- Leg B (answers only): **0 captured / 7 partial / 13 missing**

Leg B's 7 partials track the interview answers almost exactly; everything
Zach didn't say out loud was simply gone. (Bias caveat applies: Leg A's
20/20 is optimistic since the fixture descends from the answer key.)

**Precision: zero invented facts in either leg.** Both agents stubbed and
asked instead of fabricating — Leg B's `company/source-documents` context
explicitly forbids guessing at the owner's-manual contents.

**Structure:** both legs placed facts well (contexts = facts, workflows =
process, skill for the 9-step Gusto procedure). Minor drift risks noted:
Leg A duplicated insurance specifics between context and ticket; patent
details live only in a ticket body.

**Findings for the spec (what the dry run validates/changes):**

1. **The interview alone captures intent, not operation.** Four answers ≈
   7/20 facts at partial fidelity. The scan step is not an enhancement —
   it's where most durable knowledge comes from. Empty-repo path is
   workable but produces a *starter* relay-os, not a complete one.
2. **The open-questions list should be a first-class output.** Both
   agents independently produced one (Leg B: 10 questions mapping exactly
   what the four answers can't carry). The setup ticket's review step
   should present it to the human; spec should require it.
3. **"Docs win on facts, answers win on intent" works.** 4 conflicts
   (940/941 vs nine forms; Jan-1 vs Q4-retry; unreconcile-as-routine vs
   recovery-path; "lots of mistakes" vs nuanced reality) all resolved
   correctly under that precedence. Put the rule in the spec.
4. **Interview tweak candidates:** (a) follow-up probe on enumerables —
   "a few year-end processes" should trigger "list them"; (b) Q2 should
   ask *where* referenced documents live (owner's manual was a Google
   Doc — scannable if pointed at); (c) ask for the pay/anchor dates of
   any non-cron-expressible cadence (bi-weekly broke both legs' crons).
5. **Scan must degrade gracefully:** ops repos can be nearly empty
   outside relay-os (real admin = 3 files). Also fixture-construction
   note: we stripped relay-os/skills, so the receipt-sweep script's
   absence in the fixture is OUR artifact, not signal.
6. **Real-admin side catch:** admin's `.gitignore` ignores
   `2026-tax-materials/` but the dir is `2026-tax-doc/` — stale entry.

**Fixtures kept for the real implementation test:** `~/Desktop/admin-init-test`
(committed baseline + generated relay-os) and `~/Desktop/admin-fresh`.
Replay Zach's recorded answers above against the built feature and diff
against these dry-run outputs.

## Full-process prototype (2026-06-12, `~/Desktop/relay-marketing-test`)

Second validation, downstream of the dry run: the entire setup flow was
run end to end on a real fresh repo (Relay's marketing repo), from
interview answers through generated artifacts, an owner Q&A pass, and
apply-review to done. The repo is kept as a fixture — its
`relay-os/workflows/init/setup.md` is the exact file now shipped in this
branch, and its `tasks/relay-setup/` shows a completed run.

What the prototype changed in the spec:

1. **Interview moved from init-time to launch-time** (Nico: questions at
   `relay init` aren't doable). Init scaffolds the ticket with an empty
   Context; the `interview` workflow step fills it at first launch. Side
   effect: the four questions now live in the workflow file only — no
   second copy in CLI code to drift.
2. **`resolve-open-questions` is a real step, not a hope.** In the
   prototype, scan-and-generate produced 7 open questions that just sat
   on the blackboard; the human review step had no reason to engage with
   them. An agent-driven Q&A step between generation and review got all 7
   answered in minutes, and the review then covered artifacts that
   already reflected the answers.
3. **Ask with options, not open prompts.** Presenting each open question
   as 3–4 plausible choices (drawn from the scan) plus a free-form escape
   got faster, more decisive answers than open-ended asking — and wrong
   options got corrected cheaply ("weekly from Zach's account" → "both
   Zach's and the company account").
4. **Chase document pointers to exact links.** Owners answer "it's in
   Drive somewhere"; the agent searching connected tools and putting a
   candidate link in front of them ("is it this Relay CRM sheet?") turned
   vague pointers into followable references. One guess was wrong
   (evaluation notes were in "Relay Competition Tests", not the folder
   the agent guessed) — which is why candidates are confirmed, not
   silently recorded.
5. **Record-don't-interrogate at the interview step.** Probing every
   vague answer up front is wasted motion — after the scan, the agent has
   concrete options to probe with. The interview records; step 3 chases.
