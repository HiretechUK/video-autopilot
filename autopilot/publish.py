"""Post an approved episode to every connected platform. A platform that is not connected yet, or fails,
is reported and retried on the next run; the others still post."""
from __future__ import annotations

import traceback

ACCOUNTS = {  # series -> account key per platform
    "imagine_you": {"youtube": "imagine_you", "made_for_kids": False,
                    "hashtags": "#Shorts #survival #whatwouldyoudo #imagineyou"},
}


def publish(series: str, ep: dict, video: str, done: dict | None = None) -> dict:
    from . import youtube
    cfg = ACCOUNTS[series]
    done = dict(done or {})
    if not str(done.get("youtube", "")).startswith("http"):
        desc = f"{ep.get('description', '')}\n\n{cfg['hashtags']}"
        try:
            done["youtube"] = youtube.upload(cfg["youtube"], video, ep["title"], desc, ep.get("tags", []), cfg["made_for_kids"])
        except LookupError:
            done["youtube"] = "not connected yet"
        except Exception as e:  # keep going; retried next run
            traceback.print_exc()
            done["youtube"] = f"failed: {e}"[:300]
    return done
