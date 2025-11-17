# Pub/Sub Alert Notifications

The error simulator now sends alert notifications to both **email** and **Pub/Sub** when errors are detected. This allows you to build automated triaging and incident response systems.

## Configuration

**Pub/Sub Topic**: `error-simulator-alerts`
**Project**: `prj-croud-dev-dst-sandbox`
**Region**: Global (Pub/Sub topics are global by default)

## Alert Message Format

When an alert fires, Cloud Monitoring sends a JSON message to the Pub/Sub topic with this structure:

```json
{
  "incident": {
    "incident_id": "...",
    "resource_id": "...",
    "resource_name": "error-simulator",
    "resource": {
      "type": "cloud_run_revision",
      "labels": {
        "service_name": "error-simulator",
        "revision_name": "...",
        "location": "us-central1"
      }
    },
    "policy_name": "Error Simulator - Any Error Alert",
    "condition_name": "Any 5xx error detected",
    "state": "open",
    "started_at": 1234567890,
    "ended_at": null,
    "summary": "...",
    "documentation": {
      "content": "...",
      "mime_type": "text/markdown"
    },
    "metric": {
      "type": "run.googleapis.com/request_count",
      "displayName": "Request count",
      "labels": {
        "response_code_class": "5xx"
      }
    },
    "condition": {
      "displayName": "Any 5xx error detected",
      "conditionThreshold": {
        "filter": "...",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 0,
        "duration": "0s"
      }
    },
    "url": "https://console.cloud.google.com/monitoring/alerting/incidents/..."
  }
}
```

## Using the Subscriber Script

### Install Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate

# Install google-cloud-pubsub
uv pip install google-cloud-pubsub>=2.24.0
```

### Option 1: Stream Mode (Continuous Listening)

This mode listens continuously for incoming alerts:

```bash
# Listen forever (until Ctrl+C)
python3 subscribe_alerts.py --mode stream

# Listen for 60 seconds then stop
python3 subscribe_alerts.py --mode stream --timeout 60
```

**Output**:
```
================================================================================
🚨 ALERT RECEIVED
================================================================================

📋 Incident Details:
   • Incident ID: 0.lzf0c8ep97zo
   • Policy Name: Error Simulator - Any Error Alert
   • State: open
   • Started: 1700000000
   • Resource: cloud_run_revision

⚠️  Condition:
   • Name: Any 5xx error detected

📊 Metric:
   • Type: run.googleapis.com/request_count
   • Value: 5

📦 Full Alert Data:
{
  "incident": { ... }
}

================================================================================
✓ Message acknowledged
```

### Option 2: Pull Mode (Batch Processing)

This mode pulls messages once and exits (useful for scheduled jobs):

```bash
# Pull up to 10 messages
python3 subscribe_alerts.py --mode pull

# Pull up to 5 messages
python3 subscribe_alerts.py --mode pull --max-messages 5
```

## Testing Pub/Sub Alerts

### 1. Trigger Errors

Use the trigger script to generate errors:

```bash
./trigger_alert.sh
```

### 2. Subscribe to Alerts

In a separate terminal, run the subscriber:

```bash
cd /Users/iranga.gamage/src/test_projects/gcp_error_triager/error_simulator
source .venv/bin/activate
python3 subscribe_alerts.py --mode stream
```

### 3. Wait for Alerts

After 1-2 minutes, you should see alert messages in both:
- Your email (iranga.gamage@croud.com)
- The subscriber terminal

## Using Pub/Sub in Your Triaging Application

### Example: Basic Message Consumer

```python
from google.cloud import pubsub_v1
import json

PROJECT_ID = "prj-croud-dev-dst-sandbox"
SUBSCRIPTION_NAME = "error-simulator-alerts-sub"

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_NAME)

def callback(message):
    alert_data = json.loads(message.data.decode("utf-8"))
    incident = alert_data["incident"]

    # Extract key information
    incident_id = incident["incident_id"]
    policy_name = incident["policy_name"]
    state = incident["state"]

    print(f"Processing incident {incident_id}: {policy_name} ({state})")

    # TODO: Add your triaging logic here
    # - Analyze error patterns
    # - Create tickets
    # - Send notifications
    # - Update dashboards

    message.ack()

# Start listening
streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
streaming_pull_future.result()
```

### Example: Integration with Cloud Functions

You can deploy a Cloud Function triggered by Pub/Sub to automatically process alerts:

```python
import functions_framework
from google.cloud import logging
import json

