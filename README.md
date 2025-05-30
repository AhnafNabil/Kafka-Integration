# Kafka Integration Testing Documentation

This document provides comprehensive testing procedures for the Kafka-based event streaming integration between Product Service and Inventory Service in the e-commerce microservices architecture.

## Overview

The Kafka integration enables **asynchronous communication** between Product and Inventory services, ensuring:
- **Service Decoupling**: Product service operates independently of inventory service
- **Event-Driven Architecture**: Product lifecycle events trigger inventory operations
- **Resilience**: Events are queued and processed even when services are temporarily unavailable
- **Scalability**: Multiple consumers can process events in parallel

## Prerequisites

- Docker and Docker Compose installed
- All services configured with correct Kafka bootstrap servers (`kafka:29092`)
- Network connectivity between containers

## Test Architecture

```
Product Service → Kafka Topic (product.events) → Inventory Service
     ↓                    ↓                           ↓
  MongoDB            Event Storage              PostgreSQL
```

## Testing Procedures

### 1. System Initialization

Start the complete microservices ecosystem:

```bash
# Start all services with fresh builds
docker-compose up --build -d

# Verify all services are running
docker-compose ps
```

**Expected Output:**
All services should show `Up` status with healthy containers.

### 2. Kafka Infrastructure Verification

Verify Kafka is running and topics are available:

```bash
# List Kafka topics (should auto-create product.events)
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

**Expected Output:**
```
__consumer_offsets
product.events
```

### 3. Basic Event Flow Testing

Test the core Kafka integration with a new product:

```bash
# Create a test product
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

### 4. Event Processing Verification

Verify the event was processed and inventory was created:

```bash
# Extract product ID from the API response
PRODUCT_ID=$(curl -s "http://localhost/api/v1/products/" | \
  jq -r '.[] | select(.name=="Kafka Test Product") | ._id')

echo "Product ID: $PRODUCT_ID"

# Check if inventory was automatically created
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

### 5. Event Message Inspection

Examine the actual Kafka messages to verify event structure:

```bash
# View messages in the product.events topic
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic product.events \
  --from-beginning \
  --max-messages 5
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

### 6. Service Monitoring

Monitor service logs for Kafka-related activities:

```bash
# Check product service Kafka publishing
docker-compose logs product-service | grep -i kafka

# Check inventory service Kafka consumption  
docker-compose logs inventory-service | grep -i kafka
```

**Expected Log Patterns:**

**Product Service:**
```
✅ Published product.created event for product ObjectId_string
```

**Inventory Service:**
```
Starting inventory event consumer...
Processing event: product.created (ID: uuid)
✅ Successfully created inventory for product ObjectId_string: quantity=25, threshold=5
```

### 7. Kafka UI Monitoring

Access the Kafka UI for visual monitoring:

```bash
echo "Open Kafka UI: http://localhost:8082"
```

Navigate to:
- **Topics** → `product.events` → View messages
- **Consumer Groups** → `inventory-consumer-group` → Monitor lag

### 8. Service Decoupling Test

Test that services can operate independently:

```bash
# Stop inventory service temporarily
docker-compose stop inventory-service

# Create a product while inventory service is down
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

### 9. Event Replay and Recovery

Test event processing after service recovery:

```bash
# Restart inventory service
docker-compose start inventory-service

# Wait for consumer to process queued events
sleep 10

# Verify inventory was created for the product created during downtime
PRODUCT_ID_2=$(curl -s "http://localhost/api/v1/products/" | \
  jq -r '.[] | select(.name=="Decoupled Test Product") | ._id')

echo "Second Product ID: $PRODUCT_ID_2"
curl -s "http://localhost/api/v1/inventory/$PRODUCT_ID_2" | jq .
```

**Expected Output:**
Inventory should be created automatically once the service restarts and processes the queued event.

### 10. Consumer Group Analysis

Monitor Kafka consumer group status:

```bash
# Check consumer group status and lag
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

### 11. Integration with Existing Features

Test that Kafka integration doesn't break existing functionality:

```bash
# Test low stock notification (Redis integration)
curl -X PUT "http://localhost/api/v1/inventory/$PRODUCT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "available_quantity": 2,
    "reorder_threshold": 5
  }' | jq .
```

**Expected Behavior:**
- Inventory should be updated
- Low stock notification should be sent via Redis
- Notification service should receive and process the alert

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Inventory Not Created Automatically

**Symptoms:**
- Product created successfully
- No inventory record found
- Consumer group shows LAG > 0

**Diagnosis:**
```bash
# Check inventory service logs
docker-compose logs inventory-service | grep -i error

# Check consumer group status
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group inventory-consumer-group
```

**Solutions:**
- Verify Kafka bootstrap servers configuration (`kafka:29092`)
- Check SQLAlchemy syntax in consumer code
- Restart inventory service: `docker-compose restart inventory-service`

#### 2. Kafka Connection Issues

**Symptoms:**
- Services unable to connect to Kafka
- No events in topics
- Connection timeout errors

**Diagnosis:**
```bash
# Test Kafka connectivity from services
docker-compose exec inventory-service ping kafka
docker-compose exec product-service ping kafka

# Check Kafka health
docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092
```

**Solutions:**
- Verify network configuration in docker-compose.yml
- Ensure services depend on Kafka health check
- Check Kafka advertised listeners configuration

#### 3. Event Schema Issues

**Symptoms:**
- Events published but not processed
- Schema validation errors in logs

**Diagnosis:**
```bash
# Examine actual event structure
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic product.events \
  --from-beginning \
  --max-messages 1
```

**Solutions:**
- Verify Pydantic schema definitions match
- Check event serialization/deserialization code
- Validate required fields in event data

## Performance Testing

### Load Testing Event Processing

Test the system under load:

```bash
# Create multiple products rapidly
for i in {1..10}; do
  curl -X POST "http://localhost/api/v1/products/" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"Load Test Product $i\",
      \"description\": \"Load testing product\",
      \"category\": \"Test\",
      \"price\": $(($i * 10.99)),
      \"quantity\": $((10 + $i))
    }" > /dev/null 2>&1 &
done

# Wait for all requests to complete
wait

# Check if all inventories were created
sleep 5
echo "Checking inventory creation for load test..."
curl -s "http://localhost/api/v1/inventory/" | jq 'length'
```

### Monitor Consumer Lag

```bash
# Monitor consumer lag during load test
watch -n 1 'docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group inventory-consumer-group'
```

## Success Criteria

The Kafka integration is working correctly when:

1. ✅ **Product creation triggers events** - Messages appear in `product.events` topic
2. ✅ **Events are consumed** - Consumer group shows LAG = 0
3. ✅ **Inventory auto-creation** - Inventory records created automatically
4. ✅ **Service decoupling** - Product service works independently
5. ✅ **Event replay** - Queued events processed after service restart
6. ✅ **No data loss** - All events eventually processed
7. ✅ **Integration compatibility** - Existing features (notifications) still work

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Consumer Lag**: Messages waiting to be processed
2. **Event Processing Rate**: Events processed per second
3. **Error Rate**: Failed event processing attempts
4. **Service Health**: Kafka and consumer service availability

### Recommended Alerts

- Consumer lag > 100 messages
- No events processed in 5 minutes
- Kafka cluster down
- Inventory service consumer offline

## Conclusion

This testing framework ensures the Kafka integration provides reliable, scalable event-driven communication between services while maintaining system resilience and data consistency. Regular execution of these tests helps maintain system health and catch integration issues early.