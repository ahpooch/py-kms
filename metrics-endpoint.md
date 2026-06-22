## Prometheus Metrics Endpoint

The py-kms server exposes Prometheus metrics on a **separate port** from the WebUI. This provides clean separation between the web interface and observability concerns.

### Architecture

- **WebUI** (`pykms_WebUI.py`): Serves HTML pages at `http://<host>:8080`
- **Metrics** (`pykms_WebMetrics.py`): Serves Prometheus metrics at `http://<host>:9090/metrics`

**Key principle:** WebUI and Metrics are **fully independent**. Enable any combination you need.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBUI` | `0` | Enable WebUI |
| `WEBUI_PORT` | `8080` | Port for WebUI |
| `METRICS` | `0` | Enable metrics endpoint |
| `METRICS_PORT` | `9090` | Port for metrics |

### Deployment Modes

| WEBUI | METRICS | Ports | Use Case |
|-------|---------|-------|----------|
| 0 | 0 | — | KMS only (minimal, no monitoring) |
| 1 | 0 | 8080 | WebUI only (development, manual monitoring) |
| 0 | 1 | 9090 | Metrics only (production, minimal attack surface) |
| 1 | 1 | 8080 + 9090 | Full monitoring with WebUI and separate metrics endpoint |

### Docker Examples

**Metrics only (recommended for production):**
```bash
docker run -d --name py-kms --restart always \
  -p 1688:1688 -p 9090:9090 \
  -e METRICS=1 \
  -e METRICS_PORT=9090 \
  ghcr.io/py-kms-organization/py-kms
```

**WebUI only (development):**
```bash
docker run -d --name py-kms --restart always \
  -p 1688:1688 -p 8080:8080 \
  -e WEBUI=1 \
  -e WEBUI_PORT=8080 \
  ghcr.io/py-kms-organization/py-kms
```

**Both WebUI + Metrics:**
```bash
docker run -d --name py-kms --restart always \
  -p 1688:1688 -p 8080:8080 -p 9090:9090 \
  -e WEBUI=1 -e WEBUI_PORT=8080 \
  -e METRICS=1 -e METRICS_PORT=9090 \
  ghcr.io/py-kms-organization/py-kms
```

### Docker Compose

**Metrics only:**
```yaml
version: '3.8'
services:
  py-kms:
    image: ghcr.io/py-kms-organization/py-kms
    ports:
      - "1688:1688"  # KMS port
      - "9090:9090"  # Metrics port
    environment:
      - METRICS=1
      - METRICS_PORT=9090
    restart: always
```

**WebUI + Metrics:**
```yaml
version: '3.8'
services:
  py-kms:
    image: ghcr.io/py-kms-organization/py-kms
    ports:
      - "1688:1688"  # KMS port
      - "8080:8080"  # WebUI port
      - "9090:9090"  # Metrics port
    environment:
      - WEBUI=1
      - WEBUI_PORT=8080
      - METRICS=1
      - METRICS_PORT=9090
    restart: always
```

### Accessing Metrics

- **Metrics only mode:** `http://<host>:9090/metrics`
- **WebUI + Metrics mode:** `http://<host>:9090/metrics` (metrics always on separate port)

### Available Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `pykms_up` | gauge | Service status (1 = up, 0 = down) |
| `pykms_start_time_seconds` | gauge | Service start time as Unix timestamp |
| `pykms_uptime_seconds` | gauge | Service uptime in seconds |
| `pykms_clients_total` | gauge | Total number of unique clients |
| `pykms_clients_by_application{application="Windows\|Office"}` | gauge | Number of clients by application type |
| `pykms_client_request_count_total` | counter | Total number of activation requests from all clients |
| `pykms_activations_total{status="..."}` | gauge | Total number of activations by status (aggregated) |
| `pykms_activations_by_application{application="..."}` | gauge | Total number of activations by application type |
| `pykms_activations_by_sku{sku_id="..."}` | gauge | Total number of activations by SKU |
| `pykms_products_total` | gauge | Total number of products in KMS database |
| `pykms_products_with_gvlk_total` | gauge | Number of products with GVLK keys |
| `pykms_products_by_category{category="..."}` | gauge | Number of products by category |

### Example Output

```
# HELP pykms_up Service status (1=up, 0=down)
# TYPE pykms_up gauge
pykms_up 1
# HELP pykms_start_time_seconds Service start time as Unix timestamp
# TYPE pykms_start_time_seconds gauge
pykms_start_time_seconds 1718712000
# HELP pykms_uptime_seconds Service uptime in seconds
# TYPE pykms_uptime_seconds gauge
pykms_uptime_seconds 3600.5
# HELP pykms_clients_total Total number of unique clients
# TYPE pykms_clients_total gauge
pykms_clients_total 5
# HELP pykms_clients_by_application Number of clients by application type
# TYPE pykms_clients_by_application gauge
pykms_clients_by_application{application="Windows"} 3
pykms_clients_by_application{application="Office"} 2
# HELP pykms_client_request_count_total Total number of activation requests from all clients
# TYPE pykms_client_request_count_total counter
pykms_client_request_count_total 47
# HELP pykms_activations_total Total number of activations by status
# TYPE pykms_activations_total gauge
pykms_activations_total{status="Licensed"} 4
pykms_activations_total{status="Grace Period"} 1
```

### Prometheus Configuration

```yaml
scrape_configs:
  - job_name: 'py-kms'
    static_configs:
      - targets: ['<py-kms-host>:9090']
    metrics_path: /metrics
    scrape_interval: 30s
```

### Grafana Dashboard

Example queries:

- **Total active clients:** `pykms_clients_total`
- **Clients by application type:** `pykms_clients_by_application`
- **Service uptime:** `pykms_uptime_seconds`
- **Total activation requests:** `pykms_client_request_count_total`
- **Activations by status:** `pykms_activations_total{status="Licensed"}`
- **Activations by application type:** `pykms_activations_by_application`
- **Activations by SKU:** `pykms_activations_by_sku`

### Notes

- The metrics endpoint does not require authentication. If you expose it publicly, consider placing it behind a reverse proxy with authentication.
- Metrics are generated in real-time from the SQLite database.
- **Cardinality:** Activation metrics are **aggregated** to avoid cardinality explosion in Prometheus. Per-client labels (`client_machine_id`) are intentionally excluded.
- **SQLite requirement:** SQLite is required for client/activation metrics. Without it, only basic service metrics (up, uptime) and static product info are available.
