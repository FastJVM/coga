# Blackboard — fail-loud-when-an-env-indirected-secret-is-missing

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
