"""Assemble an episode from its plan and downloaded clips: clips/<ep>/<gen>.mp4 -> out/<ep>.mp4 (1080p 24fps) and
out/<ep>-short.mp4 (vertical 1080x1920, first chorus + verse 1, <= 59 s).

python assemble.py <episode>
"""
import json, subprocess, sys
from pathlib import Path

FPS = 24


def run(cmd):
    subprocess.run(cmd, check=True)


_LEAD = {}


def lead_of(src, cap=0.35):
    """Seconds of near-still ease-in at the start of a generated clip (the model starts from the still image)."""
    if src not in _LEAD:
        import numpy as np
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-t", "1.2", "-i", src, "-vf", "scale=160:90,format=gray",
                              "-f", "rawvideo", "-"], capture_output=True).stdout
        f = np.frombuffer(raw, np.uint8).reshape(-1, 90, 160).astype(float)
        d = [np.abs(f[i] - f[i - 1]).mean() for i in range(1, len(f))]
        k = next((i for i, x in enumerate(d) if x > 1.5), len(d))
        _LEAD[src] = min(cap, k / FPS)
    return _LEAD[src]


def piece(src, start_in_clip, dur, out, vertical=False, cap=0.35):
    """Take `dur` seconds of a clip from start_in_clip, stretching slightly or holding the last frame if the clip is short."""
    probe = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                                 capture_output=True, text=True).stdout.strip() or 0)
    if start_in_clip < 0.05:  # a cut into the start of a clip: skip its still ease-in so the cut never looks frozen
        start_in_clip = lead_of(src, cap)
    avail = max(0.1, probe - start_in_clip)
    speed = 1.0
    if avail < dur:
        speed = max(avail / dur, 0.85)  # slow down up to 15%
    pad = max(0.0, dur - avail / speed)
    vf = f"trim=start={start_in_clip:.3f},setpts=(PTS-STARTPTS)/{speed:.4f},fps={FPS}"
    if pad > 0:
        vf += f",tpad=stop_mode=clone:stop_duration={pad + 0.1:.3f}"
    if vertical:  # whole frame (all four friends) over a blurred fill, bigger than a plain letterbox
        vf += (",split[a][b];[a]scale=-2:1920,crop=1080:1920,boxblur=20:2,eq=brightness=-0.05[bg];"
               "[b]scale=1080:-2:flags=lanczos,scale=iw*1.25:-2,crop=1080:ih[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    else:
        vf += ",scale=1920:1080:flags=lanczos"
    vf += ",format=yuv420p"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-filter_complex" if vertical else "-vf", vf, "-t", f"{dur:.3f}",
         "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23" if vertical else "20", "-r", str(FPS), out])


def build(ep, timeline, mp3, out, vertical=False, t0=0.0, t1=None):
    work = Path(f"work/{ep}{'-v' if vertical else ''}")
    work.mkdir(parents=True, exist_ok=True)
    plan = json.load(open(f"plans/{ep}.json"))
    parts, t = [], t0
    end = t1 if t1 is not None else plan["dur"]
    for i, seg in enumerate(timeline):
        a, b = max(seg["a"], t0), min(seg["b"], end)
        if b <= a:
            continue
        g = plan["gens"][seg["gen"]]
        # where in the generated clip this moment sits (later choruses map onto chorus1 proportionally)
        if seg["gen"].startswith("chorus"):
            frac = (a - seg["a"]) / max(0.01, seg["b"] - seg["a"])
            inclip = frac * (g["b"] - g["a"])
        else:
            inclip = a - seg.get("base", g["a"])
        f = work / f"{i:03d}.mp4"
        # frame-exact durations so audio stays in sync
        d = round((b - a) * FPS) / FPS
        if d < 1.0 / FPS:  # sliver shorter than a frame
            continue
        # solo verses are close-up singing: trim little so lips stay in sync; group shots can lose more
        cap = 0.35 if seg["gen"].startswith("verse") else 0.9
        piece(f"clips/{ep}/{seg['gen']}.mp4", inclip, d, str(f), vertical, cap)
        parts.append(f)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-ss", f"{t0:.3f}",
         "-t", f"{end - t0:.3f}", "-i", mp3, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-af", f"afade=t=out:st={max(0, end - t0 - 2):.3f}:d=2", "-c:a", "aac", "-b:a", "192k",
         "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart", out])


def main(ep):
    plan = json.load(open(f"plans/{ep}.json"))
    Path("out").mkdir(exist_ok=True)
    build(ep, plan["timeline"], plan["mp3"], f"out/{ep}.mp4")
    secs = dict((n, t) for n, t in reversed(plan["sections"]))  # first occurrence of each name
    t0 = secs["chorus"]
    t1 = min(secs.get("verse1", t0 + 58), t0 + 58)
    build(ep, plan["timeline"], plan["mp3"], f"out/{ep}-short.mp4", vertical=True, t0=t0, t1=t1)
    print("done", ep)


if __name__ == "__main__":
    main(sys.argv[1])
