# 部署 MoneyPrinterTurbo 到服务器（120.77.251.48）

本文档给出在服务器上通过 Docker 部署 MoneyPrinterTurbo 的步骤，供在具备实际网络出口权限的环境（本地终端 / 本地 Claude Code）中执行。

> 安全提示：root 密码曾在聊天记录中以明文出现，建议部署完成后立即通过 `passwd` 修改，
> 并尽快改用 SSH 密钥登录、禁用密码登录（`PasswordAuthentication no`）。

## 0. 域名

`dixiaoer.top` 已解析到 `120.77.251.48`，用于反向代理 WebUI（见第 8 步）。

## 1. 连接服务器

```shell
ssh root@120.77.251.48
```

### 配置 SSH 公钥登录（推荐，替代密码登录）

在服务器上执行，将本地生成的公钥写入 `authorized_keys`：

```shell
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cat >> ~/.ssh/authorized_keys <<'EOF'
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCwYlGj1LA3jjjX8Tubu/ZjLN49FAqVg/kJ3MzKzVuCqa7UHNM62MmUdNgSgmK/LoICqwlDpMWeggHK+MrvWsxnRqlixXBaqcw0DQKDWs5+rHDLpuoxANXGLsGPahuz+sGnAzRdyWLlm2ZE+IS3k89x/lO0BYQ72dZqMhLFH63T0/Ey9JqrOcgzQjUAtNcz1v9j62Vz7WCr0DMfOYLvAGkDoE5YvUHDgNmgFgCfFdBcWbo6rWSsTXS8KIzW8PrfVbS2xup2qVNG6YAyayDKa/uv9Xs6HWrxPc/GZY9U0Kffsy2Im2EgwHWI6t5S8mACEQsQ/ErxyI9qNkRgASU/8tDX skp-wz93smjogwnmnmnaqpzr
EOF
chmod 600 ~/.ssh/authorized_keys
```

确认可以用密钥登录后，再执行 `passwd` 修改密码，并考虑在 `/etc/ssh/sshd_config` 中设置
`PasswordAuthentication no` 后 `systemctl restart sshd`。

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

## 8. 配置域名与 HTTPS（dixiaoer.top → WebUI 8501）

### ① 安装 Nginx 与 Certbot

```shell
apt-get update
apt-get install -y nginx certbot python3-certbot-nginx
```

### ② 配置反向代理

创建 `/etc/nginx/sites-available/dixiaoer.top`：

```nginx
server {
    listen 80;
    server_name dixiaoer.top;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

启用站点：

```shell
ln -s /etc/nginx/sites-available/dixiaoer.top /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
ufw allow 80/tcp
ufw allow 443/tcp
```

### ③ 申请 HTTPS 证书

```shell
certbot --nginx -d dixiaoer.top --redirect -m <your-email> --agree-tos --non-interactive
```

Certbot 会自动改写 Nginx 配置以启用 443/HTTPS，并配置证书自动续期（`certbot renew` 的定时任务默认已安装）。

### ④ 验证

```shell
curl -I https://dixiaoer.top
```

浏览器访问 https://dixiaoer.top 应看到 MoneyPrinterTurbo WebUI。
