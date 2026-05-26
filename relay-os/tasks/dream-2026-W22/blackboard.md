The blackboard is a notepad to be written to often as the human and agent works through a task.

## Run state

- Started: 2026-05-25
- Mode: interactive (Nick at terminal)
- Branch base for PRs: `origin/main`
- Parent task dir committed to local main (not pushed): `4caffa8`

## Phase 1 — validate-drift

- Child task: `dream-w22-validate-drift` (script, done)
- Result: 14 issue(s) — 0 direct-fix, 0 PR-proposal, 14 human-needed
- All 14 are draft tickets missing a `workflow:` field. Without one they can't be activated by `relay mark active`. The script's safe-repair pass intentionally does not synthesize workflows (a workflow choice is human design judgment).
- Affected draft slugs: `add-always-on-context-tier`, `add-browser-skill-for-automating-tasks-click-test`, `add-killer-demo`, `autotrigger-ticket-type`, `improve-readme-and-doc`, `install-init-skills-via-skill-downloader`, `launch-tasks-in-container-or-vm`, `pass-secrets-to-skills-with-per-skill-scope`, `plan-second-wave-dream-workers`, `recurring-task-for-relay-dev-udpate`, `rewrite-slack-messages`, `stream-agent-progress-in-auto-mode-and-recurring-l`, `token-budget-aware-idle-execution-of-low-priority`, `use-slack-as-a-sync-channel-for-tickets`
- Disposition: Phase 6 — these are real `gap`-style findings (draft work that needs a workflow before it can move). They will get routed by the disposition pass; no single Dream PR can fix them because each one needs a per-ticket human design call.

## Findings

### Phase 2 — knowledge scan

#### Stale

**S1. Bootstrap architecture context lags live one**
- Target: `relay-os/bootstrap/contexts/relay/architecture/SKILL.md`
- The bundled bootstrap copy still describes Dream as an ad-hoc `relay dream` task and references the `bootstrap/dream`/`dream.md` prompt resource. The live `relay-os/contexts/relay/architecture/SKILL.md` describes Dream as a recurring template under `relay-os/recurring/dream/` with an alias. The bootstrap copy also omits ticket-frontmatter extensions, the workflow-at-activation gate, the `RELAY_*` script-mode env vars, and the new `mode: script` worker shape. The live override hides this, but `relay init --update` ships the stale copy to other repos.

**S2. relay/cli context still credits `relay status` with automerge**
- Target: `relay-os/bootstrap/contexts/relay/cli/SKILL.md` (~191-194, ~369-370)
- The merged `move-automerge-out-of-relay-status` removed the opportunistic automerge call from `relay status`, but the bundled cli context still says "`relay status` also calls it opportunistically" and "(also fires automatically on `git pull` and from `relay status`)". Update to drop the `relay status` caller and describe the explicit-`relay automerge` + `post-merge` hook surface only.

**S3. relay/sync context lists status as automerge caller**
- Target: `relay-os/contexts/relay/sync/SKILL.md` (~29, ~127)
- Still describes the automerge broadcast as covering "`relay status` callers that wrap it" and lists `automerge.auto_bump_merged` "called by `commands/automerge.py` and opportunistically by `commands/status.py`". The status caller is gone; only `commands/automerge.py` (and the `post-merge` hook) remain.

**S4. Bootstrap orient attaches relay/cli broadly vs ticket-skill's selection contract**
- Target: `relay-os/bootstrap/orient/ticket.md` vs `bootstrap/ticket` skill's "context selection contract"
- `bootstrap/ticket` tells authors not to attach broad orientation contexts by default and to copy specific facts into `## Context` instead. The orient shim itself attaches `relay/architecture`, `relay/principles`, and `relay/cli` to every ad-hoc session. Either explicitly exempt orient or narrow orient's inclusion. Surfaced by review on `measure-relay-prompt-scope-and-agent-precision`.

#### Gap

