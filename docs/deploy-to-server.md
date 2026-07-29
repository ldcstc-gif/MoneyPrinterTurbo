# 部署 MoneyPrinterTurbo 到服务器（120.77.251.48）

本文档给出在服务器上通过 Docker 部署 MoneyPrinterTurbo 的步骤，供在具备实际网络出口权限的环境（本地终端 / 本地 Claude Code）中执行。

> 安全提示：root 密码曾在聊天记录中以明文出现，建议部署完成后立即通过 `passwd` 修改，
> 并尽快改用 SSH 密钥登录、禁用密码登录（`PasswordAuthentication no`）。

## 1. 连接服务器

```shell
ssh root@120.77.251.48
```

## 2. 安装 Docker（如未安装）

```shell
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
docker compose version   # 确认 compose 插件可用
```

## 3. 拉取代码

```shell
cd /opt
git clone https://github.com/ldcstc-gif/moneyprinterturbo.git MoneyPrinterTurbo
cd MoneyPrinterTurbo
git checkout claude/server-connection-credentials-7e4xk6   # 如需部署本分支
```

## 4. 配置

```shell
cp config.example.toml config.toml
vi config.toml   # 填入所需的 API Key（LLM、TTS 等）
```

## 5. 启动服务

```shell
docker compose up -d
```

- WebUI: http://120.77.251.48:8501
- API: http://120.77.251.48:8080/docs

## 6. 开放端口

确认服务器安全组 / 防火墙放行 8501、8080：

```shell
ufw allow 8501/tcp
ufw allow 8080/tcp
```

## 7. 验证

```shell
docker compose ps
docker compose logs -f --tail=100
curl -I http://127.0.0.1:8080/docs
```
