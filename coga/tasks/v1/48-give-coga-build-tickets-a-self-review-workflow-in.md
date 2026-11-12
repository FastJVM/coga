---
title: Give coga build tickets a self-review workflow in one-agent repos
status: in_progress
owner: zach
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
  - name: review-design
    skills: []
    assignee: owner
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 5 (peer-review)
agent: claude
---

## Description

Coga ships three workflows with `other-agent` steps: `code/with-review`,
`code/design-then-implement`, and `docs/with-review`. In a repo where no peer
agent resolves (one declared agent, or three or more with no `peer =`) those
steps can never run. One-agent repos are now the norm on single-agent machines
(v1/20), yet `coga build` hands every starter implementation ticket
`code/design-then-implement` and Dream files `code/with-review` drafts.

Today the failure is also badly placed (verified 2026-11-11 in a scratch
one-agent repo):

- `coga create --workflow code/design-then-implement` writes the ticket and a
  `created` log line, *then* `assert_task_valid` fails on
  `unresolvable-step-assignee` for step 2 and the command exits non-zero. A
  half-created, unpublished ticket stays on disk.
- The `coga ticket` interviewer writes a bare `workflow:` name onto a draft;
  validation only sees `unfrozen-workflow` (a warning), so nothing objects
  until the ticket is started.
- `coga mark active` passes its pre-write check (it resolves only the current
  step), writes `status: active`, then post-write validation refuses: the file
  says `active` with no log line and no publication. Launch's grouped startup
  validates before writing and refuses cleanly; launch's non-grouped path
  (`_commit_auto_activate` → `mark_active`) has the same write-then-refuse bug.

The fix: refuse **before writing**, with a short message pointing at
`code/with-self-review`, wherever a ticket is created or activated with a
workflow whose `other-agent` steps cannot resolve; and have `coga build` and
Dream choose `code/with-self-review` up front through a new
`coga create --fallback-workflow` option, so the refusal is a backstop.
Peer workflows keep shipping unchanged, and two-agent repos see no change.

### Acceptance criteria

- [ ] In a one-agent repo, `coga create "<t>" --workflow code/design-then-implement`
      (likewise `code/with-review`, `docs/with-review`) exits non-zero with the
      one-agent refusal text below, and leaves no ticket file and no
      `coga/log.md` line.
- [ ] In a three-agent repo with no `peer =` on the default agent, the same
      create exits non-zero with the ambiguous-peer refusal text below, and
      writes nothing.
- [ ] In a two-agent repo, with or without `peer =`, those creates succeed
      exactly as today. A three-agent repo whose main agent declares `peer =`
      also succeeds.
- [ ] `coga create "<t>" --workflow code/design-then-implement --fallback-workflow code/with-self-review`:
      in a one-agent repo creates a `code/with-self-review` ticket and prints
      one line naming the substitution; in a two-agent repo creates a
      `code/design-then-implement` ticket and prints no extra line.
- [ ] If the fallback workflow is itself unresolvable, create refuses with
      the fallback's refusal text and does **not** print the substitution
      line. `--fallback-workflow` without `--workflow` exits 2 with a usage
      error and writes nothing.
- [ ] A directory-form create (`force_directory=True`, as recurring period
      tasks use) of an unresolvable peer workflow refuses with no residue: no
      task directory, no parent directories created by the attempt, no log
      line. After the config gains a peer, retrying the same create at the
      same slug succeeds (no `Task directory already exists`).
- [ ] `coga mark active` on a draft whose workflow (bare ref or frozen
      snapshot) has an unresolvable `other-agent` step at **any** frozen
      position exits non-zero with the refusal text, and the ticket file is
      byte-identical afterwards (no `status: active`, no log line).
- [ ] `coga launch` of such a draft refuses before any write on both the
      grouped-startup and the non-grouped (`_commit_auto_activate`) paths,
      with `Cannot launch <slug>: <refusal text>`; neither prints the
      misleading "could not be frozen" wording.
- [ ] Megalaunch, the recurring runner, and `coga unblock` refuse the same
      tickets through their existing `WorkflowError` handling, now before
      writing (no new output format needed there).
