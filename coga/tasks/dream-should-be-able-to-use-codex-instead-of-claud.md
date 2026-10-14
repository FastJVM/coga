---
title: dream should be able to use codex instead of claude
status: in_progress
owner: nicktoper
agent: claude
contexts:
- dev/code
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
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 5 (open-pr)
---

## Description

Today the only way to make Dream (and any other agent-backed recurring job,
or any newly activated ticket) run on `codex` rather than `claude` is to
reorder the `[agents.*]` tables in `coga.toml` — the "default agent" is
implicit, whichever table is declared first. Add an explicit, named
repo-wide default-agent key so an operator can switch the default to `codex`
without reordering tables, and confirm the existing
`coga recurring --agent <type>` sweep flag reaches Dream.

The key lives in shared `coga.toml` as the team default and may also be set in
machine-local `coga.local.toml`, where it wins — so one operator can switch
their machine to `codex` (e.g. while a Claude quota is exhausted) without
editing a committed file. `Config.default_agent()` honours the key first and
falls back to first-declared `[agents.*]` only when it is unset anywhere. The
proposed spelling is a top-level scalar `default_agent = "<type>"`, matching
the existing top-level `default_status = "draft"`; the design step may pick a
different shape but must justify it.

Done when: setting the key to `codex` (in either file) makes
`Config.default_agent()` — and therefore ticket activation, `coga create` into
a live status, `coga retire`'s default, the autofix fallback, and a
`coga recurring` sweep's next newly materialized Dream period task — resolve
`codex` without any `[agents.*]` reorder; a local value overrides the shared one; an unset key keeps
today's first-declared behaviour byte-for-byte; `coga recurring --agent codex`
reaching the Dream launch is covered by test (one already exists, see
Context); the contexts, docs, and docstrings named under Context that describe
the default are updated; `python -m pytest` passes and `coga validate --json`
is clean.

### Acceptance criteria

- [ ] `coga.toml` and `coga.local.toml` both accept a top-level string
      `default_agent`. It is in both `config._ALLOWED_SHARED_SECTIONS` and
      `config._ALLOWED_LOCAL_SECTIONS`.
- [ ] Precedence inside `Config.default_agent()`: local `default_agent`, then
      shared `default_agent`, then the first-declared entry of the merged
      `cfg.agents`. With the key unset in both files the result is identical to
      today's (same `AgentType`, and no new output or warnings).
- [ ] A non-string, blank, or unknown value raises `ConfigError` at
      `load_config`. The message names the file that supplied it
      (`coga.toml` / `coga.local.toml`) and lists the known types, so a typo
      fails on the next command, not mid-sweep. The value is validated against
      the **effective merged** `[agents]` table, like `[autofix] agent`.
- [ ] With `default_agent = "codex"` in either file and `claude` declared
      first, these all resolve `codex` with no table reorder (one test each, or
      a parametrized test):
      `coga mark active` stamps `agent: codex` (`mark._select_main_agent`);
      `create_task(status="active")` without an explicit agent writes
      `agent: codex` (`create._select_main_agent`);
      `commands/retire._default_agent`;
      `recurring_autofix._analyze_agent` when neither `--agent` nor
      `[autofix] agent` is set;
      `authoring.resolve_authoring_agent` when terms 1–5 are all absent;
      `bump.resolve_main_agent(cfg, None, allow_prospective_default=True)`, and
      `bump.resolve_other_agent` for an absent agent derives the peer of `codex`.
- [ ] A local value overrides a shared one (shared `claude`, local `codex` →
      `codex`). A local-only `[agents.<x>]` type may be named by a local
      `default_agent`.
- [ ] Dream: on `dream_repo` with `[agents.codex]` added and
      `default_agent = "codex"`, a bare `coga recurring` sweep materializes the
      Dream period ticket with `agent: codex`. A second test pins the freeze
      rule: an already-materialized period ticket carrying `agent: claude`
      keeps `claude` when a forced rerun in the same period reactivates it
      (`recurring_runner` → `mark_active`), even after `default_agent = "codex"`
      is set.
