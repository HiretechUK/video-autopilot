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


def send(subject: str, body: str, attachments: list[str] | None = None) -> None:
    u, p = _creds()
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = u, TO, subject
    m.set_content(body)
    for path in attachments or []:
        if os.path.getsize(path) > 24 * 1024 * 1024:
            continue  # Gmail limit; the body says where to find it instead
        with open(path, "rb") as f:
            m.add_attachment(f.read(), maintype="video", subtype="mp4", filename=os.path.basename(path))
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
