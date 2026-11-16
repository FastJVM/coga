---
title: 03 Fix prompt assembly defects
status: in_progress
owner: nicktoper
contexts:
- coga-dev/microkernel/objectives
- coga-dev/principles
- coga-dev/codebase/gotchas
- coga-dev/testing
- coga-dev/microkernel
- coga-dev/project-stage
workflow:
  name: code/design-then-implement
  steps:
  - name: design
    skills:
    - code/design
    assignee: agent
    checkout: control
  - name: evaluate-design
    skills:
    - code/review-design
    assignee: other-agent
    checkout: control
  - name: review-design
    skills: []
    assignee: owner
    checkout: control
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
    checkout: create-or-reuse
  - name: peer-review
    skills:
    - code/peer-review
    assignee: other-agent
    checkout: reuse-required
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
    checkout: control
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
    checkout: reuse-required
step: 4 (implement)
agent: claude
---

## Description

Fix structural defects in the current prompt assembly (`compose.compose_prompt_report`). Owner rewrite, 2026-11-15: the experiment line ended with no positive selection (ticket 02: C1 disqualified; ticket 04: output quality inconclusive, current assembly kept), so this ticket no longer migrates to a new assembly form. Instead, it fixes defects in the current form that are visible in any captured launch prompt. Done means each defect below is fixed with unit-test coverage, a before/after `coga launch <ref> --prompt-report` (plus the full composed text) shows the change on a real ticket, and `coga/prompt-composition` describes the result.

### Defects to fix

Observed in the composed prompt for this ticket on 2026-11-15 (85 KiB, ~21.7k tokens):

1. **Template comments compose.** The ticket-guide HTML comment (`<!-- Ticket guide — keep this comment … -->`, about 5 KiB, in 83 tickets) is in `## Context` and is passed through verbatim as "Task-specific context" on every launch. Template comments must not reach the agent. The file on disk keeps the comment for human editors.
2. **Frontmatter composes.** Context and skill layers include their YAML frontmatter (`---\nname: …\ndescription: …\n---`). Its `---` delimiters are indistinguishable from the `---` separators between layers.
3. **Heading hierarchy collides.**
   - Each layer's wrapper `## <title>` is followed by the resource's own H1, so titles repeat (`## Coga base prompt` / `# Coga base prompt`, `## Repo context` / `# Context`).
   - The resources' `##` sections sit at the same level as the layer headings, so the prompt is one flat list of `##` headings.
   - The blackboard's own `## Blockers` and `## Gate status` look like top-level prompt sections.

   Make the layer boundaries unambiguous, for example by demoting headings inside each layer. The design picks the mechanism, which must stay fence-aware (no rewriting `#` lines inside code fences).
4. **Open blockers appear twice.** When the blocker preamble lists them, the blackboard repeats them under `## Blockers`. Compose them once, and keep resolved blocker history available where it matters.
5. **Template filler composes.** The blackboard placeholder ("The blackboard is a notepad to be written to often …") goes in as current state.

### Tests

Add unit tests in `tests/test_compose.py` (and fixtures as needed) that cover each defect: template comment absent from the composed prompt, frontmatter absent, heading levels inside layers below the layer level (including a fenced `#` line left untouched), blockers composed once, and filler absent. Keep the `--prompt-report` layer accounting correct. Update the seeded fixture under `tests/fixtures/seeded-repo/` if the smoke path changes.

### Scope and boundary

Change composition only. Do not change prompt resource wording beyond what the heading fix requires, the layer order, launch/checkout behavior, or `recurring_autofix.build_prompt` unless it shares the defective helper. Guided authoring (`commands.ticket._authoring_ticket`) composes through the same path: check it, and keep the ticket guide visible wherever the authoring agent needs it to edit the file. That is a design decision to record, not a guess.

### Acceptance criteria

