Item 7bc153, label Y (pair script-handoff r1)

# script-handoff, repetition 1

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

- launcher result: `{'exit_code': 0, 'termination_kind': 'done', 'termination_reason': 'sentinel-file (COGA_DONE_SENTINEL touched)', 'done_signalled': True}`; wall 41.0 s
- delivered prompt equals frozen (modulo marker): True
- live repo changed: False; effective writable roots: [[['/tmp/coga-prompt-trial-667707cc/.git', '/tmp']]]
- branch pre → post: main → main; worktree status post: `''`
- commits on HEAD since pre:

```
c98e8974aebf96f856a76ff1175001fa421368e6 Log: script-handoff
3dd5c7e516c514cdeccbc5d20b2558ae8be9d3da Ticket: script-handoff — step 2 (judge)
8717feaa8aaf1224df47b3c8673bb35041da8063 Log: script-handoff

```
- local origin main log (newest first):

```
c98e8974aebf96f856a76ff1175001fa421368e6 Log: script-handoff
3dd5c7e516c514cdeccbc5d20b2558ae8be9d3da Ticket: script-handoff — step 2 (judge)
8717feaa8aaf1224df47b3c8673bb35041da8063 Log: script-handoff
f4f773269f58a40e83d03a42161e1f8971bd45cc Log: script-handoff
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
index 0ec73c6..f595b08 100644
--- a/coga/log.md
+++ b/coga/log.md
@@ -1,2 +1,6 @@
 # Trial lifecycle log
 2026-11-13 12:47 v1 [script-handoff] [system] launched as a script (ticket.py)
+2026-11-13 12:47 v1 [script-handoff] [system] script exited with code 0
+2026-11-13 12:47 v1 [script-handoff] [human:trial-owner] trial adapter launch (script-handoff)
+2026-11-13 12:48 v1 [script-handoff] [agent:codex] advanced to step 2 (judge) → trial-owner
+2026-11-13 12:48 v1 [script-handoff] [system] {"agent":"codex","agent_turns":2,"cache_creation_input_tokens":null,"cache_read_input_tokens":143872,"cli":"codex","content_status":"ok","elapsed_seconds":40.809241,"ended_at":"2026-11-13T20:48:35.081821Z","exit_code":0,"exit_kind":"done","human_turns":0,"input_tokens":34102,"model":"gpt-6.1-sol","outcome":"The pending edits are the script’s handoff: `prepared.txt` contains `prepared`, and the blackboard records that the script succeeded. Local `main` matches `origin/main`; the ticket is still on `write` and has no branch or PR record. I’ll preserve that handoff, apply `trial/report` to record the result, and finish this routine task-state step on `main`.","outcome_status":"completed","output_tokens":1032,"provider":"openai","request":null,"schema":2,"session_id":"01a1d6aa-b999-7e02-a7b7-2222a226ac3f","slug":"script-handoff","started_at":"2026-11-13T20:47:54.272580Z","step":"write","title":"script-handoff","ts":"2026-11-13T20:48:35.081821Z","usage_reason":null,"usage_status":"ok"}
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
index 2b1329e..a07ab7b 100644
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
@@ -29,4 +29,12 @@ Use only the isolated trial repository.
 
 ## Notes
 
-No work performed yet.
+Script phase succeeded once; prepared.txt contains prepared. Agent work remains in this step.
+
+## Write step evidence
+
+Read `prepared.txt`: `prepared` followed by one newline. Read the script success note; did not rerun `ticket.py`.
+
+Wrote `coga/tasks/script-handoff/result.txt` and read it back: exactly `ready` followed by one newline (6 bytes).
+
+Checkout: `main`, no task branch or PR recorded. Existing script-produced ticket note and prepared file were preserved as the explicitly requested handoff. Fetched local origin before editing; main matched origin/main. Only routine task state changed. Write step complete; owner judge remains.

```

## (none: no controller input; analysis/probe run or lifecycle run without replies)