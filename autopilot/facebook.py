"""Facebook Page Reels via the Graph API Reels Publishing endpoint (/{page-id}/video_reels).

Uses the same Facebook Page token that `connect_instagram` saves (the Instagram account is posted through its
linked Page). Posting needs the pages_manage_posts permission, so after this was added the connection is run once
more: python -m autopilot.pipeline connect_instagram imagine_you
"""
from __future__ import annotations

import os
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


def find_existing(account: str, title: str) -> str | None:
    """Return the link of a Page Reel already posted with this title (duplicate guard)."""
    rec = tokens.get("instagram", account)
    if not rec or not rec.get("page_id"):
        raise LookupError("not connected")
    tok, page = rec["page_token"], rec["page_id"]
    want = title.strip().lower()
    for v in instagram._get(f"{page}/video_reels", fields="description,permalink_url", limit=50,
                            access_token=tok).get("data", []):
        if (v.get("description") or "").strip().lower().startswith(want):
            link = v.get("permalink_url") or f"/reel/{v['id']}"
            return link if link.startswith("http") else f"https://www.facebook.com{link}"
    return None


GV = "https://graph-video.facebook.com/v23.0"


def upload_video(account: str, video: str, title: str, description: str) -> str:
    """Long-form (16:9) Page video, for series whose full episode goes to Facebook (Every How)."""
    rec = tokens.get("instagram", account)
    if not rec or not rec.get("page_id"):
        raise LookupError("not connected")
    tok, page = rec["page_token"], rec["page_id"]
    with open(video, "rb") as f:
        r = requests.post(f"{GV}/{page}/videos", data={"title": title[:250], "description": description[:5000],
                                                         "published": "true", "access_token": tok},
                          files={"source": (os.path.basename(video), f, "video/mp4")}, timeout=1800).json()
    if "id" not in r:
        raise RuntimeError(f"Facebook video upload failed: {r}")
    return f"https://www.facebook.com/{page}/videos/{r['id']}"


def find_existing_video(account: str, title: str) -> str | None:
    """Duplicate guard for long-form Page videos (matched on the video title)."""
    rec = tokens.get("instagram", account)
    if not rec or not rec.get("page_id"):
        raise LookupError("not connected")
    tok, page = rec["page_token"], rec["page_id"]
    want = title[:250].strip().lower()
    for v in instagram._get(f"{page}/videos", fields="title,permalink_url", limit=50, access_token=tok).get("data", []):
        if (v.get("title") or "").strip().lower() == want:
            link = v.get("permalink_url") or f"/{page}/videos/{v['id']}"
            return link if link.startswith("http") else f"https://www.facebook.com{link}"
    return None
