#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus metrics module for py-kms.

This module provides a standalone Prometheus metrics server that can be
optionally enabled alongside the KMS server and WebUI. It exposes metrics
about KMS activations, requests, errors, and system status.

Metrics are exposed on a separate HTTP server (default port 9090) at /metrics.
"""

import logging
import os
import threading
import time
from prometheus_client import start_http_server, Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.registry import CollectorRegistry

logger = logging.getLogger('metrics')

# Metric definitions
# These are registered with the default Prometheus registry

# KMS Server Metrics
kms_requests_total = Counter(
    'kms_requests_total',
    'Total number of KMS requests received',
    ['type']  # 'bind' or 'activation'
)

kms_activations_total = Counter(
    'kms_activations_total',
    'Total number of successful KMS activations',
    ['product']  # 'Windows', 'Office', or 'Unknown'
)

kms_errors_total = Counter(
    'kms_errors_total',
    'Total number of KMS errors',
    ['type']  # Error category
)

kms_request_duration_seconds = Histogram(
    'kms_request_duration_seconds',
    'Time spent handling KMS requests',
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# System Metrics
pykms_uptime_seconds = Gauge(
    'pykms_uptime_seconds',
    'Number of seconds since py-kms started'
)

pykms_clients_connected = Gauge(
    'pykms_clients_connected',
    'Number of currently connected KMS clients'
)

# Internal state
_metrics_server_started = False
_metrics_port = 9090
_start_time = None
_active_connections = 0
_connections_lock = threading.Lock()


def _update_uptime():
    """Background task to update uptime gauge."""
    while True:
        if _start_time:
            pykms_uptime_seconds.set(time.time() - _start_time)
        time.sleep(1)


def _increment_connections():
    """Increment the active connections gauge."""
    global _active_connections
    with _connections_lock:
        _active_connections += 1
        pykms_clients_connected.set(_active_connections)


def _decrement_connections():
    """Decrement the active connections gauge."""
    global _active_connections
    with _connections_lock:
        _active_connections = max(0, _active_connections - 1)
        pykms_clients_connected.set(_active_connections)


def start_metrics_server(port=None):
    """
    Start the Prometheus metrics HTTP server.
    
    Args:
        port: Port number for metrics endpoint (default: 9090 from env or default)
    
    Returns:
        True if server started successfully, False otherwise
    """
    global _metrics_server_started, _metrics_port, _start_time
    
    if _metrics_server_started:
        logger.warning('Metrics server already running')
        return True
    
    # Get port from environment or use default
    if port is None:
        port = int(os.environ.get('METRICS_PORT', '9090'))
    
    _metrics_port = port
    
    try:
        # Start Prometheus HTTP server
        start_http_server(port=_metrics_port)
        _metrics_server_started = True
        _start_time = time.time()
        
        # Start uptime tracking thread
        uptime_thread = threading.Thread(target=_update_uptime, daemon=True)
        uptime_thread.start()
        
        logger.info(f'Prometheus metrics server started on port {_metrics_port}')
        logger.info(f'Metrics available at http://0.0.0.0:{_metrics_port}/metrics')
        return True
        
    except Exception as e:
        logger.error(f'Failed to start metrics server: {e}')
        return False


def stop_metrics_server():
    """Stop the metrics server (note: prometheus_client doesn't support clean shutdown)."""
    global _metrics_server_started
    logger.warning('Metrics server shutdown requested (note: prometheus_client does not support clean shutdown)')
    _metrics_server_started = False


def is_metrics_enabled():
    """Check if metrics are enabled via environment variable."""
    return os.environ.get('METRICS', '0') == '1'


# KMS-specific metric helpers
def record_kms_bind():
    """Record a KMS RPC bind request."""
    kms_requests_total.labels(type='bind').inc()


def record_kms_activation(product='Unknown'):
    """Record a successful KMS activation."""
    # Normalize product type
    if product:
        product_lower = product.lower()
        if 'windows' in product_lower:
            product = 'Windows'
        elif 'office' in product_lower:
            product = 'Office'
        else:
            product = 'Unknown'
    else:
        product = 'Unknown'
    
    kms_activations_total.labels(product=product).inc()


def record_kms_error(error_type='unknown'):
    """Record a KMS error."""
    kms_errors_total.labels(type=error_type).inc()


def record_request_duration(duration_seconds):
    """Record the duration of a KMS request."""
    kms_request_duration_seconds.observe(duration_seconds)


def connection_opened():
    """Call when a new client connection is established."""
    _increment_connections()


def connection_closed():
    """Call when a client connection is closed."""
    _decrement_connections()


# Context manager for tracking request duration
class RequestTimer:
    """Context manager to automatically time KMS requests."""
    
    def __init__(self):
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            record_request_duration(duration)
        return False


# Flask middleware for WebUI metrics (optional, for future use)
class PrometheusMiddleware:
    """
    Flask middleware to track WebUI requests.
    
    Usage:
        app = Flask(__name__)
        app.wsgi_app = PrometheusMiddleware(app.wsgi_app)
    """
    
    def __init__(self, app):
        self.app = app
        self.webui_requests_total = Counter(
            'webui_requests_total',
            'Total number of WebUI HTTP requests',
            ['method', 'endpoint', 'status']
        )
        self.webui_request_duration = Histogram(
            'webui_request_duration_seconds',
            'Time spent handling WebUI requests',
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
        )
    
    def __call__(self, environ, start_response):
        start_time = time.time()
        
        def custom_start_response(status, headers, exc_info=None):
            # Extract status code
            status_code = status.split()[0] if status else 'unknown'
            duration = time.time() - start_time
            
            # Record metrics
            method = environ.get('REQUEST_METHOD', 'UNKNOWN')
            endpoint = environ.get('PATH_INFO', '/')
            self.webui_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status_code
            ).inc()
            self.webui_request_duration.observe(duration)
            
            return start_response(status, headers, exc_info)
        
        return self.app(environ, custom_start_response)