**G5. No "exploration / concept-capture draft" supported state documented**
- Target: `relay-os/contexts/relay/architecture/SKILL.md` (Two state machines / draft section) or new `relay-os/contexts/relay/draft-shapes/SKILL.md`
- Dream W21 (12) and W22 (14) validate-drift runs are dominated by `missing-workflow` warnings on concept-capture drafts — an intentional authored state, not authoring drift, and the validator keeps re-flagging them every Dream. Open ticket `resolve-missing-workflow-validator-vs-concept-capt` proposes a fix but until then nothing documents that "workflow-less draft" is a supported product state.
- Draft outline: heading "Workflow-less drafts (concept capture)"; 2-3 bullets covering legitimacy, activation refusal, concept-capture-then-spawn lifecycle, and the validator-flagging gap.

**G6. No place documents "broad contexts as labels" anti-pattern**
- Target: `relay-os/contexts/relay/architecture/SKILL.md` (Prompt composition) or new `relay-os/contexts/relay/prompt-scope/SKILL.md`
- Final blackboard of `measure-relay-prompt-scope-and-agent-precision` captures a load-bearing correction: "ticket creation should not attach broad contexts as labels. It should select exact context payload that must be included, and process knowledge should stay in workflow step `skill:` refs." This now lives only inside `bootstrap/ticket`'s body. It is a domain fact about prompt composition that generalizes — agents touching contexts directly need it. The 35.8 KiB → 25 KiB measurement is concrete recurrence evidence.
- Draft outline: heading "Contexts are prompt payload, not tags"; 3 bullets — attach only contexts whose body must be read; copy a single fact into `## Context` instead of attaching the whole; skills attach via workflow steps, not `contexts:`.

**G7. No context-level guidance on `bootstrap/ticket` in skills frontmatter**
- Target: `relay-os/contexts/relay/architecture/SKILL.md` or extend `bootstrap/ticket` skill body
- Six open drafts (`add-always-on-context-tier`, `add-browser-skill-for-automating-tasks-click-test`, `autotrigger-ticket-type`, `pass-secrets-to-skills-with-per-skill-scope`, `token-budget-aware-idle-execution-of-low-priority`, `use-slack-as-a-sync-channel-for-tickets`) carry `skills: [bootstrap/ticket]` directly. That field is for ticket-level skills, but `bootstrap/ticket` is the authoring interview and only makes sense via the launch shim. `bootstrap/ticket` step 5 tells authors to remove this when found — but the rule is buried in one skill body, no architecture-level guidance.
- Draft outline: one sentence under architecture "Primitives" / "Canonical ticket frontmatter": `skills:` is for ticket-level refs only; `bootstrap/ticket` is launch-shim-only.

**G8. "Design pivot in blackboard" convention is undocumented**
- Target: `relay-os/contexts/dev/code/SKILL.md` or new `relay-os/contexts/relay/blackboard-conventions/SKILL.md`
- `move-automerge-out-of-relay-status` shows the pattern: ticket `## Description` is rewritten after a major pivot, blackboard preserves the prior design under `## Design decision (date) — SUPERSEDES the X plan`. Several open drafts (`autotrigger-ticket-type`, `debug-surface-for-recurring-tasks-streamed-output`) carry the same pattern. Convention exists in practice; only `dev/code`'s `## Dev` section is documented.
- Draft outline: section "Design pivots and superseded plans" in `dev/code`; 2-3 bullets on intent-only ticket body, dated SUPERSEDES blackboard heading, ticket-body callout pointer.

**G9. No skill for "split-into-sibling-ticket" discipline**
- Target: new `relay-os/skills/code/split-ticket/SKILL.md` (or section in `code/design`)
- `move-automerge-out-of-relay-status` + its sibling `remove-the-post-merge-automerge-git-hook` show a repeated discipline: when a design exceeds one PR, split into ≥2 sibling tickets and record the split in the blackboard under `## Split`. `code/implement` / `code/design` say "stop and split the ticket on the blackboard" without defining the mechanic — what filename, blackboard section, cross-link convention.
- Draft outline: section "Splitting a ticket"; bullets on when (PR too big, concerns coupling), how (scaffold sibling drafts, cross-link under `## Sequencing` / `## Split`), and the cross-link convention.

