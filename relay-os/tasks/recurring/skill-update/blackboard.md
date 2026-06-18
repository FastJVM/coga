The blackboard is a notepad to be written to often as the human and agent works through a task.

## Skill Update

Generated: 2026-06-18T04:02:18+00:00
Command: `/home/n/Code/relay/relay-os/.relay/.venv/bin/python -m relay.cli skill update --all --json --pr --pr-title 'Update Relay-managed skills'`
Task: `recurring/skill-update`

Result: 12 skill(s): 1 updated, 0 need follow-up, 11 skipped.
PR: https://github.com/FastJVM/relay/pull/386

### Updated

- `gh-managed`: `delegated` (github) - delegated GitHub-backed skill updates to gh skill

### Skipped

- `bootstrap/delete-task`: `skipped-bundled` (bundled) - bundled skill updates come from the relay package; run `pip install --upgrade relay-os` then `relay init --update`
- `bootstrap/dream/scan/contract-audit`: `skipped-bundled` (bundled) - bundled skill updates come from the relay package; run `pip install --upgrade relay-os` then `relay init --update`
- `bootstrap/dream/scan/knowledge-scan`: `skipped-bundled` (bundled) - bundled skill updates come from the relay package; run `pip install --upgrade relay-os` then `relay init --update`
- `bootstrap/dream/tasks/cleanup-orphan-markers`: `skipped-bundled` (bundled) - bundled skill updates come from the relay package; run `pip install --upgrade relay-os` then `relay init --update`
- `bootstrap/dream/tasks/validate-drift`: `skipped-bundled` (bundled) - bundled skill updates come from the relay package; run `pip install --upgrade relay-os` then `relay init --update`
- `bootstrap/import`: `skipped-bundled` (bundled) - bundled skill updates come from the relay package; run `pip install --upgrade relay-os` then `relay init --update`
- `bootstrap/project`: `skipped-bundled` (bundled) - bundled skill updates come from the relay package; run `pip install --upgrade relay-os` then `relay init --update`
- `bootstrap/skill-update`: `skipped-bundled` (bundled) - bundled skill updates come from the relay package; run `pip install --upgrade relay-os` then `relay init --update`
- `bootstrap/ticket`: `skipped-bundled` (bundled) - bundled skill updates come from the relay package; run `pip install --upgrade relay-os` then `relay init --update`
- `eval/ticket-diagnostic`: `skipped-bundled` (bundled) - bundled skill updates come from the relay package; run `pip install --upgrade relay-os` then `relay init --update`
- `retro/done-ticket`: `skipped-bundled` (bundled) - bundled skill updates come from the relay package; run `pip install --upgrade relay-os` then `relay init --update`
