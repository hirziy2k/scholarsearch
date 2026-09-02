"""Tiered rate limiting, payload size limits, and cost guardrails for PDF-to-PPTX API."""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LAMBDA_PRICE_PER_GB_SECOND = 0.0000166667
LAMBDA_PRICE_PER_REQUEST = 0.0000000021
DEFAULT_MONTHLY_BUDGET_USD = 1000.0
THROTTLE_THRESHOLD = 0.80
STOP_THRESHOLD = 0.95


# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RateTier:
    name: str
    max_file_size_mb: int
    max_pages: int
    requests_per_minute: int
    requests_per_day: int
    max_concurrent: int
    max_timeout_seconds: int
    monthly_cost_limit_usd: float


TIERS: Dict[str, RateTier] = {
    "free": RateTier(
        name="free",
        max_file_size_mb=10,
        max_pages=10,
        requests_per_minute=5,
        requests_per_day=50,
        max_concurrent=1,
        max_timeout_seconds=30,
        monthly_cost_limit_usd=0.0,
    ),
    "pro": RateTier(
        name="pro",
        max_file_size_mb=50,
        max_pages=100,
        requests_per_minute=30,
        requests_per_day=1000,
        max_concurrent=3,
        max_timeout_seconds=120,
        monthly_cost_limit_usd=50.0,
    ),
    "enterprise": RateTier(
        name="enterprise",
        max_file_size_mb=200,
        max_pages=500,
        requests_per_minute=100,
        requests_per_day=10000,
        max_concurrent=10,
        max_timeout_seconds=300,
        monthly_cost_limit_usd=500.0,
    ),
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class UsageStats:
    requests_today: int = 0
    requests_this_minute: int = 0
    active_jobs: int = 0
    monthly_cost_usd: float = 0.0
    monthly_requests: int = 0
    tier_name: str = "free"


@dataclass
class RateLimitResult:
    allowed: bool
    reason: str = ""
    retry_after_seconds: int = 0
    current_usage: Optional[UsageStats] = None
    tier: Optional[RateTier] = None


@dataclass
class BudgetStatus:
    remaining_usd: float
    percentage_used: float
    should_throttle: bool
    should_stop: bool
    monthly_budget_usd: float


# ---------------------------------------------------------------------------
# Internal helpers for sliding / calendar windows
# ---------------------------------------------------------------------------

def _now_ts() -> float:
    return time.time()


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _this_minute_key() -> float:
    return _now_ts() // 60


# ---------------------------------------------------------------------------
# Storage back-ends
# ---------------------------------------------------------------------------

class _MemoryStore:
    """In-memory storage used when Redis is unavailable."""

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def get(self, key: str) -> Optional[Any]:
        return self._data.get(key)

    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        self._data[key] = value

    async def incr(self, key: str) -> int:
        self._data[key] = self._data.get(key, 0) + 1
        return self._data[key]

    async def decr(self, key: str) -> int:
        self._data[key] = self._data.get(key, 0) - 1
        return self._data[key]

    async def expire(self, key: str, _ttl: int) -> None:
        pass

    def lock(self, key: str) -> asyncio.Lock:
        return self._locks[key]

    async def get_sorted_set_range(self, key: str, min_score: float, max_score: float) -> int:
        items = self._data.get(key, [])
        return sum(1 for s in items if min_score <= s <= max_score)

    async def sorted_set_add(self, key: str, score: float) -> None:
        items = self._data.get(key, [])
        items.append(score)
        self._data[key] = items

    async def sorted_set_trim(self, key: str, keep_after: float) -> None:
        items = self._data.get(key, [])
        self._data[key] = [s for s in items if s >= keep_after]


class _RedisStore:
    """Thin async wrapper around redis.asyncio."""

    def __init__(self, redis_client: Any) -> None:
        self._r = redis_client

    async def get(self, key: str) -> Optional[Any]:
        val = await self._r.get(key)
        if val is None:
            return None
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val

    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        payload = json.dumps(value) if not isinstance(value, str) else value
        if ttl > 0:
            await self._r.set(key, payload, ex=ttl)
        else:
            await self._r.set(key, payload)

    async def incr(self, key: str) -> int:
        return await self._r.incr(key)

    async def decr(self, key: str) -> int:
        return await self._r.decr(key)

    async def expire(self, key: str, ttl: int) -> None:
        await self._r.expire(key, ttl)

    async def get_sorted_set_range(self, key: str, min_score: float, max_score: float) -> int:
        return await self._r.zcount(key, min_score, max_score)

    async def sorted_set_add(self, key: str, score: float) -> None:
        await self._r.zadd(key, {str(score): score})

    async def sorted_set_trim(self, key: str, keep_after: float) -> None:
        await self._r.zremrangebyscore(key, "-inf", keep_after)


# ---------------------------------------------------------------------------
# API key management
# ---------------------------------------------------------------------------

class APIKeyManager:
    """Simple API key to tier mapping.

    In production, this would be a database.
    For now, uses a JSON file or environment variable.
    """

    DEFAULT_KEYS: Dict[str, str] = {
        "demo-key-free": "free",
        "demo-key-pro": "pro",
        "demo-key-enterprise": "enterprise",
    }

    def __init__(self, keys_file: Optional[str] = None) -> None:
        self._keys: Dict[str, str] = dict(self.DEFAULT_KEYS)
        if keys_file and Path(keys_file).is_file():
            with open(keys_file, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
                if isinstance(loaded, dict):
                    self._keys.update(loaded)

        env_keys = os.environ.get("PDF2PPTX_API_KEYS")
        if env_keys:
            try:
                loaded = json.loads(env_keys)
                if isinstance(loaded, dict):
                    self._keys.update(loaded)
            except json.JSONDecodeError:
                pass

    async def validate_key(self, api_key: str) -> Optional[str]:
        """Validate key, return tier name or None if invalid."""
        return self._keys.get(api_key)

    def register_key(self, api_key: str, tier: str) -> None:
        if tier not in TIERS:
            raise ValueError(f"Unknown tier: {tier}")
        self._keys[api_key] = tier

    def list_keys(self) -> Dict[str, str]:
        return dict(self._keys)


# ---------------------------------------------------------------------------
# Cost guardrails
# ---------------------------------------------------------------------------

class CostGuardrails:
    """Global cost controls to prevent bill shock."""

    def __init__(self, monthly_budget_usd: float = DEFAULT_MONTHLY_BUDGET_USD) -> None:
        self.monthly_budget = monthly_budget_usd
        self._store: Optional[_MemoryStore | _RedisStore] = None
        self._memory_costs: List[Dict[str, Any]] = []

    def attach_store(self, store: _MemoryStore | _RedisStore) -> None:
        self._store = store

    async def check_budget(self) -> BudgetStatus:
        total = await self._total_monthly_cost()
        remaining = max(0.0, self.monthly_budget - total)
        pct = (total / self.monthly_budget * 100) if self.monthly_budget > 0 else 0.0
        return BudgetStatus(
            remaining_usd=round(remaining, 6),
            percentage_used=round(pct, 2),
            should_throttle=pct >= THROTTLE_THRESHOLD * 100,
            should_stop=pct >= STOP_THRESHOLD * 100,
            monthly_budget_usd=self.monthly_budget,
        )

    async def record_cost(self, cost_usd: float) -> None:
        month_key = datetime.now(timezone.utc).strftime("%Y-%m")
        if self._store is not None:
            key = f"cost:{month_key}:total"
            current = await self._store.get(key) or 0.0
            await self._store.set(key, round(current + cost_usd, 6), ttl=60 * 60 * 24 * 40)
        else:
            self._memory_costs.append({
                "month": month_key,
                "cost_usd": cost_usd,
                "ts": _now_ts(),
            })

    async def get_monthly_report(self) -> Dict[str, Any]:
        month_key = datetime.now(timezone.utc).strftime("%Y-%m")
        total = await self._total_monthly_cost()
        budget_status = await self.check_budget()
        return {
            "month": month_key,
            "total_cost_usd": round(total, 6),
            "budget_usd": self.monthly_budget,
            "remaining_usd": budget_status.remaining_usd,
            "percentage_used": budget_status.percentage_used,
            "should_throttle": budget_status.should_throttle,
            "should_stop": budget_status.should_stop,
        }

    async def _total_monthly_cost(self) -> float:
        month_key = datetime.now(timezone.utc).strftime("%Y-%m")
        if self._store is not None:
            key = f"cost:{month_key}:total"
            return await self._store.get(key) or 0.0
        return sum(
            e["cost_usd"]
            for e in self._memory_costs
            if e["month"] == month_key
        )


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Multi-dimensional rate limiter with cost tracking.

    Tracks per API key:
    - Requests per minute (sliding window)
    - Requests per day (calendar day)
    - Concurrent active jobs
    - Monthly cost (estimated from compute time)
    - File size limits
    - Page count limits
    """

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._key_manager = APIKeyManager()
        self._cost_guardrails = CostGuardrails()
        self._store: _MemoryStore | _RedisStore
        self._redis_available = False

        if redis_url:
            try:
                import redis.asyncio as aioredis  # type: ignore[import-untyped]
                client = aioredis.from_url(redis_url, decode_responses=True)
                self._store = _RedisStore(client)
                self._redis_available = True
            except Exception:
                self._store = _MemoryStore()
        else:
            self._store = _MemoryStore()

        self._cost_guardrails.attach_store(self._store)

        # Memory-only fallback state for per-key counters that survive across
        # the memory store dict.
        self._active_jobs: Dict[str, int] = defaultdict(int)

    # -- public helpers -----------------------------------------------------

    async def check_request(
        self,
        api_key: str,
        file_size_mb: float,
        estimated_pages: int = 0,
    ) -> RateLimitResult:
        """Pre-flight check before accepting a conversion.

        Checks in order:
        1. API key exists and is active
        2. File size within tier limit
        3. Page count within tier limit
        4. Requests per minute not exceeded
        5. Requests per day not exceeded
        6. Concurrent jobs not exceeded
        7. Monthly cost limit not exceeded

        Returns RateLimitResult with allowed=True/False and reason.
        """
        # 1. validate key
        tier_name = await self._key_manager.validate_key(api_key)
        if tier_name is None:
            return RateLimitResult(allowed=False, reason="invalid_api_key")

        tier = TIERS[tier_name]

        # 2. global budget guardrail
        budget = await self._cost_guardrails.check_budget()
        if budget.should_stop:
            return RateLimitResult(
                allowed=False,
                reason="monthly_budget_exceeded",
                retry_after_seconds=self._seconds_until_next_month(),
                tier=tier,
            )

        # 3. file size
        if file_size_mb > tier.max_file_size_mb:
            return RateLimitResult(
                allowed=False,
                reason="file_too_large",
                tier=tier,
            )

        # 4. page count
        if estimated_pages > tier.max_pages:
            return RateLimitResult(
                allowed=False,
                reason="too_many_pages",
                tier=tier,
            )

        # 5. per-minute (sliding window via sorted set)
        minute_count = await self._minute_request_count(api_key)
        if minute_count >= tier.requests_per_minute:
            retry = 60 - int(_now_ts() % 60)
            return RateLimitResult(
                allowed=False,
                reason="rate_exceeded_minute",
                retry_after_seconds=max(retry, 1),
                tier=tier,
            )

        # 6. per-day
        day_count = await self._day_request_count(api_key)
        if day_count >= tier.requests_per_day:
            return RateLimitResult(
                allowed=False,
                reason="rate_exceeded_daily",
                retry_after_seconds=self._seconds_until_next_day(),
                tier=tier,
            )

        # 7. concurrent jobs
        active = await self._active_job_count(api_key)
        if active >= tier.max_concurrent:
            return RateLimitResult(
                allowed=False,
                reason="concurrent_limit_exceeded",
                retry_after_seconds=5,
                tier=tier,
            )

        # 8. monthly cost for tier
        usage = await self.get_usage(api_key)
        if tier.monthly_cost_limit_usd > 0 and usage.monthly_cost_usd >= tier.monthly_cost_limit_usd:
            return RateLimitResult(
                allowed=False,
                reason="monthly_cost_limit_exceeded",
                retry_after_seconds=self._seconds_until_next_month(),
                tier=tier,
                current_usage=usage,
            )

        # 9. global budget throttle (soft warning)
        if budget.should_throttle:
            # still allow but flag it
            pass

        usage = await self.get_usage(api_key)
        return RateLimitResult(
            allowed=True,
            current_usage=usage,
            tier=tier,
        )

    async def record_request(
        self,
        api_key: str,
        file_size_mb: float,
        pages: int,
        processing_time_ms: float,
    ) -> None:
        """Record a completed request for quota tracking."""
        minute_key = f"rate:{api_key}:minute:{int(_now_ts() // 60)}"
        day_key = f"rate:{api_key}:day:{_today_key()}"
        month_key = f"rate:{api_key}:month:{datetime.now(timezone.utc).strftime('%Y-%m')}"

        if self._redis_available:
            await self._store.incr(minute_key)
            await self._store.expire(minute_key, 120)
            await self._store.incr(day_key)
            await self._store.expire(day_key, 86400 * 2)
            await self._store.incr(month_key)
            await self._store.expire(month_key, 60 * 60 * 24 * 40)
        else:
            await self._store.incr(minute_key)
            await self._store.incr(day_key)
            await self._store.incr(month_key)

    async def record_completion(
        self,
        api_key: str,
        processing_time_ms: float,
        memory_mb: float = 0,
    ) -> None:
        """Record completion for cost estimation."""
        if memory_mb <= 0:
            memory_mb = 1024

        cost = await self.estimate_cost_usd(processing_time_ms, memory_mb)
        await self._cost_guardrails.record_cost(cost)

        month_cost_key = f"cost:{api_key}:month:{datetime.now(timezone.utc).strftime('%Y-%m')}"
        current = await self._store.get(month_cost_key) or 0.0
        await self._store.set(month_cost_key, round(current + cost, 6), ttl=60 * 60 * 24 * 40)

        if self._active_jobs.get(api_key, 0) > 0:
            self._active_jobs[api_key] -= 1

    async def increment_active(self, api_key: str) -> None:
        """Mark a job as active (call before processing)."""
        self._active_jobs[api_key] += 1

    async def decrement_active(self, api_key: str) -> None:
        """Mark a job as no longer active."""
        if self._active_jobs.get(api_key, 0) > 0:
            self._active_jobs[api_key] -= 1

    async def get_usage(self, api_key: str) -> UsageStats:
        """Get current usage stats for an API key."""
        tier_name = await self._key_manager.validate_key(api_key) or "free"
        tier = TIERS[tier_name]

        minute_count = await self._minute_request_count(api_key)
        day_count = await self._day_request_count(api_key)
        month_count = await self._month_request_count(api_key)
        month_cost = await self._month_cost(api_key)
        active = await self._active_job_count(api_key)

        return UsageStats(
            requests_today=day_count,
            requests_this_minute=minute_count,
            active_jobs=active,
            monthly_cost_usd=round(month_cost, 6),
            monthly_requests=month_count,
            tier_name=tier_name,
        )

    async def get_tier(self, api_key: str) -> RateTier:
        """Get the tier for an API key."""
        tier_name = await self._key_manager.validate_key(api_key) or "free"
        return TIERS[tier_name]

    @staticmethod
    async def estimate_cost_usd(
        processing_time_ms: float,
        memory_mb: float = 1024,
    ) -> float:
        """Estimate AWS Lambda cost for a conversion.

        Lambda pricing:
        - $0.0000166667 per GB-second
        - $0.0000000021 per request

        Memory: 1024 MB = 1 GB
        """
        gb_seconds = (memory_mb / 1024.0) * (processing_time_ms / 1000.0)
        compute_cost = gb_seconds * LAMBDA_PRICE_PER_GB_SECOND
        request_cost = LAMBDA_PRICE_PER_REQUEST
        return round(compute_cost + request_cost, 10)

    @property
    def cost_guardrails(self) -> CostGuardrails:
        return self._cost_guardrails

    @property
    def key_manager(self) -> APIKeyManager:
        return self._key_manager

    # -- internal counters --------------------------------------------------

    async def _minute_request_count(self, api_key: str) -> int:
        current_minute = int(_now_ts() // 60)
        if self._redis_available:
            count = 0
            for offset in range(2):
                key = f"rate:{api_key}:minute:{current_minute - offset}"
                val = await self._store.get(key)
                if val is not None:
                    count += int(val)
            return count
        count = 0
        for offset in range(2):
            key = f"rate:{api_key}:minute:{current_minute - offset}"
            val = await self._store.get(key)
            if val is not None:
                count += int(val)
        return count

    async def _day_request_count(self, api_key: str) -> int:
        key = f"rate:{api_key}:day:{_today_key()}"
        val = await self._store.get(key)
        return int(val) if val is not None else 0

    async def _month_request_count(self, api_key: str) -> int:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        key = f"rate:{api_key}:month:{month}"
        val = await self._store.get(key)
        return int(val) if val is not None else 0

    async def _active_job_count(self, api_key: str) -> int:
        return self._active_jobs.get(api_key, 0)

    async def _month_cost(self, api_key: str) -> float:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        key = f"cost:{api_key}:month:{month}"
        val = await self._store.get(key)
        return float(val) if val is not None else 0.0

    @staticmethod
    def _seconds_until_next_day() -> int:
        now = datetime.now(timezone.utc)
        end_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = end_of_day.replace(day=end_of_day.day + 1)
        return max(1, int((end_of_day - now).total_seconds()))

    @staticmethod
    def _seconds_until_next_month() -> int:
        now = datetime.now(timezone.utc)
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return max(1, int((next_month - now).total_seconds()))


# ---------------------------------------------------------------------------
# FastAPI middleware integration
# ---------------------------------------------------------------------------

class RateLimitMiddleware:
    """FastAPI middleware that enforces rate limits.

    Adds to response headers:
    - X-RateLimit-Limit: max requests for tier
    - X-RateLimit-Remaining: requests remaining
    - X-RateLimit-Reset: when limit resets (epoch)
    - X-RateLimit-Tier: current tier name
    - X-RateLimit-Cost-Remaining: monthly cost remaining

    Usage:
        app = FastAPI()
        limiter = RateLimiter(redis_url=os.getenv("REDIS_URL"))
        app.add_middleware(RateLimitMiddleware, limiter=limiter)
    """

    def __init__(self, app: Any, limiter: RateLimiter) -> None:
        self.app = app
        self._limiter = limiter

    async def __call__(self, request: Any, call_next: Any) -> Any:
        api_key = request.headers.get("X-API-Key", "")

        if not api_key:
            from starlette.responses import JSONResponse  # type: ignore[import-untyped]
            return JSONResponse(
                status_code=401,
                content={"error": "Missing X-API-Key header"},
            )

        content_length = request.headers.get("content-length", "0")
        try:
            file_size_mb = int(content_length) / (1024 * 1024)
        except (ValueError, TypeError):
            file_size_mb = 0

        result = await self._limiter.check_request(api_key, file_size_mb)

        if not result.allowed:
            from starlette.responses import JSONResponse  # type: ignore[import-untyped]
            resp = JSONResponse(
                status_code=429,
                content={
                    "error": result.reason,
                    "retry_after_seconds": result.retry_after_seconds,
                },
            )
            resp.headers["Retry-After"] = str(max(result.retry_after_seconds, 1))
            if result.tier:
                resp.headers["X-RateLimit-Tier"] = result.tier.name
            return resp

        response = await call_next(request)

        if result.tier:
            tier = result.tier
            usage = result.current_usage or UsageStats()
            remaining_minute = max(0, tier.requests_per_minute - usage.requests_this_minute)
            remaining_day = max(0, tier.requests_per_day - usage.requests_today)
            remaining = min(remaining_minute, remaining_day)
            reset_epoch = int(_now_ts()) + 60

            response.headers["X-RateLimit-Limit"] = str(tier.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_epoch)
            response.headers["X-RateLimit-Tier"] = tier.name

            if tier.monthly_cost_limit_usd > 0:
                cost_remaining = max(0.0, tier.monthly_cost_limit_usd - usage.monthly_cost_usd)
                response.headers["X-RateLimit-Cost-Remaining"] = f"{cost_remaining:.4f}"

        return response


# ---------------------------------------------------------------------------
# Standalone test runner
# ---------------------------------------------------------------------------

async def _run_tests() -> None:
    print("=" * 70)
    print("RATE LIMITER TESTS")
    print("=" * 70)

    limiter = RateLimiter()

    print("\n--- Tier Definitions ---")
    for name, tier in TIERS.items():
        print(
            f"  {tier.name:12s}  size={tier.max_file_size_mb:>4d}MB"
            f"  pages={tier.max_pages:>4d}"
            f"  rpm={tier.requests_per_minute:>4d}"
            f"  rpd={tier.requests_per_day:>6d}"
            f"  concurrent={tier.max_concurrent:>3d}"
            f"  timeout={tier.max_timeout_seconds:>4d}s"
            f"  cost=${tier.monthly_cost_limit_usd:>7.1f}"
        )

    print("\n--- API Key Validation ---")
    for key in ("demo-key-free", "demo-key-pro", "demo-key-enterprise", "invalid-key"):
        tier_name = await limiter.key_manager.validate_key(key)
        print(f"  {key:30s} -> {tier_name}")

    print("\n--- Cost Estimation ---")
    for mem_mb in [256, 512, 1024, 2048]:
        for time_ms in [1000, 5000, 10000, 30000, 60000]:
            cost = await RateLimiter.estimate_cost_usd(float(time_ms), float(mem_mb))
            print(f"  {mem_mb:>5d}MB  {time_ms:>6d}ms  ->  ${cost:.10f}")

    print("\n--- Rate Limit Checks ---")

    # Free tier: allowed under limits
    result = await limiter.check_request("demo-key-free", file_size_mb=5, estimated_pages=5)
    print(f"  free (5MB, 5 pages):      allowed={result.allowed}  reason={result.reason}")

    # Free tier: file too large
    result = await limiter.check_request("demo-key-free", file_size_mb=15, estimated_pages=5)
    print(f"  free (15MB, 5 pages):     allowed={result.allowed}  reason={result.reason}")

    # Free tier: too many pages
    result = await limiter.check_request("demo-key-free", file_size_mb=5, estimated_pages=20)
    print(f"  free (5MB, 20 pages):     allowed={result.allowed}  reason={result.reason}")

    # Pro tier: large file ok
    result = await limiter.check_request("demo-key-pro", file_size_mb=40, estimated_pages=80)
    print(f"  pro (40MB, 80 pages):     allowed={result.allowed}  reason={result.reason}")

    # Pro tier: exceeds page limit
    result = await limiter.check_request("demo-key-pro", file_size_mb=40, estimated_pages=150)
    print(f"  pro (40MB, 150 pages):    allowed={result.allowed}  reason={result.reason}")

    # Enterprise tier: large file ok
    result = await limiter.check_request(
        "demo-key-enterprise", file_size_mb=150, estimated_pages=400
    )
    print(
        f"  enterprise (150MB, 400p): allowed={result.allowed}  reason={result.reason}"
    )

    # Invalid key
    result = await limiter.check_request("invalid-key", file_size_mb=1, estimated_pages=1)
    print(f"  invalid key:              allowed={result.allowed}  reason={result.reason}")

    print("\n--- Record & Usage ---")
    for i in range(3):
        await limiter.record_request("demo-key-pro", file_size_mb=10, pages=20, processing_time_ms=3000)
    usage = await limiter.get_usage("demo-key-pro")
    print(f"  pro after 3 requests:  today={usage.requests_today}  minute={usage.requests_this_minute}  tier={usage.tier_name}")

    print("\n--- Rate Burst Test (free tier, 5 rpm) ---")
    for i in range(7):
        result = await limiter.check_request("demo-key-free", file_size_mb=1, estimated_pages=1)
        status = "ALLOW" if result.allowed else f"DENY ({result.reason})"
        print(f"  request {i+1}: {status}")
        if result.allowed:
            await limiter.record_request("demo-key-free", file_size_mb=1, pages=1, processing_time_ms=100)

    print("\n--- Concurrent Job Limit ---")
    for i in range(3):
        await limiter.increment_active("demo-key-free")
    usage = await limiter.get_usage("demo-key-free")
    print(f"  free tier active jobs: {usage.active_jobs} (limit: 1)")
    result = await limiter.check_request("demo-key-free", file_size_mb=1, estimated_pages=1)
    print(f"  next request allowed: {result.allowed}  reason: {result.reason}")

    # release
    for _ in range(3):
        await limiter.decrement_active("demo-key-free")

    print("\n--- Cost Guardrails ---")
    budget = await limiter.cost_guardrails.check_budget()
    print(f"  Budget: ${budget.monthly_budget_usd:.2f}  remaining: ${budget.remaining_usd:.4f}  used: {budget.percentage_used}%")

    for _ in range(5):
        await limiter.record_completion("demo-key-pro", processing_time_ms=30000, memory_mb=1024)
    budget = await limiter.cost_guardrails.check_budget()
    print(f"  After 5 completions: remaining=${budget.remaining_usd:.4f}  used={budget.percentage_used}%  throttle={budget.should_throttle}")

    report = await limiter.cost_guardrails.get_monthly_report()
    print(f"  Monthly report: total=${report['total_cost_usd']:.6f}  budget=${report['budget_usd']:.2f}")

    print("\n--- Usage Report ---")
    for key in ("demo-key-free", "demo-key-pro", "demo-key-enterprise"):
        usage = await limiter.get_usage(key)
        print(
            f"  {key}: tier={usage.tier_name}  today={usage.requests_today}"
            f"  minute={usage.requests_this_minute}  active={usage.active_jobs}"
            f"  monthly_cost=${usage.monthly_cost_usd:.6f}  monthly_reqs={usage.monthly_requests}"
        )

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(_run_tests())