- [ ] **Comments.** No HTML comment block from any file-backed layer reaches the prompt (`<!-- Ticket guide` is absent). A `<!--` line inside a code fence, and inline `` `<!-- … -->` `` code within a prose line, are kept verbatim. An unterminated `<!--` is left as text, never stripped to EOF. A complete comment inside `## Context`/`## Description` containing `##` lines (including `## Context`) does not truncate the section, manufacture a section, or drop visible prose after it. The ticket file on disk is unchanged.
- [ ] **Frontmatter.** No leading YAML frontmatter block from a context, skill or other file-backed layer composes; a fenced `---` example inside a layer body is untouched.
- [ ] **Headings.** The prompt has exactly one `#` heading (the task header). Every layer heading is `##`. Inside every layer body, every ATX heading outside code fences is level 3 or deeper. A resource's leading document title (e.g. `# Coga base prompt`, `# Context`, a context's `# …` H1) no longer repeats under the layer heading. Fenced `#`/`##` lines are byte-identical to the source.
- [ ] **Session conduct** keeps the selected context visible in its layer heading (`## Session conduct — attended`, etc.).
- [ ] **Blockers once.** When the blocker preamble composes, open asks appear only in the preamble; the blackboard keeps resolved entries with their `resolved:` lines and shows one pointer line where open entries were. When the preamble is off (guided authoring, `include_blocker_preamble=False`) or there are no open asks, the blackboard's blocker text composes as today (headings demoted). An unchecked entry with a later `resolved:` line counts as resolved and is kept.
- [ ] **Filler.** The stock blackboard placeholder (packaged `blackboard.md`, a repo override, or that override rendered with the ticket title) does not compose when it leads the blackboard region. A blackboard that is only the placeholder composes a blackboard layer whose body says no state is recorded yet. With a `## Superseded designs` section present, the placeholder is still removed and the archive pointer kept (tested for placeholder + history, and placeholder + live notes + history); size-warning and readiness behavior are unchanged.
- [ ] **Report accounting.** `--prompt-report` layer bytes/tokens are measured on the normalized text, and the reported total equals `len(composition.prompt.encode())`.
- [ ] **Guided authoring** follows the decision recorded under Proposed shape (strip there too) and `bootstrap/ticket` tells the authoring agent where to read the guide.
- [ ] Unit tests in `tests/test_compose.py` cover each bullet above, including the fenced and unterminated-comment edge cases; existing tests that assert literal `## …` strings inside layers are updated to the new levels; the seeded fixture is updated if the smoke path asserts changed text.
- [ ] Before/after evidence on this ticket's blackboard: per-layer report and total for this ticket, at the base commit and at the PR head (baseline below), plus the full composed text of both saved as ticket attachments or quoted excerpts showing each defect gone.
- [ ] `coga/prompt-composition` is updated in the same PR (see Proposed shape §6), and `coga-dev/internals/compose` where it describes `_extract_section`/blackboard projection.
- [ ] Full Linux suite run with receipt per `coga-dev/testing`; native checks recorded as deferred to release.

### Proposed shape

1. **One layer-text normalizer in `src/coga/compose.py`.** Add a private pure function, e.g. `_prompt_text(text: str, *, drop_title: bool) -> str`, applied when each `PromptLayer` is *constructed* (so `text`, `rendered`, the report and the prompt agree). Steps, in order, all line-based over `taskfile.markdown_lines` so fenced lines are never touched:
   1. Strip a leading frontmatter block (same shape as `skill._FM_RE`: `---` at byte 0 through the next `---` line).
   2. Remove HTML comment blocks: a non-fenced line whose content after ≤3 spaces starts with `<!--`, through the first line containing `-->`, provided nothing but whitespace follows that `-->`. Drop one blank line following a removed block. Leave an unterminated opener as text.
   3. If `drop_title`: when the first non-blank line is an ATX heading, it is the only heading at the shallowest level in the body, drop it (it is the document title the layer heading replaces).
   4. Demote: let `m` be the shallowest remaining ATX heading level outside fences; shift every such heading by `max(0, 3 - m)`, clamping at 6. Only demote, never promote. Setext headings are not rewritten (blackboards use `---` as a separator; this matches `blackboard._without_superseded_designs`).
