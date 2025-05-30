# Inventory Service

This microservice is responsible for managing product inventory in the e-commerce system.

## Features

- Track product stock levels
- Reserve inventory for orders
- Release inventory from cancelled orders
- Low stock notifications
- Inventory history tracking
- Health check endpoint

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Container**: Docker
- **Authentication**: Token-based (relies on API Gateway)

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.8+

### Environment Setup

1. Copy the example environment file and modify as needed:
   ```
   cp .env.example .env
   ```

2. Update the PostgreSQL URI and other settings in the `.env` file if necessary.

### Running the Service

With Docker Compose:

```bash
docker-compose up
```

For development without Docker:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn app.main:app --reload
```

## API Documentation

When the service is running, you can access:

- Swagger UI: http://localhost:8002/api/v1/docs
- ReDoc: http://localhost:8002/api/v1/redoc

## API Endpoints

### Inventory

- `GET /api/v1/inventory` - List all inventory items
- `GET /api/v1/inventory/{product_id}` - Get inventory for a specific product
- `GET /api/v1/inventory/check` - Check if a product has sufficient inventory
- `POST /api/v1/inventory` - Update product inventory levels
- `POST /api/v1/inventory/reserve` - Reserve inventory for an order
- `POST /api/v1/inventory/release` - Release previously reserved inventory
- `GET /api/v1/inventory/low-stock` - Get products with low inventory

## Integration with Other Services

This service interacts with:

- **Product Service**: Gets product information
- **Order Service**: Processes inventory reservations and releases

## Data Model

An inventory item contains:
- Product ID
- Available quantity
- Reserved quantity
- Reorder threshold
- Last updated timestamp

## Testing

```bash
pytest
```

## Docker Compose

The included docker-compose.yml file sets up:
- The inventory service
- PostgreSQL for inventory data
- Network connectivity to other services