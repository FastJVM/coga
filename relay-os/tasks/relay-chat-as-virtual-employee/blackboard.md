# Blackboard — relay-chat-as-virtual-employee

Two things for the future implementer:

1. `## Conversation digest` — short summary of how this ticket
   relates to the companion `virtual-employee` ticket (PR #208).
2. `## Evaluator review` — verbatim critique from a fresh-session
   reviewer; treat as input for the human (nick) to act on before
   activating.

---

## Conversation digest

This ticket is the **positive half** of a matched pair with the
`virtual-employee` ticket (PR #208).

- PR #208 rejects `virtual-employee` as a Relay *primitive* — no
  `[employees.*]` table, no memory-bearing role abstraction, no
  identity-bearing agent entry. It explicitly preserves the
  *metaphor* for UX positioning.
- This ticket is where that preservation cashes out: the `relay
  chat` alias (which composes the canonical relay contexts and the
  repo's contexts into a stateless session) genuinely behaves like
  talking to a teammate who's been onboarded into the company.
  "Your virtual employee for this repo" is an honest description
  of that UX.
- Scope is small on purpose — three files (the live bootstrap shim,
  its packaged copy, README's `relay chat` mention). No vision.md
  edits (PR #208 owns that surface for the rejection side).
- The `bootstrap/orient/ticket.md` shim has a footer warning "Don't
  edit this shim except to swap `assignee`" — that warning is aimed
  at *downstream* vendored copies. This PR is the *upstream* edit
  and is the right place for the framing change. CLAUDE.md's sync
  rule means the packaged copy
  (`src/relay/resources/templates/relay-os/bootstrap/orient/ticket.md`)
  must be updated in the same PR.
- Tone discipline: lead with the metaphor, then ground it in the
  substrate (composed prompt, stateless session, no persistent
  identity/memory/tenure) so a reader doesn't feel oversold.

---

## Evaluator review

**1. Description clarity for a cold-start agent.** Strong. Lines
33-48 land the thesis in one paragraph and make the "positive half
of a matched pair" framing explicit. The PR #208 reference would
carry more weight with one extra clause naming the artifact PR #208
changed (it just says "rejects 'virtual employee' as a Relay
*primitive*" — fine, but a cold reader doesn't know whether that
means vision.md, a context, or config) — line 62 in the Context
section partially fixes this. Net: an agent picking this up cold
can act without re-deriving the conversation.

**2. Scope.** Right-sized. Three files is the minimum honest scope
given the `CLAUDE.md` sync rule. One thing missing: `src/relay/
resources/templates/CLAUDE.md` (the packaged downstream agent
guide) has a "Start here" section that says
`relay launch bootstrap/orient` drops you into a "relay-aware
session" — if the framing changes upstream, a one-line nudge here
would keep messaging coherent. Defensible to exclude, but worth at
least an out-of-scope note.

**3. Tone guidance.** The example block (lines 82-87) is the
strongest part of the ticket. It leads with the metaphor, then
names the substrate ("composed prompt over a stateless session;
there's no persistent identity, memory, or tenure") — which is
exactly the line PR #208 draws. It does not conflict with the
rejection: the rejection bans the *primitive*, the example only
claims UX shape. The "For ticket-bound work, exit and `relay launch
<slug>`" sentence is already in the live shim (lines 21-23), so the
example honestly preserves existing guardrails rather than
rewriting them.

**4. Sync handling.** Flagged clearly (lines 69-77). The "Don't
edit this shim except to swap `assignee`" disambiguation (line
74-77: "aimed at *downstream* repos that vendored the shim; this PR
is the *upstream* edit") is exactly the right call-out — a cold
agent reading the shim's footer (line 39 of the live shim) would
otherwise hesitate.

**5. Out-of-scope clauses.** Mostly right. The `[employees.*]`/
`[personas.*]` fence (lines 100-103) and the "don't add VE language
to ticket-bound surfaces" fence (lines 104-108) are the
load-bearing ones. The vision.md exclusion (line 109-110) is
correct. Missing: an explicit fence around the `claude` / `codex`
per-agent alias comments (README line 582-584) — an implementer
could reasonably ask "should those get positioning lines too?" The
answer is presumably no (they're commented-out examples), but the
ticket doesn't say.

**6. PR shape and workflow fit.** `dev/with-self-review` is right.
Self-QA on prose wording (line 113-114) is the correct read, and
the "*not* a `/simplify` run on prose, which would mangle it"
caveat is a real save. A `docs/`-only workflow would be lighter but
doesn't exist; this is the right available fit.

**7. Anything missing.** Two snags: (a) line 92-95 says "around
line 580" — line numbers drift; safer to anchor on the section
heading `### Aliases`. (b) The ticket doesn't say whether the
README update should also touch the `relay chat --agent codex`
paragraph at lines 365-367 — it explicitly says it shouldn't (lines
96-98), but the rationale ("about agent overrides, not what chat
*is*") would be more convincing if it noted that paragraph already
exists in the launch section, not the Aliases section, so a single
positioning line in Aliases is sufficient.

**Verdict.** Ready to activate after a tiny polish pass (anchor
README references to headings, add a one-line `templates/CLAUDE.md`
out-of-scope note); the matched-pair framing and tone discipline
are already doing real work.
