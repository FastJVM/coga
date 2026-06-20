# Blackboard — readme-and-docs

## Design step (2026-06-20) — verification log

The ticket arrived already carrying a full spec (Description / AC / Proposed
Shape / Out of Scope / Decisions). The design step's job here was to verify
that spec against real CLI behavior, refine the gaps, and surface decisions —
not author from scratch. All claims were ground-truthed against the
`~/Desktop/relay-cli` checkout (the `relay` on PATH runs this source).

Confirmed real / accurate:

- `relay init --user <name>` — required for a fresh init (`relay init --help`).
  Seeds `tasks/relay-build/` onboarding ticket, stamps `new-user` →
  `<name>` on owner/human/assignee, prunes it on a non-empty repo
  (`src/relay/commands/init.py`, `_ONBOARDING_TICKET_DIRS = ("relay-build",)`).
- `relay build` = alias → `relay launch relay-build` (`relay.toml` `[aliases]`).
  Launches the `build/onboarding` workflow (`gather-and-spec` →
  `generate-batch`): one scripted question → agent chat → vision written to
  `contexts/product/vision/SKILL.md` + a batch of draft tickets → `relay launch
  <slug>`. So `init --user → build → launch` does land a newcomer on a
  launchable ticket — the stated Win holds.
- `relay digest` exists (flags `--quiet-empty` / `--announce-empty`); no README
  entry today. `relay validate` exists (`--json`, `--task`, `--fix`,
  `--idle-hours`, `--max-blackboard-kb`, `--check-slack`, `--check-github`);
  also no dedicated README entry.
- License = `AGPL-3.0-or-later` (`pyproject.toml`, `LICENSE` present).
- vision.md stale items at the specced lines: repo URL `relay-dev/relay` (L14),
  "six-command CLI" (L22), `[FILL IN WITH REAL NUMBERS]` (L246).
- README stale items: hand-edit `user =` / `relay ticket "First task"` block
  (L133-139); `gh skill` "once those commands land" (L100) — contradicted by
  the README's own `### relay skill` section, which treats `gh skill` as a
  shipped public preview.

## Resolved questions (answered by zach, in-session)

1. **Install duplication.** `## Development` (L772-781) also has `git clone` +
   `pip install -e .`, so "one source of install truth" was not fully covered.
   → **Decision: Dev references Getting Started**, keeps only dev-only commands.
   Folded into AC + Proposed Shape item 3.
2. **Three onboarding narratives.** Getting Started (`init→build→launch`) vs the
   existing `## Task lifecycle` path and `relay ticket` "usual boot sequence",
   both centered on `relay ticket`.
   → **Decision: light cross-reference** — one line distinguishing them; do not
   rewrite those sections. Folded into AC + Proposed Shape item 2.

No open questions remain. Spec is ready for `review-design`.

## Clean-room test of Getting Started (2026-06-20)

Ran the Getting Started happy path in an isolated clean-room (fresh `git clone`
+ a brand-new venv + `pip install -e .`, then a fresh `git init` project with a
throwaway local remote — never the real GitHub/Slack). Reusable harness lives at
`/tmp/relay-cleanroom/` (`setup.sh` rebuilds the install layer; `reset.sh` wipes
the project back to pristine for another run). Install (`relay 0.2.0`),
`relay init --user`, and the `build`/`launch` wiring (`--prompt-report`) all pass.
Four findings surfaced — flagged by whether they're in-scope **doc** edits or
sibling-ticket **code** bugs:

1. **`git init` → `master`, but relay syncs to `main` (highest impact).** Step 2's
   plain `git init` makes a `master` branch (machine default); `[git].control_branch`
   defaults to `main`, so every mutating command fails its sync but still exits 0:
   `relay create … → [git] sync failed: 'git fetch origin main' (exit 128): couldn't
   find remote ref main`. Work stays local, never reaches the remote — easy to miss.
   Dents the AC ("newcomer reaches a launchable ticket"). **Doc:** change step 2 to
   `git init -b main`. **Code (sibling):** relay should detect the repo's branch.
2. **`relay init` prints 5 managed-skill failures.** `Managed skills: failed=5,
   installed=7`; all 404 against `FastJVM/relay-skills` (repo doesn't resolve), e.g.
   `relay/gmail`, `relay/google-calendar`, `browser/playwright`. Fires for everyone,
   not just "older gh". **Doc:** the new `## External CLI Tools` line ("a fresh
   `relay init` on an older `gh` just skips them with a warning") misattributes the
   cause and undersells the noise — retarget it. **Code:** `quiet-relay-init-managed-skill-failures`.
3. **A `browser-automation` draft ships in the templates.** Every fresh init seeds
   it (+ browser contexts + a workflow) under `resources/templates/relay-os/tasks/`,
   so `relay status` shows a ticket the newcomer never authored — before `build`
   even runs. Muddies "launch your first ticket — which slug?". **Doc (optional):**
   "What you end up with" implies the drafts come from `relay build`. **Code:** remove
   the example from templates.
4. **`relay --version` errors inside the cloned source repo (low).** Natural
   post-install check while still `cd`'d in `relay/`: `'user' is missing from
   …/relay.local.toml` (a gitignored file that isn't there). Works from any
   non-`relay-os/` dir. Happy path dodges it (step 2 moves away). Minor; likely no
   doc change.