**G10. Recurring template lives in two places, no sync convention captured in contexts**
- Target: `relay-os/contexts/relay/recurring/SKILL.md` or `relay/codebase/SKILL.md`
- The recurring template body under `relay-os/recurring/<name>/ticket.md` IS the run prompt. The "live + packaged" mirror rule is in `CLAUDE.md` but absent from `relay/recurring` and `relay/codebase`. New recurring authors won't know to keep `src/relay/resources/templates/relay-os/recurring/<name>/ticket.md` in sync; `relay init --update` re-introduces drift.
- Draft outline: bullet under `relay/recurring` "Gotchas" — Relay-shipped recurring templates have a packaged twin; edits must be mirrored.

#### Extract (done tickets → context/skill area)

Grouped by target area for Phase 4 batching:

**Area: relay/principles + relay/sync (command-shape principle)**
- **E11. Read-only commands must not mutate state** (from `move-automerge-out-of-relay-status`) → `relay-os/contexts/relay/principles/SKILL.md` (under "Fail loud" or new "Command shape"). Ticket body and final blackboard articulate the principle Nick added to the canon: read-only-looking commands must not mutate state or shell out to the network silently. Sharper than current principles text. **Overlap note:** stale findings S2 and S3 also touch `relay/sync` / `relay/cli` — Phase 4's knowledge PR covering this extract should consume those stale fixes too rather than opening parallel PRs.

#### Phase 2 done-ticket roster (Retro inputs)

- `move-automerge-out-of-relay-status` — durable knowledge (extract E11), with S2/S3 overlap; Phase 4 PR consumes both.
- `dream-w21-validate-drift` — no new durable knowledge; the recurring `missing-workflow` evidence is captured by gap G5 / open ticket `resolve-missing-workflow-validator-vs-concept-capt`. Expect `no-new-durable-knowledge` + prune.
- `dream-w21-cleanup-orphan-markers` — same as above: no new durable knowledge.
- `dream-w22-validate-drift` — same.

### Phase 3 — contract audit

#### Drift

**D1. `recurring/dream.md` named as file instead of directory**
- Target: `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/cli/SKILL.md:21,297`; `relay-os/bootstrap/contexts/relay/cli/SKILL.md:21,291`; `src/relay/resources/templates/relay-os/relay.toml:65`
- Source of truth: artifact — `relay-os/recurring/dream/` is now a directory; the scanner refuses bare-file recurring shapes.
- Three shipped docs reference `recurring/dream.md` as if it were a single file. Recurring tasks were migrated to ticket-format directories (`relay-os/recurring/<name>/ticket.md`).

**D2. `relay panic` claims to release a task lock**
- Target: `README.md:498`; `relay-os/bootstrap/contexts/relay/cli/SKILL.md:273`
- Source of truth: code — no `task.lock` exists in `src/relay/`; `relay/project-stage` and `relay/architecture` confirm the lock was removed. README itself says "no lock" at line 391.
- Both docs claim `relay panic` "releases the lock." The lock mechanism was removed; status is the sole signal. README is internally inconsistent.

**D3. `cli/SKILL.md` listed as canonical but missing**
- Target: `CLAUDE.md:10`; `AGENTS.md:10`
- Source of truth: artifact — `relay-os/contexts/relay/` has `architecture`, `codebase`, `current-direction`, `principles`, `project-stage`, `recurring`, `sync`. No `cli/`. The only on-disk `cli/SKILL.md` is under `relay-os/bootstrap/contexts/relay/cli/`.
- Both agent-instruction files list `cli/SKILL.md` alongside the canonical relay contexts. A reader following these instructions will not find it where listed.

**D4. `example/projects/*/relay-os/` cited as fixture but absent**
- Target: `CLAUDE.md:17`; `AGENTS.md:17`
- Source of truth: artifact — `example/projects/` does not exist; only `example/relay-os/` is present.
- Both files instruct contributors to use `example/relay-os/` and `example/projects/*/relay-os/` as the seeded fixture. The second path is dead.