@functions_framework.cloud_event
def process_alert(cloud_event):
    """Triggered by Pub/Sub message on error-simulator-alerts topic."""

    # Decode the Pub/Sub message
    pubsub_message = cloud_event.data["message"]
    alert_data = json.loads(base64.b64decode(pubsub_message["data"]).decode())

    incident = alert_data["incident"]

    # Log to Cloud Logging
    logging_client = logging.Client()
    logger = logging_client.logger("alert-processor")
    logger.log_struct({
        "severity": "ERROR",
        "message": f"Processing alert: {incident['policy_name']}",
        "incident_id": incident["incident_id"],
        "state": incident["state"]
    })

    # TODO: Add your triaging logic
    # - Create Jira ticket
    # - Send Slack notification
    # - Trigger runbook automation
    # - Update incident dashboard

    return {"status": "processed"}
```

Deploy the function:

```bash
gcloud functions deploy process-error-alerts \
  --gen2 \
  --runtime=python313 \
  --region=us-central1 \
  --source=. \
  --entry-point=process_alert \
  --trigger-topic=error-simulator-alerts
```

## Managing Subscriptions

### List Subscriptions

```bash
gcloud pubsub subscriptions list --filter="topic:error-simulator-alerts"
```

### Create Additional Subscription

```bash
gcloud pubsub subscriptions create my-custom-subscription \
  --topic=error-simulator-alerts \
  --ack-deadline=60
```

### Delete Subscription

```bash
gcloud pubsub subscriptions delete error-simulator-alerts-sub
```

## Viewing Messages in Console

You can also view Pub/Sub messages in the GCP Console:

1. Navigate to: https://console.cloud.google.com/cloudpubsub/topic/list?project=prj-croud-dev-dst-sandbox
2. Click on `error-simulator-alerts`
3. Click "MESSAGES" tab
4. Click "PULL" to manually retrieve messages

## IAM Permissions

The subscriber needs these permissions:
- `pubsub.subscriptions.consume`
- `pubsub.subscriptions.get`

To grant access to a service account:

```bash
gcloud pubsub subscriptions add-iam-policy-binding error-simulator-alerts-sub \
  --member="serviceAccount:your-sa@project.iam.gserviceaccount.com" \
  --role="roles/pubsub.subscriber"
```

## Monitoring Subscription Health

### View Subscription Metrics

```bash
gcloud pubsub subscriptions describe error-simulator-alerts-sub
```

### Check Unacknowledged Messages

```bash
gcloud pubsub subscriptions describe error-simulator-alerts-sub \
  --format="value(numUndeliveredMessages)"
```

### View Subscription in Monitoring

https://console.cloud.google.com/monitoring/metrics-explorer?project=prj-croud-dev-dst-sandbox&pageState=%7B%22xyChart%22:%7B%22dataSets%22:%5B%7B%22timeSeriesFilter%22:%7B%22filter%22:%22resource.type%3D%5C%22pubsub_subscription%5C%22%22%7D%7D%5D%7D%7D

## Troubleshooting

### No Messages Received

1. **Check if alerts are firing**:
   ```bash
   # Check Cloud Monitoring incidents
   gcloud monitoring incidents list --project=prj-croud-dev-dst-sandbox
   ```

2. **Verify subscription exists**:
   ```bash
   gcloud pubsub subscriptions describe error-simulator-alerts-sub
   ```

3. **Check for undelivered messages**:
   ```bash
   gcloud pubsub subscriptions describe error-simulator-alerts-sub \
     --format="value(numUndeliveredMessages)"
   ```

### Permission Denied

Make sure you're authenticated:
```bash
gcloud auth application-default login
```

### Messages Not Being Acknowledged

Check the ack deadline is sufficient:
```bash
gcloud pubsub subscriptions update error-simulator-alerts-sub \
  --ack-deadline=60
```

## Next Steps

1. ✅ Test the subscription with `subscribe_alerts.py`
2. ✅ Trigger some errors with `trigger_alert.sh`
3. ✅ Build your triaging application logic
4. ✅ Consider deploying a Cloud Function for automated processing
5. ✅ Set up monitoring for your subscription metrics
6. ✅ Implement incident response workflows

## Related Links

- [Pub/Sub Topic](https://console.cloud.google.com/cloudpubsub/topic/detail/error-simulator-alerts?project=prj-croud-dev-dst-sandbox)
- [Monitoring Incidents](https://console.cloud.google.com/monitoring/alerting/incidents?project=prj-croud-dev-dst-sandbox)
- [Alert Policy](https://console.cloud.google.com/monitoring/alerting/policies?project=prj-croud-dev-dst-sandbox)
- [Cloud Run Service](https://console.cloud.google.com/run/detail/us-central1/error-simulator?project=prj-croud-dev-dst-sandbox)
