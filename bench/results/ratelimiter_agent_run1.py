import pytest

from ratelimiter import RateLimiter


def test_starts_full():
    rl = RateLimiter(5, 1)
    assert rl.tokens(0.0) == 5.0


def test_invalid_capacity():
    with pytest.raises(ValueError):
        RateLimiter(0, 1)
    with pytest.raises(ValueError):
        RateLimiter(-3, 1)


def test_invalid_capacity_message():
    with pytest.raises(ValueError, match=r"^capacity must be positive$"):
        RateLimiter(0, 1)
    with pytest.raises(ValueError, match=r"^capacity must be positive$"):
        RateLimiter(-3, 1)


def test_invalid_refill():
    with pytest.raises(ValueError):
        RateLimiter(5, -0.5)


def test_invalid_refill_message():
    with pytest.raises(ValueError, match=r"^refill_per_sec must be non-negative$"):
        RateLimiter(5, -0.5)


def test_zero_refill_allowed_and_never_refills():
    rl = RateLimiter(2, 0)
    assert rl.allow(0.0) is True
    assert rl.allow(0.0) is True
    assert rl.allow(1000.0) is False
    assert rl.tokens(2000.0) == 0.0


def test_allow_consumes_until_empty():
    rl = RateLimiter(5, 1)
    for _ in range(5):
        assert rl.allow(0.0) is True
    assert rl.allow(0.0) is False


def test_failed_allow_takes_nothing():
    rl = RateLimiter(3, 1)
    assert rl.allow(0.0, cost=5) is False
    assert rl.tokens(0.0) == 3.0


def test_cost_equal_to_available_is_allowed():
    rl = RateLimiter(3, 1)
    assert rl.allow(0.0, cost=3) is True
    assert rl.tokens(0.0) == 0.0


def test_cost_multiple_tokens():
    rl = RateLimiter(10, 1)
    assert rl.allow(0.0, cost=4) is True
    assert rl.tokens(0.0) == 6.0
    assert rl.allow(0.0, cost=7) is False
    assert rl.tokens(0.0) == 6.0


def test_invalid_cost():
    rl = RateLimiter(5, 1)
    with pytest.raises(ValueError):
        rl.allow(0.0, cost=0)
    with pytest.raises(ValueError):
        rl.allow(0.0, cost=-1)


def test_invalid_cost_message():
    rl = RateLimiter(5, 1)
    with pytest.raises(ValueError, match=r"^cost must be positive$"):
        rl.allow(0.0, cost=0)
    with pytest.raises(ValueError, match=r"^cost must be positive$"):
        rl.allow(0.0, cost=-1)


def test_refill_over_time():
    rl = RateLimiter(4, 2)
    assert rl.allow(0.0, cost=4) is True
    assert rl.tokens(0.0) == 0.0
    assert rl.tokens(1.0) == 2.0
    assert rl.tokens(1.5) == 3.0


def test_refill_capped_at_capacity():
    rl = RateLimiter(4, 2)
    assert rl.allow(0.0, cost=1) is True
    assert rl.tokens(100.0) == 4.0


def test_fractional_refill():
    rl = RateLimiter(1, 1)
    assert rl.allow(0.0) is True
    assert rl.allow(0.5) is False
    assert rl.tokens(0.5) == 0.5
    assert rl.allow(1.0) is True


def test_first_call_sets_reference_no_refill():
    rl = RateLimiter(5, 10)
    assert rl.tokens(1000.0) == 5.0
    assert rl.allow(1000.0, cost=5) is True
    assert rl.tokens(1000.0) == 0.0
    assert rl.tokens(1000.25) == 2.5


def test_first_call_with_large_time_via_allow():
    rl = RateLimiter(2, 1)
    assert rl.allow(500.0) is True
    assert rl.tokens(500.0) == 1.0


def test_time_backwards_raises_in_allow():
    rl = RateLimiter(5, 1)
    rl.allow(10.0)
    with pytest.raises(ValueError):
        rl.allow(9.0)


def test_time_backwards_raises_in_tokens():
    rl = RateLimiter(5, 1)
    rl.tokens(10.0)
    with pytest.raises(ValueError):
        rl.tokens(9.99)


def test_time_backwards_message_in_allow():
    rl = RateLimiter(5, 1)
    rl.allow(10.0)
    with pytest.raises(ValueError, match=r"^time went backwards$"):
        rl.allow(9.0)


def test_time_backwards_message_in_tokens():
    rl = RateLimiter(5, 1)
    rl.tokens(10.0)
    with pytest.raises(ValueError, match=r"^time went backwards$"):
        rl.tokens(9.99)


def test_same_time_is_fine():
    rl = RateLimiter(5, 1)
    rl.tokens(10.0)
    assert rl.tokens(10.0) == 5.0


def test_tokens_refill_is_cumulative_across_calls():
    rl = RateLimiter(10, 1)
    assert rl.allow(0.0, cost=10) is True
    assert rl.tokens(2.0) == 2.0
    assert rl.tokens(5.0) == 5.0
