Item ff9470, label Y (pair author-paused r1)

# author-paused, repetition 1

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

- launcher result: `{'exit_code': 0, 'termination_kind': 'natural', 'termination_reason': None, 'done_signalled': False}`; wall 151.1 s
- delivered prompt equals frozen (modulo marker): True
- live repo changed: False; effective writable roots: [[['/tmp/coga-prompt-trial-667707cc/.git', '/tmp']]]
- branch pre → post: main → main; worktree status post: `' M coga/tasks/author-paused/ticket.md\n'`
- commits on HEAD since pre:

```
8074ac621bc5aa2d720024ce11418fbac86ce448 Log: bootstrap/ticket
efb62c48c0e74c4d196252ba01d9461dd0d9f9d2 Log: author-paused

```
- local origin main log (newest first):

```
8074ac621bc5aa2d720024ce11418fbac86ce448 Log: bootstrap/ticket
efb62c48c0e74c4d196252ba01d9461dd0d9f9d2 Log: author-paused
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
index bf18b2a..62f699a 100644
--- a/coga/log.md
+++ b/coga/log.md
@@ -1 +1,3 @@
 # Trial lifecycle log
+2026-11-13 12:26 v1 [author-paused] [human:trial-owner] ticket authoring launched (trial adapter)
+2026-11-13 12:28 v1 [bootstrap/ticket] [system] {"agent":"codex","agent_turns":4,"cache_creation_input_tokens":null,"cache_read_input_tokens":255616,"cli":"codex","content_status":"ok","elapsed_seconds":150.993434,"ended_at":"2026-11-13T20:28:41.792733Z","exit_code":0,"exit_kind":"natural","human_turns":2,"input_tokens":46672,"model":"gpt-6.1-sol","outcome":"Confirmed. The ticket remains paused; no workflow advancement or task execution.","outcome_status":"completed","output_tokens":856,"provider":"openai","request":"Add this sentence to the Description: Verify the output before handoff. Preserve the paused status, current step and frozen workflow. Do not run the work. Confirmed. Keep it paused; do not advance.","schema":2,"session_id":"01a1d696-d718-7c91-905c-888170e0d0a1","slug":"bootstrap/ticket","started_at":"2026-11-13T20:26:10.799299Z","step":null,"title":"author-paused","ts":"2026-11-13T20:28:41.792733Z","usage_reason":null,"usage_status":"ok"}
diff --git a/coga/tasks/author-paused/ticket.md b/coga/tasks/author-paused/ticket.md
index e94603a..0da7b3a 100644
--- a/coga/tasks/author-paused/ticket.md
+++ b/coga/tasks/author-paused/ticket.md
@@ -19,7 +19,7 @@ step: 1 (write)
 
 ## Description
 
-Preserve the existing intent: write the agreed result after the owner resumes execution.
+Preserve the existing intent: write the agreed result after the owner resumes execution. Verify the output before handoff.
 
 ## Context
 

```

## Controller inputs (UTC; run start 2026-11-13T20:26:10Z):

- 2026-11-13T20:26:55Z	Add this sentence to the Description: Verify the output before handoff. Preserve the paused status, current step and frozen workflow. Do not run the work.
- 2026-11-13T20:28:15Z	Confirmed. Keep it paused; do not advance.
- 2026-11-13T20:28:41Z	<key C-c>