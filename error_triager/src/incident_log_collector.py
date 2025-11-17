#!/usr/bin/env python3
"""
GCP Incident Log Collector

Collects all logs related to a GCP incident based on PubSub alert payload.
Captures logs with configurable time buffers before and after the incident.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from google.cloud import logging
from google.cloud.logging import DESCENDING


class IncidentLogCollector:
    """Collects logs related to a GCP incident"""

    def __init__(self, project_id: str = None):
        """
        Initialize the log collector

        Args:
            project_id: GCP project ID (optional, can be extracted from incident)
        """
        self.project_id = project_id
        self.client = None
        self.incident_data = None

    def load_incident(self, incident_file: str) -> Dict[str, Any]:
        """
        Load incident data from JSON file

        Args:
            incident_file: Path to incident JSON file

        Returns:
            Incident data dictionary
        """
        with open(incident_file, 'r') as f:
            data = json.load(f)

        self.incident_data = data

        # Extract project_id from incident if not provided
        if not self.project_id:
            if 'incident' in data:
                incident = data['incident']
                if 'scoping_project_id' in incident:
                    self.project_id = incident['scoping_project_id']
                elif 'resource' in incident and 'labels' in incident['resource']:
                    self.project_id = incident['resource']['labels'].get('project_id')

        if not self.project_id:
            raise ValueError("Could not determine project_id from incident data")

        # Initialize client with project_id
        self.client = logging.Client(project=self.project_id)

        return self.incident_data

    def parse_incident_time_range(self,
                                   minutes_before: int = 1,
                                   minutes_after: int = 1) -> tuple[datetime, Optional[datetime]]:
        """
        Parse incident time range with buffers

        Args:
            minutes_before: Minutes to look back before incident start
            minutes_after: Minutes to look ahead after incident end

        Returns:
            Tuple of (start_time, end_time)
        """
        if not self.incident_data or 'incident' not in self.incident_data:
            raise ValueError("No incident data loaded")

        incident = self.incident_data['incident']

        # Parse started_at (Unix timestamp)
        started_at = incident.get('started_at')
        if not started_at:
            raise ValueError("Incident has no started_at timestamp")

        # Convert Unix timestamp to datetime
        incident_start = datetime.fromtimestamp(started_at, tz=timezone.utc)

        # Apply before buffer
        start_time = incident_start - timedelta(minutes=minutes_before)

        # Parse ended_at if available
        ended_at = incident.get('ended_at')
        if ended_at:
            incident_end = datetime.fromtimestamp(ended_at, tz=timezone.utc)
            end_time = incident_end + timedelta(minutes=minutes_after)
        else:
            # Incident still open, use current time + buffer
            end_time = datetime.now(timezone.utc) + timedelta(minutes=minutes_after)

        return start_time, end_time

    def build_log_filter(self,
                         start_time: datetime,
                         end_time: datetime,
                         include_all_severities: bool = True) -> str:
        """
        Build Cloud Logging filter query from incident data

        Args:
            start_time: Start of time range
            end_time: End of time range
            include_all_severities: Include all severity levels (default: True)

        Returns:
            Filter string for Cloud Logging query
        """
        if not self.incident_data or 'incident' not in self.incident_data:
            raise ValueError("No incident data loaded")

        incident = self.incident_data['incident']
        resource = incident.get('resource', {})
        resource_type = resource.get('type')
        resource_labels = resource.get('labels', {})

        if not resource_type:
            raise ValueError("Incident has no resource type")

        # Build filter components
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
                     minutes_before: int = 1,
                     minutes_after: int = 1,
                     max_entries: int = 10000,
                     include_all_severities: bool = True) -> List[Dict[str, Any]]:
        """
        Collect all logs related to the incident

        Args:
            minutes_before: Minutes to look back before incident
            minutes_after: Minutes to look ahead after incident
            max_entries: Maximum number of log entries to retrieve
            include_all_severities: Include all severity levels

        Returns:
            List of log entries as dictionaries
        """
        # Get time range
        start_time, end_time = self.parse_incident_time_range(
            minutes_before=minutes_before,
            minutes_after=minutes_after
        )

        # Build filter
        filter_str = self.build_log_filter(
            start_time=start_time,
            end_time=end_time,
            include_all_severities=include_all_severities
        )

        print(f"[Incident Log Collector]", file=sys.stderr)
        print(f"Incident ID: {self.incident_data['incident'].get('incident_id')}", file=sys.stderr)
        print(f"Project: {self.project_id}", file=sys.stderr)
        print(f"Time range: {start_time.isoformat()} to {end_time.isoformat()}", file=sys.stderr)
        print(f"Duration: {minutes_before}m before -> {minutes_after}m after", file=sys.stderr)
        print(f"\n[Log Filter]", file=sys.stderr)
        print(filter_str, file=sys.stderr)
        print(f"\n[Collecting logs...]", file=sys.stderr)

        # Query logs
        entries = list(self.client.list_entries(
            filter_=filter_str,
            order_by=DESCENDING,
            page_size=max_entries
        ))

        print(f"Collected {len(entries)} log entries", file=sys.stderr)

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

    def save_logs(self,
                  log_entries: List[Dict[str, Any]],
                  output_file: str,
                  include_metadata: bool = True):
        """
        Save collected logs to JSON file

        Args:
            log_entries: List of log entry dictionaries
            output_file: Output file path
            include_metadata: Include incident metadata in output
        """
        output_data = {}

        if include_metadata:
            output_data['incident_metadata'] = {
                'incident_id': self.incident_data['incident'].get('incident_id'),
                'started_at': self.incident_data['incident'].get('started_at'),
                'ended_at': self.incident_data['incident'].get('ended_at'),
                'state': self.incident_data['incident'].get('state'),
                'summary': self.incident_data['incident'].get('summary'),
                'policy_name': self.incident_data['incident'].get('policy_name'),
                'condition_name': self.incident_data['incident'].get('condition_name'),
                'resource': self.incident_data['incident'].get('resource'),
                'metric': self.incident_data['incident'].get('metric'),
                'observed_value': self.incident_data['incident'].get('observed_value'),
                'threshold_value': self.incident_data['incident'].get('threshold_value'),
                'url': self.incident_data['incident'].get('url')
            }

            # Add collection metadata
            output_data['collection_metadata'] = {
                'collected_at': datetime.now(timezone.utc).isoformat(),
                'total_entries': len(log_entries),
                'project_id': self.project_id
            }

        output_data['logs'] = log_entries

        # Write to file
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)

        print(f"\n[Output]", file=sys.stderr)
        print(f"Saved {len(log_entries)} log entries to: {output_file}", file=sys.stderr)

    def get_log_statistics(self, log_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about collected logs

        Args:
            log_entries: List of log entry dictionaries

        Returns:
            Statistics dictionary
        """
        stats = {
            'total_entries': len(log_entries),
            'by_severity': {},
            'by_log_name': {},
            'time_range': {
                'earliest': None,
                'latest': None
            },
            'unique_traces': set(),
            'http_status_codes': {}
        }

        for entry in log_entries:
            # Count by severity
            severity = entry.get('severity', 'UNKNOWN')
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1

            # Count by log name
            log_name = entry.get('log_name', 'unknown')
            # Simplify log name for display
            log_name_short = log_name.split('/')[-1] if '/' in log_name else log_name
            stats['by_log_name'][log_name_short] = stats['by_log_name'].get(log_name_short, 0) + 1

            # Track time range
            timestamp = entry.get('timestamp')
            if timestamp:
                if not stats['time_range']['earliest'] or timestamp < stats['time_range']['earliest']:
                    stats['time_range']['earliest'] = timestamp
                if not stats['time_range']['latest'] or timestamp > stats['time_range']['latest']:
                    stats['time_range']['latest'] = timestamp

            # Track unique traces
            trace = entry.get('trace')
            if trace:
                stats['unique_traces'].add(trace)

            # Track HTTP status codes
            http_request = entry.get('http_request')
            if http_request and http_request.get('status'):
                status = http_request['status']
                stats['http_status_codes'][status] = stats['http_status_codes'].get(status, 0) + 1

        # Convert set to count
        stats['unique_traces'] = len(stats['unique_traces'])

        return stats


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Collect all logs related to a GCP incident',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect logs with default 1-minute buffers
  python incident_log_collector.py --incident incident.json --output logs.json

  # Collect logs with 10 minutes before and 2 minutes after
  python incident_log_collector.py --incident incident.json --output logs.json \\
    --minutes-before 10 --minutes-after 2

  # Collect only ERROR and above severity
  python incident_log_collector.py --incident incident.json --output logs.json \\
    --errors-only

  # Specify project explicitly
  python incident_log_collector.py --incident incident.json --output logs.json \\
    --project my-project-id

  # Collect more entries
  python incident_log_collector.py --incident incident.json --output logs.json \\
    --max-entries 50000

  # Collect with wider time range
  python incident_log_collector.py --incident incident.json --output logs.json \\
    --minutes-before 30 --minutes-after 15
        """
    )

    parser.add_argument('--incident', '-i', required=True,
                       help='Path to incident JSON file (PubSub alert payload)')
    parser.add_argument('--output', '-o', required=True,
                       help='Output JSON file path')
    parser.add_argument('--project', '-p',
                       help='GCP Project ID (optional, will be extracted from incident)')
    parser.add_argument('--minutes-before', '-b', type=int, default=1,
                       help='Minutes to look back before incident start (default: 1)')
    parser.add_argument('--minutes-after', '-a', type=int, default=1,
                       help='Minutes to look ahead after incident end (default: 1)')
    parser.add_argument('--max-entries', '-m', type=int, default=10000,
                       help='Maximum number of log entries to collect (default: 10000)')
    parser.add_argument('--errors-only', '-e', action='store_true',
                       help='Collect only ERROR and above severity (default: all severities)')
    parser.add_argument('--no-metadata', action='store_true',
                       help='Exclude incident metadata from output')
    parser.add_argument('--stats', '-s', action='store_true',
                       help='Print statistics about collected logs')

    args = parser.parse_args()

    try:
        # Initialize collector
        collector = IncidentLogCollector(project_id=args.project)

        # Load incident data
        print(f"[Loading incident data from: {args.incident}]", file=sys.stderr)
        collector.load_incident(args.incident)

        # Collect logs
        log_entries = collector.collect_logs(
            minutes_before=args.minutes_before,
            minutes_after=args.minutes_after,
            max_entries=args.max_entries,
            include_all_severities=not args.errors_only
        )

        if not log_entries:
            print("\nWarning: No log entries found matching the criteria", file=sys.stderr)

        # Print statistics if requested
        if args.stats:
            stats = collector.get_log_statistics(log_entries)
            print(f"\n[Log Statistics]", file=sys.stderr)
            print(f"Total entries: {stats['total_entries']}", file=sys.stderr)
            print(f"Time range: {stats['time_range']['earliest']} to {stats['time_range']['latest']}", file=sys.stderr)
            print(f"Unique traces: {stats['unique_traces']}", file=sys.stderr)
            print(f"\nBy severity:", file=sys.stderr)
            for severity, count in sorted(stats['by_severity'].items(), key=lambda x: (x[0] is None, x[0])):
                print(f"  {severity}: {count}", file=sys.stderr)
            print(f"\nBy log type:", file=sys.stderr)
            for log_name, count in sorted(stats['by_log_name'].items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {log_name}: {count}", file=sys.stderr)
            if stats['http_status_codes']:
                print(f"\nHTTP status codes:", file=sys.stderr)
                for status, count in sorted(stats['http_status_codes'].items()):
                    print(f"  {status}: {count}", file=sys.stderr)

        # Save logs
        collector.save_logs(
            log_entries=log_entries,
            output_file=args.output,
            include_metadata=not args.no_metadata
        )

        return 0

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
