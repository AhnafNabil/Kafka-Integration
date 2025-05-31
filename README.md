# E-commerce Microservices: A Testing Scenario

Welcome to **E-commerce Site**, a modern e-commerce platform built with microservices. This guide tells the story of how our system handles real-world scenarios - from busy shopping days to unexpected service outages.

In this documentation, we will test 3 different scenarios:

1. Order Processing Workflow with RabbitMQ
2. Notification Service with Redis
3. Kafka Integration

## The Setup

Clone the repository:

```bash
git clone https://github.com/poridhioss/E-commerce-Microservices-with-Kafka.git
```

>**Note:** you have to change env variables of the notification service in order to test mail notifications. Here, we used `mailtrap.io` to test the mail notifications. So, create a free account on `mailtrap.io` and change the env variables in the `notification-service/.env` file. 

You have to change the `MAIL_USERNAME`, `MAIL_PASSWORD` variables in the `.env` file of the `notification-service` folder. You will get these credentials from `mailtrap.io` sandbox.

Run the application using docker compose:

```bash
docker-compose up --build -d
```

This will start all services including:

- Product Service (MongoDB)
- Order Service (MongoDB)
- Inventory Service (PostgreSQL)
- User Service (PostgreSQL)
- RabbitMQ Message Broker
- Nginx API Gateway
- Redis
- Kafka
- Notification Service (PostgreSQL)

verify that all services are running:

```bash
docker-compose ps -a
```

Install `jq` to make JSON output more readable in the terminal:

```bash
apt-get update && apt-get install -y jq
```

# Order Processing Workflow with RabbitMQ

In this documentation, we will describe the entire testing procedure through a story or scenario that could occur in a real-world setting.

![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/cebdaf0c344e65f11223da2f920bcbe67e1baf7e/E-commerce-with-kafka/images/rabbitmq-01.svg)

![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/cebdaf0c344e65f11223da2f920bcbe67e1baf7e/E-commerce-with-kafka/images/rabbitmq-02.svg)

**RabbitMQ Dashboard**: Open http://localhost:15672 (guest/guest) to watch our message queues in action.

## Chapter 1: A New Customer Arrives

*Sarah visits the site for the first time. She needs to create an account and add her shipping address.*

### Creating Sarah's Account
```bash
curl -X POST "http://localhost/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "sarah@example.com",
    "password": "Password123",
    "first_name": "Sarah",
    "last_name": "Johnson",
    "phone": "555-123-4567"
  }' | jq .
```

### Sarah Logs In

Saving the authentication token:
```bash
curl -s -X POST "http://localhost/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=sarah@example.com&password=Password123" | jq .
```

Save the access_token for subsequent requests:
```bash
TOKEN="eyJhbGciOiJS..."  # Replace with the actual token from the response
```

Saving the user ID:
```bash
USER_ID=$(curl -s -X GET "http://localhost/api/v1/users/me" \
  -H "Authorization: Bearer $TOKEN" | jq -r .id)
```

### Adding Her Shipping Address
```bash
curl -X POST "http://localhost/api/v1/users/me/addresses" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "line1": "456 Tech Street",
    "line2": "Apt 12B",
    "city": "San Francisco",
    "state": "CA",
    "postal_code": "94105",
    "country": "USA",
    "is_default": true
  }' | jq .
```

## Chapter 2: Stocks Products

### Adding the iPhone 15
```bash
curl -s -X POST "http://localhost/api/v1/products/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "iPhone 15 Pro",
    "description": "Latest Apple smartphone with advanced camera system",
    "category": "Electronics",
    "price": 999.99,
    "quantity": 25
  }' | jq .
```

```bash
IPHONE_ID="iphone id" # Replace with the actual id from the response
```

### Adding AirPods
```bash
curl -s -X POST "http://localhost/api/v1/products/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AirPods Pro 2",
    "description": "Wireless earbuds with active noise cancellation",
    "category": "Audio",
    "price": 249.99,
    "quantity": 50
  }' | jq .
```

```bash
AIRPODS_ID="airpods id" # Replace with the actual id from the response
```

### Verifying Automatic Inventory Creation

Check that inventory was automatically created for iPhone:
```bash
curl -s -X GET "http://localhost/api/v1/inventory/$IPHONE_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

Check inventory for AirPods:
```bash
curl -s -X GET "http://localhost/api/v1/inventory/$AIRPODS_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**🎯 Scenario Point**: Notice how inventory records are created automatically with smart thresholds (10% of stock, minimum 5 units).

