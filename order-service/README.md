# Order Service

This microservice is responsible for managing orders in the e-commerce system.

## Features

- Create, read, update, and delete orders
- Process payments (simulated)
- Manage order status (pending, paid, shipped, delivered, cancelled)
- Verify product availability with the inventory service
- Verify user information with the user service
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

- Swagger UI: http://localhost:8001/api/v1/docs
- ReDoc: http://localhost:8001/api/v1/redoc

## API Endpoints

### Orders

- `POST /api/v1/orders/` - Create a new order
- `GET /api/v1/orders/` - List orders (with filtering options)
- `GET /api/v1/orders/{order_id}` - Get a specific order
- `GET /api/v1/orders/user/{user_id}` - Get all orders for a user
- `PUT /api/v1/orders/{order_id}/status` - Update order status
- `DELETE /api/v1/orders/{order_id}` - Cancel an order (if not shipped)

## Integration with Other Services

This service interacts with:

- **User Service**: Validates user information when creating orders
- **Product Service**: Gets product details for order items
- **Inventory Service**: Checks and updates product availability

## Data Model

An order contains:
- Order ID
- User ID
- Order items (product ID, quantity, price)
- Total price
- Status (pending, paid, shipped, delivered, cancelled)
- Timestamps (created, updated)
- Shipping address
- Payment information

## Docker Compose

The included docker-compose.yml file sets up:
- The order service
- MongoDB for order data
- Network connectivity to other services