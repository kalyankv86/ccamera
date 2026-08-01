"""AES-256-GCM encryption for device credentials at rest (NFR-08)."""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ccms.config import settings


def _key() -> bytes:
    key = base64.b64decode(settings.cred_enc_key)
    if len(key) != 32:
        raise RuntimeError("CCMS_CRED_ENC_KEY must decode to exactly 32 bytes (AES-256)")
    return key


def encrypt_secret(plaintext: str) -> str:
    aesgcm = AESGCM(_key())
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_secret(token: str) -> str:
    raw = base64.b64decode(token)
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(_key())
    return aesgcm.decrypt(nonce, ciphertext, None).decode()
