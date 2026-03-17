# -*- coding: utf-8 -*-
import time

from playwright.sync_api import sync_playwright


def find_captcha_endpoint():
    print("🚀 Starting analysis to find Captcha API endpoint...")

    with sync_playwright() as p:
        # Launch browser (headless=True is fine)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        captured_requests = []

        # 1. Set up request listener
        def on_request(req):
            # We look for keywords often associated with captchas
            url_lower = req.url.lower()
            if (
                "captcha" in url_lower
                or "code" in url_lower
                or "random" in url_lower
                or "verify" in url_lower
            ):
                captured_requests.append(req)
                print(f"   [Passive Log] {req.method} {req.url}")

        page.on("request", on_request)

        # 2. Navigate to login page
        print("🌐 Navigating to: https://seat.ujn.edu.cn/libseat/#/login")
        try:
            page.goto("https://seat.ujn.edu.cn/libseat/#/login", timeout=30000)
            page.wait_for_load_state("networkidle")
        except Exception as e:
            print(f"⚠️ Navigation warning: {e}")

        time.sleep(2)  # Wait for initial load

        # 3. Locate Captcha Element
        print("\n🕵️ Looking for captcha image element...")
        captcha_img = page.locator(".captcha-wrap img").first

        if not captcha_img.count():
            # Fallback based on analyze_login.py findings
            captcha_img = page.locator("img[src^='data:image']").first

        if not captcha_img.count():
            # Fallback 2: Generic image in likely container
            captcha_img = page.locator(".el-form-item__content img").first

        if captcha_img.count():
            print("✅ Captcha image element found.")

            # 4. Interact: Click to refresh and capture specific request
            print("👇 Clicking captcha to trigger refresh request...")

            # We use expect_request to strictly catch what happens next
            # We filter for likely types, or just catch the next request that isn't static
            try:
                with page.expect_request(
                    lambda r: r.resource_type in ["xhr", "fetch", "image"], timeout=5000
                ) as request_info:
                    captcha_img.click()

                req = request_info.value
                print(f"\n🎯 CONFIRMED CAPTCHA ENDPOINT: {req.url}")
                print(f"   Method: {req.method}")
                print("   Headers:")
                for k, v in req.all_headers().items():
                    print(f"     {k}: {v}")

                # Check response
                try:
                    resp = req.response()
                    if resp:
                        print(f"   Status: {resp.status}")
                        body = resp.body()
                        print(f"   Body Length: {len(body)} bytes")
                        # If it's JSON, print it
                        try:
                            json_body = resp.json()
                            print(f"   JSON Response: {json_body}")
                        except:
                            print("   (Response is not JSON, likely binary image)")
                except Exception as e:
                    print(f"   Could not read response: {e}")

            except Exception as e:
                print(f"❌ Timed out waiting for request after click: {e}")
                print("   Checking passive logs for candidates...")
                if captured_requests:
                    print(
                        f"   Found {len(captured_requests)} candidate requests in background:"
                    )
                    for r in captured_requests:
                        print(f"   - {r.url}")

        else:
            print("❌ Could not locate captcha image element on page.")

        browser.close()


if __name__ == "__main__":
    find_captcha_endpoint()