2. **Which layers get what.** `drop_title=True` for the fixed resources (`prompt.md`, `prompt-ticket.md`, conduct, `prompt-blocker-resolution.md`), repo `context.md`, ticket contexts, and skills (`_skill_layers`, `_step_layers` skill branch). `drop_title=False` for workflow inline instructions, `## Description`, `## Context`, and the blackboard (their first heading is content, not a title). The header and checkout notice are generated and not normalized. Steps 1–2 run on every file-backed layer; that is one rule ("HTML comments and frontmatter never compose") rather than a ticket-only special case. For the ticket regions, comment removal must also run *before* extraction: apply step 2 to the above-fence body (from `split_body`) before `_extract_section`, in composition only, so a complete comment containing `##` lines neither truncates `## Context` nor manufactures a composed section, and visible prose after it survives. `taskfile.body_sections`, validation and the file on disk are unchanged.
3. **Session conduct.** Stop treating the conduct layer as `raw`. Take its title from the resource's leading heading text (fallback `Session conduct` when it has none), then normalize with `drop_title=True`, so the heading still names the selected context and its body sits below it. The header layer stays `raw`.
4. **Blockers once** (`src/coga/blackboard.py`). Add a pure `without_open_blockers(text: str, pointer: str) -> str` that removes exactly the lines `parse_blockers_text` reports as open — checkbox `- [ ]` entries, and legacy entries not followed by a `resolved:` line — using the same regexes, the same superseded-designs projection and `markdown_lines` fencing, and inserts `pointer` once at the first removed position. Open/resolved follows the parser's *final* state: an unchecked `- [ ]` entry followed (even after intervening prose or fenced lines) by a `resolved:` line is resolved and stays. In `compose_prompt_report`, compute `open_asks` from the projected blackboard as today; only when the preamble layer is appended, pass the blackboard text through `without_open_blockers` with a pointer such as `- Open asks are listed under "Resolve the open blocker first" above.` before building the blackboard layer.
5. **Filler** (`src/coga/blackboard.py`). Add `without_stock_placeholder(text: str, *, cfg: Config | None, task_title: str) -> str` that removes a leading block equal (after `lstrip`) to the packaged `blackboard.md`, the raw override, or `render_blackboard(task_title, cfg=cfg)`, only when the match ends at end-of-text or a line break. Reuse the candidate set behind `_is_stock_blackboard` rather than a second definition. Call it in `compose_prompt_report` on the raw blackboard region *before* `blackboard_for_prompt`, because that projection prepends a superseded-designs archive pointer when it removes history, after which the placeholder no longer leads; the pointer is retained. When the region exists but the result is blank, compose the blackboard layer with a one-line body (e.g. `*No state recorded yet.*`) instead of omitting it — the ticket loop tells the agent the blackboard is "composed into this prompt below". Leave `blackboard_size_warning` and `_is_stock_blackboard` behavior unchanged.
6. **Contract.** In `coga/prompt-composition`: replace "read **whole**: `SKILL.md` frontmatter … is included" with the normalization rule (frontmatter and HTML comments dropped; document title dropped; headings demoted under the `##` layer heading; fences untouched); add HTML comments and frontmatter to "What never composes"; state in "Blocker preamble versus authoring" that open asks compose once (preamble) and resolved history stays in the blackboard, and that authoring (preamble off) shows them in the blackboard; state that the stock placeholder never composes. Mirror the implementation notes in `docs/contexts/coga-dev/internals/compose/SKILL.md`.
7. **Guided authoring decision.** Strip the guide there too (no new compose flag). The authoring agent must read `ticket.md` before editing it, and the guide is only useful next to the text it governs. Change one clause in `bootstrap/ticket` "Before the interview" to say the guide is in the ticket file and launch prompts omit HTML comments, so read the file. Tradeoff: relies on the agent reading the file (which editing requires) instead of threading a `keep_comments` flag through `launch.run_agent_session` → `compose_prompt`. Owner confirmed 2026-11-15.
8. **Order of work.** Normalizer + its unit tests → wire into layers and update existing literal-heading assertions → conduct title → blocker dedupe → filler → contract docs → before/after evidence → full suite.

