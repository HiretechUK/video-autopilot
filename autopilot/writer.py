"""Claude writes an episode script (JSON) for a series, following its bible and recent lessons."""
from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = [os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5"), "claude-sonnet-4-5"]

VOCAB = {
    "bg": {"city_night", "island", "island_night", "bunker", "forest_night", "desert", "snow", "supermarket", "amsterdam_1637"},
    "pose": {"stand", "walk", "phone", "point", "shock", "think", "sit", "crouch", "wave", "run", "drink", "lookout",
             "kneel", "reach", "carry", "signal", "build", "shiver", "cower"},
    "props": {"car", "crate", "radio", "fire", "fire_triangle", "ship", "leaf_water", "tulip_stall"},
    "fx": {"shake", "flash", "rain", "red", "dark", "window"},
    "mood": {"calm", "tense", "whisper", "urgent", "reveal", "warm"},
}

SCHEMA = """Return ONLY a JSON object:
{"id": "<slug>", "title": "<YouTube title, max 70 chars: a curiosity gap about a hidden survival rule or mechanism>",
 "description": "<2-3 sentence YouTube description ending with a question>",
 "tags": ["5-10 short tags"], "series": "SURVIVE #<n>", "voice": "am_michael", "speed": 1.15,
 "costume": "cap", "hud": ["...", "● ...", "..."],
 "scenes": [{"bg": "...", "pose": "...", "poses": ["action1", "action2"], "x": 0.5, "move_to": 0.4 (optional), "props": [], "fx": "",
   "cam": {"z0": 1.0, "z1": 1.1}, "hud": [...] (optional), "rule": {...} (optional), "mood": "...",
   "narration": "...", "highlight": ["word"]},
   ... last scene adds "choice": {"q": "WHAT DO YOU DO?", "options": ["A · ...", "B · ..."]}, "hold_after": 2.0]}"""


def _client():
    import anthropic
    return anthropic.Anthropic()


def _ask(system: str, user: str) -> str:
    import anthropic
    c = _client()
    last = None
    for m in MODELS:
        try:
            r = c.messages.create(model=m, max_tokens=4000, system=system, messages=[{"role": "user", "content": user}])
            return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        except anthropic.NotFoundError as e:
            last = e
    raise last


def validate(ep: dict) -> list[str]:
    errs = []
    sc = ep.get("scenes") or []
    if not 7 <= len(sc) <= 12:
        errs.append(f"need 8-12 scenes, got {len(sc)}")
    words = 0
    for i, s in enumerate(sc, 1):
        for ps in s.get("poses", []) or []:
            if ps not in VOCAB["pose"]:
                errs.append(f"scene {i}: pose '{ps}' not allowed")
        for key in ("bg", "pose", "mood"):
            if s.get(key) not in VOCAB[key]:
                errs.append(f"scene {i}: {key} '{s.get(key)}' not allowed")
        for p in s.get("props", []) or []:
            if p not in VOCAB["props"]:
                errs.append(f"scene {i}: prop '{p}' not allowed")
        if s.get("fx") and s["fx"] not in VOCAB["fx"]:
            errs.append(f"scene {i}: fx '{s['fx']}' not allowed")
        n = s.get("narration", "")
        if not n.strip():
            errs.append(f"scene {i}: empty narration")
        if n.strip().startswith("[pause]") or n.strip().endswith("[pause]"):
            errs.append(f"scene {i}: [pause] at start/end")
        if re.search(r"[\U0001F300-\U0001FAFF#]", n):
            errs.append(f"scene {i}: emoji/hashtag in narration")
        words += len(re.sub(r"\[pause\]", "", n).split())
        r = s.get("rule")
        if r and (len(r.get("text", "")) > 16 or len(r.get("sub", "")) > 20):
            errs.append(f"scene {i}: rule text too long")
    if sum(1 for s in sc if len(s.get("poses") or []) >= 2 or s.get("move_to") is not None) < len(sc) * 0.6:
        errs.append("the character is too static: give most scenes 2-3 'poses' actions or a move_to")
    if sc and not sc[-1].get("choice"):
        errs.append("last scene needs a choice")
    if not 150 <= words <= 220:
        errs.append(f"narration is {words} words; target 160-210 (50-60 seconds at ~3.7 words a second)")
    if sum(s.get("narration", "").count("[pause]") for s in sc) > 1:
        errs.append("more than 1 [pause] tag")
    if sc and re.search(r"\bfollow\b", sc[-1].get("narration", ""), re.I):
        errs.append("last scene: end on 'Comment A or B.' with no 'follow' call")
    return errs


def _extract(text: str) -> dict:
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("no JSON object in your reply")
    raw = m.group(0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # common slips: trailing commas, missing comma between "}" / "]" / '"' and the next item
        fixed = re.sub(r",\s*([}\]])", r"\1", raw)
        fixed = re.sub(r'([}\]"0-9e])\s*\n(\s*["{\[])', r"\1,\n\2", fixed)
        return json.loads(fixed)


def write_episode(series: str, number: int, recent: list[str], lessons: str = "", notes: str = "",
                  previous: dict | None = None) -> dict:
    if series == "every_how":  # long-form explainers: own writer with trend picking, research and fact-check
        from . import writer_everyhow
        return writer_everyhow.write(number, recent, lessons, notes, previous)
    bible = open(os.path.join(HERE, f"bible_{series}.md")).read()
    system = bible + "\n\n" + SCHEMA
    user = f"Write episode number {number}.\nRecent episodes (do not repeat these scenarios): {', '.join(recent) or 'none'}.\n"
    if lessons:
        user += f"\nWhat has performed well or badly so far (apply it):\n{lessons}\n"
    if previous is not None:
        user += ("\nRevise this episode according to Haseeb's notes. Keep everything he did not ask to change.\n"
                 f"Notes: {notes}\nCurrent episode JSON:\n{json.dumps(previous)}\n")
    errs = []
    for attempt in range(4):
        try:
            ep = _extract(_ask(system, user))
        except (ValueError, json.JSONDecodeError) as e:
            errs = [f"reply was not valid JSON ({e}); return ONLY one valid JSON object, no comments"]
            user += f"\nYour last reply could not be parsed: {errs[0]}\n"
            continue
        errs = validate(ep)
        if not errs:
            ep["series"] = f"SURVIVE #{number:02d}" if series == "imagine_you" else ep.get("series", "")
            return ep
        user += f"\nYour last attempt had problems, fix all of them: {'; '.join(errs)}\n"
    raise RuntimeError(f"episode failed validation: {errs}")
