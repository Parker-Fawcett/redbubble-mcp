"""Rate guards so agents never spam Redbubble (their ToS allows perma-bans for bot abuse)."""

from __future__ import annotations

import datetime as dt
import json
import os
import time
from pathlib import Path

RB_MAX_UPLOADS_PER_DAY = 30  # Redbubble's own published daily upload limit (all accounts combined)


class UploadBlocked(Exception):
    def __init__(self, reason: str, retry_after_s: float = 0.0):
        super().__init__(reason)
        self.reason = reason
        self.retry_after_s = retry_after_s


DEFAULT_DIR = Path(
    os.environ.get("RB_MCP_STATE_DIR")
    or Path(os.path.expanduser("~")) / ".redbubble-mcp"
)


def _today(day: dt.date | None = None) -> str:
    return (day or dt.date.today()).isoformat()


class UploadLedger:
    """Persistent ledger of uploads, enforcing Redbubble's daily cap + a pacing interval."""

    def __init__(
        self,
        state_dir: str | os.PathLike | None = None,
        *,
        min_interval_s: float | None = None,
        daily_cap: int = RB_MAX_UPLOADS_PER_DAY,
    ):
        self.state_dir = Path(state_dir) if state_dir else DEFAULT_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.state_dir / "ledger.json"
        self.min_interval_s = (
            min_interval_s
            if min_interval_s is not None
            else float(os.environ.get("RB_UPLOAD_MIN_INTERVAL_S", "300"))
        )
        self.daily_cap = daily_cap

    # -- persistence ------------------------------------------------
    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text("utf-8"))
        except (OSError, ValueError):
            return {"count": 0, "last_ts": 0.0}

    def _write(self, data: dict) -> None:
        self.path.write_text(json.dumps(data), "utf-8")

    # -- state ------------------------------------------------------
    def count_on(self, day: dt.date) -> int:
        data = self._read()
        return data["count"] if data.get("date") == _today(day) else 0

    def seconds_since_last(self, now: float) -> float | None:
        last = self._read().get("last_ts") or 0.0
        return (now - last) if last else None

    # -- actions ----------------------------------------------------
    def assert_can_upload(self, now: dt.datetime, *, bypass: bool = False) -> None:
        """Raise UploadBlocked if an upload is not allowed right now."""
        count = self.count_on(now.date())
        epoch = now.timestamp()
        if not bypass and count >= self.daily_cap:
            raise UploadBlocked(
                f"Daily upload cap reached ({count}/{self.daily_cap}). "
                "Redbubble's ToS bans accounts for automated uploads beyond their limits — try again tomorrow."
            )
        since = self.seconds_since_last(epoch)
        if not bypass and since is not None and since < self.min_interval_s:
            raise UploadBlocked(
                f"Only {since:.0f}s since the last upload; pacing minimum is {self.min_interval_s:.0f}s.",
                retry_after_s=self.min_interval_s - since,
            )

    def record_upload(self, now: dt.datetime, *, force: bool = False) -> None:
        """force=True skips the cap/interval checks (used to simulate reaching the cap)."""
        self.assert_can_upload(now, bypass=force)
        today = _today(now.date())
        data = self._read()
        if data.get("date") != today:
            data = {"date": today, "count": 0}
        data["count"] += 1
        data["last_ts"] = now.timestamp()
        self._write(data)
