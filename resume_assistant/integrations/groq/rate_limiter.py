"""Proactive Groq rate-limit handling using API response headers."""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Mapping, Optional

logger = logging.getLogger(__name__)

WaitCallback = Callable[[str, str, float, float], None]

_RESET_PATTERN = re.compile(
    r"^(?:(?P<minutes>\d+)m)?(?P<seconds>\d+(?:\.\d+)?)s$", re.IGNORECASE
)


@dataclass
class RateLimitSnapshot:
    """Latest Groq rate-limit counters for one model (from response headers)."""

    model_id: str
    limit_requests: Optional[int] = None
    remaining_requests: Optional[int] = None
    reset_requests_sec: Optional[float] = None
    limit_tokens: Optional[int] = None
    remaining_tokens: Optional[int] = None
    reset_tokens_sec: Optional[float] = None
    updated_at: float = field(default_factory=time.time)

    def requests_usage_ratio(self) -> Optional[float]:
        if self.limit_requests and self.remaining_requests is not None:
            used = self.limit_requests - self.remaining_requests
            return used / self.limit_requests
        return None

    def tokens_usage_ratio(self) -> Optional[float]:
        if self.limit_tokens and self.remaining_tokens is not None:
            used = self.limit_tokens - self.remaining_tokens
            return used / self.limit_tokens
        return None


def parse_groq_reset_seconds(value: Optional[str]) -> Optional[float]:
    """Parse Groq reset headers like ``7.66s`` or ``2m59.56s`` into seconds."""
    if not value or not str(value).strip():
        return None
    text = str(value).strip().lower()
    match = _RESET_PATTERN.match(text)
    if not match:
        try:
            return float(text.rstrip("s"))
        except ValueError:
            return None
    minutes = int(match.group("minutes") or 0)
    seconds = float(match.group("seconds"))
    return minutes * 60 + seconds


def _parse_int_header(headers: Mapping[str, str], key: str) -> Optional[int]:
    raw = headers.get(key)
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


