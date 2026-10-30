"""Post an approved episode to each connected platform. Platforms that are not connected yet are skipped,
so approved episodes simply wait (status 'approved') until the accounts are connected."""
from __future__ import annotations

import os


def publish(series: str, ep: dict, video: str) -> dict:
    links = {}
    # YouTube, Instagram and TikTok uploaders plug in here once their access is connected.
    if not os.environ.get("YT_CLIENT_ID"):
        links["youtube"] = "not connected yet (episode kept as approved)"
    return links
