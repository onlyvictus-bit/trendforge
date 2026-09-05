from __future__ import annotations

import threading
from datetime import datetime, timezone

from .source_monitor import check_sources


class SourceMonitorScheduler:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.interval_seconds = 0
        self.fetch = False
        self.source_keys: list[str] | None = None
        self.last_run_at: str | None = None
        self.last_error: str | None = None
        self.last_summary: dict | None = None

    def status(self) -> dict:
        with self._lock:
            return {
                "running": self._thread is not None and self._thread.is_alive(),
                "intervalSeconds": self.interval_seconds,
                "fetch": self.fetch,
                "sourceKeys": self.source_keys,
                "lastRunAt": self.last_run_at,
                "lastError": self.last_error,
                "lastSummary": self.last_summary,
            }

    def start(
        self,
        *,
        interval_seconds: int,
        fetch: bool = False,
        source_keys: list[str] | None = None,
    ) -> dict:
        if interval_seconds < 60:
            raise ValueError("interval_seconds must be at least 60")
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                already_running = True
            else:
                already_running = False
                self.interval_seconds = interval_seconds
                self.fetch = fetch
                self.source_keys = source_keys
                self._stop_event.clear()
                self._thread = threading.Thread(target=self._run_loop, daemon=True)
                self._thread.start()
        if already_running:
            return self.status()
        return self.status()

    def stop(self) -> dict:
        with self._lock:
            self._stop_event.set()
            thread = self._thread
        if thread is not None:
            thread.join(timeout=2)
        with self._lock:
            self._thread = None
        return self.status()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.run_once()
            self._stop_event.wait(self.interval_seconds)

    def run_once(self) -> dict:
        try:
            summary = check_sources(self.source_keys, fetch=self.fetch)
            dumped = summary.model_dump(mode="json", by_alias=True, exclude={"results"})
            with self._lock:
                self.last_run_at = datetime.now(timezone.utc).isoformat()
                self.last_error = None
                self.last_summary = dumped
            return dumped
        except Exception as exc:  # pragma: no cover - defensive scheduler boundary
            with self._lock:
                self.last_run_at = datetime.now(timezone.utc).isoformat()
                self.last_error = str(exc)
                self.last_summary = None
            return {"error": str(exc)}


SOURCE_MONITOR_SCHEDULER = SourceMonitorScheduler()