- [ ] Recurring autofix behavior is unchanged (it still falls back to
      `code/with-self-review`), now through the shared selector.
- [ ] `coga validate` output, kinds, and severities are unchanged.
- [ ] Shipped prose: `build/onboarding` and Dream create implementation/code
      drafts with `--fallback-workflow code/with-self-review`; the
      `bootstrap/ticket` skill tells the interviewer not to pick a workflow
      with `other-agent` steps when no peer resolves; `coga/first-task` leads
      with `code/with-self-review`; `coga/workflows` documents the refusal and
      the flag.
- [ ] Tests cover each repo shape above (one agent; two agents with and
      without `peer =`; three agents with and without `peer =`), and
      `python -m pytest` passes.
- [ ] Verification tier (`coga-dev/testing`): this change is **not**
      platform-sensitive, so no native Windows AWS-harness receipt is
      required. The only filesystem touch is reordering existing `mkdir`
      calls in `create_task` after the checks; it adds no new path,
      encoding, process, or lock behavior. Required evidence is a tier-1
      Linux full-suite receipt (full SHA, OS, Python, exact command, counts,
      runtime) in the PR and on the ticket. The owner also does a manual
      behavior walk in the Windows VMware VM, installed from the PR branch.
      If the implementation ends up touching path handling beyond that
      reorder, the change becomes platform-sensitive and needs the Windows
      AWS receipt before merge.

Refusal text (`<wf>` is the workflow name; `<main>` the main agent):

- one agent: `<wf> is a two-agent workflow, and this repo has one agent. Use code/with-self-review, or declare a second agent in coga.toml.`
- three or more, no `peer =`: `<wf> needs a peer agent, but [agents.<main>] has no peer = to pick one. Set one, or use code/with-self-review.`
- For a workflow not under `code/` (e.g. `docs/with-review`, no docs
  self-review workflow ships), drop the `code/with-self-review` clause:
  `... has one agent. Declare a second agent in coga.toml.` /
  `... Set one.`

The substitution line on a successful fallback:
`No peer agent resolves; using code/with-self-review instead of code/design-then-implement.`

### Proposed shape

1. **Typed peer failure** — `src/coga/bump.py`: add
   `PeerAgentUnresolvable(OperatorResolutionError)` carrying `main`,
   `candidates`, and `ambiguous: bool`. `resolve_other_agent()` raises it in
   both of its existing failure branches (`ambiguous=True` on the
   `len(cfg.agents) >= 3` branch). Keep the existing `str(exc)` text
   unchanged — `validate.py`'s `other-agent` branch embeds it in
   `unresolvable-step-assignee` and tests assert on it. Failures from
   `resolve_main_agent()` stay plain `OperatorResolutionError` (not a peer
   problem; existing refusals own them).
2. **Pure workflow check** — `src/coga/bump.py` (beside
   `effective_step_role()`): `unresolvable_peer_refusal(cfg, workflow_name,
   steps, agent, *, allow_prospective_default) -> str | None`. It walks
   **every** step, takes `effective_step_role(steps, i)`, and for the first
   `other-agent` calls `resolve_other_agent()` once (the peer does not vary
   per step). On `PeerAgentUnresolvable` it returns the refusal text above,
   choosing the variant from `exc.ambiguous` and the `code/` prefix of
   `workflow_name`; otherwise `None`. Checking every step, not just remaining
   ones, matches `validate.py`, which errors on any frozen step — anything
   narrower would let the post-write validation refuse after the write.
   Accept steps as frozen dicts (`step.get("assignee")`); `create_task`
   passes `wf.freeze()["steps"]`.
3. **Workflow selector** — `src/coga/create.py`:
   `select_workflow(cfg, workflow_name, fallback_name, *, agent=None) ->
   tuple[str, bool]` returns the workflow to use and whether it substituted.
   Loads the primary workflow, runs the check with the prospective main agent
   (`allow_prospective_default=agent is None`); on a refusal with a fallback,
   returns the fallback. `recurring_autofix.autofix_workflow()` becomes a
   call to it with `AUTOFIX_WORKFLOW` / `AUTOFIX_NO_PEER_WORKFLOW`, keeping
   its existing stderr note in `create_autofix_ticket()`.
