---
title: 02 Compare current and candidate prompt assembly
status: done
owner: nicktoper
contexts:
- coga-dev/microkernel/objectives
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: report-to-coga
    skills: []
    assignee: agent
agent: claude
---

## Description

Test whether a candidate prompt assembler is actually better than the current one before replacing production assembly. Execute the paired, bounded protocol approved in ticket 01, retain complete input/output evidence, and let the owner judge the results. This ticket is done when the approved trials have been run or their limitations explicitly recorded, the report is reproducible and inspectable, and the owner's decision is recorded as a selected candidate, no demonstrated gain, or inconclusive. Completion of this ticket alone is not permission to implement a replacement.

### Prerequisite and execution

Do not begin trials until `v1/microkernel/03-prompt-assembly/01-define-prompt-candidates-and-trial-protocol` has produced its owner-approved protocol, complete candidates, fixtures and bounded budget. Copy the needed approved inputs into this ticket's attachments so their later retirement cannot invalidate the evidence. Record the source revisions and approval provenance.

Run baseline and candidate with the same task inputs, starting state and agent settings, using the protocol's pairing, repetitions and observations. Preserve the actual rendered prompt for each run and its block/source manifest, outcomes, failures, deviations and limits. Use isolated fixture repositories with local publication targets and notifications disabled so a trial's lifecycle or checkout actions cannot alter live work. Never recursively invoke `coga launch` inside an agent launch; use bounded independent agent sessions or the approved subprocess/test seam.

The noninteractive recurring autofix prompt is included, with its output parsing and exit behavior checked as such. The deterministic-only control must still run code without prompt composition or an agent. Assess skilled and inline workflow cases and the representative invocation cases selected in the protocol; do not silently drop failing cases or change criteria after seeing results.

### Decision before replacement

Apply the approved correctness gates first. A candidate that loses completion, checkout, authority, required-input or deterministic-execution guarantees cannot win. For candidates that pass, compare demonstrated improvements and costs using the pre-agreed measures. Distinguish static composition regressions from observed agent behavior; neither substitutes for the other. Prompt-size estimates do not establish task-success improvements.

The report must support an explicit owner decision. If the candidate is not better or the evidence is inconclusive, record that result and leave ticket 03 unlaunched; do not force a rewrite to justify the experiment. If one wins, retain the exact selected prompt form, explicit applicability facts, required additions, block provenance and known limits as the implementation input. Any materially revised candidate needs a new comparison before it can replace production.

Distinguish observed results from an enduring product decision. Transfer any
enduring ruling, including a deliberate refusal to replace the assembler and
its reopening conditions, to the owner `coga/prompt-composition`. A positive
selection is carried by ticket 03's documentation change. Otherwise, create
a narrow `docs/with-review` follow-up with the complete decision before
finishing `report-to-coga`; do not leave its only copy in a temporary report.
This experiment workflow does not itself edit the packaged topic.

No production prompt or launcher changes belong here. Executing the experiment is separate from implementing the winning form.

## Context

Owns the comparison evidence and result; ticket 01 owns protocol preparation and ticket 03 owns any production implementation. Ticket 02 may finish successfully with a negative result. Its `done` status must not be treated as proof that ticket 03 is eligible.

Read the copied approved protocol first, then the actual resolved source for baseline and candidates. The source inventory must include `src/coga/recurring_autofix.py` (`build_prompt`, `analyze_record`) as well as `src/coga/compose.py` and the shared-session callers. Neither the paused launch-decomposition scope nor a previous suite receipt proves a candidate improves behavior.

Cited rather than attached: `coga-dev/testing`, `docs/contexts/coga-dev/testing/SKILL.md`, "Verification tiers and receipts". Record the exact revision, working-tree differences, platform, agent CLI/version and model settings when available, actual commands, counts and runtime for every run. Mark unavailable information and native-platform limits explicitly. Do not claim that mocked transport tests establish native Windows behavior.

