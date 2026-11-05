"""Writing agent (editor) for every new episode. Haseeb, 4 Nov 2026: "the videos have been shit".

The script writer drafts; this separate editor judges the draft the way a demanding YouTube editor would, against
a rubric drawn from what makes the top channels in each format work, and sends it back with concrete rewrite
instructions until it clears the bar (at most MAX_ROUNDS rewrites). Its scores and verdict go in the approval
email, so Haseeb sees why an episode was judged good enough, and an episode that never clears the bar is
flagged as weak instead of presented as ready.
"""
from __future__ import annotations

import json

MAX_ROUNDS = 2
BAR_AVG, BAR_MIN = 8.0, 7

RUBRICS = {
    "imagine_you": {
        "premise": "Is the situation one millions would stop scrolling for (a real, vivid danger with a counter-intuitive rule), not a safe generic tip?",
        "hook": "Does sentence one state a surprising deadly fact or paradox in under 15 words, with no setup?",
        "title": "Does the title open a curiosity gap about a hidden mechanism (like 'Why sailors carried storm oil'), not describe the plot?",
        "specificity": "Real numbers, real mechanisms, an everyday comparison after 'You see,'; nothing vague or padded",
        "escalation": "3 to 5 beats, each clearly worse than the last, with time stamps that make sense",
        "twist": "One twist near the end that recontextualises the story, then a genuinely hard A/B choice",
        "showability": "Every line can be drawn literally with the allowed sets, props and poses; nothing narrated that is not on screen",
        "voice": "Fast, plain, punchy spoken English; no cliches, no filler, no 'imagine' overuse; 160-210 words",
    },
    "every_how": {
        "question": "Is this the big global story people are talking about today, framed as a gripping 'what happens if' a viewer in Lagos or Jakarta would click?",
        "hook": "The cold open lands a real quote or headline and the question within 20 seconds, with a 'wait, really?' fact",
        "story": "Told as an unfolding scenario with rising stakes (place, region, world), not a list of facts",
        "surprise": "At least three facts most viewers will not know, each sourced",
        "clarity": "A 12-year-old could follow every step; the mechanism is explained with simple analogies",
        "money": "The 'Your money' section is concrete and useful worldwide (prices, rates, savings, jobs), calm, no stock tips",
        "visuals": "Dark news scenes (maps, headlines, ladder, price) carry the news; paper scenes carry the explanations; every visual matches its line",
        "accuracy_tone": "Facts and scenario clearly separated, scenario numbers sourced, neutral wording, nothing graphic or sensational",
    },
}

SYSTEM = """You are the head writer and editor of a fast-growing YouTube channel. You are blunt and specific.
Judge the draft episode below against each rubric item from 1 to 10 (10 = as good as the best channels in this
format). Be harsh: 7 is merely acceptable, 9 is excellent. Then give rewrite instructions that would raise every
item below 8: concrete changes (which scene, what to say instead), not general advice.
Return ONLY JSON: {"scores": {"<item>": <int>, ...}, "verdict": "ship" | "rewrite",
"strengths": ["..."], "problems": ["..."], "instructions": "<numbered concrete rewrite instructions>"}"""


def review(series: str, ep: dict, ask) -> dict:
    from .writer import _extract
    rubric = RUBRICS[series]
    user = ("Rubric:\n" + "\n".join(f"- {k}: {v}" for k, v in rubric.items()) +
            f"\n\nDraft episode JSON:\n{json.dumps(ep)[:60000]}")
    try:
        r = _extract(ask(SYSTEM, user))
    except Exception as e:
        return {"error": f"editor reply unreadable: {e}", "ship": False, "scores": {}}
    scores = {k: int(r.get("scores", {}).get(k, 0) or 0) for k in rubric}
    avg = round(sum(scores.values()) / len(scores), 1)
    r["scores"], r["average"] = scores, avg
    r["ship"] = avg >= BAR_AVG and min(scores.values()) >= BAR_MIN
    return r


def improve(series: str, ep: dict, rewrite, ask) -> dict:
    """rewrite(previous_ep, notes) -> new ep. Returns the best draft, with ep['editor'] filled in."""
    best, best_review, rounds = ep, review(series, ep, ask), 0
    while not best_review.get("ship") and rounds < MAX_ROUNDS:
        rounds += 1
        notes = ("The channel's editor rejected this draft. Rewrite it to fix EVERY point, keeping what works.\n"
                 f"Scores: {json.dumps(best_review.get('scores'))}\nProblems: {best_review.get('problems')}\n"
                 f"Instructions:\n{best_review.get('instructions')}")
        try:
            draft = rewrite(best, notes)
        except Exception as e:
            print(f"editor round {rounds}: rewrite failed ({e})", flush=True)
            break
        r = review(series, draft, ask)
        print(f"editor round {rounds}: {r.get('average')} (was {best_review.get('average')})", flush=True)
        if r.get("average", 0) >= best_review.get("average", 0):
            best, best_review = draft, r
    best["editor"] = {k: best_review.get(k) for k in ("scores", "average", "ship", "strengths", "problems")}
    best["editor"]["rounds"] = rounds
    return best


def summary(ep: dict) -> str:
    """Lines for the approval email."""
    e = ep.get("editor") or {}
    if not e or not e.get("scores"):
        return ""
    weak = "" if e.get("ship") else ("WEAK: the editor did not rate this good enough after "
                                     f"{e.get('rounds', 0)} rewrites. Watch it before approving; skip is fine.\n")
    scores = ", ".join(f"{k} {v}" for k, v in e["scores"].items())
    lines = [weak + f"Editor score: {e.get('average')}/10 ({scores})"]
    if e.get("strengths"):
        lines.append("Strong: " + "; ".join(e["strengths"][:3]))
    if e.get("problems"):
        lines.append("Still weak: " + "; ".join(e["problems"][:3]))
    return "\n".join(lines) + "\n\n"
