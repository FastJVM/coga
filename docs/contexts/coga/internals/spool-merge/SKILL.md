---
name: coga/internals/spool-merge
description: How concurrent writers to shared Coga state files stay correct — `merge=union` append-only files (`log.md`, `retires.md`), the one-line-per-event audit-log encoding and its legacy-line policy, the union three-way merge in `publish`, content guards on union files, and why atomic replacement is crash-safety rather than a lock; also records that the digest spool no longer exists.
---

# Append-only state and concurrent writers

Coga lets several processes, worktrees, and clones write state at once. No
lock spans them: `git.state_lock` serializes one checkout only, and
cross-checkout coordination is the push compare-and-swap in
[`coga/internals/state-publication`](../state-publication/SKILL.md). Files that
many writers touch must therefore be correct **by shape**.

**No spool exists.** The daily digest and its outcome spool were removed
(#786); outcomes post live ([`coga/notifications`](../../notifications/SKILL.md)).
There is no hidden queue, drain step, or high-water watermark for
notifications. This page keeps the reusable merge rules that outlived it.

## `merge=union` files

`coga/.gitattributes` marks `**/log.md` and `**/retires.md` `merge=union`.
Union keeps both sides' lines, which is safe only when resurrecting a line
is harmless:

- `coga/log.md` — every writer only appends, so union never loses or revives
  anything meaningful. Usage records ride it (`coga/usage`).
- `coga/recurring/<name>/retires.md` — the autoclose retire worklist is
  rewritten, so a union can duplicate a slug or resurrect a dropped line; its
  reader collapses duplicates and the next reconcile re-applies the discharge
  rule (`src/coga/retire_worklist.py`).

A file that is compacted, trimmed, or rewritten without such a healing reader
must never carry the attribute: union would resurrect deletions. Because
`git.union_merge_paths` asks `git check-attr merge` rather than hardcoding
names, adding a path to `.gitattributes` is enough to route it through the
union merge — which is also why adding the wrong file is the mistake to avoid.

## One event per log line

Union merging, retraction (`logfile.retract_log_lines`), and every log reader
work on physical lines, so each `coga/log.md` event must be exactly one
LF-terminated line: `YYYY-MM-DD HH:MM [<ref>] [<actor>] <message>`.
`logfile.append_log` guarantees this centrally; callers pass raw text,
multiline Git stderr included, and never sanitize. It escapes `\` as `\\`
first, then writes LF and CR as the literal two-character text `\n` and
`\r` (CRLF becomes `\r\n`). A literal backslash can never be mistaken for
a line break, so `logfile.decode_log_message` recovers the exact message.
Other control characters, such as tabs and ANSI escapes, pass through
unchanged. Readers therefore split on LF only (`logfile.log_lines`), never on
the wider `str.splitlines` set, and decode a message before parsing it. The
returned line bytes are exactly what was appended, which is what an exact-byte
retraction removes.

**Legacy lines stay.** The log is append-only, so events written before this
encoding are not rewritten. A message that contained a line break left one or
more continuation lines with no leading timestamp, sometimes starting with a
`[<ref>]`-looking prefix. Readers skip such a line rather than misparse it,
and `coga show` (`logfile.task_log_lines`) prints it with the event it
follows. The decode is applied to legacy lines too. It can alter the free text
of an old line that held a literal `\\`, `\n`, or `\r`, so a reader that
needs exact legacy text falls back to the raw message when the decoded one
does not parse (`usage.load_records`). Retraction removes the tagged event and
any continuation lines that follow it, and matches the `[<ref>]` field rather
than a substring, so a peer event that mentions the tag stays. That
whole-event guarantee covers events written under this encoding; an
already-malformed historical event need not retract cleanly.

## How `publish` lands a union path

- No provenance check: union paths merge rather than overlay.
- The landed bytes are `git merge-file --union` of (merge-base copy, control's
  copy, working copy) (`_merge_union_bytes`), and those bytes are what the
  control checkout is fast-forwarded to.
- A union path missing locally while control has it is refused, never
  published as a deletion (`coga/internals/git-regressions`).
- When a writer decided something from control's exact copy, it pins it:
  `expect` adds a blob check (only while the path is a candidate), and
  `guard` re-evaluates control's *content* before every attempt. The
  recurring create uses both — it pins the ledger and template it read and
  refuses once control records the period as serviced — so a peer that
  serviced the period between fetch and push makes the create re-read
  control instead of landing a duplicate.

## Crash-safe replacement is not a lock

`atomicio.atomic_write_text` writes a same-directory temp file (fsync by
default), then `os.replace`s it, so a reader sees the old or the new complete
file and a crash never leaves a half-written file for the sweep to publish. It
does **not** serialize writers: two read-modify-write cycles can still race,
and the later one wins. A composition must stay correct through one of:

- append-only regions (union-merged);
- disjoint hunks that git merges cleanly;
- an explicit primitive — `state_lock` within a checkout or launch claims
  ([`coga/internals/launch-claims`](../launch-claims/SKILL.md)), `expect`/`guard`
  across checkouts.

`merge=union` resolves only the pure append-versus-append case; it resolves
nothing else.
