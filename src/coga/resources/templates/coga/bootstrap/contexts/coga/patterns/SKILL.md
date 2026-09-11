---
name: coga/patterns
description: Reusable Coga design patterns built from the core primitives, and the rules of thumb for composing new ones without hidden state. Attach when designing a feature that collects events or state across runs.
---

# Coga patterns

Compositions of the core primitives (`coga/architecture`) that recur often
enough to be worth naming, so a new feature reaches for the established shape
instead of re-deriving it — or worse, inventing a hidden `.queue` dotfile that
breaks Coga's no-hidden-state rule.

Use these rules when a feature needs to collect events or carry state across
runs.

## Rules of thumb for a new composition

- **No hidden state.** Anything that accumulates between runs is a real,
  git-tracked, human-readable file under `coga/` — openable mid-flight, never
  a dotfile or opaque store.
- **Capture at event time, not from history.** Record what happened the moment
  it fires so nothing depends on scanning `git log` to reconstruct it, and so
  work that is done-and-deleted before a later reader runs is still accounted
  for.
- **Reuse the recurring machinery for the periodic half.** A scheduled reader
  is a `recurring/<job>/` ticket (see `coga/recurring`) whose deterministic
  half is the reserved sibling `ticket.py`; its cadence lives in `schedule:`
  frontmatter, reproducible from the repo with no external cron.
- **Cross-run state lives beside the template, not in the period task.**
  `coga/recurring/<job>/` carries across runs; the per-period task is gone
  next period.
- **Atomic file replacement is crash-safety, not a lock.**
  `atomicio.atomic_write_text` guarantees a reader sees the old or the new
  complete file; it does not serialize two writers. Coga allows multiple
  processes and clones to race on state-plane writes, so a composition must
  stay correct *by shape* — append-only regions, disjoint hunks — or add an
  explicit primitive. `merge=union` (`.gitattributes`) resolves the pure
  append-vs-append case for `log.md`; it does not resolve anything else.
- **Prefer the live path when volume is low.** Batching buys nothing until the
  live feed is noisy enough to be a problem; until then it only adds a queue,
  a consumer, and a class of drain/merge bugs.

## What this context does NOT cover

- The primitives themselves (recurring tasks, status, git sync) — see
  `coga/architecture` and `coga/recurring`.
- How `log.md` lands across branches and checkouts — see `coga/sync`.
- The checkout-local state admission/publication barrier — `coga/architecture`.
