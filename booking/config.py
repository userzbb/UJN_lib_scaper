# ================= Configuration =================
HMAC_SECRET = "ujnLIB2022tsg"
AES_KEY = "server_date_time"
AES_IV = "client_date_time"

BASE_URL = "https://seat.ujn.edu.cn"
LOGIN_API = f"{BASE_URL}/rest/auth"
CAPTCHA_API = f"{BASE_URL}/auth/createCaptcha"

BOOKING_API = f"{BASE_URL}/rest/v2/freeBook"
CHECKIN_API = f"{BASE_URL}/rest/v2/checkIn"
CANCEL_API = f"{BASE_URL}/rest/v2/cancel"
RESERVATIONS_API = f"{BASE_URL}/rest/v2/user/reservations"
FILTERS_API = f"{BASE_URL}/rest/v2/free/filters"
ROOM_LAYOUT_API = f"{BASE_URL}/rest/v2/room/layoutByDate"
START_TIMES_API = f"{BASE_URL}/rest/v2/startTimesForSeat"
END_TIMES_API = f"{BASE_URL}/rest/v2/endTimesForSeat"
ROOM_STATS_API = f"{BASE_URL}/rest/v2/room/stats2"