- [ ] `tests/test_recurring.py::test_bare_recurring_passes_agent_override_to_agent_tasks`
      stays as is (it already asserts `seen == ["codex"]`). No duplicate test.
- [ ] Interactive `coga init` makes a chosen agent the default by writing
      `default_agent = "<name>"` into the new `coga.toml`, not by reordering
      `[agents.*]` tables. `_make_default_agent`'s reorder machinery is removed
      along with its test. `_stamp_agent_into_delivered_tickets` still runs.
- [ ] The packaged `coga init` template
      `src/coga/resources/templates/coga/coga.toml` documents the key as a
      commented example beside `default_status`, and mentions the local
      override.
- [ ] Docs and docstrings are updated (canonical topics and packaged twins
      byte-identical): `coga/agents` owns the key's description, precedence,
      the local override, the freeze rule, and its relationship to
      `[authoring] agent` and `[autofix] agent`; `coga/configuration` lists the
      key in both allowlists; `coga/tickets`, `coga/recurring/autofix`, and
      `coga/init` stop saying "first-declared"/"first agent" as the whole rule;
      so do the docstrings/comments in `config.py` (`Config.default_agent`,
      the `autofix_agent` field comment, `_parse_autofix`), `create.py`
      (`_select_main_agent`), `recurring_autofix.py` (`_analyze_agent`),
      `authoring.py` (`resolve_authoring_agent`), `mark.py`
      (`_select_main_agent`'s "reordering `[agents.*]`"), and
      `commands/init.py`. A final grep for `first-declared`, `first declared`,
      `first agent`, `lists its default first` and `reorder` across `docs/`,
      `src/`, and `coga/` leaves only correct statements of the fallback.
- [ ] `python -m pytest` passes; `coga validate --json` is clean.

### Proposed shape

**Spelling: top-level scalar `default_agent = "<type>"`.** It mirrors
`default_status` (also top-level and also a create-time default). Two
alternatives were considered and rejected:
- `[agents] default = "codex"` puts a scalar inside a table whose keys are
  agent type names. `_parse_agents` currently skips non-mapping entries
  silently. This shape would make `default` a reserved type name and blur two
  namespaces.
- A new `[defaults] agent` table adds a section to hold one key.

The top-level form is one more name in each allowlist, and nothing else
changes.

**`src/coga/config.py`**
1. Add `"default_agent"` to `_ALLOWED_SHARED_SECTIONS` and
   `_ALLOWED_LOCAL_SECTIONS`. Add a comment that it is deliberately local-
   capable (unlike shared-only `[autofix]`), because which vendor a machine
   can run right now (quota, install) is an operator fact.
2. New `_parse_default_agent(shared: object, local: object, agents:
   dict[str, AgentType]) -> str | None`, modelled on `_parse_autofix`. For each
   of `("coga.local.toml", local)`, `("coga.toml", shared)`, in that order:
   - skip `None`;
   - require a non-blank `str`, else raise
     `ConfigError(f"default_agent in {source} must be a non-empty agent type name (got {value!r})")`;
   - strip it, and require it to be in `agents`, else raise
     `ConfigError(f"default_agent in {source} names {name!r}, which is not defined in [agents]. Known: {sorted(agents)}.")`.

   Validate **both** values even when local wins, so a broken shared value
   still fails on the machine that overrides it. Return the local name if
   set, else the shared name, else `None`.
3. In `load_config`, call it right after `_parse_agents`:
   `default_agent_name = _parse_default_agent(shared.get("default_agent"), local.get("default_agent"), agents)`.
   Pass the result into `Config`.
4. `Config` gets a field `default_agent_name: str | None = None`, with a
   comment like the one on `autofix_agent`. `default_agent()` returns
   `self.agents[self.default_agent_name]` when it is set, and otherwise keeps
   today's first-entry code unchanged. Update its docstring to give the
   precedence.
   - Field name: a `default_agent` field would clash with the method.
   - Check every direct `Config(...)` construction in tests. The field must
     default to `None` so they keep working.

No consumer changes. Every reader already goes through `default_agent()`.
Do not add a parallel resolver.

**`src/coga/commands/init.py`**
- Replace `_make_default_agent(coga_toml, name)` with
  `_write_default_agent(coga_toml, name) -> bool`. It inserts
  `default_agent = "<name>"` as a top-level line.
  - Where: if the template's commented example line
    (`# default_agent = "claude"`) is present, replace that line. Otherwise
    insert just before the first table header, because a top-level key must
    precede every table.
  - Guard: parse before and after with `tomllib`. Write only if the result
    equals the original data plus exactly that key. Otherwise return False,
    and keep the existing "did not … cleanly" warning path, reworded.
- `_template_default_agent` returns the template's `default_agent` when set,
  else the first-declared table, so that it matches `Config.default_agent()`.
- Delete `_TABLE_HEADER` and the span logic if nothing else uses them.
- Update `_offer_agent_cli`'s docstring and the confirm prompt wording if it
  says "first".
- The clone path (`_offer_agent_cli(None)`) is unchanged; see Out of scope.

**Template**: in `src/coga/resources/templates/coga/coga.toml`, add a
commented block after `default_status`:

```toml
# Optional: the agent type new tickets get when activated (and the fallback
# for retire, autofix, and authoring). Unset, it's the first [agents.*]
# table below. Set it in coga.local.toml to override it on one machine only.
# default_agent = "claude"
```

The live `coga/coga.toml` is already in `INTENTIONALLY_DIVERGENT_TWINS`
(`tests/test_packaging.py`), so it is not edited.

**Tests**
- `tests/test_config.py`: shared key; local override; unset fallback; local
  names a local-only type; non-string, blank, and unknown values for each file
  (the message names the file); a broken shared value fails even when local is
  valid.
- `tests/test_mark.py`, `test_create.py`, `test_retire.py`,
  `test_recurring_autofix.py`, `test_authoring.py`: one assertion each that
  the default key wins over declaration order.
- Peer flip: wherever `resolve_other_agent` is tested, with
  `[agents.codex] peer = "claude"`.
- `tests/test_recurring.py`: the two Dream tests from the acceptance
  criteria, reusing `dream_repo`, `_allow_interactive_recurring`, and
  `_patch_recurring_command_launch`.
- `tests/test_init.py`: replace
  `test_make_default_agent_reorders_the_packaged_coga_toml` with an
  equivalent test for `_write_default_agent`: the key is written, the
  `[agents.*]` order is unchanged, it is idempotent, and an unknown name or
  unparseable file is left untouched. Update any interactive-init test that
  asserts the table order.

**Docs** (canonical first, then `cp` to the packaged twin):
`docs/contexts/coga/agents/SKILL.md` (primary), `configuration`, `tickets`,
`recurring/autofix`, `init`.

Order of work:
1. config and its tests;
2. the consumer tests and the Dream tests;
3. init and its tests;
4. the template;
5. docs and twins, then the grep;
6. the full pytest run and validate.

### Out of scope

- Making Dream's skills work under `codex` (subagent and Agent-tool
  assumptions). That is a separate ticket.