4. **Create refuses before any filesystem write** — `create.create_task()`:
   run the whole-workflow check immediately after the workflow is loaded and
   its step skills are checked, **before** directory normalization, slug
   allocation, and any `mkdir` (today `task_dir.mkdir(parents=True)` for
   directory form and `ticket_path.parent.mkdir(...)` for file form both run
   before the step-1 resolve block). Raise `ValueError(refusal)` there. The
   existing step-1 `resolve_operator(..., step_index=1)` block has the same
   ordering bug for non-peer failures (owner-less owner step, unknown agent):
   split path allocation so the slug, `ticket_path`/`task_dir`, existence
   checks, and `created_ref` are computed first, run the step-1 resolve, and
   only then `mkdir`. Either keep the step-1 resolve or fold it into the
   pre-allocation check, as long as every refusal happens before the first
   `mkdir`. This matters most for `recurring._create_at_slug`, which uses
   `force_directory=True` and catches `ValueError`: a stranded empty
   directory would make the retry fail with `Task directory already exists`
   instead of re-evaluating the workflow. `commands/create.create_draft()`
   already turns `ValueError` into `_bail` (exit 2).
5. **Create CLI flag** — `src/coga/commands/create.py`: add
   `--fallback-workflow` to `create()` and a `fallback_workflow` kwarg to
   `create_draft()`. Usage error if given without `--workflow`. Call
   `select_workflow()` after `load_config()` and pass the chosen name to
   `create_task()`. Echo the substitution line only **after** `create_task()`
   returns successfully; if it raises (e.g. the fallback is itself
   unresolvable), the user sees only the fallback's refusal.
   `select_workflow()` does not pre-validate the fallback; `create_task()`'s
   guard is the single place that refuses it.
   `commands/ticket.py`'s `create_draft(title=target)` call is unaffected.
6. **Activation refuses before writing** — `src/coga/mark.py`:
   `_assert_operator_resolves()` also runs the whole-workflow check on the
   prospective (already frozen, agent-selected) ticket and raises a new
   `PeerWorkflowUnavailable(WorkflowError)` with the refusal text. Being a
   `WorkflowError` subclass keeps megalaunch (`_ACTIVATION_REFUSALS`-style
   tuple and its `isinstance(exc, WorkflowError)` branch), the recurring
   runner, and `commands/unblock.py` handling it unchanged. Since
   `prepare_active()` runs it, every activation path — `mark_active`, both
   launch paths, assist prospective — refuses before writing.
7. **Clean wording** — catch `PeerWorkflowUnavailable` *before*
   `WorkflowError` in `commands/mark.active()`
   (`Cannot activate <slug>: <text>`), `launch._prepare_auto_activate()` and
   `launch._prospective_assist_ticket()` (`Cannot launch <slug>: <text>`), so
   the "could not be frozen" message stays for real freeze failures.
8. **Prose (package owners under `src/coga/resources/templates/coga/`)**:
   - `bootstrap/workflows/build/onboarding.md` `## generate-batch`:
     implementation tickets use
     `coga create "<title>" --workflow code/design-then-implement --fallback-workflow code/with-self-review`;
     explain one-agent repos get `code/with-self-review` (no design step, so
     the thin ticket goes straight to implement). Decision tickets keep
     `draft-for-human`. Update `## No other-agent code review` accordingly.
   - `recurring/dream/ticket.md`: the `coga create ... --workflow
     code/with-review` gap-filing command gains `--fallback-workflow
     code/with-self-review`; the "scoped `code/with-review` draft" phrases in
     the proposal-ownership and Phase 1 PR-proposal rules say the same.
   - `bootstrap/skills/bootstrap/ticket/SKILL.md` (Workflow question and the
     frontmatter rule for drafts): do not pick a workflow with `other-agent`
     steps unless a peer resolves (two agents, or `peer =` set); otherwise
     use `code/with-self-review`; activation will refuse otherwise.
   - `bootstrap/contexts/coga/first-task/SKILL.md`: the example command uses
     `code/with-self-review`; note that a repo with two agents can use
     `code/with-review` for peer review; fix the "such as `code/with-review`
     ... rotating to the peer agent" sentence.
   - `bootstrap/contexts/coga/workflows/SKILL.md`: "Roles are the routing"
     gains that create and activation refuse a workflow whose `other-agent`
     steps cannot resolve, before writing; "Code review gate" mentions
     `--fallback-workflow`.
   - `bootstrap/workflows/code/with-self-review.md` `## No other-agent code
     review`: mention create/activation refusal and that `coga build` and
     Dream fall back to it.
   - No user topic lists `coga create` options today (only `first-task` and
     `workflows` mention `--workflow`); the Typer help text is the option's
     reference, so write it carefully.
