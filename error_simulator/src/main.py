"""
Main Flask application for the Error Simulator API.
"""

import json
import os
import traceback
from typing import Any

from flask import Flask, jsonify, request

from layers.business_layer import BusinessLogicError, SalesAnalytics
from layers.data_layer import DataLayerError, TransactionDataReader
from layers.error_generator import ErrorSimulator, ErrorType, IncidentCreator

# Initialize Flask app
app = Flask(__name__)

# Get GCP project ID from environment
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'test-project')

# Initialize components
error_simulator = ErrorSimulator(project_id=PROJECT_ID)
incident_creator = IncidentCreator(project_id=PROJECT_ID)


@app.route('/', methods=['GET'])
def health_check() -> tuple[dict[str, Any], int]:
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'error-simulator',
        'version': '1.0.0'
    }), 200


@app.route('/api/v1/analytics', methods=['POST'])
def process_analytics() -> tuple[dict[str, Any], int]:
    """
    Process sales analytics request.

    Query Parameters:
        error_type (str, optional): Error type to simulate
        create_incident (bool, optional): Create GCP incident on error
        date_range (str, optional): Date range filter (start_date,end_date)

    Returns:
        JSON response with analytics data or error information
    """
    # Parse query parameters
    error_type_param = request.args.get('error_type')
    create_incident = request.args.get('create_incident', 'false').lower() == 'true'
    date_range = request.args.get('date_range')

    try:
        # Check if we should simulate a standalone error (not data/calculation related)
        if error_type_param in ['MEMORY_ERROR', 'TIMEOUT', 'EXTERNAL_SERVICE']:
            error_type = ErrorType(error_type_param)
            error_simulator.simulate_error(error_type, create_incident)

        # Parse date range
        start_date, end_date = None, None
        if date_range:
            try:
                dates = date_range.split(',')
                if len(dates) == 2:
                    start_date, end_date = dates[0].strip(), dates[1].strip()
            except ValueError:
                return jsonify({
                    'error': 'Invalid date_range format. Expected: start_date,end_date'
                }), 400

        # Data Layer - Read transactions
        data_reader = TransactionDataReader()

        # Pass error simulation to data layer if applicable
        data_error_type = error_type_param if error_type_param in ['FILE_NOT_FOUND', 'INVALID_DATA'] else None
        transactions = data_reader.read_transactions(simulate_error=data_error_type)

        # Filter by date range if specified
        if start_date or end_date:
            transactions = data_reader.filter_by_date_range(transactions, start_date, end_date)

        # Business Layer - Perform analytics
        analytics = SalesAnalytics(transactions)

        # Pass error simulation to business layer if applicable
        calc_error_type = error_type_param if error_type_param == 'CALCULATION_ERROR' else None
        summary = analytics.generate_summary(simulate_error=calc_error_type)

        # Success response
        return jsonify({
            'status': 'success',
            'data': summary,
            'metadata': {
                'project_id': PROJECT_ID,
                'timestamp': analytics.generate_summary()['date_range'],
                'simulated_error': error_type_param if error_type_param else None
            }
        }), 200

    except DataLayerError as e:
        # Handle data layer errors
        return handle_error(e, 'DATA_LAYER_ERROR', create_incident, 500)

    except BusinessLogicError as e:
        # Handle business logic errors
        return handle_error(e, 'BUSINESS_LOGIC_ERROR', create_incident, 500)

    except Exception as e:
        # Handle unexpected errors
        error_type_str = getattr(e, 'error_info', {}).get('error_type', 'UNEXPECTED_ERROR')
        incident_data = getattr(e, 'error_info', {}).get('incident')

        # If error already has incident info (from error simulator), use it
        if incident_data:
            return jsonify({
                'status': 'error',
                'error': {
                    'type': error_type_str,
                    'message': str(e),
                    'incident': incident_data
                }
            }), 500

        return handle_error(e, error_type_str, create_incident, 500)


@app.route('/api/v1/errors', methods=['GET'])
def list_error_types() -> tuple[dict[str, Any], int]:
    """
    List available error types for simulation.

    Returns:
        JSON response with error types and descriptions
    """
    error_types = [
        {
            'type': 'FILE_NOT_FOUND',
            'description': 'Simulates missing data file',
            'layer': 'data'
        },
        {
            'type': 'INVALID_DATA',
            'description': 'Simulates corrupted or malformed CSV data',
            'layer': 'data'
        },
        {
            'type': 'CALCULATION_ERROR',
            'description': 'Simulates calculation errors (division by zero, etc.)',
            'layer': 'business'
        },
        {
            'type': 'VALIDATION_ERROR',
            'description': 'Simulates business rule validation failure',
            'layer': 'business'
        },
        {
            'type': 'MEMORY_ERROR',
            'description': 'Simulates out of memory error',
            'layer': 'runtime'
        },
        {
            'type': 'TIMEOUT',
            'description': 'Simulates operation timeout',
            'layer': 'runtime'
        },
        {
            'type': 'EXTERNAL_SERVICE',
            'description': 'Simulates external service failure',
            'layer': 'integration'
        }
    ]

    return jsonify({
        'status': 'success',
        'error_types': error_types,
        'usage': {
            'endpoint': '/api/v1/analytics',
            'parameters': {
                'error_type': 'One of the error types listed above',
                'create_incident': 'Set to "true" to create GCP incident',
                'date_range': 'Optional date range (YYYY-MM-DD,YYYY-MM-DD)'
            },
            'example': '/api/v1/analytics?error_type=CALCULATION_ERROR&create_incident=true'
        }
    }), 200


def handle_error(
    error: Exception,
    error_type: str,
    create_incident: bool,
    status_code: int
) -> tuple[dict[str, Any], int]:
    """
    Handle errors and optionally create incidents.

    Args:
        error: The exception that occurred
        error_type: Type of error
        create_incident: Whether to create a GCP incident
        status_code: HTTP status code

    Returns:
        JSON error response
    """
    error_message = str(error)
    stack_trace = traceback.format_exc()

    incident_data = None
    if create_incident:
        # Determine severity
        severity = 'HIGH' if status_code >= 500 else 'MEDIUM'

        # Create incident
        incident_data = incident_creator.create_incident(
            error_type,
            error_message,
            stack_trace,
            severity
        )

    return jsonify({
        'status': 'error',
        'error': {
            'type': error_type,
            'message': error_message,
            'stack_trace': stack_trace if app.debug else None,
            'incident': incident_data
        }
    }), status_code


if __name__ == '__main__':
    # Run the Flask app
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
