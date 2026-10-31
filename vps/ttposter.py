"""TikTok poster that runs on Haseeb's VPS.

Daily (cron): reads the public repo's state, finds approved episodes not yet on TikTok, downloads the video
from GitHub Pages, and posts it through TikTok Studio in a browser that stays logged in.

  python ttposter.py login     one-time: shows a QR code at http://<vps-ip>:8088/ to scan with the TikTok app
  python ttposter.py run       post anything new (cron runs this)
  python ttposter.py dry IY-02 fill in everything for an episode but do NOT click Post (test)
"""
from __future__ import annotations

import http.server
import json
import os
import smtplib
import sys
import threading
import time
import traceback
from email.message import EmailMessage

import requests
from playwright.sync_api import sync_playwright

HOME = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.path.join(HOME, "profile")
WWW = os.path.join(HOME, "www")
POSTED = os.path.join(HOME, "posted.json")
ENV = os.path.join(HOME, ".env")
RAW = "https://raw.githubusercontent.com/HiretechUK/video-autopilot/main"
PAGES = "https://hiretechuk.github.io/video-autopilot"
SERIES = {"imagine_you": {"handle": "imagineyouseries",
                          "hashtags": "#survival #whatwouldyoudo #stranded #survivaltips #imagineyou"}}
STUDIO = "https://www.tiktok.com/tiktokstudio/upload?from=upload"


def env() -> dict:
    d = {}
    if os.path.exists(ENV):
        for line in open(ENV):
            if "=" in line:
                k, v = line.strip().split("=", 1)
                d[k] = v
    return d


def mail(subject: str, body: str, attach: str | None = None):
    e = env()
    if not e.get("SMTP_USER"):
        print("MAIL:", subject, body)
        return
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = e["SMTP_USER"], e.get("TO", "haseeb.ahmed.talent@gmail.com"), subject
    m.set_content(body)
    if attach and os.path.exists(attach):
        m.add_attachment(open(attach, "rb").read(), maintype="image", subtype="png", filename=os.path.basename(attach))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(e["SMTP_USER"], e["SMTP_APP_PASSWORD"])
        s.send_message(m)


def browser(p):
    return p.chromium.launch_persistent_context(
        PROFILE, headless=False, viewport={"width": 1366, "height": 900}, locale="en-GB", timezone_id="Europe/London",
        args=["--disable-blink-features=AutomationControlled", "--no-first-run"])


def serve():
    os.makedirs(WWW, exist_ok=True)
    h = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=WWW, **k)
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", 8088), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def login():
    srv = serve()
    open(os.path.join(WWW, "index.html"), "w").write(
        '<meta http-equiv="refresh" content="3"><body style="background:#111;color:#eee;font-family:sans-serif;text-align:center">'
        '<h2>Scan with the TikTok app (Profile &rarr; &#9776; &rarr; scan icon)</h2><img src="qr.png?%d" style="max-width:95vw"></body>' % time.time())
    with sync_playwright() as p:
        ctx = browser(p)
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto("https://www.tiktok.com/login/qrcode", wait_until="domcontentloaded")
        end = time.time() + 600
        while time.time() < end:
            time.sleep(3)
            pg.screenshot(path=os.path.join(WWW, "qr.png"))
            if "/login" not in pg.url:
                break
        pg.goto("https://www.tiktok.com/tiktokstudio/content", wait_until="domcontentloaded")
        time.sleep(6)
        pg.screenshot(path=os.path.join(WWW, "qr.png"))
        ok = "/login" not in pg.url
        ctx.close()
    srv.shutdown()
    print("LOGGED IN" if ok else "NOT LOGGED IN")


def pending(include: str | None = None) -> list[tuple[str, dict, dict]]:
    st = requests.get(f"{RAW}/autopilot/state.json", timeout=30).json()
    done = json.load(open(POSTED)) if os.path.exists(POSTED) else {}
    out = []
    for ref, rec in sorted(st["episodes"].items(), key=lambda kv: kv[1].get("approved", "")):
        if ref != include and (rec.get("status") not in ("approved", "partly_published", "published") or ref in done):
            continue
        if rec["series"] not in SERIES:
            continue
        ep = requests.get(f"{RAW}/{rec['file']}", timeout=30).json()
        out.append((ref, rec, ep))
    return out


def caption(rec: dict, ep: dict) -> str:
    return f"{ep['title']}. {ep.get('description', '')} Comment A or B. {SERIES[rec['series']]['hashtags']}"


