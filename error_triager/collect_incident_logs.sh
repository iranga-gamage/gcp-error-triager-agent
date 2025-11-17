#!/bin/bash
#
# Helper script to collect incident logs
# Usage: ./collect_incident_logs.sh <incident.json> [output.json]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <incident.json> [output.json]"
    echo ""
    echo "Examples:"
    echo "  $0 incident.json"
    echo "  $0 incident.json custom_output.json"
    echo "  MINUTES_BEFORE=10 MINUTES_AFTER=5 $0 incident.json"
    exit 1
fi

INCIDENT_FILE="$1"
OUTPUT_FILE="${2:-incident_logs_$(date +%Y%m%d_%H%M%S).json}"

# Configuration via environment variables
MINUTES_BEFORE="${MINUTES_BEFORE:-1}"
MINUTES_AFTER="${MINUTES_AFTER:-1}"
MAX_ENTRIES="${MAX_ENTRIES:-10000}"
SHOW_STATS="${SHOW_STATS:-true}"

# Check if incident file exists
if [ ! -f "$INCIDENT_FILE" ]; then
    echo "Error: Incident file not found: $INCIDENT_FILE"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "$SCRIPT_DIR/.venv" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Build command
CMD="python $SCRIPT_DIR/src/incident_log_collector.py"
CMD="$CMD --incident $INCIDENT_FILE"
CMD="$CMD --output $OUTPUT_FILE"
CMD="$CMD --minutes-before $MINUTES_BEFORE"
CMD="$CMD --minutes-after $MINUTES_AFTER"
CMD="$CMD --max-entries $MAX_ENTRIES"

if [ "$SHOW_STATS" = "true" ]; then
    CMD="$CMD --stats"
fi

# Run collection
echo "Collecting incident logs..."
echo "Incident: $INCIDENT_FILE"
echo "Output: $OUTPUT_FILE"
echo "Time window: -${MINUTES_BEFORE}m to +${MINUTES_AFTER}m"
echo ""

$CMD

# Print success message
if [ -f "$OUTPUT_FILE" ]; then
    echo ""
    echo "✓ Success! Logs saved to: $OUTPUT_FILE"
    echo ""
    echo "Quick analysis commands:"
    echo "  # View incident summary"
    echo "  jq '.incident_metadata.summary' $OUTPUT_FILE"
    echo ""
    echo "  # Count logs by severity"
    echo "  jq -r '.logs[].severity' $OUTPUT_FILE | sort | uniq -c"
    echo ""
    echo "  # Extract error messages"
    echo "  jq -r '.logs[] | select(.severity==\"ERROR\") | .text_payload // .json_payload' $OUTPUT_FILE"
    echo ""
    echo "  # Extract unique traces"
    echo "  jq -r '.logs[].trace' $OUTPUT_FILE | grep -v null | sort -u"
fi