9. **Tests** — reuse the agent-shape setups: `tests/test_validate.py`
   `test_agentless_draft_validates_future_peer_without_selecting_main_agent`
   (parametrized one/two/three agents ± peer) and
   `tests/test_recurring_autofix.py`'s one-agent autofix test. Add:
   create refusal per shape with "nothing on disk" assertions (file absent,
   log unchanged) — note these must use the *packaged* peer workflows, not
   the `test_validate.py` fixture's local `code/with-review` override, which
   has no `other-agent` step; the fallback flag per shape; an unresolvable
   fallback refusing with no substitution line in output; a directory-form
   (`force_directory=True`) refusal leaving no directory, then a successful
   retry at the same slug once a peer is configured; `mark active`
   byte-identical refusal; launch refusal on both paths (see
   `tests/test_launch.py` for existing auto-activate refusal tests); the
   unchanged-validate check. Optional but recommended: end-to-end no-write
   assertions for megalaunch, the recurring runner, and `coga unblock`.

### Out of scope

- Removing or changing the peer workflows themselves, or adding a
  docs self-review workflow or a design step to `code/with-self-review`.
- Changing `coga validate` (kinds, severities, messages).
- Changing bump's or launch's refusal at an `other-agent` step reached
  mid-workflow (config changed after activation) — it already refuses before
  writing.
- An `[agents]` listing command, launch env var, or a general fix for other
  write-then-validate paths in `create_task`/`mark_active`.
- Changing `coga init` defaults.

## Context

### Decisions (2026-11-11, with the owner in the design session)

- **Refuse, don't warn.** The authoring-time plan was to warn and still
  succeed. Investigation showed create and activation already refuse (after
  writing), so a warning would need `coga validate` to downgrade
  `unresolvable-step-assignee`. Owner chose: a one-agent repo should not be
  able to create or activate a peer-workflow ticket; validate stays
  unchanged; the fix moves the refusal before the write. Superseded design on
  the blackboard.
- **Activation must check too, not only create.** A peer workflow can reach
  activation without `create --workflow`: the `coga ticket` interviewer
  writes a bare `workflow:` on a draft; agents can change after creation
  (including per-machine `coga.local.toml`); tickets can be hand-edited.
- **Whole workflow, not remaining steps.** `validate.py` checks every frozen
  step, so the pre-write check must too or the post-write validation still
  refuses after writing.
- **Trigger is "no peer resolves"**, i.e. `bump.resolve_other_agent()` fails:
  one agent, or three or more with no `peer =` for the main agent. A
  two-agent repo without `peer =` resolves and must not refuse.
- **Build/Dream choose via `--fallback-workflow`**, decided at create time
  against live config (not at `init`: users often add a second agent between
  `init` and `coga build`). Rejected: a launch-exported peer env var (prose
  branching, shell syntax differs on native Windows) and prose parsing
  `coga.toml` (misses `coga.local.toml` merging).
- **Accepted cost:** `code/with-self-review` has no `design` step or owner
  design gate, so a thin `coga build` ticket in a one-agent repo goes
  straight to implement.

### Where things live

- `src/coga/bump.py`: `resolve_main_agent()`, `resolve_other_agent()` (the two
  failure branches), `effective_step_role()`, `resolve_operator()`.
- `src/coga/create.py`: `create_task()` — step-1 `resolve_operator` block
  before `git.write_ticket()`; `assert_task_valid(..., action="create")` after
  the write and log append is what refuses today.
- `src/coga/commands/create.py`: `create()` (Typer options), `create_draft()`
  (also called by `commands/ticket.py` for a new interview draft).
