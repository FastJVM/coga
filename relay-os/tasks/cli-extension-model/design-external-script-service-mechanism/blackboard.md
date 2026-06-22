The blackboard is a notepad to be written to often as the human and agent works through a task.

## 2026-06-22 execution

Read the live ticket, `direct/body`, `docs/vision.md`, `relay/extension-model`,
`relay/principles`, `docs/cli-extension-audit.md`,
`src/relay/commands/skill.py`, `src/relay/skill_manager.py`, and the launch /
compose script-loading paths.

Decision:

- Home the deliverable in `docs/cli-extension-external-surface.md`.
  Rationale: this is design rationale and an implementation contract, while
  `relay/extension-model` remains the launch-loaded behavioral rule.
- Update `relay-os/contexts/relay/extension-model/SKILL.md` only as a pointer
  so the context no longer says the external-script mechanism is entirely
  undesigned.
- Specify verify-at-compose as kernel: both agent prompt composition and
  script-mode skill loading should refuse a managed skill whose current tree
  digest differs from recorded `installed_tree_digest`, before status mutation,
  secret injection, prompt composition, or script execution.
- Pick a narrow `gh`-style extension for the first external-script extraction:
  the skill acquirer. This is not a generic `relay-os/scripts/` dispatcher and
  not a hosted service. Future non-GitHub helpers can use normal local CLIs.
- Leave read-view migration (`status`, `show`, `recurring list`, `skill status`)
  to the companion Pass 2 task.

Follow-ups named in the doc:

- Implement the shared verify hook and tests.
- Normalize provenance for all externally acquired skills before compose relies
  on it.
- Extract `skill install/install-local/install-url/update/remove` after the
  verify hook/provenance contract is in place.
- Consider `init --update` only after the acquirer extraction proves the
  external package boundary.
