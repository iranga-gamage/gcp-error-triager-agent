# GCP Error Triager

A comprehensive Python toolset for GCP incident triage and error analysis.

## Tools

### 1. **Error Triager** (`triage.py`)
Query and analyze GCP logs with automatic error classification and recommendations.

### 2. **Incident Log Collector** (`incident_log_collector.py`)
Collect all logs related to a GCP incident from PubSub alerts.

## Features

### Error Triager
- Query GCP Cloud Logging with flexible filters
- Automatic error classification and grouping
- Timeline analysis of errors
- Pattern detection in error messages
- Actionable next steps and recommendations
- Support for Cloud Run, GCE, GKE, and other GCP services

### Incident Log Collector
- Extract all logs related to a specific incident
- Configurable time buffers (before/after incident)
- Complete log capture without summarization
- JSON output with incident metadata
- Statistics and analysis

## Prerequisites

- Python 3.13
- `uv` package manager
- GCP Project with Cloud Logging enabled
- GCP credentials configured (gcloud auth or service account)

## Installation

1. **Install uv** (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Install dependencies**:
```bash
uv pip install -e .
```

## Authentication

The tool uses Google Cloud authentication. Set up credentials using one of these methods:

### Option 1: Application Default Credentials (Recommended for local development)
```bash
gcloud auth application-default login
```

### Option 2: Service Account
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### Option 3: Workload Identity (for GKE/Cloud Run)
Automatically configured when running in GCP environments.

## Usage

### Basic Usage

Query errors from the last 24 hours:
```bash
gcp-triage --project YOUR_PROJECT_ID
```

### Query Last 48 Hours
```bash
gcp-triage --project YOUR_PROJECT_ID --hours 48
```

### Filter by Resource Type

Query Cloud Run errors:
```bash
gcp-triage --project YOUR_PROJECT_ID --resource-type cloud_run_revision
```

Query GCE instance errors:
```bash
gcp-triage --project YOUR_PROJECT_ID --resource-type gce_instance
```

Query GKE errors:
```bash
gcp-triage --project YOUR_PROJECT_ID --resource-type k8s_container
```

### Search for Specific Text
```bash
gcp-triage --project YOUR_PROJECT_ID --search "division by zero"
```

### Change Severity Level
```bash
# Include warnings and above
gcp-triage --project YOUR_PROJECT_ID --severity WARNING

# Only critical errors
gcp-triage --project YOUR_PROJECT_ID --severity CRITICAL
```

### Detailed Error View

Show detailed information for errors:
```bash
gcp-triage --project YOUR_PROJECT_ID --detailed

# Show only specific error type
gcp-triage --project YOUR_PROJECT_ID --detailed --error-type CALCULATION_ERROR

# Increase number of detailed errors shown
gcp-triage --project YOUR_PROJECT_ID --detailed --limit 20
```

### Custom Filters

Use custom Cloud Logging filter syntax:
```bash
# Filter by label
gcp-triage --project YOUR_PROJECT_ID --filter 'labels.error_type="CALCULATION_ERROR"'

# Multiple conditions
gcp-triage --project YOUR_PROJECT_ID --filter 'resource.labels.service_name="error-simulator"'
```

### Increase Log Limit
```bash
# Fetch up to 500 log entries
gcp-triage --project YOUR_PROJECT_ID --limit 500
```

## Example Scenarios

### Scenario 1: Investigating a Recent Incident

You notice errors spiking in the last 2 hours:
```bash
gcp-triage --project my-prod-project --hours 2 --detailed
```

### Scenario 2: Cloud Run Service Errors

Your Cloud Run service is failing:
```bash
gcp-triage --project my-prod-project \
  --resource-type cloud_run_revision \
  --hours 6 \
  --detailed
```

### Scenario 3: Finding Specific Error Pattern

Looking for database connection errors:
```bash
gcp-triage --project my-prod-project \
  --search "connection refused" \
  --hours 12
```

### Scenario 4: Weekly Error Review

Review all errors from the past week:
```bash
gcp-triage --project my-prod-project \
  --hours 168 \
  --severity ERROR \
  --limit 500
```

## Output

The tool provides three main sections:

### 1. Error Triage Summary
- Total error count
- Breakdown by error type (FILE_NOT_FOUND, CALCULATION_ERROR, etc.)
- Top error groups by similar messages
- Recent errors timeline

### 2. Detailed Error Analysis (with --detailed flag)
- Full error messages
- Resource information
- Timestamps
- Trace IDs
- Labels and metadata

### 3. Suggested Next Steps
- Prioritized action items based on error patterns
- Specific recommendations for each error type
- General triage workflow

## Error Classification

The tool automatically classifies errors into types:

| Error Type | Description |
|------------|-------------|
| `FILE_NOT_FOUND` | Missing files or resources |
| `CALCULATION_ERROR` | Math errors (division by zero, overflow) |
| `TIMEOUT` | Operation timeout errors |
| `MEMORY_ERROR` | Out of memory errors |
| `NETWORK_ERROR` | Network connectivity issues |
| `PERMISSION_ERROR` | Access denied errors |
| `VALIDATION_ERROR` | Input validation failures |
| `EXCEPTION` | General exceptions |
| `UNKNOWN` | Unclassified errors |

## Incident Log Collector

When GCP Cloud Monitoring creates an incident (via PubSub alert), use the Incident Log Collector to capture all related logs.

### Quick Start

```bash
# Using the helper script (recommended)
./collect_incident_logs.sh incident.json output.json

# Or directly with Python
python src/incident_log_collector.py \
  --incident sample_pubsub_alert.json \
  --output incident_logs.json
```

### Key Features

- **Automatic Filtering**: Extracts resource labels from incident and queries matching logs
- **Time Buffers**: Captures logs before/after incident for context (default: ±5 minutes)
- **Complete Capture**: No summarization - gets all raw log data
- **Incident Metadata**: Includes full incident details in output
- **Statistics**: Shows log breakdown by severity, type, HTTP status

### Common Use Cases

**Collect logs with default 5-minute buffers:**
```bash
python src/incident_log_collector.py \
  --incident incident.json \
  --output logs.json \
  --stats
```

**Wide time window for deep investigation:**
```bash
python src/incident_log_collector.py \
  --incident incident.json \
  --output logs.json \
  --minutes-before 30 \
  --minutes-after 15
```

**Errors only (reduce volume):**
```bash
python src/incident_log_collector.py \
  --incident incident.json \
  --output logs.json \
  --errors-only
```

**Large incidents:**
```bash
python src/incident_log_collector.py \
  --incident incident.json \
  --output logs.json \
  --max-entries 50000
```

### Output Format

The output JSON contains:
1. **Incident Metadata**: incident_id, started_at, resource, metric, etc.
2. **Collection Metadata**: collected_at, total_entries, project_id
3. **Logs Array**: All log entries with complete details

### Environment Variable Configuration

Use with the helper script:
```bash
# Customize time windows
MINUTES_BEFORE=10 MINUTES_AFTER=5 ./collect_incident_logs.sh incident.json

# Increase max entries
MAX_ENTRIES=50000 ./collect_incident_logs.sh incident.json
```

### Quick Analysis Commands

After collecting logs:
```bash
# View incident summary
jq '.incident_metadata.summary' logs.json

# Count by severity
jq -r '.logs[].severity' logs.json | sort | uniq -c

# Extract error messages
jq -r '.logs[] | select(.severity=="ERROR") | .text_payload // .json_payload' logs.json

# Get unique traces
jq -r '.logs[].trace' logs.json | grep -v null | sort -u
```

### See Also

For complete documentation, examples, and integration guides, see:
- **[INCIDENT_LOG_COLLECTOR.md](INCIDENT_LOG_COLLECTOR.md)** - Complete documentation

## Advanced Usage

### Programmatic Usage

You can also use the tool as a library:

```python
from src.triage import GCPErrorTriager

# Initialize
triager = GCPErrorTriager(project_id='my-project')

# Query logs
entries = triager.query_logs(
    severity='ERROR',
    hours=24,
    resource_type='cloud_run_revision',
    limit=100
)

# Analyze
triager.analyze_logs(entries)

# Get summary
summary = triager.analyzer.get_summary()
print(f"Total errors: {summary['total_errors']}")

# Print reports
triager.print_summary()
triager.print_detailed_errors(limit=5)
triager.suggest_next_steps()
```

### Custom Analysis

Extend the `ErrorAnalyzer` class for custom error classification:

```python
from src.triage import ErrorAnalyzer

class CustomAnalyzer(ErrorAnalyzer):
    def _classify_error(self, message: str) -> str:
        # Add your custom classification logic
        if 'payment failed' in message.lower():
            return 'PAYMENT_ERROR'
        return super()._classify_error(message)
```

## Integration with Error Simulator

This tool works perfectly with the Error Simulator in the `error_simulator/` directory:

1. Deploy the error simulator to Cloud Run
2. Generate test errors
3. Use this tool to triage the errors

```bash
# Generate an error
curl -X POST "https://your-service.run.app/api/v1/analytics?error_type=CALCULATION_ERROR"

# Analyze it
gcp-triage --project YOUR_PROJECT_ID --hours 1 --detailed
```

## Troubleshooting

### Authentication Errors

If you see authentication errors:
```bash
# Re-authenticate
gcloud auth application-default login

# Verify credentials
gcloud auth application-default print-access-token
```

### No Logs Found

If no logs are found:
- Verify the project ID is correct
- Check the time range (increase `--hours`)
- Verify logs exist in Cloud Logging console
- Check resource type filter is correct

### Permission Errors

Ensure your account/service account has these IAM roles:
- `roles/logging.viewer` or `roles/logging.admin`
- `roles/errorreporting.user` (for Error Reporting integration)

## Development

### Running Tests
```bash
# TODO: Add tests
uv pip install pytest
pytest tests/
```

### Code Structure
```
error_trager/
├── src/
│   ├── __init__.py
│   └── triage.py          # Main triager implementation
├── pyproject.toml          # Project dependencies
├── .python-version         # Python version
└── README.md               # This file
```

## Future Enhancements

- [ ] Export results to JSON/CSV
- [ ] Integration with Error Reporting API
- [ ] Slack/email notifications
- [ ] Dashboard visualization
- [ ] Automatic incident creation
- [ ] Machine learning-based error prediction
- [ ] Integration with Cloud Monitoring alerts

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License
