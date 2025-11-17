# Incident Log Collector

Collects all logs related to a GCP incident from Cloud Logging based on PubSub alert payloads.

## Overview

When GCP Cloud Monitoring detects an incident and sends a PubSub alert, this tool:
1. Parses the incident details (resource, time, metrics)
2. Queries Cloud Logging for all related logs
3. Captures logs with configurable time buffers before/after the incident
4. Outputs all logs as a single JSON file for analysis

## Key Features

- **Automatic Resource Filtering**: Extracts resource type and labels from incident
- **Time Window Buffering**: Captures logs before and after incident for context
- **Complete Log Capture**: No summarization - gets all raw log data
- **Metadata Preservation**: Includes incident details in output
- **Flexible Querying**: Configurable time buffers and severity filters
- **Statistics**: Optional log statistics output

## Installation

Already included in the error_trager package:

```bash
cd error_trager
source .venv/bin/activate
```

## Usage

### Basic Usage

```bash
python src/incident_log_collector.py \
  --incident sample_pubsub_alert.json \
  --output incident_logs.json
```

This collects logs with default 5-minute buffers before and after the incident.

### Custom Time Buffers

Capture 10 minutes before and 2 minutes after:

```bash
python src/incident_log_collector.py \
  --incident incident.json \
  --output logs.json \
  --minutes-before 10 \
  --minutes-after 2
```

### Show Statistics

Display log statistics after collection:

```bash
python src/incident_log_collector.py \
  --incident incident.json \
  --output logs.json \
  --stats
```

### Errors Only

Collect only ERROR severity and above:

```bash
python src/incident_log_collector.py \
  --incident incident.json \
  --output logs.json \
  --errors-only
```

### Large Incidents

Increase max entries for high-volume incidents:

```bash
python src/incident_log_collector.py \
  --incident incident.json \
  --output logs.json \
  --max-entries 50000
```

### Specify Project

Explicitly set project ID (normally extracted from incident):

```bash
python src/incident_log_collector.py \
  --incident incident.json \
  --output logs.json \
  --project my-project-id
```

### Minimal Output

Exclude incident metadata from output:

```bash
python src/incident_log_collector.py \
  --incident incident.json \
  --output logs.json \
  --no-metadata
```

## Command-Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--incident` | `-i` | Path to incident JSON file (required) | - |
| `--output` | `-o` | Output JSON file path (required) | - |
| `--project` | `-p` | GCP Project ID (optional) | Extracted from incident |
| `--minutes-before` | `-b` | Minutes to look back before incident | 5 |
| `--minutes-after` | `-a` | Minutes to look ahead after incident | 5 |
| `--max-entries` | `-m` | Maximum log entries to collect | 10000 |
| `--errors-only` | `-e` | Collect only ERROR+ severity | false (all) |
| `--no-metadata` | - | Exclude incident metadata | false |
| `--stats` | `-s` | Print collection statistics | false |

## Input Format

The script expects a GCP Cloud Monitoring incident in PubSub alert format:

```json
{
  "incident": {
    "incident_id": "0.nzkl1309yzci",
    "started_at": 1763211782,
    "ended_at": null,
    "state": "open",
    "resource": {
      "type": "cloud_run_revision",
      "labels": {
        "service_name": "error-simulator",
        "revision_name": "error-simulator-00002-5gc",
        "project_id": "prj-croud-dev-dst-sandbox",
        "location": "us-central1",
        "configuration_name": "error-simulator"
      }
    },
    "policy_name": "Error Alert",
    "condition_name": "Any 5xx error detected",
    "summary": "...",
    "metric": {...}
  },
  "version": "1.2"
}
```

### Required Fields

The incident must contain:
- `incident.started_at` - Incident start time (Unix timestamp)
- `incident.resource.type` - GCP resource type
- `incident.resource.labels` - Resource labels for filtering
- `incident.scoping_project_id` or `incident.resource.labels.project_id` - Project ID

### Optional Fields

- `incident.ended_at` - If null, uses current time + buffer
- `incident.incident_id` - Included in output metadata
- `incident.metric` - Included in output metadata

## Output Format

The output JSON contains three sections:

### 1. Incident Metadata

```json
{
  "incident_metadata": {
    "incident_id": "0.nzkl1309yzci",
    "started_at": 1763211782,
    "ended_at": null,
    "state": "open",
    "summary": "Request Count for...",
    "policy_name": "Error Simulator - Any Error Alert",
    "condition_name": "Any 5xx error detected",
    "resource": {...},
    "metric": {...},
    "observed_value": "10.000",
    "threshold_value": "0",
    "url": "https://console.cloud.google.com/..."
  }
}
```

### 2. Collection Metadata

```json
{
  "collection_metadata": {
    "collected_at": "2025-11-16T18:00:27.862126+00:00",
    "total_entries": 36,
    "project_id": "prj-croud-dev-dst-sandbox"
  }
}
```

