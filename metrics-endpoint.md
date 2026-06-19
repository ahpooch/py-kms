## Prometheus Metrics Endpoint

The py-kms WebUI exposes a `/metrics` endpoint that provides KMS server statistics in Prometheus text format. This allows you to monitor your KMS server using Prometheus and visualize the data with tools like Grafana.

### Enabling the Metrics Endpoint

The metrics endpoint is available when the WebUI is enabled. To enable the WebUI:

**Docker:**
```bash
docker run -d --name py-kms --restart always \
  -p 1688:1688 -p 8080:8080 \
  -e WEBUI=1 \
  ghcr.io/py-kms-organization/py-kms
```

**Docker Compose:**
```yaml
version: '3.8'
services:
  py-kms:
    image: ghcr.io/py-kms-organization/py-kms
    ports:
      - "1688:1688"  # KMS port
      - "8080:8080"  # WebUI/Metrics port
    environment:
      - WEBUI=1
    restart: always
```

### Accessing Metrics

Once the WebUI is enabled, the metrics endpoint is available at:
```
http://<host>:8080/metrics
```

### Available Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `pykms_up` | gauge | Service status (1 = up, 0 = down) |
| `pykms_start_time_seconds` | gauge | Service start time as Unix timestamp |
| `pykms_uptime_seconds` | gauge | Service uptime in seconds |
| `pykms_requests_total` | counter | Total number of HTTP requests to WebUI |
| `pykms_clients_total` | gauge | Total number of unique clients |
| `pykms_clients_by_application{application="Windows\|Office"}` | gauge | Number of clients by application type |
| `pykms_client_request_count{client_machine_id="...",application_id="...",sku_id="..."}` | gauge | Number of activation requests from each client |
| `pykms_activations_by_status{client_machine_id="...",application_id="...",sku_id="...",status="..."}` | gauge | Activation status of each client |
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
# HELP pykms_requests_total Total number of HTTP requests to WebUI
# TYPE pykms_requests_total counter
pykms_requests_total 42
# HELP pykms_clients_total Total number of unique clients
# TYPE pykms_clients_total gauge
pykms_clients_total 5
# HELP pykms_clients_by_application Number of Windows clients
# TYPE pykms_clients_by_application gauge
pykms_clients_by_application{application="Windows"} 3
pykms_clients_by_application{application="Office"} 2
# HELP pykms_client_request_count Number of activation requests from this client
# TYPE pykms_client_request_count gauge
pykms_client_request_count{client_machine_id="abc123",application_id="Windows",sku_id="Windows-11"} 5
pykms_client_request_count{client_machine_id="def456",application_id="Office",sku_id="Office-2021"} 3
# HELP pykms_products_total Total number of products in KMS database
# TYPE pykms_products_total gauge
pykms_products_total 150
# HELP pykms_products_with_gvlk_total Number of products with GVLK keys
# TYPE pykms_products_with_gvlk_total gauge
pykms_products_with_gvlk_total 142
```

### Prometheus Configuration

Add the following to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'py-kms'
    static_configs:
      - targets: ['<py-kms-host>:8080']
    metrics_path: /metrics
    scrape_interval: 30s
```

### Grafana Dashboard

You can import the metrics into Grafana to create dashboards. Example queries:

- **Total active clients:**
  ```
  pykms_clients_total
  ```

- **Clients by application type:**
  ```
  pykms_clients_by_application
  ```

- **Service uptime:**
  ```
  pykms_uptime_seconds
  ```

- **Activation requests per client:**
  ```
  pykms_client_request_count
  ```

### Notes

- The metrics endpoint does not require authentication. If you expose it publicly, consider placing it behind a reverse proxy with authentication.
- Metrics are generated in real-time from the SQLite database.
- Client-specific metrics include labels for `client_machine_id`, `application_id`, and `sku_id` for detailed filtering.
