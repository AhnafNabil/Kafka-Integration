# Alternative Kafka client using confluent-kafka
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Callable, Awaitable, Optional, List
from confluent_kafka import Producer, Consumer, KafkaError
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class KafkaClient:
    """Kafka client using confluent-kafka library"""
    
    def __init__(self, bootstrap_servers: str, client_id: str = None):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id or "kafka-client"
        self.producer: Optional[Producer] = None
        self.consumers: Dict[str, Consumer] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._running = False
    
    async def start_producer(self):
        """Initialize the Kafka producer"""
        if self.producer is None:
            producer_config = {
                'bootstrap.servers': self.bootstrap_servers,
                'client.id': f"{self.client_id}-producer",
                'acks': 'all',
                'retries': 3,
                'retry.backoff.ms': 1000
            }
            self.producer = Producer(producer_config)
            logger.info(f"Kafka producer started for {self.bootstrap_servers}")
    
    async def stop_producer(self):
        """Stop the Kafka producer"""
        if self.producer:
            # Flush any pending messages
            def flush_producer():
                self.producer.flush(timeout=10)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, flush_producer)
            logger.info("Kafka producer stopped")
    
    async def publish_event(
        self, 
        topic: str, 
        event: BaseModel, 
        key: Optional[str] = None,
        partition: Optional[int] = None
    ) -> bool:
        """Publish an event to a Kafka topic"""
        if not self.producer:
            await self.start_producer()
        
        try:
            # Convert Pydantic model to dict
            event_dict = event.dict()
            
            # Add metadata for debugging
            event_dict['_kafka_metadata'] = {
                'topic': topic,
                'producer_client_id': self.client_id,
                'key': key
            }
            
            # Serialize the event with custom datetime serializer
            value = json.dumps(event_dict, default=json_serializer).encode('utf-8')
            key_bytes = key.encode('utf-8') if key else None
            
            # Delivery callback
            def delivery_callback(err, msg):
                if err:
                    logger.error(f"Message delivery failed: {err}")
                else:
                    logger.info(
                        f"Event delivered: topic={msg.topic()}, "
                        f"partition={msg.partition()}, offset={msg.offset()}"
                    )
            
            # Produce message (FIXED to handle None values properly)
            def produce_message():
                try:
                    # Build produce arguments, filtering out None values that cause issues
                    produce_args = {
                        'topic': topic,
                        'value': value,
                        'callback': delivery_callback
                    }
                    
                    # Only add key if it's not None
                    if key_bytes is not None:
                        produce_args['key'] = key_bytes
                    
                    # Only add partition if it's not None and is a valid integer
                    if partition is not None and isinstance(partition, int) and partition >= 0:
                        produce_args['partition'] = partition
                    
                    # Produce the message
                    self.producer.produce(**produce_args)
                    
                    # Poll for delivery callbacks
                    self.producer.poll(0)
                    return True
                except Exception as e:
                    logger.error(f"Error producing message: {str(e)}")
                    return False
            
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(self.executor, produce_message)
            return success
            
        except Exception as e:
            logger.error(f"Error publishing event to {topic}: {str(e)}")
            return False
    
    async def create_consumer(
        self, 
        topics: List[str], 
        group_id: str,
        auto_offset_reset: str = 'earliest'
    ) -> Consumer:
        """Create a Kafka consumer for given topics"""
        consumer_config = {
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': group_id,
            'client.id': f"{self.client_id}-consumer-{group_id}",
            'auto.offset.reset': auto_offset_reset,
            'enable.auto.commit': False,  # Manual commit for better control
            'max.poll.interval.ms': 300000,
            'session.timeout.ms': 30000
        }
        
        consumer = Consumer(consumer_config)
        consumer.subscribe(topics)
        
        self.consumers[group_id] = consumer
        logger.info(f"Created consumer for topics: {topics}")
        return consumer
    
    async def consume_events(
        self,
        consumer: Consumer,
        message_handler: Callable[[Dict[str, Any]], Awaitable[bool]]
    ):
        """Consume events from Kafka and process them with the provided handler"""
        self._running = True
        
        try:
            logger.info("Starting to consume events...")
            
            while self._running:
                def poll_messages():
                    return consumer.poll(timeout=1.0)
                
                # Poll for messages in executor
                loop = asyncio.get_event_loop()
                msg = await loop.run_in_executor(self.executor, poll_messages)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        continue
                
                try:
                    # Decode message
                    value = json.loads(msg.value().decode('utf-8'))
                    
                    logger.debug(
                        f"Processing message: topic={msg.topic()}, "
                        f"partition={msg.partition()}, offset={msg.offset()}"
                    )
                    
                    # Process the message
                    success = await message_handler(value)
                    
                    if success:
                        # Commit the offset
                        def commit_offset():
                            consumer.commit(msg)
                        
                        await loop.run_in_executor(self.executor, commit_offset)
                        logger.debug(f"Message processed and committed: offset={msg.offset()}")
                    else:
                        logger.error(f"Message processing failed: offset={msg.offset()}")
                        
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Fatal error in event consumption: {str(e)}")
        finally:
            logger.info("Event consumption stopped")
    
    async def stop_consumers(self):
        """Stop all consumers"""
        self._running = False
        
        for group_id, consumer in self.consumers.items():
            try:
                def close_consumer():
                    consumer.close()
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self.executor, close_consumer)
                logger.info(f"Consumer {group_id} stopped")
            except Exception as e:
                logger.error(f"Error stopping consumer {group_id}: {str(e)}")
        
        self.consumers.clear()
    
    async def close(self):
        """Close the Kafka client and all resources"""
        await self.stop_consumers()
        await self.stop_producer()
        self.executor.shutdown(wait=True)
        logger.info("Kafka client closed")


# Kafka topic constants
class KafkaTopics:
    PRODUCT_EVENTS = "product.events"
    INVENTORY_EVENTS = "inventory.events"