#!/usr/bin/env python3
"""
Subscribe to and process alert notifications from Pub/Sub.
This script demonstrates how to consume alert messages for your triaging application.
"""

import json
import sys
from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1

# Configuration
PROJECT_ID = "prj-croud-dev-dst-sandbox"
TOPIC_NAME = "error-simulator-alerts"
SUBSCRIPTION_NAME = "error-simulator-alerts-sub"


def create_subscription_if_not_exists():
    """Create a subscription to the alerts topic if it doesn't exist."""
    subscriber = pubsub_v1.SubscriberClient()
    topic_path = subscriber.topic_path(PROJECT_ID, TOPIC_NAME)
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_NAME)

    try:
        # Try to get the subscription
        subscriber.get_subscription(subscription=subscription_path)
        print(f"✓ Using existing subscription: {SUBSCRIPTION_NAME}")
    except Exception:
        # Create subscription if it doesn't exist
        try:
            subscription = subscriber.create_subscription(
                request={
                    "name": subscription_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": 60,
                }
            )
            print(f"✓ Created subscription: {subscription.name}")
        except Exception as e:
            print(f"❌ Error creating subscription: {e}")
            sys.exit(1)

    return subscription_path


def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    """Process incoming alert messages."""
    print("\n" + "="*80)
    print("🚨 ALERT RECEIVED")
    print("="*80)

    # Parse the message data
    try:
        alert_data = json.loads(message.data.decode("utf-8"))

        # Display alert information
        incident = alert_data.get("incident", {})
        print(f"\n📋 Incident Details:")
        print(f"   • Incident ID: {incident.get('incident_id', 'N/A')}")
        print(f"   • Policy Name: {incident.get('policy_name', 'N/A')}")
        print(f"   • State: {incident.get('state', 'N/A')}")
        print(f"   • Started: {incident.get('started_at', 'N/A')}")
        print(f"   • Resource: {incident.get('resource', {}).get('type', 'N/A')}")

        # Display condition information
        condition = incident.get("condition", {})
        if condition:
            print(f"\n⚠️  Condition:")
            print(f"   • Name: {condition.get('displayName', 'N/A')}")

        # Display metric information
        metric = incident.get("metric", {})
        if metric:
            print(f"\n📊 Metric:")
            print(f"   • Type: {metric.get('type', 'N/A')}")
            print(f"   • Value: {metric.get('value', 'N/A')}")

        # Display full alert data
        print(f"\n📦 Full Alert Data:")
        print(json.dumps(alert_data, indent=2))

    except json.JSONDecodeError:
        print(f"\n📦 Raw Message Data:")
        print(message.data.decode("utf-8"))

    # Display message attributes
    if message.attributes:
        print(f"\n🏷️  Message Attributes:")
        for key, value in message.attributes.items():
            print(f"   • {key}: {value}")

    print("\n" + "="*80)

    # Acknowledge the message
    message.ack()
    print("✓ Message acknowledged")


def listen_for_alerts(timeout: float = None) -> None:
    """
    Listen for alert messages from Pub/Sub.

    Args:
        timeout: How long to listen in seconds. None = listen forever
    """
    subscription_path = create_subscription_if_not_exists()
    subscriber = pubsub_v1.SubscriberClient()

    print(f"\n👂 Listening for alerts on: {subscription_path}")
    print(f"   Press Ctrl+C to stop\n")

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

    try:
        # Block and wait for messages
        streaming_pull_future.result(timeout=timeout)
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped by user")
        streaming_pull_future.cancel()
    except TimeoutError:
        print(f"\n\n⏱️  Timeout after {timeout} seconds")
        streaming_pull_future.cancel()
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        streaming_pull_future.cancel()


def pull_messages_once(max_messages: int = 10) -> None:
    """
    Pull messages once (synchronous pull) instead of streaming.
    Useful for batch processing or testing.

    Args:
        max_messages: Maximum number of messages to pull
    """
    subscription_path = create_subscription_if_not_exists()
    subscriber = pubsub_v1.SubscriberClient()

    print(f"\n📥 Pulling up to {max_messages} messages from: {subscription_path}\n")

    # Pull messages
    response = subscriber.pull(
        subscription=subscription_path,
        max_messages=max_messages,
        timeout=10.0
    )

    if not response.received_messages:
        print("📭 No messages available")
        return

    print(f"📬 Received {len(response.received_messages)} message(s)\n")

    # Process messages
    ack_ids = []
    for received_message in response.received_messages:
        message = received_message.message
        callback(message)
        ack_ids.append(received_message.ack_id)

    # Acknowledge all messages
    if ack_ids:
        subscriber.acknowledge(subscription=subscription_path, ack_ids=ack_ids)
        print(f"\n✓ Acknowledged {len(ack_ids)} message(s)")


def main():
    """Main function with CLI options."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Subscribe to error simulator alerts from Pub/Sub"
    )
    parser.add_argument(
        "--mode",
        choices=["stream", "pull"],
        default="stream",
        help="Stream (continuous) or pull (once) mode (default: stream)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Timeout in seconds for streaming mode (default: no timeout)"
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=10,
        help="Maximum messages to pull in pull mode (default: 10)"
    )

    args = parser.parse_args()

    print("\n" + "="*80)
    print("GCP ERROR SIMULATOR - ALERT SUBSCRIBER".center(80))
    print("="*80)
    print(f"\nProject: {PROJECT_ID}")
    print(f"Topic: {TOPIC_NAME}")
    print(f"Subscription: {SUBSCRIPTION_NAME}")
    print(f"Mode: {args.mode}")

    if args.mode == "stream":
        listen_for_alerts(timeout=args.timeout)
    else:
        pull_messages_once(max_messages=args.max_messages)


if __name__ == "__main__":
    main()
