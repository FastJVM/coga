# cleanup/

Everything that must be done before the marketing materials ship.

The owner opened this directory on 2026-09-03 while finishing step 2 of
`marketing/phase-0-audit`. That audit ran the README quickstart end to end on
a fresh repo and found the first-run path broken in several independent ways;
these tickets are those findings, plus the release that makes a first run
possible at all. The audit ticket itself holds the evidence — its `## Step 1
findings` section is the source for every ticket here.

Drain the queue with `coga megalaunch cleanup`.

## Ordering

One hard dependency, recorded in the ticket bodies rather than in the
directory name: `fix-coga-init-crash-on-python-3-11-by-adding-the-r` must land
before `publish-coga-1-0-to-pypi` cuts the release, or the release must raise
its Python floor instead. Everything else is independent and runs in age
order.

Whether the remaining polish also ships inside 1.0 is an open owner decision.
If it should, rename the tickets with `1-` / `2-` / `3-` prefixes: megalaunch
runs a numbered sub-directory in number order, and plain `mv` is the whole
mechanism.

## Not here

- `marketing/readme-top` and `marketing/discord` are marketing work with their
  own tickets, not cleanup.
- The community home decision belongs to `marketing/discord`; the hygiene
  ticket here deliberately stops short of it.
