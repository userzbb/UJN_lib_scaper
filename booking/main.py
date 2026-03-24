#!/usr/bin/env python3
import sys
import json
import csv
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, ".")
from booking.client import LibraryClient, time_to_minutes


def load_config():
    try:
        with open("booking/config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def get_password_from_csv(username):
    try:
        with open("found_passwords.csv", "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row.get("username", "").strip() == username:
                    return row.get("password", "").strip()
    except:
        pass
    return None


def get_date(day_offset):
    return (datetime.now() + timedelta(days=day_offset)).strftime("%Y-%m-%d")


def check_existing_reservation(client, target_date, room_id, seat_num):
    result = client.get_reservations()
    if result.get("status") != "success":
        return None

    today = get_date(0)
    tomorrow = get_date(1)

    for r in result.get("data", []):
        status = r.get("status", "")
        on_date = r.get("onDate", "")
        checked = r.get("checkedIn", False)

        if status in ["RESERVE", "CHECK_IN"] and not checked:
            if on_date == today:
                if target_date == "today":
                    return f"今日已有预约: {r.get('location')} {r.get('begin')}-{r.get('end')} (ID: {r.get('id')})"
            elif on_date == tomorrow:
                return f"明日已有预约: {r.get('location')} {r.get('begin')}-{r.get('end')} (ID: {r.get('id')})"

    return None


def main():
    parser = argparse.ArgumentParser(description="UJN图书馆预约签到")
    parser.add_argument("username", help="学号")
    parser.add_argument("--room", type=int, help="阅览室ID")
    parser.add_argument("--seat", help="座位号")
    parser.add_argument(
        "--date",
        choices=["today", "tomorrow"],
        default="tomorrow",
        help="日期(默认明日)",
    )
    parser.add_argument("--start", help="开始时间 HH:MM")
    parser.add_argument("--end", help="结束时间 HH:MM")
    parser.add_argument("--list", action="store_true", help="查看预约")
    parser.add_argument("--rooms", action="store_true", help="查看阅览室")
    parser.add_argument("--checkin", type=int, help="签到(预约ID)")
    parser.add_argument("--cancel", type=int, help="取消预约(预约ID)")
    parser.add_argument("--auto", action="store_true", help="预约成功后自动签到")
    args = parser.parse_args()

    password = get_password_from_csv(args.username)
    if not password:
        print(
            f"错误: 未在学号列表中找到 {args.username}，或 found_passwords.csv 不存在"
        )
        sys.exit(1)

    config = load_config()
    client = LibraryClient(args.username, password)

    ok, msg = client.login()
    if not ok:
        print(f"登录失败: {msg}")
        sys.exit(1)
    print(f"✅ 登录成功")

    if args.rooms:
        result = client.get_filters()
        if result.get("status") == "success":
            print("\n阅览室:")
            print(f"{'ID':<6} {'名称':<20} {'校区'}")
            print("-" * 40)
            for room in result.get("data", {}).get("rooms", []):
                b = "东校区" if room[2] == 1 else "西校区" if room[2] == 2 else "其他"
                print(f"{room[0]:<6} {room[1]:<20} {b}")
        return

    if args.list:
        result = client.get_reservations()
        if result.get("status") == "success":
            print("\n预约:")
            print(f"{'ID':<12} {'位置':<25} {'日期':<12} {'时间':<12} {'状态'}")
            print("-" * 75)
            for r in result.get("data", []):
                loc = r.get("location", "")[:23]
                on_date = r.get("onDate", "")
                time_range = f"{r.get('begin')}-{r.get('end')}"
                status = r.get("status", "")
                checked = "✅" if r.get("checkedIn") else "⏳"
                print(
                    f"{r.get('id'):<12} {loc:<25} {on_date:<12} {time_range:<12} {checked}"
                )
        return

    if args.checkin:
        result = client.check_in(args.checkin)
        if result.get("status") == "success":
            print("✅ 签到成功!")
        else:
            print(f"❌ 签到失败: {result.get('message')}")
        return

    if args.cancel:
        result = client.cancel(args.cancel)
        if result.get("status") == "success":
            print(f"✅ 已取消预约 {args.cancel}")
        else:
            print(f"❌ 取消失败: {result.get('message')}")
        return

    room_id = args.room or config.get("room_id")
    seat_num = args.seat or config.get("seat_num")
    start_time = args.start or config.get("start_time", "09:00")
    end_time = args.end or config.get("end_time", "12:00")

    if not room_id:
        print("错误: 需要指定 --room 或在config.json中配置")
        sys.exit(1)

    date = get_date(0 if args.date == "today" else 1)

    existing = check_existing_reservation(client, args.date, room_id, seat_num)
    if existing:
        print(f"⚠️ {existing}")
        print(f"   请先 --cancel <ID> 取消后再预约")
        sys.exit(1)

    print(f"\n预约信息:")
    print(f"  账号: {args.username}")
    print(f"  阅览室: {room_id} ({config.get('room_name', '')})")
    print(f"  座位: {seat_num}")
    print(f"  日期: {date}")
    print(f"  时间: {start_time} - {end_time}")

    seat_id = None
    if seat_num:
        print(f"\n查找座位 {seat_num}...")
        result = client.get_room_layout(room_id, date)
        if result.get("status") == "success":
            for k, v in result.get("data", {}).get("layout", {}).items():
                if v.get("type") == "seat" and v.get("name") == seat_num:
                    if v.get("status") == "FREE":
                        seat_id = v.get("id")
                        print(f"  找到: ID={seat_id}")
                    else:
                        print(f"  座位状态: {v.get('status')} (已被预约)")

                        print(f"\n该座位已被预约，正在查询该阅览室空闲座位...")
                        free_seats = client.get_free_seats(room_id, date)

                        if not free_seats:
                            print("  该阅览室暂无空闲座位")
                            sys.exit(1)

                        print(f"\n可选座位 (共 {len(free_seats)} 个):")
                        for i, seat in enumerate(free_seats[:10], 1):
                            print(f"  {i}. 座位号: {seat['name']}")
                        print(f"  0. 退出")

                        while True:
                            try:
                                choice = input("\n请选择座位 (输入编号): ").strip()
                                if choice == "0":
                                    print("已退出")
                                    sys.exit(0)
                                idx = int(choice) - 1
                                if 0 <= idx < len(free_seats):
                                    seat_id = free_seats[idx]["id"]
                                    seat_num = free_seats[idx]["name"]
                                    print(f"  已选择: 座位号 {seat_num} (ID={seat_id})")
                                    break
                                else:
                                    print("  无效编号，请重新选择")
                            except ValueError:
                                print("  请输入有效编号")
                    break

    if not seat_id:
        print(f"错误: 找不到可用座位 {seat_num}")
        sys.exit(1)

    print(f"\n正在预约...")
    result = client.book_seat(
        date, seat_id, time_to_minutes(start_time), time_to_minutes(end_time)
    )

    if result.get("status") == "success":
        data = result.get("data", {})
        print(f"✅ 预约成功! ID: {data.get('id')}")
        print(f"   {data.get('location')}")
        print(f"   {data.get('begin')} - {data.get('end')}")

        if args.auto or config.get("auto_checkin"):
            print(f"\n自动签到...")
            checkin = client.check_in(data.get("id"))
            if checkin.get("status") == "success":
                print("✅ 签到成功!")
            else:
                print(f"❌ 签到失败: {checkin.get('message')}")
    else:
        print(f"❌ 预约失败: {result.get('message')}")


if __name__ == "__main__":
    main()
