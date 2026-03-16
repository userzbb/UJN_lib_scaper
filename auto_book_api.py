# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
import time
import base64
import requests
import json

# ================= 配置区域 =================
USERNAME = "YOUR_USERNAME"
PASSWORD = "YOUR_PASSWORD"

# 【在此处填入你的打码平台信息】
# 这里以 YesCaptcha / 2Captcha 类的通用接口为例
# 如果你用的是其他平台，请参考他们的 "Base64 识别文档" 修改 solve_captcha 函数
API_KEY = "你的_API_KEY_填在这里"
API_URL = "https://api.yescaptcha.com/createTask"  # 示例 URL
# ===========================================


def solve_captcha_via_api(image_path):
    """
    读取图片 -> 转 Base64 -> 发送给 AI API -> 获取结果
    """
    with open(image_path, "rb") as f:
        img_bytes = f.read()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")

    # 构造请求数据 (这是 YesCaptcha 的通用格式，其他平台大同小异)
    data = {
        "clientKey": API_KEY,
        "task": {
            "type": "ImageToTextTask",  # 图片转文字任务
            "body": img_base64,
            "websiteInstanceId": "",
            "websiteKey": "",
        },
    }

    try:
        print(f"正在请求 API 识别验证码...")
        resp = requests.post(API_URL, json=data, timeout=10)
        result = resp.json()

        # 解析返回结果 (根据不同平台的文档，这里的字段可能不同)
        # YesCaptcha / 2Captcha 通常是 solution -> text
        if result.get("errorId") == 0:
            code = result.get("solution", {}).get("text", "")
            print(f"API 识别成功: {code}")
            return code
        else:
            print(f"API 报错: {result}")
            return None

    except Exception as e:
        print(f"API 请求失败: {e}")
        return None


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("正在打开登录页面...")
        page.goto("https://seat.ujn.edu.cn/libseat/#/login")
        page.wait_for_load_state("networkidle")

        # 尝试自动登录
        for attempt in range(3):
            print(f"尝试登录第 {attempt + 1} 次...")

            try:
                page.fill("input[placeholder='请输入账号']", USERNAME)
                page.fill("input[placeholder='请输入密码']", PASSWORD)

                # 截图验证码
                # 注意：这里需要根据实际页面调整选择器，如果找不到图会报错
                captcha_elem = page.query_selector(
                    "img[src*='captcha'], img[src*='random'], .captcha-img"
                )

                # 如果找不到，尝试暴力找 img
                if not captcha_elem:
                    imgs = page.query_selector_all("img")
                    for img in imgs:
                        box = img.bounding_box()
                        if box and 60 < box["width"] < 200 and 20 < box["height"] < 80:
                            captcha_elem = img
                            break

                if not captcha_elem:
                    print("找不到验证码图片！")
                    return

                captcha_path = "temp_captcha_api.png"
                captcha_elem.screenshot(path=captcha_path)

                # === 调用 API 识别 ===
                code = solve_captcha_via_api(captcha_path)

                if code:
                    page.fill("input[placeholder='请输入验证码']", code)

                    # 点击登录
                    login_btn = page.query_selector(
                        "button:has-text('登录'), .login-btn"
                    )
                    if login_btn:
                        login_btn.click()

                    # 检查结果
                    try:
                        page.wait_for_url("**/#/home", timeout=5000)
                        print("登录成功！")
                        break
                    except:
                        print("登录可能失败，重试中...")
                        captcha_elem.click()  # 刷新验证码
                        time.sleep(2)
                else:
                    print("API 未返回结果，重试...")
                    time.sleep(1)

            except Exception as e:
                print(f"发生错误: {e}")

        else:
            print("多次登录失败，退出。")
            browser.close()
            return

        # 登录成功后保持浏览器打开
        print("\n=== 登录成功，请手动继续或编写后续预约逻辑 ===")
        page.pause()


if __name__ == "__main__":
    run()
