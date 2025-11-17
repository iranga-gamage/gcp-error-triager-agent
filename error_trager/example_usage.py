#!/usr/bin/env python3
"""
Example usage of GCP Error Triager as a library
"""

from src.triage import GCPErrorTriager, LogQueryBuilder

# Replace with your project ID
PROJECT_ID = "your-project-id"


def example_basic_query():
    """Basic error query example"""
    print("=" * 80)
    print("Example 1: Basic Error Query")
    print("=" * 80)

    triager = GCPErrorTriager(project_id=PROJECT_ID)

    # Query errors from last 24 hours
    entries = triager.query_logs(
        severity='ERROR',
        hours=24,
        limit=100
    )

    if entries:
        triager.analyze_logs(entries)
        triager.print_summary()


def example_cloud_run_errors():
    """Query Cloud Run specific errors"""
    print("\n" + "=" * 80)
    print("Example 2: Cloud Run Service Errors")
    print("=" * 80)

    triager = GCPErrorTriager(project_id=PROJECT_ID)

    # Query Cloud Run errors
    entries = triager.query_logs(
        severity='ERROR',
        hours=6,
        resource_type='cloud_run_revision',
        limit=50
    )

    if entries:
        triager.analyze_logs(entries)
        triager.print_summary()
        triager.print_detailed_errors(limit=3)


def example_search_pattern():
    """Search for specific error pattern"""
    print("\n" + "=" * 80)
    print("Example 3: Search for Specific Error Pattern")
    print("=" * 80)

    triager = GCPErrorTriager(project_id=PROJECT_ID)

    # Search for calculation errors
    entries = triager.query_logs(
        severity='ERROR',
        hours=12,
        text_search='division by zero',
        limit=50
    )

    if entries:
        triager.analyze_logs(entries)
        triager.print_detailed_errors(error_type='CALCULATION_ERROR', limit=5)


def example_custom_filter():
    """Use custom filter query"""
    print("\n" + "=" * 80)
    print("Example 4: Custom Filter Query")
    print("=" * 80)

    triager = GCPErrorTriager(project_id=PROJECT_ID)

    # Custom filter for specific service
    entries = triager.query_logs(
        severity='ERROR',
        hours=24,
        custom_filter='resource.labels.service_name="error-simulator"',
        limit=100
    )

    if entries:
        triager.analyze_logs(entries)
        triager.print_summary()
        triager.suggest_next_steps()


def example_programmatic_analysis():
    """Programmatic error analysis"""
    print("\n" + "=" * 80)
    print("Example 5: Programmatic Analysis")
    print("=" * 80)

    triager = GCPErrorTriager(project_id=PROJECT_ID)

    entries = triager.query_logs(
        severity='ERROR',
        hours=24,
        limit=100
    )

    if entries:
        triager.analyze_logs(entries)

        # Get summary data
        summary = triager.analyzer.get_summary()

        print(f"\nTotal errors found: {summary['total_errors']}")
        print(f"\nError type breakdown:")
        for error_type, errors in summary['error_types'].items():
            print(f"  {error_type}: {len(errors)} occurrences")

        # Find most common error
        if summary['grouped_errors']:
            most_common = max(summary['grouped_errors'].items(), key=lambda x: len(x[1]))
            print(f"\nMost common error pattern:")
            print(f"  Message: {most_common[0]}")
            print(f"  Occurrences: {len(most_common[1])}")

        # Check for critical issues
        critical_types = ['MEMORY_ERROR', 'CALCULATION_ERROR', 'FILE_NOT_FOUND']
        critical_found = [t for t in critical_types if t in summary['error_types']]

        if critical_found:
            print(f"\n⚠️  Critical error types detected: {', '.join(critical_found)}")
            print("   Immediate investigation recommended!")


def example_query_builder():
    """Build complex queries with LogQueryBuilder"""
    print("\n" + "=" * 80)
    print("Example 6: Advanced Query Building")
    print("=" * 80)

    # Build a complex query
    query = LogQueryBuilder()
    query.add_severity('ERROR')
    query.add_time_range(hours=12)
    query.add_resource_type('cloud_run_revision')
    query.add_custom_filter('labels.error_type:*')

    filter_str = query.build()
    print("Generated filter query:")
    print(filter_str)

    # Use with client
    from google.cloud import logging
    from google.cloud.logging import DESCENDING

    client = logging.Client(project=PROJECT_ID)
    entries = list(client.list_entries(
        filter_=filter_str,
        order_by=DESCENDING,
        page_size=50
    ))

    print(f"\nFound {len(entries)} log entries")


def example_incident_timeline():
    """Create an incident timeline"""
    print("\n" + "=" * 80)
    print("Example 7: Incident Timeline")
    print("=" * 80)

    triager = GCPErrorTriager(project_id=PROJECT_ID)

    # Query a specific time window when incident occurred
    entries = triager.query_logs(
        severity='WARNING',  # Include warnings to see escalation
        hours=2,
        limit=200
    )

    if entries:
        triager.analyze_logs(entries)

        summary = triager.analyzer.get_summary()
        timeline = summary['timeline']

        print(f"\nIncident Timeline ({len(timeline)} events):")
        print("-" * 80)

        for event in timeline[:20]:  # Show first 20 events
            print(f"{event['timestamp'].strftime('%H:%M:%S')} | "
                  f"{event['severity']:8s} | "
                  f"{event['message'][:60]}")


def main():
    """Run all examples"""
    print("\nGCP Error Triager - Example Usage\n")
    print("Replace PROJECT_ID at the top of this file with your GCP project ID\n")

    try:
        # Uncomment the examples you want to run:

        # example_basic_query()
        # example_cloud_run_errors()
        # example_search_pattern()
        # example_custom_filter()
        # example_programmatic_analysis()
        # example_query_builder()
        # example_incident_timeline()

        print("\n✓ Example script ready!")
        print("  Uncomment the examples you want to run in the main() function")

    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("1. You've set PROJECT_ID to your GCP project")
        print("2. You're authenticated: gcloud auth application-default login")
        print("3. Your account has logging.viewer permissions")


if __name__ == '__main__':
    main()
