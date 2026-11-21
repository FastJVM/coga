---
name: coga/init
description: What `coga init` does for a fresh repo versus a clone of a repo that already uses Coga, what it writes and seeds, and how it records the operator's name.
---

# Initialize Coga

Run `coga init --user NAME` in the project directory. It creates the
`coga/` workspace, a local identity, and the agent discovery links. It
can initialize a directory with or without a Git repository. Review and
commit the shared files when ready if you use Git.

In an existing Coga workspace without a configured machine-local user,
the same invocation writes the local identity and repairs agent skill
links. It preserves the shared configuration. If the project directory
is empty, the scaffold supplies the first-run `coga build` ticket.
