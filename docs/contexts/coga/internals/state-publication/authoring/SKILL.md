---
name: coga/internals/state-publication/authoring
description: What `coga ticket` guided authoring publishes on finalization — fingerprinting the Coga roots, config reload and Git-destination refusal, one guarded publish with required knowledge paths — and how ordinary manual edits publish.
---

# Guided authoring

Part of [coga/internals/state-publication](../SKILL.md).

`coga ticket` guided authoring (`authoring.finalize_authored`) fingerprints
the eligible files under the Coga roots before the interview — file mode plus
content hash, so a mode-only edit is a change
(`authoring_sync_roots` is `coga_root_paths`; Git lists the files, so ignored
ones are never hashed, and symlinks are never followed). After it, finalization
reloads and validates configuration before discovering files or validating
tickets. An authored change to the Git destination (`[git]` enabled, remote,
or control branch) refuses, as at the launch boundary, and keeps the edits:
the handoff publishes only where the interview started. The changed set compares the original snapshot with the new roots,
so a context relocation carries the old-path deletions, destination files,
and layout config in the same publication. A regular file still on disk but
excluded from the new eligible inventory (for example by a new ignore rule)
stays local; it is not a deletion or a required publication path. If a previously snapshotted path
now has a symlinked ancestor, finalization refuses instead of treating it as
a deletion and following its new target. Invalid configuration refuses
before publication and keeps the edits. An existing target is validated even when
unchanged, but its task path is selected only when its ticket or attachments
changed; file-to-directory conversions include both paths; a deleted target
is skipped. Bootstrap interviews discover and validate changed or new tasks.

After validation, the authored task paths and every changed file outside the
tasks directory (contexts, skills, workflows, config; the log is left to its
writers and the sweep) land in **one** guarded publish. Finalization
requires its changed knowledge files through `require_paths`: committed
feature-branch edits, mode included, must already be on control or finalization fails with a
review/merge remedy before publishing the task. A bootstrap interview
that only writes a context still publishes it, so the next ticket launch finds
it on control with no extra branch. Validation errors propagate before
anything is published. A refused or failed publish keeps every edit on disk,
exactly as authored, and raises `AuthoringError` — `coga ticket` exits
non-zero rather than reporting a completed handoff. That invocation withholds
its final sweep so it cannot publish a task separately from the knowledge the
authoring transaction refused; a later command may retry eligible dirty files.
A successful publish names the non-task files it carried on
stderr. The boundary is identical with or without launch metadata, on control
and feature checkouts.

Ordinary manual edits inside the roots publish the same way, through the next
command's sweep. Local prompt composition still reads local edits. This is an
automatic publication boundary, not a permission barrier against explicit Git
commands; a human may still choose a PR for a change they want reviewed.
