"""Redis client wrapper for idempotency cache."""

import redis.asyncio as redis
import structlog

logger = structlog.get_logger()


class RedisClient:
    """Async Redis client with connection pooling."""

    def __init__(self, host: str, port: int, db: int = 0, max_connections: int = 10):
        """Initialize Redis client.
        
        Args:
            host: Redis hostname
            port: Redis port
            db: Database number
            max_connections: Maximum pool connections
        """
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            max_connections=max_connections,
            decode_responses=True,
        )
        self.client: redis.Redis | None = None
        logger.info("redis_client_initialized", host=host, port=port, db=db)

    async def connect(self) -> None:
        """Connect to Redis."""
        self.client = redis.Redis(connection_pool=self.pool)
        await self.client.ping()
        logger.info("redis_connected")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.client:
            await self.client.aclose()
            await self.pool.aclose()
            logger.info("redis_disconnected")

    async def set_with_ttl(self, key: str, value: str, ttl: int) -> bool:
        """Set key with TTL in seconds.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")

        result = await self.client.set(key, value, ex=ttl)
        logger.debug("redis_set", key=key, ttl=ttl, success=bool(result))
        return bool(result)

    async def get(self, key: str) -> str | None:
        """Get value by key.
        
        Args:
            key: Cache key
            
        Returns:
            Value or None if not found
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")

        value = await self.client.get(key)
        logger.debug("redis_get", key=key, found=value is not None)
        return value

    async def exists(self, key: str) -> bool:
        """Check if key exists.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")

        result = await self.client.exists(key)
        logger.debug("redis_exists", key=key, exists=bool(result))
        return bool(result)

    async def delete(self, key: str) -> bool:
        """Delete key.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted
        """
        if not self.client:
            raise RuntimeError("Redis client not connected")

        result = await self.client.delete(key)
        logger.debug("redis_delete", key=key, deleted=bool(result))
        return bool(result)
