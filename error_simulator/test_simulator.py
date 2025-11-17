#!/usr/bin/env python3
"""
Test script for Error Simulator Cloud Run service.
Makes authenticated requests and displays inputs/outputs clearly.
"""

import json
import subprocess
import sys
from typing import Any, Optional

import requests


# Configuration
SERVICE_URL = "https://error-simulator-zvfvbwinca-uc.a.run.app"
PROJECT_ID = "prj-croud-dev-dst-sandbox"


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}\n")


def print_section(text: str) -> None:
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BLUE}{'-' * len(text)}{Colors.END}")


def print_input(label: str, value: Any) -> None:
    """Print input information."""
    print(f"{Colors.YELLOW}📤 {label}:{Colors.END} {Colors.BOLD}{value}{Colors.END}")


def print_output(label: str, value: Any) -> None:
    """Print output information."""
    if isinstance(value, (dict, list)):
        value_str = json.dumps(value, indent=2)
        print(f"{Colors.GREEN}📥 {label}:{Colors.END}")
        print(f"{Colors.GREEN}{value_str}{Colors.END}")
    else:
        print(f"{Colors.GREEN}📥 {label}:{Colors.END} {Colors.BOLD}{value}{Colors.END}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}❌ Error: {message}{Colors.END}")


def get_auth_token() -> str:
    """Get Google Cloud identity token for authentication."""
    print_section("Authentication")
    print_input("Getting identity token using", "gcloud auth print-identity-token")

    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-identity-token"],
            capture_output=True,
            text=True,
            check=True
        )
        token = result.stdout.strip()
        print_output("Token obtained", f"{token[:30]}...{token[-30:]}")
        return token
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to get identity token: {e.stderr}")
        print("\n💡 Make sure you're authenticated with: gcloud auth login")
        sys.exit(1)
    except Exception as e:
        print_error(f"Failed to get identity token: {e}")
        print("\n💡 Make sure gcloud CLI is installed and configured")
        sys.exit(1)


def make_request(
    method: str,
    endpoint: str,
    token: str,
    params: Optional[dict] = None,
    description: str = ""
) -> tuple[int, dict]:
    """Make an authenticated request to the service."""
    url = f"{SERVICE_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}

    print_section(description or f"{method} {endpoint}")
    print_input("Method", method)
    print_input("URL", url)

    if params:
        print_input("Query Parameters", params)

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, params=params)
        else:
            raise ValueError(f"Unsupported method: {method}")

        print_output("Status Code", f"{response.status_code} {response.reason}")

        try:
            response_data = response.json()
            print_output("Response Body", response_data)
            return response.status_code, response_data
        except json.JSONDecodeError:
            print_output("Response Body (raw)", response.text)
            return response.status_code, {"error": "Invalid JSON response"}

    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        return 0, {"error": str(e)}


def test_health_check(token: str) -> None:
    """Test health check endpoint."""
    print_header("TEST 1: Health Check")
    make_request("GET", "/", token, description="Health Check Endpoint")


def test_list_errors(token: str) -> None:
    """Test list error types endpoint."""
    print_header("TEST 2: List Available Error Types")
    status, response = make_request(
        "GET",
        "/api/v1/errors",
        token,
        description="List All Error Types"
    )

    if status == 200 and "error_types" in response:
        print(f"\n{Colors.BOLD}Available Error Types:{Colors.END}")
        for error_type in response["error_types"]:
            print(f"  • {Colors.CYAN}{error_type['type']}{Colors.END} "
                  f"({error_type['layer']}): {error_type['description']}")


def test_normal_analytics(token: str) -> None:
    """Test normal analytics request (success case)."""
    print_header("TEST 3: Normal Analytics Request (Success)")
    status, response = make_request(
        "POST",
        "/api/v1/analytics",
        token,
        description="Normal Analytics Request"
    )

    if status == 200 and "data" in response:
        data = response["data"]
        print(f"\n{Colors.BOLD}Analytics Summary:{Colors.END}")
        print(f"  • Total Revenue: ${data['total_revenue']:,.2f}")
        print(f"  • Total Transactions: {data['total_transactions']}")
        print(f"  • Average Transaction: ${data['average_transaction_value']:.2f}")
        print(f"  • Date Range: {data['date_range']['start']} to {data['date_range']['end']}")
        print(f"\n{Colors.BOLD}Top 3 Products:{Colors.END}")
        for i, product in enumerate(data['top_products'][:3], 1):
            print(f"  {i}. {product['product_name']}: ${product['total_revenue']:,.2f} "
                  f"({product['total_quantity']} units)")


def test_date_range_filter(token: str) -> None:
    """Test analytics with date range filter."""
    print_header("TEST 4: Date Range Filtering")
    status, response = make_request(
        "POST",
        "/api/v1/analytics",
        token,
        params={"date_range": "2024-01-15,2024-01-20"},
        description="Analytics with Date Range Filter"
    )

    if status == 200 and "data" in response:
        data = response["data"]
        print(f"\n{Colors.BOLD}Filtered Results:{Colors.END}")
        print(f"  • Total Revenue: ${data['total_revenue']:,.2f}")
        print(f"  • Total Transactions: {data['total_transactions']}")
        print(f"  • Date Range: {data['date_range']['start']} to {data['date_range']['end']}")


