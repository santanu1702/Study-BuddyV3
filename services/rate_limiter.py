# ============================================================
#         StudyBuddyV3BOT — Rate Limiter Service
#         Per-user AI request rate limiting
#         Separate from message rate limit middleware
# ============================================================

import time
from collections import defaultdict
from typing import Dict, Tuple, List

from config.settings import settings
from config.constants import TimeConstants
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
#   IN-MEMORY AI RATE LIMIT STORE
#   Tracks AI requests per user per hour
#   Format: {user_id: [(timestamp1, timestamp2, ...)]}
# ============================================================

# Stores list of request timestamps per user
_ai_request_store: Dict[int, List[float]] = defaultdict(list)


# ============================================================
#   RATE LIMITER SERVICE
# ============================================================

class RateLimiter:
    """
    Per-user AI request rate limiter.

    Separate from the message rate limit middleware.
    This specifically tracks OpenAI API calls per user
    to prevent API abuse and control costs.

    Uses sliding window algorithm:
    - Keeps timestamps of last N requests
    - On each check, removes expired timestamps
    - If remaining timestamps >= limit → rate limited

    Config (from .env):
        AI_RATE_LIMIT_PER_HOUR: Max AI requests per hour
        AI_RATE_LIMIT_WINDOW:   Window in seconds (3600 = 1 hour)
    """

    def __init__(self) -> None:
        self.max_requests  = settings.AI_RATE_LIMIT_PER_HOUR
        self.window_secs   = TimeConstants.AI_RATE_LIMIT_WINDOW  # 3600

    # ================================================================
    #   MAIN CHECK METHOD
    # ================================================================

    async def check_ai_rate_limit(
        self,
        user_id: int,
    ) -> Tuple[bool, int]:
        """
        Check if a user has exceeded their AI request limit.
        Updates the request store if not limited.

        Args:
            user_id: Telegram user ID

        Returns:
            Tuple of (is_limited, wait_seconds)
            - is_limited: True if user should be blocked
            - wait_seconds: Seconds until limit resets (0 if not limited)

        Usage:
            is_limited, wait_time = await rate_limiter.check_ai_rate_limit(user_id)
            if is_limited:
                await msg.reply(f"Wait {wait_time} seconds")
        """
        now = time.monotonic()

        # ── Clean expired timestamps ──
        self._clean_expired(user_id, now)

        # ── Get current request count ──
        requests = _ai_request_store[user_id]
        count    = len(requests)

        # ── Under limit — record and allow ──
        if count < self.max_requests:
            _ai_request_store[user_id].append(now)
            logger.debug(
                f"AI rate check | User: {user_id} | "
                f"Count: {count + 1}/{self.max_requests} | "
                f"Allowed: True"
            )
            return False, 0

        # ── Over limit — calculate wait time ──
        oldest_request = requests[0]
        wait_secs      = int(
            self.window_secs - (now - oldest_request)
        )
        wait_secs      = max(0, wait_secs)

        logger.info(
            f"⚠️ AI rate limit exceeded | "
            f"User: {user_id} | "
            f"Count: {count}/{self.max_requests} | "
            f"Wait: {wait_secs}s"
        )

        return True, wait_secs

    # ================================================================
    #   CHECK WITHOUT RECORDING
    # ================================================================

    async def is_rate_limited(self, user_id: int) -> bool:
        """
        Check if user is rate limited WITHOUT recording a request.
        Used for pre-checks before processing.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user is currently rate limited
        """
        now = time.monotonic()
        self._clean_expired(user_id, now)
        count = len(_ai_request_store[user_id])
        return count >= self.max_requests

    # ================================================================
    #   REMAINING REQUESTS
    # ================================================================

    async def get_remaining_ai_requests(self, user_id: int) -> int:
        """
        Get remaining AI requests for a user in current window.

        Args:
            user_id: Telegram user ID

        Returns:
            Number of remaining requests (0 if exhausted)
        """
        now = time.monotonic()
        self._clean_expired(user_id, now)
        count = len(_ai_request_store[user_id])
        return max(0, self.max_requests - count)

    async def get_wait_time(self, user_id: int) -> int:
        """
        Get seconds until rate limit resets for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            Seconds to wait (0 if not rate limited)
        """
        now = time.monotonic()
        self._clean_expired(user_id, now)

        requests = _ai_request_store[user_id]

        if len(requests) < self.max_requests:
            return 0

        if not requests:
            return 0

        oldest    = requests[0]
        wait_secs = int(self.window_secs - (now - oldest))
        return max(0, wait_secs)

    # ================================================================
    #   STATUS
    # ================================================================

    async def get_status(self, user_id: int) -> Dict:
        """
        Get full rate limit status for a user.
        Used for admin monitoring and user info.

        Args:
            user_id: Telegram user ID

        Returns:
            Dict with full status information
        """
        now = time.monotonic()
        self._clean_expired(user_id, now)

        requests   = _ai_request_store[user_id]
        count      = len(requests)
        is_limited = count >= self.max_requests
        remaining  = max(0, self.max_requests - count)

        wait_secs = 0
        if is_limited and requests:
            oldest    = requests[0]
            wait_secs = max(0, int(self.window_secs - (now - oldest)))

        return {
            "user_id":      user_id,
            "count":        count,
            "limit":        self.max_requests,
            "remaining":    remaining,
            "is_limited":   is_limited,
            "wait_seconds": wait_secs,
            "window_secs":  self.window_secs,
        }

    # ================================================================
    #   ADMIN CONTROLS
    # ================================================================

    def reset_user(self, user_id: int) -> None:
        """
        Reset AI rate limit for a specific user.
        Can be called by admin commands.

        Args:
            user_id: Telegram user ID to reset
        """
        _ai_request_store[user_id] = []
        logger.info(f"🔄 AI rate limit reset | User: {user_id}")

    def reset_all(self) -> None:
        """
        Reset AI rate limits for all users.
        Used during bot restart or admin command.
        """
        _ai_request_store.clear()
        logger.info("🔄 All AI rate limits reset")

    def get_top_users(self, limit: int = 10) -> List[Dict]:
        """
        Get users with highest AI request counts.
        Used for admin monitoring.

        Args:
            limit: Number of top users to return

        Returns:
            List of dicts sorted by request count
        """
        now = time.monotonic()

        # Clean and count for all users
        user_counts = []
        for user_id in list(_ai_request_store.keys()):
            self._clean_expired(user_id, now)
            count = len(_ai_request_store[user_id])
            if count > 0:
                user_counts.append({
                    "user_id":   user_id,
                    "count":     count,
                    "limit":     self.max_requests,
                    "remaining": max(0, self.max_requests - count),
                })

        # Sort by count descending
        user_counts.sort(key=lambda x: x["count"], reverse=True)
        return user_counts[:limit]

    def get_store_size(self) -> int:
        """
        Return number of users currently tracked.
        Used for memory monitoring.

        Returns:
            Number of users in store
        """
        return len(_ai_request_store)

    # ================================================================
    #   INTERNAL HELPERS
    # ================================================================

    def _clean_expired(self, user_id: int, now: float) -> None:
        """
        Remove expired timestamps from a user's request list.
        Timestamps older than window_secs are removed.

        Args:
            user_id: Telegram user ID
            now:     Current monotonic time
        """
        cutoff   = now - self.window_secs
        requests = _ai_request_store[user_id]

        # Remove all timestamps older than cutoff
        _ai_request_store[user_id] = [
            ts for ts in requests if ts > cutoff
        ]

    def _get_window_start(self, user_id: int) -> float:
        """
        Get the start of the current rate limit window.

        Args:
            user_id: Telegram user ID

        Returns:
            Monotonic timestamp of window start
        """
        requests = _ai_request_store.get(user_id, [])
        if not requests:
            return time.monotonic()
        return requests[0]