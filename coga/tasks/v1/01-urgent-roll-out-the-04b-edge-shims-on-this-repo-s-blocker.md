---
title: Roll out the 04b edge shims on this repo's blocker-reminders period
status: done
owner: nicktoper
workflow:
  name: maintenance/with-approval
  steps:
  - name: inventory
    skills: []
    assignee: agent
    checkout: manual
  - name: approve
    skills: []
    assignee: owner
    checkout: manual
  - name: cleanup-and-verify
    skills: []
    assignee: agent
    checkout: manual
agent: claude
---

## Description

Finish the repo-local rollout of PR #1272 before the next affected sweep can execute a legacy blocker-reminders shim against the new wheel. Inventory the writers and old shim callers, then obtain the owner's decision on whether to keep the retained `done` period with its shim replaced in place, or let normal recurring rollover replace the period. Before applying the approved action, verify affected launches and sweeps were quiesced before wheel installation and that every participating writer now uses the reviewed wheel containing 04b. This is done when the approved disposition is verified on current control, the caller inventory shows no remaining executable legacy blocker-reminders or skill-update shim, and the blackboard records the rollout evidence.

## Context

- PR #1272 merged as `dcba1b1dc`. The retired 04b ticket's blackboard recorded that both recurring parents are state-only carriers. Future periods get the packaged shims from the installed wheel. Recheck the configured roots and carrier state, including parked, hidden, and ignored candidates. The only caller observed during authoring is `coga/tasks/recurring/blocker-reminders/ticket.py`, still the stock PR-827 blob `035f27cb` in a `done` period. No skill-update period existed.
- Which runs can reach the old shim (from `coga/recurring/scheduling`, "Variants" and the period-status rules): a bare sweep or `coga recurring launch blocker-reminders` *replaces* a prior-period `done` period with a fresh one that freezes the new packaged shim. Only `coga recurring --force`, which reactivates `done` periods, or re-running the current period executes the frozen legacy `ticket.py`. Quiescence must cover those variants on every writer, including cron and agent-app schedulers.
- Follow the `coga/edge-code` runbook at `src/coga/resources/templates/coga/bootstrap/contexts/coga/edge-code/edge-code-upgrades.md`, especially steps 1–4 and “Recipe-backed recurring shims.” Use the runbook's `recipe-shim-callers` inventory before and after the rollout. Record participating writers, quiescence evidence, and the reviewed wheel hash and installation evidence. Get owner evidence for writers outside the session's visibility. A CLI version or successful import alone cannot establish writer readiness.
- Owner decision (authoring): every writer that runs sweeps, including this repo's dev `.venv` (currently an editable install, which the runbook says is not upgrade evidence), must install a wheel built from a reviewed commit containing `dcba1b1dc` and record that wheel's hash. An editable install does not satisfy this ticket.
- Inventory is read-only. At the owner gate, record the approved disposition and action list. If any writer still needs upgrading, record who will quiesce and upgrade it and which reviewed wheel they will install. Hold the shim action until all writer receipts are available. Recheck quiescence, wheel readiness, period identity, and candidate bytes before acting. For a retained period, use the runbook's installed-wheel lookup with `JOB=blocker-reminders` and its byte-guarded compare/replace procedure. The old registry call fails with `unknown recipe` on the new wheel. For replacement, verify the selected package-backed parent and the upgraded wheel's packaged shim before allowing the approved rollover invocation, which can materialize and start the job in one call. Afterward, verify the new period generation and its frozen shim bytes on control. Keep sweeps quiesced while any eligible caller could still reach the old shim.
- Apply any approved frozen-period edit as routine Coga state and verify the published bytes on control. Preserve the period ticket's lifecycle fields, generation, and blackboard during a shim edit. Preserve changed or unexpected callers for owner review. Record the selected shim source, result of the final inventory, and any unresolved prerequisites before advancing.

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
          checkout: create-or-reuse        # Entry checkout: control, create-or-reuse, reuse-required, manual.
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

## Inventory — 2026-11-20

