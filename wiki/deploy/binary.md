# 二进制部署

直接下载编译好的可执行文件运行，无需安装 Python 环境。

## 下载

前往 [Releases](https://github.com/luoyanglang/TelegramMonitor/releases) 页面下载对应系统的文件：

- **Linux**: `telegram-monitor-linux-x64.tar.gz`
- **Windows**: `telegram-monitor-windows-x64.zip`

## Linux 部署

### 1. 下载并解压

```bash
# 下载（替换为实际版本号）
wget https://github.com/luoyanglang/TelegramMonitor/releases/download/v2.0.0/telegram-monitor-linux-x64.tar.gz

# 解压
tar -xzf telegram-monitor-linux-x64.tar.gz
cd telegram-monitor
```

### 2. 配置环境变量

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置
nano .env
```

填写你的配置信息：

```env
BOT_TOKEN=你的Token
TELEGRAM_API_ID=你的API_ID
TELEGRAM_API_HASH=你的API_Hash
AUTHORIZED_USER_ID=你的用户ID
```

### 3. 运行

```bash
# 添加执行权限
chmod +x telegram-monitor-linux-x64

# 运行
./telegram-monitor-linux-x64
```

### 4. 后台运行（推荐）

使用 screen 或 nohup：

```bash
# 使用 screen
screen -S telegram-monitor
./telegram-monitor-linux-x64
# 按 Ctrl+A+D 退出 screen

# 或使用 nohup
nohup ./telegram-monitor-linux-x64 > monitor.log 2>&1 &
```

## Windows 部署

### 1. 下载并解压

下载 `telegram-monitor-windows-x64.zip` 并解压到任意目录。

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，用记事本编辑填写配置。

### 3. 运行

双击 `telegram-monitor-windows-x64.exe` 运行。

或在命令行中运行：

```cmd
telegram-monitor-windows-x64.exe
```

## 使用 systemd 管理（Linux）

创建服务文件 `/etc/systemd/system/telegram-monitor.service`：

```ini
[Unit]
Description=Telegram Monitor Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/telegram-monitor
ExecStart=/opt/telegram-monitor/telegram-monitor-linux-x64
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用并启动：

```bash
systemctl daemon-reload
systemctl enable telegram-monitor
systemctl start telegram-monitor

# 查看状态
systemctl status telegram-monitor

# 查看日志
journalctl -u telegram-monitor -f
```

---

[← 返回文档首页](../index.md)
