---
title: Correct README claims about prompt report output
status: draft
owner: nicktoper
workflow: null
---

## Description

Correct the README claim that coga launch --prompt-report shows the exact prompt. The reported behavior is a layer and token-count report, not full prompt text.

Verify installed help and current source, then make the README accurately describe the existing inspection surface with a runnable target-specific example. If full prompt output is desired, explicitly scope that option and its behavior before implementing it; the default scope here is the factual documentation correction. Done when documented output matches a representative invocation and does not claim unavailable functionality.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