## Chapter 3: Sarah's Shopping Experience

*Sarah browses products and decides to make her first purchase.*

### Browsing Available Products

Sarah sees all available products:
```bash
curl -s -X GET "http://localhost/api/v1/products/" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

She filters by Electronics category:
```bash
curl -s -X GET "http://localhost/api/v1/products/?category=Electronics" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Sarah Places Her Order

Sarah orders an iPhone and AirPods:
```bash
curl -s -X POST "http://localhost/api/v1/orders/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "items": [
      {
        "product_id": "'$IPHONE_ID'",
        "quantity": 1,
        "price": 999.99
      },
      {
        "product_id": "'$AIRPODS_ID'",
        "quantity": 2,
        "price": 249.99
      }
    ],
    "shipping_address": {
      "line1": "456 Tech Street",
      "line2": "Apt 12B",
      "city": "San Francisco",
      "state": "CA",
      "postal_code": "94105",
      "country": "USA"
    }
  }' | jq .
``` 

Save the order id for subsequent requests:
```bash
ORDER_ID="order id" # Replace with the actual id from the response
```

### Behind the Scenes: RabbitMQ Magic

Check RabbitMQ queues to see the asynchronous processing:
```bash
curl -s -u guest:guest http://localhost:15672/api/queues | \
  jq '.[] | select(.name | contains("order") or contains("inventory")) | {name: .name, total_published: (.message_stats.publish // 0)}'
```

### Verifying Inventory Reservation

Check that inventory was automatically reserved:
```bash
curl -s -X GET "http://localhost/api/v1/inventory/$IPHONE_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

```bash
curl -s -X GET "http://localhost/api/v1/inventory/$AIRPODS_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**🎯 Story Point**: The order is created instantly (status: "pending"), while inventory is reserved asynchronously via RabbitMQ. Sarah gets immediate confirmation!

## Chapter 4: Processing Sarah's Order

### Updating Order Status

```bash
curl -X PUT "http://localhost/api/v1/orders/$ORDER_ID/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "paid"}' | jq '{id: ._id, status: .status, updated_at: .updated_at}'
```

## Chapter 5: The Cancellation Crisis

*Sarah also wants to order for her friend, but then changes her mind. This tests our cancellation system.*

### Places an Order for her friend

Orders an iPhone for her friend:
```bash
curl -s -X POST "http://localhost/api/v1/orders/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "items": [
      {
        "product_id": "'$IPHONE_ID'",
        "quantity": 1,
        "price": 999.99
      }
    ],
    "shipping_address": {
      "line1": "456 Tech Street",
      "city": "San Francisco",
      "state": "CA", 
      "postal_code": "94105",
      "country": "USA"
    }
  }' | jq .
```

Save the order id for subsequent requests:
```bash
FRIEND_ORDER_ID="order id" # Replace with the actual id from the response
```

### Inventory Before Cancellation

```bash
curl -s -X GET "http://localhost/api/v1/inventory/$IPHONE_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Cancels the Order

```bash
curl -X DELETE "http://localhost/api/v1/orders/$FRIEND_ORDER_ID" \
  -H "Authorization: Bearer $TOKEN"
```

Check that RabbitMQ processed the cancellation:
```bash
curl -s -u guest:guest http://localhost:15672/api/queues | \
  jq '.[] | select(.name | contains("order") or contains("inventory")) | {name: .name, total_published: (.message_stats.publish // 0)}'
```

Check that inventory was released:
```bash
curl -s -X GET "http://localhost/api/v1/inventory/$IPHONE_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**🎯 Story Point**: Inventory is automatically released via RabbitMQ when orders are cancelled, ensuring accurate stock levels.

## Chapter 6: Black Friday Disaster (Service Outage Test)

*It's Black Friday! Suddenly, the inventory service crashes due to high load. But our system keeps running...*

### The Crash Happens

Inventory service crashes during peak traffic:
```bash
docker-compose stop inventory-service
```

### Customers Keep Shopping

Customer places order while service is down:
```bash
curl -s -X POST "http://localhost/api/v1/orders/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "items": [
      {
        "product_id": "'$AIRPODS_ID'",
        "quantity": 1,
        "price": 249.99
      }
    ],
    "shipping_address": {
      "line1": "456 Tech Street",
      "city": "San Francisco",
      "state": "CA",
      "postal_code": "94105", 
      "country": "USA"
    }
  }' | jq .
```