- Rewriting frozen `agent:` on already-activated tickets, including an
  existing Dream period ticket, when the default changes.
- Changing the `agent: claude` pins on packaged bootstrap tickets
  (`bootstrap/ticket`, `bootstrap/orient`, `bootstrap/browser-automation`,
  `tasks/coga-build.md`). Those pins outrank `Config.default_agent()` in
  authoring precedence (term 5), so `coga ticket` and `coga chat` still open
  `claude` under `default_agent = "codex"`. See Open Questions. Document this
  in `coga/agents`. Do not change it here.
- Having `coga init` on a clone write a local `default_agent` into
  `coga.local.toml`.
- Any new CLI flag. `coga recurring --agent` and
  `coga recurring launch --agent` already exist.
- Changing `[authoring] agent`, `COGA_AUTHORING_AGENT`, or `[autofix] agent`
  semantics.

## Context

**Current mechanism.** `config.Config.default_agent` returns the first entry of
`cfg.agents` (TOML declaration order over the merged shared+local tables). Its
consumers: `mark._select_main_agent` (activation stamps `agent:` from it),
`create._select_main_agent` (via `bump.resolve_main_agent(...,
allow_prospective_default=True)` for a live create),
`commands/retire._default_agent`, `recurring_autofix._analyze_agent` (the
fallback after `--agent` and `[autofix] agent`), and
`authoring.resolve_authoring_agent`'s last term (the `coga ticket`
interviewer falls back to `Config.default_agent()`). Routing the new key through `default_agent()` itself is the
intent, so every consumer changes together with one edit — do not add a
parallel resolver.

