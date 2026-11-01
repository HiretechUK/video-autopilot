"""Post an approved episode to every connected platform. A platform that is not connected yet, or fails,
is reported and retried on the next run; the others still post."""
from __future__ import annotations

import os
import traceback

ACCOUNTS = {  # series -> account key per platform
    "imagine_you": {"youtube": "imagine_you", "instagram": "imagine_you", "tiktok": "imagine_you", "made_for_kids": False,
                    "hashtags": "#Shorts #survival #whatwouldyoudo #imagineyou",
                    "ig_hashtags": "#survival #whatwouldyoudo #stranded #survivaltips #imagineyou"},
    "every_how": {"youtube": "every_how", "instagram": "every_how", "tiktok": "every_how", "made_for_kids": False,
                  "hashtags": "#EveryHow #explained #howitworks #education",
                  "ig_hashtags": "#everyhow #explained #howitworks #learnontiktok #didyouknow #education"},
    "paws_claws": {"youtube": "paws_claws", "instagram": "paws_claws", "tiktok": "paws_claws", "made_for_kids": True,
                   "hashtags": "#nurseryrhymes #kidssongs #toddlers #singalong #pawsandclawsclub",
                   "ig_hashtags": "#kidssongs #nurseryrhymes #toddleractivities #preschool #singalong #pawsandclawsclub"},
}


def _run(done: dict, platform: str, fn, find=None):
    """Post to one platform, unless it is already there. `find` looks on the platform itself for a post with
    this episode's title first, so a post that went live during a run that later failed is recorded, never
    posted twice (Haseeb, 1 Nov 2026: no duplicates, ever). If that check itself fails, nothing is posted
    and the platform is retried on the next run."""
    if str(done.get(platform, "")).startswith("http"):
        return
    try:
        if find:
            existing = find()
            if existing:
                print(f"{platform}: already posted, recording {existing}")
                done[platform] = existing
                return
        done[platform] = fn()
    except LookupError:
        done[platform] = "not connected yet"
    except Exception as e:  # keep going; retried next run
        traceback.print_exc()
        done[platform] = f"failed: {e}"[:300]


def chapters(timeline_path: str) -> str:
    """YouTube chapters from the section starts (needs 3+ chapters, first at 0:00, each 10 s or longer)."""
    import json
    try:
        tl = json.load(open(timeline_path))
    except Exception:
        return ""
    marks, last = [], None
    for sc in tl["scenes"]:
        if sc.get("visual", {}).get("type") == "end":
            continue
        h = sc.get("heading") or "Intro"
        if h != last:
            t = 0 if not marks else int(sc["start"])
            if marks and t - marks[-1][0] < 10:
                continue
            marks.append((t, h))
            last = h
    if len(marks) < 3:
        return ""
    return "\n".join(f"{t // 60}:{t % 60:02d} {h}" for t, h in marks)


def publish_every_how(ep: dict, video: dict, done: dict) -> dict:
    from . import facebook, instagram, youtube
    cfg = ACCOUNTS["every_how"]
    srcs = "\n".join(f"- {s.get('title')}: {s.get('url')}" for s in ep.get("sources", []))
    chap = chapters(video.get("timeline", ""))
    long_desc = (f"{ep.get('description', '')}\n\n" + (f"Chapters\n{chap}\n\n" if chap else "") +
                 f"Sources\n{srcs}\n\n{cfg['hashtags']}")[:4900]
    _run(done, "youtube", lambda: youtube.upload(cfg["youtube"], video["full"], ep["title"], long_desc,
                                                 ep.get("tags", []), False, category="27"),
         lambda: youtube.find_existing(cfg["youtube"], ep["title"]))
    short_title = f"{ep['title'][:88]} #Shorts"
    full_link = done.get("youtube", "")
    short_desc = (f"{ep.get('description', '')}\n\n" + (f"Full video: {full_link}\n\n" if str(full_link).startswith("http") else "") +
                  "#Shorts #EveryHow #explained")
    _run(done, "youtube_short", lambda: youtube.upload(cfg["youtube"], video["short"], short_title, short_desc,
                                                       ep.get("tags", []), False, category="27"),
         lambda: youtube.find_existing(cfg["youtube"], short_title))
    caption = (f"{ep['title']}\n\n{ep.get('description', '')}\n\nFull video on YouTube: Every How\n\n{cfg['ig_hashtags']}")
    _run(done, "instagram", lambda: instagram.upload(cfg["instagram"], video["short"], caption, os.path.basename(video["short"])),
         lambda: instagram.find_existing(cfg["instagram"], ep["title"]))
    _run(done, "facebook", lambda: facebook.upload_video(cfg["instagram"], video["full"], ep["title"], long_desc),
         lambda: facebook.find_existing_video(cfg["instagram"], ep["title"]))
    return done


def publish(series: str, ep: dict, video: str, done: dict | None = None) -> dict:
    from . import facebook, instagram, youtube
    cfg = ACCOUNTS[series]
    if series == "every_how":
        return publish_every_how(ep, video, dict(done or {}))
    done = dict(done or {})
    desc = ep.get("description", "")
    full = short = video
    if isinstance(video, dict):  # premade series: long episode to YouTube, vertical cut to Reels
        full, short = video["full"], video["short"]
    _run(done, "youtube", lambda: youtube.upload(cfg["youtube"], full, ep["title"], f"{desc}\n\n{cfg['hashtags']}",
                                                 ep.get("tags", []), cfg["made_for_kids"]),
         lambda: youtube.find_existing(cfg["youtube"], ep["title"]))
    caption = ep.get("caption") or f"{ep['title']}.\n\n{desc} Comment A or B.\n\n{cfg['ig_hashtags']}"
    _run(done, "instagram", lambda: instagram.upload(cfg["instagram"], short, caption, os.path.basename(short)),
         lambda: instagram.find_existing(cfg["instagram"], ep["title"]))
    _run(done, "facebook", lambda: facebook.upload(cfg["instagram"], short, caption, os.path.basename(short)),
         lambda: facebook.find_existing(cfg["instagram"], ep["title"]))
    # TikTok is posted by the VPS poster (vps/ttposter.py); tiktok.upload (inbox drafts) stays as a fallback.
    return done