### Out of scope

- Prompt resource wording (the normalizer makes the heading fix without resource edits), layer order, the `---` layer separator, launch/checkout behavior, `recurring_autofix.build_prompt` (it builds its own string and shares no helper).
- Composing `## Blocker reminders` (CLI-maintained fingerprints) differently; noted as a possible follow-up.
- Setext heading rewriting; inline (mid-line) HTML comments.
- Changing what `blackboard_size_warning` measures or `_is_stock_blackboard`'s readiness semantics.
- Any new assembly form from tickets 02/04.

## Context

Prior scope: this ticket was drafted to migrate to an experimentally selected assembly form. It is now ineligible, because tickets 02 and 04 produced no positive selection. Their evidence is `coga/tasks/v1/microkernel/03-prompt-assembly/02-compare-current-and-candidate-prompt-assembly/report.md` and `…/04-compare-prompt-assembly-output-quality/report.md`. That scope is dropped and is not to be revived here.

Implementation source: `src/coga/compose.py` (`compose_prompt_report`, `_section`, `_extract_section`, `_skill_layers`, `_step_layers`), `src/coga/taskfile.py` (`split_body`, `body_sections`) and `src/coga/blackboard.py` (`blackboard_for_prompt`). Reproduce the defects with `coga launch <ref> --prompt-report` and with `compose.compose_prompt(cfg, ref, read_ticket(ref))` for the full text.

The contract owner is `src/coga/resources/templates/coga/bootstrap/contexts/coga/prompt-composition/SKILL.md` ("Layer order", "What each layer reads", "The ticket is a three-region extract", "Blocker preamble versus authoring", "What never composes"). Update it in the same PR.

Codebase facts the design relies on (verify after drift; symbols, not lines):

- `PromptLayer.rendered` wraps non-raw text with `_section(title, text)` (`## <title>\n\n<body>`), and `byte_count`/`approx_tokens` measure `rendered`; `PromptComposition.prompt` joins rendered layers with `\n\n---\n\n`. Normalizing `text` at construction therefore keeps the report consistent.
- The header layer (`# Coga task — …`) and the conduct layer are `raw=True` today; conduct relies on its resource's own `## Session conduct — <context>` line. `prompt.md`, `prompt-ticket.md` and `prompt-blocker-resolution.md` start with `#` titles equal to their layer titles; repo `coga/context.md` starts with `# Context`.
- Contexts and skills are read with `read_text` whole in `compose_prompt_report` and `_skill_layers` / `_step_layers`; `skill._FM_RE` is the existing frontmatter shape.
- `taskfile.markdown_lines` is the shared fence-aware line reader (unclosed opener = plain text); `blackboard._without_superseded_designs` deliberately ignores setext.
- The blocker preamble's `open_asks` come from `blackboard.parse_blockers_text` over the already-projected blackboard (`blackboard_for_prompt`), which matches entries anywhere in the region, not only under `## Blockers`. `without_open_blockers` must use the same matching so "listed in the preamble" and "removed from the blackboard" are the same set.
- `blackboard._is_stock_blackboard` already recognizes the packaged stub, a raw override, and a title-rendered override (as a whole region); `render_blackboard` renders the override.
- Guided authoring: `commands.ticket._authoring_ticket` projects `skills: [bootstrap/ticket]`, drops `step`, and `_run_authoring_session` calls `launch.run_agent_session(..., include_blocker_preamble=False)`, which reaches `compose_prompt`. `bootstrap/ticket` "Before the interview" currently says "Read it and keep it" of the guide.
- Other HTML-comment users: `<!-- coga:blackboard -->` is never in a composed region (split off by `split_body`); `<!-- coga:recurring-state -->` sits above the fence outside `## Description`/`## Context`; the one in `coga/recurring/templates` is inside a code fence. Some tickets carry `<!-- Moved from … -->` provenance comments; stripping them is intended.
- Existing tests in `tests/test_compose.py` (and `test_launch`, `test_megalaunch`, `test_packaging`) assert literal strings such as `"## Evaluator review"` or `"Session conduct — attended"`; demotion changes the former.

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

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design (2026-11-15, design session)

