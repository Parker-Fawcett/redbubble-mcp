"""Persisted Redbubble session state (cookies + user agent) captured by `redbubble-mcp-login`."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import unquote

from redbubble_mcp.guards import DEFAULT_DIR


class SessionStore:
    def __init__(self, state_dir: str | os.PathLike | None = None):
        self.state_dir = Path(state_dir) if state_dir else DEFAULT_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.state_dir / "session.json"
        data = self._read()
        self.cookies: dict[str, str] = data.get("cookies", {})
        self.user_agent: str = data.get("user_agent", "")

    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text("utf-8"))
        except (OSError, ValueError):
            return {}

    def _flush(self) -> None:
        self.path.write_text(
            json.dumps({"cookies": self.cookies, "user_agent": self.user_agent}), "utf-8"
        )

    def save_cookies(self, cookies: dict[str, str], *, user_agent: str = "") -> None:
        self.cookies = dict(cookies)
        if user_agent:
            self.user_agent = user_agent
        self._flush()

    def merge_cookies(self, cookies: dict[str, str]) -> None:
        self.cookies = {**self.cookies, **dict(cookies)}
        self._flush()

    def cookie_names(self) -> set[str]:
        return set(self.cookies)

    def cookie_header(self) -> str:
        return "; ".join(f"{k}={v}" for k, v in self.cookies.items())

    def xsrf_token(self) -> str | None:
        for name, value in self.cookies.items():
            if "xsrf" in name.lower() or "csrf" in name.lower():
                return unquote(value)
        return None
