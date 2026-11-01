"""Post an approved episode to every connected platform. A platform that is not connected yet, or fails,
is reported and retried on the next run; the others still post."""
from __future__ import annotations

import os
import traceback

ACCOUNTS = {  # series -> account key per platform
    "imagine_you": {"youtube": "imagine_you", "instagram": "imagine_you", "tiktok": "imagine_you", "made_for_kids": False,
                    "hashtags": "#Shorts #survival #whatwouldyoudo #imagineyou",
                    "ig_hashtags": "#survival #whatwouldyoudo #stranded #survivaltips #imagineyou"},
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


def publish(series: str, ep: dict, video: str, done: dict | None = None) -> dict:
    from . import facebook, instagram, youtube
    cfg = ACCOUNTS[series]
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
