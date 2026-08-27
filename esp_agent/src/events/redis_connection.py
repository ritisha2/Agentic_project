"""
Redis Connection Pool & Client Manager
Grounded in Phase 6 Event-Driven Architecture Spec §8, §20
"""

import os
import logging
from typing import Optional
import redis

logger = logging.getLogger(__name__)


class RedisConnectionManager:
    """
    Singleton connection manager for Redis Streams.
    """

    _instance: Optional["RedisConnectionManager"] = None
    _client: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisConnectionManager, cls).__new__(cls)
        return cls._instance

    def get_client(self) -> redis.Redis:
        if self._client is None:
            host = os.environ.get("REDIS_HOST", "localhost")
            port = int(os.environ.get("REDIS_PORT", 6379))
            db = int(os.environ.get("REDIS_DB", 0))

            logger.info(f"Initializing RedisConnectionManager connecting to {host}:{port}/{db}")
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True
            )
        return self._client

    def ping(self) -> bool:
        try:
            return self.get_client().ping()
        except Exception as ex:
            logger.error(f"Redis ping failed: {ex}")
            return False