**Why a machine-local value matters.** `config._parse_agents` merges shared
`[agents.*]` tables first, then local; a local-only type is appended last and a
local table cannot reorder shared ones. So today there is *no* machine-local way
to change the default at all.

**Every read of the default flips together.** Besides the consumers above,
`validate`, `commands/common`, `megalaunch`, `views`, `launch_script`, and
`commands/launch` call `resolve_main_agent(...,
allow_prospective_default=True)`, so status/show/compose/validate/launch
report the new default, and `resolve_other_agent` derives the peer from the main agent, so
the `other-agent` peer flips too. Cover these in tests and docs.

**Frozen period tickets keep their agent.** The Dream template
(`coga/recurring/dream/ticket.md`) sets no `agent:`; `recurring` materializes
the period task via `create_task(status="active")`, so its `agent:` comes from
`default_agent()`. But an already-materialized period ticket has `agent:`
frozen, and a forced rerun / `coga dream` in the same period reactivates it
(`recurring_runner` → `mark_active`) keeping the old agent. The key takes effect
from the next newly materialized period — pin that with a test.

**Config parsing.** Top-level tables are allow-listed in
`config._ALLOWED_SHARED_SECTIONS` and `config._ALLOWED_LOCAL_SECTIONS`; unknown
sections/keys fail via `_reject_unknown_sections` / `_reject_unknown_keys`.
The new table goes in **both** allow-lists. Model the parser on
`config._parse_autofix` (`[autofix] agent`), which already validates a named
agent type against the effective `[agents]` table at config load so a typo
fails loud there, not mid-sweep. Precedence: local value, then shared value,
then first-declared `[agents.*]`. A value naming an agent not in the effective
merged `[agents]` table must raise `ConfigError`. Design must decide: a
*shared* value naming a type defined only in some operator's local file would
fail on other clones — acceptable, or reject/warn? Note `[autofix]` is
shared-only, so a local-capable default key is a deliberate asymmetry.

**The flag already exists.** `coga recurring --agent <type>` (sweep-wide) and
`coga recurring launch <name> --agent <type>` are implemented in
`commands/recurring.py` and threaded as `agent_override` through
`recurring_runner`. `coga dream` is an alias for `coga recurring launch dream`.
The human's ask is specifically the `coga recurring --agent` sweep form. No new
flag is expected. `tests/test_recurring.py::test_bare_recurring_passes_agent_override_to_agent_tasks`
already runs `coga recurring --agent codex` on the `dream_repo` fixture and
asserts the override reaches the launch — extend it only if it does not
assert the launched agent is `codex`; do not duplicate it.

**`coga init` reorders tables today.** `commands/init._offer_agent_cli` /
`_make_default_agent` make a detected agent CLI the default by moving its
`[agents.*]` table first in the new `coga.toml`. Design must decide whether
init writes the new key instead (simpler, and the reason the key exists) or
keeps reordering; `coga/init` documents the current behaviour.

**Precedence with other agent knobs, for docs.** `--agent` > `[autofix] agent`
> new default key > first-declared, for the autofix analyst. For a recurring
agent-backed launch: `--agent` > the period ticket's `agent:` (stamped from
`default_agent()` at activation). Frozen `agent:` on already-activated tickets
is not rewritten by changing the default — same rule as reordering today.