### 3. Logs Array

```json
{
  "logs": [
    {
      "timestamp": "2025-11-15T13:38:47.113103+00:00",
      "severity": "ERROR",
      "log_name": "projects/.../logs/run.googleapis.com%2Fstderr",
      "insert_id": "691882670001b9cfbfef00fc",
      "resource": {
        "type": "cloud_run_revision",
        "labels": {...}
      },
      "text_payload": "Error message here",
      "labels": {...},
      "http_request": {
        "request_method": "POST",
        "request_url": "https://...",
        "status": 500,
        "latency": "0.005s",
        ...
      },
      "trace": "projects/.../traces/...",
      "span_id": "..."
    },
    ...
  ]
}
```

Each log entry includes:
- **timestamp**: When the log was created
- **severity**: Log severity level (ERROR, WARNING, INFO, etc.)
- **log_name**: Full log name/path
- **insert_id**: Unique log entry ID
- **resource**: Resource that generated the log
- **payload**: Log message (text_payload or json_payload)
- **labels**: Custom labels
- **http_request**: HTTP request details (if applicable)
- **trace**: Trace ID for distributed tracing
- **span_id**: Span ID within trace
- **source_location**: Source code location (if available)
- **operation**: Operation details (if available)

## Log Query Strategy

The script builds Cloud Logging filters based on incident data:

```
resource.type="cloud_run_revision"
AND resource.labels.service_name="error-simulator"
AND resource.labels.revision_name="error-simulator-00002-5gc"
AND resource.labels.project_id="prj-croud-dev-dst-sandbox"
AND resource.labels.location="us-central1"
AND timestamp >= "{incident_start - minutes_before}"
AND timestamp <= "{incident_end + minutes_after}"
```

### Why Time Buffers Matter

**Before Buffer** (`--minutes-before`):
- Captures pre-incident conditions
- Shows what led to the failure
- Reveals gradual degradation patterns
- Includes startup/initialization logs

**After Buffer** (`--minutes-after`):
- Captures recovery attempts
- Shows cascading failures
- Includes retry logic
- Reveals auto-scaling responses

### Log Types Captured

For Cloud Run incidents, this typically includes:
- `run.googleapis.com/requests` - HTTP request logs
- `run.googleapis.com/stdout` - Application stdout
- `run.googleapis.com/stderr` - Application stderr
- `run.googleapis.com/varlog/system` - System logs
- `monitoring.googleapis.com/*` - Monitoring events

## Statistics Output

When using `--stats`, you'll see:

```
[Log Statistics]
Total entries: 36
Time range: 2025-11-15T13:03:02+00:00 to 2025-11-15T13:38:47+00:00
Unique traces: 18

By severity:
  ERROR: 10
  INFO: 10
  None: 16

By log type:
  run.googleapis.com%2Frequests: 18
  run.googleapis.com%2Fstderr: 10
  monitoring.googleapis.com%2FViolationAutoResolveEventv1: 2
  monitoring.googleapis.com%2FViolationOpenEventv1: 2

HTTP status codes:
  200: 8
  500: 10
```

## Example Workflows

### Workflow 1: Quick Incident Analysis

```bash
# Collect logs with default 5-minute buffers
python src/incident_log_collector.py \
  --incident incident.json \
  --output quick_analysis.json \
  --stats

# View error counts
cat quick_analysis.json | jq '.logs[] | select(.severity=="ERROR") | .text_payload' | wc -l

# Extract unique error messages
cat quick_analysis.json | jq -r '.logs[] | select(.severity=="ERROR") | .text_payload' | sort -u
```

### Workflow 2: Deep Investigation

```bash
# Collect wide time window (30min before, 15min after)
python src/incident_log_collector.py \
  --incident incident.json \
  --output deep_investigation.json \
  --minutes-before 30 \
  --minutes-after 15 \
  --max-entries 50000 \
  --stats

# Extract all traces
cat deep_investigation.json | jq -r '.logs[].trace' | sort -u > traces.txt

# Group errors by type
cat deep_investigation.json | jq -r '.logs[] | select(.severity=="ERROR") | .text_payload' | sort | uniq -c | sort -rn
```

### Workflow 3: HTTP Error Analysis

```bash
# Collect all logs
python src/incident_log_collector.py \
  --incident incident.json \
  --output http_errors.json

# Extract 5xx errors with URLs
cat http_errors.json | jq '.logs[] | select(.http_request.status >= 500) | {url: .http_request.request_url, status: .http_request.status, latency: .http_request.latency}'

# Count errors by endpoint
cat http_errors.json | jq -r '.logs[] | select(.http_request.status >= 500) | .http_request.request_url' | sed 's/?.*$//' | sort | uniq -c | sort -rn
```

### Workflow 4: Automated Processing

