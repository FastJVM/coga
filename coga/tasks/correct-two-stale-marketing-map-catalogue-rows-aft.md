---
title: Correct two stale marketing map catalogue rows after PR 841 lands
status: draft
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
---

## Description

Filed by Dream 2026-W39, Phase 6. Route: `stale` findings on `coga/contexts/marketing/map/SKILL.md` (touched by open PR #841 `remove-narrative-candidates`, whose diff does not carry these corrections). Apply after #841 lands. The `marketing/distribution` half of F31 has its own proposal PR from this run.

**F30 — marketing/map links three clarity files the install allowlist pruned**  
(Dream 2026-W39 Phase 2, shard ks-02, ks-01 (merged); class `stale`; target `coga/contexts/marketing/map/SKILL.md`; overlapping open PR: #841)

The "Writing methods" table in `coga/contexts/marketing/map/SKILL.md` has a row "Imported skill documentation and examples" linking `../../../skills/clarity/README.md`, `../../../skills/clarity/PRODUCT.md` and `../../../skills/clarity/samples/README.md`, and the catalogue header claims "no missing files or broken local links" (coverage checked 2026-09-10). None of the three paths exists: `coga/skills/clarity/` holds only `SKILL.md`, `LICENSE`, `references/` and `scripts/`, because `coga/skills/clarity/.coga-source.json` (installed 2026-09-08 by `coga skill install-url`) records an `include` allowlist and `local_adaptation_notes` that deliberately drop `README`, `PRODUCT` and `samples/` so `coga skill update` re-applies the pruning. The done ticket `no-comms-writing-skill-the-process-is-smeared-thro` planned that prune; no open ticket owns the dangling row (grep of `coga/tasks/` for `PRODUCT.md`, `clarity/README`, `samples/README` hits only that done ticket). The peer review in `phase-0-audit-is-complete-per-the-plan-but-still-i` already noted "three missing Clarity documentation links already exist on origin/main" without fixing them. Fix: delete the row (the notes say the skill body never loads those files) or repoint it to the upstream `source_url` in `.coga-source.json`, and drop the "no broken local links" claim or re-verify it.

_Merged duplicate from ks-01 ("marketing/map links clarity README, PRODUCT and samples that the prune removed"):_ The "Writing methods" table row "Imported skill documentation and examples" links `../../../skills/clarity/README.md`, `../../../skills/clarity/PRODUCT.md` and `../../../skills/clarity/samples/README.md` and describes them as "Third-party examples and skill documentation". None of the three exists on `main`: `coga/skills/clarity/` now holds only `LICENSE`, `SKILL.md`, `references/` and `scripts/`, and `.coga-source.json`'s `include` allowlist (`local_adaptation_notes`: "Pruned to the runtime skill only ... README/DESIGN/PRODUCT ... samples/ ... are excluded by that allowlist") makes `coga skill update` re-apply that pruning, so the files will not come back. `git log -- coga/skills/clarity/README.md` shows the last removal in `7966c2a23` (2026-09-14), after the map's "Coverage checked against the repo on 2026-09-10" line, and the map was last touched by #805 on 2026-09-14 without correcting this row. The row should be dropped or reduced to the `.coga-source.json` provenance pointer; the adjacent "Prose craft" row already covers what survives.

**F31 — marketing/map and marketing/distribution still call the telemetry ticket an empty concept with no policy decision**  
(Dream 2026-W39 Phase 2, shard ks-02; class `stale`; target `coga/contexts/marketing/map/SKILL.md, coga/contexts/marketing/distribution/SKILL.md`; overlapping open PR: #841 (map half only))

`coga/contexts/marketing/map/SKILL.md` ("Distribution and audience" table) describes `coga/tasks/marketing/add-telemetry.md` as "Empty concept draft. It authorizes no instrumentation or change to distribution policy", and `coga/contexts/marketing/distribution/SKILL.md` ("Measurement and interpretation") says "The existing measurement boundary remains: no user instrumentation is authorized. The telemetry concept has no developed brief or policy decision." Current reality: `marketing/add-telemetry` ("Add PostHog phone-home telemetry for V1 product-market-fit signal") is `status: in_progress` at `step: 3 (review-design)` of `code/design-then-implement`, is 32 KB with acceptance criteria, a proposed shape and a completed design/evaluator review (log 2026-09-20 14:00–14:02), and its description records "Owner decisions, nicktoper, attended session 2026-09-20: reverse the principles #5 telemetry ban … These choices are settled." So the brief exists and the policy decision is made; only the implementation has not landed (`coga/contexts/coga/principles/SKILL.md` §5 still carries the absolute ban, which the ticket plans to amend). The ticket's "Documentation ownership and verification" section lists principles, architecture, usage, README and `docs/operations.md` as surfaces to update but not these two marketing contexts, so nothing currently scheduled fixes them. Fix: reword the map row to "in-progress design ticket; owner reversed the ban 2026-09-20" and replace distribution's "no user instrumentation is authorized … no developed brief or policy decision" with a pointer to the ticket and to `coga/principles` as the policy owner, so marketing measurement planning does not re-assert a boundary the owner has lifted.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
