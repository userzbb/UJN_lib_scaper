#!/usr/bin/env python3
import sys
import base64

sys.path.insert(0, ".")
from src.utils.crypto import generate_headers, encrypt_aes
import requests
import ddddocr

BASE_URL = "https://seat.ujn.edu.cn"
CAPTCHA_API = f"{BASE_URL}/auth/createCaptcha"
LOGIN_API = f"{BASE_URL}/rest/auth"

ocr = ddddocr.DdddOcr(show_ad=False, old=True)


def solve_captcha(img_b64):
    return ocr.classification(base64.b64decode(img_b64))


def main():
    username = "202331223125"
    password = "080518"

    print(f"UJN 图书馆 API 验证 - {username}")
    print("=" * 60)

    sess = requests.Session()

    print("\n[1] 登录...")
    resp = sess.get(CAPTCHA_API, timeout=10)
    data = resp.json()
    captcha_id = data.get("captchaId")
    img_b64 = data.get("captchaImage", "").split(",")[-1]

    code = solve_captcha(img_b64)
    print(f"    OCR: {code}")

    headers = generate_headers("GET")
    headers["username"] = encrypt_aes(username)
    headers["password"] = encrypt_aes(password)

    resp = sess.get(
        LOGIN_API,
        headers=headers,
        params={"captchaId": captcha_id, "answer": code},
        timeout=10,
    )
    result = resp.json()

    token = result.get("data", {}).get("token", "")
    print(f"    ✅ Token: {token[:30]}...")

    print("\n[2] 测试各 API...")

    tests = [
        ("GET", f"/rest/v2/free/filters", None),
        ("GET", f"/rest/v2/user/reservations", {"token": token}),
        ("GET", f"/rest/v2/availSeats", None),
        ("GET", f"/rest/v2/room/stats2/2/2024-03-25", None),
        ("GET", f"/rest/v2/startTimesForSeat/1234/2024-03-25", None),
    ]

    for method, path, params in tests:
        url = BASE_URL + path
        headers = generate_headers(method)

        try:
            r = sess.get(url, headers=headers, params=params, timeout=10)
            print(f"\n    {method} {path}")
            print(f"    Status: {r.status_code}")
            resp_text = r.text[:400]
            print(f"    Response: {resp_text}")
        except Exception as e:
            print(f"    Error: {e}")


if __name__ == "__main__":
    main()
