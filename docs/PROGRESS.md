# 项目进度报告 (Project Progress)

**最后更新时间**: 2026-03-24

## 🟢 已完成功能 (Completed)

### 1. 极速 HTTP 爆破系统
- **`crack_login_http.py`**: 纯协议层爆破工具
  - 支持 64+ 线程并发
  - HMAC-SHA256 签名 + AES 加密
  - SQLite 断点续传

### 2. 图书馆预约签到工具
- **`booking/`**: 纯 Python 实现的核心功能

| 模块 | 文件 | 功能 |
|------|------|------|
| 加密 | `crypto.py` | HMAC签名、AES加密 |
| API | `api.py` | 端点常量 |
| 客户端 | `client.py` | LibraryClient 类 |
| 入口 | `main.py` | 命令行工具 |

**已实现功能**：
- ✅ 登录认证（自动验证码识别）
- ✅ 查看阅览室列表
- ✅ 查看我的预约
- ✅ 取消预约
- ❌ 签到（API不可用，需扫码或触屏机）

## 🟡 逆向工程成果

### JS 逆向
- **文件位置**: `data/app.js`, `data/vendor.js`
- **方法**: 浏览器 Network 抓包 + JS 关键词搜索

### 已破解的密钥

| 密钥 | 值 | 用途 |
|------|-----|------|
| HMAC Secret | `ujnLIB2022tsg` | 请求签名 |
| AES Key | `server_date_time` | 密码加密 |
| AES IV | `client_date_time` | 密码加密 |

### API 端点

```
POST /rest/auth                           # 登录
GET  /rest/v2/free/filters               # 阅览室列表
GET  /rest/v2/room/layoutByDate/{roomId}/{date}  # 座位布局
GET  /rest/v2/startTimesForSeat/{seatId}/{date}  # 可选开始时间
GET  /rest/v2/endTimesForSeat/{seatId}/{date}/{start}  # 可选结束时间
GET  /rest/v2/user/reservations           # 我的预约
GET  /rest/v2/checkIn/{id}               # 签到
GET  /rest/v2/cancel/{id}                 # 取消预约
POST /rest/v2/freeBook                     # 预约座位 ⚠️
```

## 🔴 当前阻塞点

### 预约 API 需要验证码

预约功能（`POST /rest/v2/freeBook`）在提交时会触发**点击式汉字验证码**：

1. 用户在浏览器选择座位和时间
2. 点击"立即预约"
3. 系统弹出验证码图片，要求点击指定汉字（如"块"、"山"等）
4. 验证通过后预约才真正提交

**影响**：纯 API 调用无法绕过此验证码，必须通过浏览器 UI 交互。

### 签到 API 完全不可用

经实际测试，签到 API 返回：
```
"请扫描小程序签到二维码或在触屏机上操作"
```

**这意味着无法通过任何自动化方式完成签到**，必须：
- 扫描图书馆小程序二维码
- 或在图书馆触屏机上手动操作

## 📋 待办

- [ ] 研究验证码绕过方案
- [ ] 评估第三方验证码识别服务（如 2Captcha）
- [ ] 完善文档

## 📁 项目结构

```
UJN_lib_scaper/
├── crack_login_http.py    # HTTP 爆破入口
├── booking/               # 预约签到模块
│   ├── main.py          # CLI 入口
│   ├── client.py         # API 客户端
│   ├── crypto.py        # 加密工具
│   ├── api.py           # 端点常量
│   └── config.py        # 配置
├── data/                 # 逆向 JS 文件
│   ├── app.js           # 应用主逻辑
│   └── vendor.js        # 第三方库
├── docs/                 # 文档
│   ├── API.md           # API 文档
│   ├── BOOKING.md        # 使用指南
│   └── ...
├── found_passwords.csv   # 爆破结果
└── crack.db             # 进度数据库
```