- Clean control matched `origin/main` at `ed2d599c77c7ec06a46a31fdc41ca9df7f2c0bea`, which contains PR #1272's merge `dcba1b1dcd4ffab1cb6573575b0b2660c2c8e384`. Loaded config resolves the roots to `coga/recurring` and `coga/tasks` in this checkout.
- Both affected parents contain only state-carrier `ticket.md` files with empty YAML and the carrier marker. The merged package supplies both definitions and their shims, each calling its corresponding `coga_edge` module with `scheduled=True`.
- The runbook's `recipe-shim-callers` search returned one hit across both roots with hidden and ignored paths included, covering parked copies. The name inventory found no skill-update period or additional affected shim. There are no symlinks in those roots. The sole hit is `coga/tasks/recurring/blocker-reminders/ticket.py:15`, a registry call. The working file and control blob both match the PR-827 baseline `035f27cb0bcf7fb8372c78c44392f0d5922bbe35`. The older direct-import baselines and both skill-update baselines had no callers. Its sibling ticket is `done`, generation `7c8e61c5-0b9c-410d-9069-cab3b3da6d9e`. The log records materialization for 2026-11-18 and completion on 2026-11-19 at 09:04.
- Known writer environment is this repo's `.venv/bin/python`. Its Coga metadata points to this checkout with `editable: true`. The PATH entry `/home/n/.local/bin/coga` resolves to a second candidate writer, the uv tool at `/home/n/.local/share/uv/tools/coga/bin/coga`, with that tool's own Python shebang and another editable install of this checkout. Confirm its participation with the owner. No reviewed wheel hash or per-writer installation receipt was established.
- A scoped process check in this sandbox found no matching Python/Coga worker. User crontab access was denied and the user timer bus was unavailable. Git lists this as the only non-prunable linked checkout. The owner must account for host processes, schedulers (including cron and agent apps), other users, hosts and standalone clones. These observations do not establish quiescence.

## Proposed actions for owner approval

1. Identify every writer and its operator, scheduler, checkout, command and actual interpreter. Confirm whether the PATH uv tool participates. Assign each operator to disable affected scheduling and drain any live runs before installation, then record when and how they verified the stop. Cover bare sweeps, force sweeps, named launches and direct current-period execution. Keep other writers paused through control verification. Plain named launch leaves a current-period done run alone. The documented named `--rerun` replaces it and runs a fresh job, so treat that as an explicit live invocation, not a diagnostic.
2. Have the owner designate the reviewed build commit and wheel artifact. Propose the PR #1272 merge commit above as the minimum reviewed source, subject to owner choice of the exact artifact or a reviewed descendant. Record ancestry, build provenance and SHA-256. Have each operator retain its old wheel and hash where applicable, or record its editable source baseline, and install the reviewed artifact in the actual writer environment after the stop. Record install receipts, interpreter and package resource locations, and verify the installed shim bytes against the artifact in every writer. Both observed editable environments lack readiness receipts. A version or import alone is insufficient.
3. Approve one disposition. Recommend retaining the existing period because it changes only the shim and does not trigger a reminder run. Recheck current control, generation, quiescence and receipts. Locate the installed wheel shim per the runbook with `JOB=blocker-reminders`, extract the PR-827 baseline, and use its byte-guarded compare/replace on that one path. Publish it as routine Coga state. Preserve the period ticket bytes (including lifecycle, generation, frozen workflow and blackboard), parent carriers, and unrelated attachments. Leave unexpected or changed candidates for owner review.
4. Alternatively, approve normal rollover. After the same readiness checks, verify the package-backed parent, installed shim and that scheduling sees the retained generation as prior-period. Use the approved `coga recurring launch blocker-reminders` from current control with the reviewed writer. It may start the live reminder job immediately. Preserve parent state and log history through normal Coga dispatch. Avoid force and manual deletion. Confirm the replacement generation differs and its frozen shim came from that wheel.
5. Fetch control after the selected action. Compare its frozen shim bytes to the reviewed wheel and verify the selected generation and preservation rules. Repeat the runbook search over configured roots (exit 1 expected for zero callers), including ignored and parked paths. Record artifact and control identities, per-writer receipts, final inventory and any unresolved exceptions before resuming sweeps or advancing. No cleanup, installation or scheduler changes occurred during inventory.
## Owner approval

- The owner explicitly approved retaining the completed blocker-reminders period, replacing only its stock legacy `ticket.py` with the reviewed wheel's packaged shim, building from PR #1272 merge `dcba1b1dcd4ffab1cb6573575b0b2660c2c8e384`, and advancing to cleanup-and-verify. Preserve generation `7c8e61c5-0b9c-410d-9069-cab3b3da6d9e`, the period ticket bytes, both parent carriers, and unrelated attachments. Leave unexpected or changed callers for owner review.
- The cleanup agent can build the approved wheel, record its SHA-256, and upgrade the repo `.venv` once the scheduler operator has paused affected scheduling and verified that active runs have drained. The owner still needs to identify the scheduler operator, confirm whether the PATH uv tool participates, and identify operators for any additional writers. Each participating operator must supply quiescence evidence and an installation receipt for the same wheel.
- At approval, fetched control was `3dd1014ee1b99b29f42ac5bd0f813e0cfbb8f305`. The runbook search still found only the blocker-reminders registry call, with control blob `035f27cb0bcf7fb8372c78c44392f0d5922bbe35`. Hold the shim replacement until all writer receipts are available. Then recheck control, generation, and candidate bytes, perform the runbook's byte-guarded replacement, publish as routine Coga state, and verify the published bytes and zero legacy callers before resuming sweeps.

