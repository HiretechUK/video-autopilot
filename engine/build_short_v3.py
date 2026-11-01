"""Imagine You v3: 2D characters in colourful 3D sets (the Rick's Clips look; rule book: autopilot/RULEBOOK_imagine_you.md).

Same free stack and the same episode JSON as v2. Voice, timing and sound come from v2 unchanged; only the picture is new:
renderer_v3.html draws each scene as a three.js 3D set (ink outlines, lens blur, grade) with the red-cap hero as a lit
2D card, a gliding camera that keeps creeping in, one-word captions and a 4-frame flash on place changes.

Usage: python build_short_v3.py episode.json out.mp4 [--models DIR] [--fps 30]
"""
import argparse, json, os, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_short as v1  # noqa: E402
import build_short_v2 as v2  # noqa: E402

CHROME_ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
               "--allow-file-access-from-files"]


def render_video(tl, wav, out_mp4, fps):
    from playwright.sync_api import sync_playwright
    n = int(tl["duration"] * fps)
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps),
                            "-c:v", "mjpeg", "-i", "-", "-i", wav, "-af", "apad", "-t", f"{n / fps:.3f}", "-c:v", "libx264",
                            "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                            "-movflags", "+faststart", out_mp4], stdin=subprocess.PIPE)
    with sync_playwright() as p:
        kw = {"args": CHROME_ARGS}
        if os.environ.get("CHROME_PATH"):
            kw["executable_path"] = os.environ["CHROME_PATH"]
        b = p.chromium.launch(**kw)
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto("file://" + os.path.join(HERE, "renderer_v3.html"))
        pg.wait_for_function("window.ready === true", timeout=60000)
        pg.evaluate("tl => window.setup(tl)", tl)
        t0 = time.time()
        for f in range(n):
            pg.evaluate(f"window.renderAt({f / fps})")
            if errors:
                sys.exit("renderer error: " + errors[0])
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
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        print("voice…", flush=True)
        clips = v1.tts_scenes(ep, a.models)
        tl = v1.build_timeline(ep, clips)
        shift = 0.35  # hook: frame 0 is mid-action (the reference's voice starts at frame 1-4)
        for s in tl["scenes"]:
            for k in ("start", "end", "voice_start"):
                s[k] = max(0.0, s[k] - shift)
        for w in tl["words"]:
            w["start"] -= shift
            w["end"] -= shift
        tl["duration"] -= shift
        print(f"duration {tl['duration']:.1f}s", flush=True)
        wav = os.path.join(tmp, "mix.wav")
        v2.make_audio_v2(tl, clips, wav, tmp)
        print("frames…", flush=True)
        render_video(tl, wav, a.out, a.fps)
    print("done", a.out)


if __name__ == "__main__":
    main()
