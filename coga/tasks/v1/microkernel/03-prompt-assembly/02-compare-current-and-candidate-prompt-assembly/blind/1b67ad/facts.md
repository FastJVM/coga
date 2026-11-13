Item 1b67ad, label X (pair script-handoff r2)

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

- launcher result: `{'exit_code': 0, 'termination_kind': 'done', 'termination_reason': 'sentinel-file (COGA_DONE_SENTINEL touched)', 'done_signalled': True}`; wall 54.6 s
- delivered prompt equals frozen (modulo marker): True
- live repo changed: False; effective writable roots: [[['/tmp/coga-prompt-trial-667707cc/.git', '/tmp']]]
- branch pre → post: main → main; worktree status post: `''`
- commits on HEAD since pre:

```
1700b63b0201c4b06f6b3fbf20ea67eb868b2e80 Log: script-handoff
1d847620ca069d228fc872d3a193ae978f9736f3 Ticket: script-handoff — step 2 (judge)
23c1049de71ca596121000ac4014f58a1f332800 Publish coga state
e67645db6862dac057b56f5278081232ff683067 Log: script-handoff

```
- local origin main log (newest first):

```
1700b63b0201c4b06f6b3fbf20ea67eb868b2e80 Log: script-handoff
1d847620ca069d228fc872d3a193ae978f9736f3 Ticket: script-handoff — step 2 (judge)
23c1049de71ca596121000ac4014f58a1f332800 Publish coga state
e67645db6862dac057b56f5278081232ff683067 Log: script-handoff
7071fccb3ce6a014df6c837c9890ced12e8d1845 Log: script-handoff
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
index b4d7888..440ae4d 100644
--- a/coga/log.md
+++ b/coga/log.md
@@ -1,2 +1,6 @@
 # Trial lifecycle log
 2026-11-13 13:13 v1 [script-handoff] [system] launched as a script (ticket.py)
+2026-11-13 13:13 v1 [script-handoff] [system] script exited with code 0
+2026-11-13 13:13 v1 [script-handoff] [human:trial-owner] trial adapter launch (script-handoff)
+2026-11-13 13:14 v1 [script-handoff] [agent:codex] advanced to step 2 (judge) → trial-owner
+2026-11-13 13:14 v1 [script-handoff] [system] {"agent":"codex","agent_turns":3,"cache_creation_input_tokens":null,"cache_read_input_tokens":203776,"cli":"codex","content_status":"ok","elapsed_seconds":54.407761,"ended_at":"2026-11-13T21:14:02.717516Z","exit_code":0,"exit_kind":"done","human_turns":0,"input_tokens":41620,"model":"gpt-6.1-sol","outcome":"`result.txt` contains exactly `ready` followed by one newline, verified by reading its bytes back. The blackboard now records the evidence, and local origin has no intervening changes. I’ll advance the write step to owner judgment.","outcome_status":"completed","output_tokens":1246,"provider":"openai","request":null,"schema":2,"session_id":"01a1d6c1-d3d0-7bd1-a600-1bc3222ac5ee","slug":"script-handoff","started_at":"2026-11-13T21:13:08.309755Z","step":"write","title":"script-handoff","ts":"2026-11-13T21:14:02.717516Z","usage_reason":null,"usage_status":"ok"}
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
index 2b1329e..2ea2dc3 100644
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
@@ -29,4 +29,10 @@ Use only the isolated trial repository.
 
 ## Notes
 
-No work performed yet.
+Script phase succeeded once; prepared.txt contains prepared. Agent work remains in this step.
+
+## Write step evidence
+
+Read `prepared.txt` (`prepared\n`) and the script note; did not rerun `ticket.py`.
+Wrote `coga/tasks/script-handoff/result.txt` and read it back: exactly `ready\n` (one trailing newline).
+Local origin/main reconciled; write step complete and ready for owner judgment.

```

## (none: no controller input; analysis/probe run or lifecycle run without replies)