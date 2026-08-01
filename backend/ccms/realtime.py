"""Bridges state changes from Celery worker processes to WebSocket clients
connected to the API process, via Redis pub/sub (SDD 3.7: "WebSocket push of
state changes"). Workers and the API are separate OS processes with no shared
memory, so pub/sub - not an in-process event bus - is the only thing that
actually reaches a live WS connection."""

import json

import redis
import redis.asyncio as aioredis

from ccms.config import settings

CHANNEL = "ccms:status_updates"

_sync_client: redis.Redis | None = None


def _get_sync_client() -> redis.Redis:
    global _sync_client
    if _sync_client is None:
        _sync_client = redis.Redis.from_url(settings.redis_broker_url)
    return _sync_client


def publish_status_change(*, device_id: int, old_state: str, new_state: str) -> None:
    """Called from Celery worker processes (evaluator/service.py) after a
    status_event commits. Fire-and-forget: a missed push just means the
    dashboard's 15s polling fallback picks it up instead (SDD 3.7)."""
    payload = json.dumps({"device_id": device_id, "old_state": old_state, "new_state": new_state})
    try:
        _get_sync_client().publish(CHANNEL, payload)
    except redis.RedisError:
        pass


async def subscribe_status_changes():
    """Async generator of decoded {device_id, old_state, new_state} dicts, used
    by the /api/v1/status/live WebSocket route."""
    client = aioredis.Redis.from_url(settings.redis_broker_url)
    pubsub = client.pubsub()
    await pubsub.subscribe(CHANNEL)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await client.aclose()
