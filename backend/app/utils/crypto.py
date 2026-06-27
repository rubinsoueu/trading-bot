from cryptography.fernet import Fernet
import base64
import os
from app.config import settings

def get_fernet_key() -> bytes:
    key = settings.ENCRYPTION_KEY
    return base64.urlsafe_b64encode(key.encode()[:32].ljust(32, b"0"))


def encrypt_secret(plaintext: str) -> str:
    f = Fernet(get_fernet_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    f = Fernet(get_fernet_key())
    return f.decrypt(ciphertext.encode()).decode()


def mask_key(key: str, show_last: int = 4) -> str:
    if not key:
        return ""
    visible = key[-show_last:]
    return f"***{visible}"