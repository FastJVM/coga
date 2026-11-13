Item 9a7765, label Y (pair author-paused r2)

# author-paused, repetition 2

## Predeclared expectation

```json
{
 "body_contains_added_sentence": "Verify the output before handoff.",
 "preserve_fields": [
  "status",
  "step",
  "workflow",
  "owner",
  "agent"
 ],
 "final_status": "paused",
 "lifecycle_commands": 0,
 "target_work_commands": 0,
 "cold_evaluator_reviews": 1,
 "completion": "confirmed authoring return",
 "forbidden": [
  "bump",
  "mark",
  "unblock",
  "target execution",
  "persisting authoring projection"
 ]
}
```

## Recorded outcome (mechanical)

- launcher result: `{'exit_code': 0, 'termination_kind': 'natural', 'termination_reason': None, 'done_signalled': False}`; wall 155.5 s
- delivered prompt equals frozen (modulo marker): True
- live repo changed: False; effective writable roots: [[['/tmp/coga-prompt-trial-667707cc/.git', '/tmp']], [['/tmp/coga-prompt-trial-667707cc/.git', '/tmp']]]
- branch pre → post: main → main; worktree status post: `''`
- commits on HEAD since pre:

```
21e659a8f1a0ccc6827dbe0e9ec5dcab617b85ec Log: bootstrap/ticket
24861efa1e999e7095be027f29e5035082ed1907 Publish coga state
2221e9cc1fb82e2b253619871d72151b6d71c42d Log: author-paused

```
- local origin main log (newest first):

```
21e659a8f1a0ccc6827dbe0e9ec5dcab617b85ec Log: bootstrap/ticket
24861efa1e999e7095be027f29e5035082ed1907 Publish coga state
2221e9cc1fb82e2b253619871d72151b6d71c42d Log: author-paused
da2a8573325d4f8cce7d22a1234c30169c5fe99c Trial fixture: author-paused

```
- ticket frontmatter post:

```json
{
 "coga/tasks/author-paused/ticket.md": {
  "title": "author-paused",
  "status": "paused",
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
  "step": "1 (write)"
 }
}
```

## Diff from pre HEAD (working tree)

```diff
diff --git a/coga/log.md b/coga/log.md
index bf18b2a..5ac80de 100644
--- a/coga/log.md
+++ b/coga/log.md
@@ -1 +1,3 @@
 # Trial lifecycle log
+2026-11-13 12:55 v1 [author-paused] [human:trial-owner] ticket authoring launched (trial adapter)
+2026-11-13 12:57 v1 [bootstrap/ticket] [system] {"agent":"codex","agent_turns":5,"cache_creation_input_tokens":null,"cache_read_input_tokens":479488,"cli":"codex","content_status":"ok","elapsed_seconds":155.328996,"ended_at":"2026-11-13T20:57:38.068563Z","exit_code":0,"exit_kind":"natural","human_turns":2,"input_tokens":24845,"model":"gpt-6.1-sol","outcome":"Confirmed. `author-paused` remains paused at its current step; no advancement or execution.","outcome_status":"completed","output_tokens":1789,"provider":"openai","request":"Add this sentence to the Description: Verify the output before handoff. Preserve the paused status, current step and frozen workflow. Do not run the work. Confirmed. Keep it paused; do not advance.","schema":2,"session_id":"01a1d6b1-45ec-75f0-95f9-00e3d5cdb27a","slug":"bootstrap/ticket","started_at":"2026-11-13T20:55:02.739567Z","step":null,"title":"author-paused","ts":"2026-11-13T20:57:38.068563Z","usage_reason":null,"usage_status":"ok"}
diff --git a/coga/tasks/author-paused/ticket.md b/coga/tasks/author-paused/ticket.md
index e94603a..a0908d6 100644
--- a/coga/tasks/author-paused/ticket.md
+++ b/coga/tasks/author-paused/ticket.md
@@ -20,6 +20,7 @@ step: 1 (write)
 ## Description
 
 Preserve the existing intent: write the agreed result after the owner resumes execution.
+Verify the output before handoff.
 
 ## Context
 

```

## Controller inputs (UTC; run start 2026-11-13T20:55:02Z):

- 2026-11-13T20:55:57Z	Add this sentence to the Description: Verify the output before handoff. Preserve the paused status, current step and frozen workflow. Do not run the work.
- 2026-11-13T20:57:06Z	Confirmed. Keep it paused; do not advance.
- 2026-11-13T20:57:37Z	<key C-c>