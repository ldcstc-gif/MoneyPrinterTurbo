#!/bin/bash
set -e
INSTALL_DIR="/opt/camera-ai"

echo "=== 安装 Camera AI ==="

# 复制文件
mkdir -p "$INSTALL_DIR"
cp -r "$(dirname "$0")"/* "$INSTALL_DIR/"

# 安装依赖
pip3 install -r "$INSTALL_DIR/requirements.txt" -q

# 创建 systemd 服务（开机自启）
cat > /etc/systemd/system/camera-ai.service << EOF
[Unit]
Description=Camera AI Upload Server
After=network.target

[Service]
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable camera-ai
systemctl start camera-ai

echo ""
echo "=== 安装完成 ==="
echo "服务状态: systemctl status camera-ai"
echo "查看日志: journalctl -u camera-ai -f"
echo "上传测试: curl -X POST http://localhost:9100/upload -H 'X-Token: change-me-please' -F 'file=@/path/to/test.jpg'"
