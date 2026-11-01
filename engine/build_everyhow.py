"""Every How: script JSON -> narrated Paper Cut-Out explainer (16:9) plus a vertical cut for Reels/TikTok/Shorts.

All free and CPU only: Kokoro voice (bm_fable), a gentle numpy music bed, paper "swish" sound on every cut,
and the canvas renderer in engine/everyhow/renderer.html driven frame by frame by headless Chromium.

Usage: python build_everyhow.py episode.json out.mp4 [--short out_short.mp4] [--models DIR] [--fps 30] [--workers N]
Episode JSON (see autopilot/writer.py): {"title", "sections": [{"heading", "scenes": [{"narration", "visual"}]}],
                                         "short": {"scenes": [global scene numbers, 1-based], "outro": "..."}}
"""
import argparse, base64, json, math, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(HERE, "everyhow")
SR = 24000
VOICE, LANG, SPEED = "bm_fable", "en-gb", 1.0
LEAD, GAP, SECTION_GAP, TAIL = 0.5, 0.35, 0.8, 0.6
END_CARD = 4.5


# ------------------------------------------------------------------ voice
def voice_scenes(texts, models):
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(models, "kokoro-v1.0.onnx"), os.path.join(models, "voices-v1.0.bin"))
    out = []
    for t in texts:
        a, sr = k.create(t, voice=VOICE, speed=SPEED, lang=LANG)
        assert sr == SR, sr
        out.append(np.asarray(a, dtype=np.float32))
    return out


def flatten(ep):
    scenes = []
    for si, sec in enumerate(ep["sections"]):
        for sc in sec["scenes"]:
            scenes.append({"narration": sc["narration"].strip(), "visual": sc.get("visual") or {"type": "question", "text": ""},
                           "section": si, "heading": sec.get("heading", "")})
    return scenes


def lay_out(scenes, clips, extra_gap=None):
    """Place clips on a timeline; returns (timeline scenes, voice track)."""
    t, track, tl = LEAD, [np.zeros(int(LEAD * SR), np.float32)], []
    for i, (sc, a) in enumerate(zip(scenes, clips)):
        d = len(a) / SR
        tl.append(dict(sc, start=round(t, 3), end=round(t + d, 3)))
        nxt = scenes[i + 1] if i + 1 < len(scenes) else None
        gap = (extra_gap or GAP) if nxt is None or nxt["section"] == sc["section"] else SECTION_GAP
        track += [a, np.zeros(int(gap * SR), np.float32)]
        t += d + gap
    return tl, np.concatenate(track), t


