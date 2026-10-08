# Context

This repo is Coga itself: the source of the `coga` package, its packaged
resources, and the canonical topic library under `docs/contexts/`. Root
`CLAUDE.md`/`AGENTS.md` carry the full repository guidelines.

## Keep Coga small and legible

Preserve Coga's microkernel boundary. `src/coga/` contains only:

1. shared infrastructure with at least two real consumers; and
2. reviewed, co-versioned command contracts: the fixed functions registered
   in `runner.RECIPES` behind `coga run`, or commands whose contracts name a
   package-private invariant or atomic transaction that an edge implementation
   using stable CLI and filesystem interfaces could not preserve. Python
   logic or inability to use an alias does not establish a core home.

Everything else stays at the edge: process knowledge and reusable recipes in
skills, ticket-owned deterministic work in its exact sibling `ticket.py`
(which may call a wheel-owned edge module; see `coga/packaging`), and
launch-target spellings as aliases. Backing a CLI spelling is not by itself a
pass into core — a launch-target command is an argv rewrite in `[aliases]`,
whereas a registered `coga run` name is a real package implementation with a
stable argv, stdout, and exit contract. Prefer plain markdown, Python, git,
and shell operations over hidden state or new machinery. `coga/extension-model`
owns the full rule.
