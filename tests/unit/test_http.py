from collections.abc import Callable, Iterator
from datetime import UTC, datetime

import httpx
import pytest

from finhak.ingest.http import (
    DEFAULT_USER_AGENT,
    FetchError,
    PoliteClient,
    RateLimiter,
    ResponseTooLarge,
    RobotsDisallowed,
    RobotsUnavailable,
)

pytestmark = pytest.mark.unit

FIXED_NOW = datetime(2026, 10, 23, 13, 0, tzinfo=UTC)
HOST = "https://www.mevzuat.gov.tr"
MEVZUAT_ROBOTS = "User-agent: Googlebot\nNoindex:/MevzuatMetin/1.5.7354.pdf\n"
INTERVAL = 1.1

Handler = Callable[[httpx.Request], httpx.Response]


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _client(
    handler: Handler,
    clock: FakeClock,
    user_agent: str = "finhak-test/0.1",
    max_bytes: int = 1_000_000,
) -> PoliteClient:
    return PoliteClient(
        transport=httpx.MockTransport(handler),
        limiter=RateLimiter(INTERVAL, clock=clock.monotonic, sleep=clock.sleep),
        sleep=clock.sleep,
        clock=clock.monotonic,
        now=lambda: FIXED_NOW,
        user_agent=user_agent,
        max_bytes=max_bytes,
    )


def _with_robots(robots: str, inner: Handler) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots)
        return inner(request)

    return handler


def _ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text="ok")


# --- RateLimiter -----------------------------------------------------------------


def test_first_request_to_a_host_does_not_wait() -> None:
    clock = FakeClock()
    limiter = RateLimiter(INTERVAL, clock=clock.monotonic, sleep=clock.sleep)

    limiter.wait("www.mevzuat.gov.tr")

    assert clock.sleeps == []


def test_second_request_waits_for_the_remaining_interval() -> None:
    clock = FakeClock()
    limiter = RateLimiter(INTERVAL, clock=clock.monotonic, sleep=clock.sleep)

    limiter.wait("www.mevzuat.gov.tr")
    clock.now += 0.3
    limiter.wait("www.mevzuat.gov.tr")

    assert clock.sleeps == [pytest.approx(0.8)]


def test_hosts_are_limited_independently() -> None:
    clock = FakeClock()
    limiter = RateLimiter(INTERVAL, clock=clock.monotonic, sleep=clock.sleep)

    limiter.wait("www.mevzuat.gov.tr")
    limiter.wait("www.bddk.org.tr")

    assert clock.sleeps == []


def test_no_wait_once_the_interval_has_elapsed() -> None:
    clock = FakeClock()
    limiter = RateLimiter(INTERVAL, clock=clock.monotonic, sleep=clock.sleep)

    limiter.wait("www.mevzuat.gov.tr")
    clock.now += 5
    limiter.wait("www.mevzuat.gov.tr")

    assert clock.sleeps == []


def test_slow_down_raises_the_interval_for_one_host_only() -> None:
    clock = FakeClock()
    limiter = RateLimiter(INTERVAL, clock=clock.monotonic, sleep=clock.sleep)

    limiter.slow_down("www.mevzuat.gov.tr", 5.0)
    limiter.wait("www.mevzuat.gov.tr")
    limiter.wait("www.mevzuat.gov.tr")
    limiter.wait("www.bddk.org.tr")
    limiter.wait("www.bddk.org.tr")

    assert clock.sleeps == [pytest.approx(5.0), pytest.approx(INTERVAL)]


def test_slow_down_never_goes_below_the_minimum() -> None:
    clock = FakeClock()
    limiter = RateLimiter(INTERVAL, clock=clock.monotonic, sleep=clock.sleep)

    limiter.slow_down("www.mevzuat.gov.tr", 0.1)
    limiter.wait("www.mevzuat.gov.tr")
    limiter.wait("www.mevzuat.gov.tr")

    assert clock.sleeps == [pytest.approx(INTERVAL)]


@pytest.mark.parametrize("interval", [0.5, 0.0, -1.0, float("nan"), float("inf")])
def test_unsafe_intervals_are_rejected(interval: float) -> None:
    with pytest.raises(ValueError, match="1 request per second"):
        RateLimiter(interval)


# --- PoliteClient: basics ------------------------------------------------------------