def post(ref: str, rec: dict, ep: dict, dry: bool = False) -> str:
    vid = os.path.join(HOME, f"{ref}.mp4")
    r = requests.get(f"{PAGES}/media/{ref}.mp4", timeout=300)
    if r.status_code != 200:
        raise FileNotFoundError(f"video not hosted yet: {PAGES}/media/{ref}.mp4")
    open(vid, "wb").write(r.content)
    shot = os.path.join(WWW, f"{ref}.png")
    os.makedirs(WWW, exist_ok=True)
    with sync_playwright() as p:
        ctx = browser(p)
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            pg.goto(STUDIO, wait_until="domcontentloaded")
            pg.wait_for_timeout(6000)
            if "/login" in pg.url:
                raise RuntimeError("TikTok session logged out: run 'python ttposter.py login' again")
            pg.locator('input[type="file"]').first.set_input_files(vid)
            # wait for the editor + upload to finish
            ed = pg.locator('div[contenteditable="true"]').first
            ed.wait_for(timeout=120000)
            pg.wait_for_timeout(4000)
            ed.click()
            pg.keyboard.press("Control+A")
            pg.keyboard.press("Backspace")
            for word in caption(rec, ep).split(" "):
                pg.keyboard.type(word, delay=15)
                if word.startswith("#"):
                    pg.wait_for_timeout(900)
                    pg.keyboard.press("Escape")  # close hashtag suggestions without picking one
                pg.keyboard.type(" ")
            pg.mouse.click(5, 300)
            for label in ("Show more", "More options"):
                b = pg.get_by_text(label, exact=True)
                if b.count():
                    b.first.click()
                    pg.wait_for_timeout(1000)
                    break
            ai = pg.get_by_text("AI-generated content", exact=False)
            if ai.count():
                sw = ai.first.locator("xpath=ancestor::*[.//input[@type='checkbox' or @role='switch'] or .//*[@role='switch']][1]")
                tog = sw.locator('input[type="checkbox"], [role="switch"]').first
                checked = tog.get_attribute("aria-checked") == "true" or tog.is_checked()
                if not checked:
                    tog.click(force=True)
                    pg.wait_for_timeout(800)
                    for t in ("Turn on", "Confirm"):
                        c = pg.get_by_role("button", name=t)
                        if c.count():
                            c.first.click()
                            break
            # wait until TikTok says the upload is done
            for _ in range(120):
                if pg.get_by_text("Uploaded", exact=False).count() or not pg.get_by_text("Uploading", exact=False).count():
                    break
                pg.wait_for_timeout(2000)
            pg.screenshot(path=shot, full_page=True)
            if dry:
                return f"dry run ok, screenshot at :8088/{ref}.png"
            pg.get_by_role("button", name="Post", exact=True).last.click()
            pg.wait_for_timeout(4000)
            for t in ("Post now", "Continue", "Post anyway"):
                c = pg.get_by_role("button", name=t)
                if c.count():
                    c.first.click()
                    pg.wait_for_timeout(3000)
                    break
            pg.wait_for_url("**/tiktokstudio/content**", timeout=120000)
            pg.wait_for_timeout(5000)
            pg.screenshot(path=shot)
            return f"https://www.tiktok.com/@{SERIES[rec['series']]['handle']}"
        except Exception:
            try:
                pg.screenshot(path=shot, full_page=True)
            except Exception:
                pass
            raise
        finally:
            ctx.close()
            if os.path.exists(vid):
                os.remove(vid)


def run(dry_ref: str | None = None):
    done = json.load(open(POSTED)) if os.path.exists(POSTED) else {}
    for ref, rec, ep in pending(dry_ref):
        if dry_ref and ref != dry_ref:
            continue
        try:
            link = post(ref, rec, ep, dry=bool(dry_ref))
            print(ref, link)
            if dry_ref:
                return
            done[ref] = {"link": link, "at": time.strftime("%Y-%m-%d %H:%M")}
            json.dump(done, open(POSTED, "w"), indent=1)
            mail(f"Posted on TikTok: {ep['title']} [{ref}]", f"Live on {link}\n\nCaption:\n{caption(rec, ep)}",
                 os.path.join(WWW, f"{ref}.png"))
        except FileNotFoundError as e:
            print(ref, "waiting:", e)
        except Exception as e:
            traceback.print_exc()
            mail(f"TikTok post FAILED [{ref}]", f"{e}\n\nIt will retry on the next run. Screenshot attached.",
                 os.path.join(WWW, f"{ref}.png"))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "login":
        login()
    elif cmd == "dry":
        run(sys.argv[2])
    else:
        run()
