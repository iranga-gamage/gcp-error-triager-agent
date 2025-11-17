#!/usr/bin/env python3
"""
Simple test client for the GCP Log Collector MCP Server
"""
import asyncio
from fastmcp import Client


async def test_mcp_server():
    """Test the MCP server by listing tools and calling one"""

    server_url = "http://localhost:8080/mcp"

    print(f"Connecting to MCP server at {server_url}...")

    # Connect using FastMCP Client
    async with Client(server_url) as client:
        print("✓ Connected to MCP server")

        # List available tools
        tools = await client.list_tools()
        print(f"\n✓ Available tools: {len(tools)}")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")

        # Example: Call collect_gcp_logs tool
        print("\n--- Example Tool Call ---")
        print("To call the tool, use:")
        print("""
result = await client.call_tool(
    "collect_gcp_logs",
    project_id="your-project-id",
    resource_type="cloud_run_revision",
    resource_labels={
        "service_name": "my-service",
        "location": "us-central1"
    },
    start_time="2025-11-17T10:00:00Z",
    end_time="2025-11-17T11:00:00Z",
    include_all_severities=True,
    max_entries=100
)
print(result)
""")


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
