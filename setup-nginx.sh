#!/bin/bash
set -e

DOMAIN="dixiaoer.top"
PROJECT_DIR="/opt/MoneyPrinterTurbo"

echo "============================================"
echo "  配置 Nginx 反向代理: ${DOMAIN}"
echo "============================================"

# Install Nginx
if ! command -v nginx &> /dev/null; then
    echo "[*] 正在安装 Nginx..."
    apt-get update -qq && apt-get install -y -qq nginx
fi
echo "[✓] Nginx 已安装"

# Copy config
echo "[*] 正在配置 Nginx..."
cp "${PROJECT_DIR}/nginx.conf" "/etc/nginx/sites-available/${DOMAIN}"
ln -sf "/etc/nginx/sites-available/${DOMAIN}" "/etc/nginx/sites-enabled/${DOMAIN}"

# Remove default site if it exists
rm -f /etc/nginx/sites-enabled/default

# Test and reload
nginx -t
systemctl reload nginx
systemctl enable nginx

echo "[✓] Nginx 配置完成"

# Update MoneyPrinterTurbo config endpoint
if [ -f "${PROJECT_DIR}/config.toml" ]; then
    sed -i "s|^endpoint = \"\"$|endpoint = \"http://${DOMAIN}\"|" "${PROJECT_DIR}/config.toml"
    echo "[✓] config.toml endpoint 已更新为 http://${DOMAIN}"
fi

# Open port 80
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp 2>/dev/null || true
    ufw allow 443/tcp 2>/dev/null || true
fi

echo ""
echo "============================================"
echo "  Nginx 配置完成！"
echo "============================================"
echo ""
echo "  现在可以通过以下地址访问:"
echo "    Web 界面:  http://${DOMAIN}"
echo "    API 文档:  http://${DOMAIN}/api/docs"
echo ""
echo "  如需 HTTPS，运行:"
echo "    apt install certbot python3-certbot-nginx"
echo "    certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
echo ""
