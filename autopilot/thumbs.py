"""Custom YouTube thumbnails for every series (Haseeb, 1 Nov 2026: thumbnails good enough to make people click,
and kid-friendly for Paws & Claws).

  Imagine You  (Shorts, 1080x1920): the best frame of the episode + 2-4 huge words, key word in yellow.
  Every How    (long video, 1280x720): paper cut-out look like the videos, a big question in 3-6 words,
                one word underlined in red, and the episode's icon on a big paper circle.
  Paws & Claws (long video, 1280x720): a bright frame with the whole club smiling + 1-3 words in
                rainbow letters with a thick white and navy outline (classic kids-channel style).

Text and frame can be fixed per episode in its JSON: "thumb": {"text": "...", "highlight": "...", "at": 12.5,
"icon": "clock"}. Anything missing is chosen automatically (frame by sharpness and colour, text by Claude).
"""
from __future__ import annotations

import html
import json
import os
import random
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "engine", "thumbs", "fonts")
EH_DIR = os.path.join(ROOT, "engine", "everyhow")
CHROME_ARGS = ["--allow-file-access-from-files"]
MAX_BYTES = 2_000_000  # YouTube's limit for a custom thumbnail

FIT_JS = """
for (const el of document.querySelectorAll('[data-fit]')) {
  const max = +el.dataset.fit, lines = +(el.dataset.lines || 2);
  let s = +el.dataset.size;
  const lh = () => parseFloat(getComputedStyle(el).lineHeight);
  while (s > 30 && (el.scrollWidth > max || el.offsetHeight > lh() * lines + 4)) { s -= 4; el.style.fontSize = s + 'px'; }
}
window.done = true;
"""


def _font(name: str, file: str, weight: int = 400) -> str:
    return f"@font-face{{font-family:{name};font-weight:{weight};src:url(file://{os.path.join(FONTS, file)})}}"


def render(page_html: str, out: str, w: int, h: int) -> str:
    from playwright.sync_api import sync_playwright
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(page_html)
        src = f.name
    kw = {"args": CHROME_ARGS}
    if os.environ.get("CHROME_PATH"):
        kw["executable_path"] = os.environ["CHROME_PATH"]
    with sync_playwright() as p:
        b = p.chromium.launch(**kw)
        pg = b.new_page(viewport={"width": w, "height": h})
        pg.goto("file://" + src)
        pg.evaluate("document.fonts.ready")
        pg.wait_for_function("window.done === true", timeout=30000)
        q = 92
        while True:
            data = pg.screenshot(type="jpeg", quality=q)
            if len(data) < MAX_BYTES or q <= 60:
                break
            q -= 8
        b.close()
    os.unlink(src)
    with open(out, "wb") as f:
        f.write(data)
    return out


# ---------- frames ----------

def duration(video: str) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                                capture_output=True, text=True, check=True).stdout)


def grab(video: str, t: float, out: str) -> str:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-q:v", "2", out],
                   check=True)
    return out


def best_frame(video: str, out: str, start: float = 2.0, end_pad: float = 6.0, step: float = 3.0) -> tuple[str, float]:
    """Sharpest, most colourful, well-lit frame (skips the first seconds and the outro)."""
    import numpy as np
    from PIL import Image, ImageFilter
    d = duration(video)
    best, best_t = -1.0, start
    with tempfile.TemporaryDirectory() as tmp:
        t = start
        while t < max(start + 0.1, d - end_pad):
            f = grab(video, t, os.path.join(tmp, "f.jpg"))
            im = Image.open(f).convert("RGB")
            im.thumbnail((640, 640))
            sharp = np.asarray(im.convert("L").filter(ImageFilter.FIND_EDGES)).astype(float).var()
            hsv = np.asarray(im.convert("HSV")).astype(float)
            score = sharp * 0.5 + hsv[..., 1].mean() * 3 + hsv[..., 2].mean()
            if score > best:
                best, best_t = score, t
            t += step
    return grab(video, best_t, out), best_t


# ---------- text ----------

def thumb_text(series: str, ep: dict) -> dict:
    """{"text", "highlight", "icon"} from the episode JSON, else written by Claude."""
    th = dict(ep.get("thumb") or {})
    if th.get("text"):
        return th
    from .writer import _ask
    if series == "every_how":
        rule = ("3 to 6 words, a question or a surprising claim that makes people need to click, about the episode's "
                "question. No clickbait lies, no profanity, no shock words. Also pick the single most important word "
                "as highlight.")
    elif series == "paws_claws":
        rule = ("1 to 3 words a toddler's parent instantly understands, upbeat, ending with '!', e.g. 'BATH TIME!'.")
    else:
        rule = ("2 to 4 words, the scariest or most surprising idea of the episode, e.g. 'NO POWER FOR 30 DAYS'. "
                "Also pick the one word to colour yellow as highlight.")
    user = (f"Episode title: {ep.get('title')}\nDescription: {ep.get('description', '')[:600]}\n"
            f"Question: {ep.get('question', '')}\n\nWrite the thumbnail text: {rule} "
            'Reply JSON only: {"text": "...", "highlight": "..."}')
    raw = _ask("You write YouTube thumbnail text. Short, honest, irresistible.", user)
    try:
        got = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
    except Exception:
        got = {"text": ep.get("title", "")[:30]}
    th.update({k: v for k, v in got.items() if k in ("text", "highlight")})
    return th


