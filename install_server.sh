#!/bin/bash
set -e

echo "============================================"
echo "  MoneyPrinterTurbo 服务器安装脚本"
echo "============================================"
echo ""

PROJECT_DIR="/opt/MoneyPrinterTurbo"

# 1. 安装系统依赖
echo "[1/6] 安装系统依赖..."
apt-get update -y
apt-get install -y git python3.11 python3.11-venv python3-pip imagemagick ffmpeg curl

# 修复 ImageMagick 安全策略
if [ -f /etc/ImageMagick-6/policy.xml ]; then
    sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' /etc/ImageMagick-6/policy.xml
fi

# 2. 克隆项目
echo "[2/6] 克隆项目代码..."
if [ -d "$PROJECT_DIR" ]; then
    echo "项目目录已存在，拉取最新代码..."
    cd "$PROJECT_DIR"
    git pull origin main || true
else
    git clone https://github.com/harry0703/MoneyPrinterTurbo.git "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# 3. 创建虚拟环境并安装依赖
echo "[3/6] 创建 Python 虚拟环境并安装依赖..."
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. 创建配置文件
echo "[4/6] 创建配置文件..."
if [ ! -f config.toml ]; then
    cp config.example.toml config.toml
    echo "已创建 config.toml，请稍后编辑配置 API Key 等信息"
else
    echo "config.toml 已存在，跳过"
fi

# 5. 创建 systemd 服务（WebUI）
echo "[5/6] 创建 systemd 服务..."

cat > /etc/systemd/system/moneyprinter-webui.service << 'EOF'
[Unit]
Description=MoneyPrinterTurbo WebUI
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/MoneyPrinterTurbo
Environment=PYTHONPATH=/opt/MoneyPrinterTurbo
ExecStart=/opt/MoneyPrinterTurbo/.venv/bin/streamlit run ./webui/Main.py --server.port=8501 --server.address=0.0.0.0 --browser.gatherUsageStats=False
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/moneyprinter-api.service << 'EOF'
[Unit]
Description=MoneyPrinterTurbo API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/MoneyPrinterTurbo
Environment=PYTHONPATH=/opt/MoneyPrinterTurbo
ExecStart=/opt/MoneyPrinterTurbo/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 6. 启动服务
echo "[6/6] 启动服务..."
systemctl daemon-reload
systemctl enable moneyprinter-webui moneyprinter-api
systemctl start moneyprinter-webui moneyprinter-api

echo ""
echo "============================================"
echo "  安装完成！"
echo "============================================"
echo ""
echo "  WebUI 地址: http://$(hostname -I | awk '{print $1}'):8501"
echo "  API 文档:   http://$(hostname -I | awk '{print $1}'):8080/docs"
echo ""
echo "  管理命令:"
echo "    查看状态:  systemctl status moneyprinter-webui"
echo "    重启WebUI: systemctl restart moneyprinter-webui"
echo "    重启API:   systemctl restart moneyprinter-api"
echo "    查看日志:  journalctl -u moneyprinter-webui -f"
echo ""
echo "  重要: 请编辑 /opt/MoneyPrinterTurbo/config.toml"
echo "  配置 pexels_api_keys 和 LLM 提供商的 API Key"
echo "============================================"
