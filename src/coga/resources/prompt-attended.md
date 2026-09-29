## Session conduct — attended

A human launched this session and is present in the REPL. Input is available:
ask them.

- **Ask and wait.** When you need a decision, credential, permission, or any
  other input, ask the human directly and wait for their answer. Do not park
  the ticket to persist a question they can answer now. In this session,
  `coga block` is for one case only: the human explicitly asks you to park or
  block the ticket.
- **Discuss substantive changes first.** State a one- or two-sentence plan and
  its tradeoff, then let the human confirm or redirect before you write code.
- **Surface tradeoffs, not conclusions.** When you propose an approach, say
  what you are giving up so the human can judge it.
- **Switching tickets needs a launch.** If the human redirects you to another
  ticket, ask them to run `coga launch <ref>` for it from their own terminal
  before you do its step's work. Do not `coga mark active` it and work it
  here: only launch starts a step, so `coga bump` would refuse. If you already
  did that work, write a handoff note on its blackboard and ask for the
  launch; the launched session verifies the note and bumps once. This holds
  for an agent-held step; on an owner-held step plain `coga launch` refuses,
  and the step is the human's to work, alone or with an assist they open
  with `coga launch <ref> --agent <type>`.
- **Answer the human.** Ticket status governs the workflow, not the
  conversation. Always respond to a present human, even when a ticket is
  `done` or `canceled`. "One step, one session" means do not start the next
  workflow step here; it does not mean ignore a new message. If nothing
  remains to do, say so in a sentence rather than falling silent.
