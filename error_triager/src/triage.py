#!/usr/bin/env python3
"""
GCP Error Triager - Query and analyze GCP logs for incident triage
"""

import argparse
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any
from dateutil import parser as date_parser

from google.cloud import logging
from google.cloud.logging import DESCENDING
from tabulate import tabulate


class LogQueryBuilder:
    """Build Cloud Logging filter queries"""

    def __init__(self):
        self.filters = []

    def add_severity(self, severity: str = "ERROR"):
        """Add severity filter (ERROR, WARNING, CRITICAL, etc.)"""
        self.filters.append(f'severity >= {severity}')
        return self

    def add_resource_type(self, resource_type: str):
        """Add resource type filter (cloud_run_revision, gce_instance, etc.)"""
        self.filters.append(f'resource.type="{resource_type}"')
        return self

    def add_time_range(self, hours: int = None, start_time: str = None, end_time: str = None):
        """Add time range filter"""
        if hours:
            start = datetime.utcnow() - timedelta(hours=hours)
            self.filters.append(f'timestamp >= "{start.isoformat()}Z"')
        elif start_time:
            self.filters.append(f'timestamp >= "{start_time}"')
            if end_time:
                self.filters.append(f'timestamp <= "{end_time}"')
        return self

    def add_text_search(self, text: str):
        """Add text search in log payload"""
        self.filters.append(f'"{text}"')
        return self

    def add_custom_filter(self, filter_str: str):
        """Add custom filter string"""
        self.filters.append(filter_str)
        return self

    def build(self) -> str:
        """Build final filter string"""
        return '\n'.join(self.filters)


class ErrorAnalyzer:
    """Analyze and group errors from log entries"""

    def __init__(self):
        self.errors_by_type = defaultdict(list)
        self.errors_by_message = defaultdict(list)
        self.timeline = []

    def analyze_entry(self, entry):
        """Analyze a single log entry"""
        error_info = {
            'timestamp': entry.timestamp,
            'severity': entry.severity,
            'resource': self._get_resource_info(entry.resource),
            'message': self._extract_message(entry),
            'labels': dict(entry.labels) if entry.labels else {},
            'trace': entry.trace if hasattr(entry, 'trace') else None,
            'insert_id': entry.insert_id,
        }

        # Group by error type/pattern
        error_type = self._classify_error(error_info['message'])
        self.errors_by_type[error_type].append(error_info)

        # Group by similar messages
        message_key = self._normalize_message(error_info['message'])
        self.errors_by_message[message_key].append(error_info)

        self.timeline.append(error_info)

    def _get_resource_info(self, resource) -> Dict[str, str]:
        """Extract resource information"""
        return {
            'type': resource.type,
            'labels': dict(resource.labels) if resource.labels else {}
        }

    def _extract_message(self, entry) -> str:
        """Extract error message from entry"""
        if hasattr(entry, 'payload') and entry.payload:
            if isinstance(entry.payload, str):
                return entry.payload
            elif isinstance(entry.payload, dict):
                # Try common error message fields
                for key in ['message', 'error', 'msg', 'text']:
                    if key in entry.payload:
                        return str(entry.payload[key])
                return str(entry.payload)
        return str(entry)

    def _classify_error(self, message: str) -> str:
        """Classify error type based on message patterns"""
        message_lower = message.lower()

        if 'file not found' in message_lower or 'no such file' in message_lower:
            return 'FILE_NOT_FOUND'
        elif 'division by zero' in message_lower or 'divide by zero' in message_lower:
            return 'CALCULATION_ERROR'
        elif 'timeout' in message_lower or 'timed out' in message_lower:
            return 'TIMEOUT'
        elif 'memory' in message_lower or 'out of memory' in message_lower:
            return 'MEMORY_ERROR'
        elif 'connection' in message_lower or 'network' in message_lower:
            return 'NETWORK_ERROR'
        elif 'permission' in message_lower or 'forbidden' in message_lower:
            return 'PERMISSION_ERROR'
        elif 'validation' in message_lower or 'invalid' in message_lower:
            return 'VALIDATION_ERROR'
        elif 'exception' in message_lower or 'error' in message_lower:
            return 'EXCEPTION'
        else:
            return 'UNKNOWN'

    def _normalize_message(self, message: str) -> str:
        """Normalize error message for grouping (remove IDs, timestamps, etc.)"""
        import re
        # Remove UUIDs
        normalized = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<UUID>', message, flags=re.IGNORECASE)
        # Remove numbers that might be IDs
        normalized = re.sub(r'\b\d{5,}\b', '<ID>', normalized)
        # Remove timestamps
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}', '<TIMESTAMP>', normalized)
        # Remove file paths
        normalized = re.sub(r'(/[\w/]+/[\w.]+|\w:\\[\w\\]+)', '<PATH>', normalized)
        return normalized[:200]  # Truncate for grouping

    def get_summary(self) -> Dict[str, Any]:
        """Get analysis summary"""
        return {
            'total_errors': len(self.timeline),
            'error_types': dict(self.errors_by_type),
            'grouped_errors': dict(self.errors_by_message),
            'timeline': sorted(self.timeline, key=lambda x: x['timestamp'], reverse=True)
        }