**Contexts/docs to update (read and edit, not attached).** Each has a packaged
twin under `src/coga/resources/templates/coga/bootstrap/contexts/coga/`
(byte-identity enforced by `tests/test_packaging.py`):
- `docs/contexts/coga/agents/SKILL.md` — owns the default ("The first declared
  type is the default … so a team lists its default first"). Primary owner of
  the new key's description.
- `docs/contexts/coga/configuration/SKILL.md` — owns the top-level key set and
  the "Unknown keys fail loud" rule; add the key and its local/shared
  precedence.
- `docs/contexts/coga/tickets/SKILL.md` — the `agent` field paragraph
  ("first agent in merged config") and the authoring-agent precedence list.
- `docs/contexts/coga/recurring/autofix/SKILL.md` — the "Which agent type
  analyzes" precedence bullet.
- `docs/contexts/coga/init/SKILL.md` — the paragraph on init reordering the
  chosen agent's table first.
- `src/coga/resources/templates/coga/coga.toml` (the `coga init` template) —
  add a commented example.
- Docstrings/comments saying "first-declared": `Config.default_agent`,
  `config.py` near the `[autofix]` parser, `create.py`, `recurring_autofix.py`,
  `authoring.py`, `commands/init.py`.
Grep `first-declared`, `first declared`, `first agent` across `docs/`, `src/`,
and `coga/` before finishing.

**Related, not in scope.** The landed `add-an-agent-picker-for-recurring` work
added a machine-local `[authoring] agent` key and `COGA_AUTHORING_AGENT` for
the `coga ticket` interviewer; its last fallback is `Config.default_agent()`,
so the new key also changes the default interviewer when nothing more specific
is set. Keep `[authoring] agent` independent and document the relationship in
`coga/agents`.
Making Dream's skills actually work under `codex` (they assume Claude's Agent
tool for subagents) is a separate ticket — out of scope here.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: default-agent-key

## Implementation plan (implement step, 2026-10-14)

- Evaluator must-resolve 1 (init writer): `_write_default_agent` returns False
  for a name not among the parsed `[agents.*]`. An existing top-level
  `default_agent` with the same value succeeds without writing; a different
  value is replaced in place. Otherwise it uncomments the template example, or
  inserts before the first table. A tomllib guard requires
  after == before | {default_agent: name}.
- Evaluator must-resolve 2: every `default_agent` ConfigError (non-string,
  blank, unknown) names the source file and lists the known types.

## Design notes (design step, 2026-10-14)

- The spec lives under `## Description`: acceptance criteria, proposed shape,
  and out of scope.
- Spelling: top-level `default_agent`, readable from both files with local
  winning, and validated at load against the merged `[agents]`. Rejected
  alternatives: `[agents] default` (puts a scalar among the type-name tables;
  `_parse_agents` currently skips scalars silently) and a new `[defaults]`
  table.
- Init: it writes the key instead of reordering tables, and the
  `_make_default_agent` reorder machinery goes.
- Gap found: packaged `bootstrap/ticket` and `bootstrap/orient` pin
  `agent: claude`. That pin outranks `default_agent()` in authoring
  precedence, so the key does **not** move the `coga ticket` or `coga chat`
  interviewer. It does still move Dream, activation, retire, and autofix.
- The existing test `test_bare_recurring_passes_agent_override_to_agent_tasks`
  already asserts `seen == ["codex"]`, so no new `--agent` test is needed.

## Open Questions

1. **A shared value naming a local-only type.** Recommendation: validate
   against the merged table and fail loud, naming `coga.toml`. This is the same
   rule as `[autofix] agent`. A clone without that type breaks on every command
   until fixed. That is visible immediately, which is better than silently
   ignoring a committed setting. Alternative: validate a shared value against
   shared tables only. That is stricter, and catches the problem on the
   committer's machine. Which one?
2. **Bootstrap `agent: claude` pins.** Should `default_agent = "codex"` also
   move `coga ticket` and `coga chat`? Doing so means dropping the pins from
   the packaged `bootstrap/ticket` and `bootstrap/orient` (and maybe
   `coga-build`), which changes install-level authoring behaviour. Currently
   out of scope. Is a follow-up ticket wanted?
3. **Init on a clone.** Should init write `default_agent` into
   `coga.local.toml` when the operator has only `codex` installed? Currently
   out of scope.
