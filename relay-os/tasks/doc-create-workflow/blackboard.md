The blackboard is a notepad to be written to often as the human and agent works through a task.

## Decision — workflow shape (2026-06-02)

Approach **A**: native structured relay workflow (frontmatter `steps:` + inline
bodies), not a prose guide. Lives at `workflows/docs/create-google-doc.md`,
name `docs/create-google-doc`.

The source description had a precondition + 9 numbered items including a
"repeat 5–7 until sign-off" loop. Relay's `bump` is forward-only and can't
express a backward loop, so the 9 items collapse into 4 session-boundary steps:

1. `preflight` (agent) — verify Google MCP + Drive HTML upload-and-convert;
   `relay panic` if down (enforces the precondition as a real fail-fast gate).
2. `draft` (agent) — gather → clarify → generate HTML → import → hand off first Doc.
3. `revise` (agent) — capture feedback → regen from (current Doc + changes) →
   re-import; **the review/revise loop lives inside this step** since the human
   is interactive. No fake backward bumps.
4. `sign-off` (owner) — human's explicit approval → `relay mark done`.

Inline step bodies (no separate skill files) — matches `_template.md` and
`code/with-review.md` convention.

Validated with `relay validate`: no parse / unknown-workflow errors for the file.

## Open question for the human

The CLAUDE.md sync rule covers *shipped framework templates* under
`src/relay/resources/templates/relay-os/`. This new workflow is a user
workflow in the live `relay-os/`, not a framework default — so I did **not**
copy it into the packaged templates. Flag if you actually want it shipped as a
default template too.