Save the order id for subsequent requests:
```bash
BLACKFRIDAY_ORDER_ID="order id" # Replace with the actual id from the response
```

### Messages Queue Up

Check that messages are waiting in queue:
```bash
curl -s -u guest:guest http://localhost:15672/api/queues/%2F/order_created | \
  jq '{messages_waiting: .messages, consumers: .consumers}'
```

![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/cebdaf0c344e65f11223da2f920bcbe67e1baf7e/E-commerce-with-kafka/images/image-00.png)

### Customer Tries to Cancel During Outage

Customer decides to cancel during the outage:
```bash
curl -X DELETE "http://localhost/api/v1/orders/$BLACKFRIDAY_ORDER_ID" \
  -H "Authorization: Bearer $TOKEN"
```

Check that cancellation message is also queued:
```bash
curl -s -u guest:guest http://localhost:15672/api/queues/%2F/inventory_release | \
  jq '{messages_waiting: .messages}'
```

![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/cebdaf0c344e65f11223da2f920bcbe67e1baf7e/E-commerce-with-kafka/images/image-01.png)

### Service Recovery

DevOps team fixes the service:
```bash
docker-compose start inventory-service
```

Check that all messages were processed:
```bash
curl -s -u guest:guest http://localhost:15672/api/queues | \
  jq '.[] | select(.name | contains("order") or contains("inventory")) | {name: .name, messages_waiting: .messages}'
```

![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/cebdaf0c344e65f11223da2f920bcbe67e1baf7e/E-commerce-with-kafka/images/image-02.png)

Verify order was processed and then cancelled:
```bash
curl -s -X GET "http://localhost/api/v1/orders/$BLACKFRIDAY_ORDER_ID" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**🎯 Story Point**: Even during service outages, orders are accepted and queued. When services recover, everything processes automatically!

## Chapter 7: The Final Inventory Report

*At the end of the day, let's see how our system performed.*

### Order Summary

View all orders from today:
```bash
curl -s -X GET "http://localhost/api/v1/orders/" -H "Authorization: Bearer $TOKEN" | \
  jq '.[] | {id: ._id, status: .status, total_price: .total_price}'
```

### Inventory Status

Check final inventory levels:
```bash
curl -s -X GET "http://localhost/api/v1/inventory/" -H "Authorization: Bearer $TOKEN" | \
  jq '.[] | {product_id: .product_id, available: .available_quantity, reserved: .reserved_quantity, threshold: .reorder_threshold}'
```

### RabbitMQ Performance Report

See total message throughput:
```bash
curl -s -u guest:guest http://localhost:15672/api/queues | \
  jq '.[] | select(.name | contains("order") or contains("inventory")) | {
    queue: .name,
    total_processed: (.message_stats.deliver // 0),
    currently_waiting: .messages
  }'
