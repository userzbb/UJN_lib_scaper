#!/usr/bin/env python3
import sys

sys.path.insert(0, ".")
from src.utils.crypto import generate_headers, encrypt_aes
import requests
import time
import uuid

BASE_URL = "https://seat.ujn.edu.cn"
CAPTCHA_API = f"{BASE_URL}/auth/createCaptcha"
LOGIN_API = f"{BASE_URL}/rest/auth"


def get_captcha(sess):
    resp = sess.get(CAPTCHA_API, timeout=5)
    data = resp.json()
    return data.get("captchaId"), data.get("captchaImage", "").split(",")[-1]


def test_booking_api():
    print("UJN 图书馆 API 完整测试")
    print("=" * 60)

    sess = requests.Session()

    # 先登录获取token
    print("\n[1] 获取验证码...")
    captcha_id, img_b64 = get_captcha(sess)
    print(f"    CaptchaId: {captcha_id}")

    # 保存验证码图片用于识别
    import base64

    with open("test_captcha.png", "wb") as f:
        f.write(base64.b64decode(img_b64))
    print("    验证码已保存到 test_captcha.png")
    print("    请识别验证码并填入下面（或者用ddddocr自动识别）")

    code = input("    输入验证码: ").strip()

    # 测试账号 - 需要修改为有效账号
    username = input("    输入学号: ").strip()
    password = input("    输入密码: ").strip()

    print(f"\n[2] 登录中... ({username})")
    headers = generate_headers("GET")
    headers["username"] = encrypt_aes(username)
    headers["password"] = encrypt_aes(password)

    resp = sess.get(
        LOGIN_API,
        headers=headers,
        params={"captchaId": captcha_id, "answer": code},
        timeout=5,
    )
    print(f"    Status: {resp.status_code}")
    print(f"    Response: {resp.text[:500]}")

    login_data = resp.json()
    if login_data.get("status") == "success":
        token = login_data.get("data", {}).get("token")
        print(
            f"    ✅ 登录成功! Token: {token[:20]}..."
            if token
            else "    ✅ 登录成功! (无token)"
        )

        # 保存session信息
        sess.headers.update({"token": token} if token else {})

        print("\n[3] 测试各API端点...")

        api_tests = [
            ("GET", "/rest/filters", None),
            ("GET", "/rest/user", None),
            ("GET", "/rest/reservations", None),
        ]

        for method, path, data in api_tests:
            url = BASE_URL + path
            headers = generate_headers(method)
            if token:
                headers["token"] = token

            try:
                if method == "GET":
                    r = sess.get(url, headers=headers, timeout=5)
                else:
                    r = sess.post(url, headers=headers, data=data, timeout=5)

                print(f"\n    --- {method} {path} ---")
                print(f"    Status: {r.status_code}")
                resp_text = r.text[:300]
                print(f"    Response: {resp_text}")
            except Exception as e:
                print(f"    Error: {e}")
    else:
        print(f"    ❌ 登录失败: {login_data.get('message')}")


if __name__ == "__main__":
    test_booking_api()
