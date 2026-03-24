# UJN 图书馆预约签到工具

> 基于纯协议层实现的自动化工具，绕过浏览器直接调用API。

## 功能状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 登录认证 | ✅ 可用 | 自动识别验证码 |
| 查看阅览室 | ✅ 可用 | `--rooms` |
| 查看预约列表 | ✅ 可用 | `--list` |
| 取消预约 | ✅ 可用 | `--cancel <ID>` |
| 签到 | ✅ 可用 | `--checkin <ID>` |
| 预约座位 | ⚠️ 受限 | 需要通过点击验证码验证 |

## 安装依赖

```bash
uv sync
uv run playwright install chromium  # 仅首次需要
```

## 快速开始

### 1. 查看可用账号

账号信息存储在 `found_passwords.csv` 中：

```bash
cat found_passwords.csv
```

### 2. 查看阅览室列表

```bash
uv run python booking/main.py <学号> --rooms
```

示例输出：
```
阅览室:
ID     名称                   校区
----------------------------------------
8      第五阅览室北区              西校区
17     第三阅览室北区              西校区
19     第三阅览室南区              西校区
...
```

### 3. 查看我的预约

```bash
uv run python booking/main.py <学号> --list
```

示例输出：
```
预约:
ID           位置                        日期           时间           状态
---------------------------------------------------------------------------
19971660     西校区7层701室区第七阅览室南区，座位号27   2026-03-24   16:30-22:00  ⏳
```

### 4. 取消预约

```bash
uv run python booking/main.py <学号> --cancel <预约ID>
```

### 5. 签到

```bash
uv run python booking/main.py <学号> --checkin <预约ID>
```

### 6. 预约座位（需浏览器验证）

```bash
uv run python booking/main.py <学号> --room 17 --seat 001 --date tomorrow
```

## 配置文件

编辑 `booking/config.json`：

```json
{
    "room_id": 17,
    "room_name": "第三阅览室北区",
    "seat_num": "001",
    "start_time": "09:00",
    "end_time": "12:00",
    "auto_checkin": false
}
```

| 配置项 | 说明 |
|--------|------|
| room_id | 阅览室ID（`--rooms` 查看） |
| room_name | 阅览室名称（仅显示用） |
| seat_num | 座位号 |
| start_time | 开始时间（需半小时对齐） |
| end_time | 结束时间 |
| auto_checkin | 预约成功后自动签到 |

## 使用示例

### 查看阅览室

```bash
uv run python booking/main.py 202331223125 --rooms
```

### 查看预约

```bash
uv run python booking/main.py 202331223125 --list
```

### 取消预约

```bash
uv run python booking/main.py 202331223125 --cancel 19971660
```

### 签到

```bash
uv run python booking/main.py 202331223125 --checkin 19971660
```

### 预约座位（默认明日）

```bash
uv run python booking/main.py 202331223125 --room 17 --seat 001
```

### 预约今日

```bash
uv run python booking/main.py 202331223125 --room 17 --seat 001 --date today
```

### 指定时间段

```bash
uv run python booking/main.py 202331223125 --room 17 --seat 001 --start 09:30 --end 12:00
```

### 预约成功后自动签到

```bash
uv run python booking/main.py 202331223125 --room 17 --seat 001 --auto
```

## 预约限制

- 只能预约**今日**或**明日**
- 时间需**半小时对齐**（如 09:00, 09:30, 10:00）
- 每人同时只能有**一个有效预约**
- 签到需在预约开始时间 **45分钟内** 完成

## 关于预约API

预约功能（`--book`）在提交时会触发**点击式验证码**，需要：

1. 在浏览器中选择座位和时间
2. 点击"立即预约"按钮
3. 通过验证码验证（点击图片中的指定汉字）
4. 才能完成预约

**直接API调用无法绕过此验证码**，因此booking功能需要浏览器辅助。

### 当前可用的API

基于逆向分析，已确认可用的API端点：

```
POST /rest/auth                    - 登录认证
GET  /rest/v2/free/filters        - 获取阅览室列表
GET  /rest/v2/room/layoutByDate/{roomId}/{date}  - 获取座位布局
GET  /rest/v2/startTimesForSeat/{seatId}/{date} - 获取可选开始时间
GET  /rest/v2/endTimesForSeat/{seatId}/{date}/{start} - 获取可选结束时间
GET  /rest/v2/user/reservations   - 获取我的预约
GET  /rest/v2/checkIn/{id}        - 签到
GET  /rest/v2/cancel/{id}         - 取消预约
POST /rest/v2/freeBook            - 预约座位（需验证码）
```

## 错误处理

### 登录失败

- 验证码识别错误 → 自动重试
- 用户名/密码错误 → 检查 `found_passwords.csv`

### 预约失败

- "参数错误" → 通常是验证码未通过
- "已有预约" → 需先取消已有预约
- "座位已被预约" → 选择其他座位
