# Relay relaunch chain — test artifact

## 1. draft (claude)

This document is a throwaway vehicle for the relaunch-chain teardown test. Each
workflow step appends its own section so there is something on disk to touch.

## 2. expand (claude)

The expand step picked up via supervisor auto-relaunch — no human typed
`relay launch` between draft and here. This second section is the on-disk proof
that the same `relay launch` process respawned a fresh claude REPL after tearing
down the draft one.

## 3. peer-pass (codex)

The peer-pass step picked up via supervisor auto-relaunch across the claude ->
codex agent rotation. The live task log has no second
`started (active -> in_progress) via relay launch` entry, and the current codex
REPL is parented by the original `relay launch` supervisor. This section is the
throwaway on-disk write before bumping to the human-check gate.
