"""Post an approved episode to every connected platform. A platform that is not connected yet, or fails,
is reported and retried on the next run; the others still post."""
from __future__ import annotations

import os
import traceback

ACCOUNTS = {  # series -> account key per platform
    "imagine_you": {"youtube": "imagine_you", "instagram": "imagine_you", "tiktok": "imagine_you", "made_for_kids": False,
                    "hashtags": "#Shorts #survival #whatwouldyoudo #imagineyou",
                    "ig_hashtags": "#survival #whatwouldyoudo #stranded #survivaltips #imagineyou"},
}


def _run(done: dict, platform: str, fn):
    if str(done.get(platform, "")).startswith("http"):
        return
    try:
        done[platform] = fn()
    except LookupError:
        done[platform] = "not connected yet"
    except Exception as e:  # keep going; retried next run
        traceback.print_exc()
        done[platform] = f"failed: {e}"[:300]


def publish(series: str, ep: dict, video: str, done: dict | None = None) -> dict:
    from . import instagram, tiktok, youtube
    cfg = ACCOUNTS[series]
    done = dict(done or {})
    desc = ep.get("description", "")
    _run(done, "youtube", lambda: youtube.upload(cfg["youtube"], video, ep["title"], f"{desc}\n\n{cfg['hashtags']}",
                                                 ep.get("tags", []), cfg["made_for_kids"]))
    caption = f"{ep['title']}.\n\n{desc} Comment A or B.\n\n{cfg['ig_hashtags']}"
    _run(done, "instagram", lambda: instagram.upload(cfg["instagram"], video, caption, os.path.basename(video)))
    _run(done, "tiktok", lambda: tiktok.upload(cfg["tiktok"], video, caption))
    return done
