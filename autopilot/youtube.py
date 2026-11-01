"""YouTube: one-time device sign-in per channel, then automatic uploads with the stored refresh token.

Connect:  python -m autopilot.pipeline connect_youtube imagine_you
  -> emails Haseeb a short code; he enters it at google.com/device, picks the channel, clicks Allow.
"""
from __future__ import annotations

import os
import time

import requests

from . import mailer, tokens

DEVICE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/youtube"
API = "https://www.googleapis.com/youtube/v3"


def _client():
    cid, sec = os.environ.get("YT_CLIENT_ID"), os.environ.get("YT_CLIENT_SECRET")
    if not cid or not sec:
        raise RuntimeError("YT_CLIENT_ID / YT_CLIENT_SECRET secrets are not set")
    import re
    cid = cid.strip()
    m = re.search(r"GOCSPX-[A-Za-z0-9_-]+", sec)  # secret may be stored with an 'x' (and spaces) in front
    sec = m.group(0) if m else sec.strip()
    return cid, sec


# Google account to sign in with, per series, when a channel lives on its own Gmail. Imagine You is a brand account
# under Haseeb's own Gmail; Every How's channel ("Every How Channel") is on harry.taroles@gmail.com (1 Nov 2026).
SIGN_IN = {"every_how": "harry.taroles@gmail.com"}


def connect(account: str, channel_name: str) -> str:
    cid, sec = _client()
    own = SIGN_IN.get(account)
    who = (f"3. Sign in as {own} and, if Google asks which channel, pick {channel_name}.\n" if own else
           f"3. Sign in as haseeb.ahmed.talent@gmail.com (not the channel's own Gmail) and, when asked which account,\n"
           f"   choose the brand account for {channel_name}{' (listed as What Nearly Was)' if account == 'imagine_you' else ''}\n"
           f"   (NOT your personal 'haseeb ahmed' channel).\n")
    r = requests.post(DEVICE_URL, data={"client_id": cid, "scope": SCOPE}, timeout=30)
    r.raise_for_status()
    d = r.json()
    mailer.send(f"Connect YouTube: {channel_name} (code {d['user_code']})",
                f"To let the autopilot post to the {channel_name} YouTube channel:\n\n"
                f"1. On your phone or computer open: {d['verification_url']}\n"
                f"2. Enter this code: {d['user_code']}\n"
                + who +
                f"4. Click Allow. Google may warn the app is unverified: click Advanced, then continue.\n\n"
                f"The code works for {d['expires_in'] // 60} minutes.")
    print(f"::notice::Enter code {d['user_code']} at {d['verification_url']}", flush=True)
    deadline = time.time() + d["expires_in"]
    interval = d.get("interval", 5)
    while time.time() < deadline:
        time.sleep(interval)
        t = requests.post(TOKEN_URL, data={"client_id": cid, "client_secret": sec, "device_code": d["device_code"],
                                           "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}, timeout=30).json()
        if "refresh_token" in t:
            ch = requests.get(f"{API}/channels", params={"part": "snippet", "mine": "true"},
                              headers={"Authorization": f"Bearer {t['access_token']}"}, timeout=30).json()
            title = ch["items"][0]["snippet"]["title"] if ch.get("items") else "?"
            cid_ = ch["items"][0]["id"] if ch.get("items") else "?"
            if title == "?":
                mailer.send("YouTube NOT connected: no channel on that account",
                            f"The Google account you signed in with has no YouTube channel, so nothing was saved.\n"
                            + (f"Create the {channel_name} channel on {own} first (youtube.com, Create a channel), then run the connect again."
                               if own else f"Run the connect again, sign in as haseeb.ahmed.talent@gmail.com and pick the brand account "
                                           f"that holds {channel_name} (for Imagine You it is still called 'What Nearly Was')."))
                raise RuntimeError("no channel on chosen account; refused")
            if "haseeb ahmed" in title.lower():
                mailer.send("YouTube NOT connected: wrong channel",
                            f"You picked '{title}', your personal channel. Nothing was saved. Run the connect again and pick {channel_name}.")
                raise RuntimeError("personal channel chosen; refused")
            tokens.put("youtube", account, {"refresh_token": t["refresh_token"], "channel_id": cid_, "channel_title": title})
            mailer.send(f"YouTube connected: {title}", f"The autopilot can now post to '{title}' ({cid_}).")
            return title
        if t.get("error") == "slow_down":
            interval += 5
        elif t.get("error") not in ("authorization_pending",):
            raise RuntimeError(f"device sign-in failed: {t}")
    raise RuntimeError("code expired before it was approved")


def _access(account: str) -> tuple[str, dict]:
    rec = tokens.get("youtube", account)
    if not rec:
        raise LookupError("not connected")
    cid, sec = _client()
    t = requests.post(TOKEN_URL, data={"client_id": cid, "client_secret": sec, "refresh_token": rec["refresh_token"],
                                       "grant_type": "refresh_token"}, timeout=30).json()
    if "access_token" not in t:
        raise RuntimeError(f"YouTube token refresh failed: {t.get('error')}")
    return t["access_token"], rec


def upload(account: str, video: str, title: str, description: str, tags: list[str], made_for_kids: bool,
           category: str = "24") -> str:
    at, rec = _access(account)
    meta = {"snippet": {"title": title[:100], "description": description[:4900], "tags": tags[:15], "categoryId": category},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": made_for_kids,
                       "containsSyntheticMedia": True}}
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos",
                      params={"uploadType": "resumable", "part": "snippet,status"},
                      headers={"Authorization": f"Bearer {at}", "X-Upload-Content-Type": "video/mp4",
                               "X-Upload-Content-Length": str(os.path.getsize(video))},
                      json=meta, timeout=60)
    r.raise_for_status()
    with open(video, "rb") as f:
        u = requests.put(r.headers["Location"], data=f, headers={"Content-Type": "video/mp4"}, timeout=1800)
    u.raise_for_status()
    vid = u.json()["id"]
    return f"https://youtube.com/watch?v={vid}"


def find_existing(account: str, title: str) -> str | None:
    """Return the link of a video on this channel that already has this title (duplicate guard)."""
    at, _ = _access(account)
    h = {"Authorization": f"Bearer {at}"}
    ch = requests.get(f"{API}/channels", params={"part": "contentDetails", "mine": "true"}, headers=h, timeout=30)
    ch.raise_for_status()
    uploads = ch.json()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    r = requests.get(f"{API}/playlistItems", params={"part": "snippet", "playlistId": uploads, "maxResults": 50},
                     headers=h, timeout=30)
    r.raise_for_status()
    want = title[:100].strip().lower()
    for it in r.json().get("items", []):
        if it["snippet"]["title"].strip().lower() == want:
            return f"https://youtube.com/watch?v={it['snippet']['resourceId']['videoId']}"
    return None
