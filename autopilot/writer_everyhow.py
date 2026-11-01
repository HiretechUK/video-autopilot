"""Every How writer: pick today's question from what's trending, research it, write the episode, fact-check it.

Flow (one `make`):
  1. trending(): Google Trends daily RSS (GB + US) and Wikipedia's most-read articles from yesterday. Free.
  2. Claude (with web search) picks a "How does/did/will" question, researches it and writes the episode JSON
     against the series bible and the scene kit in engine/everyhow/.
  3. validate() checks structure and repairs small slips (unknown icon or country names).
  4. A separate Claude call (with web search) fact-checks every claim; problems go back for one rewrite.
Cost: Anthropic API tokens plus web searches ($10 per 1,000), capped at MAX_SEARCHES per call.
"""
from __future__ import annotations

import datetime as dt
import difflib
import json
import os
import re
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "autopilot")
KIT = os.path.join(ROOT, "engine", "everyhow")
MODELS = [os.environ.get("EVERYHOW_MODEL", "claude-sonnet-5-5"), "claude-sonnet-4-5"]
MAX_SEARCHES = int(os.environ.get("EVERYHOW_MAX_SEARCHES", "8"))
TYPES = {"title", "hero", "compare", "list", "flow", "cycle", "timeline", "stat", "bars", "map", "quote", "zoom", "crowd", "question"}
UA = {"User-Agent": "EveryHow/1.0 (https://github.com/HiretechUK/video-autopilot)"}

SCHEMA = """Return ONLY one JSON object, no prose before or after:
{"title": "<YouTube title, max 70 chars, starts with 'How', ends with '?'>",
 "question": "<the full question>",
 "description": "<3-4 sentence YouTube description; first line hooks; ends with the comment question>",
 "tags": ["8-12 search tags"],
 "ad_safety": {"rating": "green" | "yellow", "reason": "<one line>"},
 "sources": [{"title": "...", "url": "https://..."}, ... at least 4],
 "sections": [{"heading": "" for the first, then 2-4 words, "scenes": [{"narration": "...", "visual": {"type": "...", ...}}]}],
 "short": {"scenes": [4-7 scene numbers], "outro": "..."}}"""


# ------------------------------------------------------------------ trending topics (free sources)
def trending(today: dt.date | None = None) -> list[str]:
    import requests
    today = today or dt.date.today()
    out = []
    for geo in ("GB", "US"):
        try:
            r = requests.get(f"https://trends.google.com/trending/rss?geo={geo}", headers=UA, timeout=30)
            root = ET.fromstring(r.content)
            for it in root.iter("item"):
                t = it.findtext("title") or ""
                news = [n.findtext("{https://trends.google.com/trending/rss}news_item_title") or ""
                        for n in it.findall("{https://trends.google.com/trending/rss}news_item")][:1]
                out.append(f"[Google Trends {geo}] {t}" + (f" -- {news[0]}" if news and news[0] else ""))
        except Exception as e:
            print("trends", geo, "failed:", e)
    y = today - dt.timedelta(days=1)
    for url in (f"https://api.wikimedia.org/feed/v1/wikipedia/en/featured/{y:%Y/%m/%d}",
                f"https://en.wikipedia.org/api/rest_v1/feed/featured/{y:%Y/%m/%d}"):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            arts = (r.json().get("mostread") or {}).get("articles", [])[:25]
            out += [f"[Wikipedia most read] {a.get('normalizedtitle', '')}: {(a.get('description') or '')[:90]}" for a in arts]
            if arts:
                break
        except Exception as e:
            print("wikipedia most-read failed:", url, e)
    return out[:70]


# ------------------------------------------------------------------ Claude with web search
def _ask(system: str, user: str, search: bool = True, max_tokens: int = 16000) -> str:
    import anthropic
    c = anthropic.Anthropic()
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": MAX_SEARCHES}] if search else []
    last = None
    for m in MODELS:
        try:
            msgs = [{"role": "user", "content": user}]
            for _ in range(6):  # long searches may pause; send the turn back unchanged to continue
                kw = dict(model=m, max_tokens=max_tokens, system=system, messages=msgs)
                if tools:
                    kw["tools"] = tools
                r = c.messages.create(**kw)
                if r.stop_reason != "pause_turn":
                    break
                msgs = msgs + [{"role": "assistant", "content": r.content}]
            return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        except anthropic.NotFoundError as e:
            last = e
    raise last