- `src/coga/mark.py`: `prepare_active()` → `_select_main_agent()` then
  `_assert_operator_resolves()` (current step only); `mark_active()` writes
  then `assert_task_valid`.
- `src/coga/launch.py`: `_prepare_auto_activate()` (bails per exception
  type), `_commit_auto_activate()` (non-grouped write via `mark_active`),
  `_publish_startup` path's pre-write `assert_task_valid(..., action="launch
  startup")`, `_prospective_assist_ticket()`, and
  `_prospective_activation_identity()` (swallows all refusals — leave it).
- `src/coga/megalaunch.py`: tuple of `prepare_active` refusals and its
  `isinstance(exc, WorkflowError)` formatting; `src/coga/recurring_runner.py`
  and `src/coga/commands/unblock.py` catch `WorkflowError`.
- `src/coga/recurring_autofix.py`: `autofix_workflow()`,
  `AUTOFIX_WORKFLOW`, `AUTOFIX_NO_PEER_WORKFLOW`, `create_autofix_ticket()`.
- `src/coga/validate.py`: the `assignee == "other-agent"` branch (imports
  from `coga.bump` lazily to avoid a module cycle — `bump.py` must not import
  `validate.py` at module level).
- Existing hint text to stay consistent with: "code/with-self-review without
  a peer agent" in `commands/mark.py` `done()` and `commands/bump.py`.
- Experiment scripts used for the verification above were throwaway (session
  scratchpad), not committed.

<!-- Ticket guide — keep this comment when filling in or updating the ticket.
It documents field shapes; these are examples, not values to copy into every
ticket. Omit optional fields and sections until needed. Editing rules come
from the base prompt; body regions from coga/tickets; blackboard conventions
(superseded designs, draft cleanup, oversized notes) from coga/blackboard.
Write requirements under ### subheadings of Description or Context; any other
level-two heading above the fence does not reach the launch prompt.

FRONTMATTER
The real values are in this ticket's YAML header. Required ordinary-ticket
keys are title, status, owner, and workflow. A minimal draft has workflow: null.

    title: Fix retry diagnostics           # What the work is called; identity comes from the file path.
    status: draft                          # CLI state: draft, active, in_progress, paused, blocked, done, canceled.
    owner: human-name                      # Accountable human; receives notifications and owner gates.
    agent: codex                           # Optional configured main agent; activation supplies the default if absent.
    contexts:                              # Optional facts to include in every launch; attach only what is needed.
      - service/retries
    skills:                                # Optional ticket-wide procedures, in addition to workflow step skills.
      - infra/testing-conventions
    workflow: code/with-review             # Draft reference or null; live tickets have the frozen mapping below.
    secrets:                               # Optional environment names mapped to references, never credentials.
      - API_TOKEN: env:LOCAL_API_TOKEN
      - SERVICE_KEY: op://automation-vault/service/api-key

The agent choice is not the current operator or the ticket interviewer.
Omit empty contexts, skills, and secrets lists. Each secrets entry has exactly
one unique name (no COGA_ prefix); env: reads the operator's environment and
op:// reads a 1Password item at launch, exposing the value under the left-hand
name. An unavailable reference prevents launch. Never put a literal secret here.

A workflow must be selected before activation. Creation with --workflow, or
activation of a draft reference, freezes its steps. CLI transitions manage step;
do not rewrite a live snapshot or advance it by editing YAML. Frozen example:

    workflow:
      name: code/with-review                # Selected workflow name.
      steps:
        - name: implement                  # Ordered step name.
          skills:                          # Optional procedures for this step; plural, never skill.
            - code/implement
          assignee: agent                  # Role: owner, agent, or other-agent (the configured peer).
          requires: branch                 # Optional completion gate: branch or pr.
    step: 1 (implement)                    # One-based position plus name; CLI removes this on completion.

An omitted step assignee inherits the previous role; the first defaults to
owner. The current step determines who holds the ticket. There is no top-level
assignment field. Removed keys slug, human, assignee, and watchers are invalid.
There is no execution-mode field: a sibling ticket.py supplies a script phase.