```

## The Story's Lessons

### ✅ **What We Proved**

1. **Seamless User Experience**: Orders are accepted instantly while processing happens asynchronously
2. **Automatic Inventory Management**: Stock levels update automatically via RabbitMQ
3. **Service Resilience**: System continues working even during service outages
4. **Data Consistency**: All operations maintain inventory accuracy
5. **Zero Message Loss**: RabbitMQ ensures reliable message delivery

### 📊 **Business Impact**

- **Customer Satisfaction**: No failed orders due to temporary service issues
- **Operational Efficiency**: Automatic inventory tracking and threshold alerts
- **Scalability**: System handles traffic spikes gracefully
- **Reliability**: 99.9% uptime even with individual service failures

# E-commerce Notification System Testing Guide

This comprehensive guide will walk you through testing the **E-commerce Notification System** that automatically monitors inventory levels and sends email alerts when products run low. The system uses **Redis pub/sub** for real-time communication and **SMTP** for email delivery.

## System Architecture

![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/cebdaf0c344e65f11223da2f920bcbe67e1baf7e/E-commerce-with-kafka/images/Notification-service.svg)


## Testing Scenarios

### Scenario 1: Direct Email Testing

**Purpose**: Verify the email delivery system works independently

**When to Use**: 
- Initial system setup
- Email configuration troubleshooting
- SMTP connectivity verification

**Steps**:

Send test email:

```bash
curl -X POST "http://localhost/api/v1/notifications/test" | jq . 
```

**Expected Response**:

```json
{
  "message": "Test notification created",
  "notification_id": 1,
  "email_sent": true,
  "admin_email": "admin@example.com"
}
```

**Success Indicators**:
- `email_sent: true` in response
- Email appears in Mailtrap inbox
- Subject: "Test Notification"

![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/cebdaf0c344e65f11223da2f920bcbe67e1baf7e/E-commerce-with-kafka/images/image.png)

### Scenario 2: Product Creation Flow

**Purpose**: Test automatic inventory creation and threshold setup

**When to Use**:
- New product onboarding
- Inventory service integration testing

**Steps**:

1. Create a test product:

    ```bash
    curl -X POST "http://localhost/api/v1/products/" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "Smart Watch",
        "description": "Waterproof fitness tracker with heart rate monitoring",
        "category": "Electronics",
        "price": 299.99,
        "quantity": 15
      }' | jq .
    ```

2. Extract product ID from response:

    ```bash
    PRODUCT_ID=$(curl -s "http://localhost/api/v1/products/" | \
      jq -r '.[] | select(.name=="Smart Watch") | ._id')
    echo "Product ID: $PRODUCT_ID"
    ```

3. Verify automatic inventory creation:

    ```bash
    curl -s "http://localhost/api/v1/inventory/$PRODUCT_ID" | jq .
    ```

**Expected Results**:
- Product created successfully
- Inventory record auto-generated
- Default reorder threshold set (minimum 5 or 10% of initial quantity)

### Scenario 3: Direct Inventory Update Trigger

**Purpose**: Test low stock detection via manual inventory adjustment

**When to Use**:
- Inventory management scenarios
- Stock adjustment workflows
- Immediate notification triggers

**Steps**:

1. Update inventory below threshold to trigger notification:

    ```bash
    curl -X PUT "http://localhost/api/v1/inventory/$PRODUCT_ID" \
      -H "Content-Type: application/json" \
      -d '{
        "available_quantity": 3,
        "reorder_threshold": 8
      }' | jq .
    ```

2. Wait for notification processing:

    ```bash
    sleep 10
    ```

3. Verify notification was created:

    ```bash
    curl -s "http://localhost/api/v1/notifications/?limit=3" | jq '.[0]'
    ```

    ![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/cebdaf0c344e65f11223da2f920bcbe67e1baf7e/E-commerce-with-kafka/images/image-1.png)

**Success Flow**:
- Inventory updated successfully
- Low stock condition detected (3 < 8)
- Redis message published
- Notification service receives message
- Email sent to admin
- Database record created

**📧 Expected Email Content**:
- Subject: "Low Stock Alert: Smart Watch"
- Product details with current quantity (3) and threshold (8)

![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/cebdaf0c344e65f11223da2f920bcbe67e1baf7e/E-commerce-with-kafka/images/image-2.png)

### Scenario 4: Order-Triggered Notification Flow
**Purpose**: Test complete e-commerce workflow from order to notification

**When to Use**:
- End-to-end system testing
- Customer order impact simulation
- Multi-service integration verification

**Setup**:

1. Create another test product with specific threshold:

    ```bash
    curl -X POST "http://localhost/api/v1/products/" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "Wireless Noise-Cancelling Headphones",
        "description": "Premium headphones with active noise cancellation",
        "category": "Audio",
        "price": 149.99,
        "quantity": 12
      }' | jq .
    ```

2. Get the new product ID:

    ```bash
    ORDER_PRODUCT_ID=$(curl -s "http://localhost/api/v1/products/" | \
      jq -r '.[] | select(.name=="Wireless Noise-Cancelling Headphones") | ._id')
    echo "Order Product ID: $ORDER_PRODUCT_ID"
    ```

**User Registration & Order Process**:

3. Register a test user:

    ```bash
    curl -X POST "http://localhost/api/v1/auth/register" \
      -H "Content-Type: application/json" \
      -d '{
        "email": "order-test@example.com",
        "password": "OrderTest123",
        "first_name": "Order",
        "last_name": "Tester",
        "phone": "555-ORDER-TEST"
      }' | jq .
    ```

4. Login to get authentication token:

    ```bash
    TOKEN=$(curl -s -X POST "http://localhost/api/v1/auth/login" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=order-test@example.com&password=OrderTest123" | \
      jq -r .access_token)
    ```

5. Get user ID for order creation:

    ```bash
    USER_ID=$(curl -s -X GET "http://localhost/api/v1/users/me" \
      -H "Authorization: Bearer $TOKEN" | jq -r .id)
    ```

6. Place order that will trigger low stock (12 - 8 = 4, which is < 5 threshold):

    ```bash
    curl -X POST "http://localhost/api/v1/orders/" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "user_id": "'$USER_ID'",
        "items": [
          {
            "product_id": "'$ORDER_PRODUCT_ID'",
            "quantity": 8,
            "price": 149.99
          }
        ],
        "shipping_address": {
          "line1": "123 Order Test Lane",
          "city": "Notification City",
          "state": "NC",
          "postal_code": "12345",
          "country": "Testland"
        }
      }' | jq .
    ```

**Verification**:

7. Wait for order processing and notification:

    ```bash
    sleep 15
    ```

8. Check inventory was reduced:

    ```bash
    curl -s "http://localhost/api/v1/inventory/$ORDER_PRODUCT_ID" | jq .
    ```

9. Verify notification was triggered:

    ```bash
    curl -s "http://localhost/api/v1/notifications/?limit=5" | \
      jq '.[] | select(.type=="low_stock") | {id, subject, status, created_at}'
    ```

    ![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/cebdaf0c344e65f11223da2f920bcbe67e1baf7e/E-commerce-with-kafka/images/image-3.png)

10. Check Email Notifications:

    ![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/cebdaf0c344e65f11223da2f920bcbe67e1baf7e/E-commerce-with-kafka/images/image-4.png)

    

**Complete Order Flow**:

1. **Order Placed** → Order Service creates order
2. **Inventory Reserved** → Inventory Service reduces available stock
3. **Low Stock Detected** → Available quantity (4) < threshold (5)
4. **Redis Message** → Inventory publishes low stock event
5. **Notification Triggered** → Notification Service processes message
6. **Email Sent** → Admin receives low stock alert
7. **Database Updated** → Notification record stored

### Scenario 5: Direct Redis Messaging

**Purpose**: Test Redis pub/sub communication directly

**When to Use**:
- Debugging message queue issues
- Testing notification service isolation
- Verifying Redis connectivity

**Steps**:

1. Send direct Redis message:

    ```bash
    docker-compose exec redis redis-cli PUBLISH inventory:low-stock '{
      "type": "low_stock",
      "product_id": "redis-direct-test",
      "product_name": "Direct Redis Test Product",
      "current_quantity": 2,
      "threshold": 5,
      "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'"
    }'
    ```

2. Wait for processing:

    ```bash
    sleep 5
    ```

3. Check notification was created:

    ```bash
    curl -s "http://localhost/api/v1/notifications/?limit=3" | \
      jq '.[] | select(.data.product_id=="redis-direct-test")'
    ```

**Success Indicators**:
- Redis returns `(integer) 1` (message published to 1 subscriber)
- Notification appears in database
- Email sent to admin

![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/cebdaf0c344e65f11223da2f920bcbe67e1baf7e/E-commerce-with-kafka/images/image-5.png)

# Kafka Testing Workflow Documentation

This document provides comprehensive testing procedures for the Kafka-based event streaming integration between Product Service and Inventory Service in the e-commerce microservices architecture.

## Overview

The Kafka integration enables **asynchronous communication** between Product and Inventory services, ensuring:
- **Service Decoupling**: Product service operates independently of inventory service
- **Event-Driven Architecture**: Product lifecycle events trigger inventory operations
- **Resilience**: Events are queued and processed even when services are temporarily unavailable
- **Scalability**: Multiple consumers can process events in parallel

## Kafka Integration Architecture

![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/cebdaf0c344e65f11223da2f920bcbe67e1baf7e/E-commerce-with-kafka/images/Kafka-integration.svg)

## Testing Procedures for Kafka Integration

### 1. Basic Event Flow Testing

Test the core Kafka integration with a new product:

```bash
curl -X POST "http://localhost/api/v1/products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Kafka Test Product",
    "description": "Testing Kafka integration",
    "category": "Test",
    "price": 99.99,
    "quantity": 25
  }' | jq .