def _extract(text: str) -> dict:
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("no JSON object in the reply")
    raw = m.group(0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        fixed = re.sub(r",\s*([}\]])", r"\1", raw)
        return json.loads(fixed)


# ------------------------------------------------------------------ validation + small repairs
_ICONS = _COUNTRIES = None


def _kit_names():
    global _ICONS, _COUNTRIES
    if _ICONS is None:
        _ICONS = open(os.path.join(KIT, "icon_names.txt")).read().split()
        js = open(os.path.join(KIT, "assets.js")).read()
        world = js[js.index("window.WORLD=") + len("window.WORLD="):].rstrip().rstrip(";")
        _COUNTRIES = list(json.loads(world).keys())
    return _ICONS, _COUNTRIES


ALIASES = {"usa": "United States of America", "united states": "United States of America", "us": "United States of America",
           "america": "United States of America", "uk": "United Kingdom", "britain": "United Kingdom",
           "great britain": "United Kingdom", "england": "United Kingdom", "scotland": "United Kingdom",
           "wales": "United Kingdom", "czech republic": "Czechia", "uae": "United Arab Emirates",
           "ivory coast": "Côte d'Ivoire", "drc": "Dem. Rep. Congo", "democratic republic of the congo": "Dem. Rep. Congo",
           "bosnia": "Bosnia and Herz.", "bosnia and herzegovina": "Bosnia and Herz.", "south sudan": "S. Sudan",
           "central african republic": "Central African Rep.", "dominican republic": "Dominican Rep.",
           "north macedonia": "Macedonia", "eswatini": "eSwatini", "burma": "Myanmar", "holland": "Netherlands"}


def _fix_icon(n: str) -> str:
    icons, _ = _kit_names()
    n = str(n or "").lower().strip().replace(" ", "-").replace("_", "-")
    if n in icons:
        return n
    near = difflib.get_close_matches(n, icons, 1, 0.75)
    return near[0] if near else "question"


def _fix_country(n: str) -> str | None:
    _, countries = _kit_names()
    if n in countries:
        return n
    k = str(n).lower().strip()
    if k in ALIASES and ALIASES[k] in countries:
        return ALIASES[k]
    low = {c.lower(): c for c in countries}
    if k in low:
        return low[k]
    near = difflib.get_close_matches(k, list(low), 1, 0.8)
    return low[near[0]] if near else None


def validate(ep: dict) -> list[str]:
    """Return problems the writer must fix. Repairs icon and country names in place."""
    errs = []
    title = ep.get("title", "")
    if not title.lower().startswith("how ") or len(title) > 70:
        errs.append("title must start with 'How' and be at most 70 characters")
    if len(ep.get("sources") or []) < 4 or not all(str(s.get("url", "")).startswith("http") for s in ep.get("sources", [])):
        errs.append("give at least 4 sources, each with a full https URL")
    if (ep.get("ad_safety") or {}).get("rating") not in ("green", "yellow"):
        errs.append("ad_safety.rating must be green or yellow")
    secs = ep.get("sections") or []
    scenes = [s for sec in secs for s in sec.get("scenes", [])]
    if not 5 <= len(secs) <= 10:
        errs.append(f"need 5-9 sections, got {len(secs)}")
    if not 28 <= len(scenes) <= 60:
        errs.append(f"need 30-55 scenes, got {len(scenes)}")
    words = 0
    run, prev = 0, None
    types = set()
    for i, s in enumerate(scenes, 1):
        n = (s.get("narration") or "").strip()
        wc = len(n.split())
        words += wc
        if not 4 <= wc <= 48:
            errs.append(f"scene {i}: narration is {wc} words (8-40)")
        if re.search(r"[\U0001F300-\U0001FAFF#\[\]]", n):
            errs.append(f"scene {i}: no emojis, hashtags or [tags] in narration")
        v = s.get("visual") or {}
        t = v.get("type")
        if t not in TYPES:
            errs.append(f"scene {i}: visual type '{t}' not in the kit")
            continue
        types.add(t)
        run = run + 1 if t == prev else 1
        prev = t
        if run > 2:
            errs.append(f"scene {i}: '{t}' used more than twice in a row")
        for key in ("icon", "inner_icon"):
            if key in v:
                v[key] = _fix_icon(v[key])
        for key in ("items", "steps", "events"):
            for it in v.get(key) or []:
                if isinstance(it, dict) and it.get("icon"):
                    it["icon"] = _fix_icon(it["icon"])
        for side in ("left", "right"):
            if isinstance(v.get(side), dict) and v[side].get("icon"):
                v[side]["icon"] = _fix_icon(v[side]["icon"])
        if t == "map":
            fixed = [c for c in (_fix_country(c) for c in v.get("countries") or []) if c]
            if not fixed:
                errs.append(f"scene {i}: map has no recognisable country names")
            v["countries"] = fixed
        if t == "bars" and any(not re.search(r"\d", str(b.get("value", ""))) for b in v.get("items", [])):
            errs.append(f"scene {i}: bars values must be numbers")
        if t == "quote" and not v.get("who"):
            errs.append(f"scene {i}: quotes need 'who' (and must be exact, sourced words)")
    if not 750 <= words <= 1250:
        errs.append(f"narration is {words} words; target 800-1150 (5-7 minutes)")
    if len(types) < 7:
        errs.append(f"only {len(types)} visual types used; use at least 7")
    sh = (ep.get("short") or {}).get("scenes") or []
    if not 3 <= len(sh) <= 8 or not all(isinstance(x, int) and 1 <= x <= len(scenes) for x in sh):
        errs.append("short.scenes must be 4-7 valid scene numbers")
    elif sum(len(scenes[x - 1]["narration"].split()) for x in sh) > 190:
        errs.append("the vertical cut is too long; keep its scenes under about 170 words")
    return errs


# ------------------------------------------------------------------ fact-check
FACTCHECK = """You are a strict fact-checker for an educational YouTube channel. Today is {today}.
Check EVERY factual claim (numbers, dates, names, causes, quotes, 'this week' style timing) in the
narration below against reliable sources, using web search. Also flag myths, overstatements, claims a
source does not support, and anything that breaks the advertiser-friendly rules (graphic violence,
glorifying violence, one-sided politics, medical advice).
Return ONLY JSON: {{"ok": true|false, "issues": [{{"scene": <number>, "claim": "...", "problem": "...",
"fix": "<corrected wording or 'remove'>", "source": "<url>"}}], "summary": "<one line>"}}.
Minor style points are not issues."""


def factcheck(ep: dict, today: dt.date) -> dict:
    scenes = [s for sec in ep["sections"] for s in sec["scenes"]]
    text = "\n".join(f"{i}. {s['narration']}" for i, s in enumerate(scenes, 1))
    srcs = "\n".join(f"- {s.get('title')}: {s.get('url')}" for s in ep.get("sources", []))
    reply = _ask(FACTCHECK.format(today=today.isoformat()), f"Title: {ep['title']}\n\nNarration:\n{text}\n\nWriter's sources:\n{srcs}")
    try:
        return _extract(reply)
    except Exception:
        return {"ok": False, "issues": [], "summary": "fact-check reply could not be read; review manually"}


# ------------------------------------------------------------------ main entry
def write(number: int, recent: list[str], lessons: str = "", notes: str = "", previous: dict | None = None) -> dict:
    today = dt.date.today()
    bible = open(os.path.join(HERE, "bible_every_how.md")).read()
    icons, _ = _kit_names()
    system = (bible + "\n\n## Icon names you may use\n" + " ".join(icons) + "\n\n" + SCHEMA +
              f"\n\nToday is {today:%A %d %B %Y}.")
    if previous is None:
        trend = trending(today)
        user = (f"Make Every How episode {number}.\n\nWhat people are searching for today:\n" +
                "\n".join(trend or ["(trend feeds unavailable: pick a strong evergreen question tied to this week)"]) +
                f"\n\nRecent episodes (do not repeat these questions or angles): {'; '.join(recent) or 'none'}.\n"
                "Pick today's question, research it with web search, then write the episode.\n")
    else:
        user = ("Revise this episode according to Haseeb's notes. Keep everything he did not ask to change, re-check any "
                f"facts you change with web search.\nNotes: {notes}\nCurrent episode JSON:\n{json.dumps(previous)}\n")
    if lessons:
        user += f"\nWhat has performed well or badly so far (apply it):\n{lessons}\n"

    errs, ep = [], None
    for attempt in range(4):
        try:
            ep = _extract(_ask(system, user))
        except (ValueError, json.JSONDecodeError) as e:
            user += f"\nYour last reply could not be parsed ({e}). Return ONLY one valid JSON object.\n"
            continue
        errs = validate(ep)
        if errs:
            user += f"\nYour last attempt had problems, fix ALL of them and return the full JSON again: {'; '.join(errs)}\nYour last attempt:\n{json.dumps(ep)}\n"
            continue
        fc = factcheck(ep, today)
        issues = fc.get("issues") or []
        if issues and attempt < 3:
            user += ("\nAn independent fact-check found these problems. Fix every one (use its fix or remove the claim), "
                     f"keep everything else, and return the full JSON again:\n{json.dumps(issues)}\nYour last attempt:\n{json.dumps(ep)}\n")
            ep["_factcheck_pending"] = True
            continue
        ep.pop("_factcheck_pending", None)
        ep["factcheck"] = {"ok": not issues, "summary": fc.get("summary", ""), "open_issues": issues}
        ep["series"] = f"EVERY HOW #{number:02d}"
        return ep
    raise RuntimeError(f"Every How episode failed validation: {errs}")