Repo extensions are string fields declared under [ticket.fields.<name>] in
coga.toml: description explains the field, values restricts its choices,
default seeds it, and required prevents activation while it is empty. Actual
values live below the extensions marker comment in the YAML header. Preserve
them; do not invent extension fields or change their definitions in config.

Machine-owned fields: delegate freezes a recurring parent's bootstrap/<name>
target; period_generation identifies its materialized run. Both belong only on
period tasks directly under tasks/recurring/. launch_generation is megalaunch's
session claim. Preserve these fields; do not add or clear them yourself.

BLACKBOARD (BELOW THE FENCE)
Keep current decisions and their reasons, verification, next actions, and
blockers here. Update current values in place instead of appending stale copies.

Optional ## Dev: branch: <name> when created; pr: <full /pull/ URL> when opened;
worktree: <path> only for a sandbox clone. One field per line, notes on separate
lines, omit unknown values. For multiple owned branches, the first branch is
the workflow branch.

Optional ## PR: one fenced YAML mapping of PR-preparation receipts (title,
author, head/base OIDs, review depth, files, review, checks). Record only actual
implementation and evidence, never placeholders; coga/pr-publication/
preparation owns the fields and the publishing workflow the review rules.

Optional ## Blockers and ## Blocker reminders are CLI-maintained. Preserve
blocker IDs, timestamps, actor names, resolved answers, and reminder fingerprints
with last_reminded timestamps; use lifecycle commands to block or resolve them.

Recurring parents (coga/recurring/<name>/ticket.md) take schedule and related
template settings owned by coga/recurring/templates; do not add them to an
ordinary ticket.
-->

<!-- coga:blackboard -->

## Dev

branch: coga/v1-48-give-coga-build-tickets-a-self-review-work-5d47f4

## Implement handoff (2026-11-11)

Implemented the spec as written (Proposed shape items 1–9) in one commit,
`4f4adf45a` on the branch above, rebased on main `8ab0f010e` and pushed.

- `bump.py`: `PeerAgentUnresolvable(OperatorResolutionError)` (main,
  candidates, ambiguous; `str(exc)` unchanged), `peer_refusal_text()`,
  `unresolvable_peer_refusal()` (every step, effective role, resolve once).
- `create.py`: peer check right after workflow load/skill check; the step-1
  resolve stays but every `mkdir` now runs after it (no residue, retryable).
  New `select_workflow()`. `commands/create.py`: `--fallback-workflow`
  (exit 2 without `--workflow`); substitution line echoed only after
  `create_task` succeeds.
- `mark.py`: `PeerWorkflowUnavailable(WorkflowError)` raised in
  `_assert_operator_resolves` (whole frozen workflow) before the
  current-step resolve, so `prepare_active` refuses on every activation path.
  `commands/mark.active`, `launch._prepare_auto_activate`,
  `launch._prospective_assist_ticket` catch it before `WorkflowError`.
- `recurring_autofix.autofix_workflow()` now calls `select_workflow`.
- Prose: onboarding, Dream, bootstrap/ticket, first-task, workflows,
  with-self-review, design-then-implement (peer-review note), and
  coga-dev/codebase/gotchas.
- Decision: activation's peer check runs before the current-step
  `resolve_operator`, so even a step-1 `other-agent` shows the short refusal;
  the existing `test_mark_active_refuses_an_unresolvable_step_one_role`
  assertion was updated to the new text.
- Not done (optional per spec): end-to-end no-write tests for megalaunch,
  recurring runner, `coga unblock`; only the subclass relation is pinned.
- Open question (interviewer deterministic check) unchanged: prose only.

Pre-existing failures, reproduced identically on an `origin/main` worktree
(not caused by this change; not fixed here):
`test_config.py::test_layout_contexts_cyclic_root_rejected`,
`test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`,
`test_git.py::test_final_package_edits_never_escape_a_mutating_cli_sweep`
(both params), `test_packaging.py::test_context_navigation_has_no_broken_links`
(README links the missing ticket
`coga/tasks/document-the-remedy-for-a-bloated-blackboard-sibli.md`).

## PR

