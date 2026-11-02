"""One test per bug that reached Haseeb (2 Nov 2026 onwards). Runs on every push (.github/workflows/tests.yml).
Offline: no API keys, no network, no posting."""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from autopilot import mailer, pipeline, watchdog, writer  # noqa: E402


def test_imagine_you_writer_allows_long_replies():
    # IY-03 was cut off at 4000 tokens: "no JSON object" on all 4 tries
    src = open("autopilot/writer.py").read()
    assert "max_tokens=4000" not in src and "max_tokens=16000" in src


def test_extract_handles_text_around_json():
    assert writer._extract('Here it is:\n{"a": 1,}\nThanks') == {"a": 1}
    with pytest.raises(ValueError):
        writer._extract('{"a": 1, "scenes": [')  # truncated reply must fail loudly, not silently


def test_watchdog_full_run_sends_auto_not_empty():
    # an empty cmd became the workflow default "make" (Imagine You only), so Every How was skipped
    src = open("autopilot/watchdog.py").read()
    assert '"cmd=auto"' in src and '"cmd="' not in src
    wf = open(".github/workflows/video.yml").read()
    assert '[ "$CMD" = "auto" ]' in wf


def test_watchdog_dispatch_always_calls_github(monkeypatch):
    calls = []
    monkeypatch.setattr(watchdog, "gh", lambda *a: calls.append(a) or "")
    watchdog.dispatch("run")
    watchdog.dispatch("check")
    assert len(calls) == 2 and any("cmd=check" in c for c in calls[1])


def test_render_cache_changes_when_scenes_change(tmp_path):
    # IY-03 v2: same title, new scenes -> the old render was reused and Haseeb got the same video back
    ep = {"title": "T", "scenes": [{"bg": "snow", "narration": "a"}]}
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(ep))
    ep["scenes"][0]["bg"] = "forest_night"
    b.write_text(json.dumps(ep))
    assert pipeline._script_hash(str(a)) != pipeline._script_hash(str(b))


def test_auto_approve_is_off_by_default(monkeypatch):
    monkeypatch.delenv("AUTO_APPROVE", raising=False)
    assert pipeline.auto_ok({"series": "imagine_you"}, {}) is False


def test_revised_episode_never_auto_posts(monkeypatch):
    monkeypatch.setenv("AUTO_APPROVE", "on")
    assert pipeline.auto_ok({"series": "imagine_you"}, {}) is True
    assert pipeline.auto_ok({"series": "imagine_you", "version": 2}, {}) is False
    green = {"ad_safety": {"rating": "green"}, "factcheck": {"ok": True}}
    assert pipeline.auto_ok({"series": "every_how"}, green) is True
    assert pipeline.auto_ok({"series": "every_how", "version": 2}, green) is False


def test_reply_parsing():
    assert mailer.parse("Approved")[0] == "approve"
    assert mailer.parse("approved!")[0] == "approve"
    assert mailer.parse("skip")[0] == "skip"
    act, notes = mailer.parse("Notes. The scenes don't match the script. You need to redo this")
    assert act == "change" and "scenes" in notes


def test_big_video_is_shrunk_not_dropped(tmp_path):
    # a 25 MB render was silently dropped: "The video is attached" with no video
    v = str(tmp_path / "IY-99-x.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30",
                    "-t", "70", "-c:v", "libx264", "-preset", "ultrafast", "-b:v", "3M", v], check=True)
    assert os.path.getsize(v) > 22 * 1024 * 1024
    p = mailer._preview(v)
    assert p and os.path.getsize(p) <= 22 * 1024 * 1024


def test_redo_request_applied_once(monkeypatch, tmp_path):
    # a queued "revise" run was cancelled by GitHub; redo requests now live in state and any run applies them once
    st = {"episodes": {"IY-77": {"status": "pending", "series": "imagine_you", "number": 77,
                                 "file": "episodes/IY-77.json"}}, "seen": []}
    ep_file = os.path.join(ROOT, "episodes", "IY-77.json")
    notes_file = os.path.join(ROOT, "episodes", "IY-77.notes.txt")
    open(ep_file, "w").write(json.dumps({"title": "x", "scenes": []}))
    open(notes_file, "w").write("redo it")
    try:
        sent = []
        monkeypatch.setattr(pipeline.writer, "write_episode", lambda *a, **k: {"title": "y", "scenes": []})
        monkeypatch.setattr(pipeline, "render", lambda s, p: "v.mp4")
        monkeypatch.setattr(pipeline, "email_for_approval", lambda *a: sent.append(a[0]))
        monkeypatch.setattr(pipeline, "save", lambda s: None)
        assert pipeline.revise_from_file(st, "IY-77") is True
        assert pipeline.revise_from_file(st, "IY-77") is False
        assert sent == ["IY-77"] and st["episodes"]["IY-77"]["version"] == 2
    finally:
        os.remove(ep_file)
        os.remove(notes_file)


def test_every_how_writer_streams_with_room():
    src = open("autopilot/writer_everyhow.py").read()
    assert "messages.stream(" in src and "max_tokens: int = 32000" in src


def test_all_modules_import():
    import importlib
    for m in ("analyst", "publish", "instagram", "facebook", "youtube", "thumbs", "writer_everyhow"):
        importlib.import_module(f"autopilot.{m}")


def test_video_workflow_installs_every_library_the_code_imports():
    # IY-03 thumbnail failed: "No module named 'PIL'" (thumbs.py needs Pillow, the workflow did not install it)
    import re
    wf = open(".github/workflows/video.yml").read()
    installed = set(re.search(r"pip install -q ([^\n&]+)", wf).group(1).split())
    needs = {"PIL": "pillow", "anthropic": "anthropic", "requests": "requests", "cryptography": "cryptography",
             "playwright": "playwright", "soundfile": "soundfile", "kokoro_onnx": "kokoro-onnx"}
    used = set()
    for f in os.listdir("autopilot"):
        if f.endswith(".py"):
            src = open(os.path.join("autopilot", f)).read()
            used |= {mod for mod in needs if re.search(rf"^\s*(from|import) {mod}\b", src, re.M)}
    missing = {needs[m] for m in used} - installed
    assert not missing, f"video.yml does not install: {missing}"


def test_every_how_review_copies_watchable_by_link():
    # Haseeb could not open private review copies on his phone (signed in to his own account)
    src = open("autopilot/publish.py").read()
    assert 'privacy="private"' not in src and src.count('privacy="unlisted"') >= 2


def test_thumbnail_backfill_finds_hashed_video_name():
    # IY-03 thumbnail retry looked for media/IY-03.mp4, but it was posted as media/IY-03-5e6ada78.mp4
    assert pipeline.hosted_name("IY-03").startswith("IY-03-") or not os.path.exists("media")
    assert pipeline.hosted_name("IY-01") == "IY-01.mp4"
