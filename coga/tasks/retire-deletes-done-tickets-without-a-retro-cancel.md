---
title: Retire deletes done tickets without a retro; canceled tickets get one
status: in_progress
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
step: 3 (open-pr)
agent: claude
launch_generation: 52af10df-029f-4d98-8cae-db24df757a98
---

## Description

Owner decision 2026-10-13. Done tickets pile up (136 done, 29 canceled): autoclose marks them done and deletes their branch but leaves the branch: line in ## Dev, and Dream's Phase 4 gate only checks that the line is present, so it skips every one (it reports 153 tickets of retirement debt each week). For 119 of them the recorded branch no longer exists. Only manual coga retire drains them, at one agent run per ticket; it has run 5 times ever. New rule: positive learning already landed in the merged PR (the sync rule updates the owning topic in the same PR), and negative learning lives in the ticket or blackboard, usually as the cancellation reason. So (1) coga retire on a done ticket disposes of its checkout and deletes the ticket deterministically, with no retro agent; (2) coga retire accepts canceled tickets and runs the retro on them to extract the cancellation reason and any other negative learning, then deletes; (3) the Dream retirement gate checks whether the recorded branch or worktree still exists (as retire_worklist already does) instead of whether the line is written; (4) update dev/checkout-cleanup, coga/dream and coga/lifecycle, plus packaged twins, in the same PR. Then drain the backlog: plain deletes for done tickets with no live branch, retire for the ~17 with a live branch, and retros for the canceled tickets.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/1014
branch: retire-done-deterministic

## Plan

- `coga retire` on `done`: dispose checkout (same proofs), discharge worklist, then `delete_task` + sync. No retire task, no agent. A kept checkout exits 2 and leaves the ticket (it is the owner record).
- `coga retire` on `canceled`: existing path (dispose, retire task running Retro), Retro extracts the cancellation reason / negative learning.
- Dream Phase 4 gate: done ticket eligible unless its recorded branch/worktree still exists.
- Backlog drain deferred until this merges (it needs the new retire).

## Implement handoff

Branch `retire-done-deterministic` pushed (head d50a13b2c, on origin/main 33435783a). No PR yet.