```

**Expected Output:**
```json
{
  "name": "Kafka Test Product",
  "description": "Testing Kafka integration", 
  "category": "Test",
  "price": 99.99,
  "quantity": 25,
  "_id": "ObjectId_string"
}
```

### 2. Event Processing Verification

Verify the event was processed and inventory was created:

- Extract product ID from the API response:

    ```bash
    PRODUCT_ID=$(curl -s "http://localhost/api/v1/products/" | \
      jq -r '.[] | select(.name=="Kafka Test Product") | ._id')
    echo "Product ID: $PRODUCT_ID"
    ```

- Check if inventory was automatically created:

    ```bash
    curl -s "http://localhost/api/v1/inventory/$PRODUCT_ID" | jq .
    ```

    **Expected Output:**
    ```json
    {
      "id": 1,
      "product_id": "ObjectId_string",
      "available_quantity": 25,
      "reserved_quantity": 0,
      "reorder_threshold": 5,
      "created_at": "2025-05-30T16:00:00Z",
      "updated_at": "2025-05-30T16:00:00Z"
    }
    ```

### 3. Kafka Infrastructure Verification

Verify Kafka is running and topics are available:

```bash
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

**Expected Output:**
```
__consumer_offsets
product.events
inventory.events
```

### 4. Event Message Inspection

