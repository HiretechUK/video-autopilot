"""Render an Imagine You episode script (JSON) into a 1080x1920 MP4.

Usage: python build_short.py episode.json out.mp4 [--models DIR] [--fps 30]
Free stack: Kokoro (voice, CPU) + Playwright/Chromium (frames) + ffmpeg (encode/mix).
"""
import argparse, json, os, re, subprocess, sys, tempfile, time
import numpy as np, soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 24000
GAP = 0.28  # silence between scenes (s)


MOODS = {  # gentle whole-scene nudges: (speed multiplier, volume)
    "calm": (1.0, 1.0), "tense": (0.96, 0.97), "whisper": (0.95, 0.8),
    "urgent": (1.06, 1.03), "reveal": (0.95, 1.0), "warm": (0.98, 1.0),
}


def split_sentences(text):
    parts = re.findall(r"[^.!?…]+(?:\.\.\.|[.!?…]+)?", text)
    return [p.strip() for p in parts if p.strip()]


def spoken(text):
    """Text sent to the voice engine (captions keep the original). Fixes known mispronunciations."""
    t = text.replace("...", ",").replace("…", ",")
    # a capital letter used as an option/label ("A or B", "option A", "Comment A") must be read as the letter
    t = re.sub(r"\b([A-D])\b(?=\s+(?:or|and)\b)", r"\1,", t)
    t = re.sub(r"\b((?:option|comment|answer|choose|pick)\s+)([A-D])\b(?![,.?!])", r"\1\2,", t, flags=re.I)
    return re.sub(r",\s*,", ",", t)


PAUSE_Q = 0.42   # beat after a mid-line question ("Your phone? ... No signal.")
PAUSE_TAG = 0.5  # explicit [pause] in a script


def chunks(text):
    """Split a narration only where a deliberate beat belongs: explicit [pause] tags, or a question
    followed by more words. Returns [(chunk_text, pause_after_seconds)]."""
    out = []
    for part, tag in re.findall(r"(.*?)(\[pause\]|$)", text, flags=re.S):
        part = part.strip()
        if not part:
            if tag and out: out[-1] = (out[-1][0], out[-1][1] + PAUSE_TAG)
            continue
        qs = re.split(r"(?<=\?)\s+(?=\S)", part)
        for i, q in enumerate(qs):
            out.append((q, PAUSE_Q if i < len(qs) - 1 else 0.0))
        if tag: out[-1] = (out[-1][0], out[-1][1] + PAUSE_TAG)
    return out


def tts_scenes(ep, models):
    """Each chunk is voiced in one natural pass; beats are inserted only between chunks.
    Mood gently nudges pace/volume of the whole scene."""
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(models, "kokoro-v1.0.onnx"), os.path.join(models, "voices-v1.0.bin"))
    voice, base = ep.get("voice", "am_michael"), ep.get("speed", 1.05)
    out = []
    for sc in ep["scenes"]:
        sp_m, vol = MOODS.get(sc.get("mood", "calm"), MOODS["calm"])
        audio, segs, cur = [], [], 0.0
        for txt, pause in chunks(sc.get("narration", "").strip()):
            a, sr = k.create(spoken(txt), voice=sc.get("voice", voice), speed=base * sp_m, lang="en-us")
            nz = np.where(np.abs(a) > 0.01)[0]
            a = ((a[max(0, nz[0] - 600): nz[-1] + 1200] if len(nz) else a) * vol).astype(np.float32)
            segs.append((txt, cur, len(a) / SR)); audio.append(a); cur += len(a) / SR
            if pause:
                audio.append(np.zeros(int(SR * pause), dtype=np.float32)); cur += pause
        if not audio:
            audio = [np.zeros(int(SR * sc.get("hold", 1.5)), dtype=np.float32)]
        out.append((np.concatenate(audio), segs))
    return out


