# User Service

This microservice is responsible for managing users, authentication, and authorization in the e-commerce system.

## Features

- User registration and login
- User profile management
- Address management
- Password reset functionality
- JWT-based authentication
- Role-based authorization
- Email verification
- Health check endpoint

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **Authentication**: JWT tokens
- **Password Hashing**: bcrypt
- **Container**: Docker

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.8+

### Environment Setup

1. Copy the example environment file and modify as needed:
   ```
   cp .env.example .env
   ```

2. Update the PostgreSQL URI, JWT secret, and other settings in the `.env` file if necessary.

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

## API Endpoints

### Authentication

- `POST /api/v1/auth/register` - Register a new user
- `POST /api/v1/auth/login` - Login and get access token
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/forgot-password` - Initiate password reset
- `POST /api/v1/auth/reset-password` - Complete password reset
- `POST /api/v1/auth/verify-email` - Verify email address

### Users

- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update current user profile
- `GET /api/v1/users/{user_id}` - Get user by ID (admin only)
- `PUT /api/v1/users/{user_id}` - Update user (admin only)
- `DELETE /api/v1/users/{user_id}` - Delete user (admin only)

### Addresses

- `GET /api/v1/users/me/addresses` - List user's addresses
- `POST /api/v1/users/me/addresses` - Add new address
- `GET /api/v1/users/me/addresses/{address_id}` - Get specific address
- `PUT /api/v1/users/me/addresses/{address_id}` - Update address
- `DELETE /api/v1/users/me/addresses/{address_id}` - Delete address
- `PUT /api/v1/users/me/addresses/{address_id}/default` - Set as default address

## Integration with Other Services

This service is designed as the authentication and user management system for the entire e-commerce platform. Other services should verify JWT tokens against this service.

## Data Model

User data includes:
- Basic information (name, email, etc.)
- Authentication details (password hash, role)
- Multiple addresses
- Email verification status
- Account status (active/inactive)

## Testing

```bash
pytest
```

## Docker Compose

The included docker-compose.yml file sets up:
- The user service
- PostgreSQL for user data
- Network connectivity to other services