def test_calculation_error(token: str) -> None:
    """Test calculation error simulation."""
    print_header("TEST 5: Simulate CALCULATION_ERROR")
    status, response = make_request(
        "POST",
        "/api/v1/analytics",
        token,
        params={
            "error_type": "CALCULATION_ERROR",
            "create_incident": "true"
        },
        description="Simulate Division by Zero Error"
    )

    if status == 500 and "error" in response:
        error = response["error"]
        print(f"\n{Colors.BOLD}Error Details:{Colors.END}")
        print(f"  • Type: {Colors.RED}{error['type']}{Colors.END}")
        print(f"  • Message: {error['message']}")

        if "incident" in error:
            incident = error["incident"]
            print(f"\n{Colors.BOLD}Incident Created:{Colors.END}")
            print(f"  • Incident ID: {incident['incident_id']}")
            print(f"  • Severity: {incident['severity']}")
            print(f"  • State: {incident['state']}")
            print(f"  • Start Time: {incident['start_time']}")


def test_file_not_found_error(token: str) -> None:
    """Test file not found error simulation."""
    print_header("TEST 6: Simulate FILE_NOT_FOUND Error")
    status, response = make_request(
        "POST",
        "/api/v1/analytics",
        token,
        params={
            "error_type": "FILE_NOT_FOUND",
            "create_incident": "true"
        },
        description="Simulate Missing Data File"
    )

    if status == 500 and "error" in response:
        error = response["error"]
        incident = error.get("incident", {})
        print(f"\n{Colors.BOLD}Summary:{Colors.END}")
        print(f"  • Error Type: {error['type']}")
        print(f"  • Incident ID: {incident.get('incident_id', 'N/A')}")
        print(f"  • Severity: {incident.get('severity', 'N/A')}")


def test_timeout_error(token: str) -> None:
    """Test timeout error simulation."""
    print_header("TEST 7: Simulate TIMEOUT Error")
    status, response = make_request(
        "POST",
        "/api/v1/analytics",
        token,
        params={
            "error_type": "TIMEOUT",
            "create_incident": "true"
        },
        description="Simulate Operation Timeout"
    )

    if status == 500 and "error" in response:
        error = response["error"]
        incident = error.get("incident", {})
        print(f"\n{Colors.BOLD}Summary:{Colors.END}")
        print(f"  • Error Type: {error['type']}")
        print(f"  • Message: {error['message']}")
        print(f"  • Incident ID: {incident.get('incident_id', 'N/A')}")


def test_external_service_error(token: str) -> None:
    """Test external service error simulation."""
    print_header("TEST 8: Simulate EXTERNAL_SERVICE Error")
    status, response = make_request(
        "POST",
        "/api/v1/analytics",
        token,
        params={
            "error_type": "EXTERNAL_SERVICE",
            "create_incident": "true"
        },
        description="Simulate External Service Failure"
    )

    if status == 500 and "error" in response:
        error = response["error"]
        incident = error.get("incident", {})
        print(f"\n{Colors.BOLD}Summary:{Colors.END}")
        print(f"  • Error Type: {error['type']}")
        print(f"  • Message: {error['message']}")
        print(f"  • Incident ID: {incident.get('incident_id', 'N/A')}")


def test_invalid_data_error(token: str) -> None:
    """Test invalid data error simulation."""
    print_header("TEST 9: Simulate INVALID_DATA Error")
    status, response = make_request(
        "POST",
        "/api/v1/analytics",
        token,
        params={
            "error_type": "INVALID_DATA",
            "create_incident": "true"
        },
        description="Simulate Corrupted CSV Data"
    )

    if status == 500 and "error" in response:
        error = response["error"]
        incident = error.get("incident", {})
        print(f"\n{Colors.BOLD}Summary:{Colors.END}")
        print(f"  • Error Type: {error['type']}")
        print(f"  • Message: {error['message']}")
        print(f"  • Incident ID: {incident.get('incident_id', 'N/A')}")


def main():
    """Run all tests."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔═══════════════════════════════════════════════════════════════════════════════╗")
    print("║                    GCP ERROR SIMULATOR TEST SUITE                             ║")
    print("║                                                                               ║")
    print(f"║  Service URL: {SERVICE_URL:57s}║")
    print(f"║  Project ID:  {PROJECT_ID:57s}║")
    print("╚═══════════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")

    # Get authentication token
    token = get_auth_token()

    # Run tests
    tests = [
        test_health_check,
        test_list_errors,
        test_normal_analytics,
        test_date_range_filter,
        test_calculation_error,
        test_file_not_found_error,
        test_timeout_error,
        test_external_service_error,
        test_invalid_data_error,
    ]

    for i, test in enumerate(tests, 1):
        try:
            test(token)
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}⚠️  Test interrupted by user{Colors.END}")
            sys.exit(0)
        except Exception as e:
            print_error(f"Test failed with exception: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print_header("TEST SUITE COMPLETE")
    print(f"{Colors.BOLD}{Colors.GREEN}✅ All {len(tests)} tests executed{Colors.END}")
    print(f"\n{Colors.BOLD}Next Steps:{Colors.END}")
    print("  1. Check Cloud Logging for incident records")
    print("  2. View monitoring dashboard for metrics")
    print("  3. Use these error scenarios to test your triaging app")
    print(f"\n{Colors.BOLD}View Logs:{Colors.END}")
    print(f"  gcloud run services logs read error-simulator --region=us-central1\n")


if __name__ == "__main__":
    main()
