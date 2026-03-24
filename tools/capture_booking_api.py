# -*- coding: utf-8 -*-
"""
UJN 图书馆座位预约/签到 API 抓包分析脚本

功能：
1. 登录并获取 Token
2. 捕获预约、签到、取消等所有 API 请求
3. 分析请求头、请求体、响应格式

使用方法:
    uv run python tools/capture_booking_api.py
"""

import base64
import time

import ddddocr
from playwright.sync_api import sync_playwright

# 复用现有的 HMAC 认证逻辑
import sys

sys.path.insert(0, ".")
from src.utils.crypto import generate_headers


def capture_booking_api():
    print("🚀 启动预约/签到 API 抓包分析...")
    print("目标: 捕获座位预约、签到、取消等关键API")
    print("=" * 60)

    ocr = ddddocr.DdddOcr(show_ad=False, old=True)

    # 用于存储所有请求
    all_requests = []

    # 关键域名/路径过滤关键词
    API_KEYWORDS = [
        "rest",
        "api",
        "book",
        "reserve",
        "sign",
        "check",
        "cancel",
        "seat",
        "room",
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 头less=False方便观察
        context = browser.new_context()
        page = context.new_page()

        def on_request(req):
            """捕获所有非静态资源的请求"""
            url_lower = req.url.lower()
            # 过滤：只保留目标网站的API请求
            if "seat.ujn.edu.cn" not in req.url:
                return
            if req.resource_type in [
                "image",
                "stylesheet",
                "font",
                "media",
                "websocket",
            ]:
                return
            # 进一步过滤API关键词
            for kw in API_KEYWORDS:
                if kw in url_lower:
                    all_requests.append(
                        {
                            "request": req,
                            "url": req.url,
                            "method": req.method,
                            "timestamp": time.time(),
                        }
                    )
                    break

        page.on("request", on_request)

        print("🌐 打开登录页面: https://seat.ujn.edu.cn/libseat/#/login")
        page.goto("https://seat.ujn.edu.cn/libseat/#/login")

        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass

        # ========== 第1步: 登录 ==========
        print("\n[1/4] 执行登录操作...")

        # 获取验证码
        captcha_elem = page.locator(".captcha-wrap img").first
        if not captcha_elem.count():
            captcha_elem = page.locator("img[src^='data:image']").first

        code = "0000"
        if captcha_elem.count():
            time.sleep(1)
            captcha_bytes = captcha_elem.screenshot()
            res = ocr.classification(captcha_bytes)
            code = res.get("text", "0000") if isinstance(res, dict) else str(res)
            print(f"   验证码识别: {code}")

        # 填写登录信息 (使用测试账号，需要时可修改)
        test_user = "202331223125"  # TODO: 修改为有效账号
        test_pass = "080518"  # TODO: 修改为有效密码

        try:
            page.fill("input[placeholder='请输入账号']", test_user)
            page.fill("input[placeholder='请输入密码']", test_pass)
            page.fill("input[placeholder='请输入验证码']", code)
        except Exception as e:
            print(f"   填写表单失败: {e}")

        # 点击登录
        login_btn = page.query_selector(
            "button:has-text('登录')"
        ) or page.query_selector(".login-btn")
        if login_btn:
            login_btn.click()
            print("   已点击登录按钮")

        time.sleep(3)

        # 检查登录是否成功
        try:
            page.wait_for_url("**/#/home", timeout=5000)
            print("   ✅ 登录成功!")
        except:
            print("   ⚠️ 未检测到跳转，可能登录失败")
            current_url = page.url
            print(f"   当前URL: {current_url}")

        time.sleep(2)

        # ========== 第2步: 进入预约页面 ==========
        print("\n[2/4] 导航到座位预约页面...")

        # 尝试点击"自选座位"或类似入口
        try:
            self_select = page.locator("text=自选座位").first
            if self_select.count():
                self_select.click()
                print("   点击了'自选座位'")
                time.sleep(2)
        except Exception as e:
            print(f"   点击'自选座位'失败: {e}")

        # 尝试选择一个阅览室
        try:
            rooms = page.locator(".room-name").all()
            if rooms:
                print(f"   发现 {len(rooms)} 个阅览室")
                # 点击第一个可见的阅览室
                for room in rooms:
                    if room.is_visible():
                        room.click()
                        print(f"   点击了阅览室: {room.inner_text()}")
                        time.sleep(2)
                        break
        except Exception as e:
            print(f"   选择阅览室失败: {e}")

        time.sleep(2)

        # ========== 第3步: 选择座位并尝试预约 ==========
        print("\n[3/4] 尝试选择座位...")

        # 点击座位
        try:
            seats = page.locator(".seat-name").all()
            if seats:
                print(f"   发现 {len(seats)} 个座位")
                for seat in seats[:5]:  # 最多尝试前5个
                    try:
                        if seat.is_visible():
                            seat_text = seat.inner_text()
                            # 点击座位的父元素
                            seat.click()
                            print(f"   点击了座位: {seat_text}")
                            time.sleep(1)
                            break
                    except:
                        continue
        except Exception as e:
            print(f"   选择座位失败: {e}")

        time.sleep(2)

        # 查找并点击"确认"或"预约"按钮
        print("   查找确认/预约按钮...")
        confirm_keywords = [
            "确认",
            "提交",
            "预约",
            "确定",
            "book",
            "confirm",
            "reserve",
        ]

        for keyword in confirm_keywords:
            try:
                btns = page.locator(f"button:has-text('{keyword}')").all()
                for btn in btns:
                    if btn.is_visible():
                        print(f"   点击按钮: {keyword}")
                        btn.click()
                        time.sleep(2)
                        break
            except:
                continue

        # ========== 第4步: 分析捕获的请求 ==========
        print("\n" + "=" * 60)
        print("[4/4] 捕获到的 API 请求分析")
        print("=" * 60)

        # 去重
        seen_urls = set()
        api_requests = []

        for item in all_requests:
            req = item["request"]
            url = req.url
            if url not in seen_urls and "seat.ujn.edu.cn" in url:
                seen_urls.add(url)
                api_requests.append(item)

        print(f"\n共捕获 {len(api_requests)} 个独立API请求:\n")

        for i, item in enumerate(api_requests, 1):
            req = item["request"]
            print(f"--- 请求 #{i} ---")
            print(f"URL: {req.url}")
            print(f"方法: {req.method}")

            # 打印请求头
            print("请求头:")
            headers = req.all_headers()
            for k, v in headers.items():
                if k in [
                    "x-request-id",
                    "x-request-date",
                    "x-hmac-request-key",
                    "content-type",
                    "authorization",
                    "logintype",
                ]:
                    print(f"  {k}: {v}")

            # 尝试获取post数据
            try:
                post_data = req.post_data
                if post_data:
                    print(f"POST数据: {post_data[:200]}")
            except:
                pass

            # 获取响应
            try:
                resp = req.response()
                if resp:
                    print(f"响应状态: {resp.status}")
                    body = resp.text()
                    if body:
                        print(f"响应内容: {body[:300]}...")
            except:
                pass

            print()

        # ========== 保存结果 ==========
        output_file = "captured_apis.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("UJN 图书馆 API 抓包结果\n")
            f.write(f"抓包时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")

            for i, item in enumerate(api_requests, 1):
                req = item["request"]
                f.write(f"#{i} {req.method} {req.url}\n")
                headers = req.all_headers()
                for k, v in headers.items():
                    f.write(f"  {k}: {v}\n")
                f.write("\n")

        print(f"✅ 结果已保存到: {output_file}")

        print("\n按 Enter 关闭浏览器...")
        input()
        browser.close()


if __name__ == "__main__":
    capture_booking_api()