4. **Template default.** Should the template ship `default_agent = "claude"`
   uncommented, to make the default explicit in new repos? The spec keeps it
   commented, so unset repos stay byte-for-byte identical and init has one
   line to uncomment.

## Evaluator review

Cold review completed 2026-10-14. The central design is sound and fits one
coherent PR, but resolve the two specification inconsistencies below before
implementation. This is evidence for owner review, not design approval.

### Must resolve before implementation

1. **Make the init writer's algorithm satisfy its stated tests.** Proposed
   shape specifies replacing a commented example or inserting a new key before
   the first table. After one successful call the comment is gone, so a second
   call inserts a duplicate `default_agent`, fails `tomllib` parsing, and
   returns False. That contradicts the required idempotency and the existing
   success-on-repeat contract in
   `tests/test_init.py::test_make_default_agent_reorders_the_packaged_coga_toml`.
   The proposed before/after dictionary guard also does not reject an unknown
   agent name, although the replacement test requires that rejection. Specify
   an existing-key branch (same value succeeds without writing; define whether
   a different value is replaced or refused) and validate membership in the
   parsed agent tables before writing. Evidence: `commands/init.py`
   `_make_default_agent` currently checks membership and returns True when the
   requested agent is already first; `_do_init` uses the boolean to decide
   whether to stamp delivered tickets and report success. Test both repeat
   calls and an existing explicit key, preserving unrelated TOML and order.
2. **Align the error-message requirement with the proposed parser.** Acceptance
   criteria require every non-string, blank, or unknown-value error to name
   the source file and list known agent types. The proposed non-string/blank
   `ConfigError` does not list known types. Either include them in that branch
   and assert them for both files, or narrow the acceptance criterion to
   unknown names. Evidence: `config.py::_parse_autofix`, the stated model,
   likewise lists known types only in its unknown-name branch. Copying its
   messages as proposed cannot meet the current criterion.

### Optional recommendations and owner decisions

- Treat the final grep as a review of current default-agent claims, not a
  requirement that every match describe the fallback. `service_order.py`
  discusses reordering task queues, `coga/skills/clarity/SKILL.md` discusses
  reordering prose, and `docs/archive/` and ticket blackboards contain dated
  history. Those are legitimate matches and should not be rewritten for this
  feature. Also update `_do_init`'s success text, which currently says
  "declared first under [agents]" and is missed by the specified patterns.
- Consider the existing `tomlkit` dependency and
  `commands/init.py::_write_local_user` as an alternative to new line-editing
  logic. It already edits a top-level scalar while retaining comments and
  nested tables. Either implementation is compatible with the required
  semantic guard; no new dependency is needed.
- The body already selects merged-table validation, unchanged bootstrap pins,
  no clone-path write, and a commented template example. The four Open
  Questions should receive owner dispositions consistent with those choices
  before handoff; they do not require expanding this PR's scope.

### Verified evidence

- All spec subsections are under `## Description`; `## Context` supplies the
  implementation references. The frozen workflow matches the packaged
  `code/design-then-implement` workflow and correctly hands this review to an
  owner gate. The attached `dev/code` context and explicit topic read/update
  list fit the work. Shared config resolution is established core
  infrastructure; no new command or parallel resolver is needed.
- `Config.default_agent` currently returns the first merged agent;
  `_parse_agents` preserves shared order and appends local-only types. The
  named mark/create/retire/autofix/authoring consumers and
  `bump.resolve_main_agent` use this resolver. `resolve_other_agent` delegates
  to it; an absent agent requires `allow_prospective_default=True` there too.
  Existing direct peer tests are in `tests/test_commands.py`.
- `recurring.py` creates active period tickets with the template's optional
  agent; Dream's template has no agent pin. `recurring_runner.py`
  `_prepare_forced_launch` reactivates existing tickets via `mark_active`, and
  `mark._select_main_agent` retains an existing valid agent. The proposed
  new-period and forced-rerun tests exercise distinct, real paths.
