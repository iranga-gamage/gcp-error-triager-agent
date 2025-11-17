#!/usr/bin/env python3
"""
Simple test script for GCP Log Collector
Using actual parameters from sample_pubsub_alert.json
"""

from datetime import datetime, timezone, timedelta
from src.gcp_log_collector import LogCollector


def main():
    # Parameters from sample_pubsub_alert.json
    PROJECT_ID = "prj-croud-dev-dst-sandbox"
    RESOURCE_TYPE = "cloud_run_revision"
    RESOURCE_LABELS = {
        "service_name": "error-simulator",
        "location": "us-central1",
        "revision_name": "error-simulator-00002-5gc",
        "configuration_name": "error-simulator"
    }

    # Incident started at 1763211782 (Unix timestamp)
    # Let's look at 1 minute before and 5 minutes after
    incident_time = datetime.fromtimestamp(1763211782, tz=timezone.utc)
    start_time = incident_time - timedelta(minutes=1)
    end_time = incident_time + timedelta(minutes=5)

    print("Testing GCP Log Collector")
    print("=" * 80)
    print(f"Project: {PROJECT_ID}")
    print(f"Resource: {RESOURCE_TYPE}")
    print(f"Labels: {RESOURCE_LABELS}")
    print(f"Time: {start_time.isoformat()} to {end_time.isoformat()}")
    print("=" * 80)

    # Build filter
    print("\n[1] Building filter...")
    filter_str = LogCollector.build_filter_from_params(
        resource_type=RESOURCE_TYPE,
        resource_labels=RESOURCE_LABELS,
        start_time=start_time,
        end_time=end_time,
        include_all_severities=True
    )
    print(f"Filter:\n{filter_str}")

    # Initialize collector
    print("\n[2] Initializing collector...")
    collector = LogCollector(project_id=PROJECT_ID)
    print(f"✓ Connected to project: {PROJECT_ID}")

    # Collect logs
    print("\n[3] Collecting logs...")
    logs = collector.collect_logs(
        filter_str=filter_str,
        max_entries=100  # Get more logs
    )

    print(f"✓ Collected {len(logs)} log entries")

    # Display results
    if logs:
        print("\n[4] ALL log entries:")
        for i, log in enumerate(logs, 1):
            print(f"\n--- Entry {i} ---")
            print(f"Time: {log['timestamp']}")
            print(f"Severity: {log.get('severity', 'None')}")
            print(f"Log name: {log.get('log_name', 'N/A')}")

            # Show payload
            if 'text_payload' in log:
                print(f"Text payload: {log['text_payload'][:200]}")
            elif 'json_payload' in log:
                import json
                print(f"JSON payload: {json.dumps(log['json_payload'], indent=2)[:500]}")
            else:
                print(f"Payload: {log.get('payload', 'N/A')}")

            # Show HTTP request if present
            if 'http_request' in log:
                req = log['http_request']
                print(f"HTTP: {req.get('request_method')} {req.get('request_url')} -> {req.get('status')}")

            # Show full log entry as JSON
            import json
            print(f"\nFull log entry:")
            print(json.dumps(log, indent=2, default=str))
    else:
        print("\n⚠ No logs found. This could mean:")
        print("  - The service hasn't generated logs in this time range")
        print("  - The resource labels don't match any resources")
        print("  - Check your PROJECT_ID, RESOURCE_TYPE, and RESOURCE_LABELS")


if __name__ == "__main__":
    main()
