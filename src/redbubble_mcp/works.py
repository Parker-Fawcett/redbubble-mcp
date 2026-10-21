"""Pure helpers for parsing your works list out of portfolio page URLs."""

from __future__ import annotations

import re
from urllib.parse import urlparse

WORK_RE = re.compile(r"^/portfolio/images/(?P<id>\d+)-(?P<slug>[a-z0-9-]+)$")


def parse_works(hrefs: list[str]) -> list[dict]:
    works = []
    seen: set[str] = set()
    for href in hrefs or []:
        path = urlparse(href).path
        match = WORK_RE.match(path)
        if not match or match.group("id") in seen:
            continue
        seen.add(match.group("id"))
        base = f"{urlparse(href).scheme}://{urlparse(href).netloc}{path}"
        works.append(
            {
                **match.groupdict(),
                "title": match.group("slug").replace("-", " "),
                "url": base,
                "edit_url": f"{base}/edit",
                "duplicate_url": f"{base}/duplicate",
            }
        )
    return works
