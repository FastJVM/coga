# Recurring sweep — 2026-09-02 11:56:27

- repo: coga
- mode: bare sweep
- templates scanned: 7
- tasks run: 7
- problems: 0

## Scan

```
autoclose-merged     ready (Wed 08:00)          launch
blocker-reminders    ready (Wed 10:00)          launch
branch-sweep         overdue 2d (Mon 07:00)     launch
digest               ready (Wed 09:00)          launch
dream                overdue 2d (Mon 09:00)     launch
resolve-conflicts    overdue 2d (Mon 08:00)     launch
skill-update         overdue 2d (Mon 09:00)     launch
```

## Task outcomes

### recurring/branch-sweep — completed

- template: `branch-sweep`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.
```

### recurring/resolve-conflicts — completed

- template: `resolve-conflicts`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.
```

### recurring/skill-update — completed

- template: `skill-update`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Skill Update

Generated: 2026-09-02T18:58:53+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python3 -m coga.cli skill update --all --json --pr --pr-title 'Update Coga-managed skills'`
Task: `recurring/skill-update`

Result: 15 skill(s): 1 updated, 0 need follow-up, 14 skipped.
PR: https://github.com/FastJVM/coga/pull/736

### Updated

- `gh-managed`: `delegated` (github) - delegated GitHub-backed skill updates to gh skill

### Skipped

- `bootstrap/delete-task`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/scan/contract-audit`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/scan/knowledge-scan`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/scan/scan-protocol`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/tasks/cleanup-orphan-markers`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/dream/tasks/validate-drift`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/import`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/skill-update`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `bootstrap/ticket`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `browser/build-automation`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/calendar-reminder`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/gmail`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `coga/google-calendar`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
- `retro/done-ticket`: `skipped-bundled` (bundled) - bundled skill updates come from the coga package; run `pip install --upgrade coga`
```

### recurring/autoclose-merged — completed

- template: `autoclose-merged`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.
```

### recurring/digest — completed

- template: `digest`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.
```

### recurring/blocker-reminders — completed

- template: `blocker-reminders`
- ticket status after the run: done

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.
```

### recurring/dream — completed

- template: `dream`
- ticket status after the run: done

What the run wrote to its blackboard:

```
[... truncated ...]
rchitecture: step-gate registry, composition constraint, reserved frontmatter keys, launch env vars |
| #745 | cut agent instructions from `code/*` workflow step bodies that never compose |
| #746 | document `coga usage` and `coga digest`; drop a nonexistent `cron.sh`; fix the concepts prompt-layer order |

Verified after the fact: every branch is pushed, every enforced live/packaged twin
pair touched by a PR is still byte-identical, and no PR edits a file another PR edits.

### Draft tickets created (`code/with-review`)

- `isolated-checkouts-nothing-says-what-a-fresh-workt`
- `no-context-records-the-ci-posture-publish-only-rel`
- `recurring-context-never-mentions-the-packaged-twin`
- `sync-context-omits-preflight-post-from-the-notific`
- `no-rule-says-ticket-context-must-cite-symbols-not`
- `dream-findings-have-three-routing-holes-that-lose`
- `the-human-doc-vs-agent-context-boundary-is-decided`
- `dream-2026-w36-extract-backlog-18-findings-phase-4`
- `four-parked-tickets-carry-premises-that-have-since`

### `human-needed` — decisions this run could not make

1. **Phase 1's 22 `human-needed` validator issues have no route out of this
   blackboard.** They are: 11 `unfrozen-workflow`, 6 `stuck-in-progress`, 5
   `unknown-assignee: 'nicktoper'`. Four consecutive runs have reported the same
   classes with no downward trend (W33 23, W34 23, W35 29, W36 22), and two of the
   stuck tickets have been idle since before W34. Ticketed as
   `dream-findings-have-three-routing-holes-that-lose`, but the underlying
   lifecycle decisions are the owner's.
2. **21 done tickets are outstanding retirement debt.** Each records a real `## Dev`
   branch and worktree, so Retro must not touch them and `coga retire <slug>` stays
   the human-typed path. They are listed in full in the Phase 4 eligibility section
   above. This is also why Phase 4 had no knowledge to extract.
3. **All 18 `extract` findings are orphaned by that debt.** Phase 6's `extract` route
   assumes Phase 4 handled them; Phase 4 structurally could not. Carried into
   `dream-2026-w36-extract-backlog-18-findings-phase-4` so they survive this
   blackboard, but whether to land them as knowledge PRs or let `coga retire` consume
   them is a human call.
4. **Two code-side gaps found but not fixed** (documentation-only PRs by design):
   `config._RESERVED_TICKET_FIELD_NAMES` omits `period_generation` (so
   `[ticket.fields.period_generation]` is accepted and would collide with the
   runner-written key on any period task) and omits `slug` (so
   `[ticket.fields.slug]` loads despite `slug` being required). Flagged in PR #744.
5. **One finding deferred for overlap.** `coga/skills/google-agents-cli-workflow/SKILL.md`
   tells agents to refresh the pack with `uvx google-agents-cli setup`, bypassing
   `coga skill install`/`update` and the `recurring/skill-update` PR loop. Open PR
   **#736** already edits that file, so per the Dream body no conflicting PR was
   opened — it goes to that PR's review.

### Notes for the operator

- `coga/tasks/triage-the-v2-parking-area-empty-descriptions-prem.md` was being edited
  by a concurrent session throughout this run (an evaluator review written into its
  blackboard). Dream did not touch it, but the `coga create` calls in Phase 6 fired
  the ordinary `sync_coga_state` sweep, which will have published that in-progress
  edit along with the new tickets. That is normal Coga behavior, not data loss — and
  it is the same hazard `extract` finding 14 describes.
- This task's own blackboard now trips the `large-blackboard` warning. Expected: the
  recurring scanner deletes this task before creating the 2026-W37 Dream.
- Scan directories `/tmp/dream-ks-Poha8f` and `/tmp/dream-ca-6o1Ife` were deleted
  after their findings merged. The Phase 4 worktree, its temporary branch, the copied
  `coga.local.toml` and the evidence snapshot were all removed and verified gone. The
  ten PR worktrees were removed; their branches are kept because the PRs need them.
```

## Sweep notes

- launching 7 due task(s) sequentially