Workflow `draft-for-human` is for conducting bounded experiments and preparing a decision report, followed by the owner's judgment and recording of that decision. The deliverables are trial inputs, prompt specimens, transcripts and results, not product code or a permanent harness. A new reusable code artifact requires a separately reviewed code scope rather than silently extending this experiment.

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

## Provenance

- Approved inputs copied to `approved/` from ticket 01 (all files except its ticket.md).
  Tree hash (ticket 01 method) `3da24c2f…6977` = ticket 01's `artifact_tree_sha256_after_record`;
  accepted package `f5ee59e2…dbbc`. Approval: owner, 2026-11-12, recorded in commit `01bb00f9`.
- Production source pin `c3a86e7f`; `git diff c3a86e7f c66f6437 -- src/` is empty. Trial install: non-editable venv at `c66f6437`.

## Execution pins (owner, 2026-11-12, this session)

- Codex `codex-cli 0.167.2`, exe sha256 `a9672d0f…f56b` (rechecked), `-m gpt-6.1-sol -c model_reasoning_effort="medium"`.
- Sandbox: `-s workspace-write -a never`, `sandbox_workspace_write.writable_roots=["/tmp"]`, `network_access=true` (localhost sink).
- Env: allowlist PATH (pinned venv first), HOME, USER, TERM, LANG/LC_*, SHELL, TMPDIR + Coga launch vars; all else stripped.
- Disposable adapter (this ticket dir) approved: real `spawn_agent_session(composed_prompt=…)`, real `analyze_record` with prompt substitution, real script dispatch with spies. Controller = this agent via tmux, fixed `dialogues.json` lines only. Blinded evaluator = owner.
- Run mode: non-model checks + adapter smoke first, then full 44 + 12 series in protocol order; stop only on gate/stop rules.

## Deviations (both arms identical; fixed before any model session)

- D1: approved `fixtures/configuration.toml` has `user` in shared config, which the real loader rejects; moved to fixture `coga/coga.local.toml` (gitignored). All 8 interactive baselines re-render byte-identical in the materialized fixture (real `load_config` + `compose_prompt`).
- D2: Codex argv adds `-c projects."/tmp/coga-prompt-trial-667707cc".trust_level="trusted"` (otherwise a trust dialog needs an unscripted keypress).
- D3: adapter process itself runs under the env allowlist (ambient `SLACK_WEBHOOK_URL` made config load fail).
- Megalaunch cases use megalaunch's spawn args (actor, `launch_context="megalaunch"`, supervised env, no return witness) but not its launch-claim guards (outside assembly). Authoring uses `_authoring_ticket` + `_run_authoring_session`'s spawn args. Owner-assist: adapter switches to `trial/assist` first, ordinary assist (no recorded-PR proof). Fixture tickets say `agent: claude`; both arms run codex.
- Smoke accident: a stub-PATH bug started one real Codex process (baseline workflow-inline prompt) during smoke; no rollout written (no model turn; likely trust dialog), killed ~3 min. Not a trial; evidence in `runs/_smoke/accident-real-codex-no-turn`.

- D2b: Codex still showed its folder-trust dialog once (pre-model); controller pressed Enter "Trust and continue", saving `[projects."/tmp/coga-prompt-trial-667707cc"]` in `~/.codex/config.toml`. Later sessions do not show it.
- **Containment C1 (owner decision):** `/etc/codex/requirements.toml` (root, multiply harness) forced profile `multiply-full` (write `/home/n/Code`, `/home/n/.codex`, `/tmp`; read all) over the `-c` sandbox pins. author-paused baseline r1 (model ran; listed live repo filtered to checkouts/reconciliation/knowledge paths, read live `coga/checkouts` skill copies; no expected-outcome/other-arm reads seen; no live writes) moved to `runs/_replaced/` — replaced infrastructure run, uses 1 of 4 reserve sessions. Owner sets the policy file aside for the trial; restore afterwards. Verified 2026-11-13 after the owner moved it to `requirements.toml.trial-aside`: a no-op `codex exec` with the pins (infrastructure, not a trial session; 4,934 tokens) recorded `sandbox_policy` workspace-write, writable_roots `["/tmp"]`, network on; permission profile writes only the cwd, `/tmp`, tmpdir.