def test_get_returns_content_and_sends_our_headers() -> None:
    seen: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=MEVZUAT_ROBOTS)
        return httpx.Response(200, content=b"%PDF-1.7", headers={"content-type": "application/pdf"})

    result = _client(handler, FakeClock()).get(f"{HOST}/MevzuatMetin/1.5.6502.pdf")

    assert result.content == b"%PDF-1.7"
    assert result.status == 200
    assert result.content_type == "application/pdf"
    assert result.fetched_at == FIXED_NOW
    assert [h["user-agent"] for h in seen] == ["finhak-test/0.1", "finhak-test/0.1"]
    # Compressed bodies cannot be size-checked before decompression, so ask for none.
    assert all(h["accept-encoding"] == "identity" for h in seen)


def test_consecutive_requests_are_spaced_by_the_rate_limiter() -> None:
    clock = FakeClock()
    client = _client(_with_robots(MEVZUAT_ROBOTS, _ok), clock)

    client.get(f"{HOST}/a")
    client.get(f"{HOST}/b")

    # robots.txt, /a and /b: two waits of the full interval, no request is back-to-back.
    assert clock.sleeps == [pytest.approx(INTERVAL), pytest.approx(INTERVAL)]
    assert client.request_count == 3


@pytest.mark.parametrize(
    "url",
    [
        "http://www.mevzuat.gov.tr/a",
        "file:///etc/passwd",
        "https://evil.example/a",
        "https://mevzuat.gov.tr/a",
        "https://www.mevzuat.gov.tr:8443/a",
    ],
)
def test_only_https_on_allowed_hosts_is_fetched(url: str) -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, text="ok")

    with pytest.raises(FetchError, match="not allowed"):
        _client(handler, FakeClock()).get(url)

    assert requested == []


# --- robots.txt ------------------------------------------------------------------


def test_robots_is_fetched_once_per_host() -> None:
    robots_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal robots_calls
        if request.url.path == "/robots.txt":
            robots_calls += 1
            return httpx.Response(200, text=MEVZUAT_ROBOTS)
        return httpx.Response(200, text="ok")

    client = _client(handler, FakeClock())

    client.get(f"{HOST}/a")
    client.get(f"{HOST}/b")

    assert robots_calls == 1


def test_path_disallowed_for_everyone_is_never_requested() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")

    with pytest.raises(RobotsDisallowed):
        _client(handler, FakeClock()).get(f"{HOST}/private/doc.pdf")

    assert requested == ["/robots.txt"]


def test_robots_group_for_our_product_token_applies_with_the_default_user_agent() -> None:
    robots = "User-agent: finhak\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
    client = _client(_with_robots(robots, _ok), FakeClock(), user_agent=DEFAULT_USER_AGENT)

    with pytest.raises(RobotsDisallowed):
        client.get(f"{HOST}/a")


def test_crawl_delay_slows_down_that_host() -> None:
    clock = FakeClock()
    client = _client(_with_robots("User-agent: *\nCrawl-delay: 3\n", _ok), clock)

    client.get(f"{HOST}/a")
    client.get(f"{HOST}/b")

    assert clock.sleeps == [pytest.approx(3.0), pytest.approx(3.0)]


def test_robots_redirect_on_the_same_host_is_followed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(301, headers={"location": "/robots-v2.txt"})
        if request.url.path == "/robots-v2.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /a\n")
        return httpx.Response(200, text="ok")

    with pytest.raises(RobotsDisallowed):
        _client(handler, FakeClock()).get(f"{HOST}/a")


def test_missing_robots_file_allows_crawling() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404, text="not found")
        return httpx.Response(200, text="ok")

    assert _client(handler, FakeClock()).get(f"{HOST}/Mevzuat/Liste/49").content == b"ok"


@pytest.mark.parametrize("status", [401, 403])
def test_robots_behind_authentication_disallows_everything(status: int) -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        return httpx.Response(status)

    with pytest.raises(RobotsDisallowed):
        _client(handler, FakeClock()).get(f"{HOST}/a")

    assert requested == ["/robots.txt"]


@pytest.mark.parametrize("status", [500, 501])
def test_robots_server_error_stops_crawling_that_host(status: int) -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        return httpx.Response(status, text="error")

    with pytest.raises(RobotsUnavailable):
        _client(handler, FakeClock()).get(f"{HOST}/a")

    assert set(requested) == {"/robots.txt"}


# --- retries -----------------------------------------------------------------------


def test_server_errors_are_retried_with_exponential_backoff() -> None:
    clock = FakeClock()
    responses = iter([503, 503, 200])
    client = _client(_with_robots(MEVZUAT_ROBOTS, lambda r: httpx.Response(next(responses))), clock)

    result = client.get(f"{HOST}/a")

    assert result.status == 200
    # One limiter wait before the first attempt, then backoff of 2 s and 4 s (which already
    # exceed the interval, so the limiter does not add waits of its own).
    assert clock.sleeps == [pytest.approx(INTERVAL), 2.0, 4.0]