class GroqRateLimiter:
    """
    Tracks per-model limits from Groq headers and sleeps before requests when
    remaining quota is low, to avoid 429 responses.
    """

    def __init__(self) -> None:
        self.min_remaining_requests = int(os.getenv("GROQ_MIN_REMAINING_REQUESTS", "2"))
        self.min_remaining_tokens_ratio = float(
            os.getenv("GROQ_MIN_REMAINING_TOKENS_RATIO", "0.15")
        )
        self.min_interval_sec = float(os.getenv("GROQ_MIN_REQUEST_INTERVAL_SEC", "1.0"))
        self.safety_buffer_sec = float(os.getenv("GROQ_RATE_LIMIT_BUFFER_SEC", "0.5"))
        self.max_wait_sec = float(os.getenv("GROQ_MAX_WAIT_SEC", "120"))
        self._lock = threading.Lock()
        self._per_model: Dict[str, RateLimitSnapshot] = {}
        self._last_request_at: Dict[str, float] = {}
        self._wait_callback: Optional[WaitCallback] = None

    def set_wait_callback(self, callback: Optional[WaitCallback]) -> None:
        self._wait_callback = callback

    def _sleep_with_countdown(
        self,
        model_id: str,
        reason: str,
        seconds: float,
    ) -> None:
        """Sleep in 1s steps so the UI can show a countdown."""
        total = seconds
        remaining = seconds
        tick = 1.0
        while remaining > 0:
            if self._wait_callback:
                self._wait_callback(model_id, reason, remaining, total)
            chunk = min(tick, remaining)
            time.sleep(chunk)
            remaining -= chunk
        if self._wait_callback:
            self._wait_callback(model_id, reason, 0.0, total)

    def _cap_wait(self, delay: float) -> float:
        """Never block the UI longer than GROQ_MAX_WAIT_SEC."""
        if delay <= 0:
            return 0.0
        if delay > self.max_wait_sec:
            logger.warning(
                "Capping Groq wait from %.1fs to %.1fs (GROQ_MAX_WAIT_SEC)",
                delay,
                self.max_wait_sec,
            )
            return self.max_wait_sec
        return delay

    def update_from_headers(self, model_id: str, headers: Mapping[str, str]) -> RateLimitSnapshot:
        """Record limits from a successful (or 429) Groq HTTP response."""
        with self._lock:
            snap = self._per_model.get(model_id) or RateLimitSnapshot(model_id=model_id)
            snap.limit_requests = _parse_int_header(headers, "x-ratelimit-limit-requests")
            snap.remaining_requests = _parse_int_header(
                headers, "x-ratelimit-remaining-requests"
            )
            snap.reset_requests_sec = parse_groq_reset_seconds(
                headers.get("x-ratelimit-reset-requests")
            )
            snap.limit_tokens = _parse_int_header(headers, "x-ratelimit-limit-tokens")
            snap.remaining_tokens = _parse_int_header(
                headers, "x-ratelimit-remaining-tokens"
            )
            snap.reset_tokens_sec = parse_groq_reset_seconds(
                headers.get("x-ratelimit-reset-tokens")
            )
            snap.updated_at = time.time()
            self._per_model[model_id] = snap
            return snap

    def get_snapshot(self, model_id: str) -> Optional[RateLimitSnapshot]:
        with self._lock:
            return self._per_model.get(model_id)

    def get_all_snapshots(self) -> Dict[str, RateLimitSnapshot]:
        with self._lock:
            return dict(self._per_model)

    def wait_before_request(self, model_id: str) -> float:
        """
        Block until it is safe to send the next request for this model.
        Returns seconds slept.
        """
        reason = "min_request_interval"
        with self._lock:
            snap = self._per_model.get(model_id)
            delays: list[tuple[str, float]] = []

            if snap:
                if snap.remaining_requests is not None:
                    low_requests = snap.remaining_requests <= self.min_remaining_requests
                    if low_requests and snap.reset_requests_sec:
                        wait = snap.reset_requests_sec + self.safety_buffer_sec
                        delays.append(("low_daily_requests", wait))
                        logger.info(
                            "Groq %s: low request quota (%s left), waiting %.1fs",
                            model_id,
                            snap.remaining_requests,
                            wait,
                        )

                if snap.remaining_tokens is not None and snap.limit_tokens:
                    token_ratio = snap.remaining_tokens / snap.limit_tokens
                    if token_ratio <= self.min_remaining_tokens_ratio:
                        token_wait = (snap.reset_tokens_sec or 10.0) + self.safety_buffer_sec
                        delays.append(("low_tokens_per_minute", token_wait))
                        logger.info(
                            "Groq %s: low token quota (%s/%s), waiting %.1fs",
                            model_id,
                            snap.remaining_tokens,
                            snap.limit_tokens,
                            token_wait,
                        )

            last_at = self._last_request_at.get(model_id, 0.0)
            since_last = time.time() - last_at
            if since_last < self.min_interval_sec:
                delays.append(
                    ("min_request_interval", self.min_interval_sec - since_last)
                )

        if delays:
            reason, raw_delay = max(delays, key=lambda item: item[1])
        else:
            raw_delay = 0.0

        sleep_for = self._cap_wait(raw_delay)
        if sleep_for > 0:
            self._sleep_with_countdown(model_id, reason, sleep_for)
        with self._lock:
            self._last_request_at[model_id] = time.time()
        return sleep_for

    def wait_after_429(
        self,
        model_id: str,
        headers: Mapping[str, str],
        *,
        sleep: bool = True,
    ) -> float:
        """Wait after HTTP 429; uses retry-after or reset headers."""
        self.update_from_headers(model_id, headers)
        retry_after = headers.get("retry-after") or headers.get("Retry-After")
        delay: float
        if retry_after:
            try:
                delay = float(retry_after) + self.safety_buffer_sec
            except ValueError:
                delay = self._default_429_delay(model_id)
        else:
            delay = self._default_429_delay(model_id)

        if not sleep:
            logger.warning(
                "Groq 429 for %s — not waiting (probe/no-sleep); reset in ~%.1fs",
                model_id,
                delay,
            )
            return delay

        delay = self._cap_wait(delay)
        logger.warning("Groq 429 for %s — waiting %.1fs", model_id, delay)
        self._sleep_with_countdown(model_id, "rate_limit_429", delay)
        return delay

    def _default_429_delay(self, model_id: str) -> float:
        snap = self._per_model.get(model_id)
        if snap and snap.reset_requests_sec:
            return snap.reset_requests_sec + self.safety_buffer_sec
        if snap and snap.reset_tokens_sec:
            return snap.reset_tokens_sec + self.safety_buffer_sec
        return float(os.getenv("GROQ_RETRY_DELAY_SEC", "10"))
