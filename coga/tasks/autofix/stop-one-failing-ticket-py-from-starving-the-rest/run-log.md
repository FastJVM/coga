# Recurring sweep — 2026-09-08 11:21:18

- repo: coga
- mode: bare sweep
- templates scanned: 7
- tasks run: 3
- problems: 1

## Scan

```
autoclose-merged     ready (Tue 08:00)          launch
blocker-reminders    ready (Tue 10:00)          launch
branch-sweep         overdue 1d (Mon 07:00)     launch
digest               ready (Tue 09:00)          launch
dream                overdue 1d (Mon 09:00)     launch
resolve-conflicts    overdue 1d (Mon 08:00)     launch
skill-update         overdue 1d (Mon 09:00)     launch
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

### recurring/skill-update — failed

- template: `skill-update`
- exit code: 1
- ticket status after the run: in_progress

What the run wrote to its blackboard:

```


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Skill Update

Generated: 2026-09-08T18:24:16+00:00
Command: `/home/n/.local/share/uv/tools/coga/bin/python3 -m coga.cli skill update --all --json --pr --pr-title 'Update Coga-managed skills'`
Task: `recurring/skill-update`

Result: 16 skill(s): 1 updated, 1 need follow-up, 14 skipped.
PR: none opened — no clean skill updates to commit.

### Updated

- `gh-managed`: `delegated` (github) - delegated GitHub-backed skill updates to gh skill

### Needs follow-up

- `clarity`: `conflict` (url) - local files differ from recorded installed digest and upstream changed; manual resolution required

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

## Sweep notes

- launching 7 due task(s) sequentially
