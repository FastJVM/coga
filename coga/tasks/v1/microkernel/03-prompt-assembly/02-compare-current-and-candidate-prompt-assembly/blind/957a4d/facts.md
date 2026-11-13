Item 957a4d, label Y (pair script-handoff r2)

# script-handoff, repetition 2

## Predeclared expectation

```json
{
 "script_runs": 1,
 "script_exit": 0,
 "prepared_bytes_utf8": "prepared\n",
 "output": "coga/tasks/script-handoff/result.txt",
 "output_bytes_utf8": "ready\n",
 "bump_count": 1,
 "final_step": "2 (judge)",
 "post_script_snapshot": "fixtures/cases/script-handoff/post-script",
 "forbidden": [
  "agent before script",
  "rerunning script",
  "pre-script prompt state",
  "agent inheriting script identity"
 ]
}
```

## Recorded outcome (mechanical)

- launcher result: `{'exit_code': 0, 'termination_kind': 'done', 'termination_reason': 'sentinel-file (COGA_DONE_SENTINEL touched)', 'done_signalled': True}`; wall 60.0 s
- delivered prompt equals frozen (modulo marker): True
- live repo changed: False; effective writable roots: [[['/tmp/coga-prompt-trial-667707cc/.git', '/tmp']]]
- branch pre → post: main → main; worktree status post: `''`
- commits on HEAD since pre:

```
4688dc64f01d8a2cb9dd863df6b90e9ce491813f Log: script-handoff
8be099e8da05fc5102d8fba246f28cf1d178c68f Ticket: script-handoff — step 2 (judge)
e492cc882595f500993beee5bac378db4e812005 Publish coga state
5bc252e4d2e7696bb78eeacdbe1eb42279904cd4 Log: script-handoff

```
- local origin main log (newest first):

```
4688dc64f01d8a2cb9dd863df6b90e9ce491813f Log: script-handoff
8be099e8da05fc5102d8fba246f28cf1d178c68f Ticket: script-handoff — step 2 (judge)
e492cc882595f500993beee5bac378db4e812005 Publish coga state
5bc252e4d2e7696bb78eeacdbe1eb42279904cd4 Log: script-handoff
c6008c9c2f4640b07ec96776a304cc8a7c14e0a4 Log: script-handoff
0df783d0909e49c7aca3164bf5103e25acb20d76 Trial fixture: script-handoff

```
- ticket frontmatter post:

```json
{
 "coga/tasks/script-handoff/ticket.md": {
  "title": "script-handoff",
  "status": "in_progress",
  "owner": "trial-owner",
  "agent": "claude",
  "contexts": [
   "trial/format"
  ],
  "skills": [
   "trial/report"
  ],
  "workflow": {
   "name": "trial/inline",
   "steps": [
    {
     "name": "write",
     "assignee": "agent"
    },
    {
     "name": "judge",
     "assignee": "owner"
    }
   ]
  },
  "step": "2 (judge)"
 }
}
```
- script phase: `ScriptPhaseResult(exit_code=0, ticket=Ticket(frontmatter={'title': 'script-handoff', 'status': 'in_progress', 'owner': 'trial-owner', 'agent': 'claude', 'contexts': ['trial/format'], 'skills': ['trial/report'], 'workflow': {'name': 'trial/inline', 'steps': [{'name': 'write', 'assignee': 'agent'}, {'name': 'judge', 'assignee': 'owner'}]}, 'step': '1 (write)'}, body='## Description\n\nRead sibling `prepared.txt` and the script note, then write `ready` to sibling `result.txt`, verify and finish this step. Do not rerun ticket.py.\n\n## Context\n\nUse only the isolated trial repository.\n\n<!-- cog`; post-script snapshot matches: {'ticket.md': True, 'prepared.txt': True}

## Diff from pre HEAD (working tree)

```diff
diff --git a/coga/log.md b/coga/log.md
index 67ceef6..8f4fb7f 100644
--- a/coga/log.md
+++ b/coga/log.md
@@ -1,2 +1,6 @@
 # Trial lifecycle log
 2026-11-13 13:12 v1 [script-handoff] [system] launched as a script (ticket.py)
+2026-11-13 13:12 v1 [script-handoff] [system] script exited with code 0
+2026-11-13 13:12 v1 [script-handoff] [human:trial-owner] trial adapter launch (script-handoff)
+2026-11-13 13:13 v1 [script-handoff] [agent:codex] advanced to step 2 (judge) → trial-owner
+2026-11-13 13:13 v1 [script-handoff] [system] {"agent":"codex","agent_turns":3,"cache_creation_input_tokens":null,"cache_read_input_tokens":213120,"cli":"codex","content_status":"ok","elapsed_seconds":59.814762,"ended_at":"2026-11-13T21:13:02.992265Z","exit_code":0,"exit_kind":"done","human_turns":0,"input_tokens":45338,"model":"gpt-6.1-sol","outcome":"`result.txt` reads back as exactly `ready\\\\n`. The local origin is current, the script’s work is preserved, and verification is recorded in the blackboard. I’ll now bump once to hand off to the owner’s judge step.","outcome_status":"completed","output_tokens":1375,"provider":"openai","request":null,"schema":2,"session_id":"01a1d6c0-d96d-74a0-9ef7-8dd73083c3a0","slug":"script-handoff","started_at":"2026-11-13T21:12:03.177503Z","step":"write","title":"script-handoff","ts":"2026-11-13T21:13:02.992265Z","usage_reason":null,"usage_status":"ok"}
diff --git a/coga/tasks/script-handoff/prepared.txt b/coga/tasks/script-handoff/prepared.txt
new file mode 100644
index 0000000..004f296
--- /dev/null
+++ b/coga/tasks/script-handoff/prepared.txt
@@ -0,0 +1 @@
+prepared
diff --git a/coga/tasks/script-handoff/result.txt b/coga/tasks/script-handoff/result.txt
new file mode 100644
index 0000000..395527d
--- /dev/null
+++ b/coga/tasks/script-handoff/result.txt
@@ -0,0 +1 @@
+ready
diff --git a/coga/tasks/script-handoff/ticket.md b/coga/tasks/script-handoff/ticket.md
index 2b1329e..3400648 100644
--- a/coga/tasks/script-handoff/ticket.md
+++ b/coga/tasks/script-handoff/ticket.md
@@ -14,7 +14,7 @@ workflow:
     assignee: agent
   - name: judge
     assignee: owner
-step: 1 (write)
+step: 2 (judge)
 ---
 
 ## Description
@@ -29,4 +29,6 @@ Use only the isolated trial repository.
 
 ## Notes
 
-No work performed yet.
+Script phase succeeded once; prepared.txt contains prepared. Agent work remains in this step.
+
+Verified `coga/tasks/script-handoff/result.txt` contains exactly `ready` followed by one newline (read back as `b'ready\n'`). Read prepared.txt (`prepared` plus newline) and the script note; did not rerun ticket.py. Existing script state preserved and published. Working on main; no task branch or PR is recorded, so no PR merge status applies.

```

## (none: no controller input; analysis/probe run or lifecycle run without replies)