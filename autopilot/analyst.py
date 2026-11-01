"""Channel analyst (Haseeb, 1 Nov 2026): reads each YouTube channel's numbers, works out what is and isn't working,
tells the CEO agent, and feeds the lessons straight into that series' script writer.

Runs daily from .github/workflows/analyst.yml:
  1. Snapshot: channel subscribers/views and every posted episode's views, likes and comments (YouTube Data API)
     -> autopilot/analytics.json (history, so growth over time is visible).
  2. Report: autopilot/analyst_report.md, a short plain-English brief per channel that the CEO agent reads nightly.
  3. Lessons (Mondays, or when a channel has 3+ new episodes since its last lessons): Claude compares the best and
     worst episodes and rewrites autopilot/lessons_<series>.md, which the writers read before every new episode.
Read-only on YouTube: it never changes a video.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

import requests

from . import youtube

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "autopilot", "state.json")
HIST = os.path.join(ROOT, "autopilot", "analytics.json")
REPORT = os.path.join(ROOT, "autopilot", "analyst_report.md")
API = "https://www.googleapis.com/youtube/v3"
YTA = "https://youtubeanalytics.googleapis.com/v2/reports"
SERIES = {"imagine_you": "Imagine You", "every_how": "Every How", "paws_claws": "Paws & Claws Club"}
NOW = datetime.now(timezone.utc)


def vid(url: str) -> str | None:
    m = re.search(r"(?:v=|shorts/|youtu\.be/)([\w-]{11})", str(url))
    return m.group(1) if m else None


def hours_since(iso: str) -> float:
    return (NOW - datetime.fromisoformat(iso)).total_seconds() / 3600


def fetch(series: str, eps: dict) -> dict:
    at, _ = youtube._access(series)
    h = {"Authorization": f"Bearer {at}"}
    ch = requests.get(f"{API}/channels", params={"part": "statistics,snippet", "mine": "true"}, headers=h, timeout=30).json()
    item = (ch.get("items") or [{}])[0]
    st = item.get("statistics", {})
    out = {"channel": item.get("snippet", {}).get("title", "?"), "subscribers": int(st.get("subscriberCount", 0) or 0),
           "channel_views": int(st.get("viewCount", 0) or 0), "videos": {}}
    ids = {}
    for ref, e in eps.items():
        for plat in ("youtube", "youtube_short"):
            v = vid(e.get("links", {}).get(plat, ""))
            if v:
                ids[v] = (ref, plat)
    keys = list(ids)
    for i in range(0, len(keys), 50):
        r = requests.get(f"{API}/videos", params={"part": "statistics,contentDetails", "id": ",".join(keys[i:i + 50])},
                         headers=h, timeout=30).json()
        for it in r.get("items", []):
            ref, plat = ids[it["id"]]
            s = it.get("statistics", {})
            out["videos"][f"{ref}:{plat}"] = {"id": it["id"], "views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                                             "comments": int(s.get("commentCount", 0)), "duration": it["contentDetails"].get("duration")}
    out["deep"] = deep(h, [v for v, (r, p) in ids.items()])
    return out


def deep(h: dict, video_ids: list[str]) -> dict:
    """YouTube Analytics (watch time, % watched, retention). Returns {} plus an "error" note if not available."""
    if not video_ids:
        return {}
    res = {}
    try:
        q = {"ids": "channel==MINE", "startDate": "2026-01-01", "endDate": NOW.strftime("%Y-%m-%d"),
             "metrics": "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,shares",
             "dimensions": "video", "filters": "video==" + ",".join(video_ids[:200])}
        r = requests.get(YTA, params=q, headers=h, timeout=30)
        if r.status_code != 200:
            return {"error": f"{r.status_code} {r.text[:200]}"}
        print("analytics:", r.status_code, json.dumps(r.json())[:600], flush=True)
        cols = [c["name"] for c in r.json().get("columnHeaders", [])]
        for row in r.json().get("rows", []):
            d = dict(zip(cols, row))
            res[d["video"]] = {k: d[k] for k in cols if k != "video"}
        for v in list(res)[:20]:  # retention curve: share of viewers still watching at 10%, 50%, 90% of the video
            q = {"ids": "channel==MINE", "startDate": "2026-01-01", "endDate": NOW.strftime("%Y-%m-%d"),
                 "metrics": "audienceWatchRatio", "dimensions": "elapsedVideoTimeRatio", "filters": f"video=={v}"}
            r = requests.get(YTA, params=q, headers=h, timeout=30)
            rows = r.json().get("rows", []) if r.status_code == 200 else []
            if rows:
                pick = lambda x: min(rows, key=lambda rw: abs(rw[0] - x))[1]
                res[v]["kept_10"], res[v]["kept_50"], res[v]["kept_90"] = (round(pick(x), 2) for x in (.1, .5, .9))
    except Exception as e:
        return {"error": str(e)[:200]}
    return res


def lessons_due(series: str, hist: dict, eps: dict) -> bool:
    last = hist.get("lessons", {}).get(series)
    if not last:
        return len(eps) >= 2
    new = [r for r, e in eps.items() if e.get("approved", "") > last]
    return NOW.weekday() == 0 or len(new) >= 3


def write_lessons(series: str, rows: list[dict]) -> str:
    from .writer import _ask
    table = "\n".join(f"- {r['ref']} \"{r['title']}\" | {r['age_h']:.0f} h live | views {r['views']} | likes {r['likes']} | "
                      f"comments {r['comments']}" + (f" | Short views {r['short_views']}" if r.get('short_views') is not None else "")
                      + (f" | avg % watched {r['deep'].get('averageViewPercentage')} | avg seconds {r['deep'].get('averageViewDuration')} | "
                         f"still watching at 10/50/90% of video {r['deep'].get('kept_10')}/{r['deep'].get('kept_50')}/{r['deep'].get('kept_90')} | "
                         f"subs gained {r['deep'].get('subscribersGained')} | shares {r['deep'].get('shares')}" if r.get('deep') and 'views' in r['deep'] else "")
                      for r in rows)
    system = ("You are a YouTube growth analyst for a small automated channel. Be concrete and honest. Small numbers are "
              "normal for a new channel: compare episodes with each other, normalise for hours live, and say when the data is "
              "too thin to conclude anything. Never suggest anything that breaks the channel's fixed rules below; work within them.")
    rb = os.path.join(ROOT, "autopilot", f"RULEBOOK_{series}.md")
    if os.path.exists(rb):
        system += "\n\nFIXED RULES:\n" + open(rb).read()
    user = (f"Channel: {SERIES[series]}. Episodes (oldest first):\n{table}\n\n"
            "Watch-time numbers (% watched, viewers still watching at 10/50/90%) matter most for Shorts: a big drop by 10% means the "
            "hook failed; a drop in the middle means the story sagged there. "
            "Write the lessons file the script writer will read before every new episode. Markdown, max 12 bullets, in three "
            "sections: '## Keep doing' (what the better performers share: topic, hook, title wording, length), '## Stop or change' "
            "and '## Try next' (2-3 specific experiments, e.g. a title style or topic family to test). Each bullet names the "
            "episodes it is based on. If there are fewer than 4 episodes or under ~200 views total, say the data is early and keep "
            "it to 3-5 cautious bullets. No preamble.")
    return _ask(system, user).strip()


def main():
    st = json.load(open(STATE))
    hist = json.load(open(HIST)) if os.path.exists(HIST) else {"snapshots": [], "lessons": {}}
    snap = {"at": NOW.isoformat(), "series": {}}
    report = [f"# Channel analyst report, {NOW:%Y-%m-%d %H:%M} UTC", ""]
    for series, name in SERIES.items():
        eps = {r: e for r, e in st["episodes"].items() if e["series"] == series and any(
            str(e.get("links", {}).get(p, "")).startswith("http") for p in ("youtube", "youtube_short"))}
        try:
            data = fetch(series, eps)
        except LookupError:
            report += [f"## {name}", "YouTube not connected yet.", ""]
            continue
        except Exception as e:
            report += [f"## {name}", f"Could not read YouTube: {e}", ""]
            continue
        snap["series"][series] = data
        prev = next((s["series"].get(series) for s in reversed(hist["snapshots"]) if
                     series in s["series"] and hours_since(s["at"]) >= 20), None)
        rows = []
        for ref, e in sorted(eps.items(), key=lambda kv: kv[1].get("approved", "")):
            full = data["videos"].get(f"{ref}:youtube", {})
            short = data["videos"].get(f"{ref}:youtube_short")
            rows.append({"ref": ref, "title": e.get("title", ""), "age_h": hours_since(e.get("approved") or e["created"]),
                         "views": full.get("views", 0), "likes": full.get("likes", 0), "comments": full.get("comments", 0),
                         "short_views": short.get("views") if short else None,
                         "deep": data.get("deep", {}).get(full.get("id"), {})})
        d_subs = data["subscribers"] - prev["subscribers"] if prev else None
        d_views = data["channel_views"] - prev["channel_views"] if prev else None
        report += [f"## {name} ({data['channel']})",
                   f"- Subscribers: {data['subscribers']}" + (f" ({d_subs:+d} in the last day)" if d_subs is not None else ""),
                   f"- Channel views: {data['channel_views']}" + (f" ({d_views:+d} in the last day)" if d_views is not None else "")]
        if rows:
            best = max(rows, key=lambda r: r["views"] / max(r["age_h"], 6))
            worst = min(rows, key=lambda r: r["views"] / max(r["age_h"], 6))
            report.append(f"- Episodes live: {len(rows)}; strongest: {best['ref']} "
                          f"({best['views'] / max(best['age_h'], 6):.0f} views/hour live); weakest: {worst['ref']} "
                          f"({worst['views'] / max(worst['age_h'], 6):.0f} views/hour live)")
            for r in rows[-5:]:
                dp = r["deep"]
                report.append(f"  - {r['ref']} {r['title'][:60]}: {r['views']} views, {r['likes']} likes, {r['comments']} comments"
                              + (f", Short {r['short_views']} views" if r["short_views"] is not None else "")
                              + (f", watched {dp['averageViewPercentage']:.0f}% on average ({dp['averageViewDuration']} s)"
                                 if "averageViewPercentage" in dp else "")
                              + (f", still watching at 10/50/90%: {dp['kept_10']}/{dp['kept_50']}/{dp['kept_90']}" if "kept_10" in dp else "")
                              + (f", +{dp['subscribersGained']} subs" if dp.get("subscribersGained") else ""))
        if not data.get("deep"):
            report.append("- Watch-time data: none yet (YouTube publishes it 1-2 days after a video goes live)")
        if data.get("deep", {}).get("error"):
            report.append(f"- Watch-time data not available: {data['deep']['error'][:160]}")
        if rows and lessons_due(series, hist, eps):
            try:
                text = write_lessons(series, rows)
                open(os.path.join(ROOT, "autopilot", f"lessons_{series}.md"), "w").write(
                    f"<!-- written by the channel analyst {NOW:%Y-%m-%d} -->\n{text}\n")
                hist.setdefault("lessons", {})[series] = NOW.isoformat()
                report += ["- New lessons for the script writer:", *["  " + ln for ln in text.splitlines() if ln.strip()]]
            except Exception as e:
                report.append(f"- Lessons not updated: {e}")
        else:
            lp = os.path.join(ROOT, "autopilot", f"lessons_{series}.md")
            report.append("- Current lessons in use: " + ("yes (see lessons file)" if os.path.exists(lp) else "none yet"))
        report.append("")
    hist["snapshots"] = (hist["snapshots"] + [snap])[-120:]
    json.dump(hist, open(HIST, "w"), indent=1)
    open(REPORT, "w").write("\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()
