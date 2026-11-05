"""Every How hybrid format (5 Nov 2026): the validator accepts a good big-news episode and rejects the slips that
matter most: wrong title shape, no money disclaimer, no subscribe ask, photos of people, too few news scenes."""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from autopilot import writer_everyhow as w  # noqa: E402

SAMPLE = json.load(open(os.path.join(ROOT, "tests", "fixtures", "eh_hybrid_sample.json")))


def scenes(ep):
    return [s for sec in ep["sections"] for s in sec["scenes"]]


def test_sample_passes():
    assert w.validate(copy.deepcopy(SAMPLE)) == []


def test_title_shapes():
    for good in ("What Happens If the Strait of Hormuz Reopens?", "How Would a Chip Ban Hit Your Phone?", "How Does Rain Form?"):
        ep = copy.deepcopy(SAMPLE); ep["title"] = good
        assert not [e for e in w.validate(ep) if e.startswith("title")]
    for bad in ("Strait of Hormuz explained", "What Happens If the Strait Reopens", "x" * 80 + "?"):
        ep = copy.deepcopy(SAMPLE); ep["title"] = bad
        assert any(e.startswith("title") for e in w.validate(ep))


def test_money_disclaimer_required():
    ep = copy.deepcopy(SAMPLE)
    for s in scenes(ep):
        s["narration"] = s["narration"].replace("none of it is financial advice", "it is just a view")
    assert any("financial advice" in e for e in w.validate(ep))


def test_subscribe_ask_required():
    ep = copy.deepcopy(SAMPLE)
    for s in scenes(ep):
        s["narration"] = s["narration"].replace("subscribe", "stay")
    assert any("subscribe" in e for e in w.validate(ep))


def test_no_photos_of_people():
    ep = copy.deepcopy(SAMPLE)
    next(s for s in scenes(ep) if s["visual"]["type"] == "photo")["visual"]["query"] = "president speech"
    assert any("never people" in e for e in w.validate(ep))


def test_needs_dark_news_scenes():
    ep = copy.deepcopy(SAMPLE)
    for s in scenes(ep):
        if s["visual"]["type"] in w.DARK:
            s["visual"] = {"type": "question", "text": "?"}
    assert any("dark news scenes" in e for e in w.validate(ep))


def test_country_names_repaired_for_news_maps():
    ep = copy.deepcopy(SAMPLE)
    m = next(s for s in scenes(ep) if s["visual"]["type"] == "newsmap")["visual"]
    m["focus"] = ["usa", "UAE"]
    w.validate(ep)
    assert m["focus"] == ["United States of America", "United Arab Emirates"]
