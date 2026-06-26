---
name: bootstrap/import
description: How to bring an external Agent Skill into a Coga repo — when to import, adapt, or write from scratch, how to find a candidate, and how provenance is recorded so a human can see what was imported and what changed locally.
---

# Import an external skill

Coga skills are plain `SKILL.md` files — the same format Claude Code, Codex,
and the wider ecosystem (OpenClaw / ClawHub and its registries) already speak.
That means the reusable playbook you need has often *already been written*.
Before you hand-write a skill from scratch, check whether an external one fits.

This skill is the decision process for that. It does **not** replace
`coga skill` — the CLI (`install-url`, `status`, `update`) is the *mechanism*
that copies files and records provenance. This is the *judgment* layer that
sits on top: should you import at all, and which way.

## When this fires

Do **not** trawl registries speculatively. The trigger is a concrete gap:

- A workflow step references a `skill:` that doesn't exist yet, **or**
- The ticket interview surfaces a recurring process need with no skill behind
  it (the `bootstrap/ticket` step-4 "create missing skill" moment).

At that point — before writing a local skill — run the check below. If no
gap exists, there is nothing to import.

## The decision: import, adapt, or write

Work top to bottom; stop at the first that fits.

1. **Import (unchanged)** — an external skill covers the need closely, its
   process matches how this repo works, and it has no hard-coded commands or
   paths that don't apply here. Install it as-is and record provenance.
2. **Adapt** — a good external skill is *most* of what you need but has
   repo-specific friction (a wrong test command, an assumed directory layout,
   an extra workflow phase you don't run). Import it, then make the smallest
   local edit that fixes the friction, and record *why* in the provenance
   notes. Adaptation is a fork you are choosing to maintain — keep it minimal.
3. **Write local** — nothing external fits, or the only candidates are broad
   "do everything" skills whose real value is one paragraph. Write a small
   focused skill under `coga-os/skills/<ns>/<name>/` per `bootstrap/ticket`
   step 4. No provenance file — it's original.

When import and write are close, prefer **import**: a skill with provenance is
one a future `coga skill update` can refresh against upstream; a hand-written
twin of an upstream skill is drift you now own forever.

## Finding a candidate

Build the query from the task domain plus the missing capability — not a vague
keyword. "pytest failure-reporting SKILL.md", "changelog generation skill",
"release-notes agent skill". Then look where SKILL.md files actually live:

- The OpenClaw / ClawHub skills registry and community indexes
  (e.g. `openclaw/agent-skills`, VoltAgent's awesome-skills list).
- GitHub code search for `path:SKILL.md` plus your domain terms.
- Any source the human points you at.

Read the candidate's `SKILL.md` before proposing it. A skill is only worth
importing if its *body* — the actual process — is what you need, not just its
title.

## Recording provenance — use the existing mechanism

Provenance is **not** a markdown block you write by hand. `coga skill
install-url <url> [path-inside-archive]` installs the skill as a plain
directory and writes a `.coga-source.json` (`schema: coga.skill-source.v1`)
beside its `SKILL.md`. That file is the provenance record. Its fields:

- `source_url` — where it came from (the upstream URL / repo).
- `selector` — the path inside the source when it holds more than one skill.
- `installed_ref` — the ref/version installed.
- `installed_at` / `updated_at` — import and last-update dates.
- `source_digest` / `source_tree_digest` / `installed_tree_digest` — content
  hashes that let `coga skill status` and `coga skill update` tell a clean
  import from a local adaptation and detect upstream changes.
- `local_adaptation_notes` — **hand-edit this.** When you adapt (decision 2),
  write one or two lines: *what* you changed and *why*. This is the field a
  future human reads to understand the fork; `coga skill update` preserves it
  across clean updates and refuses to silently overwrite an adapted skill
  without `--force`.

Together those fields satisfy a ticket's provenance requirement — source URL,
upstream repo, import date, local changes (the digests), and reason for
adaptation (the notes) — without inventing a parallel scheme. Do not duplicate
them into the `SKILL.md` body.

## Where imported skills live

Imported and adapted skills are ordinary project-local skills:
`coga-os/skills/<namespace>/<name>/`, resolved before the bundled batteries
like every other local skill. They stay plain directories — no package cache,
no hidden service owns them — so the `.coga-source.json` sitting beside the
`SKILL.md` is the *only* thing marking them as imported. Bundled
package-backed skills under `bootstrap/skills/` are not an import target; those
ship with Coga.

## Don't import broad skills blindly

The most common mistake is pulling a large, popular skill for the one useful
paragraph inside it. Reject a candidate when:

- It hard-codes commands, paths, or tool names that don't match this repo (a
  fixed `npm test` when the repo is Python, an assumed CI provider).
- It drags in a whole workflow or extra phases the ticket doesn't run.
- Its real value is a small idea wrapped in a lot of scaffolding — copy the
  idea into a small local skill instead and skip the import.

Small surface, sharp behavior. An import should *reduce* what this repo has to
maintain, not add a dependency that fights it.

## Worked example — a dev unit-testing skill

A ticket needs a "run the unit tests and report failures clearly" step, and no
local skill covers it.

1. **Gap detected** — the workflow step has no `skill:` for it.
2. **Search** — "unit test runner failure-reporting SKILL.md" turns up a few
   candidates (e.g. a generic `test` runner skill, an "update unit tests"
   workflow skill).
3. **Read them** — one is a clean, low-scaffolding test-runner with good
   failure reporting; another bakes in a `jest` command this Python repo can't
   use.
4. **Decide** — import the clean one; reject the `jest` one (broad + wrong
   command). The clean one assumes `pytest -q` but the repo runs
   `python -m pytest` → **adapt**: `coga skill install-url <url>`, change the
   one command line, and set `local_adaptation_notes` to
   `"swapped pytest invocation to python -m pytest for this repo"`.
5. **Wire it** — add the skill ref to the workflow step (or note it on the
   ticket body for the human to wire, per `bootstrap/ticket`).

The result: a maintained import with a one-line record of exactly what was
changed and why — refreshable later, and legible to the next human.
