Item 37fc94, label X (pair script-handoff r1)

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

- launcher result: `{'exit_code': 0, 'termination_kind': 'done', 'termination_reason': 'sentinel-file (COGA_DONE_SENTINEL touched)', 'done_signalled': True}`; wall 54.4 s
- delivered prompt equals frozen (modulo marker): True
- live repo changed: False; effective writable roots: [[['/tmp/coga-prompt-trial-667707cc/.git', '/tmp']]]
- branch pre → post: main → main; worktree status post: `''`
- commits on HEAD since pre:

```
d2be57be8c916bde075402e59f14d899c6dde373 Log: script-handoff
5a4f05e92946a246a981a6dcd28779305d6658b3 Ticket: script-handoff — step 2 (judge)
34a8e6dfc796a975be1e74895b6d39864338fa98 Publish coga state
a1d2df83068d7474311491bb8ba316285a856c8a Log: script-handoff

```
- local origin main log (newest first):

```
d2be57be8c916bde075402e59f14d899c6dde373 Log: script-handoff
5a4f05e92946a246a981a6dcd28779305d6658b3 Ticket: script-handoff — step 2 (judge)
34a8e6dfc796a975be1e74895b6d39864338fa98 Publish coga state
a1d2df83068d7474311491bb8ba316285a856c8a Log: script-handoff
d73517a9341f5e18c0ad7fb6c5b686a3a7ed65f6 Log: script-handoff
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
index 11474fa..787b8dc 100644
--- a/coga/log.md
+++ b/coga/log.md
@@ -1,2 +1,6 @@
 # Trial lifecycle log
 2026-11-13 12:48 v1 [script-handoff] [system] launched as a script (ticket.py)
+2026-11-13 12:48 v1 [script-handoff] [system] script exited with code 0
+2026-11-13 12:48 v1 [script-handoff] [human:trial-owner] trial adapter launch (script-handoff)
+2026-11-13 12:49 v1 [script-handoff] [agent:codex] advanced to step 2 (judge) → trial-owner
+2026-11-13 12:49 v1 [script-handoff] [system] {"agent":"codex","agent_turns":3,"cache_creation_input_tokens":null,"cache_read_input_tokens":247808,"cli":"codex","content_status":"ok","elapsed_seconds":54.255886,"ended_at":"2026-11-13T20:49:33.646139Z","exit_code":0,"exit_kind":"done","human_turns":0,"input_tokens":21089,"model":"gpt-6.1-sol","outcome":"`result.txt` reads back as exactly `ready` followed by one newline. The blackboard records the verification, and origin has no intervening changes. I’ll now advance the completed write step.","outcome_status":"completed","output_tokens":1249,"provider":"openai","request":null,"schema":2,"session_id":"01a1d6ab-6a40-78d0-9936-a50db0098732","slug":"script-handoff","started_at":"2026-11-13T20:48:39.390253Z","step":"write","title":"script-handoff","ts":"2026-11-13T20:49:33.646139Z","usage_reason":null,"usage_status":"ok"}
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
index 2b1329e..e94c7f9 100644
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
+Verified `coga/tasks/script-handoff/prepared.txt` contains `prepared\n`; read the script note without rerunning `ticket.py`. Wrote `coga/tasks/script-handoff/result.txt` and read back exactly `ready\n` (one trailing newline). Script handoff preserved and published. No feature branch or PR is associated with this routine trial state. Write step complete; owner judgment remains.

```

## (none: no controller input; analysis/probe run or lifecycle run without replies)