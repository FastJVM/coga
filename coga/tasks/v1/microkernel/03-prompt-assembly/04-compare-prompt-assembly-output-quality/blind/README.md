# Blinded output pairs (ticket 04)

Eight pairs, two per case × repetition. Each pair folder holds two outputs of the
same task, `X/artifact.md` and `Y/artifact.md`, one from each prompt arm. Labels
are shuffled per pair. The key (`../blind-key.json`, sha256
`d5580c5fc6dacda1c74490b505f9cac939d34e8870cf711eff8112ba72d094ce`) and the
mechanical gate checks (`../gates.json`, arm-labeled) stay closed until
`verdicts.csv` is filled.

| Case | Task the agent was given | What `artifact.md` shows |
| --- | --- | --- |
| code | `fail-validation-when-local-user-is-required-for-ex`, `code/with-review` implement step | commit messages, diff (product files only), and the end-of-step blackboard handoff with PR receipts |
| design | `warn-when-coga-delete-or-coga-retire-leaves-a-live`, `code/design-then-implement` design step | the full ticket after the design step and its diff |
| docs | `document-untrusted-tool-output-verify-through-grou`, `docs/with-review` implement step | commits, diff, and handoff |
| author | `coga ticket "Flag stalled in-progress tickets in coga status"`, fixed brief and replies (`../dialogues.json`) | the full authored ticket |

For each pair, fill `verdicts.csv`:

- `better`: `X`, `Y` or `tie`;
- `reason`: one short sentence;
- `correction_X` / `correction_Y` (optional, secondary): how much correction
  the output would need before you would accept it. Use `none`, `minor` or
  `major`, or free text.

Notes for judging:

- **Both arms ran in an identical sandbox fixture.** This explains three things
  you will see:
  - mentions of a "trial", an absent Claude peer, or `/tmp` paths;
  - `trial-owner` as the owner;
  - an origin that is a local bare repo.
- **No gate violation was found in any of the 16 runs.** Every run kept prompt
  identity, made one transition (or none, for authoring), produced no merge
  commits, and left the live repo untouched. Nothing is disqualified, so judge
  on quality alone.
- **The authoring controller replies were fixed.** It answered every
  interview question "No preference; use your judgment and note the assumption
  in the ticket." and every request for approval "Looks good. Finalize it."
  Differences in the assumptions are therefore the agent's own choices.
