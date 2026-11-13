---
title: stateless-recurring
contexts:
- trial/format
---

## Description

Write `ready` to `coga/bootstrap/trial/result.txt`. Preserve launch argument boundaries. End with one successful `coga slack --task bootstrap/trial --message "Trial report: ready; arguments preserved"` to report and release this stateless session. There is no task lifecycle.

## Context

Use only the isolated trial repository.