```bash
#!/bin/bash
# Process incident automatically

INCIDENT_FILE=$1
OUTPUT_DIR="incident_logs_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$OUTPUT_DIR"

# Collect logs
python src/incident_log_collector.py \
  --incident "$INCIDENT_FILE" \
  --output "$OUTPUT_DIR/all_logs.json" \
  --minutes-before 10 \
  --minutes-after 5 \
  --stats

# Extract errors only
jq '.logs[] | select(.severity=="ERROR")' "$OUTPUT_DIR/all_logs.json" > "$OUTPUT_DIR/errors_only.json"

# Extract traces
jq -r '.logs[].trace' "$OUTPUT_DIR/all_logs.json" | sort -u > "$OUTPUT_DIR/traces.txt"

# Generate summary
echo "Incident Analysis Summary" > "$OUTPUT_DIR/summary.txt"
echo "=========================" >> "$OUTPUT_DIR/summary.txt"
echo "" >> "$OUTPUT_DIR/summary.txt"
jq -r '.incident_metadata.summary' "$OUTPUT_DIR/all_logs.json" >> "$OUTPUT_DIR/summary.txt"
echo "" >> "$OUTPUT_DIR/summary.txt"
echo "Total Logs: $(jq '.collection_metadata.total_entries' "$OUTPUT_DIR/all_logs.json")" >> "$OUTPUT_DIR/summary.txt"
echo "Errors: $(jq '[.logs[] | select(.severity=="ERROR")] | length' "$OUTPUT_DIR/all_logs.json")" >> "$OUTPUT_DIR/summary.txt"

echo "Analysis complete in: $OUTPUT_DIR"
```

## Integration with Cloud Functions

You can deploy this as a Cloud Function that processes incidents automatically:

```python
from google.cloud import storage
from incident_log_collector import IncidentLogCollector
import json

def process_incident(event, context):
    """Cloud Function triggered by PubSub incident alerts"""

    # Parse PubSub message
    import base64
    incident_data = json.loads(base64.b64decode(event['data']).decode('utf-8'))

    # Save to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(incident_data, f)
        incident_file = f.name

    # Collect logs
    collector = IncidentLogCollector()
    collector.load_incident(incident_file)
    logs = collector.collect_logs(minutes_before=10, minutes_after=5)

    # Save to Cloud Storage
    incident_id = incident_data['incident']['incident_id']
    bucket = storage.Client().bucket('incident-logs')
    blob = bucket.blob(f'incidents/{incident_id}/logs.json')

    output_data = {
        'incident_metadata': incident_data['incident'],
        'logs': logs
    }
    blob.upload_from_string(json.dumps(output_data, indent=2, default=str))

    print(f"Collected {len(logs)} logs for incident {incident_id}")
```

## Troubleshooting

### No logs found

**Problem**: Script returns 0 log entries

**Solutions**:
1. Check time window - incident might be outside buffer range
2. Verify resource labels match exactly
3. Increase `--minutes-before` and `--minutes-after`
4. Check if logs were actually generated
5. Verify project ID is correct

### Authentication errors

**Problem**: Permission denied when querying logs

**Solutions**:
```bash
# Re-authenticate
gcloud auth application-default login

# Or set service account
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
```

Required IAM roles:
- `roles/logging.viewer` or `roles/logging.admin`

### Too many logs

**Problem**: Hitting max_entries limit

**Solutions**:
1. Increase `--max-entries` (e.g., 50000)
2. Reduce time window with smaller buffers
3. Use `--errors-only` to filter by severity
4. Run multiple queries with smaller time windows

### Memory issues

**Problem**: Script runs out of memory with large log volumes

**Solutions**:
1. Process logs in smaller time chunks
2. Use `--errors-only` to reduce volume
3. Stream logs to file instead of loading all in memory
4. Run on a machine with more RAM

## Performance Considerations

- **Query time**: Depends on log volume, typically 5-30 seconds
- **Memory usage**: ~100MB per 10,000 log entries
- **Network**: Uses Cloud Logging API, may incur costs
- **Rate limits**: Respects Cloud Logging API quotas

## Best Practices

1. **Start narrow, expand if needed**: Begin with default 5-minute buffers
2. **Use statistics**: Always use `--stats` to understand what you're collecting
3. **Save metadata**: Keep incident metadata for correlation
4. **Archive raw logs**: Store complete logs before analyzing
5. **Track costs**: Monitor Cloud Logging API usage
6. **Automate collection**: Set up Cloud Functions for automatic collection
7. **Regular cleanup**: Archive old incident logs to cheaper storage

## Next Steps

After collecting logs:
1. Use the main `triage.py` tool for error analysis
2. Extract unique error patterns
3. Correlate with traces in Cloud Trace
4. Review HTTP status codes and latencies
5. Check for cascading failures across services

## See Also

- [README.md](README.md) - Main triager documentation
- [QUICKSTART.md](QUICKSTART.md) - Getting started guide
- [example_usage.py](example_usage.py) - Programmatic examples
