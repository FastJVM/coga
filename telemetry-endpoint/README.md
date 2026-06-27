# Coga telemetry relay

A tiny, inspectable GCP Cloud Function (gen2) that receives Coga's anonymous
install ping and forwards a one-line message to an internal Slack channel. It is
the only piece of telemetry that lives off the user's machine, and it is
deliberately as small and legible as possible.

There is **no datastore**. At ~100 users the Slack channel *is* the record —
counting distinct `instance_id`s and recent `last_run`s is done by eye/search.
BigQuery and an "active installs" dashboard are intentionally deferred.

## The three-field contract

The client (`coga telemetry send`) POSTs exactly:

```json
{"instance_id": "<uuid4>", "tickets_total": 12, "last_run": "2026-06-19"}
```

The function validates the shape (`instance_id` must look like a uuid4,
`tickets_total` a non-negative int, `last_run` a `YYYY-MM-DD` date) and posts:

```
ping: instance=<uuid4> tickets=12 last_run=2026-06-19
```

It then returns `204` with an empty body. It returns `204` on **every** path —
malformed input or a Slack error are logged server-side and still answered
`204`, because the client ignores the body and a duplicate ping is just a
harmless duplicate line.

## No-PII controls (both load-bearing)

1. **The handler never reads the client IP.** `main.py` touches no
   `X-Forwarded-For` / `remote_addr` / IP header.
2. **The request access log's `remoteIp` is suppressed.** Cloud Functions
   request logs include `httpRequest.remoteIp` by default, so `deploy.sh`
   applies a Cloud Logging exclusion filter on this function's request logs.
   Without this, the IP would be persisted in logs even though the handler
   never reads it.
3. **Only the three known fields are forwarded.** Any extra key in the body is
   ignored and never reaches Slack — belt-and-suspenders if a future client (or
   an attacker) adds fields.

The Slack incoming webhook is held server-side as a Secret Manager secret and
injected as the `SLACK_WEBHOOK_URL` env var. It is never in the shipped client.

## Deploy

Everything except the credentialed run is in this directory. The owner runs:

```sh
PROJECT_ID=my-proj REGION=us-central1 \
SLACK_WEBHOOK_URL='https://hooks.slack.com/services/XXX/YYY/ZZZ' \
  ./deploy.sh
```

`deploy.sh` is idempotent: it stores/updates the webhook secret, deploys the
gen2 function `--allow-unauthenticated` (anonymous installs POST without
credentials), applies the IP-drop log exclusion, and prints the function URL.

Pin that URL into `TELEMETRY_URL` in `src/coga/telemetry.py` (or export
`COGA_TELEMETRY_URL=<url>` to point a single checkout at a test relay).

## Abuse / cost posture

The function is the only holder of the webhook, so the webhook can't be abused
directly. The endpoint is unauthenticated by necessity (random installs have no
credentials); at this scale that's acceptable. If volume ever warrants it, a
Cloud Armor rate-limit policy in front of the function is the natural next step
— noted, not required for v1.

## Local test

```sh
pip install -r requirements.txt
SLACK_WEBHOOK_URL='https://hooks.slack.com/services/XXX' \
  functions-framework --target telemetry --debug
# then, in another shell:
curl -i -X POST localhost:8080 \
  -H 'Content-Type: application/json' \
  -d '{"instance_id":"d13a905a-0856-44cc-afa5-d5494364aa7a","tickets_total":12,"last_run":"2026-06-19"}'
# -> HTTP/1.1 204, one line posted to Slack
```