def _words(text: str, highlight: str | None, cls: str) -> str:
    out = []
    hl = (highlight or "").strip().lower()
    for w in text.split():
        bare = w.strip("?!.,:'\"").lower()
        out.append(f'<span class="{cls}">{html.escape(w)}</span>' if hl and bare == hl else html.escape(w))
    return " ".join(out)


# ---------- designs ----------

def imagine_you(ep: dict, video: str, out: str) -> dict:
    th = thumb_text("imagine_you", ep)
    with tempfile.TemporaryDirectory() as tmp:
        fr = os.path.join(tmp, "f.jpg")
        if th.get("at") is not None:
            grab(video, float(th["at"]), fr)
        else:
            _, th["at"] = best_frame(video, fr)
        words = _words(th["text"].upper(), th.get("highlight", "").upper(), "hl")
        page = f"""<!doctype html><html><head><style>{_font('Anton', 'anton-latin-400-normal.woff2')}
html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:#000}}
.bg{{position:absolute;inset:0;background:url(file://{fr}) center/cover;filter:saturate(1.2) contrast(1.08)}}
.blur{{position:absolute;left:0;right:0;top:0;height:1180px;backdrop-filter:blur(18px) brightness(.55);
  -webkit-mask-image:linear-gradient(#000 0%,#000 78%,transparent 100%)}}
.shade{{position:absolute;inset:0;background:linear-gradient(#000a 0%,#0004 40%,#0000 60%)}}
.t{{position:absolute;left:60px;right:60px;top:260px;font:400 210px/1.0 Anton;color:#fff;text-align:center;
   text-transform:uppercase;-webkit-text-stroke:14px #000;paint-order:stroke fill;letter-spacing:1px;
   text-shadow:0 10px 0 #000,0 0 40px #0009}}
.hl{{color:#ffd400}}</style></head><body><div class="bg"></div><div class="blur"></div><div class="shade"></div>
<div class="t" data-fit="960" data-size="210" data-lines="3">{words}</div>
<script>document.fonts.ready.then(()=>{{{FIT_JS}}})</script></body></html>"""
        render(page, out, 1080, 1920)
    return th


def every_how(ep: dict, out: str) -> dict:
    th = thumb_text("every_how", ep)
    icon = th.get("icon")
    if not icon:
        for sec in ep.get("sections", []):
            for sc in sec.get("scenes", []):
                icon = icon or sc.get("visual", {}).get("icon")
        icon = icon or "question"
        th["icon"] = icon
    rng = random.Random(ep.get("title", ""))
    circle = rng.choice(["#e4572e", "#2f7fbf", "#3a9e6e", "#f2a541", "#8e5bbf", "#d64f7c"])
    words = _words(th["text"], th.get("highlight"), "hl")
    page = f"""<!doctype html><html><head><style>
@font-face{{font-family:Kalam;font-weight:700;src:url(file://{EH_DIR}/fonts/kalam-latin-700-normal.woff2)}}
@font-face{{font-family:Hand;src:url(file://{EH_DIR}/fonts/patrick-hand-latin-400-normal.woff2)}}
html,body{{margin:0;width:1280px;height:720px;overflow:hidden;background:#f3ead6}}
.grain{{position:absolute;inset:0;background:
  radial-gradient(circle at 20% 30%,#fff8 0,#fff0 40%),radial-gradient(circle at 80% 90%,#d9c9a6 0,#d9c9a600 45%)}}
.band{{position:absolute;left:-20px;right:-20px;bottom:-30px;height:150px;background:#e2d3b1;
  clip-path:polygon(0 30%,8% 18%,17% 32%,27% 14%,38% 28%,49% 12%,60% 30%,71% 16%,82% 29%,92% 13%,100% 26%,100% 100%,0 100%);
  filter:drop-shadow(0 -4px 0 #cbb88f)}}
.t{{position:absolute;left:64px;top:70px;width:690px;font:700 120px/1.02 Kalam;color:#2a2320;letter-spacing:-1px}}
.hl{{white-space:nowrap;color:#c8341f;padding:0 6px;
  background:linear-gradient(transparent 58%,#ffcf3f 58%,#ffcf3f 86%,transparent 86%)}}
.disc{{position:absolute;right:70px;top:120px;width:420px;height:420px;border-radius:50%;background:{circle};
  box-shadow:8px 12px 0 #0002,inset 0 0 0 10px #ffffff22;transform:rotate(-4deg)}}
.disc svg{{position:absolute;left:70px;top:70px;width:280px;height:280px;fill:#fff;filter:drop-shadow(4px 6px 0 #0003)}}
.q{{position:absolute;right:52px;top:60px;width:150px;height:150px;border-radius:50%;background:#ffcf3f;
  font:700 120px/150px Kalam;color:#2a2320;text-align:center;transform:rotate(10deg);box-shadow:6px 8px 0 #0002}}
.brand{{position:absolute;left:66px;bottom:36px;font:400 40px Hand;color:#5b4a3a}}
.brand b{{font:700 40px Kalam;color:#2a2320}}
</style><script src="file://{EH_DIR}/assets.js"></script></head><body><div class="grain"></div><div class="band"></div>
<div class="t" data-fit="690" data-size="120" data-lines="4">{words}</div>
<div class="disc"><svg viewBox="0 0 256 256"><path id="ic"/></svg></div><div class="q">?</div>
<div class="brand"><b>Every How</b> explained</div>
<script>
const n = {json.dumps(icon)}.toLowerCase().trim().replace(/[\\s_]+/g, '-');
document.getElementById('ic').setAttribute('d', ICONS[n] || ICONS[n + 's'] || ICONS['question']);
document.fonts.ready.then(()=>{{{FIT_JS}}})</script></body></html>"""
    render(page, out, 1280, 720)
    return th