**D5. `launch.py` / `launch_script.py` / `panic.py` cited as top-level modules**
- Target: `relay-os/contexts/relay/codebase/SKILL.md:24-27`
- Source of truth: code — these files live at `src/relay/commands/`, not `src/relay/`.
- The codebase context names `launch.py` and `launch_script.py` bare and inconsistently prefixes `panic.py`. A reader using this as a source-tree map looks in the wrong directory.

**D6. `relay feed` referenced but does not exist**
- Target: `relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md:213`
- Source of truth: code — no `relay feed` in `src/relay/cli.py` or `commands/`.
- The ticket skill suggests `relay feed --task <slug> --message "<short>"` for an FYI. The current surface is `relay slack`.

**D7. Nonexistent ticket cited as concrete example**
- Target: `relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md:20`
- Source of truth: artifact — `relay-os/tasks/fix-relay-status-narrow-terminal-table-wrapping/` does not exist.
- The ticket skill cites that path as a real reference example for slug shape. The citation is dead.

**D8. Worker skill calls Retro "Phase 3"**
- Target: `relay-os/bootstrap/skills/bootstrap/dream/tasks/cleanup-orphan-markers/SKILL.md:12-13`
- Source of truth: artifact — `relay-os/recurring/dream/ticket.md` (this task's template) numbers Retro as Phase 4 and contract audit as Phase 3.
- The orphan-markers skill explains markers "belong to the Phase 3 Retro pass." Phase numbering disagrees with the Dream template.

**D9. `recurring launch <name>` says "file stem" not "directory name"**
- Target: `relay-os/bootstrap/contexts/relay/cli/SKILL.md:320`
- Source of truth: copy — contradicts `relay-os/contexts/relay/recurring/SKILL.md:34` ("`<name>` is the directory name") and on-disk reality.
- Two canonical contexts disagree on the same identifier.

#### Overlap with Phase 2 stale findings
- S1 (bootstrap architecture context) and D1/D2/D9 all touch `relay-os/bootstrap/contexts/relay/cli/SKILL.md` and the bootstrap copy. Phase 6 should batch them into one bootstrap-context refresh PR rather than open four parallel PRs against the same file.
- S2/S3 (relay/sync and relay/cli automerge text) overlap E11 (extract from `move-automerge-out-of-relay-status`). Phase 4's knowledge PR for E11 should consume S2 and S3.

### Phase 4 — Retro

- Eligible done tickets processed (4): `move-automerge-out-of-relay-status`, `dream-w21-validate-drift`, `dream-w21-cleanup-orphan-markers`, `dream-w22-validate-drift`.
- PR opened: **#216 — "New principle: read-only commands stay read-only"** (https://github.com/FastJVM/relay/pull/216). Sources: `move-automerge-out-of-relay-status`. Pruned (folded into `## Pruned`): `dream-w21-validate-drift`, `dream-w21-cleanup-orphan-markers`, `dream-w22-validate-drift`.
- **Important discovery during Phase 4:** the `move-automerge-out-of-relay-status` ticket was marked `status: done` by the human, but the actual code change (removing the `auto_bump_merged` call from `commands/status.py`) **was never landed** — `src/relay/commands/status.py:79` still calls `auto_bump_merged`. This means Phase 2 findings **S2 and S3 are NOT actually stale** — the cli/sync contexts that say "`relay status` calls automerge opportunistically" are still accurate against current code. Phase 4 correctly deferred the S2/S3 fold-in. Surfaced for reviewer attention on PR #216.

### Phase 5 — cleanup-orphan-markers

- Child task: `dream-w22-cleanup-orphan-markers` (script, done).
- Result: **no-op** (0 orphan markers). PR #216 deletes its 4 source tickets in the same PR, so nothing was left for orphan cleanup to find.

### Phase 6 — disposition

#### Gap draft tickets created (6, all `status: draft`, workflow `code/with-review`)

- `document-workflow-less-concept-capture-drafts-as-s` (G5)
- `document-contexts-as-prompt-payload-not-tags-princ` (G6)
- `document-bootstrap-ticket-not-in-skills-frontmatte` (G7)
- `document-design-pivot-in-blackboard-convention` (G8)
- `skill-for-split-into-sibling-ticket-discipline` (G9)
- `document-recurring-template-live-vs-packaged-sync` (G10)

#### Proposal PRs opened (6)

- **#217** "Refresh bootstrap cli context for current code reality" (D1, D2, D9)
- **#218** "Fix dead canonical-context and fixture paths in agent instructions" (D3, D4)
- **#219** "Point codebase context at src/relay/commands/ for moved modules" (D5)
- **#220** "Replace relay feed wording and dead example ticket in bootstrap/ticket" (D6, D7)
- **#221** "Renumber Retro as Phase 4 in cleanup-orphan-markers skill" (D8)
- **#222** "Narrow bootstrap/orient context attachment by exempting it in ticket skill" (S4)

#### Findings demoted to no-op (4)

- **S1** — phantom finding. The bundled bootstrap copy at `relay-os/bootstrap/contexts/relay/architecture/SKILL.md` is `.gitignore`d locally; `relay-os/.gitignore:14` excludes the `bootstrap/` tree. The source of truth is the packaged twin at `src/relay/resources/templates/relay-os/bootstrap/contexts/relay/architecture/SKILL.md`, which is byte-identical to the live override `relay-os/contexts/relay/architecture/SKILL.md`. Commit `a0f6738` ("Resync packaged bootstrap relay/{architecture,sync} from live contexts") already shipped the resync. The 157-line stale copy Phase 2 read is vendored locally and is regenerated by `relay init --update`. No PR needed.
- **S2** — not actually stale. `commands/status.py:79` still calls `auto_bump_merged`, so the cli context's claim that "`relay status` calls it opportunistically" is currently true. Will become stale only when the `move-automerge-out-of-relay-status` code change actually lands.
- **S3** — same as S2. The `relay/sync` context's claim is also currently true against code.
- **E11** — handled by Phase 4 PR #216.

## Dream Run Summary

Generated: 2026-05-25 (US/Pacific)
Run mode: interactive
Branch base for all PRs: `origin/main` (at `2b9be0b` after Phase 6 inline commits)

| Phase | Result | Detail |
| --- | --- | --- |
| 1. validate-drift | reported | 14 human-needed (draft tickets missing workflow) |
| 2. knowledge scan | reported | 4 stale, 6 gap, 1 extract |
| 3. contract audit | reported | 9 drift |
| 4. retro/done-ticket | pr-opened | PR #216 (1 source, 3 pruned) |
| 5. cleanup-orphan-markers | no-op | 0 orphan markers |
| 6. disposition | proposed | 6 proposal PRs + 6 gap drafts + 4 demoted no-ops |

### Findings → durable homes (totals)

- **Knowledge PR:** PR #216 (`move-automerge-out-of-relay-status` extract).
- **Proposal PRs:** PR #217–#222 (six file/theme-scoped doc fixes).
- **Gap drafts:** six tickets under `relay-os/tasks/document-*` and `relay-os/tasks/skill-for-split-into-sibling-ticket-discipline/`.
- **Demoted no-ops:** S1 (phantom — bootstrap is gitignored), S2/S3 (not actually stale; code still does what the contexts say), E11 (absorbed by PR #216).

### Human-needed callouts

1. **PR #216 reviewer note:** the `move-automerge-out-of-relay-status` ticket is marked done but its code change isn't on origin/main. Code-reality drift between ticket lifecycle and source. Either the code change needs to land, or the ticket should be reopened.
2. **14 validate-drift human-needed warnings:** all are draft tickets missing `workflow:`. Each needs a per-ticket design call before `relay mark active` will accept it. Gap G5 (concept-capture documentation) tracks the meta-issue.
3. **PR #220 + PR #222 share a file:** both edit `relay-os/bootstrap/skills/bootstrap/ticket/SKILL.md`. Whichever merges second will need a trivial rebase.

### Slack

Posted via `relay slack --task dream-2026-W22` for each PR. Final run summary will post on `relay mark done`.
