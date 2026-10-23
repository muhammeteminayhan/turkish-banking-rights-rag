"""A polite HTTP client: host allowlist, per-host rate limit, robots.txt, bounded retries.

The project brief caps crawling at one request per second per site. Every request,
including robots.txt, retries and redirect hops, goes through the same limiter, and every
hop must stay on an allowed https host. Bodies are streamed with a size cap and a deadline.
"""

import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

MIN_ALLOWED_INTERVAL = 1.0
ROBOTS_PRODUCT_TOKEN = "finhak"
DEFAULT_USER_AGENT = (
    f"Mozilla/5.0 (compatible; {ROBOTS_PRODUCT_TOKEN}/0.1; portfolio research on public law texts)"
)
# mevzuat.gov.tr for legislation; www.tcmb.gov.tr for texts TCMB publishes only itself.
DEFAULT_ALLOWED_HOSTS = frozenset({"www.mevzuat.gov.tr", "www.tcmb.gov.tr"})
DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=15.0)
MAX_RESPONSE_BYTES = 50 * 1024 * 1024  # the largest file in the corpus is about 1 MB
MAX_ROBOTS_BYTES = 512 * 1024
REQUEST_DEADLINE_SECONDS = 180.0
MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 2.0
MAX_RETRY_AFTER_SECONDS = 60.0
MAX_REDIRECTS = 3
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
REDIRECT_STATUS = frozenset({301, 302, 303, 307, 308})


class FetchError(RuntimeError):
    """A URL could not be fetched."""


class RobotsDisallowed(FetchError):
    """robots.txt forbids fetching this URL."""


class RobotsUnavailable(FetchError):
    """robots.txt could not be read, so the host is not crawled."""


class ResponseTooLarge(FetchError):
    """The body exceeded the size cap."""


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int
    content: bytes
    content_type: str | None
    fetched_at: datetime


@dataclass(frozen=True)
class _RawResponse:
    status: int
    headers: httpx.Headers
    content: bytes