class GCPErrorTriager:
    """Main triager class for querying and analyzing GCP logs"""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = logging.Client(project=project_id)
        self.analyzer = ErrorAnalyzer()

    def query_logs(self,
                   severity: str = "ERROR",
                   hours: int = 24,
                   resource_type: str = None,
                   text_search: str = None,
                   custom_filter: str = None,
                   limit: int = 100) -> List[Any]:
        """
        Query GCP logs with filters

        Args:
            severity: Minimum severity level (ERROR, WARNING, CRITICAL)
            hours: Number of hours to look back
            resource_type: GCP resource type to filter (e.g., cloud_run_revision)
            text_search: Text to search in logs
            custom_filter: Custom filter string
            limit: Maximum number of entries to return

        Returns:
            List of log entries
        """
        # Build filter query
        query_builder = LogQueryBuilder()
        query_builder.add_severity(severity)
        query_builder.add_time_range(hours=hours)

        if resource_type:
            query_builder.add_resource_type(resource_type)

        if text_search:
            query_builder.add_text_search(text_search)

        if custom_filter:
            query_builder.add_custom_filter(custom_filter)

        filter_str = query_builder.build()

        print(f"\n[Query Filter]")
        print(filter_str)
        print(f"\n[Fetching logs...]")

        # Query logs
        entries = list(self.client.list_entries(
            filter_=filter_str,
            order_by=DESCENDING,
            page_size=limit
        ))

        print(f"Found {len(entries)} log entries\n")

        return entries

    def analyze_logs(self, entries: List[Any]):
        """Analyze log entries"""
        for entry in entries:
            self.analyzer.analyze_entry(entry)

    def print_summary(self):
        """Print analysis summary"""
        summary = self.analyzer.get_summary()

        print("=" * 80)
        print("ERROR TRIAGE SUMMARY")
        print("=" * 80)
        print(f"\nTotal Errors: {summary['total_errors']}\n")

        # Error types breakdown
        print("Error Types Breakdown:")
        print("-" * 80)
        type_data = [
            [error_type, count]
            for error_type, errors in summary['error_types'].items()
            for count in [len(errors)]
        ]
        type_data.sort(key=lambda x: x[1], reverse=True)
        print(tabulate(type_data, headers=['Error Type', 'Count'], tablefmt='grid'))

        # Grouped errors (similar messages)
        print("\n\nTop Error Groups (Similar Errors):")
        print("-" * 80)
        grouped_data = [
            [msg_key[:60] + '...' if len(msg_key) > 60 else msg_key, len(errors)]
            for msg_key, errors in sorted(summary['grouped_errors'].items(),
                                          key=lambda x: len(x[1]),
                                          reverse=True)[:10]
        ]
        print(tabulate(grouped_data, headers=['Message Pattern', 'Occurrences'], tablefmt='grid'))

        # Recent errors timeline
        print("\n\nRecent Errors Timeline:")
        print("-" * 80)
        timeline_data = [
            [
                error['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                error['severity'],
                error['resource']['type'],
                error['message'][:60] + '...' if len(error['message']) > 60 else error['message']
            ]
            for error in summary['timeline'][:20]
        ]
        print(tabulate(timeline_data,
                      headers=['Timestamp', 'Severity', 'Resource', 'Message'],
                      tablefmt='grid'))

    def print_detailed_errors(self, error_type: str = None, limit: int = 5):
        """Print detailed error information"""
        summary = self.analyzer.get_summary()

        print("\n\n" + "=" * 80)
        print("DETAILED ERROR ANALYSIS")
        print("=" * 80)

        if error_type:
            errors = summary['error_types'].get(error_type, [])
            print(f"\nShowing {min(len(errors), limit)} errors of type: {error_type}")
        else:
            errors = summary['timeline']
            print(f"\nShowing {min(len(errors), limit)} most recent errors")

        for i, error in enumerate(errors[:limit], 1):
            print(f"\n{'='*80}")
            print(f"Error #{i}")
            print(f"{'='*80}")
            print(f"Timestamp:    {error['timestamp']}")
            print(f"Severity:     {error['severity']}")
            print(f"Resource:     {error['resource']['type']}")
            print(f"Service:      {error['resource']['labels'].get('service_name', 'N/A')}")
            print(f"Revision:     {error['resource']['labels'].get('revision_name', 'N/A')}")
            print(f"Insert ID:    {error['insert_id']}")
            if error['trace']:
                print(f"Trace:        {error['trace']}")
            print(f"\nMessage:")
            print("-" * 80)
            print(error['message'])
            print("-" * 80)

            if error['labels']:
                print(f"\nLabels:")
                for key, value in error['labels'].items():
                    print(f"  {key}: {value}")

    def suggest_next_steps(self):
        """Suggest next steps for triage"""
        summary = self.analyzer.get_summary()

        print("\n\n" + "=" * 80)
        print("SUGGESTED NEXT STEPS")
        print("=" * 80)

        # Analyze patterns and suggest actions
        error_types = summary['error_types']

        suggestions = []

        if 'FILE_NOT_FOUND' in error_types:
            suggestions.append({
                'priority': 'HIGH',
                'issue': 'File Not Found Errors',
                'action': 'Check if data files are missing or paths are incorrect. Verify deployment includes all necessary files.',
                'count': len(error_types['FILE_NOT_FOUND'])
            })

        if 'CALCULATION_ERROR' in error_types:
            suggestions.append({
                'priority': 'HIGH',
                'issue': 'Calculation Errors (Division by Zero)',
                'action': 'Review data validation logic. Check for empty datasets or zero values in calculations.',
                'count': len(error_types['CALCULATION_ERROR'])
            })

        if 'TIMEOUT' in error_types:
            suggestions.append({
                'priority': 'MEDIUM',
                'issue': 'Timeout Errors',
                'action': 'Investigate slow queries or external service calls. Consider increasing timeout limits or optimizing performance.',
                'count': len(error_types['TIMEOUT'])
            })

        if 'MEMORY_ERROR' in error_types:
            suggestions.append({
                'priority': 'CRITICAL',
                'issue': 'Memory Errors',
                'action': 'Check memory limits and usage. Consider increasing Cloud Run memory allocation or optimizing data processing.',
                'count': len(error_types['MEMORY_ERROR'])
            })

        if 'NETWORK_ERROR' in error_types or 'EXTERNAL_SERVICE' in error_types:
            suggestions.append({
                'priority': 'HIGH',
                'issue': 'Network/External Service Errors',
                'action': 'Check external service status and network connectivity. Implement retry logic and circuit breakers.',
                'count': len(error_types.get('NETWORK_ERROR', [])) + len(error_types.get('EXTERNAL_SERVICE', []))
            })

        if 'VALIDATION_ERROR' in error_types:
            suggestions.append({
                'priority': 'MEDIUM',
                'issue': 'Data Validation Errors',
                'action': 'Review input validation logic. Check API request parameters and data format requirements.',
                'count': len(error_types['VALIDATION_ERROR'])
            })

        # Sort by priority
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        suggestions.sort(key=lambda x: priority_order[x['priority']])

        if suggestions:
            table_data = [
                [s['priority'], s['issue'], s['count'], s['action']]
                for s in suggestions
            ]
            print(tabulate(table_data,
                          headers=['Priority', 'Issue', 'Count', 'Recommended Action'],
                          tablefmt='grid'))
        else:
            print("\nNo specific patterns detected. Review detailed errors above for more context.")

        print("\n\nGeneral Triage Steps:")
        print("1. Review the most frequent error groups above")
        print("2. Check Cloud Run logs for full stack traces")
        print("3. Verify recent deployments or configuration changes")
        print("4. Check external dependencies and third-party services")
        print("5. Review monitoring dashboards for resource usage patterns")
        print("6. Consider setting up alerts for error rate thresholds")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='GCP Error Triager - Query and analyze GCP logs for incident triage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query last 24 hours of errors
  gcp-triage --project my-project

  # Query specific time range
  gcp-triage --project my-project --hours 48

  # Filter by resource type (Cloud Run)
  gcp-triage --project my-project --resource-type cloud_run_revision

  # Search for specific text
  gcp-triage --project my-project --search "division by zero"

  # Show detailed errors
  gcp-triage --project my-project --detailed --limit 10

  # Query with custom filter
  gcp-triage --project my-project --filter 'labels.error_type="CALCULATION_ERROR"'
        """
    )

    parser.add_argument('--project', '-p', required=True,
                       help='GCP Project ID')
    parser.add_argument('--severity', '-s', default='ERROR',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Minimum severity level (default: ERROR)')
    parser.add_argument('--hours', type=int, default=24,
                       help='Number of hours to look back (default: 24)')
    parser.add_argument('--resource-type', '-r',
                       help='Filter by resource type (e.g., cloud_run_revision)')
    parser.add_argument('--search', '-t',
                       help='Search for text in logs')
    parser.add_argument('--filter', '-f',
                       help='Custom filter string')
    parser.add_argument('--limit', '-l', type=int, default=100,
                       help='Maximum number of log entries (default: 100)')
    parser.add_argument('--detailed', '-d', action='store_true',
                       help='Show detailed error information')
    parser.add_argument('--error-type', '-e',
                       help='Filter detailed view by error type')

    args = parser.parse_args()

    try:
        # Initialize triager
        triager = GCPErrorTriager(project_id=args.project)

        # Query logs
        entries = triager.query_logs(
            severity=args.severity,
            hours=args.hours,
            resource_type=args.resource_type,
            text_search=args.search,
            custom_filter=args.filter,
            limit=args.limit
        )

        if not entries:
            print("No log entries found matching the criteria.")
            return 0

        # Analyze logs
        triager.analyze_logs(entries)

        # Print summary
        triager.print_summary()

        # Print detailed errors if requested
        if args.detailed:
            triager.print_detailed_errors(
                error_type=args.error_type,
                limit=args.limit if args.limit < 100 else 10
            )

        # Suggest next steps
        triager.suggest_next_steps()

        return 0

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
