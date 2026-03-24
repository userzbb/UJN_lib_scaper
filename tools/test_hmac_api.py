#!/usr/bin/env python3
"""
UJN 图书馆 - API 调试脚本
使用已破解的 HMAC 直接调用预约/签到 API

uv run python tools/test_hmac_api.py
"""

import base64
import hashlib
import hmac
import time
import uuid
import requests
import json

HMAC_SECRET = "ujnLIB2022tsg"
AES_KEY = "server_date_time"
AES_IV = "client_date_time"
BASE_URL = "https://seat.ujn.edu.cn"


def generate_headers(method="GET"):
    req_id = str(uuid.uuid4())
    req_date = str(int(time.time() * 1000))
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }


from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


def encrypt_aes(text):
    key = AES_KEY.encode("utf-8")
    iv = AES_IV.encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(text.encode("utf-8"), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode("utf-8") + "_encrypt"


def test_api():
    print("UJN 图书馆 API 测试")
    print("=" * 60)

    sess = requests.Session()

    # 测试各种可能的 API endpoints
    test_endpoints = [
        ("/rest/reservation", "POST"),
        ("/rest/reservation/checkIn", "POST"),
        ("/rest/checkIn", "POST"),
        ("/rest/reservations", "GET"),
        ("/rest/user", "GET"),
        ("/rest/filters", "GET"),
    ]

    for path, method in test_endpoints:
        url = BASE_URL + path
        print(f"\n--- Testing: {method} {path} ---")

        headers = generate_headers(method)

        try:
            if method == "GET":
                resp = sess.get(url, headers=headers, timeout=5)
            else:
                resp = sess.post(url, headers=headers, timeout=5)

            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text[:200]}")

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    test_api()
