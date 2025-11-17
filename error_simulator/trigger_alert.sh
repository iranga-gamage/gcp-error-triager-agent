#!/bin/bash
# Script to trigger Cloud Monitoring alert

SERVICE_URL="https://error-simulator-zvfvbwinca-uc.a.run.app"

echo "🚀 Triggering multiple errors to activate alert policy..."
echo ""

# Get auth token once
TOKEN=$(gcloud auth print-identity-token)

# Send 10 errors in rapid succession
for i in {1..10}; do
  echo "[$i/10] Sending error request..."
  curl -s -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    "${SERVICE_URL}/api/v1/analytics?error_type=TIMEOUT&create_incident=true" \
    > /dev/null &
done

wait

echo ""
echo "✅ Sent 10 error requests"
echo ""
echo "⏱️  Wait 2-3 minutes, then check:"
echo ""
echo "1. Cloud Monitoring Incidents:"
echo "   https://console.cloud.google.com/monitoring/alerting/incidents?project=prj-croud-dev-dst-sandbox"
echo ""
echo "2. Your email: iranga.gamage@croud.com"
echo ""
echo "3. Cloud Run logs:"
echo "   gcloud run services logs read error-simulator --region=us-central1 --limit=20"
echo ""
