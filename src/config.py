# ================= Configuration & Constants =================
HMAC_SECRET = "ujnLIB2022tsg"
AES_KEY = "server_date_time"
AES_IV = "client_date_time"
DB_FILE = "crack.db"
TEMP_DICT_FILE = "passwords.txt"

BASE_URL = "https://seat.ujn.edu.cn"
LOGIN_API = f"{BASE_URL}/rest/auth"
CAPTCHA_API = f"{BASE_URL}/auth/createCaptcha"
