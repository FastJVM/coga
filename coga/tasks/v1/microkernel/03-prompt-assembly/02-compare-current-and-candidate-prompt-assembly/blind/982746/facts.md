Item 982746, label Y (pair input-attended r2)

# input-attended, repetition 2

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

- launcher result: `{'exit_code': 0, 'termination_kind': 'done', 'termination_reason': 'sentinel-file (COGA_DONE_SENTINEL touched)', 'done_signalled': True}`; wall 139.6 s
- delivered prompt equals frozen (modulo marker): True
- live repo changed: False; effective writable roots: [[['/tmp/coga-prompt-trial-667707cc/.git', '/tmp']]]
- branch pre → post: main → main; worktree status post: `''`
- commits on HEAD since pre:

```
62475174c94191d5c5965bc8cc4be388002badf7 Log: input-attended
6b0d2eae3997205bb620293dac7e5144077af774 Ticket: input-attended — step 2 (judge)
3c7375638c913af5a873561b24d93748c8bcf67a Log: input-attended

```
- local origin main log (newest first):

```
62475174c94191d5c5965bc8cc4be388002badf7 Log: input-attended
6b0d2eae3997205bb620293dac7e5144077af774 Ticket: input-attended — step 2 (judge)
3c7375638c913af5a873561b24d93748c8bcf67a Log: input-attended
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
index bf18b2a..3f3f086 100644
--- a/coga/log.md
+++ b/coga/log.md
@@ -1 +1,4 @@
 # Trial lifecycle log
+2026-11-13 13:02 v1 [input-attended] [human:trial-owner] trial adapter launch (input-attended)
+2026-11-13 13:05 v1 [input-attended] [agent:codex] advanced to step 2 (judge) → trial-owner
+2026-11-13 13:05 v1 [input-attended] [system] {"agent":"codex","agent_turns":4,"cache_creation_input_tokens":null,"cache_read_input_tokens":348544,"cli":"codex","content_status":"ok","elapsed_seconds":139.45002,"ended_at":"2026-11-13T21:05:08.105044Z","exit_code":0,"exit_kind":"done","human_turns":1,"input_tokens":28061,"model":"gpt-6.1-sol","outcome":"I’ll write `approved` followed by one newline, verify it, and record the evidence using `trial/report` before advancing the step.","outcome_status":"completed","output_tokens":1168,"provider":"openai","request":"The required value is approved.","schema":2,"session_id":"01a1d6b8-602d-78d1-aab3-7cbc59d9346e","slug":"input-attended","started_at":"2026-11-13T21:02:48.655024Z","step":"write","title":"input-attended","ts":"2026-11-13T21:05:08.105044Z","usage_reason":null,"usage_status":"ok"}
diff --git a/coga/tasks/input-attended/result.txt b/coga/tasks/input-attended/result.txt
new file mode 100644
index 0000000..367ff43
--- /dev/null
+++ b/coga/tasks/input-attended/result.txt
@@ -0,0 +1 @@
+approved
diff --git a/coga/tasks/input-attended/ticket.md b/coga/tasks/input-attended/ticket.md
index 6c4494d..33af3d5 100644
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
@@ -29,4 +29,4 @@ Use only the isolated trial repository.
 
 ## Notes
 
-No work performed yet.
+Owner selected `approved`. Wrote `coga/tasks/input-attended/result.txt` and read it back: exactly `approved` followed by one newline. Write step complete; ready for owner judgment.

```

## Controller inputs (UTC; run start 2026-11-13T21:02:48Z):

- 2026-11-13T21:04:55Z	The required value is approved.