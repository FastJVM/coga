# install/

Tickets from **Greg's onboarding feedback (2026-06-24)** — issues hit while
trying to install Relay on a managed work machine.

## Filed here

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

## Deliberately NOT filed (already covered)

- **SSH vs HTTPS clone + init re-clone / `RELAY_REPO_URL`** → the behavior fix is
  covered by `relay-forces-https` (done) and `remote-default-origin` (done).
  Greg still hit it, so rather than re-implementing, the open work is the retest
  ticket `retest-ssh-https-and-init-reclone-on-fresh-machine` above.
- **Capturing the user's name at init** → `relay-init-captures-name-via-user-param`
  (done). The remaining issue is *strictness*, filed as
  `relay-help-and-cli-should-not-require-user`.
- **The 12 noisy skill-install failure dumps** → `marketing/quiet-relay-init-managed-skill-failures`
  (draft). The *access* problem is filed as `external-users-cannot-install-managed-skills`.
