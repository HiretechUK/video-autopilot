"""Hourly watchdog for the Video autopilot (Haseeb, 1 Nov 2026: never let an episode go missing).

GitHub can delay or drop scheduled runs, and a run can fail. Every hour this checks:
  1. Imagine You overdue (newest episode older than OVERDUE_H) -> start a `make` run.
  2. An approved episode not posted after STUCK_H hours, or posted on some platforms but
     failed on others (e.g. YouTube ok, Instagram failed)     -> start a `check` run (re-posts).
It never starts a run while another Video autopilot run is queued/running or started in the
last COOLDOWN_MIN minutes, so it can't make duplicates. It only emails Haseeb if an episode is
still missing after ALERT_H hours, or not on every platform after POST_ALERT_H hours
(i.e. many automatic attempts have failed).
"""
import json
import os
import subprocess
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("GITHUB_REPOSITORY", "HiretechUK/video-autopilot")
DUE_H = 36          # pipeline makes an episode once the last is 36 h old
OVERDUE_H = 40      # 4 h grace for the normal scheduled runs
STUCK_H = 3         # approved but posted nowhere
PARTIAL_H = 1       # posted on some platforms, failed on others: retry quickly
ALERT_H = 60        # episode not made at all
POST_ALERT_H = 12   # still not on YouTube/Instagram/Facebook after ~10 hourly retries
COOLDOWN_MIN = 50
EH_OVERDUE_H = 30   # Every How: one a day; scheduled runs make it after 18 h
EH_ALERT_H = 48


def gh(*args):
    return subprocess.run(["gh", *args, "-R", REPO], capture_output=True, text=True, check=True).stdout


def hours_since(iso):
    return (datetime.now(timezone.utc) - datetime.fromisoformat(iso)).total_seconds() / 3600


def autopilot_busy():
    runs = json.loads(gh("run", "list", "-w", "video.yml", "-L", "10", "--json", "status,createdAt"))
    for r in runs:
        if r["status"] in ("queued", "in_progress", "waiting", "pending", "requested"):
            return "a run is already in progress"
        if hours_since(r["createdAt"].replace("Z", "+00:00")) * 60 < COOLDOWN_MIN:
            return "a run started in the last %d min" % COOLDOWN_MIN
    return None


def dispatch(cmd, series="imagine_you"):
    gh("workflow", "run", "video.yml", "--ref", "main", "-f", f"cmd={cmd}", "-f", f"series={series}")
    print(f"started Video autopilot: {cmd} {series}")


def alert(subject, body):
    try:
        from autopilot import mailer
        mailer.send(subject, body)
        print("alert emailed:", subject)
    except Exception as exc:  # never let the alert itself crash the watchdog
        print("could not email alert:", exc)


def main():
    st = json.load(open(os.path.join(ROOT, "autopilot", "state.json")))
    eps = st["episodes"]
    iy = [e for e in eps.values() if e["series"] == "imagine_you"]
    age = min(hours_since(e["created"]) for e in iy) if iy else 999
    # approved but not posted anywhere yet, or posted on some platforms but failed on others
    def platforms_of(e):  # same as pipeline.platforms() (TikTok is separate)
        return ("youtube", "youtube_short", "instagram", "facebook") if e["series"] == "every_how" else ("youtube", "instagram", "facebook")
    stuck = [r for r, e in eps.items() if e.get("approved") and (
        (e["status"] == "approved" and hours_since(e["approved"]) > STUCK_H) or
        (e["status"] == "partly_published" and hours_since(e["approved"]) > PARTIAL_H and
         not all(str(e.get("links", {}).get(p, "")).startswith("http") for p in platforms_of(e))))]
    eh = [e for e in eps.values() if e["series"] == "every_how"]
    eh_age = min(hours_since(e["created"]) for e in eh) if eh else None
    print(f"newest Imagine You episode is {age:.1f} h old; stuck approved: {stuck or 'none'}")

    action = "make" if age > OVERDUE_H else ("check" if stuck else None)
    series = "imagine_you"
    # Every How is daily: overdue after 30 h (made only once the series has its first episode)
    if not action and eh_age is not None and eh_age > EH_OVERDUE_H:
        action, series = "make", "every_how"
        print(f"newest Every How episode is {eh_age:.1f} h old")
    if eh_age is not None and EH_ALERT_H <= eh_age < EH_ALERT_H + 2:
        alert("Every How episode is overdue",
              f"The newest Every How episode is {eh_age:.0f} hours old and the watchdog's retries have not made a new one. "
              f"Runs: https://github.com/{REPO}/actions/workflows/video.yml")
    if not action:
        print("all on schedule")
        return
    busy = autopilot_busy()
    if busy:
        print(f"{action} needed but {busy}; will look again next hour")
    else:
        dispatch(action, series)

    if ALERT_H <= age < ALERT_H + 2:
        alert("Imagine You episode is overdue",
              f"The newest Imagine You episode is {age:.0f} hours old. The watchdog has been retrying "
              f"every hour and it still hasn't been made. Runs: https://github.com/{REPO}/actions/workflows/video.yml")
    for ref in stuck:
        e = eps[ref]
        h = hours_since(e["approved"])
        if POST_ALERT_H <= h < POST_ALERT_H + 2:
            missing = {p: str(e.get("links", {}).get(p, "not posted yet")) for p in platforms_of(e)
                       if not str(e.get("links", {}).get(p, "")).startswith("http")}
            alert(f"{ref} still not on {', '.join(missing)} after {h:.0f} h of retries",
                  f"{e['title']} [{ref}] was approved {h:.0f} hours ago. The watchdog has re-tried posting every "
                  f"hour and these are still failing:\n\n" +
                  "\n".join(f"  {p}: {err[:300]}" for p, err in missing.items()) +
                  "\n\nIf it says a login or token expired, that account needs reconnecting "
                  f"(Video autopilot, Run workflow, cmd connect_instagram or connect_youtube). "
                  f"Runs: https://github.com/{REPO}/actions/workflows/video.yml")

if __name__ == "__main__":
    main()
