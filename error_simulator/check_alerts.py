#!/usr/bin/env python3
"""
Quick script to pull and display alert messages from Pub/Sub.
"""

import json
import time
import sys
from google.cloud import pubsub_v1

PROJECT_ID = "prj-croud-dev-dst-sandbox"
SUBSCRIPTION_NAME = "error-simulator-alerts-sub"

def pull_messages():
    """Pull messages from Pub/Sub subscription."""
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_NAME)

    print(f"Pulling messages from: {subscription_path}\n")

    # Pull messages
    try:
        response = subscriber.pull(
            request={
                "subscription": subscription_path,
                "max_messages": 10,
            },
            timeout=10.0
        )
    except Exception as e:
        print(f"Error pulling messages: {e}")
        return False

    if not response.received_messages:
        print("📭 No messages available yet")
        return False

    print(f"📬 Received {len(response.received_messages)} message(s)\n")
    print("="*80)

    # Process messages
    ack_ids = []
    for i, received_message in enumerate(response.received_messages, 1):
        message = received_message.message

        print(f"\n🚨 ALERT MESSAGE #{i}")
        print("="*80)

        try:
            # Parse the message data
            alert_data = json.loads(message.data.decode("utf-8"))

            # Display formatted alert
            print(f"\n📦 FULL ALERT DATA:")
            print(json.dumps(alert_data, indent=2))

        except json.JSONDecodeError:
            print(f"\n📦 RAW MESSAGE DATA:")
            print(message.data.decode("utf-8"))

        # Display message attributes
        if message.attributes:
            print(f"\n🏷️  MESSAGE ATTRIBUTES:")
            for key, value in message.attributes.items():
                print(f"   • {key}: {value}")

        print("\n" + "="*80)

        ack_ids.append(received_message.ack_id)

    # Acknowledge all messages
    if ack_ids:
        subscriber.acknowledge(subscription=subscription_path, ack_ids=ack_ids)
        print(f"\n✓ Acknowledged {len(ack_ids)} message(s)")

    return True

def main():
    """Wait for messages and display them."""
    print("⏳ Waiting for alert to fire (can take 1-3 minutes)...\n")

    max_attempts = 12  # Try for up to 2 minutes
    for attempt in range(1, max_attempts + 1):
        print(f"Attempt {attempt}/{max_attempts}...")

        if pull_messages():
            print("\n✅ Alert messages received and displayed!")
            sys.exit(0)

        if attempt < max_attempts:
            print(f"Waiting 10 seconds before next attempt...\n")
            time.sleep(10)

    print("\n⚠️  No messages received after 2 minutes.")
    print("Alert may still be processing. Try running again in a minute.")
    sys.exit(1)

if __name__ == "__main__":
    main()
