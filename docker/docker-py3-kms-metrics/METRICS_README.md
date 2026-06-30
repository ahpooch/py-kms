# Prometheus Metrics for py-kms

This document describes the Prometheus metrics implementation for py-kms.

## Overview

The metrics implementation provides a separate Prometheus metrics server that exposes KMS activation and request metrics without interfering with the existing KMS server or Flask WebUI.

## Architecture

```
┌─────────────────────────────────────────────┐
│              py-kms Container               │
│                                             │
│  ┌─────────────┐  ┌───────────────────────┐ │
│  │  KMS Server │  │  Metrics Server       │ │
│  │  (port 1688)│  │  (port 9090)          │ │
│  └──────┬──────┘  └───────────┬───────────┘ │
│         │                     │             │
│         └──────────┬──────────┘             │
│                    │                        │
│         ┌──────────▼───────────┐            │
│         │   pykms_Metrics.py   │            │
│         │   - Counters         │            │
│         │   - Gauges           │            │
│         │   - Histograms       │            │
│         └──────────────────────┘            │
└─────────────────────────────────────────────┘
```

## Enabling Metrics

Metrics are controlled by the `METRICS` environment variable:

- `METRICS=0` (default): Metrics server disabled
- `METRICS=1`: Metrics server enabled

The metrics server port is controlled by `METRICS_PORT` (default: `9090`).

### Docker Run Example

```bash
docker run -d \
  -e METRICS=1 \
  -e METRICS_PORT=9090 \
  -p 1688:1688 \
  -p 9090:9090 \
  --name py-kms \
  py-kms:metrics
```

### Docker Compose Example

```yaml
version: '3.8'
services:
  py-kms:
    image: py-kms:metrics
    environment:
      - METRICS=1
      - METRICS_PORT=9090
    ports:
      - "1688:1688"  # KMS
      - "9090:9090"  # Metrics
```

## Exposed Metrics

### KMS Server Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|--------|
| `kms_requests_total` | Counter | Total KMS requests received | `type` (bind, activation) |
| `kms_activations_total` | Counter | Total successful activations | `product` (Windows, Office, Unknown) |
| `kms_errors_total` | Counter | Total KMS errors | `type` (error category) |
| `kms_request_duration_seconds` | Histogram | Request latency | - |

### System Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|--------|
| `pykms_uptime_seconds` | Gauge | Seconds since py-kms started | - |
| `pykms_clients_connected` | Gauge | Currently connected clients | - |

## Metrics Endpoint

Once enabled, metrics are available at:

```
http://<host>:9090/metrics
```

Example output:

```
# HELP kms_requests_total Total number of KMS requests received
# TYPE kms_requests_total counter
kms_requests_total{type="bind"} 42.0
kms_requests_total{type="activation"} 38.0
# HELP kms_activations_total Total number of successful KMS activations
# TYPE kms_activations_total counter
kms_activations_total{product="Windows"} 25.0
kms_activations_total{product="Office"} 13.0
# HELP pykms_uptime_seconds Number of seconds since py-kms started
# TYPE pykms_uptime_seconds gauge
pykms_uptime_seconds 3600.5
```

## Implementation Details

### Non-Invasive Design

The metrics implementation follows a non-invasive design:

1. **Optional Import**: The `pykms_Metrics` module is imported with a try/except block. If prometheus-client is not installed, the application continues to work without metrics.

2. **Environment-Controlled**: The metrics server only starts when `METRICS=1` is set.

3. **Separate Server**: Metrics run on a separate HTTP server (port 9090) independent of the Flask WebUI (port 8080) and KMS server (port 1688).

4. **Graceful Degradation**: All metric recording is wrapped in `if metrics_available:` checks. If metrics are unavailable, the application continues normally.

### Files Modified

| File | Changes |
|------|---------|
| `pykms_Metrics.py` | New file - metrics module |
| `pykms_Server.py` | Added optional metrics import and instrumentation |
| `docker/start.py` | Added optional metrics server startup |
| `docker/docker-py3-kms-metrics/Dockerfile` | Updated to install prometheus-client |
| `docker/docker-py3-kms-metrics/requirements.txt` | Added prometheus-client dependency |

### Adding Metrics to New Code

To add metrics to new code paths:

```python
# At module level (with other imports)
try:
    import pykms_Metrics
    metrics_available = True
except ImportError:
    metrics_available = False

# In your code
if metrics_available:
    pykms_Metrics.record_kms_activation('Windows')
    pykms_Metrics.record_kms_error('network')
```

## Prometheus Configuration

Add this to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'py-kms'
    static_configs:
      - targets: ['<py-kms-host>:9090']
    scrape_interval: 15s
```

## Grafana Dashboard

A sample Grafana dashboard JSON is available in the project repository (TODO: add link when created).

## Troubleshooting

### Metrics server not starting

1. Check that `METRICS=1` is set in the environment
2. Verify port 9090 is not in use by another service
3. Check container logs: `docker logs py-kms | grep metrics`

### No metrics showing up

1. Verify the metrics endpoint: `curl http://localhost:9090/metrics`
2. Check that KMS activations are occurring
3. Verify prometheus-client is installed: `pip list | grep prometheus`

### High cardinality warnings

The current implementation uses low-cardinality labels only. If adding new labels, ensure they have a bounded set of possible values to avoid cardinality explosions.
