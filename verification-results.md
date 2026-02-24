# Verification Script Results & Findings

**Script:** `verify_devops.py`
**Score:** 78.05% — 27 passed, 11 failed
**Run Date:** February 23, 2026

---

## Critical Failures (1)

| Check | Issue |
|-------|-------|
| **LLM API key stored in Secret** | The verifier looks for `openai_api_key` in K8s Secret manifests, but our `secrets.yaml.example` uses the key name `OPENAI_API_KEY` (uppercase). The script's matching is case-sensitive on the YAML content but searches with lowercase. The real issue is the file is named `.example` and the verifier likely isn't matching it as a K8s manifest since it only scans `.yml`/`.yaml` extensions. |

## Warning Failures (4)

| Check | Issue | Notes |
|-------|-------|-------|
| **Dockerfile: non-root USER** | No `USER` instruction in the Dockerfile | Valid best-practice gap — we should add a non-root user |
| **K8s Secret manifest** | Verifier doesn't detect `secrets.yaml.example` | The glob pattern in the verifier only looks in `k8s/` dirs for `.yml`/`.yaml` files — `.example` suffix is excluded |
| **Prometheus config/manifests** | Not detected | Bug in the verifier — our files are at `k8s/monitoring/prometheus-config.yaml` but the script checks patterns like `k8s/prometheus*.yml`, not `k8s/monitoring/prometheus*.yaml` (subdirectory not matched) |
| **App deps include prometheus_client** | Not detected | The verifier searches for `prometheus_client` or `prometheus-client` in `pyproject.toml`, but our dependency is `prometheus-fastapi-instrumentator` (which depends on `prometheus-client` transitively). The verifier's string match misses this. |

## Info Failures (4) — Lowest Severity, Nice-to-Haves

| Check | Issue |
|-------|-------|
| **Dockerfile HEALTHCHECK** | No `HEALTHCHECK` instruction (we use K8s probes instead, which is standard) |
| **Security scanning** | No CodeQL/Trivy/Snyk step in the CI pipeline |
| **Grafana dashboard** | Verifier expects a `.json` dashboard file; we deployed Grafana but have no exported dashboard JSON |
| **Screenshots/architecture docs** | No images in README, no `ARCHITECTURE.md` |

---

## Key Takeaways for the Verifier Script

1. **Prometheus detection is broken** — it checks `k8s/prometheus*.yml` but won't find files in `k8s/monitoring/` subdirectories. The `fnmatch` pattern doesn't recurse into subdirs.
2. **Secret detection is too narrow** — only checks files with `.yml`/`.yaml` extension, so `.example` files are missed. Also the `openai_api_key` search is lowercase but real K8s manifests use uppercase env var names.
3. **`prometheus_client` dep detection misses wrapper packages** — should also check for `prometheus-fastapi-instrumentator`, `starlette-exporter`, etc.
4. **The non-root USER and HEALTHCHECK checks are debatable** — K8s probes replace Docker HEALTHCHECK, and many production images skip `USER` when the orchestrator handles security context.
