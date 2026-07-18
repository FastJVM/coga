# Daily digest spool

Producer/consumer queue for `coga digest`. Producers append one JSONL record
at the **bottom** of `## Spool (pending)`; the single consumer (`coga digest`)
advances the `consumed_through:` watermark to the newest record and trims the
consumed prefix, always keeping the newest record in place as an *anchor*.

This file is marked `merge=union` (`.gitattributes`) so two clones appending
concurrently merge without conflict. Together with the top-trim/bottom-append
shape (deletes and appends sit in disjoint hunks separated by the anchor), that
makes the spool mergeable by construction with no lock — see the `coga/sync`
context. The git high-water mark lives separately in the digest ticket's
`### Digest State`, not here.

## Spool (pending)





consumed_through: 5395a45530c4
{"id":"5395a45530c4","ts":"2026-07-16T10:15","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"c74322881d74","ts":"2026-07-16T10:15","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"8f2a92e28596","ts":"2026-07-16T10:15","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"a24c6c948452","ts":"2026-07-16T10:30","project":"coga","kind":"done","detail":"claude finished: implement → done ✅","ticket":"install/retest-ssh-https-and-init-reclone-on-fresh-machine","owner":"nicktoper"}
consumed_through: 8e32b965dc04
{"id":"8e32b965dc04","ts":"2026-07-15T20:14","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"b99a93978ecd","ts":"2026-07-15T20:14","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"bef10e3dc37c","ts":"2026-07-15T20:15","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"803cb28175e9","ts":"2026-07-15T20:36","project":"coga","kind":"done","detail":"→ done (script)","ticket":"dream-validate-drift-w29","owner":"nicktoper"}
{"id":"88c1b04d9318","ts":"2026-07-15T21:19","project":"coga","kind":"done","detail":"→ done (script)","ticket":"dream-cleanup-orphan-markers-w29","owner":"nicktoper"}
{"id":"efdb0827ab26","ts":"2026-07-16T11:23","project":"coga","kind":"done","detail":"zach finished: review → done ✅","ticket":"coga-important/support-second-webhook","owner":"zach"}
{"id":"3aff9b674f90","ts":"2026-07-16T16:54","project":"coga","kind":"done","detail":"nicktoper finished: review → done ✅","ticket":"install/gh-auth-hint-on-managed-skill-rate-limit","owner":"nicktoper"}
{"id":"0d6df972bfa6","ts":"2026-07-16T20:41","project":"coga","kind":"done","detail":"nicktoper finished: review → done ✅","ticket":"log-md-coga-chat-too-so-we-have-a-full-view-of-the","owner":"nicktoper"}
{"id":"2060d9f1c033","ts":"2026-07-17T15:27","project":"coga","kind":"done","detail":"zach finished: review → done ✅","ticket":"coga-important/add-coga-slack-important","owner":"zach"}
{"id":"6c0d7036b976","ts":"2026-07-17T15:55","project":"coga","kind":"done","detail":"nicktoper finished: implement → done ✅","ticket":"handle-better-delete-branches-autcommit","owner":"nicktoper"}

consumed_through: a20bb1814a33
{"id":"a20bb1814a33","ts":"2026-07-17T14:40","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/autoclose-merged","owner":"nicktoper"}
{"id":"24d9cae304bb","ts":"2026-07-17T14:40","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/digest","owner":"nicktoper"}
{"id":"d325eedef508","ts":"2026-07-17T14:40","project":"coga","kind":"done","detail":"→ done (script)","ticket":"recurring/blocker-reminders","owner":"nicktoper"}
{"id":"e658619631d8","ts":"2026-07-17T16:32","project":"coga","kind":"done","detail":"claude finished: implement → done ✅","ticket":"recurring-bugs/coga-usage-cannot-locate-claude-transcript-or-sess","owner":"nicktoper"}
{"id":"892041cbd7a5","ts":"2026-07-17T18:14","project":"coga","kind":"done","detail":"claude finished: implement → done ✅","ticket":"recurring-bugs/recurring-scan-should-skip-and-report-an-unloadabl","owner":"nicktoper"}
{"id":"2d42d0c2de91","ts":"2026-07-17T17:00","project":"coga","kind":"done","detail":"claude finished: implement → done ✅","ticket":"move-open-pr-recipe-into-the-code-open-pr-skill-ke","owner":"nicktoper"}