# ------------------------------------------------------------------ music bed + sound effects
def music_bed(dur, seed=1):
    """Soft pad + pluck arpeggio in a major key, 4 chords x 4 s, quiet. Key varies per episode."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR) + SR
    t = np.arange(n) / SR
    root = 220 * 2 ** (int(rng.integers(0, 7)) / 12)
    prog = [[0, 4, 7], [-3, 0, 4], [-7, -3, 0], [-5, -1, 2]]  # I vi IV V
    pad = np.zeros(n, np.float32)
    pl = np.zeros(n, np.float32)
    bar = 4.0
    for b in range(int(dur / bar) + 2):
        ch = prog[b % 4]
        s0, s1 = int(b * bar * SR), min(n, int((b + 1) * bar * SR + 0.6 * SR))
        if s0 >= n:
            break
        tt = t[s0:s1] - b * bar
        envl = np.minimum(1, tt / 1.2) * np.minimum(1, np.maximum(0, (bar + 0.6 - tt) / 0.8))
        for semi in ch:
            f = root * 2 ** (semi / 12)
            pad[s0:s1] += (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 1.003 * tt) +
                           0.25 * np.sin(2 * np.pi * f * 0.5 * tt)) * envl * 0.05
        for k in range(8):  # gentle arpeggio, eighth notes
            semi = ch[k % 3] + (12 if k >= 4 else 0)
            f = root * 2 * 2 ** (semi / 12)
            a0 = int((b * bar + k * bar / 8) * SR)
            m = min(n - a0, int(1.2 * SR))
            if m <= 0:
                continue
            tk = np.arange(m) / SR
            pl[a0:a0 + m] += np.sin(2 * np.pi * f * tk) * np.exp(-tk * 4) * (0.035 if k % 2 else 0.05)
    mix = pad + pl
    X = np.fft.rfft(mix)  # warm it up: roll off highs
    f = np.fft.rfftfreq(len(mix), 1 / SR)
    X *= 1 / np.sqrt(1 + (f / 1800) ** 2)
    return np.fft.irfft(X, len(mix)).astype(np.float32)[: int(dur * SR)]


def swish(seed):
    rng = np.random.default_rng(seed)
    d = 0.4
    nz = rng.standard_normal(int(d * SR)).astype(np.float32)
    X = np.fft.rfft(nz)
    f = np.fft.rfftfreq(len(nz), 1 / SR)
    X *= np.exp(-((f - 2500) / 1800) ** 2)
    s = np.fft.irfft(X, len(nz)).astype(np.float32)
    tt = np.arange(len(s)) / SR
    return s * np.sin(np.pi * tt / d) ** 2 * 0.5


def mix_audio(voice, dur, cut_times, path, seed):
    n = int(dur * SR)
    v = np.zeros(n, np.float32)
    v[: min(n, len(voice))] = voice[:n]
    m = music_bed(dur, seed)
    m = np.pad(m, (0, max(0, n - len(m))))[:n]
    # duck the music under the voice
    envl = np.convolve(np.abs(v), np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
    duck = 1 - 0.55 * np.clip(envl / (envl.max() * 0.15 + 1e-6), 0, 1)
    out = v + m * duck * 0.9
    for i, ct in enumerate(cut_times):
        s = swish(seed + i)
        a = int(ct * SR)
        if 0 <= a < n:
            out[a:a + len(s)] += s[: n - a] * 0.35
    out /= max(1e-6, np.abs(out).max()) / 0.89
    sf.write(path, out, SR)


# ------------------------------------------------------------------ picture
def render_frames(timeline, wav, out, fps, workers, size):
    from playwright.sync_api import sync_playwright
    total = int(math.ceil(timeline["duration"] * fps))
    workers = max(1, min(workers, total // 300 or 1))
    chunk = math.ceil(total / workers)
    tmp = tempfile.mkdtemp()
    w, h = size

    def part(k):
        a, b = k * chunk, min(total, (k + 1) * chunk)
        seg = os.path.join(tmp, f"part{k}.mp4")
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg",
                               "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                               "-s", f"{w}x{h}", seg], stdin=subprocess.PIPE)
        with sync_playwright() as p:
            br = p.chromium.launch()
            pg = br.new_page(viewport={"width": 1920, "height": 1080})
            pg.on("pageerror", lambda e: print("PAGE ERROR", e, file=sys.stderr))
            pg.goto("file://" + os.path.join(KIT, "renderer.html"))
            pg.evaluate("tl => setup(tl)", timeline)
            for i in range(a, b):
                b64 = pg.evaluate("t => { draw(t); return document.querySelector('canvas').toDataURL('image/jpeg', 0.92).split(',')[1]; }", i / fps)
                ff.stdin.write(base64.b64decode(b64))
                if (i - a) % 900 == 0:
                    print(f"  worker {k}: frame {i - a}/{b - a}", flush=True)
            br.close()
        ff.stdin.close()
        ff.wait()
        return seg

    with ThreadPoolExecutor(workers) as ex:
        segs = list(ex.map(part, range(workers)))
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{s}'\n" for s in segs))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-shortest", "-movflags", "+faststart", out], check=True)


def end_scene(section):
    return {"narration": "", "visual": {"type": "end", "text": "A new question, every day."}, "section": section, "heading": ""}


def build(ep_path, out, short_out=None, models=None, fps=30, workers=2):
    ep = json.load(open(ep_path))
    models = models or os.path.join(HERE, "models")
    scenes = flatten(ep)
    short = ep.get("short") or {}
    short_idx = [i - 1 for i in short.get("scenes", []) if 1 <= i <= len(scenes)]
    outro = short.get("outro", "The full story is on Every How.")
    clips = voice_scenes([s["narration"] for s in scenes] + ([outro] if short_out and short_idx else []), models)
    seed = sum(map(ord, ep["title"]))

    tl, voice, t = lay_out(scenes, clips[: len(scenes)])
    tl.append(dict(end_scene(scenes[-1]["section"] + 1), start=round(t, 3), end=round(t + END_CARD, 3)))
    dur = t + END_CARD
    timeline = {"duration": round(dur, 3), "title": ep["title"], "scenes": tl}
    wav = out.replace(".mp4", ".wav")
    mix_audio(voice, dur, [s["start"] - 0.25 for s in tl[1:]], wav, seed)
    print(f"{ep['title']}: {len(scenes)} scenes, {dur / 60:.1f} min")
    render_frames(timeline, wav, out, fps, workers, (1920, 1080))
    os.remove(wav)
    json.dump(timeline, open(out.replace(".mp4", ".timeline.json"), "w"))

    if short_out and short_idx:
        sub = [dict(scenes[i], section=0) for i in short_idx]
        sub.append({"narration": outro, "visual": {"type": "end", "text": "Full video on YouTube"}, "section": 0, "heading": ""})
        sclips = [clips[i] for i in short_idx] + [clips[-1]]
        stl, svoice, st = lay_out(sub, sclips)
        sdur = st + TAIL
        stimeline = {"duration": round(sdur, 3), "title": ep["title"], "vertical": True, "scenes": stl}
        swav = short_out.replace(".mp4", ".wav")
        mix_audio(svoice, sdur, [s["start"] - 0.25 for s in stl[1:]], swav, seed + 1)
        print(f"short: {len(sub)} scenes, {sdur:.0f} s")
        render_frames(stimeline, swav, short_out, fps, workers, (1080, 1920))
        os.remove(swav)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("out")
    ap.add_argument("--short")
    ap.add_argument("--models")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--workers", type=int, default=max(1, min(4, (os.cpu_count() or 2))))
    a = ap.parse_args()
    build(a.episode, a.out, a.short, a.models, a.fps, a.workers)
