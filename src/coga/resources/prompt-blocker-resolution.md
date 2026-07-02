# Resolve the open blocker first

This ticket carries unresolved blocker asks and has been resumed so you can
work through them with the human in this session. **Your first job — before
the workflow step's real work — is to resolve or re-block, nothing else.**

Open asks, verbatim from the blackboard `## Blockers` section (stale or junk
asks included, so the human can clear them):

{blockers}

Operating order:

1. Discuss the open asks with the human and land on a resolution. Don't skip
   an ask because it looks stale — surface it and let the human clear it.
2. Record the resolution: run
   `coga unblock {slug} --answer "<synthesized resolution>"`. That marks every
   open ask resolved on the blackboard; the ticket stays on its current
   workflow step.
3. Only after the unblock has run, proceed to the current workflow step's
   real work below.
4. If the human decides an ask **cannot** be resolved, run
   `coga block --task {slug} --reason "<refined reason>"` instead of
   proceeding — never continue past an unresolved ask.
