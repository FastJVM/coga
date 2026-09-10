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
   focused skill under `coga/skills/<ns>/<name>/` per `bootstrap/ticket`
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

### Installing and pruning

`coga skill install-url <url> [path]` is the import path. Four things about how
it actually behaves, none of them obvious from the field list above:

- **`coga skill install` is not an import path.** The sibling command
  (`install_github_skill`) only shells out to `gh skill install … --dir
  coga/skills`. It writes no `.coga-source.json`, so `coga skill status` reports
  the result as `delegated (github) — managed by gh skill metadata`: no digests,
  and therefore no dirty detection and nothing for `coga skill update` to
  compare. The seven `google-agents-cli-*` skills are exactly that. Reach for it
  only when you deliberately want `gh` to own the skill; `install-local` has the
  same property. **Both require you to name the skill**, and coga always runs
  `gh` with captured output, so gh never gets to prompt interactively.

  What gh does when you omit the name is version-dependent, and both outcomes
  are bad — which is why the rule is "always pass it" rather than "gh will tell
  you". On gh 2.92 the documented contract is that `repository` and a skill
  name are *required* non-interactively, and gh refuses with "must specify a
  skill name when not running interactively"; coga translates that into a rerun
  hint (`_translate_gh_skill_error`). Newer gh has been reported to *list* the
  matching skills instead of refusing — and a successful listing is the failure
  mode to fear, because `install_github_skill` reads gh's zero exit as an
  install and you get no error, no rerun hint, and no skill. Do not rely on the
  refusal to catch a missing name.
- **Pruning is the normal case, not the exception.** The optional selector can
  only *descend* to a subdirectory that holds a `SKILL.md`; it cannot exclude
  siblings (`_select_skill_dir`). So when upstream keeps its `SKILL.md` at the
  archive root — the usual shape for a repo tarball whose whole point is one
  skill — the selector has nothing to narrow and the entire repository lands
  under `coga/skills/<name>/`: site, evals, commands, README/DESIGN prose, large
  sample assets, and any packaging check that asserts those paths exist. Keep
  `SKILL.md`, the `references/` the body loads by path, any `scripts/` a mode
  invokes, and `LICENSE` where the license requires attribution. Delete the rest
  and hand-write what you dropped, and why, into `local_adaptation_notes` — that
  is the record a future human and a future `coga skill update` read.
- **`locally-adapted (url)` is the expected status after a prune**, not a
  failure. `coga skill status` calls a URL skill locally adapted the moment the
  installed tree stops hashing to `installed_tree_digest` (`_status_url_skill`),
  and a prune is exactly that divergence. It is the protection working: `update`
  will not silently overwrite the skill without `--force`, and the notes explain
  why the tree is smaller than upstream. A clean import is not the better
  outcome; an honest one is.
- **The install auto-commits *and publishes* before you can prune.**
  `install-url` is in `_SWEEPING_SKILL_SUBCOMMANDS`, so coga's catch-all state
  sweep (`git.sync_coga_state`) commits the freshly landed tree as a `Sync coga
  state` commit on the way out — the unpruned bulk included. It does not stop
  at a local commit: `_dispatch_branch_sync` pushes when HEAD is the control
  branch, and from a feature branch it lands the same paths on the control
  branch anyway. **Squashing a feature-branch pair therefore does not help** —
  by the time you prune, the unpruned tree is already in control-branch
  history, and only a history rewrite would remove it.

  Decide which you want before you run the install:

  - **Accept it.** Prune in a following commit and let control history carry
    the bulk once. Fine for a few hundred KB; this is the normal path.
  - **Keep it out of history.** Do the `install-url` in a throwaway clone,
    prune there, then copy the pruned directory into the real repo and commit
    that once. This is the only way to keep the unpruned tree out of the
    control branch entirely.

## Where imported skills live

Imported and adapted skills are ordinary project-local skills, resolved before
the bundled batteries like every other local skill — but you do not pick where
one lands. `install-url` takes the destination from the *upstream* `SKILL.md`'s
frontmatter `name` (`_validated_url_skill_ref` validates it, `_skill_target`
joins it under `coga/skills/`), and an upstream skill carries a plain Agent
Skills name, so an import installs flat at `coga/skills/<name>/`. Every import
in this repo looks like that: `coga/skills/clarity/` and the seven
`coga/skills/google-agents-cli-*/`.

The slash-separated `coga/skills/<namespace>/<name>/` form is Coga's own
extension to the Agent Skills name. It is available to skills *you* write — the
namespaced trees here (`coga/skills/marketing/write-post/`,
`coga/skills/code/*`) are all locally authored, per `bootstrap/ticket` step 4 —
**and an import can land on it too**. `_validated_url_skill_ref` deliberately
accepts a slash-separated Coga namespace as well as a plain Agent Skills name,
and `_skill_target` then installs at the matching nested path, so an upstream
`SKILL.md` declaring `name: tools/example` lands at `coga/skills/tools/example`
(`test_install_url_downloads_local_installs_and_records_coga_metadata` pins
that case).

So do not assume a flat ref. **Read the upstream `name:` and wire workflows to
the ref it produces** — flat when upstream carries a plain Agent Skills name,
which is the common case and what every import in this repo happens to be,
nested when it carries a namespace.

They stay plain directories — no package cache, no hidden service owns them —
so the `.coga-source.json` sitting beside the `SKILL.md` is the *only* thing
marking them as imported. Bundled package-backed skills under
`bootstrap/skills/` are not an import target; those ship with Coga.

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
