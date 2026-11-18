"""Token-bucket rate limiter. Time is passed in, so behavior is deterministic."""


class RateLimiter:
    def __init__(self, capacity: int, refill_per_sec: float) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_per_sec < 0:
            raise ValueError("refill_per_sec must be non-negative")
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec
        self._tokens = float(capacity)
        self._last = None

    def _refill(self, now: float) -> None:
        if self._last is not None:
            if now < self._last:
                raise ValueError("time went backwards")
            elapsed = now - self._last
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_per_sec)
        self._last = now

    def allow(self, now: float, cost: int = 1) -> bool:
        if cost <= 0:
            raise ValueError("cost must be positive")
        self._refill(now)
        if cost > self._tokens:
            return False
        self._tokens -= cost
        return True

    def tokens(self, now: float) -> float:
        self._refill(now)
        return self._tokens
