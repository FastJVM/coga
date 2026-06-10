## Creation Notes

Created from bootstrap/orient after the user clarified that `relay init` should
not copy/paste Relay-owned skills from bundled templates once the skill
installer exists. Init should install/download skills through the same public
skill-management path so provenance and update metadata exist from day one.

Keep the boundary narrow: non-skill scaffolding can stay template-based; skill
directories should come from a manifest and installer/updater API.

## Evaluator review

(Independent cold read, 2026-06-10. Workflow `code/with-review` set and ticket
activated after this review. Two factual premises in the ticket are stale and at
least one design question is unresolved — see "Open question before impl".)

**1. Description clear enough to start cold?**
Mostly yes. Problem statement is sharp and well-motivated; "Required behavior" and
"Acceptance criteria" are unusually concrete and testable. Gap: the ticket never
names the actual install entry point (`install_url_skill` / `update_skills` in
`src/relay/skill_manager.py`), so an implementer must reverse-engineer which public
function init should call. Discoverable but should be stated.

**2. Workflow fit?**
`code/with-review` (implement → peer-review → open-pr → review) is the right shape
for a self-contained code change landed via PR. No mismatch. Sibling ticket
`add-bootstrap-skill-for-importing-external-skills` uses the same workflow — house
pattern for this kind of work.

**3. Contexts relevant? Missing?**
Attached set (`relay/architecture`, `relay/principles`, `relay/codebase`,
`relay/current-direction`, `relay/project-stage`, `dev/code`) all relevant;
`relay/codebase` + `dev/code` are load-bearing. Most important missing fact: name
the installer API directly in `## Context` — `src/relay/skill_manager.py`
(`install_url_skill`, `install_local_skill`, `install_github_skill`,
`update_skills`, `read/write_source_metadata`) and the init copy path in
`src/relay/commands/update.py` (`copy_fresh_templates`, `refresh_templates`,
`_copy_vendored_bootstrap`). Too specific to expect discovery via a broad context.

**4. Scope reasonable?**
Borderline-large but coherent — one feature with explicit Out-of-scope fencing. 7
acceptance criteria + 5 test scenarios are a lot but all facets of the same change.
Not multiple tickets; a meaty single ticket.

**5. Stale premises / assumptions to question:**
- **The "Proposed shape" does NOT match the tree.** Ticket proposes adding
  `src/relay/resources/skills.toml`. No such file exists, and `skill_manager.py`
  has no manifest concept — it installs imperatively (one `gh skill`/URL call per
  invocation) and records provenance per-skill in `.relay-source.json`. So this
  proposes a *new* abstraction the current installer doesn't consume. Confirm the
  manifest is wanted vs. a simpler hardcoded list.
- **Referenced sibling `wrap-gh-skill-for-relay-managed-skills` does not exist.**
  The installer it "waits for" already exists and is shipped (`skill_manager.py`,
  wired into `relay skill install/install-url/update`). Dependency framing is stale
  — not blocked; correct the narrative so nobody hunts for an unbuilt dependency.
- **Path-model mismatch.** Installer writes to `skills_root(cfg) = relay-os/skills/`,
  while Relay's bundled batteries live under `relay-os/bootstrap/skills/`
  (package-vendored, refreshed by `_copy_vendored_bootstrap`, read-only-ish). Real
  ambiguity about *which* skills move to install-on-demand: the `skills/` namespace
  ones or the `bootstrap/skills/` batteries. "Required Relay skills" most naturally
  means `bootstrap/skills/relay/*` + `bootstrap/skills/bootstrap/*` — but those are
  exactly what the bundled machinery ships offline-with-the-package. Converting them
  to network installs conflicts with the existing "bundled = package-backed, no
  network" model (`_bundled_status_result`). Deepest unresolved tension.

**6. Concrete risks the implementer will hit:**
- **No upstream source URLs exist for Relay-owned skills.** The manifest needs a
  source URL/repo/ref per skill, but Relay's own skills aren't published to any
  fetchable repo — they live in the package. "Install through the downloader" has
  nowhere to download *from* unless someone first publishes them, or the manifest
  points at local package paths (which is copying again under another name). Most
  likely to stall the work.
- **Offline test requirement vs. installer design.** `install_url_skill` /
  `update_skills` take injectable `downloader`/`runner` (fakeable), but
  `install_github_skill`/`install_local_skill` go through `gh skill` (subprocess,
  faked only via `runner`). Init has no concept of these injection seams today —
  non-trivial plumbing to thread them down.
- **`gh skill` hard dependency.** `ensure_gh_skill` needs `gh` 2.90+ with the
  `skill` extension. Making fresh `relay init` depend on that external CLI for
  required bootstrap skills is a real robustness regression (init needs no `gh`
  today).
- **Bundled-skill update semantics already conflict.** `update_skills(all)` already
  returns `skipped-bundled`/`package-backed` for bundled refs and routes URL-backed
  ones through `_update_url_skill_dir`. Init's `--update` must not double-handle or
  fight the existing bundled-vs-local-override logic.
- **Custom-skill preservation already load-bearing.** `copy_fresh_templates` does a
  full tree copy on fresh init; `_PRUNE`/`_OBSOLETE` in `update.py` already
  special-case `skills/bootstrap|retro|relay`. New install path must not reintroduce
  wholesale `skills/**` copying or drift from those lists.

**Bottom line:** Clear intent, good acceptance criteria, right workflow shape — but
two premises are stale (the "future" installer already exists; the proposed
`skills.toml` does not) and the central question (do Relay's bundled batteries
become network-installed skills, and *from where*, given they have no published
upstream URL) needs a decision before this is truly launchable.

## Open question before impl

The ticket assumes Relay-owned skills can be "downloaded." They currently ship
*inside the package* (`bootstrap/skills/`) with no published upstream URL. Before
real implementation, decide: (a) publish Relay skills to a fetchable repo and have
init install from there; (b) keep them package-backed but route provenance/metadata
through the installer code path without a network fetch; or (c) build the
`skills.toml` manifest pointing at local package paths. This is a design fork the
implementer cannot resolve alone — consider a `code/design-then-implement` pass or
a human decision before launch.
