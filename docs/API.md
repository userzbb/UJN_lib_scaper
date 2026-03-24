# UJN 图书馆座位预约系统 API 文档

> 基于 JS 逆向工程获取，2024-03-24

## JS 逆向工程

### 原始文件

JS 文件位于 `data/` 目录：

```
data/
├── app.js      # 应用主逻辑 (26KB)
└── vendor.js   # 第三方库 (2MB)
```

### 逆向方法

1. **获取 JS 文件**：通过浏览器开发者工具 Network 面板捕获
2. **关键词搜索**：在 JS 文件中搜索 `freeBook`、`book`、`checkIn` 等关键词
3. **函数追踪**：找到 API 调用函数，分析参数构造方式

### 关键代码片段

**预约 API 定义**（来自 `app.js`）：

```javascript
t.h=function(e,t){return r.a.fetchPost(o+"/rest/v2/freeBook?token="+t,e)}
```

含义：`t.h(e, t)` 接收两个参数：
- `e`：预约数据对象（包含 date, seatId, start, end）
- `t`：登录 token

**座位时间查询**：

```javascript
t.w=function(e){return r.a.fetchGet(o+"/rest/v2/startTimesForSeat/"+e.seatId+"/"+e.date,{params:e})}
t.k=function(e){return r.a.fetchGet(o+"/rest/v2/endTimesForSeat/"+e.id+"/"+e.date+"/"+e.start,{params:e})}
```

### 验证消息文本

从 JS 中提取的 UI 文本：

```javascript
order:{
  time:"预约时间",
  no:"当前没有预约记录！",
  date:"预约日期",
  startTime:"预约开始时间",
  endTime:"预约结束时间",
  seat:"预约座位",
  none:"暂无记录",
  current:"立即预约",
  success:"预约成功！"
}
```

---

## 基础信息

| 项目 | 值 |
|------|-----|
| Base URL | `https://seat.ujn.edu.cn` |
| 认证方式 | HMAC-SHA256 + Token |
| HMAC Secret | `ujnLIB2022tsg` |

---

## 认证方式

### 1. HMAC 请求头 (所有API都需要)

| Header | 说明 | 示例 |
|--------|------|------|
| `x-request-id` | UUID v4 | `b718255d-98a1-4119-8b9b-4e8bc32f2e2c` |
| `x-request-date` | 时间戳(毫秒) | `1711254300000` |
| `x-hmac-request-key` | HMAC-SHA256签名 | `3a0dd81a951b6f9171dd4856da9dc754...` |
| `logintype` | 固定值 | `PC` |

**签名字符串格式:**
```
seat::<UUID>::<Timestamp>::<Method>
```

**签名计算 (Python):**
```python
import hmac
import hashlib
import time
import uuid

HMAC_SECRET = "ujnLIB2022tsg"

def generate_headers(method="GET"):
    req_id = str(uuid.uuid4())
    req_date = str(int(time.time() * 1000))
    message = f"seat::{req_id}::{req_date}::{method}"
    
    signature = hmac.new(
        bytes(HMAC_SECRET, "utf-8"),
        msg=bytes(message, "utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    
    return {
        "x-request-id": req_id,
        "x-request-date": req_date,
        "x-hmac-request-key": signature,
        "logintype": "PC",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
```

### 2. AES 加密 (登录API需要)

用于加密用户名和密码。

```python
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64

AES_KEY = "server_date_time"
AES_IV = "client_date_time"

def encrypt_aes(text):
    key = AES_KEY.encode("utf-8")
    iv = AES_IV.encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(text.encode("utf-8"), AES.block_size)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode("utf-8") + "_encrypt"
```

### 3. Token (登录后获取)

登录成功后会返回 `token`，后续API调用需要附带在URL或Header中。

---

## API 端点详解

---

### 1. 登录认证

#### POST /rest/auth

**Python 调用:**
```python
import requests
from booking.crypto import generate_headers, encrypt_aes

BASE_URL = "https://seat.ujn.edu.cn"

sess = requests.Session()

headers = generate_headers("GET")
headers['username'] = encrypt_aes("202331223125")  # 学号
headers['password'] = encrypt_aes("080518")        # 密码

resp = sess.get(
    f"{BASE_URL}/rest/auth",
    headers=headers,
    params={'captchaId': 'xxx', 'answer': 'yyy'},
    timeout=10
)

# 响应: {"status":"success","data":{"token":"xxx"},"code":"0"}
token = resp.json()['data']['token']
```

---

### 2. 获取阅览室列表

#### GET /rest/v2/free/filters

