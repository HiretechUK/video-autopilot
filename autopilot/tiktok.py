"""TikTok via the Content Posting API ("upload to inbox").

Each approved video is sent to the channel's TikTok inbox as a draft; TikTok notifies the phone and one tap
posts it (caption is emailed for pasting). Fully hands-off Direct Post needs TikTok's audit; until then this
is the most automatic route TikTok allows.

Connect once per account:  python -m autopilot.pipeline connect_tiktok imagine_you
  -> emails a TikTok link; approve as the channel, the page shows a code, reply to the email with it.
"""
from __future__ import annotations

import os
import secrets
import time
import urllib.parse

import requests

from . import mailer, tokens

API = "https://open.tiktokapis.com/v2"
REDIRECT = "https://hiretechuk.github.io/video-autopilot/tiktok.html"
SCOPE = "user.info.basic,video.upload"
HANDLES = {"imagine_you": "imagineyouseries", "paws_claws": "pawsclawsclubkids"}


def _keys() -> tuple[str, str]:
    k, s = (os.environ.get("TT_CLIENT_KEY") or "").strip(), (os.environ.get("TT_CLIENT_SECRET") or "").strip()
    if not k or not s:
        raise RuntimeError("TT_CLIENT_KEY / TT_CLIENT_SECRET secrets are not set")
    return k.split()[-1], s.split()[-1]


def _token(**data) -> dict:
    k, s = _keys()
    r = requests.post(f"{API}/oauth/token/", data={"client_key": k, "client_secret": s, **data},
                      headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30).json()
    if "access_token" not in r:
        raise RuntimeError(f"TikTok token error: {r.get('error')} {r.get('error_description')}")
    return r


def connect(account: str, name: str) -> str:
    handle = HANDLES[account]
    k, _ = _keys()
    ref = f"TTC-{secrets.token_hex(3).upper()}"
    url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(
        {"client_key": k, "scope": SCOPE, "response_type": "code", "redirect_uri": REDIRECT, "state": ref})
    mailer.send(f"Connect TikTok: {name} [{ref}]",
                f"To let the autopilot send videos to @{handle} on TikTok:\n\n"
                f"1. Open this link (on the computer where TikTok is logged in as @{handle}):\n   {url}\n"
                f"2. Click Continue / Authorize.\n"
                f"3. The page you land on shows a code. Copy it and reply to this email with just the code.\n\n"
                f"Do it within 10 minutes; the code expires quickly.")
    seen: set[str] = set()
    deadline = time.time() + 20 * 60
    while time.time() < deadline:
        time.sleep(20)
        for _, mid, text in mailer.fetch_replies([ref], seen):
            seen.add(mid)
            code = urllib.parse.unquote(text.strip().split()[0]) if text.strip() else ""
            if not code:
                continue
            t = _token(code=code, grant_type="authorization_code", redirect_uri=REDIRECT)
            me = requests.get(f"{API}/user/info/", params={"fields": "open_id,display_name"},
                              headers={"Authorization": f"Bearer {t['access_token']}"}, timeout=30).json()
            who = (me.get("data", {}).get("user", {}) or {}).get("display_name", "?")
            tokens.put("tiktok", account, {"refresh_token": t["refresh_token"], "open_id": t.get("open_id"),
                                           "display_name": who, "refresh_expires": time.time() + t.get("refresh_expires_in", 0)})
            mailer.send(f"TikTok connected: {who}",
                        f"The autopilot will send approved {name} videos to the TikTok account '{who}' as drafts.\n"
                        f"If that is not @{handle}, reply 'wrong' and we'll redo it.")
            return who
    raise RuntimeError("no code reply received within 20 minutes")


def _access(account: str) -> str:
    rec = tokens.get("tiktok", account)
    if not rec:
        raise LookupError("not connected")
    t = _token(grant_type="refresh_token", refresh_token=rec["refresh_token"])
    if t.get("refresh_token") and t["refresh_token"] != rec["refresh_token"]:
        rec["refresh_token"] = t["refresh_token"]
        rec["refresh_expires"] = time.time() + t.get("refresh_expires_in", 0)
        tokens.put("tiktok", account, rec)
    if rec.get("refresh_expires") and rec["refresh_expires"] - time.time() < 14 * 86400:
        mailer.send("TikTok connection expires soon", f"Run connect_tiktok {account} within two weeks to keep TikTok posting.")
    return t["access_token"]


def upload(account: str, video: str, caption: str) -> str:
    at = _access(account)
    size = os.path.getsize(video)
    h = {"Authorization": f"Bearer {at}", "Content-Type": "application/json; charset=UTF-8"}
    r = requests.post(f"{API}/post/publish/inbox/video/init/", headers=h, timeout=60, json={
        "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}}).json()
    if r.get("error", {}).get("code") not in (None, "ok"):
        raise RuntimeError(f"TikTok init failed: {r['error']}")
    d = r["data"]
    with open(video, "rb") as f:
        u = requests.put(d["upload_url"], data=f, timeout=900, headers={
            "Content-Type": "video/mp4", "Content-Length": str(size), "Content-Range": f"bytes 0-{size - 1}/{size}"})
    u.raise_for_status()
    for _ in range(40):
        s = requests.post(f"{API}/post/publish/status/fetch/", headers=h, json={"publish_id": d["publish_id"]}, timeout=30).json()
        st = s.get("data", {}).get("status")
        if st in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
            break
        if st == "FAILED":
            raise RuntimeError(f"TikTok processing failed: {s.get('data', {}).get('fail_reason')}")
        time.sleep(10)
    mailer.send("TikTok draft ready: tap to post",
                f"The video is in the @{HANDLES[account]} TikTok inbox. Open TikTok, tap the notification, paste this caption, "
                f"turn on 'AI-generated content', and post:\n\n{caption}")
    return f"https://www.tiktok.com/@{HANDLES[account]} (draft sent to inbox)"
