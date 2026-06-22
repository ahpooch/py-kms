#!/usr/bin/env python3
"""
Prometheus metrics endpoint for py-kms.
This module provides a standalone Flask app that exposes KMS metrics
without the full WebUI overhead.
"""

import os
import datetime
from flask import Flask, Response
from pykms_Sql import sql_get_all
from pykms_DB2Dict import kmsDB2Dict

def _get_kms_items_cache():
    """Cache KMS items from the database configuration."""
    _kms_items = {}  # {group: str -> {product: str -> gvlk: str}}
    _kms_items_noglvk = 0
    for section in kmsDB2Dict():
        for element in section:
            if "KmsItems" in element:
                for product in element["KmsItems"]:
                    group_name = product["DisplayName"]
                    items = {}
                    for item in product["SkuItems"]:
                        items[item["DisplayName"]] = item["Gvlk"]
                        if not item["Gvlk"]:
                            _kms_items_noglvk += 1
                    if len(items) == 0:
                        continue
                    if group_name not in _kms_items:
                        _kms_items[group_name] = {}
                    _kms_items[group_name].update(items)
    return _kms_items, _kms_items_noglvk

app = Flask('pykms_metrics')
app.jinja_env.globals['start_time'] = datetime.datetime.now()

_dbEnvVarName = 'PYKMS_SQLITE_DB_PATH'

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint in text format."""
    metrics_lines = []

    def add_metric(name, value, labels=None, metric_type='gauge', help_text=None):
        if help_text:
            metrics_lines.append(f'# HELP {name} {help_text}')
        metrics_lines.append(f'# TYPE {name} {metric_type}')
        if labels:
            label_str = ','.join(f'{k}="{v}"' for k, v in labels.items())
            metrics_lines.append(f'{name}{{{label_str}}} {value}')
        else:
            metrics_lines.append(f'{name} {value}')

    # Basic service metrics
    start_time = app.jinja_env.globals['start_time']
    uptime = (datetime.datetime.now() - start_time).total_seconds()

    add_metric('pykms_up', 1, help_text='Service status (1=up, 0=down)')
    add_metric('pykms_start_time_seconds', int(start_time.timestamp()), help_text='Service start time as Unix timestamp')
    add_metric('pykms_uptime_seconds', uptime, help_text='Service uptime in seconds')

    # Get database path and fetch clients
    db_path = os.environ.get(_dbEnvVarName)
    clients = None
    if db_path:
        try:
            clients = sql_get_all(db_path)
        except Exception:
            clients = None

    # Client metrics
    if clients:
        count_total = len(clients)
        count_windows = len([c for c in clients if c.get('applicationId') == 'Windows'])
        count_office = count_total - count_windows

        add_metric('pykms_clients_total', count_total, help_text='Total number of unique clients')
        add_metric('pykms_clients_by_application', count_windows, labels={'application': 'Windows'}, help_text='Number of Windows clients')
        add_metric('pykms_clients_by_application', count_office, labels={'application': 'Office'}, help_text='Number of Office clients')

        # Aggregated activation metrics (no per-client labels to avoid cardinality explosion)
        total_request_count = sum(c.get('requestCount', 0) for c in clients)

        # Count activations by status
        status_counts = {}
        for client in clients:
            status = client.get('licenseStatus', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        # Count activations by application
        app_counts = {}
        for client in clients:
            app = client.get('applicationId', 'unknown')
            app_counts[app] = app_counts.get(app, 0) + 1

        # Count activations by SKU
        sku_counts = {}
        for client in clients:
            sku = client.get('skuId', 'unknown')
            sku_counts[sku] = sku_counts.get(sku, 0) + 1

        # Total activation requests across all clients
        add_metric(
            'pykms_client_request_count_total',
            total_request_count,
            help_text='Total number of activation requests from all clients'
        )

        # Activations by status (aggregated, no client_machine_id)
        for status, count in status_counts.items():
            add_metric(
                'pykms_activations_total',
                count,
                labels={'status': status},
                help_text='Total number of activations by status'
            )

        # Activations by application (aggregated, no client_machine_id)
        for app, count in app_counts.items():
            add_metric(
                'pykms_activations_by_application',
                count,
                labels={'application': app},
                help_text='Total number of activations by application type'
            )

        # Activations by SKU (aggregated, no client_machine_id)
        for sku, count in sku_counts.items():
            add_metric(
                'pykms_activations_by_sku',
                count,
                labels={'sku_id': sku},
                help_text='Total number of activations by SKU'
            )

    # Product metrics
    items, noglvk = _get_kms_items_cache()
    count_products = sum([len(entries) for entries in items.values()])
    count_products_with_gvlk = count_products - noglvk

    add_metric('pykms_products_total', count_products, help_text='Total number of products in KMS database')
    add_metric('pykms_products_with_gvlk_total', count_products_with_gvlk, help_text='Number of products with GVLK keys')

    # Products by category
    for group_name, products in items.items():
        category = group_name.lower().split()[0] if group_name else 'unknown'
        add_metric(
            'pykms_products_by_category',
            len(products),
            labels={'category': category},
            help_text='Number of products by category'
        )

    return Response('\n'.join(metrics_lines) + '\n', mimetype='text/plain')

@app.route('/livez')
def livez():
    """Liveness probe endpoint."""
    return 'OK', 200

@app.route('/readyz')
def readyz():
    """Readiness probe endpoint."""
    if (datetime.datetime.now() - app.jinja_env.globals['start_time']).seconds > 10:
        return 'OK', 200
    else:
        return 'Not ready', 503
