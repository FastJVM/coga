# Blackboard — fail-loud-when-an-env-indirected-secret-is-missing

## Dev

- branch: `scoped-secrets`
- worktree: `../relay-scoped-secrets` (i.e. `/home/n/Code/claude/relay-scoped-secrets`)
- commit: `37b935e` (committed, not pushed — open-pr step does that)

## Implementation (claude, 2026-06-17)

All blackboard decisions honored. Single commit on `scoped-secrets`.

**Data model (the load-bearing change).** `cfg.secrets` is now
`dict[str, SecretValue]` (new frozen dataclass: `raw`, `env_var`, `value`).
`_resolve_secrets` keeps provenance — an `env:VAR` whose var is unset resolves
to `value=None`, kept distinct from an empty literal (`value == ""`). The old
`os.environ.get(VAR, "")` footgun is gone. `_resolve_secret_value` is left as-is
(still string-returning) but is now used *only* by the slack webhook path; its
docstring is corrected. Only 5 sites consumed `cfg.secrets`, so the blast radius
was contained.

**Chokepoint + three-way semantics.** New `config.select_launch_secrets(cfg,
declared)` + `SecretError`:
- `declared is None` (absent/null) → legacy blanket, minus any unset env: secret
  (never injected as "").
- `declared == []` → strict, inject nothing. (Distinguished from None — no
  `or []` collapse. `Ticket.secrets` returns the raw value for the same reason.)
- non-empty list → least privilege; `SecretError` on undeclared key or unset
  env var, message names both key + env var.
- non-list / non-string entries → `SecretError` (defensive; validate also errors).

**Inject sites.** `launch.py` (agent) and `launch_script.py` (script — folded in,
NOT dropped) both call the helper and `_bail` on `SecretError`. Blanket inject
stripped from `ticket.py` / `delete.py` / `project.py` — verified each: authoring,
planning, and task-dir deletion run no task work and need no secrets.

**Registrations.** `secrets` added to `ticket.CANONICAL_TICKET_KEYS`,
`config._RESERVED_TICKET_FIELD_NAMES`, and `validate.OPTIONAL_TASK_KEYS` (NOT
required). `validate._check_secrets`: shape error (must be null or list of
strings) + warns (undeclared key / unset env var). Templates: `secrets: null`
documented in both `_template/ticket.md` copies (live + packaged). No example
`_template` exists, nothing to sync there.

**Tests.** `python -m pytest` → 768 passed, 1 skipped (note: system `python` is
3.9; run with `python3.12`). `relay validate --json` on `example/relay-os` →
clean. New coverage: config (provenance + all 3 select_launch_secrets cases +
fail-loud), launch + launch_script (fail-loud no-spawn + least-privilege
integration), validate (shape error + both warns).

**Out of scope.** The `extra_local` typo-warn is **split to a follow-up**
(confirmed by nick at implement time, reversing the earlier "bundle" note — both
evaluators had recommended splitting; it touches a different config layer and
needs its own precise enumeration of valid `relay.local.toml` keys). NOT done
here. → needs a new draft ticket (e.g. `warn-on-unknown-relay-local-keys`).
The query/retrieve-on-demand capability remains the separate
`add-a-way-to-query-a-declared-secret-on-demand` ticket.

## Bootstrap decisions (nick + claude, 2026-06-17)

- **Premise confirmed.** `config.py:850` `os.environ.get(VAR, "")` → unset env
  var becomes `""`; `launch.py:325` `env.update(cfg.secrets)` injects it. The
  docstrings (`config.py:843`, `857`) claim launch-time validation that does
  not exist. Real footgun (e.g. typo `env:STRPE_KEY` → silent empty secret).

- **Scoping problem.** One global `[secrets]` table, blanket-injected by every
  launch path. No per-task notion of "needed" secrets. A naive "fail if any
  declared env:VAR unset" over-blocks multi-project shells.

- **Decision (nick):** add a **nullable per-ticket `secrets:` frontmatter
  field** listing the secret *keys* a task requires. Human accepts/enforces it
  deliberately. Launch enforces only the listed keys. `null`/`[]` = none.

- **Independent of the list:** stop silent empty-string injection globally
  (distinguish unset vs empty literal); fix misleading docstrings.

- **validate:** warn (not error — env is per-shell) on declared secrets whose
  env vars are unset or whose keys aren't in `[secrets]`.

- **Secondary:** `extra_local` (`config.py:225`) typo warn in the same pass.

- **Workflow:** `code/with-review`. **Assignee:** `claude`.

