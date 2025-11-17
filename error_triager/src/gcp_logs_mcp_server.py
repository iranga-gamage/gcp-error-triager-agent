#!/usr/bin/env python3
"""
MCP Server for GCP Log Collection

Provides tools to collect and analyze GCP logs through the Model Context Protocol.
Deployable on Cloud Run with HTTP transport.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# Handle imports for both module and script execution
try:
    from .gcp_log_collector import LogCollector
except ImportError:
    # Add parent directory to path for script execution
    sys.path.insert(0, str(Path(__file__).parent))
    from gcp_log_collector import LogCollector

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

# Initialize FastMCP server
mcp = FastMCP("gcp-log-collector")


def collect_logs(
    project_id: str,
    resource_type: str,
    resource_labels: dict[str, str],
    start_time: str,
    end_time: str,
    include_all_severities: bool = True,
    max_entries: int = 10000
) -> dict[str, Any]:
    """
    Collect logs from GCP based on resource and time range

    Args:
        project_id: GCP project ID
        resource_type: GCP resource type
        resource_labels: Resource labels to filter by
        start_time: Start timestamp (ISO 8601)
        end_time: End timestamp (ISO 8601)
        include_all_severities: Include all severity levels
        max_entries: Maximum number of log entries

    Returns:
        Dictionary with logs and metadata
    """
    # Initialize collector
    collector = LogCollector(project_id=project_id)

    # Parse timestamps
    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))

    # Build filter using library
    filter_str = LogCollector.build_filter_from_params(
        resource_type=resource_type,
        resource_labels=resource_labels,
        start_time=start_dt,
        end_time=end_dt,
        include_all_severities=include_all_severities
    )

    # Collect logs using library
    log_entries = collector.collect_logs(
        filter_str=filter_str,
        max_entries=max_entries
    )

    # Build response
    return {
        'collection_metadata': {
            'collected_at': datetime.now(timezone.utc).isoformat(),
            'total_entries': len(log_entries),
            'project_id': project_id,
            'time_range': {
                'start': start_time,
                'end': end_time
            },
            'filter_used': filter_str
        },
        'logs': log_entries
    }


@mcp.tool()
def collect_gcp_logs(
    project_id: str,
    resource_type: str,
    resource_labels: dict[str, str],
    start_time: str,
    end_time: str,
    include_all_severities: bool = True,
    max_entries: int = 10000
) -> dict[str, Any]:
    """
    Collect GCP logs for a specific resource and time range.
    Useful for investigating incidents, errors, and analyzing application behavior.

    Args:
        project_id: GCP project ID to query logs from
        resource_type: GCP resource type (e.g., 'cloud_run_revision', 'gce_instance', 'k8s_container')
        resource_labels: Dictionary of resource labels to filter by (e.g., {'service_name': 'my-service', 'location': 'us-central1'})
        start_time: Start timestamp in ISO 8601 format (e.g., '2025-11-17T10:00:00Z')
        end_time: End timestamp in ISO 8601 format (e.g., '2025-11-17T11:00:00Z')
        include_all_severities: Include all severity levels. If false, only ERROR and above (default: true)
        max_entries: Maximum number of log entries to collect (default: 10000)

    Returns:
        Dictionary with logs and metadata
    """
    logger.info(f">>> 🛠️ Tool: 'collect_gcp_logs' called for project '{project_id}'")

    try:
        # Collect logs using the original function
        result = collect_logs(
            project_id=project_id,
            resource_type=resource_type,
            resource_labels=resource_labels,
            start_time=start_time,
            end_time=end_time,
            include_all_severities=include_all_severities,
            max_entries=max_entries
        )
        return result
    except Exception as e:
        logger.error(f"Error collecting logs: {e}")
        return {
            "error": str(e),
            "type": type(e).__name__
        }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"🚀 GCP Log Collector MCP server started on port {port}")
    asyncio.run(
        mcp.run_async(
            transport="http",
            host="0.0.0.0",
            port=port,
        )
    )
