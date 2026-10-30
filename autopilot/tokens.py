"""Encrypted token store committed to the repo (autopilot/tokens.enc).

The key is derived from the TOKEN_PASSPHRASE secret, so the file is useless without it.
Holds long-lived platform tokens (YouTube refresh tokens, Instagram tokens) that GitHub Actions
cannot write back into GitHub secrets on its own.
"""
from __future__ import annotations

import base64
import json
import os

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens.enc")
SALT = b"video-autopilot-token-store-v1"


def _fernet():
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    pw = os.environ.get("TOKEN_PASSPHRASE")
    if not pw:
        raise RuntimeError("TOKEN_PASSPHRASE secret is not set")
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=SALT, iterations=390000)
    return Fernet(base64.urlsafe_b64encode(kdf.derive(pw.encode())))


def load() -> dict:
    if not os.path.exists(PATH):
        return {}
    return json.loads(_fernet().decrypt(open(PATH, "rb").read()))


def save(data: dict) -> None:
    with open(PATH, "wb") as f:
        f.write(_fernet().encrypt(json.dumps(data).encode()))


def get(platform: str, account: str) -> dict | None:
    return load().get(platform, {}).get(account)


def put(platform: str, account: str, value: dict) -> None:
    d = load()
    d.setdefault(platform, {})[account] = value
    save(d)