def test_retry_after_header_is_honoured_on_429() -> None:
    clock = FakeClock()
    responses = iter(
        [httpx.Response(429, headers={"retry-after": "7"}), httpx.Response(200, text="ok")]
    )
    client = _client(_with_robots(MEVZUAT_ROBOTS, lambda r: next(responses)), clock)

    client.get(f"{HOST}/a")

    assert clock.sleeps == [pytest.approx(INTERVAL), 7.0]


@pytest.mark.parametrize("value", ["nan", "inf", "-5", "soon"])
def test_unusable_retry_after_falls_back_to_backoff(value: str) -> None:
    clock = FakeClock()
    responses = iter(
        [httpx.Response(503, headers={"retry-after": value}), httpx.Response(200, text="ok")]
    )
    client = _client(_with_robots(MEVZUAT_ROBOTS, lambda r: next(responses)), clock)

    client.get(f"{HOST}/a")

    assert clock.sleeps == [pytest.approx(INTERVAL), 2.0]


def test_retries_give_up_after_max_attempts() -> None:
    client = _client(
        _with_robots(MEVZUAT_ROBOTS, lambda r: httpx.Response(503, text="down")), FakeClock()
    )

    with pytest.raises(FetchError, match="503"):
        client.get(f"{HOST}/a")


def test_client_errors_fail_immediately_without_retry() -> None:
    attempts = 0

    def inner(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(404, text="missing")

    with pytest.raises(FetchError, match="404"):
        _client(_with_robots(MEVZUAT_ROBOTS, inner), FakeClock()).get(f"{HOST}/missing")

    assert attempts == 1


def test_transport_errors_are_retried() -> None:
    calls = 0

    def inner(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectTimeout("timed out", request=request)
        return httpx.Response(200, text="ok")

    client = _client(_with_robots(MEVZUAT_ROBOTS, inner), FakeClock())

    assert client.get(f"{HOST}/a").content == b"ok"
    assert calls == 2


def test_decoding_errors_become_fetch_errors() -> None:
    def inner(request: httpx.Request) -> httpx.Response:
        raise httpx.DecodingError("bad gzip", request=request)

    with pytest.raises(FetchError, match="DecodingError"):
        _client(_with_robots(MEVZUAT_ROBOTS, inner), FakeClock()).get(f"{HOST}/a")


# --- redirects ---------------------------------------------------------------------


def test_redirects_are_followed_through_the_rate_limiter() -> None:
    def inner(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/old":
            return httpx.Response(302, headers={"location": "/new"})
        return httpx.Response(200, text="moved here")

    client = _client(_with_robots(MEVZUAT_ROBOTS, inner), FakeClock())

    result = client.get(f"{HOST}/old")

    assert result.url == f"{HOST}/new"
    assert result.content == b"moved here"
    assert client.request_count == 3


def test_redirect_to_another_host_is_refused() -> None:
    requested: list[str] = []

    def inner(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://169.254.169.254/latest"})

    with pytest.raises(FetchError, match="not allowed"):
        _client(_with_robots(MEVZUAT_ROBOTS, inner), FakeClock()).get(f"{HOST}/old")

    assert requested == [f"{HOST}/old"]


def test_redirect_to_another_allowed_host_is_refused_too() -> None:
    def inner(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://www.tcmb.gov.tr/x.pdf"})

    with pytest.raises(FetchError, match="leaves"):
        _client(_with_robots(MEVZUAT_ROBOTS, inner), FakeClock()).get(f"{HOST}/old")


def test_redirect_loops_are_cut_off() -> None:
    client = _client(
        _with_robots(
            MEVZUAT_ROBOTS, lambda r: httpx.Response(302, headers={"location": r.url.path})
        ),
        FakeClock(),
    )

    with pytest.raises(FetchError, match="redirect"):
        client.get(f"{HOST}/loop")


# --- size limits -------------------------------------------------------------------


def test_declared_oversized_body_is_refused() -> None:
    client = _client(
        _with_robots(MEVZUAT_ROBOTS, lambda r: httpx.Response(200, content=b"x" * 2_000)),
        FakeClock(),
        max_bytes=1_000,
    )

    with pytest.raises(ResponseTooLarge):
        client.get(f"{HOST}/big")


def test_streamed_body_without_length_is_cut_off_at_the_limit() -> None:
    def chunks() -> Iterator[bytes]:
        yield b"x" * 600
        yield b"x" * 600

    client = _client(
        _with_robots(MEVZUAT_ROBOTS, lambda r: httpx.Response(200, content=chunks())),
        FakeClock(),
        max_bytes=1_000,
    )

    with pytest.raises(ResponseTooLarge):
        client.get(f"{HOST}/stream")
