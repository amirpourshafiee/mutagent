# RateLimiter spec

A token bucket. It starts full with `capacity` tokens and refills continuously at
`refill_per_sec` tokens per second, never exceeding `capacity`.

- `RateLimiter(capacity, refill_per_sec)`: `capacity` must be > 0 and `refill_per_sec` >= 0,
  otherwise `ValueError`.
- `allow(now, cost=1)`: refills based on time since the previous call, then takes `cost`
  tokens if enough are available and returns True; otherwise takes nothing and returns False.
  `cost` must be > 0, otherwise `ValueError`.
- `tokens(now)`: refills, then returns the current token count as a float.
- `now` is seconds as a float. It must never go backwards between calls, otherwise `ValueError`.
- The first call sets the reference time; no refill happens before it.
