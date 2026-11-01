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
SERIES = {"imagine_you": {"prefix": "IY", "name": "Imagine You", "builder": "engine/build_short_v2.py"},
          # Paws & Claws episodes are made ahead in a batch (Higgsfield + ACE-Step) and stored as release assets;
          # each one goes live on its post_after date (Haseeb, 1 Nov: make them all at once, post periodically).
          "paws_claws": {"prefix": "PC", "name": "Paws & Claws Club", "premade": True},
          # Every How (Haseeb, 1 Nov 2026): a 5-7 minute explainer every day, YouTube only (full video + Short).
          # Each version is uploaded to YouTube as PRIVATE for review; "approved" flips both videos to public.
          "every_how": {"prefix": "EH", "name": "Every How", "builder": "engine/build_everyhow.py",
                        "staged": True, "every_days": 1,
                        # set True to stop automatic episodes and posting (manual make/resend still work)
                        "paused": False}}
RELEASE = "https://github.com/HiretechUK/video-autopilot/releases/download/paws-episodes/"

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


def fetch(name: str) -> str:
    """Download a premade episode file from the paws-episodes release (cached in out/)."""
    import requests
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, name)
    if not os.path.exists(dst):
        with requests.get(RELEASE + name, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(dst, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
    return dst


def _script_hash(ep_path: str) -> str:
    import hashlib
    ep = json.load(open(ep_path))
    core = {k: ep.get(k) for k in ("title", "sections", "short")}
    return hashlib.sha1(json.dumps(core, sort_keys=True).encode()).hexdigest()[:8]


def _render_cached(series: str, ep_path: str) -> dict:
    """Full video + vertical cut + timeline, fetched from the series release if this exact script was rendered
    before, otherwise built and uploaded there. Revisions change the script, so they get a fresh render."""
    import requests
    tag = SERIES[series]["release"]
    ref = os.path.basename(ep_path).replace(".json", "")
    stem = f"{ref}-{_script_hash(ep_path)}"
    names = {"full": f"{stem}.mp4", "short": f"{stem}_short.mp4", "timeline": f"{stem}.timeline.json"}
    os.makedirs(OUT, exist_ok=True)
    paths = {k: os.path.join(OUT, n) for k, n in names.items()}
    base = f"https://github.com/HiretechUK/video-autopilot/releases/download/{tag}/"
    if not all(os.path.exists(p) for p in paths.values()):
        try:
            for k, n in names.items():
                with requests.get(base + n, stream=True, timeout=600) as r:
                    r.raise_for_status()
                    with open(paths[k], "wb") as f:
                        for chunk in r.iter_content(1 << 20):
                            f.write(chunk)
            print("reusing render", stem)
        except Exception:
            subprocess.run([sys.executable, os.path.join(ROOT, SERIES[series]["builder"]), ep_path, paths["full"],
                            "--short", paths["short"]], check=True)
            gh = lambda *a: subprocess.run(["gh", *a, "-R", "HiretechUK/video-autopilot"], check=False)
            if gh("release", "view", tag).returncode:
                gh("release", "create", tag, "--title", f"{SERIES[series]['name']} episodes",
                   "--notes", "Rendered episodes (made by the autopilot; reused when posting).")
            gh("release", "upload", tag, *paths.values(), "--clobber")
    paths["url"] = base + names["full"]
    return paths


def render(series: str, ep_path: str):
    if SERIES[series].get("release"):
        return _render_cached(series, ep_path)
    if SERIES[series].get("staged"):  # full episode + vertical cut + timeline
        os.makedirs(OUT, exist_ok=True)
        stem = os.path.join(OUT, os.path.basename(ep_path).replace(".json", ""))
        subprocess.run([sys.executable, os.path.join(ROOT, SERIES[series]["builder"]), ep_path, stem + ".mp4",
                        "--short", stem + "_short.mp4"], check=True)
        return {"full": stem + ".mp4", "short": stem + "_short.mp4", "timeline": stem + ".timeline.json"}
    if SERIES[series].get("premade"):  # full episode for YouTube, vertical cut for Reels/TikTok
        ep = json.load(open(ep_path))
        return {"full": fetch(ep["video"]), "short": fetch(ep["short"])}
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, os.path.basename(ep_path).replace(".json", ".mp4"))
    subprocess.run([sys.executable, os.path.join(ROOT, SERIES[series]["builder"]), ep_path, out], check=True)
    return out


def script_text(ep: dict) -> str:
    scenes = ep.get("scenes") or [s for sec in ep.get("sections", []) for s in sec["scenes"]]
    return "\n".join(f"{i}. {s['narration'].replace('[pause] ', '… ')}" for i, s in enumerate(scenes, 1))


def stage(ref: str, rec: dict, ep: dict, path: str) -> dict:
    """Every How: render this version and upload it to YouTube as private videos (once per version)."""
    from . import publish
    pv = rec.get("private") or {}
    if pv.get("version") == rec.get("version", 1) and pv.get("full") and pv.get("short"):
        return pv
    video = render(rec["series"], path)
    ids = publish.stage_every_how(ep, video)
    mins = None
    try:
        mins = round(json.load(open(video["timeline"]))["duration"] / 60, 1)
    except Exception:
        pass
    old = [v for v in (pv.get("full"), pv.get("short")) if v]
    rec["private"] = dict(ids, version=rec.get("version", 1), minutes=mins, superseded=rec.get("private", {}).get("superseded", []) + old)
    return rec["private"]


def email_for_approval(ref: str, rec: dict, ep: dict, video):
    v = rec.get("version", 1)
    subject = f"{SERIES[rec['series']]['name']} #{rec['number']:02d} for approval{' (v' + str(v) + ')' if v > 1 else ''} [{ref}]"
    if rec["series"] == "every_how":  # `video` is rec["private"]: the private YouTube review copies
        mins = f" ({video['minutes']} min)" if video.get("minutes") else ""
        ad = ep.get("ad_safety") or {}
        fc = ep.get("factcheck") or {}
        flag = "YELLOW: may get limited ads. " if ad.get("rating") == "yellow" else ""
        body = (f"{ep['title']}{mins}\n\n{flag}Ad safety: {ad.get('rating', '?')} ({ad.get('reason', '')})\n"
                f"Fact-check: {'passed' if fc.get('ok') else 'see notes below'}. {fc.get('summary', '')}\n" +
                "".join(f"  - scene {i.get('scene')}: {i.get('problem')} (fix: {i.get('fix')})\n" for i in fc.get("open_issues", [])) +
                f"\nWatch it on YouTube (private until you approve; open while signed in to the Every How account):\n"
                f"  Full episode: https://youtube.com/watch?v={video['full']}\n"
                f"  Short: https://youtube.com/shorts/{video['short']}\n"
                + (f"  (Older versions stay private: {', '.join(video.get('superseded', []))}. Delete them in YouTube Studio if you like.)\n"
                   if video.get("superseded") else "") + "\n"
                f"{ep.get('description', '')}\n\nSources:\n" +
                "".join(f"  - {s.get('title')}: {s.get('url')}\n" for s in ep.get("sources", [])) +
                f"\nScript:\n{script_text(ep)}\n\n{HOW_TO.replace('it gets posted', 'both videos go public on YouTube').replace('make the hook scarier and change the ending to a nuclear bunker', 'shorter intro, and add a map of where it happened')}")
        mailer.send(subject, body)
        return
    body = (f"{ep['title']}\n\n{ep.get('description', '')}\n\nScript:\n{script_text(ep)}\n\n"
            f"The video is attached.\n\n{HOW_TO}")
    mailer.send(subject, body, [video])


EVERY_DAYS = float(os.environ.get("EPISODE_EVERY_DAYS", "2"))  # Haseeb, 31 Oct: an episode every 2nd day


def _similar(title: str, titles: list[str], cutoff: float = 0.85) -> str | None:
    """Return an earlier title that is (nearly) the same story as `title`, if any."""
    import difflib
    t = title.strip().lower()
    for old in titles:
        if difflib.SequenceMatcher(None, t, old.strip().lower()).ratio() >= cutoff:
            return old
    return None


def dupcheck(series: str):
    """Read-only test of the duplicate guards: look up each posted episode on every platform."""
    from . import facebook, instagram, youtube
    from .publish import ACCOUNTS
    cfg = ACCOUNTS[series]
    for ref, rec in load()["episodes"].items():
        if rec["series"] != series or not rec.get("links"):
            continue
        for name, fn in (("youtube", lambda: youtube.find_existing(cfg["youtube"], rec["title"])),
                         ("instagram", lambda: instagram.find_existing(cfg["instagram"], rec["title"])),
                         ("facebook", lambda: facebook.find_existing(cfg["instagram"], rec["title"]))):
            try:
                print(f"{ref} {name}: found {fn()}  (state has {rec['links'].get(name)})")
            except Exception as e:
                print(f"{ref} {name}: CHECK FAILED {e!r}")


def make(series: str, scheduled: bool = False):
    if SERIES[series].get("paused") and scheduled:
        print(f"{series} is paused (pipeline.SERIES); no automatic episode")
        return
    st = load()
    eps = [e for e in st["episodes"].values() if e["series"] == series]
    # Every make (scheduled, watchdog or manual) only runs if the last episode is due, so two runs can never
    # create two episodes. A deliberate extra episode needs the workflow input force=yes.
    if os.environ.get("FORCE_MAKE", "").lower() not in ("yes", "1", "true") and eps:
        last = max(datetime.fromisoformat(e["created"]) for e in eps)
        age_h = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        every = SERIES[series].get("every_days", EVERY_DAYS)
        due = every * 24 - min(12, every * 6)  # slack: 12 h for every 2nd day, 6 h for daily; never two in a row
        if age_h < due:
            print(f"last {series} episode is {age_h:.0f} h old; next one is due after {due:.0f} h")
            return
    number = max([e["number"] for e in eps] or [0]) + 1
    titles = [e["title"] for e in sorted(eps, key=lambda e: e["number"])]
    recent = titles[-40:]
    lessons = open(os.path.join(ROOT, "autopilot", f"lessons_{series}.md")).read() \
        if os.path.exists(os.path.join(ROOT, "autopilot", f"lessons_{series}.md")) else ""
    ep = writer.write_episode(series, number, recent, lessons)
    clash = _similar(ep["title"], titles)
    if clash:  # never make the same story twice: rewrite once, then refuse
        print(f"title too close to an earlier episode ({clash}); rewriting")
        ep = writer.write_episode(series, number, recent, lessons,
                                  notes=f"Your first idea was too close to an earlier episode: '{clash}'. Pick a clearly different scenario.")
        clash = _similar(ep["title"], titles)
        if clash:
            raise RuntimeError(f"new episode is a near-duplicate of '{clash}', not made; will retry next run")
    ref = f"{SERIES[series]['prefix']}-{number:02d}"
    os.makedirs(EPDIR, exist_ok=True)
    path = os.path.join(EPDIR, f"{ref}.json")
    json.dump(ep, open(path, "w"), indent=1)
    rec = {"series": series, "number": number, "title": ep["title"], "status": "pending", "version": 1,
           "file": os.path.relpath(path, ROOT), "created": datetime.now(timezone.utc).isoformat()}
    if SERIES[series].get("staged"):
        st["episodes"][ref] = rec
        save(st)  # recorded first, so a failed upload can never lead to a second episode being made
        video = stage(ref, rec, ep, path)
    else:
        video = render(series, path)
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
                video = stage(ref, rec, new, path) if SERIES[rec["series"]].get("staged") else render(rec["series"], path)
                email_for_approval(ref, rec, new, video)
        except Exception:
            traceback.print_exc()
            mailer.send(f"Problem with {ref}", f"Your reply was:\n{text}\n\nError:\n{traceback.format_exc()[-2000:]}")
        save(st)
    publish_queue(st)


PLATFORMS = ("youtube", "instagram", "facebook")  # TikTok: posted by the VPS (vps/ttposter.py)
SERIES_PLATFORMS = {"every_how": ("youtube", "youtube_short"),  # Haseeb, 1 Nov 2026: YouTube only for now
                    "paws_claws": ("youtube",)}  # one episode every 3rd day, YouTube first (Instagram/Facebook not connected)


def platforms(series: str):
    return SERIES_PLATFORMS.get(series, PLATFORMS)


def publish_queue(st):
    """Post every approved episode that is not yet live on all platforms (oldest first). Safe to rerun."""
    from . import publish
    for ref, rec in sorted(st["episodes"].items(), key=lambda kv: kv[1].get("approved", "")):
        if rec["status"] == "scheduled" and datetime.now(timezone.utc) >= datetime.fromisoformat(rec["post_after"]):
            rec["status"] = "approved"
            rec["approved"] = rec["post_after"]
        if rec["status"] not in ("approved", "partly_published"):
            continue
        if SERIES.get(rec["series"], {}).get("paused"):
            print(f"{ref}: {rec['series']} is paused, not posting yet")
            continue
        links = rec.get("links", {})
        if all(str(links.get(p, "")).startswith("http") for p in platforms(rec["series"])):
            continue
        path = os.path.join(ROOT, rec["file"])
        ep = json.load(open(path))
        before = dict(links)
        if SERIES[rec["series"]].get("staged"):
            if not (rec.get("private") or {}).get("full"):
                stage(ref, rec, ep, path)  # approved before a review copy existed: make one now
                save(st)
            links = publish.publish_every_how(rec["private"], links)
        else:
            links = publish.publish(rec["series"], ep, render(rec["series"], path), links)
        rec["links"] = links
        pl = platforms(rec["series"])
        live = {k: v for k, v in links.items() if k in pl and str(v).startswith("http")}  # TikTok is tracked separately
        rec["status"] = "published" if len(live) == len(pl) else ("partly_published" if live else "approved")
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
        make(arg, scheduled=os.environ.get("GITHUB_EVENT_NAME") == "schedule")
    elif cmd.startswith("connect_"):
        connect(cmd.split("_", 1)[1], arg)
    elif cmd == "dupcheck":
        dupcheck(arg)
    elif cmd == "publish":
        publish_queue(load())
    elif cmd == "replace":  # Every How: re-render a published episode, make the new copy public, old copy private
        from . import publish, youtube
        st = load()
        rec = st["episodes"][arg]
        p = os.path.join(ROOT, rec["file"])
        ep = json.load(open(p))
        old = dict(rec.get("private") or {})
        rec["version"] = rec.get("version", 1) + 1
        rec.pop("private", None)
        stage(arg, rec, ep, p)
        rec["private"]["superseded"] = [v for v in (old.get("full"), old.get("short")) if v] + old.get("superseded", [])
        save(st)
        if rec["status"] in ("published", "partly_published", "approved"):
            links = publish.publish_every_how(rec["private"], {})
            rec["links"] = links
            if all(str(links.get(k, "")).startswith("http") for k in ("youtube", "youtube_short")):
                for vid in (old.get("full"), old.get("short")):
                    if vid:
                        youtube.set_privacy(publish.ACCOUNTS["every_how"]["youtube"], vid, "private")
                rec["status"] = "published"
            save(st)
            mailer.send(f"Replaced: {ep['title']} [{arg}]", "A sharper copy is now public:\n" +
                        "\n".join(f"  {k}: {v}" for k, v in links.items()) +
                        f"\n\nThe old copies are now private (not deleted): {', '.join(rec['private']['superseded'])}.")
    elif cmd == "resend":  # email an existing pending episode for approval again: series=<REF>, e.g. EH-01
        st = load()
        rec = st["episodes"][arg]
        p = os.path.join(ROOT, rec["file"])
        ep = json.load(open(p))
        if SERIES[rec["series"]].get("staged"):
            video = stage(arg, rec, ep, p)
            save(st)
        else:
            video = render(rec["series"], p)
        email_for_approval(arg, rec, ep, video)
        save(st)
    else:
        check()