Spec written under `## Description` (Acceptance criteria / Proposed shape / Out of scope) and `## Context`. Core idea: one fence-aware normalizer applied to every file-backed layer (drop frontmatter, HTML comment blocks, the document title; demote headings so bodies sit at `###`+ under `##` layer headings), plus two blackboard projections (open blockers removed when the preamble lists them; stock placeholder removed).

Baseline (before), `compose_prompt_report` for this ticket at `2d28c451b` (run via Python; `coga launch --prompt-report` is not run inside a launch): total 83,789 bytes / ~20,923 tokens; 57 lines starting `## `, 11 starting `# `; 7 frontmatter `name:` lines; guide comment and filler both present. Per layer: header 261, base_prompt 3680, ticket_loop 3180, session_conduct 1736, repo_context 295, contexts 5882/5439/11564/20586/9964/3303, workflow_skill 5359, task_description 3243, task_context 6246, blackboard 2712, checkout 234. (This ticket's own Description/Context grew in this session, so re-measure the base from the implement branch's merge base.)

## Owner review (2026-11-15, review-design)

Open questions resolved:

1. **Guided authoring:** strip there too; edit one clause of `bootstrap/ticket` (no `keep_comments` flag).
2. **Dropped document titles:** drop; the layer heading names the ref only.
3. **Comment scope:** every file-backed layer.
4. **Placeholder-only blackboard:** one-line "no state recorded yet" layer, kept as proposed (not separately asked; owner may override before implement).

Evaluator must-fix 1 and 2 accepted and written into Proposed shape §2 and §5 plus the Comments/Filler criteria; the blocker final-state recommendation is in §4 and the Blockers criterion. Title renamed to "03 Fix prompt assembly defects" at owner request.

## Rescoped (2026-11-15, owner, from 04's report-to-coga session)

- 04 ended **inconclusive** (baseline 4, C1′ 3, tie 1); the current assembly is kept. No positive selection, so the old migration scope is dead.
- The owner rewrote this ticket to fix the current assembly's defects, seen in a captured `--prompt-report` and the full composed text, and asked for unit-test coverage. The body above is the new scope.
- The title is still the old one ("03 Implement the proven prompt assembly"). It is a frontmatter field, so the owner changes it.
- The gate notes below are historical.

## Gate status (2026-11-13, design session)

- Launched without a positive selection: ticket 02 ended with C1 disqualified (owner, 2026-11-13). No spec written.
- Owner clarified that "better" means better output (PRs, documents); 02 measured rule compliance only, never output quality.
- New prerequisite drafted: `v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality` (`draft-for-human`, owner's blinded judgment as primary measure, 02's gates kept hard).
- PR #1234's ruling should state that 02 did not measure output quality; owner to comment there and run an assist on that ticket.
- Parked by owner request until 04 records a positive selection.

---

## Blockers

- [x] [2026-11-13 23:26] [agent:claude] id=20261113T232634 Parked at owner request: no positive selection. Waiting on v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality to record a positive output-quality selection before design can start.
  resolved: [2026-11-15 18:15] [human:nicktoper] Owner rescoped 2026-11-15: 04 ended inconclusive (no positive selection), so the migration gate is dropped. Ticket now fixes current-assembly defects (template comments, frontmatter, heading collisions, duplicate blockers, filler) with unit tests.

