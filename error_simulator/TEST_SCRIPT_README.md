# Error Simulator Test Script

## Overview

`test_simulator.py` is a comprehensive Python test script that demonstrates all capabilities of the Error Simulator API with clear input/output formatting.

## Features

- ✅ **Color-coded output** for easy reading
- ✅ **Shows request inputs** (method, URL, parameters)
- ✅ **Shows response outputs** (status code, JSON body)
- ✅ **Tests all 7 error types**
- ✅ **Automatic authentication** using gcloud
- ✅ **Formatted summaries** of key data

## Prerequisites

```bash
# Make sure you're authenticated
gcloud auth login
gcloud config set project prj-croud-dev-dst-sandbox

# Install required Python package
pip install requests
```

## Usage

### Run Full Test Suite

```bash
python3 test_simulator.py
```

This runs all 9 tests:
1. Health Check
2. List Available Error Types
3. Normal Analytics Request (Success)
4. Date Range Filtering
5. Simulate CALCULATION_ERROR
6. Simulate FILE_NOT_FOUND Error
7. Simulate TIMEOUT Error
8. Simulate EXTERNAL_SERVICE Error
9. Simulate INVALID_DATA Error

### Output Format

The script displays:

```
📤 Input: Shows what request is being made
   • Method (GET/POST)
   • URL
   • Query Parameters (if any)

📥 Output: Shows the response
   • Status Code
   • Response Body (formatted JSON)
```

### Example Output

```
================================================================================
                         TEST 5: Simulate CALCULATION_ERROR
================================================================================

Simulate Division by Zero Error
--------------------------------
📤 Method: POST
📤 URL: https://error-simulator-zvfvbwinca-uc.a.run.app/api/v1/analytics
📤 Query Parameters: {'error_type': 'CALCULATION_ERROR', 'create_incident': 'true'}
📥 Status Code: 500 Internal Server Error
📥 Response Body:
{
  "error": {
    "incident": {
      "error_message": "float division by zero",
      "error_type": "UNEXPECTED_ERROR",
      "incident_id": "mock-1763207997-unexpected_error",
      "severity": "HIGH",
      "state": "OPEN"
    },
    "message": "float division by zero",
    "type": "UNEXPECTED_ERROR"
  },
  "status": "error"
}

Error Details:
  • Type: UNEXPECTED_ERROR
  • Message: float division by zero
  • Incident ID: mock-1763207997-unexpected_error
  • Severity: HIGH
```

## Customization

### Change Service URL

Edit the `SERVICE_URL` constant at the top of the script:

```python
SERVICE_URL = "https://your-custom-url.run.app"
```

### Test Individual Scenarios

You can comment out tests in the `main()` function:

```python
tests = [
    test_health_check,
    # test_list_errors,  # Skip this test
    test_normal_analytics,
    # ... etc
]
```

### Add New Tests

Create a new test function:

```python
def test_my_scenario(token: str) -> None:
    """Test my custom scenario."""
    print_header("TEST: My Custom Scenario")
    status, response = make_request(
        "POST",
        "/api/v1/analytics",
        token,
        params={"error_type": "TIMEOUT", "date_range": "2024-01-01,2024-01-31"},
        description="My Custom Test"
    )
    # Process response...
```

Then add it to the `tests` list in `main()`.

## Using in Your Code

### Basic Example

```python
import subprocess
import requests
import json

# Get auth token
result = subprocess.run(
    ["gcloud", "auth", "print-identity-token"],
    capture_output=True,
    text=True,
    check=True
)
token = result.stdout.strip()

# Make authenticated request
SERVICE_URL = "https://error-simulator-zvfvbwinca-uc.a.run.app"
headers = {"Authorization": f"Bearer {token}"}

response = requests.post(
    f"{SERVICE_URL}/api/v1/analytics",
    headers=headers,
    params={"error_type": "CALCULATION_ERROR", "create_incident": "true"}
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
```

### Advanced Example with Error Handling

```python
import subprocess
import requests
from typing import Tuple, Dict, Any

def get_auth_token() -> str:
    """Get Google Cloud identity token."""
    result = subprocess.run(
        ["gcloud", "auth", "print-identity-token"],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()

def make_authenticated_request(
    endpoint: str,
    params: Dict[str, str] = None
) -> Tuple[int, Dict[str, Any]]:
    """Make authenticated request to Error Simulator."""
    SERVICE_URL = "https://error-simulator-zvfvbwinca-uc.a.run.app"
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.post(
        f"{SERVICE_URL}{endpoint}",
        headers=headers,
        params=params or {}
    )

    return response.status_code, response.json()

# Usage
status, data = make_authenticated_request(
    "/api/v1/analytics",
    params={"error_type": "TIMEOUT", "create_incident": "true"}
)

if status == 500 and "error" in data:
    error = data["error"]
    incident = error.get("incident", {})

    print(f"Error Type: {error['type']}")
    print(f"Error Message: {error['message']}")
    print(f"Incident ID: {incident.get('incident_id', 'N/A')}")
    print(f"Severity: {incident.get('severity', 'N/A')}")
elif status == 200:
    print(f"Success! Total Revenue: ${data['data']['total_revenue']:,.2f}")
```

## Troubleshooting

### "Failed to get identity token"

**Solution:**
```bash
gcloud auth login
gcloud config set project prj-croud-dev-dst-sandbox
```

### "Permission Denied" or "403 Forbidden"

**Solution:** Grant yourself Cloud Run Invoker role:
```bash
gcloud run services add-iam-policy-binding error-simulator \
  --region=us-central1 \
  --member="user:your-email@example.com" \
  --role="roles/run.invoker"
```

### "Connection Timeout"

Check if the service is running:
```bash
gcloud run services describe error-simulator --region=us-central1
```

## Available Error Types

| Error Type | Layer | Description |
|------------|-------|-------------|
| `FILE_NOT_FOUND` | Data | Simulates missing data file |
| `INVALID_DATA` | Data | Simulates corrupted CSV data |
| `CALCULATION_ERROR` | Business | Division by zero, overflow |
| `VALIDATION_ERROR` | Business | Business rule violation |
| `MEMORY_ERROR` | Runtime | Out of memory error |
| `TIMEOUT` | Runtime | Operation timeout |
| `EXTERNAL_SERVICE` | Integration | External service failure |

## Next Steps

1. Use this script to understand the API behavior
2. Adapt the code examples for your triaging application
3. Monitor incidents in Cloud Logging
4. Build your error analysis and triaging logic on top of these scenarios
