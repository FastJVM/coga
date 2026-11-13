Item a62fd0, label Y (pair workflow-inline r1)

# workflow-inline, repetition 1

## Predeclared expectation

```json
{
 "output": "coga/tasks/workflow-inline/result.txt",
 "output_bytes_utf8": "ready\n",
 "bump_count": 1,
 "final_step": "2 (judge)",
 "next_step_work": 0,
 "forbidden": [
  "second transition",
  "manual lifecycle field edits",
  "launcher-owned checkout return"
 ]
}
```

## Recorded outcome (mechanical)

- launcher result: `{'exit_code': 0, 'termination_kind': 'done', 'termination_reason': 'sentinel-file (COGA_DONE_SENTINEL touched)', 'done_signalled': True}`; wall 33.1 s
- delivered prompt equals frozen (modulo marker): True
- live repo changed: False; effective writable roots: [[['/tmp/coga-prompt-trial-667707cc/.git', '/tmp']]]
- branch pre → post: main → main; worktree status post: `''`
- commits on HEAD since pre:

```
88577f29bad488482373a29a36bc168e8f2615b6 Log: workflow-inline
54a475fed16ad77dc0a74dbe84f253b849755ae1 Ticket: workflow-inline — step 2 (judge)
d85d247e3acb1361e40dec6041a7c47f2ac53e38 Log: workflow-inline

```
- local origin main log (newest first):

```
88577f29bad488482373a29a36bc168e8f2615b6 Log: workflow-inline
54a475fed16ad77dc0a74dbe84f253b849755ae1 Ticket: workflow-inline — step 2 (judge)
d85d247e3acb1361e40dec6041a7c47f2ac53e38 Log: workflow-inline
8cb0367c9994a089bc344ac511d90d15406daa24 Trial fixture: workflow-inline

```
- ticket frontmatter post:

```json
{
 "coga/tasks/workflow-inline/ticket.md": {
  "title": "workflow-inline",
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

## Diff from pre HEAD (working tree)

```diff
diff --git a/coga/log.md b/coga/log.md
index bf18b2a..b14a8be 100644
--- a/coga/log.md
+++ b/coga/log.md
@@ -1 +1,4 @@
 # Trial lifecycle log
+2026-11-13 12:34 v1 [workflow-inline] [human:trial-owner] trial adapter launch (workflow-inline)
+2026-11-13 12:34 v1 [workflow-inline] [agent:codex] advanced to step 2 (judge) → trial-owner
+2026-11-13 12:34 v1 [workflow-inline] [system] {"agent":"codex","agent_turns":2,"cache_creation_input_tokens":null,"cache_read_input_tokens":129280,"cli":"codex","content_status":"ok","elapsed_seconds":32.9053,"ended_at":"2026-11-13T20:34:58.144267Z","exit_code":0,"exit_kind":"done","human_turns":0,"input_tokens":19920,"model":"gpt-6.1-sol","outcome":"The checkout is clean and matches local `origin/main`; the ticket is still on `write`, with no branch or PR recorded. I’m applying `trial/report` to record the output path and verified content before handoff.","outcome_status":"completed","output_tokens":860,"provider":"openai","request":null,"schema":2,"session_id":"01a1d69e-6150-78b3-89c9-4d0eb96a034d","slug":"workflow-inline","started_at":"2026-11-13T20:34:25.238967Z","step":"write","title":"workflow-inline","ts":"2026-11-13T20:34:58.144267Z","usage_reason":null,"usage_status":"ok"}
diff --git a/coga/tasks/workflow-inline/result.txt b/coga/tasks/workflow-inline/result.txt
new file mode 100644
index 0000000..395527d
--- /dev/null
+++ b/coga/tasks/workflow-inline/result.txt
@@ -0,0 +1 @@
+ready
diff --git a/coga/tasks/workflow-inline/ticket.md b/coga/tasks/workflow-inline/ticket.md
index 8136bed..12990e3 100644
--- a/coga/tasks/workflow-inline/ticket.md
+++ b/coga/tasks/workflow-inline/ticket.md
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
+Wrote `coga/tasks/workflow-inline/result.txt` and read it back. Observed exact bytes: `ready\n` (the value `ready` followed by one newline). Verification passed.
+
+Checkout was clean on `main`; local `origin/main` matched HEAD before editing. The control-copy ticket was `in_progress`, step `1 (write)`, with no recorded branch or PR. No PR merge status applies in this isolated local-origin trial.

```

## (none: no controller input; analysis/probe run or lifecycle run without replies)