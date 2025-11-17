#!/usr/bin/env python3
"""
GCP Log Collector

Library for collecting GCP Cloud Logging entries based on resource and time filters.
"""

from datetime import datetime
from typing import Dict, Any, List

from google.cloud import logging
from google.cloud.logging import DESCENDING


class LogCollector:
    """Collects logs from GCP Cloud Logging"""

    def __init__(self, project_id: str):
        """
        Initialize the log collector

        Args:
            project_id: GCP project ID
        """
        self.project_id = project_id
        self.client = logging.Client(project=self.project_id)

    @staticmethod
    def build_filter_from_params(resource_type: str,
                                  resource_labels: Dict[str, str],
                                  start_time: datetime,
                                  end_time: datetime,
                                  include_all_severities: bool = True) -> str:
        """
        Build Cloud Logging filter query from direct parameters

        Args:
            resource_type: GCP resource type
            resource_labels: Dictionary of resource labels
            start_time: Start of time range
            end_time: End of time range
            include_all_severities: Include all severity levels (default: True)

        Returns:
            Filter string for Cloud Logging query
        """
        filters = []

        # Resource type filter
        filters.append(f'resource.type="{resource_type}"')

        # Resource labels filters
        for label_key, label_value in resource_labels.items():
            filters.append(f'resource.labels.{label_key}="{label_value}"')

        # Time range filters
        filters.append(f'timestamp>="{start_time.isoformat()}"')
        filters.append(f'timestamp<="{end_time.isoformat()}"')

        # Optionally filter by severity
        if not include_all_severities:
            filters.append('severity>=ERROR')

        return '\n'.join(filters)

    def collect_logs(self,
                     filter_str: str,
                     max_entries: int = 10000) -> List[Dict[str, Any]]:
        """
        Collect logs using a filter string

        Args:
            filter_str: Cloud Logging filter string
            max_entries: Maximum number of log entries to retrieve

        Returns:
            List of log entries as dictionaries
        """
        # Query logs
        entries = list(self.client.list_entries(
            filter_=filter_str,
            order_by=DESCENDING,
            page_size=max_entries
        ))

        # Convert entries to dictionaries
        log_entries = []
        for entry in entries:
            log_dict = self._entry_to_dict(entry)
            log_entries.append(log_dict)

        return log_entries

    def _entry_to_dict(self, entry) -> Dict[str, Any]:
        """
        Convert a log entry to a dictionary

        Args:
            entry: Cloud Logging entry object

        Returns:
            Dictionary representation of the log entry
        """
        log_dict = {
            'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
            'severity': entry.severity,
            'log_name': entry.log_name,
            'insert_id': entry.insert_id,
            'resource': {
                'type': entry.resource.type,
                'labels': dict(entry.resource.labels) if entry.resource.labels else {}
            }
        }

        # Add payload based on type
        if hasattr(entry, 'payload') and entry.payload:
            if isinstance(entry.payload, str):
                log_dict['text_payload'] = entry.payload
            elif isinstance(entry.payload, dict):
                log_dict['json_payload'] = entry.payload
            else:
                log_dict['payload'] = str(entry.payload)

        # Add labels if present
        if entry.labels:
            log_dict['labels'] = dict(entry.labels)

        # Add HTTP request if present
        if hasattr(entry, 'http_request') and entry.http_request:
            http_req = entry.http_request
            log_dict['http_request'] = {
                'request_method': http_req.get('requestMethod'),
                'request_url': http_req.get('requestUrl'),
                'request_size': http_req.get('requestSize'),
                'status': http_req.get('status'),
                'response_size': http_req.get('responseSize'),
                'user_agent': http_req.get('userAgent'),
                'remote_ip': http_req.get('remoteIp'),
                'server_ip': http_req.get('serverIp'),
                'latency': http_req.get('latency'),
                'protocol': http_req.get('protocol')
            }

        # Add trace if present
        if hasattr(entry, 'trace') and entry.trace:
            log_dict['trace'] = entry.trace

        # Add span_id if present
        if hasattr(entry, 'span_id') and entry.span_id:
            log_dict['span_id'] = entry.span_id

        # Add source location if present
        if hasattr(entry, 'source_location') and entry.source_location:
            log_dict['source_location'] = {
                'file': entry.source_location.get('file'),
                'line': entry.source_location.get('line'),
                'function': entry.source_location.get('function')
            }

        # Add operation if present
        if hasattr(entry, 'operation') and entry.operation:
            log_dict['operation'] = {
                'id': entry.operation.get('id'),
                'producer': entry.operation.get('producer'),
                'first': entry.operation.get('first'),
                'last': entry.operation.get('last')
            }

        return log_dict
