Item 3c98d2, label Y (pair input-attended r1)

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

- launcher result: `{'exit_code': 0, 'termination_kind': 'done', 'termination_reason': 'sentinel-file (COGA_DONE_SENTINEL touched)', 'done_signalled': True}`; wall 78.9 s
- delivered prompt equals frozen (modulo marker): True
- live repo changed: False; effective writable roots: [[['/tmp/coga-prompt-trial-667707cc/.git', '/tmp']]]
- branch pre → post: main → main; worktree status post: `''`
- commits on HEAD since pre:

```
8a2f021106516b6e44e5182cefbad1df0a5d3962 Log: input-attended
1c3330e6cdea27ad72bcdc26fc077c4c24230f8a Ticket: input-attended — step 2 (judge)
33dda9e427bc43ce67386999dfbfd0220afa826d Log: input-attended

```
- local origin main log (newest first):

```
8a2f021106516b6e44e5182cefbad1df0a5d3962 Log: input-attended
1c3330e6cdea27ad72bcdc26fc077c4c24230f8a Ticket: input-attended — step 2 (judge)
33dda9e427bc43ce67386999dfbfd0220afa826d Log: input-attended
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
index bf18b2a..df194ae 100644
--- a/coga/log.md
+++ b/coga/log.md
@@ -1 +1,4 @@
 # Trial lifecycle log
+2026-11-13 12:38 v1 [input-attended] [human:trial-owner] trial adapter launch (input-attended)
+2026-11-13 12:40 v1 [input-attended] [agent:codex] advanced to step 2 (judge) → trial-owner
+2026-11-13 12:40 v1 [input-attended] [system] {"agent":"codex","agent_turns":4,"cache_creation_input_tokens":null,"cache_read_input_tokens":183296,"cli":"codex","content_status":"ok","elapsed_seconds":78.744791,"ended_at":"2026-11-13T20:40:10.407253Z","exit_code":0,"exit_kind":"done","human_turns":1,"input_tokens":36743,"model":"gpt-6.1-sol","outcome":"I’m using the `trial/report` skill to record the output path and verified content in the blackboard. The checkout is clean on `main`, and the ticket is at the `write` step; no branch or PR is recorded.","outcome_status":"completed","output_tokens":1033,"provider":"openai","request":"The required value is approved.","schema":2,"session_id":"01a1d6a2-72c9-7161-9c30-c6b77c13527b","slug":"input-attended","started_at":"2026-11-13T20:38:51.662462Z","step":"write","title":"input-attended","ts":"2026-11-13T20:40:10.407253Z","usage_reason":null,"usage_status":"ok"}
diff --git a/coga/tasks/input-attended/result.txt b/coga/tasks/input-attended/result.txt
new file mode 100644
index 0000000..367ff43
--- /dev/null
+++ b/coga/tasks/input-attended/result.txt
@@ -0,0 +1 @@
+approved
diff --git a/coga/tasks/input-attended/ticket.md b/coga/tasks/input-attended/ticket.md
index 6c4494d..ebb5431 100644
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
@@ -29,4 +29,8 @@ Use only the isolated trial repository.
 
 ## Notes
 
-No work performed yet.
+The owner supplied the required value: `approved`.
+
+Wrote `coga/tasks/input-attended/result.txt` and read it back: observed exactly `approved\n` (the value followed by one newline).
+
+The write step is complete; ready for the owner-held judge step.

```

## Controller inputs (UTC; run start 2026-11-13T20:38:51Z):

- 2026-11-13T20:39:36Z	The required value is approved.