- **D4 sandbox profile (owner, 2026-11-13):** `-s workspace-write` makes `<root>/.git` read-only (verified: `git commit` → "Read-only file system"), so agent-run `coga bump` would fail in every lifecycle case in both arms. Replaced by a `-c` permission profile `trial` (`:root` read, `:slash_tmp` write, `/tmp/coga-prompt-trial-667707cc/.git` write, network on, `default_permissions="trial"`); `-a never` kept. Verified without a model (`codex sandbox`) and with one infra `codex exec` (5,310 tokens): fixture commit OK, `/home/n/Code/coga` and `~/.codex` writes blocked. author-paused baseline r1 under the old pin (clean: delivered = frozen, live repo unchanged, 171 s; agent noted git read-only) moved to `runs/_replaced/…__git-readonly` — replaced infrastructure run, 2 of 4 reserve sessions used. Adapter now keeps only rollouts whose cwd is the fixture (other Codex sessions run concurrently on this machine) and records each rollout's permission profile.

## Controller rules (pre-declared before any trial session)

- Send only `approved/fixtures/dialogues.json` lines, when their trigger occurs; plan-confirmation request in attended conduct → `Proceed as specified.`
- Queued/recurring/analysis: no replies. Any session idle at an input prompt for 3 min with nothing scripted to send → controller ends it; recorded as `idle-waiting` (a failure for no-reply cases; ambiguous/failed for unanticipated questions).
- Attended sessions with no lifecycle completion (author-paused, owner-assist): after the final scripted line and the agent's reply, controller exits Codex (`/exit` or Ctrl-C) and records it.
- Unanticipated substantive question: recorded, not answered.
- Hard stop at 12 min (`max_session=720`); analyst 300 s; probe 300 s. **Owner change P1 (2026-11-12/13, before any trial):** token ceilings are not enforced because Codex's own turn-one baseline (~22–46k input, cumulative re-billing per tool call) makes 100k/20k/30k unreachable in both arms; wall-clock limits bind; per-run total/cached/uncached/output tokens recorded from the rollout.
- Probes: `codex exec -s read-only` (pins otherwise identical) with `-c developer_instructions=<frozen prompt>`, cwd = that case's pristine fixture, 300 s timeout, fixed question text in `probes.json`; file reads counted from rollout, >4 reads recorded as a violation.

## Static result already determined

- Payload secondary: C1 total 108,052 vs baseline 111,859 bytes = 3.40% reduction < 15% threshold → no payload gain (analysis cases grow ~+55%).

## Progress

- [x] adapter + pinned venv  - [x] non-model checks  - [x] 44 main sessions (2026-11-13)  - [x] 12 probes  - [x] blinded evaluation pack (`blind/`)  - [x] report draft (`report.md`)  - [x] owner: blinded verdicts, then decision (2026-11-13)  - [x] owner: restore `/etc/codex/requirements.toml` (verified identical to `.trial-aside`, 2026-11-13); D2b trust entry removed

## Decision (owner, 2026-11-13): C1 disqualified

