# Cloud Run Infrastructure

> **Assumes `/google-agents-cli-scaffold` scaffolding.** If your project isn't scaffolded yet, see `/google-agents-cli-scaffold` first.

## Scaling & Resource Defaults

Agents CLI scaffolds Cloud Run infrastructure in `deployment/terraform/service.tf`. Check that file for current resource limits, scaling configuration, concurrency, and session affinity settings.

Key settings to be aware of: `cpu_idle` (CPU allocation strategy), `min_instance_count` (cold start avoidance), `max_instance_request_concurrency` (concurrency per instance), and `session_affinity` (sticky routing).

## Dockerfile

Scaffolded projects include a `Dockerfile` using single-stage build with `uv` for dependency management. Check the project root `Dockerfile` for the exact configuration.

## FastAPI Endpoints

Available endpoints vary by project template. Check `app/fast_api_app.py` for the exact routes in your project.

## Session Types

| Type | Configuration | Use Case |
|------|--------------|----------|
| **In-memory** | Default (`session_service_uri = None`) | Local dev only; lost on instance restart |
| **Cloud SQL** | `--session-type cloud_sql` at scaffold time | Production persistent sessions (Postgres 15, IAM auth) |
| **Agent Runtime** | `session_service_uri = agentengine://{resource_name}` | When using Agent Runtime as session backend |

Cloud SQL session infrastructure (instance, database, Cloud SQL Unix socket volume mount) is configured in `deployment/terraform/service.tf`.

> **Manual Deployment Warning:** When using Cloud SQL without Terraform (e.g., direct `gcloud run deploy` with `--add-cloudsql-instances`), you MUST manually grant `roles/cloudsql.client` to the runtime service account, otherwise the connection will fail with authorization errors.

## Network & Ingress

Default ingress is `INGRESS_TRAFFIC_ALL` (public). To restrict, change the `ingress` setting in `service.tf` to `INGRESS_TRAFFIC_INTERNAL_ONLY` (VPC only) or `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER` (internal + GCLB).

IAP (Identity-Aware Proxy) can be enabled by running `agents-cli deploy` with the appropriate Terraform variable override — for example, setting `iap_enabled = true` in your Terraform configuration adds Google identity authentication without code changes.

VPC connectors are not configured by default. Add them in custom Terraform if needed for private resource access (see `references/terraform-patterns.md`).