- The existing override test asserts `seen == ["codex"]`, as claimed. The
  packaged template and `tests/test_packaging.py`
  `INTENTIONALLY_DIVERGENT_TWINS` match the proposed template-only edit.
- Verification: `.venv/bin/python -m pytest -q
  tests/test_recurring.py::test_bare_recurring_passes_agent_override_to_agent_tasks
  tests/test_init.py::test_make_default_agent_reorders_the_packaged_coga_toml
  tests/test_init.py::test_init_writes_the_chosen_default_agent` — **3 passed**.
  The same invocation with ambient `python` failed collection because that
  environment lacks `tomlkit`; the project virtualenv works. No implementation
  changes were made, and the full suite was not run for this design review.

## Implement handoff (2026-10-14)

Branch `default-agent-key` is pushed. It has one commit, `b6db4b68e`, rebased
onto `origin/main` `05dca2a74`.

- **Config.** `config._parse_default_agent` reads top-level `default_agent`
  from both files, local first. It validates each present value against the
  merged `[agents]`, so a broken shared value fails even when local wins.
  Every error names its file and lists the known types (evaluator item 2).
  The result is stored on `Config.default_agent_name`. `Config.default_agent()`
  returns that type when it is set, and otherwise runs the first-entry code
  unchanged. The key is in both allowlists. No consumer changed.
- **Init.** `_make_default_agent` and `_TABLE_HEADER` are replaced by
  `commands/init._write_default_agent`, which resolves evaluator item 1:
  - an unknown name, or a file that will not parse, returns False and the
    file is untouched;
  - the same value already set returns True without a write;
  - an existing key is replaced in place;
  - otherwise it uncomments the template's `# default_agent = "claude"`, or
    inserts the key above the comment block that introduces the first table;
  - a tomllib guard requires the result to equal the original plus that one
    key.

  `_template_default_agent` mirrors `Config.default_agent`. The success and
  warning texts no longer mention reordering.
- **Template.** The commented `default_agent` block follows `default_status`
  in the packaged `coga.toml`.
- **Docs.** `coga/agents` gains a `## The default agent` section covering
  precedence, why the key is local-capable, validation, the freeze rule, the
  peer and read-only surfaces, the other knobs, and the bootstrap
  `agent: claude` pins that outrank it. The `configuration`, `tickets`,
  `recurring/autofix`, and `init` topics are updated too. Twins were copied
  byte-identical. The final grep left only correct fallback statements and
  unrelated "reorder" prose.
- **Tests.** In `test_config` there are 10 tests: shared, local override,
  unset fallback, a local-only type, bad values × file, and a broken shared
  value under a local win. Each consumer has one test:
  - `test_mark`, parametrized over both files;
  - `test_create`, a live create;
  - `test_retire`;
  - `test_recurring_autofix`;
  - `test_ticket`, the authoring term-6 fallback with no bootstrap pin;
  - `test_commands`, `resolve_main_agent` plus the peer flip.

  `test_recurring` has the two Dream tests: a new period gets codex, and a
  forced rerun keeps the frozen claude. The three init writer tests replace
  the reorder test, and the interactive init test now asserts the table order
  is unchanged. The existing `--agent codex` sweep test is unchanged.
- **Owner dispositions.** The Open Questions were applied as the body chose:
  merged-table validation, unchanged bootstrap pins, no clone-path write, and
  a commented template example. No human objected in this session.
- **Adjacent bugs.** None found.
- **Local quirk.** `coga validate` in `example/coga` fails if the shell
  exports a bare `SLACK_WEBHOOK_URL`, which this machine does. That is the
  intended migration error, not a regression; I ran it with the variable
  unset.

## PR

