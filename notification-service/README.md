# Notification Service

This microservice is responsible for managing notifications in the e-commerce system, with a particular focus on low stock alerts from the inventory service using Redis for message passing.

## Features

- Real-time low stock notifications via Redis pub/sub
- Notification delivery through multiple channels (email, database)
- User notification preferences management
- Notification history tracking
- Background notification processing
- Health check endpoint

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Message Queue**: Redis
- **Email**: SMTP via aiosmtplib
- **Container**: Docker
- **Authentication**: Token-based (relies on API Gateway)

## Architecture

The Notification Service follows these key architectural patterns:

1. **Pub/Sub Pattern**: Uses Redis pub/sub for real-time notifications from Inventory Service
2. **Consumer Pattern**: Background processes that consume notifications from Redis streams
3. **Repository Pattern**: Database access for notification persistence
4. **Adapter Pattern**: Multiple notification channels (email, database) with a common interface

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.8+

### Environment Setup

1. Copy the example environment file and modify as needed:
   ```
   cp .env.example .env
   ```

2. Update the PostgreSQL URI, Redis URI, SMTP settings, and other settings in the `.env` file.

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

- Swagger UI: http://localhost:8004/api/v1/docs
- ReDoc: http://localhost:8004/api/v1/redoc

## API Endpoints

### Notifications

- `GET /api/v1/notifications/` - List notifications for a user
- `GET /api/v1/notifications/unread` - Get unread notification count
- `POST /api/v1/notifications/mark-read/{notification_id}` - Mark a notification as read
- `POST /api/v1/notifications/mark-all-read` - Mark all notifications as read
- `GET /api/v1/notifications/preferences` - Get notification preferences
- `POST /api/v1/notifications/preferences` - Create notification preference
- `PUT /api/v1/notifications/preferences/{preference_id}` - Update notification preference
- `DELETE /api/v1/notifications/preferences/{preference_id}` - Delete notification preference
- `POST /api/v1/notifications/test` - Send a test notification

## Integration with Other Services

This service interacts with:

- **Inventory Service**: Receives low stock notifications via Redis
- **User Service**: Gets user information for notifications

## Redis Channels

- `inventory:low-stock`: Channel for inventory low stock notifications
- `inventory:low-stock:stream`: Redis stream for persistent storage of notifications

## Testing

```bash
pytest
```

## Docker Compose

The included docker-compose.yml file sets up:
- The notification service
- PostgreSQL for notification data
- Redis for pub/sub messaging
- Network connectivity to other services

## Code Structure

- `app/api/routes/`: API endpoints
- `app/models/`: Database and Pydantic models
- `app/services/`: Service integrations (Redis, Email, etc.)
- `app/db/`: Database setup and connections
- `app/core/`: Core configuration and settings