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


def add_thumbnail(done: dict, series: str, ep: dict, video: str | None, link_key: str = "youtube"):
    """Give the YouTube video its custom thumbnail once (Haseeb, 1 Nov 2026). Never blocks posting."""
    link = str(done.get(link_key, ""))
    if not link.startswith("http") or done.get("thumbnail") == "set":
        return
    import tempfile
    from . import thumbs, youtube
    vid = link.rstrip("/").rsplit("=", 1)[-1].rsplit("/", 1)[-1]
    try:
        out = os.path.join(tempfile.mkdtemp(), "thumb.jpg")
        thumbs.make(series, ep, video, out)
        done["thumbnail"] = youtube.set_thumbnail(ACCOUNTS[series]["youtube"], vid, out)
        print(f"thumbnail set on {vid}")
    except Exception as e:
        traceback.print_exc()
        done["thumbnail"] = f"failed: {e}"[:300]
        if "verified by phone" in str(e):
            try:
                from . import mailer
                mailer.send(f"Turn on custom thumbnails: {series.replace('_', ' ').title()} channel",
                            f"The video went live, but YouTube refused its custom thumbnail:\n\n{e}\n\n"
                            f"Once the channel is verified, run Video autopilot with cmd thumbs and series {series} "
                            "and every live video gets its thumbnail.")
            except Exception:
                traceback.print_exc()


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


def descriptions(ep: dict, timeline_path: str, full_url: str = "") -> tuple[str, str]:
    cfg = ACCOUNTS["every_how"]
    srcs = "\n".join(f"- {s.get('title')}: {s.get('url')}" for s in ep.get("sources", []))
    chap = chapters(timeline_path)
    long_desc = (f"{ep.get('description', '')}\n\n" + (f"Chapters\n{chap}\n\n" if chap else "") +
                 f"Sources\n{srcs}\n\n{cfg['hashtags']}")[:4900]
    short_desc = (f"{ep.get('description', '')}\n\n" + (f"Full video: {full_url}\n\n" if full_url else "") +
                  "#Shorts #EveryHow #explained")[:4900]
    return long_desc, short_desc


def stage_every_how(ep: dict, video: dict) -> dict:
    """Upload the full episode and the vertical cut to YouTube as PRIVATE videos for Haseeb to review.
    Returns {"full": id, "short": id}. Nothing is public until publish_every_how flips them."""
    from . import youtube
    cfg = ACCOUNTS["every_how"]
    long_desc, _ = descriptions(ep, video.get("timeline", ""))
    full = youtube.upload(cfg["youtube"], video["full"], ep["title"], long_desc, ep.get("tags", []), False,
                          category="27", privacy="private").rsplit("=", 1)[-1]
    th = {"youtube": f"https://youtube.com/watch?v={full}"}
    add_thumbnail(th, "every_how", ep, video["full"])  # on the private copy too, so Haseeb reviews it
    _, short_desc = descriptions(ep, video.get("timeline", ""), f"https://youtube.com/watch?v={full}")
    short = youtube.upload(cfg["youtube"], video["short"], f"{ep['title'][:88]} #Shorts", short_desc,
                           ep.get("tags", []), False, category="27", privacy="private").rsplit("=", 1)[-1]
    return {"full": full, "short": short, "thumbnail": th.get("thumbnail", "")}


def publish_every_how(private: dict, done: dict) -> dict:
    """Approved: make the reviewed private videos public (full first, so the Short's link works)."""
    from . import youtube
    cfg = ACCOUNTS["every_how"]
    _run(done, "youtube", lambda: youtube.set_privacy(cfg["youtube"], private["full"], "public"))
    _run(done, "youtube_short", lambda: youtube.set_privacy(cfg["youtube"], private["short"], "public"))
    return done


def publish(series: str, ep: dict, video: str, done: dict | None = None) -> dict:
    from . import facebook, instagram, youtube
    cfg = ACCOUNTS[series]
    if series == "every_how":
        raise RuntimeError("Every How publishes via publish_every_how (private review videos), not publish()")
    done = dict(done or {})
    desc = ep.get("description", "")
    full = short = video
    if isinstance(video, dict):  # premade series: long episode to YouTube, vertical cut to Reels
        full, short = video["full"], video["short"]
    _run(done, "youtube", lambda: youtube.upload(cfg["youtube"], full, ep["title"], f"{desc}\n\n{cfg['hashtags']}",
                                                 ep.get("tags", []), cfg["made_for_kids"]),
         lambda: youtube.find_existing(cfg["youtube"], ep["title"]))
    add_thumbnail(done, series, ep, full)
    caption = ep.get("caption") or f"{ep['title']}.\n\n{desc} Comment A or B.\n\n{cfg['ig_hashtags']}"
    _run(done, "instagram", lambda: instagram.upload(cfg["instagram"], short, caption, os.path.basename(short)),
         lambda: instagram.find_existing(cfg["instagram"], ep["title"]))
    _run(done, "facebook", lambda: facebook.upload(cfg["instagram"], short, caption, os.path.basename(short)),
         lambda: facebook.find_existing(cfg["instagram"], ep["title"]))
    # TikTok is posted by the VPS poster (vps/ttposter.py); tiktok.upload (inbox drafts) stays as a fallback.
    return done
