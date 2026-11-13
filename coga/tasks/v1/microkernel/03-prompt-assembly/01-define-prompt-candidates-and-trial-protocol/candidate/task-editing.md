A task is a `.md` file or a directory with `ticket.md` and optional attachments.
The exact `<!-- coga:blackboard -->` fence separates durable intent above from
working memory below. Read the blackboard first and maintain a concise handoff;
superseded designs stay on disk per `coga/blackboard`, with a composed pointer.
Do not edit the global audit `coga/log.md`; CLI commands own it.

You may edit `contexts` and body sections. Every other frontmatter field belongs
to CLI commands/humans unless the invoked authoring skill explicitly grants an
exception. This includes status, step, workflow, owner, agent, skills, secrets
and repo extensions. No assignment field exists: the current step's assignee
role determines who holds it. Preserve field order, formatting and existing
fields; invent none. Write lists one item per line, not flow-style arrays.
