---
name: test/secret-probe
description: Scratch script skill for the auth-path manual test — prints which test_* Relay secret keys were injected into the script env, names only, never values.
script: probe.sh
---

# Secret probe

Scratch fixture for the manual auth-path test
(`manually-test-auth-paths-gh-git-detection-secret-r`). Prints the **names** of
injected `test_*` secret env vars (never their values) so per-task `secrets:`
gating can be verified by eye. Delete with the rest of the test fixtures when
finished.
