# GCP Error Simulator - Sales Analytics API

## Overview
This is a Cloud Run-based error simulator application designed to generate various types of errors and create GCP incidents for testing error triaging systems.

## Application Logic

### Use Case: Sales Analytics API
The application simulates a sales analytics service that processes transaction data and provides insights. This provides a realistic scenario where errors can occur naturally across multiple layers.

### Architecture Layers

#### 1. **Data Layer** (`src/layers/data_layer.py`)
- **Responsibility**: Read and parse CSV transaction data
- **Potential Errors**:
  - File not found
  - CSV parsing errors
  - Data validation errors (missing fields, invalid formats)

#### 2. **Business Logic Layer** (`src/layers/business_layer.py`)
- **Responsibility**: Process sales data and calculate analytics
- **Functions**:
  - Calculate total revenue
  - Identify top-selling products
  - Calculate average transaction value
  - Generate sales trends
- **Potential Errors**:
  - Division by zero
  - Invalid data type calculations
  - Business rule violations
  - Memory/performance issues with large datasets

#### 3. **Error Generation Layer** (`src/layers/error_generator.py`)
- **Responsibility**: Simulate various error scenarios and create GCP incidents
- **Error Types**:
  - Application errors (exceptions, crashes)
  - Data validation errors
  - External service failures
  - Performance degradation
  - Resource exhaustion
- **GCP Integration**: Creates incidents via Cloud Monitoring API

#### 4. **API Layer** (`src/main.py`)
- **Responsibility**: HTTP endpoint interface
- **Endpoints**:
  - `POST /api/v1/analytics` - Process analytics request
    - Query parameters:
      - `error_type` (optional): Trigger specific error type
      - `create_incident` (optional): Create GCP incident on error
      - `date_range` (optional): Filter transactions by date

### Data Model

**Sales Transactions CSV** (`src/data/transactions.csv`):
```csv
transaction_id,date,product_id,product_name,quantity,unit_price,customer_id,region
```

### Error Scenarios

1. **FILE_NOT_FOUND**: Simulates missing data file
2. **INVALID_DATA**: Corrupted or malformed CSV data
3. **CALCULATION_ERROR**: Division by zero, overflow errors
4. **MEMORY_ERROR**: Out of memory simulation
5. **TIMEOUT**: Slow operation timeout
6. **EXTERNAL_SERVICE**: Failed dependency call
7. **VALIDATION_ERROR**: Business rule violation

## Technology Stack
- **Runtime**: Python 3.13
- **Package Manager**: uv
- **Web Framework**: Flask
- **Cloud Platform**: GCP Cloud Run
- **Infrastructure**: Terraform
- **Monitoring**: GCP Cloud Monitoring API

## Project Structure
```
error_simulator/
├── README.md
├── src/
│   ├── main.py                  # Flask API
│   ├── layers/
│   │   ├── __init__.py
│   │   ├── data_layer.py        # CSV reading & parsing
│   │   ├── business_layer.py    # Analytics calculations
│   │   └── error_generator.py   # Error simulation & incident creation
│   └── data/
│       └── transactions.csv     # Sample sales data
├── pyproject.toml               # uv dependencies
├── .python-version              # Python version specification
├── Dockerfile                   # Cloud Run container
└── terraform/
    ├── main.tf                  # Main infrastructure
    ├── variables.tf             # Configuration variables
    └── outputs.tf               # Output values
```

## API Usage

### Basic Request
```bash
curl -X POST https://your-service.run.app/api/v1/analytics
```

### Trigger Specific Error
```bash
curl -X POST "https://your-service.run.app/api/v1/analytics?error_type=CALCULATION_ERROR&create_incident=true"
```

### Query with Date Range
```bash
curl -X POST "https://your-service.run.app/api/v1/analytics?date_range=2024-01-01,2024-12-31"
```

## Future Extensibility

The layered architecture allows for easy enhancement:
- Add more data sources (BigQuery, Cloud Storage, databases)
- Implement additional analytics algorithms
- Add more error scenarios
- Integrate with additional GCP services
- Add authentication/authorization
- Implement caching layers
- Add message queue integration

## Quick Start

### Local Development

1. **Install dependencies**:
   ```bash
   # Install uv if not already installed
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install project dependencies
   uv pip install -e .
   ```

2. **Run locally**:
   ```bash
   cd src
   python main.py
   ```

3. **Test the API**:
   ```bash
   # Health check
   curl http://localhost:8080/

   # List error types
   curl http://localhost:8080/api/v1/errors

   # Normal analytics request
   curl -X POST http://localhost:8080/api/v1/analytics

   # Trigger an error
   curl -X POST "http://localhost:8080/api/v1/analytics?error_type=CALCULATION_ERROR"
   ```

### Deploy to GCP

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for complete deployment instructions using Terraform.

**Quick deployment**:
```bash
# 1. Configure Terraform
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your GCP project ID

# 2. Deploy infrastructure
terraform init
terraform apply

# 3. Build and deploy
cd ..
gcloud builds submit --tag $(terraform -chdir=terraform output -raw docker_image_path):latest
```

## Available Endpoints

### `GET /`
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "service": "error-simulator",
  "version": "1.0.0"
}
```

### `GET /api/v1/errors`
List all available error types.

**Response**:
```json
{
  "status": "success",
  "error_types": [...],
  "usage": {...}
}
```

### `POST /api/v1/analytics`
Process sales analytics with optional error simulation.

**Query Parameters**:
- `error_type` (optional): Error type to simulate (see `/api/v1/errors` for list)
- `create_incident` (optional): Set to `true` to create GCP incident
- `date_range` (optional): Date range filter `YYYY-MM-DD,YYYY-MM-DD`

**Success Response**:
```json
{
  "status": "success",
  "data": {
    "total_revenue": 50000.00,
    "average_transaction_value": 1000.00,
    "total_transactions": 50,
    "top_products": [...],
    "regional_breakdown": {...},
    "sales_trends": {...}
  }
}
```

**Error Response**:
```json
{
  "status": "error",
  "error": {
    "type": "CALCULATION_ERROR",
    "message": "division by zero",
    "incident": {...}
  }
}
```

## Monitoring and Observability

The application integrates with GCP Cloud Monitoring and Cloud Logging:

- **Structured Logging**: All incidents are logged with structured JSON
- **Metrics**: Request count, error rate, latency automatically tracked
- **Dashboard**: Pre-configured monitoring dashboard (see Terraform outputs)
- **Alerts**: Alert policy for high error rates

Search logs for incidents:
```bash
gcloud logging read "INCIDENT_CREATED" --limit 10
```
