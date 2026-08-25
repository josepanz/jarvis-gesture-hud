"""ForegroundApplicationTracker (TASK-027, spec.md #23/apply.md #17).

"Detection is cached/throttled if required" - querying the OS for the foreground
window on every camera frame (30-60Hz) would be wasteful and, on some platforms
(macOS/Linux via subprocess), slow enough to matter. This wraps any zero-arg
detector callable (defaults to `CrossPlatformOS.foreground_window_title`) with a
time-based cache, and never lets a detector failure raise past it either -
defense in depth on top of `foreground_window_title()` already catching its own.
"""

import time

from jarvis.os_native import CrossPlatformOS

DEFAULT_CACHE_TTL_SECONDS = 0.5


class ForegroundApplicationTracker:
    def __init__(self, detector=None, cache_ttl=DEFAULT_CACHE_TTL_SECONDS, clock=time.monotonic):
        self._detector = detector or CrossPlatformOS.foreground_window_title
        self._cache_ttl = cache_ttl
        self._clock = clock
        self._cached_title = None
        self._cached_at = None

    def get(self):
        now = self._clock()
        if self._cached_at is None or (now - self._cached_at) >= self._cache_ttl:
            try:
                self._cached_title = self._detector()
            except Exception:
                self._cached_title = None
            self._cached_at = now
        return self._cached_title

    def invalidate(self):
        self._cached_at = None