What changed:
- `src/coga/commands/retire.py`: accepts `done` or `canceled`. Both go through the same checkout disposal + worklist discharge first. `done` → `_delete_done_task`: `run_delete_task` + `git.publish` (`Ticket: <slug> — deleted (retire)`), no retire task, no agent. A kept checkout on a done ticket exits 2 and deletes/creates nothing (ticket stays as owner record; rerun `coga retire`). `canceled` → the old retire-task path unchanged (blocked task on a kept checkout).
- `src/coga/resources/retire.md`: the retire task body is now for a canceled ticket; Retro extracts the cancellation reason / negative learning. Stop condition now "not canceled".
- `bootstrap/skills/retro/done-ticket`: new `### Canceled tickets` section; status gates admit one canceled slug from `coga retire`; "Done is a status, not a receipt" skipped for canceled.
- Dream template (live + twin) Phase 4 gate: done ticket eligible unless its `## Dev` records a **live** checkout (branch still local or on the remote, or worktree dir still present and not a primary). Unanswerable probe = live. Canceled tickets listed as retirement debt.
- Dream Phase 6 routing (decision, flag for review): `done+checkout` findings now get a proposal PR (retire no longer retros done tickets, so nothing else would extract them); `canceled` findings are now listed as retirement debt with no PR (retire's Retro consumes them). Knowledge-scan `source:` definitions updated to match.
- Topics (+ packaged twins): dev/checkout-cleanup (retire section, owner decision 2026-10-13), coga/dream, coga/lifecycle, coga/tickets, coga/extension-model, coga/blackboard.
- Tests: test_retire.py (existing retire-task tests now seed canceled; new done-delete, done-kept-branch, done-worktree+worklist tests); test_dream_worker_templates.py assertions updated.

Not done here — backlog drain (needs this merged first, since it uses the new retire):
1. Done tickets with no live branch/worktree: `coga retire <slug>` (now a deterministic delete) or `coga delete`.
2. Done tickets with a live branch (~17): `coga retire <slug>` from `main`; any that exit 2 kept a checkout and need a hand fix.
3. Canceled tickets (~29): `coga retire <slug>` each (one Retro agent run per ticket).

Note: Dream Phase 4 still runs Retro over eligible done tickets; the ticket only asked to change its gate. Whether Dream should also just delete done tickets is a possible follow-up.

## Peer review

Direct Codex review **completed** on head `22e12bf57595f6cb142df64e3e126f1c0ea1adce` against base
`aa33928065ab8270cbfbde7158f9561939d6b007`. Reviewed the implementation, disposal/deletion/publication
helpers, Dream and Retro instructions, owning contracts, twins, and tests.
Claude authored the original implementation; this fresh Codex session reviewed
it independently, then authored and self-reviewed the correction below. No
nested Codex CLI or review subagent was used.

- Fixed: Dream's new local-only branch probe exempted a foreign primary clone's
  directory without checking its branch there. A done ticket could therefore
  lose its owner record while its sandbox branch survived. The final gate
  follows `retire_worklist` ownership, checks every recorded branch and the
  configured remote, anchors relative worktree paths at the repository root,
  and keeps unknown probes as retirement debt. Updated live/packaged guidance
  and prompt assertions. Commit: `22e12bf57`.
- Final re-review: no unresolved must-fix findings. Phase 6's routing change is
  consistent with the new consumers; Dream's eligible done-ticket Retro pass
  remains intentionally unchanged apart from eligibility. Backlog drain still
  waits for merge.
- Verification: final full suite `3599 passed in 319.39s (0:05:19)`; focused retire/Dream/worklist/
  packaging suite `125 passed`; scratch CLI publication smoke passed; diff
  whitespace check passed. Exact commands and revisions are in `## PR`.
- Human-visible surface: inspected scratch CLI output for deterministic delete
  and canceled `--no-launch` task creation. No raw-terminal loop, pager, TTY
  prompt, or rendered Slack change is in this diff. Live agent behavior was
  reviewed as instructions; no real-ticket retire or full Dream/Retro run.
- Freshness: unconditionally fetched and rebased onto `aa33928065ab8270cbfbde7158f9561939d6b007`;
  final branch committed and pushed with `--force-with-lease`. Checkout returned
  to clean `main` before this handoff. PR recommendation: `deep` because the
  command now deletes done tickets automatically and the final review fix is
  self-reviewed.

## PR

```yaml
title: Retire done tickets without a retro; run Retro on canceled ones
author: claude/codex
author_evidence: Claude Code (claude-opus-5-5) implemented the change in the prior session. Codex
  directly reviewed it in this fresh peer session and authored the foreign-branch ownership correction
  in 22e12bf57.
head: 22e12bf57595f6cb142df64e3e126f1c0ea1adce
base: aa33928065ab8270cbfbde7158f9561939d6b007
depth: deep
rationale: Changes a destructive lifecycle command and Dream knowledge routing. Review completed and
  checks passed; inspect the done/canceled policy split and the prompt-driven checkout gate. The Codex
  review fix is self-reviewed.
implementation: coga retire deletes done tickets after checkout disposal and runs Retro only on canceled
  tickets; Dream's retirement gate checks whether the recorded branch/worktree still exists.
deviations: Dream Phase 6 now opens proposal PRs for done+checkout findings and lists canceled findings
  as retirement debt, consistent with their new retirement consumers. Peer review corrected the live-checkout
  gate to check all branches in their owning repository. Backlog drain remains deferred until merge.
limitations: Dream eligibility and Retro extraction remain agent-run instructions; no live Dream or
  Retro agent was launched. Scratch CLI tests covered publication to a local bare remote, not real-ticket
  deletion. The full suite ran on Python 3.12.12; Python 3.11 was not tested. Existing best-effort
  cleanup exceptions (off control, Git disabled/non-Git, and remote branch leftovers) are unchanged.
  No interactive terminal, pager, or rendered Slack surface changed; CLI output was inspected in the
  scratch run.
files:
  src/coga/commands/retire.py: Deterministic delete for done tickets; accept canceled tickets for
    the Retro task.
  src/coga/resources/retire.md: Retire task body now targets a canceled ticket's negative learning.
  src/coga/resources/templates/coga/bootstrap/skills/retro/done-ticket/SKILL.md: Admit one canceled
    slug from coga retire and say what to extract from it.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/dream/scan/knowledge-scan/SKILL.md: 'source:
    classifications follow the live-checkout ownership rule and new knowledge routing.'
  coga/recurring/dream/ticket.md: Phase 4 checks every branch in its owning repository and on the
    remote, including foreign primary clones; Phase 6 routes done and canceled findings to their consumers.
  src/coga/resources/templates/coga/recurring/dream/ticket.md: Packaged twin of the Dream template.
  docs/contexts/dev/checkout-cleanup/SKILL.md: coga retire contract for done vs canceled tickets.
  docs/contexts/coga/dream/SKILL.md: Owns the live-checkout eligibility, foreign-branch ownership,
    and retirement-debt routing rules.
  docs/contexts/coga/lifecycle/SKILL.md: What retire does after a terminal transition.
  docs/contexts/coga/tickets/SKILL.md: retire accepts done or canceled.
  docs/contexts/coga/extension-model/SKILL.md: Retire-task example now names canceled tickets.
  docs/contexts/coga/blackboard/SKILL.md: Live-checkout wording for flagged done tickets.
  src/coga/resources/templates/coga/bootstrap/contexts/dev/checkout-cleanup/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/dream/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/extension-model/SKILL.md: Packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/blackboard/SKILL.md: Packaged twin.
  tests/test_retire.py: Done-path delete/refusal tests; retire-task tests now seed canceled tickets.
  tests/test_dream_worker_templates.py: Checks the revised routing and preservation of every branch,
    including branches held only in independent clones.
review:
  reviewer: codex
  kind: self
  status: passed
  head: 22e12bf57595f6cb142df64e3e126f1c0ea1adce
  base: aa33928065ab8270cbfbde7158f9561939d6b007
  detail: Direct review completed on the final diff with no unresolved must-fix findings. Independent
    review of Claude implementation found that Dream could delete a ticket whose only live branch
    was in a foreign primary clone. Codex fixed ownership, all-branch checks, canonical/packaged guidance
    and assertions, then re-reviewed the final diff. The final receipt is conservatively self-review
    because Codex authored that fix; no second independent reviewer reviewed it. No nested review
    CLI was used.
checks:
- command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q
  status: passed
  head: 22e12bf57595f6cb142df64e3e126f1c0ea1adce
  base: aa33928065ab8270cbfbde7158f9561939d6b007
  detail: '3599 passed in 319.39s (0:05:19); final committed tree, Python 3.12.12. Log: /tmp/retire-peer-final-pytest.log.'
- command: PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/test_retire.py tests/test_dream_worker_templates.py
    tests/test_retire_worklist.py tests/test_packaging.py
  status: passed
  head: 22e12bf57595f6cb142df64e3e126f1c0ea1adce
  base: aa33928065ab8270cbfbde7158f9561939d6b007
  detail: 125 passed in 6.32s on the exact tree subsequently committed as this head.
- command: PYTHONPATH=$PWD/src .venv/bin/python /tmp/retire_peer_smoke.py
  status: passed
  head: 22e12bf57595f6cb142df64e3e126f1c0ea1adce
  base: aa33928065ab8270cbfbde7158f9561939d6b007
  detail: 'On the exact tree subsequently committed as this head: scratch repository with local bare
    remote; done single-file ticket deleted and published with no Retro task; canceled source retained
    and active Retro task published with --no-launch; checkout clean. No real tickets or external
    agent launches.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: 22e12bf57595f6cb142df64e3e126f1c0ea1adce
  base: aa33928065ab8270cbfbde7158f9561939d6b007
  detail: No whitespace errors on the feature branch after the review fix.
```
