# Product Service Microservice

This service is responsible for managing product information in the e-commerce system.

## Features

- Create, read, update, and delete product information
- Filter products by various criteria (category, price range, name)
- List all product categories
- Health check endpoint

## Tech Stack

- **Framework**: FastAPI
- **Database**: MongoDB
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

2. Update the MongoDB URI and other settings in the `.env` file if necessary.

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

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Project Structure

- `app/main.py`: Application entry point
- `app/api/routes/products.py`: Product API endpoints
- `app/models/product.py`: Pydantic models for product data
- `app/db/mongodb.py`: Database connection handling

## Testing

```bash
pytest
```

## Integration with Other Services

This service is designed to work with:

- API Gateway: Handles authentication/authorization
- Inventory Service: Manages product stock levels
- Order Service: Creates orders that reference products