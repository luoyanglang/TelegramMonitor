# Docker 部署

Docker 是最简单的部署方式，推荐使用。

## 前提条件

- 已安装 Docker
- 已准备好配置信息（[获取教程](../config/bot-token.md)）

## 快速部署

```bash
docker run -d \
  --name telegram-monitor \
  --restart unless-stopped \
  -v telegram-monitor-data:/app/data \
  -v telegram-monitor-sessions:/app/sessions \
  -e BOT_TOKEN=你的Token \
  -e TELEGRAM_API_ID=你的API_ID \
  -e TELEGRAM_API_HASH=你的API_Hash \
  -e AUTHORIZED_USER_ID=你的用户ID \
  luoyanglangge/telegram-monitor:latest
```

## 使用 docker-compose

创建 `docker-compose.yml` 文件：

```yaml
version: '3'
services:
  telegram-monitor:
    image: luoyanglangge/telegram-monitor:latest
    container_name: telegram-monitor
    restart: unless-stopped
    volumes:
      - ./data:/app/data
      - ./sessions:/app/sessions
    environment:
      - BOT_TOKEN=你的Token
      - TELEGRAM_API_ID=你的API_ID
      - TELEGRAM_API_HASH=你的API_Hash
      - AUTHORIZED_USER_ID=你的用户ID
```

启动：

```bash
docker-compose up -d
```

## 查看日志

```bash
docker logs -f telegram-monitor
```

## 常用命令

```bash
# 停止
docker stop telegram-monitor

# 启动
docker start telegram-monitor

# 重启
docker restart telegram-monitor

# 删除容器
docker rm -f telegram-monitor

# 更新镜像
docker pull luoyanglangge/telegram-monitor:latest
```

## 配置代理

如果需要代理，添加环境变量：

```bash
docker run -d \
  --name telegram-monitor \
  -e BOT_TOKEN=你的Token \
  -e TELEGRAM_API_ID=你的API_ID \
  -e TELEGRAM_API_HASH=你的API_Hash \
  -e AUTHORIZED_USER_ID=你的用户ID \
  -e PROXY_TYPE=socks5 \
  -e PROXY_HOST=host.docker.internal \
  -e PROXY_PORT=1080 \
  luoyanglangge/telegram-monitor:latest
```

> 注意：Docker 容器内访问宿主机代理，使用 `host.docker.internal` 而不是 `127.0.0.1`

---

[← 返回文档首页](../index.md)
