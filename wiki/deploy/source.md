# 源码部署

适合开发者或需要自定义修改的用户。

## 前提条件

- Python 3.10+
- Git
- pip

## 部署步骤

### 1. 克隆代码

```bash
git clone https://github.com/luoyanglang/TelegramMonitor.git
cd TelegramMonitor
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写配置：

```env
BOT_TOKEN=你的Token
TELEGRAM_API_ID=你的API_ID
TELEGRAM_API_HASH=你的API_Hash
AUTHORIZED_USER_ID=你的用户ID
```

### 5. 运行

```bash
python main.py
```

## 后台运行

### 使用 screen

```bash
screen -S telegram-monitor
python main.py
# 按 Ctrl+A+D 退出
```

### 使用 systemd

创建 `/etc/systemd/system/telegram-monitor.service`：

```ini
[Unit]
Description=Telegram Monitor Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/TelegramMonitor
ExecStart=/opt/TelegramMonitor/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable telegram-monitor
systemctl start telegram-monitor
```

## 更新

```bash
git pull
pip install -r requirements.txt
# 重启服务
```

## 开发调试

```bash
# 安装开发依赖（如果有）
pip install -r requirements-dev.txt

# 运行测试
pytest
```

---

[← 返回文档首页](../index.md)
