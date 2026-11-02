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
DUE_H = 18          # pipeline makes an Imagine You episode once the last is 18 h old (daily since 2 Nov 2026)
OVERDUE_H = 30      # daily: the 4 scheduled runs should have made one by then
STUCK_H = 3         # approved but posted nowhere
PARTIAL_H = 1       # posted on some platforms, failed on others: retry quickly
ALERT_H = 48        # episode not made at all
POST_ALERT_H = 12   # still not on YouTube/Instagram/Facebook after ~10 hourly retries
COOLDOWN_MIN = 45
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
    if cmd == "run":  # the full scheduled path: check (replies, auto-approvals, posting) + make whatever is due
        gh("workflow", "run", "video.yml", "--ref", "main", "-f", "cmd=auto", "-f", f"series={series}")
        print("started Video autopilot: full run")
        return
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
        return {"every_how": ("youtube", "youtube_short")}.get(e["series"], ("youtube", "instagram", "facebook"))
    stuck = [r for r, e in eps.items() if e.get("approved") and (
        (e["status"] == "approved" and hours_since(e["approved"]) > STUCK_H) or
        (e["status"] == "partly_published" and hours_since(e["approved"]) > PARTIAL_H and
         not all(str(e.get("links", {}).get(p, "")).startswith("http") for p in platforms_of(e))))]
    try:
        from autopilot.pipeline import SERIES
        paused = {k for k, v in SERIES.items() if v.get("paused")}
    except Exception:
        paused = set()
    stuck = [r for r in stuck if eps[r]["series"] not in paused]
    eh = [e for e in eps.values() if e["series"] == "every_how" and "every_how" not in paused]
    eh_age = min(hours_since(e["created"]) for e in eh) if eh else None
    print(f"newest Imagine You episode is {age:.1f} h old; stuck approved: {stuck or 'none'}")

    auto_due = []
    try:
        from autopilot.pipeline import AUTO_APPROVE_H, auto_ok
        for r, e in eps.items():
            sent = e.get("emailed_at") or e.get("created")
            if e["status"] == "pending" and sent and hours_since(sent) > AUTO_APPROVE_H and e["series"] not in paused:
                if auto_ok(e, json.load(open(os.path.join(ROOT, e["file"])))):
                    auto_due.append(r)
    except Exception as exc:
        print("auto-approve check failed:", exc)
    if auto_due:
        print(f"auto-approval due: {auto_due}")
    # The watchdog is the real scheduler (2 Nov 2026: GitHub dropped most of the autopilot's own scheduled runs).
    # Whenever an episode is DUE (not only overdue), something is stuck or an auto-approval is due, it starts a
    # full autopilot run: replies + posting, then make Imagine You and Every How if due (due-checked, so never doubles).
    due = []
    if age > DUE_H:
        due.append(f"Imagine You due ({age:.0f} h since the last)")
    if eh_age is not None and eh_age > DUE_H:
        due.append(f"Every How due ({eh_age:.0f} h since the last)")
    try:
        from autopilot.pipeline import SERIES as _S
        from datetime import datetime as _dt
        now = _dt.now(timezone.utc)
        for r, e in eps.items():  # Paws & Claws (or any scheduled episode) whose time has come
            if e["status"] == "scheduled" and e.get("post_after") and _dt.fromisoformat(e["post_after"]) <= now:
                due.append(f"{r} scheduled to go live")
    except Exception as exc:
        print("scheduled check failed:", exc)
    # Episodes waiting for Haseeb: read his replies at least hourly (2 Nov: a reply waited for the next
    # GitHub-scheduled run, which GitHub often drops). A check run is short and cannot make or double-post anything.
    waiting = [r for r, e in eps.items() if e["status"] == "pending" and e["series"] not in paused]
    action = "run" if (due or stuck or auto_due) else ("check" if waiting else None)
    if waiting and action == "check":
        print(f"waiting for Haseeb's reply: {waiting}; reading replies")
    series = "imagine_you"
    if due:
        print("due: " + "; ".join(due))
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
