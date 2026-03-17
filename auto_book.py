# -*- coding: utf-8 -*-
import argparse
import csv
import os
import re
import time

import ddddocr
from playwright.sync_api import sync_playwright


def run(input_username=None):
    # ================= 配置区域 =================
    DEFAULT_USERNAME = "202331223111"  # 默认学号

    # 优先使用命令行传入的学号
    if input_username:
        USERNAME = input_username
    else:
        USERNAME = DEFAULT_USERNAME

    print(f"正在处理用户: {USERNAME}")

    # 从 CSV 获取密码
    PASSWORD = None
    csv_file = "found_passwords.csv"
    try:
        # 使用 utf-8-sig 以兼容带 BOM 的 CSV 文件
        with open(csv_file, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 获取 username 和 password，去除可能的空格
                u = row.get("username", "").strip()
                p = row.get("password", "").strip()

                if u == USERNAME:
                    PASSWORD = p
                    break

        if not PASSWORD:
            print(f"错误: 在 {csv_file} 中未找到用户 {USERNAME} 的密码")
            return
    except FileNotFoundError:
        print(f"错误: 找不到 {csv_file}，请确保文件存在且包含 username,password 表头")
        return
    except Exception as e:
        print(f"读取 CSV 失败: {e}")
        return

    print(f"已加载用户 {USERNAME} 的密码。")
    # ===========================================

    ocr = ddddocr.DdddOcr(show_ad=False, old=True)
    # 如果验证码只有数字/字母，可以启用旧模型模式，有时候效果更好
    # ocr = ddddocr.DdddOcr(old=True, show_ad=False)

    with sync_playwright() as p:
        # 启动浏览器 (headless=False 可以让你看到操作过程)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("正在打开登录页面...")
        page.goto("https://seat.ujn.edu.cn/libseat/#/login")

        # 等待页面加载
        page.wait_for_load_state("networkidle")

        # 尝试自动登录直到成功
        max_retries = 5
        for attempt in range(max_retries):
            print(f"尝试登录第 {attempt + 1} 次...")

            # 1. 填写账号密码
            # 注意：如果页面元素ID变了，这里可能需要调整选择器
            try:
                page.fill("input[placeholder='请输入账号']", USERNAME)
                page.fill("input[placeholder='请输入密码']", PASSWORD)
            except Exception as e:
                print(f"填写账号密码失败，请检查页面元素: {e}")
                return

            # 2. 获取验证码图片
            try:
                # 策略: 根据用户提供的 HTML 结构，直接定位 .captcha-wrap 下的图片
                captcha_elem = page.locator(".captcha-wrap img").first

                # 如果找不到，尝试查找所有 Base64 图片
                if not captcha_elem.count():
                    print("未找到 .captcha-wrap img，尝试查找 Base64 图片...")
                    captcha_elem = page.locator("img[src^='data:image']").first

                # 最终检查
                if not captcha_elem.count():
                    print(
                        "错误：无法定位验证码图片 (尝试了 .captcha-wrap img 和 Base64)"
                    )
                    return

                # 截图验证码
                captcha_path = "temp_captcha.png"
                try:
                    # Playwright 的 Locator 应该直接有 screenshot 方法
                    captcha_elem.screenshot(path=captcha_path)
                except Exception as e:
                    print(f"截图失败: {e}")
                    return

                # 3. 识别验证码
                with open(captcha_path, "rb") as f:
                    img_bytes = f.read()

                code = ocr.classification(img_bytes)
                if isinstance(code, dict):
                    # 如果 ddddocr 返回的是字典（新版可能会返回坐标或置信度），提取识别出的文字
                    code = code.get("text", "")
                elif not isinstance(code, str):
                    code = str(code)

                print(f"验证码识别结果: {code}")

                # 4. 填入验证码
                page.fill("input[placeholder='请输入验证码']", code)

                # 5. 点击登录
                # 找到登录按钮
                login_btn = page.query_selector("button:has-text('登录')")
                if not login_btn:
                    login_btn = page.query_selector(".login-btn")  # 尝试类名

                if login_btn:
                    login_btn.click()
                else:
                    print("找不到登录按钮！")
                    return

                # 6. 检查是否登录成功
                try:
                    # 等待 URL 变化或出现特定元素 (比如 '退出' 按钮，或 '预约' 菜单)
                    # 假设登录成功后 URL 会变，或者出现 .user-info
                    page.wait_for_url("**/#/home", timeout=3000)
                    print("登录成功！")
                    break  # 跳出循环
                except:
                    # 检查是否有错误提示
                    error_msg = page.query_selector(".el-message--error, .error-msg")
                    if error_msg:
                        print(f"登录失败提示: {error_msg.inner_text()}")

                    # 刷新验证码 (点击图片通常会刷新)
                    captcha_elem.click()
                    time.sleep(1)  # 等待刷新

            except Exception as e:
                print(f"发生错误: {e}")

        else:
            print("超过最大重试次数，登录失败。")
            return

        # ==========================================
        # 登录成功后的预约逻辑 (需要你补充)
        # ==========================================
        print("\n=== 开始预约流程 ===")

        # 等待页面渲染
        print("等待首页加载 (5秒)...")
        time.sleep(5)

        try:
            # 1. 尝试点击 '自选座位'
            print("正在查找 '自选座位'...")
            self_select_btn = page.locator("text='自选座位'").first
            if self_select_btn.count():
                self_select_btn.click()
                print("点击了 '自选座位'")
                time.sleep(2)
            else:
                print("未找到 '自选座位'，假设直接在列表页或已经是展开状态")

            # 2. 选择阅览室 (第三阅览室北区)
            target_room = "第三阅览室北区"
            print(f"正在选择阅览室: {target_room}...")

            # 使用用户提供的 class="room-name"
            # 这里的 selector 查找 class 为 room-name 且包含目标文字的元素
            room_locator = page.locator(".room-name").filter(has_text=target_room).first

            try:
                # 等待元素出现
                room_locator.wait_for(state="visible", timeout=5000)
                room_locator.click()
                print(f"点击了 {target_room}")
            except Exception as e:
                print(f"点击阅览室失败: {e}")
                print("尝试模糊查找...")
                # 备用：尝试点击包含文字的 div
                page.locator(f"div:has-text('{target_room}')").last.click()

            page.wait_for_load_state("networkidle")
            time.sleep(3)  # 等待座位图加载

            # 3. 选择座位 (31号)
            seat_num = "031"  # 根据截图，文本是 031
            print(f"正在查找座位: {seat_num}...")

            page.screenshot(path="debug_seats.png")

            # 策略: 根据截图 class="seat-name" 内容为 031
            # 找到包含 seat_num 的 seat-name 元素
            seat_name_elem = page.locator(".seat-name").filter(has_text=seat_num).first

            try:
                seat_name_elem.wait_for(state="visible", timeout=5000)

                # 获取父级点击目标
                # 结构通常是: seat-desk -> seat-none -> seat-num + seat-name
                # 我们尝试点击 seat-none (或者最外层 seat-desk)
                seat_click_target = seat_name_elem.locator(
                    ".."
                )  # 第一次 .. 到 seat-none

                # 检查父级类名
                parent_class = seat_click_target.get_attribute("class")
                print(f"座位容器类名: {parent_class}")

                # 尝试点击
                print(f"尝试点击座位容器 {seat_num}")
                seat_click_target.click()
                print("点击动作已执行")

                # 检查是否选中 (比如类名是否变了)
                time.sleep(1)
                new_class = seat_click_target.get_attribute("class")
                # print(f"点击后类名: {new_class}")

            except Exception as e:
                print(f"定位/点击座位失败: {e}")
                # 备用方案
                print("尝试备用方案: 点击 .seat-name 自身")
                seat_name_elem.click()

            time.sleep(1)

            # 5. 检查是否有错误提示 (比如"没有可用时间")
            error_msg = (
                page.locator(".el-message__content")
                .filter(has_text="没有可用时间")
                .first
            )
            if error_msg.count() and error_msg.is_visible():
                print(f"❌ 预约失败: {error_msg.inner_text()}")
                # 可能是因为不在预约时间内 (7:00-22:00)
                page.screenshot(path="error_unavailable.png")
                return

            # 4. 提交 / 确认
            print("查找 '确认' 或 '提交' 按钮...")

            # 广撒网查找包含关键文本的可见元素
            potential_btns = (
                page.locator("div, span, button, a")
                .filter(has_text=re.compile(r"确认|提交|预约|Confirm|Book"))
                .all()
            )

            confirm_btn = None
            for btn in potential_btns:
                if btn.is_visible():
                    txt = btn.inner_text().strip()
                    # 排除掉无关文本 (比如标题里的 '座位预约系统')
                    if len(txt) < 10 and txt not in [
                        "座位预约系统",
                        "我的预约",
                        "预约规则",
                    ]:
                        # print(f"发现潜在按钮: '{txt}'")
                        confirm_btn = btn
                        break  # 找到第一个看似按钮的

            if confirm_btn:
                try:
                    btn_text = confirm_btn.inner_text()
                    print(f"尝试点击: {btn_text}")
                    confirm_btn.click()

                    # 等待可能的二次确认
                    time.sleep(1)
                    # 再次检查是否有“确定”弹窗
                    dialog_confirm = page.locator(
                        ".el-message-box__btns button--primary"
                    ).first
                    if dialog_confirm.count() and dialog_confirm.is_visible():
                        print("检测到弹窗确认按钮，点击...")
                        dialog_confirm.click()

                    # 检查最终结果
                    time.sleep(2)
                    success_msg = page.locator("text=预约成功")
                    if success_msg.count() and success_msg.is_visible():
                        print("✅ 预约成功！")
                    else:
                        print("流程结束，请检查截图确认结果。")

                    page.screenshot(path="result.png")
                except Exception as e:
                    print(f"点击提交按钮失败: {e}")
            else:
                print("未找到提交按钮 (可能因为不在预约时间或座位不可用)")
                page.screenshot(path="debug_confirm.png")

        except Exception as e:
            print(f"预约流程出错: {e}")
            page.screenshot(path="error_booking.png")

        print("脚本已暂停，请手动完成剩余步骤，或按 Ctrl+C 结束。")
        # 保持浏览器打开，方便调试
        # page.pause()
        print(f"当前页面URL: {page.url}")
        # 简单等待一下以便观察（在无头模式下可能不需要，但在开发时有用）
        time.sleep(2)
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username", nargs="?", help="Student ID")
    args = parser.parse_args()
    run(args.username)