**Python 调用:**
```python
def api_get(path, params=None):
    headers = generate_headers("GET")
    headers['token'] = token
    resp = sess.get(BASE_URL + path, headers=headers, params=params, timeout=10)
    return resp.json()

# 获取阅览室
result = api_get("/rest/v2/free/filters")

# 响应格式
{
  "status": "success",
  "data": {
    "buildings": [[1, "东校区", 5], [2, "西校区", 8]],
    "rooms": [
      [8, "第五阅览室北区", 2, 6],
      [17, "第三阅览室北区", 2, 4],
      ...
    ]
  }
}
# rooms格式: [roomId, roomName, buildingId, floor]
```

---

### 3. 获取座位布局

#### GET /rest/v2/room/layoutByDate/{roomId}/{date}

**Python 调用:**
```python
result = api_get(f"/rest/v2/room/layoutByDate/17/2024-03-26")

# 响应
{
  "status": "success",
  "data": {
    "id": 17,
    "name": "第三阅览室北区",
    "cols": 38,
    "rows": 13,
    "layout": {
      "3002": {
        "id": 8735,
        "name": "148",
        "type": "seat",
        "status": "FREE",
        "window": false,
        "power": false,
        ...
      },
      ...
    }
  }
}
```

---

### 4. 获取可预约时间

#### GET /rest/v2/startTimesForSeat/{seatId}/{date}

**Python 调用:**
```python
result = api_get(f"/rest/v2/startTimesForSeat/8768/2026-03-24")

# 响应
{
  "status": "success",
  "data": {
    "startTimes": [
      {"id": "now", "value": "现在"},
      {"id": "660", "value": "11:00"},
      {"id": "960", "value": "16:00"},
      ...
    ]
  }
}
```

#### GET /rest/v2/endTimesForSeat/{seatId}/{date}/{startTime}

```python
result = api_get(f"/rest/v2/endTimesForSeat/8768/2026-03-24/960")

# 响应
{
  "status": "success",
  "data": {
    "endTimes": [
      {"id": "990", "value": "16:30"},
      {"id": "1020", "value": "17:00"},
      ...
    ]
  }
}
```

---

### 5. 预约座位

#### POST /rest/v2/freeBook?token={token}

**⚠️ 注意**: 预约功能需要通过浏览器 UI 完成，因为提交时会触发点击式验证码。

**参数说明:**
| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `date` | string | 日期 | "2024-03-26" |
| `seat` | string | 座位ID | "1234" |
| `start` | string | 开始时间(分钟) | "420" (07:00) |
| `end` | string | 结束时间(分钟) | "720" (12:00) |

**时间分钟对照表:**
| 时间 | 分钟 | 时间 | 分钟 |
|------|------|------|------|
| 07:00 | 420 | 14:00 | 840 |
| 08:00 | 480 | 15:00 | 900 |
| 09:00 | 540 | 16:00 | 960 |
| 10:00 | 600 | 17:00 | 1020 |
| 11:00 | 660 | 18:00 | 1080 |
| 12:00 | 720 | 19:00 | 1140 |
| 13:00 | 780 | 20:00 | 1200 |

---

### 6. 签到

#### GET /rest/v2/checkIn/{id}

**Python 调用:**
```python
result = api_get(f"/rest/v2/checkIn/1234567")

# 成功响应
{
  "status": "success",
  "message": ""
}
```

---

### 7. 获取我的预约

#### GET /rest/v2/user/reservations

**Python 调用:**
```python
result = api_get("/rest/v2/user/reservations")

# 响应
{
  "status": "success",
  "data": [
    {
      "id": 1234567,
      "receipt": "2001-702-7",
      "onDate": "2024-03-26",
      "seatId": 1234,
      "status": "RESERVE",
      "location": "第三阅览室北区，座位号001",
      "begin": "07:00",
      "end": "12:00",
      "checkedIn": false,
      "message": "请在 03月26日06:15 至 07:15 之间前往场馆签到"
    }
  ]
}
```

---

### 8. 取消预约

#### GET /rest/v2/cancel/{id}

```python
result = api_get(f"/rest/v2/cancel/1234567")

# 响应
{
  "status": "success",
  "message": ""
}
```

---

## 签到规则

- 可提前 **45分钟** 内签到
- 超过预约开始时间 **15分钟** 未签到，自动取消预约
- 预约成功后会有 `message` 提示签到时间范围

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| `0` | 成功 |
| `1` | 失败(通用) |
| `12` | 登录失败(用户名密码错误) |
| `40` | 页面不存在(API路径错误) |

---

## 预约验证码说明

预约提交时会触发**点击式验证码**（点选汉字），这是防止自动化预约的安全机制。

流程：
1. 选择座位和时间 → 点击"立即预约"
2. 弹出验证码图片，要求点击指定汉字
3. 验证通过后才会真正提交预约请求

因此**纯API调用无法完成预约**，必须通过浏览器UI交互。
