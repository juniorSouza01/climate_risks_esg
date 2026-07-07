from __future__ import annotations

import threading
import time
from typing import Any

import httpx
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from climate_esg.logging import get_logger

log = get_logger(__name__)

USER_AGENT = "climate-esg-platform/0.1 (+ingestion)"

DEFAULT_TIMEOUTS: dict[str, float] = {
    "adaptabrasil": 90.0,
    "ibge": 90.0,
    "brapi": 20.0,
    "gdelt": 20.0,
    "nominatim": 30.0,
    "brasilapi": 30.0,
    "compras_gov": 20.0,
}
FALLBACK_TIMEOUT = 30.0
MAX_RETRY_AFTER_S = 60.0

_client: httpx.Client | None = None
_client_lock = threading.Lock()


class TransientHTTPError(httpx.HTTPStatusError):
    pass


class NonJSONResponseError(RuntimeError):
    pass


def get_client() -> httpx.Client:
    global _client
    with _client_lock:
        if _client is None or _client.is_closed:
            _client = httpx.Client(
                headers={"User-Agent": USER_AGENT},
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return _client


def close_client() -> None:
    global _client
    with _client_lock:
        if _client is not None and not _client.is_closed:
            _client.close()
        _client = None


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def _log_failure(
    source: str,
    status_code: int | None,
    latency_ms: float,
    attempt: int,
    **extra: Any,
) -> None:
    log.warning(
        "http.request.failed",
        source=source,
        status_code=status_code,
        latency_ms=latency_ms,
        attempt=attempt,
        **extra,
    )


def _attempt_request(
    source: str,
    url: str,
    params: dict[str, Any] | None,
    headers: dict[str, str] | None,
    timeout: float,
    attempt: int,
) -> Any:
    start = time.monotonic()
    try:
        resp = get_client().get(url, params=params, headers=headers, timeout=timeout)
    except httpx.TransportError as exc:
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        _log_failure(source, None, latency_ms, attempt, error=str(exc))
        raise
    latency_ms = round((time.monotonic() - start) * 1000, 1)
    status = resp.status_code

    if status == 429 or status >= 500:
        _log_failure(source, status, latency_ms, attempt)
        if status == 429:
            retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
            if retry_after:
                time.sleep(min(retry_after, MAX_RETRY_AFTER_S))
        raise TransientHTTPError(
            f"{source}: HTTP {status}", request=resp.request, response=resp
        )

    if 400 <= status < 500:
        _log_failure(source, status, latency_ms, attempt)
        resp.raise_for_status()

    if status == 204 or not resp.content:
        return None

    try:
        return resp.json()
    except ValueError as exc:
        _log_failure(
            source,
            status,
            latency_ms,
            attempt,
            content_type=resp.headers.get("content-type", ""),
            error="non-json body",
        )
        raise NonJSONResponseError(f"{source}: resposta não-JSON (HTTP {status})") from exc


def request_json(
    source: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
) -> Any:
    effective_timeout = timeout if timeout is not None else DEFAULT_TIMEOUTS.get(
        source, FALLBACK_TIMEOUT
    )
    retryer = Retrying(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1.0, max=30.0),
        retry=retry_if_exception_type((httpx.TransportError, TransientHTTPError)),
    )
    result: Any = None
    for attempt in retryer:
        with attempt:
            result = _attempt_request(
                source,
                url,
                params,
                headers,
                effective_timeout,
                attempt.retry_state.attempt_number,
            )
    return result
