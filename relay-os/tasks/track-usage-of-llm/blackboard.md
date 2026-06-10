The blackboard is a notepad to be written to often as the human and agent works through a task.

## Bootstrap decisions (2026-06-09, interactive with nick)

- **Scope:** ledger primitive only. Capture + store + `relay usage` read command.
  Budget caps / "remaining" / autorouting / free-token launcher / digest wiring
  are out of scope — separate consumer tickets (one exists:
  `autoroute-agent-based-on-remaining-usage`).
- **Capture mechanism:** parse agent transcripts after the session returns
  (launches inherit the terminal, so usage can't be streamed). Claude first,
  Codex stubbed behind a provider seam.
- **Budget cap:** deferred. This ticket records spend only; "remaining" is a
  consumer's problem.
- **Workflow:** `code/design-then-implement`. Nick chose the design-gate
  variant over `code/with-review` because the ledger schema + `relay usage`
  signature are a contract the downstream tickets read — the design step
  pins them and the owner reviews the spec before any code is written.

## Evaluator review

I have enough grounding. Let me note the key mismatch I found between the ticket's claims and the actual launch.py code, then give the assessment.

Key verification finding: the ticket says capture hooks in "after the agent exits ... around line 418–435" via `run_with_done_marker` / `subprocess.run`. But that block is **inside a `while True:` per-step chaining loop** (lines 334–467). A single `relay launch` invocation can spawn **multiple** agent sessions (implement → peer-review → open-pr, rotating claude↔codex) within one process. This materially affects the design and the ticket understates it.

Assessment below.

---

1. Clarity for a cold-start agent — mostly yes, with gaps

- The three-part Capture/Store/Read structure is clear and the intent ("foundational primitive, consumers are separate tickets") is well-stated. An agent could begin.
- Concrete grounding is good: exact transcript path, the `usage` field names, the "put logic in `src/relay/usage.py`, keep `launch.py` thin" steer (correctly matches `relay/codebase`).
- Gap: the `relay usage` command surface is underspecified. "totals... overall, by task, by model, by window" — but "window" is undefined (time window? session? what granularity?), and there's no example output, no flag shape, no machine vs human output contract. The accessor is explicitly the contract for 3 downstream tickets, yet its interface is the least specified part.
- Gap: "derived cost" leans on "a small price table (Claude pricing)" with no source-of-truth named and no statement of what happens when a model id isn't in the table (silent zero? unknown? same as the transcript-missing path?).

2. Workflow fit — code/with-review is reasonable, but a design gate is warranted

- The work is genuinely a code change with testable parser/rollup logic, so code/with-review (implement → peer-review → open-pr → human review) fits the *mechanics*.
- However, the ticket itself flags three things that become contracts for other tickets: the ledger record schema, the file path/format, and the `relay usage` accessor signature. It defers all of them to "confirm during implement." With this workflow the first time a human sees those decisions is the final PR review — after the peer agent has already built on them. For a primitive whose whole justification is "3 consumers read this," an explicit design/spec checkpoint before implementation would de-risk it. There is no design-review gate in code/with-review (peer-review is a code diff review, not a schema sign-off). This is the most defensible criticism: the format-as-contract nature argues for a lighter-weight schema agreement up front, or splitting a "design the ledger record + usage interface" step out.

3. Contexts — relay/codebase is correct but insufficient; relay/architecture is needed

- relay/codebase is the right attach (it's the "editing relay's own code" context and gives source layout + test/validate commands). Good.
- relay/architecture is missing and the ticket arguably **needs** it: the Context section makes architectural claims ("no database, no daemon," "plain committed files, not hidden state," append-only ledger under `relay-os/`) and attributes them to `relay/architecture` — but that context isn't attached, so the agent picking this up won't actually have read the primitive model it's being told to respect. Either attach `relay/architecture` or drop the parenthetical that implies it was consulted.
- relay/principles would also help (the "legible, no hidden state" non-negotiable is a principle), though architecture is the higher-value add.

4. Scope — borderline; defensible as one ticket but on the heavy side

- The ticket explicitly fences out budgets/remaining/autoroute/free-token-launcher/digest-wiring, which is good discipline and keeps it as a primitive.
- What remains is still three non-trivial pieces: (a) a transcript parser with a provider seam (Claude now, Codex stubbed), (b) the launch.py capture hook with robustness/no-double-count logic, and (c) a new `relay usage` read command with multiple aggregation axes. (a)+(b) are the real primitive; (c) is a separate command surface that could be its own ticket. It doesn't bundle a *consumer's* worth of work, but it's two deliverables (write-path + read-path) wearing one ticket. Acceptable, but if velocity matters, splitting capture/store from the `usage` command would each be cleaner and independently reviewable.

5. Assumptions to question before launch

- **Multi-session per launch (most important).** The ticket says write "one record per session" after the agent exits "around line 418–435," implying one capture per launch. In reality that block sits inside a `while True:` chaining loop (launch.py 334–467): a single launch can run implement, then rotate to the peer agent for peer-review, then back for open-pr — multiple sessions, multiple transcripts, possibly two different models/CLIs, in one process. Capture must run **once per loop iteration (per session)**, not once per launch, and must handle the claude↔codex rotation. The ticket's "stub Codex" plan collides with this: a single supervised run can legitimately produce a Codex session that the Claude-only parser can't read. This needs to be called out before launch.
- **Session-id / transcript matching.** "Identify transcript(s) by the session window (launch start → exit) for the launch cwd" is fragile. launch.py does not currently capture or surface the agent's session id; matching purely by mtime-window + cwd-hash will mis-attribute when (a) the user has another Claude session open in the same cwd, or (b) the agent resumes/continues an existing session file (the JSONL appends rather than creating a new file). The robust signal is the `sessionId` in the JSONL, but relay would need to *know* which session id the spawned CLI used — it currently doesn't. Worth verifying whether claude/codex expose the session id to the parent (env, stdout, or a known path) before committing to window-matching.
- **Double-counting on resume.** Directly related: because transcripts are append-only per session file, a resumed session's JSONL contains prior turns' `usage` lines. Window-filtering by line timestamp (not file mtime) is required, and the ticket waves at this ("be careful not to double-count") without prescribing the mechanism. This is the single most likely correctness bug and deserves a concrete strategy in the ticket.
- **Cache-token cost semantics.** The transcript splits `cache_creation_input_tokens` and `cache_read_input_tokens`, which are priced differently from base input tokens. "derive cost from model + a small price table" understates this — the price table needs per-category rates, not one input price, or the cost column will be materially wrong for cache-heavy Relay prompts (which compose large context layers, so cache usage will be high).
- **Robustness path interaction with the freshness check / exit codes.** launch.py `sys.exit(exit_code)` on non-zero agent exit (line 442–448) returns before the loop re-reads state. Where capture sits relative to that early exit matters: a crashed/non-zero session would be skipped entirely unless capture runs in the `finally` around the subprocess call. The ticket says "must never break a launch" but doesn't address the non-zero-exit early-return, where a session that burned tokens then errored would silently produce no record.

Relevant files: ticket at `/home/n/Code/relay/relay-os/tasks/track-usage-of-llm/ticket.md`; capture hook reality at `/home/n/Code/relay/src/relay/commands/launch.py` (the `while True:` loop, lines 334–467, and the non-zero-exit early return at 442–448); workflow at `/home/n/Code/relay/relay-os/workflows/code/with-review.md` (no design gate; peer-review is a diff review).

## Design step (2026-06-09, claude)

Spec written into ticket.md: Acceptance Criteria, Proposed Shape, Out of Scope.
The evaluator's five risks are now all addressed in the spec:

1. **Multi-session per launch** — spec mandates one record per `while True:`
   loop iteration, each carrying its own slug/step/agent/cli/model; covers
   the claude↔codex rotation explicitly.
2. **Transcript matching** — *resolved by a new finding*: `claude` accepts
   `--session-id <uuid>`. launch.py mints a uuid4 per claude session, passes
   it, and reads exactly `~/.claude/projects/<cwd-hash>/<uuid>.jsonl`.
   Deterministic lookup, no mtime/window heuristic. Verified the path layout
   against the live `~/.claude/projects/-home-n-Code-relay/` dir and confirmed
   assistant lines carry `timestamp`, `sessionId`, `message.model`,
   `message.usage.{input,cache_creation_input,cache_read_input,output}_tokens`.
3. **Double-counting** — minted-session file is session-scoped, so summing it
   is safe; per-line `timestamp` window filter kept as a defensive guard and as
   the fallback when session-id is unknown (codex / older claude).
4. **Cache-token cost** — spec requires a per-category price table (4 rates),
   not a single input rate.
5. **Non-zero-exit early return** — capture runs in the `finally` around the
   subprocess call, before launch.py's `sys.exit(exit_code)`.

## Open Questions (for review-design)

1. **Price table source of truth.** Recommend a hardcoded `PRICES` dict in
   `usage.py` with an "as of <date>" comment + unknown-model → `cost_usd: null`.
   Alternative: put rates in `relay.toml` so they're editable without a code
   change. Hardcoded is simpler and keeps the contract in one place; config-
   driven survives price changes without a PR. Which do you want? (Default:
   hardcoded.)

2. **summary.md regeneration cadence.** Recommend regenerating on every capture
   so the committed file is always current. Tradeoff: noisier git diffs (a line
   changes on every launch). Alternative: only regenerate on
   `relay usage --write-summary`. (Default: on every capture.)

3. **Does capture auto-commit the ledger?** Currently launch.py commits nothing;
   the ledger write would sit in the working tree for the next commit to pick
   up. Auto-committing per session is possible but adds git side effects to
   `relay launch`. (Default: no auto-commit — leave it to normal flow. Listed in
   Out of Scope.)

4. **Minting `claude --session-id`.** This changes the spawned command (relay
   dictates the session id instead of letting claude generate one). Low risk and
   it's the cleanest matching strategy, but confirm you're OK with relay owning
   the session id. (Default: yes, mint it.)

5. **Codex stub acceptability.** A supervised run that rotates to codex will
   produce a `usage_status: "unknown"` record this ticket. Confirm that's an
   acceptable interim state vs. blocking on a real codex parser. (Default: stub
   is fine — full codex parser is a follow-up.)

6. **Contexts.** Evaluator suggested attaching `relay/architecture` (and maybe
   `relay/principles`) since the spec leans on the "no hidden state, plain
   committed files" model. Want me to add `relay/architecture` to `contexts:`
   before implement? (Default: add it — the implementer should read the
   primitive model it's told to respect.)