class RateLimiter:
    """Blocks until enough time passed since the last request to the same host."""

    def __init__(
        self,
        min_interval: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not (math.isfinite(min_interval) and min_interval >= MIN_ALLOWED_INTERVAL):
            raise ValueError("min_interval must keep crawling at or below 1 request per second")
        self._min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._host_interval: dict[str, float] = {}
        self._last_request: dict[str, float] = {}

    def slow_down(self, host: str, interval: float) -> None:
        """Use a longer interval for one host (robots.txt Crawl-delay); never a shorter one."""
        if math.isfinite(interval):
            self._host_interval[host] = max(self._min_interval, interval)

    def wait(self, host: str) -> None:
        last = self._last_request.get(host)
        if last is not None:
            interval = self._host_interval.get(host, self._min_interval)
            remaining = interval - (self._clock() - last)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request[host] = self._clock()


class PoliteClient:
    def __init__(
        self,
        limiter: RateLimiter,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        user_agent: str = DEFAULT_USER_AGENT,
        robots_token: str = ROBOTS_PRODUCT_TOKEN,
        allowed_hosts: frozenset[str] = DEFAULT_ALLOWED_HOSTS,
        max_bytes: int = MAX_RESPONSE_BYTES,
    ) -> None:
        self._limiter = limiter
        self._sleep = sleep
        self._clock = clock
        self._now = now
        self._robots_token = robots_token
        self._allowed_hosts = allowed_hosts
        self._max_bytes = max_bytes
        self._http = httpx.Client(
            transport=transport,
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=False,
            # A compressed body cannot be size-checked before it is inflated.
            headers={"User-Agent": user_agent, "Accept-Encoding": "identity"},
        )
        self._robots: dict[str, RobotFileParser] = {}
        self.request_count = 0

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "PoliteClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def get(self, url: str) -> FetchResult:
        """Fetch a URL that robots.txt allows; any non-200 final status is an error."""
        final_url, response = self._follow(url, self._max_bytes, check_robots=True)
        if response.status != 200:
            raise FetchError(f"{final_url}: HTTP {response.status}")
        return FetchResult(
            url=final_url,
            status=response.status,
            content=response.content,
            content_type=response.headers.get("content-type"),
            fetched_at=self._now(),
        )

    def _follow(self, url: str, max_bytes: int, check_robots: bool) -> tuple[str, _RawResponse]:
        current = url
        start_host = urlsplit(url).hostname
        for _ in range(MAX_REDIRECTS + 1):
            self._check_url(current)
            if urlsplit(current).hostname != start_host:
                raise FetchError(f"{current}: redirect leaves {start_host}")
            if check_robots:
                self._check_robots(current)
            response = self._get_with_retries(current, max_bytes)
            if response.status not in REDIRECT_STATUS:
                return current, response
            location = response.headers.get("location")
            if not location:
                raise FetchError(f"{current}: redirect without a Location header")
            current = urljoin(current, location)
        raise FetchError(f"{url}: more than {MAX_REDIRECTS} redirects")

    def _check_url(self, url: str) -> None:
        parts = urlsplit(url)
        try:
            port = parts.port
        except ValueError as exc:
            raise FetchError(f"{url}: invalid port") from exc
        if (
            parts.scheme != "https"
            or parts.hostname not in self._allowed_hosts
            or port not in (None, 443)
        ):
            raise FetchError(f"{url}: not allowed (https on {sorted(self._allowed_hosts)} only)")

    def _check_robots(self, url: str) -> None:
        host = urlsplit(url).hostname or ""
        parser = self._robots.get(host)
        if parser is None:
            parser = self._load_robots(host)
            self._robots[host] = parser
        if not parser.can_fetch(self._robots_token, url):
            raise RobotsDisallowed(f"{url}: disallowed by robots.txt")

    def _load_robots(self, host: str) -> RobotFileParser:
        robots_url = f"https://{host}/robots.txt"
        parser = RobotFileParser(robots_url)
        try:
            _, response = self._follow(robots_url, MAX_ROBOTS_BYTES, check_robots=False)
        except FetchError as exc:
            raise RobotsUnavailable(f"{robots_url}: {exc}") from exc

        status = response.status
        if status == 200:
            parser.parse(response.content.decode("utf-8", errors="replace").splitlines())
        elif status in (401, 403):
            parser.parse(["User-agent: *", "Disallow: /"])
        elif 400 <= status < 500:
            # No robots.txt means no restrictions (RFC 9309, section 2.3.1.3).
            parser.parse([])
        else:
            raise RobotsUnavailable(f"{robots_url}: HTTP {status}")

        delay = parser.crawl_delay(self._robots_token)
        if delay is not None:
            self._limiter.slow_down(host, float(delay))
        logger.info("robots.txt for %s: HTTP %s, crawl-delay %s", host, status, delay)
        return parser

    def _get_with_retries(self, url: str, max_bytes: int) -> _RawResponse:
        host = urlsplit(url).hostname or ""
        last_problem = ""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._limiter.wait(host)
            self.request_count += 1
            retry_after: float | None = None
            try:
                response = self._read(url, max_bytes)
            except httpx.TransportError as exc:
                last_problem = f"{type(exc).__name__}: {exc}"
            except (httpx.RequestError, httpx.InvalidURL) as exc:
                raise FetchError(f"{url}: {type(exc).__name__}: {exc}") from exc
            else:
                if response.status not in RETRYABLE_STATUS:
                    return response
                last_problem = f"HTTP {response.status}"
                retry_after = _retry_after_seconds(response.headers)
            if attempt < MAX_ATTEMPTS:
                delay = retry_after or BACKOFF_BASE_SECONDS * 2 ** (attempt - 1)
                logger.warning("%s: %s, retrying in %.1fs", url, last_problem, delay)
                self._sleep(delay)
        raise FetchError(f"{url}: {last_problem} after {MAX_ATTEMPTS} attempts")

    def _read(self, url: str, max_bytes: int) -> _RawResponse:
        deadline = self._clock() + REQUEST_DEADLINE_SECONDS
        with self._http.stream("GET", url) as response:
            declared = response.headers.get("content-length", "")
            if declared.isdigit() and int(declared) > max_bytes:
                raise ResponseTooLarge(f"{url}: declares {declared} bytes (cap {max_bytes})")
            chunks: list[bytes] = []
            received = 0
            for chunk in response.iter_bytes():
                received += len(chunk)
                if received > max_bytes:
                    raise ResponseTooLarge(f"{url}: more than {max_bytes} bytes")
                if self._clock() > deadline:
                    raise FetchError(f"{url}: no complete response in {REQUEST_DEADLINE_SECONDS}s")
                chunks.append(chunk)
            return _RawResponse(response.status_code, response.headers, b"".join(chunks))


def _retry_after_seconds(headers: httpx.Headers) -> float | None:
    try:
        seconds = float(headers.get("retry-after", ""))
    except ValueError:
        return None
    if not math.isfinite(seconds) or seconds <= 0:
        return None
    return min(seconds, MAX_RETRY_AFTER_SECONDS)
