"""Gmail send (SMTP) and reply reading (IMAP), same app-password setup as the LinkedIn autopilot."""
from __future__ import annotations

import email
import imaplib
import os
import re
import smtplib
from email.header import decode_header, make_header
from email.message import EmailMessage

TO = os.environ.get("APPROVER_EMAIL", "haseeb.ahmed.talent@gmail.com")


def _creds():
    u, p = os.environ.get("SMTP_USER"), os.environ.get("SMTP_APP_PASSWORD")
    if not u or not p:
        raise RuntimeError("SMTP_USER / SMTP_APP_PASSWORD secrets are not set")
    return u, p


EMAIL_BUDGET = 20 * 1024 * 1024  # raw bytes of video per email (base64 adds ~37%; Gmail SMTP takes ~35 MB in total)


def _duration(path: str) -> float:
    import subprocess
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0) or 60.0


def _preview(path: str, budget: int = EMAIL_BUDGET) -> str | None:
    """A copy that fits `budget` bytes: longest side 1280 px (720 if needed), bitrate set from the duration."""
    import subprocess
    out = path.replace(".mp4", "_preview.mp4")
    dur = _duration(path)
    for longest, share in ((1280, 0.90), (720, 0.80), (540, 0.70)):
        kbps = max(int(budget * 8 * share / dur / 1000) - 96, 150)
        scale = f"scale='if(gt(iw,ih),{longest},-2)':'if(gt(iw,ih),-2,{longest})'"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-vf", scale, "-c:v", "libx264", "-preset",
                        "veryfast", "-b:v", f"{kbps}k", "-maxrate", f"{kbps}k", "-bufsize", f"{2 * kbps}k",
                        "-c:a", "aac", "-b:a", "96k", out], check=False)
        if os.path.exists(out) and os.path.getsize(out) <= budget:
            return out
    print(f"could not shrink {path} for email", flush=True)
    return None


def send(subject: str, body: str, attachments: list[str] | None = None, smtp=None) -> None:
    u, p = _creds() if smtp is None else ("test@example.com", "")
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = u, TO, subject
    m.set_content(body)
    files = [a for a in (attachments or []) if a and os.path.exists(a)]
    each = EMAIL_BUDGET // max(len(files), 1)
    for path in files:
        if os.path.getsize(path) > each:
            # 2 Nov 2026: a 25 MB render was silently dropped, so Haseeb got "The video is attached" with no video.
            # Every video he must approve is attached; too-big ones as a smaller preview copy.
            path = _preview(path, each)
            if not path:
                continue
        with open(path, "rb") as f:
            m.add_attachment(f.read(), maintype="video", subtype="mp4", filename=os.path.basename(path))
    if smtp is not None:
        return smtp(m)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(u, p)
        s.send_message(m)


def _typed_text(msg) -> str:
    """The text Haseeb typed, without the quoted original."""
    part = None
    if msg.is_multipart():
        for p in msg.walk():
            if p.get_content_type() == "text/plain" and "attachment" not in str(p.get("Content-Disposition", "")):
                part = p
                break
    else:
        part = msg
    if part is None:
        return ""
    txt = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
    lines = []
    for line in txt.splitlines():
        st = line.strip()
        if (re.match(r"^\s*>", line) or re.match(r"^On .+wrote:\s*$", st) or st.startswith("-----") or st.startswith("_____")
                or re.match(r"^(From|Sent|Fra|Von|De):\s", st) or re.match(r"^Sent from (my |Outlook|Mail|Yahoo)", st, re.I)
                or re.match(r"^Get Outlook for", st, re.I)):
            break
        lines.append(line)
    return "\n".join(lines).strip()


def fetch_replies(refs: list[str], seen: set[str]) -> list[tuple[str, str, str]]:
    """[(ref, message_id, typed_text)] for unseen replies from the approver to the approval emails."""
    if not refs:
        return []
    u, p = _creds()
    out = []
    M = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    try:
        M.login(u, p)
        for box in ('"[Gmail]/All Mail"', '"[Google Mail]/All Mail"', "INBOX"):
            if M.select(box, readonly=True)[0] == "OK":
                break
        for ref in refs:
            typ, data = M.search(None, "X-GM-RAW", f'"subject:({ref}) from:{TO} newer_than:14d"')
            if typ != "OK":
                continue
            for num in data[0].split():
                typ, md = M.fetch(num, "(RFC822)")
                if typ != "OK" or not md or not isinstance(md[0], tuple):
                    continue
                msg = email.message_from_bytes(md[0][1])
                mid = msg.get("Message-ID", "")
                subj = str(make_header(decode_header(msg.get("Subject", ""))))
                if mid in seen or not subj.lower().startswith("re:"):
                    continue
                out.append((ref, mid, _typed_text(msg)))
    finally:
        try:
            M.logout()
        except Exception:
            pass
    return out


def parse(text: str) -> tuple[str, str]:
    """('approve'|'skip'|'change', notes)."""
    t = text.strip()
    low = t.lower()
    if re.fullmatch(r"(approved?|yes|ok(ay)?|post( it)?|go|good|looks good|publish( it)?)[.! ]*", low):
        return "approve", ""
    if re.match(r"^(skip|cancel|bin it|drop( it)?|no)\b", low):
        return "skip", ""
    if low.startswith("approved") and len(low) < 25:
        return "approve", ""
    return "change", t
