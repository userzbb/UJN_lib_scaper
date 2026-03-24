import sys
import base64
import json
import requests
import ddddocr

sys.path.insert(0, ".")
from booking.crypto import generate_headers, encrypt_aes
from booking.api import (
    BASE_URL,
    LOGIN_API,
    CAPTCHA_API,
    BOOKING_API,
    CHECKIN_API,
    CANCEL_API,
    RESERVATIONS_API,
    FILTERS_API,
    ROOM_LAYOUT_API,
    START_TIMES_API,
    END_TIMES_API,
)

ocr = ddddocr.DdddOcr(show_ad=False, old=True)


def time_to_minutes(t):
    h, m = map(int, t.split(":"))
    return h * 60 + m


class LibraryClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = None
        self.session = requests.Session()

    def solve_captcha(self):
        resp = self.session.get(CAPTCHA_API, timeout=10)
        data = resp.json()
        captcha_id = data.get("captchaId")
        img_b64 = data.get("captchaImage", "").split(",")[-1]
        code = ocr.classification(base64.b64decode(img_b64))
        return captcha_id, code if isinstance(code, str) else code.get("text", "")

    def login(self):
        captcha_id, code = self.solve_captcha()
        headers = generate_headers("GET")
        headers["username"] = encrypt_aes(self.username)
        headers["password"] = encrypt_aes(self.password)

        resp = self.session.get(
            LOGIN_API,
            headers=headers,
            params={"captchaId": captcha_id, "answer": code},
            timeout=10,
        )
        result = resp.json()

        if result.get("status") == "success":
            self.token = result.get("data", {}).get("token", "")
            return True, self.token
        return False, result.get("message", "登录失败")

    def api_get(self, url, params=None):
        headers = generate_headers("GET")
        if self.token:
            headers["token"] = self.token
        resp = self.session.get(url, headers=headers, params=params, timeout=10)
        return resp.json()

    def api_post(self, url, data):
        headers = generate_headers("POST")
        headers["Content-Type"] = "application/json"
        if self.token:
            headers["token"] = self.token
        resp = self.session.post(
            url + "?token=" + self.token, headers=headers, json=data, timeout=10
        )
        return resp.json()

    def get_filters(self):
        return self.api_get(FILTERS_API)

    def get_room_layout(self, room_id, date):
        return self.api_get(f"{ROOM_LAYOUT_API}/{room_id}/{date}/")

    def get_start_times(self, seat_id, date):
        return self.api_get(f"{START_TIMES_API}/{seat_id}/{date}")

    def get_end_times(self, seat_id, date, start_time):
        return self.api_get(f"{END_TIMES_API}/{seat_id}/{date}/{start_time}")

    def get_reservations(self):
        return self.api_get(RESERVATIONS_API)

    def book_seat(self, date, seat_id, start_min, end_min):
        return self.api_post(
            BOOKING_API,
            {
                "date": date,
                "seat": str(seat_id),
                "start": str(start_min),
                "end": str(end_min),
            },
        )

    def check_in(self, reservation_id):
        return self.api_get(f"{CHECKIN_API}/{reservation_id}")

    def cancel(self, reservation_id):
        return self.api_get(f"{CANCEL_API}/{reservation_id}")

    def get_free_seats(self, room_id, date):
        result = self.get_room_layout(room_id, date)
        if result.get("status") != "success":
            return []

        free_seats = []
        layout = result.get("data", {}).get("layout", {})
        for key, info in layout.items():
            if info.get("type") == "seat" and info.get("status") == "FREE":
                free_seats.append(
                    {
                        "id": info.get("id"),
                        "name": info.get("name"),
                        "type": info.get("type"),
                        "status": info.get("status"),
                    }
                )
        return free_seats
