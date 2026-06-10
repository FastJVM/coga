## Dev
branch: codex/init-managed-skills
worktree: /tmp/relay-init-managed-skills
pr: https://github.com/FastJVM/relay/pull/334

## Open PR (2026-06-10)

Opened PR: https://github.com/FastJVM/relay/pull/334

CI: `gh pr checks 334` reports no checks reported on the
`codex/init-managed-skills` branch.

## Peer review (2026-06-10)

Reviewed branch diff vs `main` with `/code-review` (default effort). Ran 2
correctness angles (line-by-line + cross-file) plus a removed-behavior auditor
and a cleanup/altitude angle, then verified candidates.

**Correctness: clean.** No bugs. All `managed_skills.py` calls into
`skill_manager` match real signatures; every `_UpdateResult` construction site
includes the new `managed_skills` field; required/optional failure propagation
is sound; fresh `relay init` still works offline (optional skills `required=false`
soft-fail). Removed-behavior findings (gmail/gcal pip deps + deleted skill tests
gone) are by-design tradeoffs of moving those skills to optional manifest installs.

**Two cleanups applied** (commit `5f677a8`), both matching anti-patterns the repo
contexts call out:
- Reuse `skill_manager._skill_target`/`_safe_skill_ref` instead of a byte-for-byte
  duplicate of the path-traversal validator in `managed_skills.py`. (Side effect:
  invalid-ref now raises `SkillManagerError` not `ManagedSkillError`; uncovered
  internal manifest-integrity path, acceptable.)
- Dropped the unused `url_installer` injectable seam (no test/caller passed it;
  `github_installer`/`updater` are used by tests, `url_installer` was dead —
  `relay/project-stage` forbids abstraction-for-future-use). `install_url_skill`
  already accepts `runner`/`downloader` for testing.

Verification after cleanup (venv py3.12, `PYTHONPATH=src`):
- `pytest tests/test_managed_skills.py tests/test_init.py tests/test_packaging.py` — 77 passed.
- `python -m pytest` — 627 passed (packaging test now runs, not skipped).

Decision (human, interactive): apply both cleanups. Carried over to commit above.

## Implementation Notes

Committed implementation at `5e16521` on `codex/init-managed-skills`.

What changed:
- Added `src/relay/managed_skills.py` plus `src/relay/resources/managed-skills.toml`.
- Fresh `relay init` now runs the managed-skill installer after template scaffold and before venv dependency installation, so installed optional skill requirements can be picked up.
- `relay init --update` reconciles manifest-listed managed skills one by one; source checkouts skip this reconciliation and only refresh gitignored bootstrap/recurring mirrors.
- Optional domain skills were removed from packaged template payloads. Package-backed bootstrap now keeps only core/control-plane batteries; optional domain skills are manifest-installed into `relay-os/skills/`.
- `skills/relay/calendar-reminder` is no longer pruned as obsolete, because optional Relay-owned skills now live under `relay-os/skills/`.
- Relay architecture/codebase contexts were updated to describe the two-tier model.

Verification:
- `python -m pytest tests/test_managed_skills.py tests/test_init.py tests/test_packaging.py` — passed, 76 passed / 1 skipped.
- `python -m pytest` — passed, 626 passed / 1 skipped.
- `relay validate --task install-init-skills-via-skill-downloader --json` from the primary checkout — passed.

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

## Installer audit (2026-06-10, code-level)

Audited `src/relay/skill_manager.py` (1178 lines) + `src/relay/commands/skill.py`.

**Three install paths — only one is provenance-tracked:**

| Path | Mechanism | Writes `.relay-source.json`? | Reconciled by status/update? |
|------|-----------|------------------------------|------------------------------|
| `install_github_skill` | `gh skill install <owner/repo> [skill] --dir skills/` | No | Opaque — delegated to `gh skill update --all` |
| `install_local_skill`  | `gh skill install <path> --from-local` | No | No — shows `unmanaged`/`delegated` |
| `install_url_skill`    | download bytes → materialize zip/tar/SKILL.md → install `--from-local` → write metadata | **Yes** (`relay.skill-source.v1`, digests) | **Yes** — full digest reconciliation |

- The **url path is the only one** that satisfies the ticket's "records
  provenance/update metadata" + "locally adapted skills preserved" criteria. It
  tracks `installed_tree_digest` vs `source_tree_digest`, detects local
  adaptations + upstream changes, flags conflicts, and refuses to overwrite a
  locally-adapted skill without `--force` (`skill_manager.py:175-181, 886-904`).
- **All three paths call `gh skill` (subprocess).** `ensure_gh_skill` requires
  `gh` 2.90+ with the `skill` extension — even the url path (installs the
  downloaded tree via `--from-local`). So consuming the installer makes `gh` a
  hard prerequisite of whatever calls it.
