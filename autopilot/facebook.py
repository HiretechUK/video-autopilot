"""Facebook Page Reels via the Graph API Reels Publishing endpoint (/{page-id}/video_reels).

Uses the same Facebook Page token that `connect_instagram` saves (the Instagram account is posted through its
linked Page). Posting needs the pages_manage_posts permission, so after this was added the connection is run once
more: python -m autopilot.pipeline connect_instagram imagine_you
"""
from __future__ import annotations

import time

import requests

from . import instagram, tokens

G = instagram.G
RUPLOAD = "https://rupload.facebook.com/video-upload/v23.0"


def upload(account: str, video: str, description: str, name: str) -> str:
    rec = tokens.get("instagram", account)
    if not rec or not rec.get("page_id"):
        raise LookupError("not connected")
    tok, page = rec["page_token"], rec["page_id"]
    url = instagram._host(video, name)  # same public copy Instagram uses
    start = instagram._post(f"{page}/video_reels", upload_phase="start", access_token=tok)
    vid = start["video_id"]
    r = requests.post(f"{RUPLOAD}/{vid}", headers={"Authorization": f"OAuth {tok}", "file_url": url}, timeout=180).json()
    if not r.get("success"):
        raise RuntimeError(f"Facebook upload failed: {r}")
    instagram._post(f"{page}/video_reels", upload_phase="finish", video_id=vid, video_state="PUBLISHED",
                    description=description[:2200], access_token=tok)
    for _ in range(60):  # Facebook processes, then publishes (usually a minute or two)
        st = instagram._get(vid, fields="status", access_token=tok).get("status", {})
        if st.get("video_status") == "ready" and (st.get("publishing_phase") or {}).get("status") == "complete":
            break
        if st.get("video_status") == "error" or (st.get("processing_phase") or {}).get("status") == "error":
            raise RuntimeError(f"Facebook rejected the video: {st}")
        time.sleep(10)
    return f"https://www.facebook.com/reel/{vid}"