- Verdicts: agent-prefilled from the blind pack only, owner-confirmed with rulings (355e0d fail/checkout; ff9470 fail/completion; autofix-problem "headings >=###" = nothing shallower). `blind/verdicts.csv` sha256 `a232f750…d085` recorded before the key was opened; all labels matched.
- Unblinded: 21/22 successes in each arm. C1 owner-assist r1 merged `origin/main` into the prepared `trial/assist` branch → checkout-gate violation and paired loss → disqualified per protocol. C1 authoring 2/2 vs baseline 1/2 (baseline's miss = no cold evaluator, not an execute/bump conflict). Probes 5/6 vs 4/6 (no gain). Payload −3.40% (no gain).
- `report.md` §3, §4, §7 and §8 are complete. §7 also records an adapter spy defect: `subprocess.run` was never restored, so the analysis `record.subprocess` holds a later live-repo `git rev-parse`. Prompt identity for the 12 analysis runs was re-verified from the rollouts (exact match).
- Ticket 03 stays unlaunched. Follow-up created as a draft: `v1/microkernel/03-prompt-assembly/record-the-prompt-assembly-non-replacement-ruling` (`docs/with-review`), carrying the ruling and the reopening conditions for `coga/prompt-composition`.

## Report to Coga (2026-11-13)

- **Produced:** the paired experiment, 44 sessions + 12 probes under the D1–D4 pins, plus the blinded evaluation pack. Final report `report.md` (sha256 `39a55bb7…`) has the decision in §8. Verdicts are in `blind/verdicts.csv` (`a232f750…`). The disposable tooling (`adapter.py`, `blind.py`, `ctl.sh`, `sink.py`) stays in this ticket directory as evidence only; it is not core.
- **Owner decided:** C1 is **disqualified** because owner-assist r1 merged `origin/main` into the prepared branch, a checkout-gate violation and a paired loss. Neither secondary measure shows a gain: probes 5/6 vs 4/6, payload −3.40% against a 15% threshold. The owner also chose to publish all evidence as is, including the Codex rollout `session_meta` IDs. Rulings: P1 (no token ceilings) and C1/D4 (the sandbox profile).
- **Where it landed:** everything is under this ticket directory on `main`: `approved/`, `runs/` (including `_replaced/` and `_smoke/`), `blind/`, `report.md`, about 40 MB.
- **Not published:** git ignores the fixture copies of `coga/coga.local.toml` (D1's `user` move) and the `.agent-skills/` projections under `runs/*/tree/`. They are reproducible from `approved/fixtures` together with D1.
- **Product ruling:** recorded only in the draft follow-up `record-the-prompt-assembly-non-replacement-ruling` (`docs/with-review`), which targets `coga/prompt-composition`. Ticket 03 stays unlaunched, and this ticket's `done` does not make it eligible.
- **Machine state:** `/etc/codex/requirements.toml` has been restored and the D2b trust entry removed. The `/tmp/coga-prompt-trial-*` fixtures are disposable.

## Handoff (agent-produces → human-owns-and-finishes)

- **Executed.** All 44 paired sessions and 12 probes were executed under the pins and D1–D4. Reserve used: 2 of 4 sessions, both on author-paused baseline r1, kept in `runs/_replaced/`.
- **Invariants across all 56 sessions:**
  - delivered prompt = frozen, modulo the marker;
  - live repo HEAD/status unchanged during each run;
  - effective sandbox as pinned;
  - no limit hit.
- **Evaluation pack.** Fill `blind/verdicts.csv` from `blind/<item>/facts.md` + `trace.md` (+ `answer.txt` for probes). Only then open `reveal-after-verdict/`, `blind-key.json` and `controller-checks.json`; the last two are arm-labeled, so keep them closed until the verdicts are in.
- **Report.** Complete `report.md` §3–4 and choose the decision in §8. Payload is final, with no gain (3.40%), and no simplification is claimed.
- **Evidence publication.** On 2026-11-13 10:46 -0800, a concurrent Coga command on this checkout swept this task directory to `main` (`bbc717c8b "Sync coga state"`, pushed). `runs/` holds 36 MB, including Codex rollouts whose `session_meta` carries the account/user IDs plus encrypted reasoning. Any later sweep or bump publishes the rest of `runs/` and `blind/`. Owner decision (2026-11-13): publish all evidence as is, then bump.
- **Machine cleanup for the owner:**
  - restore `/etc/codex/requirements.toml` from `.trial-aside`;
  - optionally remove the `[projects."/tmp/coga-prompt-trial-667707cc"]` trust entry (D2b) from `~/.codex/config.toml`;
  - the fixtures under `/tmp/coga-prompt-trial-*` are disposable.
- **Attachments added this step:** `blind.py` (pack builder), the `probe` command in `adapter.py`, and `report.md`. All are disposable trial tooling, not core.
