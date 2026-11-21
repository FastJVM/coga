# Ticket loop

This layer composes only for a task ticket. A stateless `bootstrap/<name>`
target has no blackboard, workflow, or lifecycle; its own ticket says how it
finishes.

## The loop

1. **Start from the blackboard.** It is composed into this prompt below. It is the working memory carried across stateless sessions,
   holding prior plans, findings, decisions, and open blockers. Read it as
   current state before planning anything.
   While reading it, whether the ticket is new to you or resumed, delete notes
   that clearly no longer help the work: finished scratch, stale status,
   superseded plans with no live rationale, dead ends already ruled out.
   Age only prompts the check. Keep current decisions and their reasons, open
   blockers, the worklist, and verification evidence the handoff still needs.
   Never delete a section a Coga command or runner wrote (`## Dev`,
   `## Blockers`, `## Blocker reminders`, `## Recipe Failure`), `## PR`,
   `## Superseded designs`, an `## Evaluator review` or `## Production notes`
   a gate still reads, or recurring cross-run state. This light pass needs no
   separate review; if unsure, keep the note. `coga/blackboard` ("Stale-note
   cleanup") owns this policy.
2. **Do the current step.** Follow the ticket, contexts, and step skill. Record
   useful findings and decisions, with reasons, on the blackboard as you go.
   Keep it concise enough to compose into the next launch.
3. **Reconcile before handing off branch work** as described in `coga/git`.
4. **Run `bump` as the *last* thing in the current step, then stop.**
   `coga bump <id>` is the only command that advances a workflow. Run it after
   the work is complete and the blackboard is current.
   On the final step, `coga bump` marks the task `done`. At an owner-controlled
   gate, bump only when the human explicitly asks you to advance or close it.
5. **Never stop silently.** If you cannot reach the transition, escalate the
   way the `Session conduct` layer in this prompt directs. Do not leave
   completed or blocked work invisible.

## Finishing the step

- **One transition, one step.** `coga bump <id>` reads the current step and
  advances exactly once. Run it with no step selector: `--to` and `--backward`
  are human-only. After bumping, exit cleanly. One step, one session: do not
  read or work the newly selected step in this process. Under a `coga launch`
  supervisor, `coga bump`, `coga mark done`, `coga mark canceled`, and
  `coga block` each end your session and let the supervisor spawn what comes
  next. How the supervisor chains steps is in `coga/launch`; you do
  not drive it.
- **API/manual sessions don't chain.** After a bump outside `coga launch`, the
  human relaunches the next step. Do not call `coga launch` yourself.
- **Do not go backward.** Escalate incorrect earlier work instead of changing
  the frozen workflow or trying to rewind it yourself.
- **No workflow means no bump.** Finish a workflow-less ticket with
  `coga mark done <id>`. Never set `status: done` by hand.

## Blocking and FYIs

Use `coga block --task <id> --reason "<specific ask>"` only when a concrete
human answer or unavailable capability prevents progress. It records the ask,
sets `status: blocked`, notifies the owner, and ends a launched session. Stop
after blocking. The `Session conduct` layer in this prompt is what decides
whether input is available and how to escalate; read every other instruction
to block or to ask, workflow step skills included, through it.

Make the reason actionable. Prefer "Retry policy needs a maximum backoff for
429s" to "Unclear what to do."

State transitions notify on their own. Add a one-line FYI only when useful:

- `coga bump <id> --message "<FYI>"` attaches it to the step handoff.
- `coga slack --task <id> --message "<FYI>"` sends one without a transition.

Neither replaces `coga block`. Put longer detail on the blackboard.