def paws_claws(ep: dict, video: str, out: str) -> dict:
    th = thumb_text("paws_claws", ep)
    with tempfile.TemporaryDirectory() as tmp:
        fr = os.path.join(tmp, "f.jpg")
        if th.get("at") is not None:
            grab(video, float(th["at"]), fr)
        else:
            _, th["at"] = best_frame(video, fr, start=3.0, end_pad=8.0, step=4.0)
        bedtime = "lullaby" in ep.get("title", "").lower() or "goodnight" in th["text"].lower()
        colours = (["#ffe066", "#ffd6a5", "#fff3b0"] if bedtime else
                   ["#ff4d6d", "#ff9f1c", "#ffd60a", "#3ddc97", "#4cc9f0", "#9d4edd"])
        letters, i = [], 0
        for ch in th["text"].upper():
            if ch.strip():
                letters.append(f'<span style="color:{colours[i % len(colours)]}">{html.escape(ch)}</span>')
                i += 1
            else:
                letters.append(" ")
        text = "".join(letters)
        page = f"""<!doctype html><html><head><style>{_font('Fredoka', 'fredoka-latin-700-normal.woff2', 700)}
html,body{{margin:0;width:1280px;height:720px;overflow:hidden;background:#fff}}
.bg{{position:absolute;inset:-4%;background:url(file://{fr}) center 35%/cover;filter:saturate(1.18) contrast(1.05) brightness(1.03)}}
.wrap{{position:absolute;left:30px;right:30px;bottom:26px;text-align:center;transform:rotate(-2deg)}}
.t{{display:inline-block;font:700 150px/1.0 Fredoka;letter-spacing:2px;white-space:nowrap}}
.l1,.l2,.l3{{position:absolute;left:0;right:0;top:0}}
.l1{{color:#1f1a5a!important;-webkit-text-stroke:34px #1f1a5a;filter:drop-shadow(0 10px 0 #1f1a5a)}}
.l1 span{{color:#1f1a5a!important}}
.l2{{-webkit-text-stroke:16px #fff}} .l2 span{{color:#fff!important}}
.box{{position:relative}}
</style></head><body><div class="bg"></div>
<div class="wrap"><div class="box t" data-fit="1200" data-size="150" data-lines="1">
<div class="l1 t">{text}</div><div class="l2 t">{text}</div><div class="l3 t" style="position:relative">{text}</div></div></div>
<script>document.fonts.ready.then(()=>{{
  const box=document.querySelector('.box'); let s=150;
  while (s>60 && box.scrollWidth>1200) {{ s-=6; document.querySelectorAll('.t').forEach(e=>e.style.fontSize=s+'px'); }}
  window.done=true; }})</script></body></html>"""
        render(page, out, 1280, 720)
    return th


def make(series: str, ep: dict, video: str | None, out: str) -> dict:
    """Render the thumbnail for one episode. video = the full video file (not needed for Every How)."""
    if series == "every_how":
        return every_how(ep, out)
    if series == "paws_claws":
        return paws_claws(ep, video, out)
    return imagine_you(ep, video, out)
