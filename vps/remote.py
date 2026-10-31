"""Remote-control the VPS browser from any web browser (for one-time logins / verification).

  python remote.py TOKEN [start_url]
Open http://<vps-ip>:8088/?t=TOKEN : click on the picture to click, type into the box to type.
Stops after 20 minutes or when you press Finish.
"""
from __future__ import annotations

import http.server
import os
import queue
import sys
import threading
import time
import urllib.parse

from playwright.sync_api import sync_playwright

HOME = os.path.dirname(os.path.abspath(__file__))
TOKEN = sys.argv[1]
START = sys.argv[2] if len(sys.argv) > 2 else "https://www.tiktok.com/login/qrcode"
W, H = 1366, 900
jobs: "queue.Queue[tuple]" = queue.Queue()
state = {"png": b"", "stop": False}

PAGE = """<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="margin:0;background:#111;color:#eee;font-family:sans-serif">
<div style="padding:8px;display:flex;gap:6px;flex-wrap:wrap;align-items:center">
<input id=t placeholder="type here, then Send" style="font-size:18px;padding:6px;width:260px">
<button onclick="go('type',t.value);t.value=''">Send</button>
<button onclick="go('key','Enter')">Enter</button><button onclick="go('key','Backspace')">Backspace</button>
<button onclick="go('key','Tab')">Tab</button><button onclick="go('scroll','600')">Scroll down</button>
<button onclick="go('scroll','-600')">Scroll up</button>
<button onclick="if(confirm('Finish and save login?'))go('done','')" style="background:#2a2;color:#fff">Finish</button>
<span id=m></span></div>
<img id=s style="width:100%;cursor:crosshair">
<script>
const T=new URLSearchParams(location.search).get('t');
function go(a,v){fetch('/act?t='+T+'&a='+a+'&v='+encodeURIComponent(v)).then(()=>{m.textContent=a+' sent'})}
s.onclick=e=>{const r=s.getBoundingClientRect();go('click',Math.round((e.clientX-r.left)*%d/r.width)+','+Math.round((e.clientY-r.top)*%d/r.height))};
setInterval(()=>{s.src='/shot?t='+T+'&'+Date.now()},1500);
</script>""" % (W, H)


class H_(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        if q.get("t") != TOKEN:
            self.send_response(403); self.end_headers(); return
        if u.path == "/shot":
            body, ctype = state["png"], "image/png"
        elif u.path == "/act":
            jobs.put((q.get("a"), q.get("v", "")))
            body, ctype = b"ok", "text/plain"
        else:
            body, ctype = PAGE.encode(), "text/html"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


srv = http.server.ThreadingHTTPServer(("0.0.0.0", 8088), H_)
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        os.path.join(HOME, "profile"), headless=False, viewport={"width": W, "height": H}, locale="en-GB",
        timezone_id="Europe/London", args=["--disable-blink-features=AutomationControlled", "--no-first-run"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto(START, wait_until="domcontentloaded")
    end = time.time() + 1200
    while time.time() < end and not state["stop"]:
        try:
            while not jobs.empty():
                a, v = jobs.get()
                if a == "click":
                    x, y = map(int, v.split(","))
                    pg.mouse.click(x, y)
                elif a == "type":
                    pg.keyboard.type(v, delay=60)
                elif a == "key":
                    pg.keyboard.press(v)
                elif a == "scroll":
                    pg.mouse.wheel(0, int(v))
                elif a == "done":
                    state["stop"] = True
                pg.wait_for_timeout(300)
            state["png"] = pg.screenshot()
        except Exception as e:
            print("err", e)
        time.sleep(0.7)
    pg.goto("https://www.tiktok.com/tiktokstudio/content", wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    print("LOGGED IN" if "/login" not in pg.url else "NOT LOGGED IN", pg.url)
    ctx.close()
srv.shutdown()
