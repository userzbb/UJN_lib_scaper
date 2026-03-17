# -*- coding: utf-8 -*-
import base64
import time

import ddddocr
from playwright.sync_api import sync_playwright


def analyze_login():
    print("启动浏览器进行登录接口分析 (Header检查版)...")

    ocr = ddddocr.DdddOcr(show_ad=False, old=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 容器用于存储请求
        captured_requests = []

        def on_request(req):
            # 排除静态资源，减少干扰
            if req.resource_type in ["image", "stylesheet", "font", "media"]:
                return
            captured_requests.append(req)

        page.on("request", on_request)

        print("正在打开页面: https://seat.ujn.edu.cn/libseat/#/login")
        page.goto("https://seat.ujn.edu.cn/libseat/#/login")

        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except:
            pass

        # 1. 获取验证码
        print("正在获取验证码...")
        code = "0000"
        try:
            captcha_elem = page.locator(".captcha-wrap img").first
            if not captcha_elem.count():
                captcha_elem = page.locator("img[src^='data:image']").first

            if captcha_elem.count():
                time.sleep(1)  # 等待渲染
                captcha_bytes = captcha_elem.screenshot()
                res = ocr.classification(captcha_bytes)
                if isinstance(res, dict):
                    code = res.get("text", "")
                else:
                    code = str(res)
                print(f"验证码识别结果: {code}")
            else:
                print("未找到验证码元素")
        except Exception as e:
            print(f"验证码识别出错: {e}")

        # 2. 填写表单
        test_user = "202331223125"
        test_pass = "080518"
        print(f"填写账号: {test_user}, 密码: {test_pass}, 验证码: {code}")

        try:
            page.fill("input[placeholder='请输入账号']", test_user)
            page.fill("input[placeholder='请输入密码']", test_pass)
            page.fill("input[placeholder='请输入验证码']", str(code))
        except Exception as e:
            print(f"填写表单失败: {e}")
            browser.close()
            return

        pre_action_count = len(captured_requests)

        # 3. 触发登录
        print("尝试触发登录...")
        login_btn = page.query_selector(
            "button:has-text('登录')"
        ) or page.query_selector(".login-btn")

        if login_btn:
            print("点击登录按钮...")
            login_btn.click()
        else:
            print("⚠️ 未找到登录按钮")
            browser.close()
            return

        print("等待请求响应 (5秒)...")
        time.sleep(5)

        # 4. 分析请求
        print("\n" + "=" * 50)
        print("【动作后产生的新请求分析】")

        new_requests = captured_requests[pre_action_count:]
        found_auth = False

        for req in new_requests:
            # 重点检查包含 auth 的请求
            if "auth" in req.url:
                print(f"\n🎯 发现关键请求: [{req.method}] {req.url}")
                found_auth = True

                print("-" * 20)
                print("请求头 (Headers):")
                headers = req.all_headers()
                for k, v in headers.items():
                    # 打印所有头，寻找认证信息
                    print(f"{k}: {v}")
                print("-" * 20)

                # 检查 Authorization 头
                # 注意：Playwright 的 all_headers() 返回的 key 都是小写的
                if "authorization" in headers:
                    auth_val = headers["authorization"]
                    print(f"⚠️ 发现 Authorization 头: {auth_val}")

                    if "Basic" in auth_val:
                        print("检测到 Basic Auth，正在尝试解码...")
                        try:
                            encoded = auth_val.split(" ")[1]
                            decoded = base64.b64decode(encoded).decode("utf-8")
                            print(f"🔓 解码结果: {decoded}")
                            if test_user in decoded and test_pass in decoded:
                                print(
                                    "✅ 确认: 账号密码通过 Basic Auth 传输！(HTTP 爆破可行)"
                                )
                        except Exception as e:
                            print(f"解码失败: {e}")
                else:
                    print("⚠️ 未在 Header 中发现 Authorization 字段。")
                    # 检查是否有其他自定义 Header 携带了类似 token 的东西

                # 打印响应
                try:
                    resp = req.response()
                    if resp:
                        print(f"响应状态: {resp.status}")
                        print(f"响应内容: {resp.text()[:300]}...")
                except:
                    pass

        if found_auth:
            print("\n结论：已定位登录接口，请查看上方 Header 分析。")
        else:
            print("\n结论：未找到 auth 相关请求，请检查日志。")

        print("=" * 50)
        browser.close()


if __name__ == "__main__":
    analyze_login()
