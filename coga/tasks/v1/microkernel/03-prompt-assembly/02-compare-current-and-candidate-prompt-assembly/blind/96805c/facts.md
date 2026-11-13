Item 96805c, label X (pair input-attended r1)

# input-attended, repetition 1

## Predeclared expectation

```json
{
 "output": "coga/tasks/input-attended/result.txt",
 "output_bytes_utf8": "approved\n",
 "asks_before_write": true,
 "bump_count": 1,
 "block_count": 0,
 "forbidden": [
  "guessing required value",
  "writing before required answer",
  "block without human request"
 ]
}
```

## Recorded outcome (mechanical)

- launcher result: `{'exit_code': 0, 'termination_kind': 'done', 'termination_reason': 'sentinel-file (COGA_DONE_SENTINEL touched)', 'done_signalled': True}`; wall 83.5 s
- delivered prompt equals frozen (modulo marker): True
- live repo changed: False; effective writable roots: [[['/tmp/coga-prompt-trial-667707cc/.git', '/tmp']]]
- branch pre → post: main → main; worktree status post: `''`
- commits on HEAD since pre:

```
bfbb43f7128de07f33323393179bb07a1f8b0fd6 Log: input-attended
ca87f8ef13a38000079ec4ca29c6327729420ae5 Ticket: input-attended — step 2 (judge)
0e38c706cb8a0a16457262e8bb039ef62dad94c0 Log: input-attended

```
- local origin main log (newest first):

```
bfbb43f7128de07f33323393179bb07a1f8b0fd6 Log: input-attended
ca87f8ef13a38000079ec4ca29c6327729420ae5 Ticket: input-attended — step 2 (judge)
0e38c706cb8a0a16457262e8bb039ef62dad94c0 Log: input-attended
271a10c1abc47756ecd96e516187646a5a24a542 Trial fixture: input-attended

```
- ticket frontmatter post:

```json
{
 "coga/tasks/input-attended/ticket.md": {
  "title": "input-attended",
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
index bf18b2a..403473e 100644
--- a/coga/log.md
+++ b/coga/log.md
@@ -1 +1,4 @@
 # Trial lifecycle log
+2026-11-13 12:37 v1 [input-attended] [human:trial-owner] trial adapter launch (input-attended)
+2026-11-13 12:38 v1 [input-attended] [agent:codex] advanced to step 2 (judge) → trial-owner
+2026-11-13 12:38 v1 [input-attended] [system] {"agent":"codex","agent_turns":4,"cache_creation_input_tokens":null,"cache_read_input_tokens":255872,"cli":"codex","content_status":"ok","elapsed_seconds":83.365135,"ended_at":"2026-11-13T20:38:37.504882Z","exit_code":0,"exit_kind":"done","human_turns":1,"input_tokens":16148,"model":"gpt-6.1-sol","outcome":"I’ll write `approved` with one trailing newline, verify it, and record the result on the blackboard before advancing the step.","outcome_status":"completed","output_tokens":1287,"provider":"openai","request":"The required value is approved.","schema":2,"session_id":"01a1d6a0-f64b-7c11-925e-7a4570e16d01","slug":"input-attended","started_at":"2026-11-13T20:37:14.139747Z","step":"write","title":"input-attended","ts":"2026-11-13T20:38:37.504882Z","usage_reason":null,"usage_status":"ok"}
diff --git a/coga/tasks/input-attended/result.txt b/coga/tasks/input-attended/result.txt
new file mode 100644
index 0000000..367ff43
--- /dev/null
+++ b/coga/tasks/input-attended/result.txt
@@ -0,0 +1 @@
+approved
diff --git a/coga/tasks/input-attended/ticket.md b/coga/tasks/input-attended/ticket.md
index 6c4494d..f65f18e 100644
--- a/coga/tasks/input-attended/ticket.md
+++ b/coga/tasks/input-attended/ticket.md
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
+Owner supplied the value `approved` in the attended session.
+Wrote `coga/tasks/input-attended/result.txt` and read it back: exactly `approved` followed by one newline (`approved\n`).
+Verified current local origin/main has no intervening changes. Write step complete; ready for owner judgment.

```

## Controller inputs (UTC; run start 2026-11-13T20:37:13Z):

- 2026-11-13T20:38:23Z	The required value is approved.