- `skills_root(cfg)` is hardcoded to `repo_root/skills` (`:87`) — the installer
  always writes to `relay-os/skills/`, never `bootstrap/skills/`.
- `relay skill` has **no search**. Discovery exists one layer down in the wrapped
  tool: `gh skill search <q>`, `gh skill preview`, `gh skill publish`.

## Resolved design: two-tier model (preinstalled + grabbed-from-repo)

Human direction (2026-06-10): keep core skills preinstalled as today, grab the
rest from a repo. This resolves all three blockers. Concrete split from the
on-disk inventory:

**Tier 1 — preinstalled (stay bundled in `bootstrap/skills/`, package-backed,
no network, no `gh`).** Relay's own machinery depends on these; init must produce
them offline:
- `bootstrap/ticket`, `bootstrap/delete-task`
- `bootstrap/dream/tasks/{validate-drift, skill-update, cleanup-orphan-markers}`
- `retro/done-ticket`, `eval/ticket-diagnostic`

**Tier 2 — grabbed from repo (installer path, lands in `relay-os/skills/`,
optional → fetch failure warns, not fatal).** Domain skills nothing in the core
loop needs:
- `google-agents-cli-*` (7), `relay/gmail`, `relay/google-calendar`,
  `relay/calendar-reminder`, `browser/dochub`, `browser/playwright`

Why it works: Tier 1 needs no network/`gh`; only optional Tier 2 does, and it
fails soft → init still produces a working repo offline. Only the ~12 Tier-2
skills must be published, not the whole set. No skill in both roots → path
collision gone.

**Recommended grab mechanism: github path** (`gh skill install
github/<relay-skills-repo>`). It's what `gh skill` is built for (search/publish/
update lifecycle) and shrinks the manifest to `(repo, skill, required=false)` per
entry. Cost: github installs get gh-native metadata, not `.relay-source.json`, so
`relay skill status` shows them `delegated`. → Acceptance criterion #2 must soften
to "provenance via the installer's source metadata (gh-native OR `.relay-source.json`)".
Alternative: url-tarball path for full Relay provenance, but needs published
release artifacts + URLs in the manifest.

## Punch list — what's missing

This ticket builds:
1. **init→installer wiring** (the core; 0% done). `init`/`init --update` only
   `copy_fresh_templates`/`refresh_templates` today — never touch `skill_manager`.
   Need: after scaffold, drive the manifest through `install_github_skill`
   (or url); on `--update`, run `update_skills` reconciliation.
2. **The manifest.** No `skills.toml` / declarative list exists. Need a small
   `(repo/url, skill, required)` file.
3. **Stop copying Tier-2 from templates** so install is the sole source (remove
   the Tier-2 set from the template/bundle copy path + delete those template
   files), else double-provisioning.
4. **Init output + soft-fail policy.** Report installed/updated/skipped counts
   separately from copied scaffolding; classify failures by manifest `required`
   (required → fail loud with source + remediation; optional → warn).
5. **Test seams.** Installer already accepts injectable `runner`/`downloader`;
   init has no path to thread them down. Required for offline tests.

Prerequisite — arguably its own ticket, this one depends on it:
6. **Publish the Tier-2 skills somewhere fetchable.** They live only inside the
   pip package; nothing is in a GitHub repo, so `relay skill install github/...`
   has nothing to point at and the integration can't be tested against anything
   real. Needs `gh skill publish` to a repo first. **Gating dependency.**

Open decision (blocks final spec, not code):
7. github-path vs url-tarball for Tier 2 (see above) — determines whether
   acceptance criterion #2 holds as written.

## Manifest / inventory state on disk

- **"What should be installed" (requirements/manifest): does not exist.** No
  `skills.toml`, no lockfile. (Note: the `requirements.txt` beside `relay/gmail`
  and `relay/google-calendar` are *Python pip deps* for those skills, installed
  into `.relay/.venv` — NOT a skill manifest. Don't conflate.)
- **"What is installed" (record): no central file.** Two partial mechanisms:
  per-skill `.relay-source.json` provenance (only for url-installs; **zero on
  disk today** — nothing url-installed yet), and `relay skill status` which
  *derives* the inventory live by walking `skills/` + `bootstrap/skills/`.
- Consider whether this ticket should also snapshot `relay skill status` to a
  tracked inventory file, or leave it derived.

## Pre-existing oddity worth a separate ticket

`relay skill status` today reports `google-agents-cli-*` as
`local-override (github) — shadows bundled package-backed skill`. They are
**already present in both `relay-os/skills/` and `bootstrap/skills/` at once**,
before any of this ticket's work — the de-duplication problem is live on disk
now. Worth investigating why they got double-materialized; may be a pre-existing
init/copy bug deserving its own ticket rather than silent cleanup here.