- [x] [2026-11-14 18:48] [agent:claude] id=20261114T184855 Still no positive selection (checked 2026-11-14). v1/microkernel/03-prompt-assembly/04-compare-prompt-assembly-output-quality has 16 runs complete, every gate passed, and its blind pack built; it is at step human-owns-and-finishes. Owner: fill blind/verdicts.csv for the 8 pairs, then unblind and record positive, negative or inconclusive. Design starts only on a positive selection.
  resolved: [2026-11-15 18:15] [human:nicktoper] Owner rescoped 2026-11-15: 04 ended inconclusive (no positive selection), so the migration gate is dropped. Ticket now fixes current-assembly defects (template comments, frontmatter, heading collisions, duplicate blockers, filler) with unit tests.

## Evaluator review

Cold design review, 2026-11-15. Reviewed at `ad44e15d584e180b78c1ff0da99e5e516a061677`; fetched origin/main before review and handoff, with no intervening relevant drift. Verdict: **resolve the two must-fix projection-order cases before implementation**. The scope is coherent, the named symbols and guided-authoring path exist, intent/acceptance live in the composed body regions, and the frozen workflow correctly routes the next step to owner review. No implementation, branch, or PR produced.

### Must fix

1. **Strip comments before ticket section extraction, without changing on-disk parsing contracts.** Proposed shape §1–2 normalizes each extracted layer only when constructed, but `compose._extract_section` first calls `taskfile.body_sections`, which ignores fences, not HTML comments. Reproduction against current code: `## Context\n\nVisible.\n\n<!-- hidden\n## Example\nsecret\n-->\n\nVisible tail.\n` extracts only `Visible.\n\n<!-- hidden`. The proposed unterminated-comment preservation then leaks the opener, and visible prose after the comment is lost. A comment containing `## Context` can also manufacture a composed section. Specify a composition-only comment-removal pass over the above-fence body before `_extract_section` (or an equivalent comment-aware extraction), preserving fenced/inline comments and truly unterminated openers. Add regressions with section headings inside a complete comment and visible prose after it. Keep general ticket parsing/validation changes outside scope unless deliberately authorized.

2. **Remove a leading placeholder before adding the superseded-history pointer.** Proposed shape §5 calls `without_stock_placeholder` immediately after `blackboard_for_prompt`. In `blackboard.blackboard_for_prompt`, any removed `## Superseded designs` section causes an archive pointer to be prepended. Reproduction: packaged stub + `\n\n## Superseded designs\nOld.\n` projects to pointer + stub; the proposed leading-only matcher cannot remove the stub, despite it leading the stored blackboard region. Specify the order or coordinate the projections so the placeholder is removed and the archive pointer retained. Test stock-only live state plus superseded history, and stock + live notes + superseded history. Do not change size-warning/readiness semantics incidentally.

### Recommendations and owner decisions

- The guided-authoring choice in Proposed shape §7 is concrete and consistent with `commands.ticket._authoring_ticket` / `_run_authoring_session`: stripping there too avoids another compose flag. Owner should resolve the listed Open Questions against the body before handing off; the evaluator does not approve them on the owner's behalf.
- For blocker deduplication, test checkbox entries with a following `resolved:` line as well as legacy entries: `blackboard.parse_blockers_text` marks either form resolved when that line is encountered, even when the checkbox remains unchecked. Its pending entry survives intervening prose/fenced lines. The removal projection must follow the parser's final resolved state, rather than treating every unchecked line as open.
- This ticket currently has resolved blockers only. Its before/after capture can demonstrate resolved-history preservation, but use a controlled test fixture/capture for open-ask deduplication rather than manufacturing live blockers in the ticket.

Verification: inspected composition, shared Markdown parsing, blocker parsing/stock recognition/archive projection, guided-authoring callers, packaged authoring skill/workflow, contract topics, and relevant compose tests. Ran two read-only Python reproductions above using `.venv/bin/python`; no product code changed, so no full-suite run is claimed or required for this design-only review. Implementation still owes the Linux receipt and release-deferred native checks required by the ticket.