Examine the actual Kafka messages to verify event structure:

```bash
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic product.events \
  --from-beginning \
  --max-messages 5 | jq .
```

**Expected Output:**
```json
{
  "metadata": {
    "event_id": "uuid",
    "event_type": "product.created",
    "timestamp": "2025-05-30T16:00:00Z",
    "source": "product-service",
    "version": "1.0"
  },
  "data": {
    "product_id": "ObjectId_string", 
    "name": "Kafka Test Product",
    "description": "Testing Kafka integration",
    "category": "Test",
    "price": 99.99,
    "initial_quantity": 25,
    "reorder_threshold": 5
  },
  "_kafka_metadata": {
    "topic": "product.events",
    "producer_client_id": "product-service",
    "key": "ObjectId_string"
  }
}
```

### 5. Kafka UI Monitoring

Access the Kafka UI for visual monitoring:

```bash
echo "Open Kafka UI: http://localhost:8082"
```

Navigate to:
- **Topics** → `product.events` → View messages
- **Consumer Groups** → `inventory-consumer-group` → Monitor lag

### 6. Service Decoupling Test

Test that services can operate independently:

- Stop inventory service temporarily:


    ```bash
    docker-compose stop inventory-service
    ```

- Create a product while inventory service is down:

    ```bash
    curl -X POST "http://localhost/api/v1/products/" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "Decoupled Test Product",
        "description": "Testing service decoupling", 
        "category": "Test",
        "price": 149.99,
        "quantity": 15
      }' | jq .
    ```

    **Expected Behavior:**
    - Product creation should succeed
    - Event should be queued in Kafka
    - No inventory record should exist yet

### 7. Event Replay and Recovery

Test event processing after service recovery:

- Stop inventory service temporarily:

    ```bash
    docker-compose start inventory-service
    ```

- Get the product ID of the decoupled product:

    ```bash
    PRODUCT_ID_2=$(curl -s "http://localhost/api/v1/products/" | \
      jq -r '.[] | select(.name=="Decoupled Test Product") | ._id')
    echo "Second Product ID: $PRODUCT_ID_2"
    ```

- Check if inventory was created:

    ```bash
    curl -s "http://localhost/api/v1/inventory/$PRODUCT_ID_2" | jq .
    ```

    **Expected Output:**
    Inventory should be created automatically once the service restarts and processes the queued event.

### 8. Consumer Group Analysis

Monitor Kafka consumer group status:

```bash
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group inventory-consumer-group
```

**Expected Output:**
```
GROUP                    TOPIC           PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
inventory-consumer-group product.events  0          6               6               0
```

- **LAG = 0**: All messages processed
- **LAG > 0**: Messages waiting to be processed

## Success Criteria

The Kafka integration is working correctly when:

1. ✅ **Product creation triggers events** - Messages appear in `product.events` topic
2. ✅ **Events are consumed** - Consumer group shows LAG = 0
3. ✅ **Inventory auto-creation** - Inventory records created automatically
4. ✅ **Service decoupling** - Product service works independently
5. ✅ **Event replay** - Queued events processed after service restart
6. ✅ **No data loss** - All events eventually processed
7. ✅ **Integration compatibility** - Existing features (notifications) still work
