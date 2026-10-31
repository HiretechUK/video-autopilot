"""Video autopilot pipeline.

  python -m autopilot.pipeline make imagine_you   write + render a new episode, email it for approval
  python -m autopilot.pipeline check              read replies: approve -> publish, notes -> revise + resend, skip

Episode scripts are committed to episodes/; videos are re-rendered from the script when publishing
(rendering is deterministic), so nothing large is stored in the repo.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone

from . import mailer, writer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "autopilot", "state.json")
EPDIR = os.path.join(ROOT, "episodes")
OUT = os.path.join(ROOT, "out")
SERIES = {"imagine_you": {"prefix": "IY", "name": "Imagine You", "builder": "engine/build_short.py"}}

HOW_TO = """How to reply (just reply to this email):
  approved            -> it gets posted
  any notes           -> I rewrite it with your notes and send the new version
                         e.g. "make the hook scarier and change the ending to a nuclear bunker"
  skip                -> drop this episode
"""


def load():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {"episodes": {}, "seen": []}


def save(st):
    json.dump(st, open(STATE, "w"), indent=1)


def render(series: str, ep_path: str) -> str:
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, os.path.basename(ep_path).replace(".json", ".mp4"))
    subprocess.run([sys.executable, os.path.join(ROOT, SERIES[series]["builder"]), ep_path, out], check=True)
    return out


def script_text(ep: dict) -> str:
    return "\n".join(f"{i}. {s['narration'].replace('[pause] ', '… ')}" for i, s in enumerate(ep["scenes"], 1))


def email_for_approval(ref: str, rec: dict, ep: dict, video: str):
    v = rec.get("version", 1)
    subject = f"{SERIES[rec['series']]['name']} #{rec['number']:02d} for approval{' (v' + str(v) + ')' if v > 1 else ''} [{ref}]"
    body = (f"{ep['title']}\n\n{ep.get('description', '')}\n\nScript:\n{script_text(ep)}\n\n"
            f"The video is attached.\n\n{HOW_TO}")
    mailer.send(subject, body, [video])


def make(series: str):
    st = load()
    eps = [e for e in st["episodes"].values() if e["series"] == series]
    number = max([e["number"] for e in eps] or [0]) + 1
    recent = [e["title"] for e in sorted(eps, key=lambda e: e["number"])[-12:]]
    lessons = open(os.path.join(ROOT, "autopilot", f"lessons_{series}.md")).read() \
        if os.path.exists(os.path.join(ROOT, "autopilot", f"lessons_{series}.md")) else ""
    ep = writer.write_episode(series, number, recent, lessons)
    ref = f"{SERIES[series]['prefix']}-{number:02d}"
    os.makedirs(EPDIR, exist_ok=True)
    path = os.path.join(EPDIR, f"{ref}.json")
    json.dump(ep, open(path, "w"), indent=1)
    video = render(series, path)
    rec = {"series": series, "number": number, "title": ep["title"], "status": "pending", "version": 1,
           "file": os.path.relpath(path, ROOT), "created": datetime.now(timezone.utc).isoformat()}
    st["episodes"][ref] = rec
    save(st)
    email_for_approval(ref, rec, ep, video)
    print("sent", ref, ep["title"])


def check():
    st = load()
    pending = [r for r, e in st["episodes"].items() if e["status"] == "pending"]
    seen = set(st["seen"])
    for ref, mid, text in mailer.fetch_replies(pending, seen):
        st["seen"].append(mid)
        rec = st["episodes"][ref]
        action, notes = mailer.parse(text)
        path = os.path.join(ROOT, rec["file"])
        ep = json.load(open(path))
        try:
            if action == "approve":
                rec["status"] = "approved"
                rec["approved"] = datetime.now(timezone.utc).isoformat()
                mailer.send(f"Approved: {ep['title']} [{ref}]", "It will be posted on the next run to every connected platform.")
            elif action == "skip":
                rec["status"] = "skipped"
                mailer.send(f"Skipped [{ref}]", f"Dropped: {ep['title']}")
            else:
                new = writer.write_episode(rec["series"], rec["number"], [], "", notes=notes, previous=ep)
                json.dump(new, open(path, "w"), indent=1)
                rec["version"] = rec.get("version", 1) + 1
                rec["title"] = new["title"]
                email_for_approval(ref, rec, new, render(rec["series"], path))
        except Exception:
            traceback.print_exc()
            mailer.send(f"Problem with {ref}", f"Your reply was:\n{text}\n\nError:\n{traceback.format_exc()[-2000:]}")
        save(st)
    publish_queue(st)


PLATFORMS = ("youtube", "instagram")  # TikTok: posted by the VPS (vps/ttposter.py)


def publish_queue(st):
    """Post every approved episode that is not yet live on all platforms (oldest first). Safe to rerun."""
    from . import publish
    for ref, rec in sorted(st["episodes"].items(), key=lambda kv: kv[1].get("approved", "")):
        if rec["status"] not in ("approved", "partly_published"):
            continue
        links = rec.get("links", {})
        if all(str(links.get(p, "")).startswith("http") for p in PLATFORMS):
            continue
        path = os.path.join(ROOT, rec["file"])
        ep = json.load(open(path))
        before = dict(links)
        links = publish.publish(rec["series"], ep, render(rec["series"], path), links)
        rec["links"] = links
        live = {k: v for k, v in links.items() if str(v).startswith("http")}
        rec["status"] = "published" if len(live) == len(PLATFORMS) else ("partly_published" if live else "approved")
        save(st)
        new = {k: v for k, v in live.items() if before.get(k) != v}
        if new:
            mailer.send(f"Posted: {ep['title']} [{ref}]", "\n".join(f"  {k}: {v}" for k, v in links.items()))


def connect(platform: str, series: str):
    from . import instagram, tiktok, youtube
    name = SERIES[series]["name"]
    if platform == "youtube":
        youtube.connect(series, name)
    elif platform == "instagram":
        instagram.connect(series, name)
    elif platform == "tiktok":
        tiktok.connect(series, name)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    arg = sys.argv[2] if len(sys.argv) > 2 else "imagine_you"
    if cmd == "make":
        make(arg)
    elif cmd.startswith("connect_"):
        connect(cmd.split("_", 1)[1], arg)
    elif cmd == "publish":
        publish_queue(load())
    else:
        check()
