"""
Conversation Store — Level A Memory Tier
Plan.md Phase A1

Redis-backed per-session conversation history. Reuses the singleton
RedisConnectionManager from checkpoint.py — no second Redis client is opened.

Key scheme:  esp:conv:{session_id}
Value:       JSON list of turn dicts, newest last, trimmed to 20 stored.
TTL:         7 days (refreshed on every append).

Per-turn schema:
  { role, content, timestamp, well_id, intent_detected }

Methods:
  append(session_id, role, content, well_id=None, intent=None)
  get_history(session_id, limit=10)  -> last N turns
  get_last_well(session_id)           -> most recent non-null well_id
  clear(session_id)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.events.redis_connection import RedisConnectionManager

logger = logging.getLogger(__name__)

_CONV_TTL_SECONDS = 7 * 24 * 3600   # 7 days
_MAX_STORED_TURNS  = 20              # keep last 20; serve last 10
_KEY_PREFIX        = "esp:conv:"


class ConversationStore:
    """
    Session-scoped conversation history backed by the shared Redis singleton.
    Falls back to an in-process dict when Redis is unavailable (mirrors
    CheckpointManager's degradation behaviour per Plan.md A1).
    """

    def __init__(self, connection_mgr: Optional[RedisConnectionManager] = None):
        # Reuse existing singleton — do NOT open a new client.
        self._redis = connection_mgr or RedisConnectionManager()
        # In-memory fallback: session_id -> list[turn]
        self._fallback: Dict[str, List[Dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append(
        self,
        session_id: str,
        role: str,
        content: str,
        well_id: Optional[str] = None,
        intent: Optional[str] = None,
    ) -> None:
        """Push one turn, trim to last _MAX_STORED_TURNS, refresh TTL."""
        turn = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "well_id": well_id,
            "intent_detected": intent,
        }
        turns = self._load(session_id)
        turns.append(turn)
        if len(turns) > _MAX_STORED_TURNS:
            turns = turns[-_MAX_STORED_TURNS:]
        self._save(session_id, turns)

    def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Return the most recent `limit` turns (sliding window)."""
        turns = self._load(session_id)
        return turns[-limit:] if len(turns) > limit else turns

    def get_last_well(self, session_id: str) -> Optional[str]:
        """Return the most recent non-null well_id seen in this session."""
        turns = self._load(session_id)
        for turn in reversed(turns):
            w = turn.get("well_id")
            if w:
                return w
        return None

    def clear(self, session_id: str) -> None:
        """Delete the conversation for this session from Redis and fallback."""
        key = _KEY_PREFIX + session_id
        self._fallback.pop(session_id, None)
        try:
            self._redis.get_client().delete(key)
        except Exception as exc:
            logger.warning("[ConversationStore] Redis delete failed for %s: %s", session_id, exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self, session_id: str) -> List[Dict[str, Any]]:
        key = _KEY_PREFIX + session_id
        try:
            raw = self._redis.get_client().get(key)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("[ConversationStore] Redis load failed for %s: %s — using fallback", session_id, exc)
        return list(self._fallback.get(session_id, []))

    def _save(self, session_id: str, turns: List[Dict[str, Any]]) -> None:
        key = _KEY_PREFIX + session_id
        payload = json.dumps(turns)
        # Always keep fallback in sync (covers Redis-down scenario)
        self._fallback[session_id] = turns
        try:
            self._redis.get_client().set(key, payload, ex=_CONV_TTL_SECONDS)
        except Exception as exc:
            logger.warning("[ConversationStore] Redis save failed for %s: %s — stored in fallback only", session_id, exc)
