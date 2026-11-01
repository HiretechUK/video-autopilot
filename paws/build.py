"""Build Paws & Claws episodes from paws/data (clip links + timing + song) into dist/PC-NN.mp4 and dist/PC-NN-short.mp4.

python paws/build.py [ep-name ...]   (default: all)
"""
import glob, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(os.getcwd(), "paws-work")
DIST = os.path.join(os.getcwd(), "dist")


def build(ep):
    d = json.load(open(os.path.join(HERE, "data", f"{ep}.json")))
    os.makedirs(os.path.join(WORK, "plans"), exist_ok=True)
    os.makedirs(os.path.join(WORK, "clips", ep), exist_ok=True)
    d["mp3"] = os.path.join(HERE, d["mp3"])
    json.dump(d, open(os.path.join(WORK, "plans", f"{ep}.json"), "w"))
    for g, url in d["clips"].items():
        f = os.path.join(WORK, "clips", ep, f"{g}.mp4")
        if not os.path.exists(f):
            subprocess.run(["curl", "-sSfL", "--retry", "3", "-o", f, url], check=True)
    subprocess.run([sys.executable, os.path.join(HERE, "assemble.py"), ep], cwd=WORK, check=True)
    os.makedirs(DIST, exist_ok=True)
    os.replace(os.path.join(WORK, "out", f"{ep}.mp4"), os.path.join(DIST, f"{d['ref']}.mp4"))
    os.replace(os.path.join(WORK, "out", f"{ep}-short.mp4"), os.path.join(DIST, f"{d['ref']}-short.mp4"))
    print("built", d["ref"], ep, flush=True)


if __name__ == "__main__":
    eps = sys.argv[1:] or sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(HERE, "data", "*.json")))
    for ep in eps:
        build(ep)
