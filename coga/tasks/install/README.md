---
slug: install/README
title: install/ — Greg's onboarding feedback index
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
contexts: []
skills: []
workflow: null
secrets: null
script: null
---

## Description

Tickets from **Greg's onboarding feedback (2026-06-24)** — issues hit while
trying to install Relay on a managed work machine.

### Filed here

- `pip-hash-requirement-breaks-editable-install` — pip global hash-checking mode
  aborts `pip install -e .`.
- `recommend-virtualenv-not-system-python` — default install path should use a
  venv, not system Python (also folds the `python` vs `python3` README nit).
- `relay-help-and-cli-should-not-require-user` — `user` is required too broadly
  (even `relay --help`); default to `$USER`.
- `init-does-not-persist-user-then-blocks-on-reinit` — a partially-failed
  `relay init` doesn't persist `user`, then re-init/`--update` wedges.
- `external-users-cannot-install-managed-skills` — outside users lack
  `relay-skills` access, so all managed skills fail on `--update`.
- `document-where-to-run-init-and-adopt-existing-repo` — make clear init runs in
  the project's git root; how to adopt an existing project.
- `harden-packaging-and-install-before-launch` — umbrella: invest in packaging /
  scripted install before announcing.
- `retest-ssh-https-and-init-reclone-on-fresh-machine` — #4 SSH-vs-HTTPS clone +
  init re-clone: the fixes shipped (see below) but Greg still hit it, so this is
  a verification/retest ticket on a clean machine.

### Filed from the fresh-container retest (2026-07-08)

Issues found re-running the full first-install path in a clean docker
`python:3.12` container (PyPI 0.2.0 + main HEAD):

- `vendor-cli-from-installed-package-not-git-clone` — init clones main HEAD to
  vendor the CLI; skew makes the vendored CLI reject init's own coga.toml.
  Replace the clone with install-from-package.
- `warn-loud-when-init-commit-is-skipped` — no git identity → init silently
  skips the coga/ commit; first `coga create` then errors on missing HEAD.
- `add-migration-errors-for-removed-config-keys` — HEAD rejects 0.2.0's own
  scaffolded `[agents.*] auto` key with a generic unknown-key error.
- `cut-release-to-realign-pypi-with-main` — main carries breaking changes but
  still calls itself 0.2.0; release after the migration errors land.
- `quiet-managed-skill-failures-on-old-gh` — gh<2.90 dumps the gh usage screen
  per skill (~260 lines); detect once, one compact line.
- `improve-reinit-already-exists-message` — bare "already exists" refusal with
  no remedy (`--update` is gone).
- `init-next-steps-should-mention-agent-cli-requireme` — "run `coga build`"
  without saying Claude Code/Codex must be installed.
- `gh-auth-hint-on-managed-skill-rate-limit` — anonymous API quota 403s the
  skill installs; remediation should say `gh auth login`.
- `decide-whether-gh-stays-required-at-init` — deliberate call on demoting gh
  to point-of-need like `op`.

Retest verdicts were also appended to the Greg-era tickets still open
(`pip-hash-requirement…`, `relay-help-and-cli…`, `document-where-to-run-init…`,
`retest-ssh-https…`). Verified fixed and left to close/delete:
`recommend-virtualenv-not-system-python` (uv path),
`init-does-not-persist-user-then-blocks-on-reinit` (atomic rollback),
`external-users-cannot-install-managed-skills` (public manifest, warn-only).

### Deliberately NOT filed (already covered)

- **SSH vs HTTPS clone + init re-clone / `RELAY_REPO_URL`** → the behavior fix is
  covered by `relay-forces-https` (done) and `remote-default-origin` (done).
  Greg still hit it, so rather than re-implementing, the open work is the retest
  ticket `retest-ssh-https-and-init-reclone-on-fresh-machine` above.
- **Capturing the user's name at init** → `relay-init-captures-name-via-user-param`
  (done). The remaining issue is *strictness*, filed as
  `relay-help-and-cli-should-not-require-user`.
- **The 12 noisy skill-install failure dumps** → `marketing/quiet-relay-init-managed-skill-failures`
  (draft). The *access* problem is filed as `external-users-cannot-install-managed-skills`.

<!-- coga:blackboard -->
