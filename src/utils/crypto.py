import base64
import hashlib
import hmac
import time
import uuid

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from src.config import AES_IV, AES_KEY, HMAC_SECRET


def encrypt_aes(text):
    """AES-128-CBC encryption matching the frontend implementation"""
    key = AES_KEY.encode("utf-8")
    iv = AES_IV.encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(text.encode("utf-8"), AES.block_size)
    encrypted = cipher.encrypt(padded)
    # Frontend appends '_encrypt' to the base64 string
    return base64.b64encode(encrypted).decode("utf-8") + "_encrypt"


def generate_headers(method="GET"):
    """Generate headers including the HMAC signature"""
    req_id = str(uuid.uuid4())
    req_date = str(int(time.time() * 1000))

    # Message format: seat::<UUID>::<Timestamp>::<Method>
    message = f"seat::{req_id}::{req_date}::{method}"

    signature = hmac.new(
        bytes(HMAC_SECRET, "utf-8"),
        msg=bytes(message, "utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return {
        "x-request-id": req_id,
        "x-request-date": req_date,
        "x-hmac-request-key": signature,
        "logintype": "PC",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
