#!/usr/bin/env python3
"""
MCP Server for GCP Log Collection

Provides tools to collect and analyze GCP logs through the Model Context Protocol.
"""

import json
from datetime import datetime, timezone
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from .gcp_log_collector import LogCollector


# Initialize MCP server
app = Server("gcp-log-collector")


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


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="collect_gcp_logs",
            description="Collect GCP logs for a specific resource and time range. "
                       "Useful for investigating incidents, errors, and analyzing application behavior.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "GCP project ID to query logs from"
                    },
                    "resource_type": {
                        "type": "string",
                        "description": "GCP resource type (e.g., 'cloud_run_revision', 'gce_instance', 'k8s_container')"
                    },
                    "resource_labels": {
                        "type": "object",
                        "description": "Dictionary of resource labels to filter by (e.g., {'service_name': 'my-service', 'location': 'us-central1'})",
                        "additionalProperties": {"type": "string"}
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start timestamp in ISO 8601 format (e.g., '2025-11-17T10:00:00Z')"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End timestamp in ISO 8601 format (e.g., '2025-11-17T11:00:00Z')"
                    },
                    "include_all_severities": {
                        "type": "boolean",
                        "description": "Include all severity levels. If false, only ERROR and above (default: true)",
                        "default": True
                    },
                    "max_entries": {
                        "type": "integer",
                        "description": "Maximum number of log entries to collect (default: 10000)",
                        "default": 10000
                    }
                },
                "required": ["project_id", "resource_type", "resource_labels", "start_time", "end_time"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    if name != "collect_gcp_logs":
        raise ValueError(f"Unknown tool: {name}")

    try:
        # Collect logs
        result = collect_logs(
            project_id=arguments["project_id"],
            resource_type=arguments["resource_type"],
            resource_labels=arguments["resource_labels"],
            start_time=arguments["start_time"],
            end_time=arguments["end_time"],
            include_all_severities=arguments.get("include_all_severities", True),
            max_entries=arguments.get("max_entries", 10000)
        )

        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": str(e),
                "type": type(e).__name__
            }, indent=2)
        )]


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
