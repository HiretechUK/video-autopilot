"""Instagram Reels via the Instagram Graph API (Facebook-Page route).

Connect once per account:  python -m autopilot.pipeline connect_instagram imagine_you
  -> emails Haseeb a code; he enters it at facebook.com/device and clicks Continue.
  The pipeline swaps it for the Page's access token, which does not expire, and stores it in tokens.enc.

Posting needs the video at a public URL: it is committed to media/ in this repo, which GitHub Pages serves.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time

import requests

from . import mailer, tokens

G = "https://graph.facebook.com/v23.0"
APP_ID = "1140868964998355"  # Meta app "Series Autopilot" (not a secret)
SCOPE = "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement,pages_manage_posts,business_management"
PAGES_BASE = "https://hiretechuk.github.io/video-autopilot"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDLES = {"imagine_you": "imagineyouseries", "paws_claws": "pawsclawsclubkids",
           "every_how": os.environ.get("EVERYHOW_IG_HANDLE", "everyhow")}


def _secret(name: str) -> str:
    v = (os.environ.get(name) or "").strip()
    if not v:
        raise RuntimeError(f"{name} secret is not set")
    return v.split()[-1]  # tolerate a stray prefix/space before the value


def _get(path: str, **params) -> dict:
    r = requests.get(f"{G}/{path}", params=params, timeout=60).json()
    if "error" in r:
        raise RuntimeError(f"Graph API {path}: {r['error'].get('message')}")
    return r


def _post(path: str, **data) -> dict:
    r = requests.post(f"{G}/{path}", data=data, timeout=120).json()
    if "error" in r:
        raise RuntimeError(f"Graph API {path}: {r['error'].get('message')}")
    return r


def connect(account: str, name: str) -> str:
    handle = HANDLES[account]
    pasted = (os.environ.get("IG_USER_TOKEN") or "").strip()
    if pasted:
        try:
            return _finish(account, handle, pasted.split()[-1])
        except RuntimeError as e:  # an old pasted token expires; fall back to the emailed-code login
            print(f"pasted IG_USER_TOKEN not usable ({e}); using the emailed code instead", flush=True)
    return _finish(account, handle, _device_login(account, name, handle))


def _device_login(account: str, name: str, handle: str) -> str:
    app_token = f"{APP_ID}|{_secret('FB_CLIENT_TOKEN')}"
    d = _post("device/login", access_token=app_token, scope=SCOPE)
    mailer.send(f"Connect Instagram: {name} (code {d['user_code']})",
                f"To let the autopilot post Reels to @{handle}:\n\n"
                f"1. Open: https://www.facebook.com/device?user_code={d['user_code']}\n"
                f"   (or go to facebook.com/device and enter {d['user_code']})\n"
                f"2. Continue as Haseeb, and when asked, tick the {name} Page and the @{handle} Instagram account.\n"
                f"3. Click Continue / Save until it says you're done.\n\n"
                f"The code works for {d['expires_in'] // 60} minutes.")
    print(f"::notice::Enter code {d['user_code']} at facebook.com/device", flush=True)
    deadline, interval = time.time() + d["expires_in"], d.get("interval", 5)
    user_token = None
    while time.time() < deadline:
        time.sleep(interval)
        s = requests.post(f"{G}/device/login_status", data={"access_token": app_token, "code": d["code"]}, timeout=30).json()
        if "access_token" in s:
            user_token = s["access_token"]
            break
        sub = s.get("error", {}).get("error_subcode")
        if sub == 1349172:
            interval += 5
        elif sub != 1349174:
            raise RuntimeError(f"Facebook device login failed: {s.get('error')}")
    if not user_token:
        raise RuntimeError("code expired before it was approved")
    return user_token


def _finish(account: str, handle: str, user_token: str) -> str:
    # Long-lived user token -> Page tokens derived from it do not expire.
    long = _get("oauth/access_token", grant_type="fb_exchange_token", client_id=APP_ID,
                client_secret=_secret("FB_APP_SECRET"), fb_exchange_token=user_token)["access_token"]
    pages = _get("me/accounts", access_token=long, fields="name,access_token,instagram_business_account{id,username}")
    found = []
    for p in pages.get("data", []):
        ig = p.get("instagram_business_account") or {}
        found.append(f"{p['name']} -> @{ig.get('username', 'no Instagram linked')}")
        if ig.get("username", "").lower() == handle:
            tokens.put("instagram", account, {"page_token": p["access_token"], "page_id": p["id"],
                                              "ig_user_id": ig["id"], "username": ig["username"]})
            mailer.send(f"Instagram + Facebook connected: @{handle}", f"The autopilot can now post Reels to @{handle} and to the {p['name']} Facebook Page.")
            return handle
    mailer.send(f"Instagram NOT connected: @{handle} not found",
                "Nothing was saved. The login gave access to these Pages:\n  " + "\n  ".join(found or ["(none)"]) +
                f"\n\nMake sure the @{handle} account is linked to its Facebook Page and that you ticked both when approving, then run it again.")
    raise RuntimeError(f"@{handle} not among authorised pages")


def _host(video: str, name: str) -> str:
    """Commit the video to media/ and return its GitHub Pages URL once it is live."""
    rel = f"media/{name}"
    os.makedirs(os.path.join(ROOT, "media"), exist_ok=True)
    shutil.copy(video, os.path.join(ROOT, rel))
    git = lambda *a: subprocess.run(["git", "-C", ROOT, *a], check=True)
    git("config", "user.name", "video-autopilot")
    git("config", "user.email", "actions@users.noreply.github.com")
    git("add", rel)
    if subprocess.run(["git", "-C", ROOT, "diff", "--cached", "--quiet"]).returncode:
        git("commit", "-m", f"autopilot: host {name} for Instagram")
        git("pull", "--rebase", "--autostash", "-q")
        git("push", "-q")
    url = f"{PAGES_BASE}/{rel}"
    size = os.path.getsize(video)
    for _ in range(40):  # Pages rebuild usually takes 1-3 minutes
        h = requests.head(url, timeout=30)
        if h.status_code == 200 and int(h.headers.get("content-length", 0)) == size:
            return url
        time.sleep(15)
    raise RuntimeError(f"video not live on GitHub Pages yet: {url}")


def upload(account: str, video: str, caption: str, name: str) -> str:
    rec = tokens.get("instagram", account)
    if not rec:
        raise LookupError("not connected")
    tok, ig = rec["page_token"], rec["ig_user_id"]
    url = _host(video, name)
    c = _post(f"{ig}/media", media_type="REELS", video_url=url, caption=caption[:2200],
              share_to_feed="true", access_token=tok)["id"]
    for _ in range(60):  # Instagram processes the video (usually under a minute)
        st = _get(c, fields="status_code,status", access_token=tok)
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram rejected the video: {st.get('status')}")
        time.sleep(10)
    else:
        raise RuntimeError("Instagram took too long to process the video")
    mid = _post(f"{ig}/media_publish", creation_id=c, access_token=tok)["id"]
    return _get(mid, fields="permalink", access_token=tok).get("permalink") or f"https://www.instagram.com/{rec['username']}/"


def find_existing(account: str, title: str) -> str | None:
    """Return the permalink of a Reel already posted with this title (duplicate guard)."""
    rec = tokens.get("instagram", account)
    if not rec:
        raise LookupError("not connected")
    tok, ig = rec["page_token"], rec["ig_user_id"]
    want = title.strip().lower()
    for m in _get(f"{ig}/media", fields="caption,permalink", limit=50, access_token=tok).get("data", []):
        if (m.get("caption") or "").strip().lower().startswith(want):
            return m.get("permalink") or f"https://www.instagram.com/{rec['username']}/"
    return None
