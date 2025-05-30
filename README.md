# Testing Commands for Kafka Integration

### 1. Start the system
docker-compose up --build -d

### 2. Wait for all services to be healthy
docker-compose ps

### 3. Check Kafka topics (should auto-create)
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

### 4. Create a test product (this should trigger Kafka event)
curl -X POST "http://localhost/api/v1/products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Kafka Test Product",
    "description": "Testing Kafka integration",
    "category": "Test",
    "price": 99.99,
    "quantity": 25
  }' | jq .

### 5. Get the product ID from response and check inventory was created
PRODUCT_ID=$(curl -s "http://localhost/api/v1/products/" | \
  jq -r '.[] | select(.name=="Kafka Test Product") | ._id')

echo "Product ID: $PRODUCT_ID"

### 6. Check if inventory was created automatically via Kafka
curl -s "http://localhost/api/v1/inventory/$PRODUCT_ID" | jq .

### 7. Check Kafka messages in topic (optional)
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic product.events \
  --from-beginning \
  --max-messages 5

### 8. Monitor Kafka UI (open in browser)
echo "Open Kafka UI: http://localhost:8080"

### 9. Check service logs for Kafka events
docker-compose logs product-service | grep -i kafka
docker-compose logs inventory-service | grep -i kafka

### 10. Verify the decoupling by stopping inventory service temporarily
docker-compose stop inventory-service

### 11. Create another product (should succeed even with inventory service down)
curl -X POST "http://localhost/api/v1/products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Decoupled Test Product",
    "description": "Testing service decoupling",
    "category": "Test",
    "price": 149.99,
    "quantity": 15
  }' | jq .

### 12. Restart inventory service (should process queued events)
docker-compose start inventory-service

### 13. Wait a few seconds and check if inventory was created for the second product
sleep 10

PRODUCT_ID_2=$(curl -s "http://localhost/api/v1/products/" | \
  jq -r '.[] | select(.name=="Decoupled Test Product") | ._id')

echo "Second Product ID: $PRODUCT_ID_2"
curl -s "http://localhost/api/v1/inventory/$PRODUCT_ID_2" | jq .

### 14. Check consumer group status
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group inventory-consumer-group

### 15. Test low stock notification still works
curl -X PUT "http://localhost/api/v1/inventory/$PRODUCT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "available_quantity": 2,
    "reorder_threshold": 5
  }' | jq .