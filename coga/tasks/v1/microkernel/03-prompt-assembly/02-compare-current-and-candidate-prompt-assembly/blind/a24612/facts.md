Item a24612, label Y (pair workflow-inline r2)

# workflow-inline, repetition 2

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

- launcher result: `{'exit_code': 0, 'termination_kind': 'done', 'termination_reason': 'sentinel-file (COGA_DONE_SENTINEL touched)', 'done_signalled': True}`; wall 56.4 s
- delivered prompt equals frozen (modulo marker): True
- live repo changed: False; effective writable roots: [[['/tmp/coga-prompt-trial-667707cc/.git', '/tmp']]]
- branch pre → post: main → main; worktree status post: `''`
- commits on HEAD since pre:

```
32760edec501cc3d893de4fc2c1198b02992e9ee Log: workflow-inline
b5aca14a09e3cfc3af96e2486cc78d319186712f Ticket: workflow-inline — step 2 (judge)
5725371fec170934363d42ed87447517148e6191 Log: workflow-inline

```
- local origin main log (newest first):

```
32760edec501cc3d893de4fc2c1198b02992e9ee Log: workflow-inline
b5aca14a09e3cfc3af96e2486cc78d319186712f Ticket: workflow-inline — step 2 (judge)
5725371fec170934363d42ed87447517148e6191 Log: workflow-inline
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
index bf18b2a..a17273b 100644
--- a/coga/log.md
+++ b/coga/log.md
@@ -1 +1,4 @@
 # Trial lifecycle log
+2026-11-13 12:58 v1 [workflow-inline] [human:trial-owner] trial adapter launch (workflow-inline)
+2026-11-13 12:58 v1 [workflow-inline] [agent:codex] advanced to step 2 (judge) → trial-owner
+2026-11-13 12:58 v1 [workflow-inline] [system] {"agent":"codex","agent_turns":3,"cache_creation_input_tokens":null,"cache_read_input_tokens":254592,"cli":"codex","content_status":"ok","elapsed_seconds":56.265947,"ended_at":"2026-11-13T20:58:59.015074Z","exit_code":0,"exit_kind":"done","human_turns":0,"input_tokens":28699,"model":"gpt-6.1-sol","outcome":"`result.txt` contains exactly `ready` followed by one newline. The blackboard records the verification, and local origin is unchanged. I’ll now bump once to hand off to the owner-held `judge` step.","outcome_status":"completed","output_tokens":1217,"provider":"openai","request":null,"schema":2,"session_id":"01a1d6b4-02bf-7141-b4d9-36e1f49b370b","slug":"workflow-inline","started_at":"2026-11-13T20:58:02.749127Z","step":"write","title":"workflow-inline","ts":"2026-11-13T20:58:59.015074Z","usage_reason":null,"usage_status":"ok"}
diff --git a/coga/tasks/workflow-inline/result.txt b/coga/tasks/workflow-inline/result.txt
new file mode 100644
index 0000000..395527d
--- /dev/null
+++ b/coga/tasks/workflow-inline/result.txt
@@ -0,0 +1 @@
+ready
diff --git a/coga/tasks/workflow-inline/ticket.md b/coga/tasks/workflow-inline/ticket.md
index 8136bed..ff1688a 100644
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
@@ -29,4 +29,8 @@ Use only the isolated trial repository.
 
 ## Notes
 
-No work performed yet.
+Wrote `coga/tasks/workflow-inline/result.txt` and read it back: exactly `ready` followed by one newline (`ready\n`, 6 bytes). Verification passed.
+
+Checkout was clean on `main`; current control ticket confirmed `in_progress`, step 1 (`write`). No recorded feature branch or PR. Fetched local origin before editing and again before handoff; `origin/main` matched HEAD both times. `git diff --check` passed.
+
+Handoff: write step complete; owner-held `judge` remains.

```

## (none: no controller input; analysis/probe run or lifecycle run without replies)