```yaml
title: Add a top-level default_agent config key
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5); coga-launch 20aee5c8-666e-4f25-b949-ae43885d19e2.
head: b6db4b68ec3ff6e98b416b56a99ac089ad396f4b
base: 05dca2a74d53326e8ba946043188d700ca0f3c52
depth: deep
rationale: >-
  Changes config parsing, which every command runs, and the default agent
  that activation, retire, autofix, authoring, and recurring resolve. It also
  replaces init's coga.toml rewrite. No code review has run yet.
implementation: >-
  New top-level default_agent, local over shared, validated at load against
  the merged [agents] table. Config.default_agent() honours it before the
  first-declared fallback, so every consumer follows with no per-consumer
  change. Interactive init writes the key instead of reordering [agents.*]
  tables. Docs and twins are updated.
deviations: >-
  Two choices resolve the evaluator's open points. All three default_agent
  error kinds list the known types. The init writer replaces an existing
  key and returns True without writing when the value already matches.
limitations: >-
  The packaged bootstrap/ticket, bootstrap/orient, and onboarding tickets
  still pin agent: claude, so coga ticket and coga chat do not follow the
  key; this is documented in coga/agents and was out of scope. Already
  activated tickets keep their frozen agent. Dream's skills under codex are
  a separate ticket.
files:
  docs/contexts/coga/agents/SKILL.md: Own the default_agent key, its precedence, local override, validation, freeze rule, and its relation to the other agent knobs.
  docs/contexts/coga/configuration/SKILL.md: List default_agent in both top-level allowlists.
  docs/contexts/coga/init/SKILL.md: Init writes default_agent instead of reordering tables.
  docs/contexts/coga/recurring/autofix/SKILL.md: The analyst fallback is default_agent() with the key, not only first-declared.
  docs/contexts/coga/tickets/SKILL.md: The activation default and authoring term 6 now name the key.
  src/coga/authoring.py: Docstring for term 6.
  src/coga/commands/init.py: Replace the table-reorder writer with _write_default_agent; _template_default_agent mirrors Config; new messages.
  src/coga/config.py: Parse, validate, and store default_agent; allowlists; default_agent() precedence.
  src/coga/create.py: Docstring for the live-create default.
  src/coga/mark.py: Docstring on the activation freeze.
  src/coga/recurring_autofix.py: Docstring for the analyst fallback.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/agents/SKILL.md: Byte-identical packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/configuration/SKILL.md: Byte-identical packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/init/SKILL.md: Byte-identical packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/autofix/SKILL.md: Byte-identical packaged twin.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/tickets/SKILL.md: Byte-identical packaged twin.
  src/coga/resources/templates/coga/coga.toml: Commented default_agent example after default_status.
  tests/test_commands.py: The prospective default and the other-agent peer follow the key.
  tests/test_config.py: Parsing, precedence, and the error matrix for both files.
  tests/test_create.py: A live create stamps the key's agent.
  tests/test_init.py: _write_default_agent behaviour; init names the agent without reordering.
  tests/test_mark.py: Activation stamps the key's agent from either file.
  tests/test_recurring.py: Dream new-period ticket gets codex; a forced rerun keeps the frozen agent.
  tests/test_recurring_autofix.py: The analyst falls back to the key.
  tests/test_retire.py: Retire defaults to the key's agent.
  tests/test_ticket.py: The authoring term-6 fallback follows the key.
review:
  reviewer: none
  kind: none
  status: not-run
  detail: No code review yet; design approval is not code review. The workflow's next step is open-pr.
checks:
  - command: .venv/bin/python -m pytest -q
    status: passed
    head: b6db4b68ec3ff6e98b416b56a99ac089ad396f4b
    base: 05dca2a74d53326e8ba946043188d700ca0f3c52
    detail: 3618 passed, on the clean committed tree after the rebase.
  - command: cd example/coga && env -u SLACK_WEBHOOK_URL ../../.venv/bin/coga validate --json
    status: passed
    head: b6db4b68ec3ff6e98b416b56a99ac089ad396f4b
    base: 05dca2a74d53326e8ba946043188d700ca0f3c52
    detail: ok_count 4, 0 issues.
  - command: .venv/bin/coga validate --json
    status: passed
    head: b6db4b68ec3ff6e98b416b56a99ac089ad396f4b
    base: 05dca2a74d53326e8ba946043188d700ca0f3c52
    detail: 0 errors; the 40 warnings are pre-existing ticket-state warnings (idle and unfrozen tickets) that this change did not cause.
```