```yaml
title: Refuse peer workflows without a peer before writing; add --fallback-workflow
author: claude
author_evidence: Implement session ran in Claude Code on Claude Opus 5.5 (claude-opus-5-5); see implement handoff.
head: 4f4adf45ab3c42cefd9e643cb106b7b414301297
base: 8ab0f010ede0c723d5b3eed20870be9318f45fd2
depth: deep
rationale: Changes create and activation refusal ordering and adds a CLI option across create, mark, launch and recurring paths; no code review has run yet.
implementation: Typed peer-resolution failure and a whole-workflow peer check shared by create (before any mkdir) and prepare_active (before any write); create --fallback-workflow and select_workflow, also used by recurring autofix; short refusal text in mark active and launch; shipped prose steers coga build, Dream and the ticket interviewer to code/with-self-review when no peer resolves.
deviations: None from the spec. Activation checks peers before the current-step resolve, so a step-1 other-agent refusal now uses the short text (one existing test assertion updated).
limitations: Megalaunch, recurring runner and coga unblock rely on PeerWorkflowUnavailable subclassing WorkflowError; no end-to-end no-write tests for them. Five full-suite failures exist identically on main. Windows VM behavior walk is the owner's.
files:
  docs/contexts/coga-dev/codebase/gotchas/SKILL.md: Note that create_task and prepare_active check peer resolution before writing.
  src/coga/bump.py: PeerAgentUnresolvable, peer_refusal_text and unresolvable_peer_refusal.
  src/coga/commands/create.py: --fallback-workflow option, usage error, post-success substitution line.
  src/coga/commands/mark.py: Short refusal for PeerWorkflowUnavailable in mark active.
  src/coga/create.py: Pre-write peer check, mkdir moved after all refusals, select_workflow.
  src/coga/launch.py: Short launch refusal for PeerWorkflowUnavailable on auto-activate and assist paths.
  src/coga/mark.py: PeerWorkflowUnavailable and whole-workflow peer check in activation.
  src/coga/recurring_autofix.py: autofix_workflow uses the shared selector.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/first-task/SKILL.md: Lead with code/with-self-review; peer review needs two agents.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/workflows/SKILL.md: Document the pre-write refusal and --fallback-workflow.
  src/coga/resources/templates/coga/bootstrap/skills/bootstrap/ticket/SKILL.md: Interviewer avoids other-agent workflows when no peer resolves.
  src/coga/resources/templates/coga/bootstrap/workflows/build/onboarding.md: Starter implementation drafts pass --fallback-workflow code/with-self-review.
  src/coga/resources/templates/coga/bootstrap/workflows/code/design-then-implement.md: Peer-review note describes the create/activation refusal.
  src/coga/resources/templates/coga/bootstrap/workflows/code/with-self-review.md: Mention refusal and the build/Dream fallback.
  src/coga/resources/templates/coga/recurring/dream/ticket.md: Dream code drafts pass --fallback-workflow code/with-self-review.
  tests/test_bootstrap_ticket_skill_template.py: Pin interviewer peer guidance.
  tests/test_bootstrap_workflow_review_sections.py: Pin fallback flag on build and Dream code-draft commands.
  tests/test_create.py: Create refusal and fallback across all agent shapes, no-residue directory retry, step-1 ordering, select_workflow.
  tests/test_launch.py: Launch refusal before writing on grouped and non-grouped paths.
  tests/test_mark.py: Byte-identical mark active refusal (bare ref and late frozen step), subclass check, updated step-1 assertion.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: Implement step; the workflow's peer-review step has not run yet. Design approval is not code review.
checks:
  - command: python -m pytest -q -p no:cacheprovider
    status: failed
    head: 4f4adf45ab3c42cefd9e643cb106b7b414301297
    base: 8ab0f010ede0c723d5b3eed20870be9318f45fd2
    detail: "5 failed, 4794 passed, 33 skipped in 426s; Linux 6.18.33.2-microsoft-standard-WSL2 (WSL2), Python 3.14.4, 2026-11-12T07:01Z. All 5 failures reproduce identically on origin/main 8ab0f010e (see handoff); none touch this change."
```


## Evaluator review