def build_timeline(ep, clips):
    t, scenes, words, gid = 0.4, [], [], 0  # 0.4s fade-in lead
    for sc, (a, segs) in zip(ep["scenes"], clips):
        dur = len(a) / SR
        start, end = t, t + dur + GAP + sc.get("hold_after", 0.0)
        s = dict(sc); s["start"], s["end"], s["voice_start"], s["voice_dur"] = start, end, t, dur
        scenes.append(s)
        hi = {h.lower() for h in sc.get("highlight", [])}
        for txt, off, sdur in segs:
            toks = txt.split()
            weights = [len(re.sub(r"[^\w]", "", w)) + 2 + (4 if re.search(r"[.,!?…]$", w) else 0) for w in toks]
            tot = sum(weights); cur = t + off; glen = 0
            for i, (w, wt) in enumerate(zip(toks, weights)):
                wd = sdur * wt / tot
                if glen >= 3 or (i and re.search(r"[.!?…]$", toks[i - 1])):
                    gid += 1; glen = 0
                clean = re.sub(r"[^\w']", "", w).lower()
                words.append({"w": re.sub(r"[\"“”]", "", w), "start": cur, "end": cur + wd, "group": gid, "hi": clean in hi})
                glen += 1; cur += wd
            gid += 1
        t = end
    return {"scenes": scenes, "words": words, "duration": t + 0.2, "hud": ep.get("hud", []),
            "series": ep.get("series", ""), "costume": ep.get("costume", "cap")}


def make_audio(tl, clips, out_wav, tmp):
    total = int(tl["duration"] * SR) + SR
    voice = np.zeros(total, dtype=np.float32)
    for sc, (a, _) in zip(tl["scenes"], clips):
        i = int(sc["voice_start"] * SR); voice[i:i + len(a)] += a[: max(0, total - i)]
    vpath = os.path.join(tmp, "voice.wav"); sf.write(vpath, voice, SR)
    d = tl["duration"]
    # free generated bed: low tension drone + soft pulse, ducked under the voice
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", vpath,
           "-f", "lavfi", "-t", f"{d:.2f}", "-i", "sine=f=55:sample_rate=24000",
           "-f", "lavfi", "-t", f"{d:.2f}", "-i", "sine=f=82.5:sample_rate=24000",
           "-f", "lavfi", "-t", f"{d:.2f}", "-i", "anoisesrc=c=brown:a=0.05:r=24000",
           "-filter_complex",
           "[1][2]amix=inputs=2,volume=0.35,tremolo=f=0.5:d=0.4[drone];"
           "[3]lowpass=f=300,volume=0.6[air];[drone][air]amix=inputs=2,afade=t=in:d=1.5,"
           f"afade=t=out:st={max(0,d-1.5):.2f}:d=1.5[bed];"
           "[bed][0]sidechaincompress=threshold=0.02:ratio=6:release=400[bedd];"
           "[0]loudnorm=I=-15:TP=-1.5:LRA=7[v];[v][bedd]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95",
           "-ar", "48000", out_wav]
    subprocess.run(cmd, check=True)


def render_video(tl, wav, out_mp4, fps):
    from playwright.sync_api import sync_playwright
    n = int(tl["duration"] * fps)
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps),
                            "-c:v", "mjpeg", "-i", "-", "-i", wav, "-af", "apad", "-t", f"{n / fps:.3f}", "-c:v", "libx264", "-preset", "medium",
                            "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                            "-movflags", "+faststart", out_mp4], stdin=subprocess.PIPE)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto("file://" + os.path.join(HERE, "renderer.html"))
        pg.evaluate("tl => window.setup(tl)", tl)
        t0 = time.time()
        for f in range(n):
            pg.evaluate(f"window.renderAt({f / fps})")
            enc.stdin.write(pg.screenshot(type="jpeg", quality=92))
            if f % (fps * 5) == 0:
                print(f"  frame {f}/{n}  {time.time() - t0:.0f}s", flush=True)
        b.close()
    enc.stdin.close(); enc.wait()
    if enc.returncode:
        sys.exit("ffmpeg failed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode"); ap.add_argument("out")
    ap.add_argument("--models", default=os.environ.get("KOKORO_DIR", os.path.join(HERE, "models")))
    ap.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()
    ep = json.load(open(a.episode))
    with tempfile.TemporaryDirectory() as tmp:
        print("voice…", flush=True); clips = tts_scenes(ep, a.models)
        tl = build_timeline(ep, clips)
        print(f"duration {tl['duration']:.1f}s", flush=True)
        wav = os.path.join(tmp, "mix.wav"); make_audio(tl, clips, wav, tmp)
        print("frames…", flush=True); render_video(tl, wav, a.out, a.fps)
    print("done", a.out)


if __name__ == "__main__":
    main()
