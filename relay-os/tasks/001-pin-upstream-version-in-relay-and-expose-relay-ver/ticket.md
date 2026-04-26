---
title: Pin upstream version in .relay/ and expose relay --version
status: ready
mode: interactive
owner: nick
assignee: nick
---

## Description

Right now nothing in a bootstrapped `relay-os/` records what version of the
upstream relay project produced its vendored CLI. After `relay init` or
`relay init --update` the `.relay/` dir is opaque — you can't tell which
commit it was cloned from, and `relay --version` doesn't exist.

This is the first thing that bites us when we want to dogfood relay on
itself: any "is this fixed in your copy?" question requires guesswork.

### Scope

- Capture the upstream commit SHA (and clone URL) inside `clone_upstream`,
  write it to `relay-os/.relay/RELAY_PIN` after the CLI is refreshed.
- Bump `pyproject.toml` version to `0.2.0` (vendored CLI + init/update merge
  + venv bootstrap warrants a minor bump).
- Add a top-level `relay --version` flag that prints both the package
  version and the pinned upstream SHA (when available).
- Echo the pin in the post-init / post-update output so users see it
  right after a refresh.

### Out of scope

- Any "you're behind upstream by N commits" drift detection — that needs a
  remote fetch every run. File a follow-up if useful.
- Versioning user content (`relay.toml`, skills, contexts). Pin is only
  about the vendored `.relay/` payload.

## Context

