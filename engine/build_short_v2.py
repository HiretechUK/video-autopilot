"""Imagine You v2: the same free stack, with the "Make It Pop" lessons applied.

- Picture: renderer_v2.html (light and dust in every scene, a punch-in on every cut, the rule sticker slams with a
  camera shake, the city lights really go out, one window glows, and no fade from black: frame 0 is mid-action).
- Sound: designed in numpy, no samples. Ambience per location, a heartbeat-and-pad score that builds scene by
  scene and stops dead before the twist, and foley timed to the picture (footsteps on the walk cycle, a whoosh on
  every cut, a thud when a rule lands, a power-down when the city goes dark, a sting when the window lights).

Usage: python build_short_v2.py episode.json out.mp4 [--models DIR] [--fps 30]
"""
import argparse, json, math, os, subprocess, tempfile

import numpy as np
import soundfile as sf

import build_short as v1

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
RNG = np.random.default_rng(7)


# ------------------------------------------------------------------ small synth kit
def tt(d):
    return np.arange(int(d * SR)) / SR


def env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(r, 1e-4))


def lowpass(x, fc):
    a = math.exp(-2 * math.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):  # one-pole; fine for short sounds
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def lp_fast(x, fc):
    """One-pole low-pass for long buffers, via an FFT brick-ish shelf (fast enough for minutes of audio)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (f / fc) ** 2)
    return np.fft.irfft(X, len(x)).astype(np.float32)


def hp_fast(x, fc):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= (f / fc) / np.sqrt(1 + (f / fc) ** 2)
    return np.fft.irfft(X, len(x)).astype(np.float32)


def noise(d):
    return RNG.standard_normal(int(d * SR)).astype(np.float32)


def put(buf, at, x, gain=1.0):
    i = int(at * SR)
    if i >= len(buf) or i + len(x) <= 0:
        return
    j = max(0, -i)
    x = x[j:]
    i = max(0, i)
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += x[:n] * gain


# ------------------------------------------------------------------ sounds
def whoosh(d=0.45):
    n = noise(d)
    sweep = np.linspace(400, 3500, len(n))
    y = np.zeros_like(n)
    acc, out = 0.0, []
    for i in range(0, len(n), 256):  # cheap swept low-pass
        a = math.exp(-2 * math.pi * sweep[i] / SR)
        seg = n[i:i + 256]
        o = np.empty_like(seg)
        for k in range(len(seg)):
            acc = (1 - a) * seg[k] + a * acc
            o[k] = acc
        out.append(o)
    y = np.concatenate(out)
    shape = np.sin(np.linspace(0, math.pi, len(y))) ** 2
    return (y * shape * 2.2).astype(np.float32)


def thud():
    t = tt(0.55)
    body = np.sin(2 * math.pi * (70 * t - 25 * t * t)) * env(len(t), 0.002, 0.16)
    slap = lp_fast(noise(0.55), 2500) * env(len(t), 0.0005, 0.03) * 1.5
    return (body + slap).astype(np.float32)


def footstep(kind):
    d = 0.12
    n = lp_fast(noise(d), 900 if kind == "soft" else 1800) * env(int(d * SR), 0.002, 0.03)
    knock = np.sin(2 * math.pi * 95 * tt(d)) * env(int(d * SR), 0.001, 0.025) * (0.5 if kind == "soft" else 0.9)
    return (n * 1.4 + knock).astype(np.float32)


def power_down():
    t = tt(1.8)
    f = 120 * np.exp(-t * 1.6) + 28
    hum = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 1.1)
    clunk = thud()[: int(0.4 * SR)]
    out = np.zeros(len(t), np.float32)
    out += hum.astype(np.float32) * 0.8
    out[: len(clunk)] += clunk * 0.7
    return out


def sting():
    t = tt(3.0)
    out = np.zeros(len(t))
    for f, a in ((392.0, 1), (587.3, .7), (784.0, .5), (1174.7, .25)):  # G major-ish bell, warm, hopeful-uneasy
        out += a * np.sin(2 * math.pi * f * t) * np.exp(-t * 1.3) * np.minimum(1, t / 0.01)
    shimmer = hp_fast(noise(3.0), 5000) * np.exp(-t * 1.8) * 0.15
    return (out * 0.35 + shimmer).astype(np.float32)


def ding():
    t = tt(1.2)
    a = np.sin(2 * math.pi * 880 * t) * np.exp(-t * 4)
    b = np.sin(2 * math.pi * 1318.5 * t) * np.exp(-t * 4)
    out = np.zeros(len(t))
    out += a * 0.4
    k = int(0.12 * SR)
    out[k:] += b[: len(t) - k] * 0.4
    return out.astype(np.float32)


# ------------------------------------------------------------------ beds
def ambience(bg, d, fire):
    n = int(d * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    if bg in ("city_night", "island_night"):
        wind = lp_fast(noise(d), 350) * (0.6 + 0.4 * np.sin(2 * math.pi * 0.11 * t))
        out += wind * 0.55
    elif bg == "supermarket":
        out += (0.05 * np.sin(2 * math.pi * 120 * t) + 0.025 * np.sin(2 * math.pi * 240 * t)).astype(np.float32)
        out += lp_fast(noise(d), 200) * 0.15
    elif bg == "forest_night":
        out += lp_fast(noise(d), 250) * 0.3
        chirp = np.sin(2 * math.pi * 4400 * t) * (np.sin(2 * math.pi * 32 * t) > 0.2)
        gate = (np.sin(2 * math.pi * 0.9 * t + 1.3) > 0.35) * (0.5 + 0.5 * np.sin(2 * math.pi * 0.07 * t))
        out += (chirp * gate * 0.035).astype(np.float32)
    else:
        out += lp_fast(noise(d), 300) * 0.3
    if fire:
        cr = np.zeros(n, np.float32)
        for at in RNG.uniform(0, d, int(d * 9)):
            put(cr, at, hp_fast(noise(0.03), 1500) * env(int(0.03 * SR), 0.0005, 0.006) * RNG.uniform(.3, 1))
        out += cr * 0.6 + lp_fast(noise(d), 180) * 0.25
    return out


def heartbeat(start, end, bpm, total):
    out = np.zeros(total, np.float32)
    beat = 60 / bpm
    k = np.sin(2 * math.pi * 52 * tt(0.25)) * env(int(0.25 * SR), 0.003, 0.07)
    t = start
    while t < end:
        put(out, t, k, 1.0)
        put(out, t + 0.22, k, 0.6)
        t += beat
    return out


def pad(start, end, total, chord=(110.0, 130.81, 164.81), level=0.12):
    d = end - start
    t = tt(d)
    x = np.zeros(len(t))
    for f in chord:
        for det in (-0.6, 0.6):
            ph = 2 * math.pi * (f + det) * t
            x += 2 * ((ph / (2 * math.pi)) % 1) - 1  # saw
    x = lp_fast(x.astype(np.float32), 700)
    fade = np.minimum(1, np.minimum(t / 1.2, (d - t) / 0.4).clip(0))
    out = np.zeros(total, np.float32)
    put(out, start, (x * fade * level / 6).astype(np.float32))
    return out


# ------------------------------------------------------------------ the mix
def design(tl, total_s):
    total = int(total_s * SR) + SR
    bed = np.zeros(total, np.float32)    # ambience + score (ducked under the voice)
    fol = np.zeros(total, np.float32)    # foley (not ducked)
    scenes = tl["scenes"]
    twist = next((i for i, s in enumerate(scenes) if s.get("fx") == "window"), len(scenes))
    for i, s in enumerate(scenes):
        st, en = s["start"], s["end"]
        put(bed, st, ambience(s["bg"], en - st, any(p.startswith("fire") for p in s.get("props", []))), 0.5)
        if i:
            put(fol, st - 0.18, whoosh(), 0.35)
        if s.get("rule"):
            put(fol, st + 0.3, thud(), 0.9)
        if s.get("move_to") is not None and abs(s["move_to"] - s.get("x", .55)) > 0.01:
            kind = "soft" if s["bg"] in ("forest_night", "island", "island_night", "desert", "snow") else "hard"
            # renderer walk cycle: legs follow sin(8t); a foot lands twice per cycle
            k0 = math.ceil((st * 8 - math.pi / 2) / math.pi)
            while True:
                at = (k0 * math.pi + math.pi / 2) / 8
                if at >= en:
                    break
                put(fol, at, footstep(kind), 0.35)
                k0 += 1
        if s.get("fx") == "dark":
            put(fol, st + 0.7 * (en - st), power_down(), 0.8)
        if s.get("choice"):
            put(fol, st, whoosh(0.35), 0.3)
            put(fol, st + 0.35, ding(), 0.5)
        # score: heartbeat + pad that build towards the twist, silence for the twist, warm return after
        if i < twist:
            bpm = 62 + 26 * i / max(1, twist - 1)
            bed += heartbeat(st, en, bpm, total) * 0.55
            bed += pad(st, en, total, level=0.10 + 0.04 * i / max(1, twist - 1))
    if twist < len(scenes):
        s = scenes[twist]
        reveal = s["voice_start"] + max(0.0, s["voice_dur"] - 0.9)
        put(fol, reveal, sting(), 0.9)
        st2 = reveal + 0.4
        bed += pad(st2, scenes[-1]["end"], total, chord=(98.0, 146.83, 196.0), level=0.12)
        bed += heartbeat(scenes[twist + 1]["start"] if twist + 1 < len(scenes) else st2, scenes[-1]["end"], 88, total) * 0.5
    return bed, fol


def make_audio_v2(tl, clips, out_wav, tmp):
    d = tl["duration"]
    total = int(d * v1.SR) + v1.SR
    voice = np.zeros(total, dtype=np.float32)
    for sc, (a, _) in zip(tl["scenes"], clips):
        i = int(sc["voice_start"] * v1.SR)
        voice[i:i + len(a)] += a[: max(0, total - i)]
    vpath = os.path.join(tmp, "voice.wav")
    sf.write(vpath, voice, v1.SR)
    bed, fol = design(tl, d)
    bpath, fpath = os.path.join(tmp, "bed.wav"), os.path.join(tmp, "foley.wav")
    sf.write(bpath, (bed / max(1e-6, np.abs(bed).max()) * 0.5).astype(np.float32), SR)
    sf.write(fpath, (fol / max(1e-6, np.abs(fol).max()) * 0.8).astype(np.float32), SR)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vpath, "-i", bpath, "-i", fpath, "-filter_complex",
                    "[0]aresample=48000,loudnorm=I=-15:TP=-1.5:LRA=7,asplit=2[v][vk];"
                    "[1]volume=0.55[b];[b][vk]sidechaincompress=threshold=0.03:ratio=5:attack=20:release=350[bd];"
                    "[2]volume=0.7[f];[v][bd][f]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.93",
                    "-ar", "48000", "-t", f"{d:.2f}", out_wav], check=True)


def render_video(tl, wav, out_mp4, fps):
    """Same as v1, but draws with renderer_v2.html."""
    import sys, time
    from playwright.sync_api import sync_playwright
    n = int(tl["duration"] * fps)
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps),
                            "-c:v", "mjpeg", "-i", "-", "-i", wav, "-af", "apad", "-t", f"{n / fps:.3f}", "-c:v", "libx264",
                            "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                            "-movflags", "+faststart", out_mp4], stdin=subprocess.PIPE)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto("file://" + os.path.join(HERE, "renderer_v2.html"))
        pg.evaluate("tl => window.setup(tl)", tl)
        t0 = time.time()
        for f in range(n):
            pg.evaluate(f"window.renderAt({f / fps})")
            enc.stdin.write(pg.screenshot(type="jpeg", quality=92))
            if f % (fps * 5) == 0:
                print(f"  frame {f}/{n}  {time.time() - t0:.0f}s", flush=True)
        b.close()
    enc.stdin.close()
    enc.wait()
    if enc.returncode:
        sys.exit("ffmpeg failed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("out")
    ap.add_argument("--models", default=os.environ.get("KOKORO_DIR", os.path.join(HERE, "models")))
    ap.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()
    ep = json.load(open(a.episode))
    with tempfile.TemporaryDirectory() as tmp:
        print("voice…", flush=True)
        clips = v1.tts_scenes(ep, a.models)
        tl = v1.build_timeline(ep, clips)
        # hook: start mid-action, no 0.4 s lead from black
        shift = 0.35
        for s in tl["scenes"]:
            for k in ("start", "end", "voice_start"):
                s[k] = max(0.0, s[k] - shift)
        for w in tl["words"]:
            w["start"] -= shift
            w["end"] -= shift
        tl["duration"] -= shift
        print(f"duration {tl['duration']:.1f}s", flush=True)
        wav = os.path.join(tmp, "mix.wav")
        make_audio_v2(tl, clips, wav, tmp)
        print("frames…", flush=True)
        render_video(tl, wav, a.out, a.fps)
    print("done", a.out)


if __name__ == "__main__":
    main()