**Resolved 2026-11-11 (owner review-design, ad-hoc chat):** both must-fix
findings are now in the spec. Finding 1 → Proposed shape item 4 (check runs
before slug/path allocation and any `mkdir`; step-1 resolve moved ahead of
`mkdir` too) plus a directory-form no-residue/retry acceptance criterion.
Finding 2 → item 5 (substitution line echoed only after `create_task()`
succeeds) plus the "no substitution line" clause on the unresolvable-fallback
criterion. The optional megalaunch/runner/unblock e2e tests are listed as
recommended in item 9. Owner also confirmed keeping `--fallback-workflow`
over always-self-review in build/Dream.

Original verdict: not ready for implementation until the two must-fix findings below
are resolved. The overall peer-resolution boundary and activation exception
shape match the current resolver and `prepare_active` seams.

### Must fix before implementation

1. **The proposed create guard still runs after a durable filesystem write for
   directory-form tasks.** Proposed Shape item 4 replaces the current step-1
   resolver block in `create.create_task`, but that block is below task-path
   allocation: `create_task` has already called `task_dir.mkdir(parents=True)`
   when `force_directory=True` (and has already created parent directories for
   file-form tasks). `recurring._create_at_slug` creates every period task with
   `force_directory=True` and catches `ValueError`; an unresolvable peer
   workflow would therefore leave an empty task directory, and the next retry
   would fail at `Task directory already exists` instead of re-evaluating the
   workflow. This contradicts the stated “refuse before writing” outcome and
   makes a failed recurring create non-retryable. Move the whole-workflow
   check above path allocation (after the workflow is loaded and checked), or
   specify an equally atomic cleanup, and add a directory-form no-residue/retry
   acceptance test.

2. **The substitution line is emitted before the fallback is known to have
   succeeded.** Proposed Shape item 5 says to echo the substitution and then
   call `create_task`. But the acceptance criteria explicitly cover a fallback
   that is itself unresolvable; `select_workflow` returns that fallback and
   `substituted=True`, then the later whole-workflow guard refuses it. The CLI
   would print `using ... instead of ...` even though it created nothing. Emit
   the line only after `create_task` succeeds, or make selection validate the
   fallback before it reports a successful substitution. Pin the failure case
   to produce the fallback refusal without the success line.

### Optional recommendations

- Add focused end-to-end assertions for the named megalaunch, recurring-runner,
  and `coga unblock` activation callers. Their current `WorkflowError` catches
  should accept the proposed subclass, but the test plan currently proves only
  direct mark/launch behavior and does not independently pin their no-write
  guarantee.
- The open `coga ticket` question does not need to block this change: the
  proposed interviewer guidance plus the activation backstop is a coherent
  boundary, provided the shipped skill wording is tested.

## Design status (2026-11-11)

Spec written under `## Description` / `## Context` in an attended design
session with the owner. Key turn: create and activation already refuse peer
workflows in one-agent repos, but only after writing; the owner chose
"refuse before writing" over "warn and succeed", and `--fallback-workflow`
over an env var or prose parsing for `coga build`/Dream.

## Open Questions

- Should `coga ticket`'s interviewer get a deterministic check (e.g. run
  `coga mark active`-style validation at interview end) rather than prose
  guidance alone? Spec keeps prose only; activation refusal is the backstop.

## Superseded designs

### 2026-11-11 — Warn on create/activation, still succeed

Print a one-line advisory from `coga create` / `mark active` / first launch
when a remaining step is an unresolvable `other-agent`, and still succeed;
`coga validate` unchanged. Dropped in design: create and activation already
refuse via post-write `assert_task_valid` (every frozen step), so succeeding
would require downgrading validate's `unresolvable-step-assignee`. Owner
chose refusing before the write instead.

### 2026-11-11 — Stop shipping peer-review workflows

Remove `code/with-review`, `code/design-then-implement`, and `docs/with-review` from the package (this repo keeping local copies), with no warnings. Rejected as unsafe after cold review: steps without `skills:` reload their instructions from the workflow file by name, so two-agent adopters' in-flight tickets would lose instructions on upgrade; `checkout_policy._changed_section` compares against the shipped copy, so this repo's local copies would degrade to `manual` checkout; and the change touched ~40 files.