### Cleanup-and-verify — 2026-11-20

- Recheck at session start: control `14bbb4b1b6477904d15c8bddc9bf2f1a793919fd` = `origin/main`, contains `dcba1b1dc`. Period still `done`; `ticket.py` working and control blob `035f27cb0bcf7fb8372c78c44392f0d5922bbe35`. `.venv` and uv tool both still editable 0.4.1 of this checkout.
- Built reviewed wheel from `git archive dcba1b1dcd4ffab1cb6573575b0b2660c2c8e384` via `.venv/bin/python -m pip wheel --no-deps --no-build-isolation`: `coga-0.4.1-py3-none-any.whl`, SHA-256 `d2550f8d46d9db8fcf7ec8be9fb8025772270013b9e67d11a5da229432f3a181`. Packaged blocker-reminders shim blob `e760d3b6992bd938f09c2c00723236748c55d27d` = source at `dcba1b1dc`.
- Owner decision: the uv tool participates. Install the wheel in both `.venv` and the uv tool for the rollout. After the ticket closes, the owner restores the uv tool to an editable source install for testing (`uv tool install --editable .`). That later restore falls outside this ticket's receipt.
- No wheel was installed in any environment. The owner reported that the "ongoing recurring" was fixed.
- What actually happened on control (`e630599faee37f27a430164e5ccbeafd3011ac8d`): sweeps were not quiesced. A sweep at 12:11 rolled the period over, which is disposition 4, not the approved retain disposition. `16423793d` (recurring create) replaced generation `7c8e61c5-…` with `f074ad63-a947-48bb-8cf9-3702b3689d4c`. `0535a9a9e` and `98252a130` ran it `in_progress` → `done` (script exit 0), and it sent blocker reminders (`18d74462a`, `88d2b107c`). The retained period's PR-827 shim never executed.
- Frozen shim on control is blob `e760d3b6992bd938f09c2c00723236748c55d27d`, byte-identical (`cmp`) to the reviewed wheel's packaged shim (SHA-256 `d2550f8d…a181`) and to `dcba1b1dc`'s source.
- Writer: the host process list shows the uv tool (`/home/n/.local/share/uv/tools/coga/bin/python`, editable install of this checkout) running `coga launch`/`coga chat` sessions, so it is a participating writer. The rollover ran from editable code at a main containing `dcba1b1dc`, not from an installed reviewed wheel. No wheel receipt exists for any writer. `.venv` was reported by the owner as not writing.
- Final runbook `recipe-shim-callers` search over `coga/recurring` and `coga/tasks` (hidden and ignored included): no hits, exit 1. `coga/recurring/skill-update` remains a carrier, and no skill-update period exists.
- Deviation for owner acceptance: the approved retain disposition and the wheel-install requirement were superseded by a live rollover from an editable writer. The end state meets the caller and shim-bytes criteria.
- Owner accepted the deviation (option 2) and chose a wheel from current control instead of `dcba1b1dc`. The `dcba1b1dc` wheel would have downgraded 41 changed `src/` files under four live uv-tool sessions. Receipt: wheel built from control `e630599faee37f27a430164e5ccbeafd3011ac8d` (contains `dcba1b1dc`) via `git archive` + `.venv/bin/python -m pip wheel --no-deps --no-build-isolation`, `coga-0.4.1-py3-none-any.whl`, SHA-256 `ed51284706d7a6d93701a14a717003399215b362916c6a181e72dff54abaeead`. Installed with `uv tool install --force <wheel>` into the uv tool (`/home/n/.local/share/uv/tools/coga/bin/python`, Python 3.14). The uv receipt and `direct_url.json` named the wheel (`archive_info`, not editable). The runbook `JOB=blocker-reminders` lookup located `site-packages/coga_edge/blocker_reminders.py` and `site-packages/coga/resources/templates/coga/recurring/blocker-reminders/ticket.py`. The installed shim (blob `e760d3b6`) matched both the wheel and control (`cmp`).
- Per the owner's option 3, the uv tool was then restored with `uv tool install --force --editable /home/n/Code/coga`. `direct_url.json` shows editable again, `coga --help` works, and the live sessions survived. `.venv` was not touched (owner: not a writer).
- Final state: legacy callers 0 (exit 1). Control's frozen shim equals the reviewed wheel's. Unresolved: none for this ticket. A stale `coga launch v1/01 --agent codex` process (pid 2392749) was still running at close and is flagged to the owner.