### Open question for implementer
Which launch paths enforce the hard-fail? `launch.py` is the agent-spawning
one named in acceptance. `launch_script.py`, `ticket.py`, `delete.py`,
`project.py` also blanket-inject — they may warrant the same guard or just the
empty-string fix. Implementer to decide and note rationale.

### Migration note
Existing tickets have no `secrets:` field. Loading must treat absent/null as
"no required secrets" (no break). Verify the ticket model + validate tolerate
the missing key.

## Scope expansion + split (nick, 2026-06-17)

nick reframed: this is 3 capabilities, not one.
1. Declare — the `secrets:` field.
2. Least-privilege injection ("don't ask more") — inject only declared secrets.
3. Query a secret on demand — retrieval CLI/helper.

Decision: **2 tickets.** Fold 1+2 into THIS ticket (retitled "Scope secret
injection to declared per-task secrets and fail loud on missing"). Split 3 →
new draft `add-a-way-to-query-a-declared-secret-on-demand` (workflow-less
concept-capture, shape TBD — nick "not sure yet" between CLI / helper / both).

**Backward-compat decision baked in (nick to confirm):** opt-in least-privilege.
Absent/null `secrets:` = legacy blanket-inject (no breakage) + empty-string fix;
declared list = strict least-privilege (inject only listed, fail-loud on
missing). Avoids breaking existing tasks that rely on ambient undeclared
secrets. Future ticket can flip default to strict.

## Evaluator review

(Independent cold read, general-purpose subagent, 2026-06-17 — verbatim.)

## Review: `fail-loud-when-an-env-indirected-secret-is-missing`

**Premise is real and correctly diagnosed.** I verified the code. `_resolve_secret_value` (config.py:850) does `os.environ.get(VAR, "")`, and every launch path blanket-injects via `env.update(cfg.secrets)` — confirmed in launch.py:325, launch_script.py:131, ticket.py:173, delete.py:62, project.py:106. The docstrings at config.py:843-844 and 857-858 do claim "validated at launch time when needed," and no such validation exists. The footgun and the misleading-comment claims are accurate.

**Clarity for a cold-start agent: good.** The ticket is unusually self-contained — problem, why it matters (fail-loud principle), the over-blocking trap ("fail-loud must not become fail-annoying"), the human-decided resolution, and a numbered fix list with concrete file/line pointers and an acceptance test. An agent could start immediately.

**Line-number drift (minor, but will mislead).** Several cited lines are stale:
- "`config.py:435`" for the `os.environ.get(VAR, "")` line — it's actually **config.py:850**. (The body later cites the correct `840-865` range, so it's internally inconsistent.)
- "`launch.py:259-260`" for the inject — it's actually **launch.py:324-325** (the Context section gets this right at :325).
- The pointers in the **Context** section are accurate; the **Description** section's line numbers are stale. An agent should trust grep over either.

**Workflow `code/with-review` fits.** This is a real code change touching a security-sensitive path with cross-cutting effects (5 inject sites, two templates, validate, config). Peer review is warranted; the choice is appropriate, not overkill.

**Scope is reasonable but on the larger side — it is effectively 3-4 coordinated changes, not one.** New frontmatter field + schema/template registration; hard-fail at launch; stop silent empty-string injection; validate warn. These are tightly coupled around one concern, so bundling is defensible, but it is not a one-liner and the reviewer should expect a sizeable diff. Item 3 (stop empty-string injection) is genuinely independent of the list and is the part that fixes the footgun even for tickets with no `secrets:` field — worth landing even if the field design slips.

**`secrets:` field design — mostly sound, with one registration gap to flag:**
- The ticket says register in `_RESERVED_TICKET_FIELD_NAMES` (config.py:364) **and** "validate's optional task keys." These are **two separate constants in two files**: config.py's `_RESERVED_TICKET_FIELD_NAMES` (collision guard for repo extensions) and validate.py's `OPTIONAL_TASK_KEYS` (config.py:364 vs validate.py:79). The ticket gestures at both but an agent could easily update only the one whose line number is given (config.py:364). **Both must change**, and `secrets:` must go in `OPTIONAL_TASK_KEYS`, not `REQUIRED_TASK_KEYS` — otherwise every existing ticket fails validation. The ticket does not name validate.py:79 explicitly; this is the most likely thing to be missed.
- **Migration / missing-field safety: confirmed safe, but verify, don't assume.** `_check_frontmatter_schema` treats any unlisted key as `orphan-extension`, and required keys missing as errors. Putting `secrets:` in `OPTIONAL_TASK_KEYS` means existing tickets that lack it stay valid. The launch enforcement must read `ticket.frontmatter.get("secrets")` and treat absent/`None`/`[]` identically as "enforce nothing" — the ticket says this for null/[] but does not explicitly cover the *absent* key. An agent should treat absent == null. If launch code ever does `for k in ticket.secrets:` without a None-guard, a missing/null field will raise `TypeError` and break launching every legacy ticket. This is the main latent gap to call out.
- The templates both carry `workflow: null` already, so adding `secrets:` (likely `secrets: []` or `secrets: null`) to both is mechanical; both files confirmed in sync today.

