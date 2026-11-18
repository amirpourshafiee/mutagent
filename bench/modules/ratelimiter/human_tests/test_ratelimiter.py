import pytest
from ratelimiter import RateLimiter


def test_starts_full_and_drains():
    r = RateLimiter(2, 1.0)
    assert r.allow(0.0) and r.allow(0.0)
    assert not r.allow(0.0)


def test_refill_over_time_and_cap():
    r = RateLimiter(2, 1.0)
    r.allow(0.0, 2)
    assert r.tokens(1.0) == pytest.approx(1.0)
    assert r.tokens(100.0) == pytest.approx(2.0)


def test_denied_request_takes_nothing():
    r = RateLimiter(3, 0.0)
    assert not r.allow(0.0, 4)
    assert r.tokens(0.0) == pytest.approx(3.0)


@pytest.mark.parametrize("args", [(0, 1.0), (-1, 1.0), (1, -0.5)])
def test_bad_constructor_args(args):
    with pytest.raises(ValueError):
        RateLimiter(*args)


def test_bad_cost_and_time_going_backwards():
    r = RateLimiter(2, 1.0)
    with pytest.raises(ValueError):
        r.allow(0.0, 0)
    r.allow(5.0)
    with pytest.raises(ValueError):
        r.allow(4.0)
