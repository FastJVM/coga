# Audit retention release notes

Audit retention is now on by default for fresh repositories and for existing
repositories after explicit adoption: 30 local calendar days, with weekly
Monday 04:00 maintenance. Set shared `[log].retention_days = 0` to disable it,
or another non-negative integer to change the window.

Full histories for tickets still on disk, recurring high-water/pause evidence,
unread phone-home movement, and opaque/incomplete content survive beyond the
window. This is a retention target, not a byte cap. Older usage queries may be
incomplete; they do not automatically read Git history. Git keeps removed
history; there is no archive file.

The audit log now uses `/log.md -merge`. Concurrent Coga appends reconcile
through the publisher; competing native Git changes can require visible
conflict recovery. Retire worklists retain their union behavior. Phone-home
migrates to local event fingerprints; payload, identity and delivery policy
are unchanged.

Upgrade every writer while sessions are quiesced, then run the feature-specific
`"$COGA_PY" -m coga_edge.trim_log --install` using the upgraded CLI's interpreter.
Wheel replacement alone does not install the schedule. The installer preserves
opt-outs, parked jobs and local forks and refuses conflicting customizations.
Review and publish the named edits. The persistent
[adoption and recovery guide](https://github.com/FastJVM/coga/blob/main/coga/recurring/trim-log/operations.md) contains the
interpreter-resolution link, exact allowlist, rollback and crash procedure.
