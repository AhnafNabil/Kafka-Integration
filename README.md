# Kafka Testing Workflow Documentation

This document provides comprehensive testing procedures for the Kafka-based event streaming integration between Product Service and Inventory Service in the e-commerce microservices architecture.

## Overview

The Kafka integration enables **asynchronous communication** between Product and Inventory services, ensuring:
- **Service Decoupling**: Product service operates independently of inventory service
- **Event-Driven Architecture**: Product lifecycle events trigger inventory operations
- **Resilience**: Events are queued and processed even when services are temporarily unavailable
- **Scalability**: Multiple consumers can process events in parallel

## Test Architecture

```
Product Service → Kafka Topic (product.events) → Inventory Service
     ↓                    ↓                           ↓
  MongoDB            Event Storage              PostgreSQL
```

## Testing Procedures

### 1. System Initialization

- Start the complete microservices ecosystem:

    ```bash
    docker-compose up --build -d
    ```

- Verify all services are running:

    ```bash
    docker-compose ps -a
    ```

- Install `jq` to parse JSON in bash:

    ```bash
    apt-get update && apt-get install -y jq
    ```

### 2. Basic Event Flow Testing

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

### 3. Event Processing Verification

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

### 4. Kafka Infrastructure Verification

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

### 5. Event Message Inspection

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

### 6. Kafka UI Monitoring

Access the Kafka UI for visual monitoring:

```bash
echo "Open Kafka UI: http://localhost:8082"
```

Navigate to:
- **Topics** → `product.events` → View messages
- **Consumer Groups** → `inventory-consumer-group` → Monitor lag

### 7. Service Decoupling Test

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

### 8. Event Replay and Recovery

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

### 9. Consumer Group Analysis

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
inventory-consumer-group product.events  0          2               2               0
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

## Conclusion

This testing framework ensures the Kafka integration provides reliable, scalable event-driven communication between services while maintaining system resilience and data consistency. Kafka helps us decouple services and make them more scalable and resilient.