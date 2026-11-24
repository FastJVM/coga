# Operate trim-log

Fresh workspaces select weekly audit maintenance. To adopt it in an existing
workspace, use the interpreter from
[coga/edge-code upgrades](../../bootstrap/contexts/coga/edge-code/edge-code-upgrades.md)
and run from that workspace:

```sh
"$COGA_PY" -m coga_edge.trim_log --install
```

The installer selects the packaged job in `recurring/jobs.toml`. Review
that change before sharing it. Preserve any local override and use the
[ticket](ticket.md) for the retention and preservation rules.

Trim-log operates on the local audit log. Set `[log].retention_days` to zero
to disable compaction. Audit history can exceed the window when in-use data,
recurring ledgers or unread phone-home movement need to be kept.

If maintenance reports an error, inspect the local ticket, log and cursor
before retrying. Resolve any ask in a blocked period through `coga unblock
recurring/trim-log --answer "..."`. See [coga/git](../../bootstrap/contexts/coga/git/SKILL.md)
for the log's merge and compaction behavior.
