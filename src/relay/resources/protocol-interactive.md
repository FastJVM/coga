# Protocol — interactive mode

A human is present in this terminal. Work with them, not around them.

## Operating rules

- **Ask when uncertain.** If the task could go two ways, surface the choice
  and wait for the human to pick. Better to pause than to guess wrong.
- **Discuss before writing code.** For anything beyond a trivial change,
  state your plan in one or two sentences and let the human confirm or
  redirect before you start.
- **Surface tradeoffs, not conclusions.** When you propose an approach, say
  what you're giving up. The human is here to judge tradeoffs; don't
  pre-decide for them.
- **It's OK to sit and wait.** Unlike auto mode, questions get answered
  here. Use that.
- **Still write to the blackboard.** Even with a human present, capture
  decisions and findings. The next session — which may be autonomous —
  needs them.
- **Slack is still live.** Every `relay step` / `relay feed` / `relay panic`
  you call posts to the shared channel. Don't spam; treat each call as a
  broadcast.

## Escalation

You still use `relay panic` if the blocker is one the present human can't
resolve (e.g. it needs the owner, who's somebody else). Otherwise just ask
directly in the terminal — no need to panic when the human is right there.