**Assumptions worth questioning before launch:**
- **"Only launch enforces; others may warrant the same guard."** The ticket explicitly punts on launch_script/ticket/delete/project. That is a deliberate ambiguity ("decide which paths enforce") — fine for an interactive ticket, but it means item 3's empty-string fix changes behavior for all 5 paths regardless, while the hard-fail (item 2) is scoped to launch. The reviewer should confirm that non-launch paths don't *rely* on the current empty-string injection for some secret (e.g. project.py spawning something that tolerates a blank). Low risk, but it is a behavior change to 4 unmentioned call sites.
- **`secrets:` is a list of keys under `[secrets]`, validated against `[secrets]` presence + env-var-set.** Sound. One edge: a key declared in `[secrets]` with a *literal* (non-`env:`) value can't be "unset" — enforcement must only hard-fail on the `env:`-indirected-but-unset case, and treat "key absent from `[secrets]` entirely" as a separate named error. The ticket's item 2 wording covers both ("not declared… or its env:VAR points at an unset env var"). Good, just make sure the two error messages are distinct.
- The `extra_local` typo-warn (config.py:225) is tacked on at the end ("worth a warn in the same pass"). This is genuinely a *separate* ticket — different config layer (local.toml unknown keys), different surface. Bundling it here would inflate scope and dilute the focused security fix. Recommend dropping it from this ticket or splitting it out.

**Bottom line:** Premise verified, design sound, safe to launch. Two things to fix/flag before or during work: (1) the stale line numbers in the Description, and (2) the dual-registration requirement — `secrets:` must be added to validate.py's `OPTIONAL_TASK_KEYS` (line 79), not only config.py's reserved set, and launch enforcement must treat an absent/null `secrets:` field as "enforce nothing" to avoid breaking every existing ticket. Consider de-scoping the `extra_local` warn into its own ticket.

## Decisions after second-pass review (nick, 2026-06-17)

- **`secrets: []` semantics:** explicit `[]` = STRICT, inject nothing
  (deliberate lockdown). absent/null = legacy blanket-inject. non-empty list =
  only those keys. `[]` ≠ null — implementer must NOT collapse via
  `get("secrets") or []` for the injection-mode branch.
- **Inject sites:** `relay launch` is the ONLY place secrets are injected.
  Strip blanket inject from launch_script/ticket/delete/project. RISK:
  launch_script.py:74 documents script-mode secret env vars — fold script-mode
  delivery into the launch chokepoint, don't silently drop it.
- **Provenance:** baked into item 3 — `cfg.secrets` loses the env:VAR ref +
  unset/empty distinction at load (config.py:223); this is a data-model change,
  not a one-liner.
- **Field shape:** validate that `secrets:` is a list of strings (error on
  scalar/non-string) — registration alone doesn't type it.
- Scope still bundled per nick's earlier call (incl. extra_local warn).

## Evaluator review — second pass (after scope expansion)

(Independent cold read, general-purpose subagent, 2026-06-17 — verbatim.)

**Second-pass cold read: `fail-loud-when-an-env-indirected-secret-is-missing`**

Code pointers in the ticket are accurate (config.py:850 footgun, :364 reserved names, launch.py:325, validate.py optional keys at :79, all 5 inject sites confirmed: launch.py:325, launch_script.py:131, ticket.py:173, delete.py:62, project.py:106). The ticket is well-written and self-aware about drift. The expansion is mostly coherent, but the second pass surfaces several real issues.

**1. The opt-in backward-compat model is coherent — but it quietly relocates where resolution must happen, and the ticket never says so.**
`cfg.secrets` is resolved eagerly at config-load (config.py:223 `_resolve_secrets`). By the time any inject site or fail-loud check runs, the `env:VAR` reference is **already gone** — it's a flat `{key: ""}` dict, with unset vars already collapsed to `""`. Item 2's fail-loud ("name the missing env var") and item 4's validate-warn both need to know *which env var* a key pointed at and *whether it was unset vs empty literal*. That information is destroyed at load time. So the real implementation either (a) stops resolving eagerly and carries raw refs forward, or (b) has `_resolve_secrets` retain provenance (e.g., a sentinel/`None` for unset, plus the original var name). The ticket gestures at "distinguish unset from empty literal in `_resolve_secret_value`/`_resolve_secrets`" but treats it as a local in-function fix; it is actually a **data-model change to `cfg.secrets`** that ripples to every consumer. This is the biggest under-specified item and the most likely source of a half-done PR.

**2. Empty-string fix vs least-privilege interact correctly in principle, but "which of the 5 sites change" is explicitly left undecided — and that's a gap, not a deferral.**
Item 3 is stated as "independent of the list" and the empty-string drop happens inside `_resolve_secrets`, which feeds all 5 sites — so all 5 automatically stop injecting `""` for free. Good. But least-privilege (item 0) only names `launch`. The ticket says the other four "may warrant the same guard" and "decide which paths enforce." For a security/least-privilege ticket, leaving 4 of 5 injection sites as blanket-inject is a coherence hole: a ticket that declares `secrets: [STRIPE_KEY]` would get least-privilege at `relay launch` but full blanket-inject at `launch_script`/`ticket`/`delete`/`project`. That's a confusing, leaky least-privilege guarantee. Acceptance only covers launch, so a PR could legitimately ship the leak. This should be **decided in the ticket**, not in the PR.

**3. No contradiction in the "absent==null==[]" rule — it's stated consistently** (lines 51-61, 84-87, and the `get("secrets") or []` defensive guidance). This part is clean. One subtle edge though: `secrets: []` (explicitly empty list) is folded into "needs none" in item 1 ("`null`/`[]` means the task needs none"), but under strict least-privilege an explicit `[]` arguably should mean "inject nothing" (strict), whereas absent/null means "blanket-inject" (legacy). The ticket collapses `[]` and `null` to the *same* legacy-blanket behavior via `get("secrets") or []` — which means a deliberately-empty `secrets: []` still gets blanket-inject, the opposite of least-privilege intent. That's a genuine latent contradiction between "the field is opt-in to least-privilege" and "`[] == null == blanket." Worth an explicit call: does `secrets: []` mean "inject nothing" or "inject everything"? The defensive idiom silently picks "everything."

**4. Scope: borderline-too-big, and one clean split is available.** Three coupled items (field + least-privilege + fail-loud/empty-string) plus template sync plus validate-warn plus the `extra_local` typo-warn aside. Items 3 (empty-string drop) and 4 (validate warn for unset env) are the core safety fix and are self-contained. Item 0 (least-privilege scoping across N inject sites) is the heavier, riskier piece and depends on the data-model change in #1. A reasonable split: **PR-A** = empty-string fail-loud fix + `_resolve_secrets` provenance change (the actual security bug, item 3, applies to all sites today). **PR-B** = the `secrets:` frontmatter field + least-privilege scoping + validate-warn. As written it's shippable as one PR but the blast radius (config data model + 5 call sites + 2 schema registries + 2 templates + validate) is large for one review.

**5. Smaller gaps:**
- The `extra_local` typo-warn (closing paragraph) is a 6th, unrelated concern bolted on — it touches neither secrets injection nor the field. Drop it or split it; it inflates scope with no acceptance coverage.
- Item 1 requires registering in *both* `_RESERVED_TICKET_FIELD_NAMES` and `OPTIONAL_TASK_KEYS` — correct and well-flagged. But note `_RESERVED_TICKET_FIELD_NAMES` is a *collision guard for extensions*, not a parser allowlist; the ticket should confirm whether `secrets` also needs to be parsed/typed somewhere as a real list (the frontmatter is otherwise free-form). Right now nothing validates that `secrets:` is a *list of strings* vs a scalar — item 4 should add that type check, and it currently doesn't mention it.
- Acceptance says "the new `secrets:` field is validated" but the only validate behavior specified (item 4) is a **warn** for unset env. There's no specified validation that the field's *shape* is correct or that listed keys exist in `[secrets]` as an error. "Validated" is vague against the actual specified behavior (warn-only). Tighten the acceptance wording.

**Net:** No fatal contradiction, and the backward-compat model is sound. The two things I'd block on before implementation: (a) make explicit that `cfg.secrets` loses provenance at load and item 3 is a data-model change, not a one-liner; (b) decide the `[] == null` semantics and which of the 5 inject sites enforce least-privilege — leaving both to the PR invites a half-correct, leaky implementation.
