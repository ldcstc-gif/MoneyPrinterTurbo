#!/bin/bash
set -e

echo "============================================"
echo "  MoneyPrinterTurbo 一键部署脚本"
echo "============================================"
echo ""

PROJECT_DIR="/opt/MoneyPrinterTurbo"
REPO_URL="https://github.com/harry0703/MoneyPrinterTurbo.git"

install_docker() {
    if command -v docker &> /dev/null; then
        echo "[✓] Docker 已安装: $(docker --version)"
        return
    fi
    echo "[*] 正在安装 Docker..."
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
    systemctl start docker
    systemctl enable docker
    echo "[✓] Docker 安装完成"
}

install_docker_compose() {
    if docker compose version &> /dev/null; then
        echo "[✓] Docker Compose 已安装: $(docker compose version)"
        return
    fi
    echo "[*] 正在安装 Docker Compose 插件..."
    apt-get update -qq && apt-get install -y -qq docker-compose-plugin
    echo "[✓] Docker Compose 安装完成"
}

clone_or_update_repo() {
    if [ -d "$PROJECT_DIR" ]; then
        echo "[*] 项目目录已存在，正在更新..."
        cd "$PROJECT_DIR"
        git pull origin main
    else
        echo "[*] 正在克隆项目..."
        git clone "$REPO_URL" "$PROJECT_DIR"
        cd "$PROJECT_DIR"
    fi
    echo "[✓] 项目代码已就绪"
}

setup_config() {
    if [ -f "$PROJECT_DIR/config.toml" ]; then
        echo "[✓] config.toml 已存在，跳过创建（如需修改请手动编辑）"
        return
    fi
    echo "[*] 正在创建配置文件..."
    cp "$PROJECT_DIR/config.example.toml" "$PROJECT_DIR/config.toml"
    echo "[✓] config.toml 已创建，请稍后根据需要编辑配置"
}

setup_storage() {
    mkdir -p "$PROJECT_DIR/storage"
    echo "[✓] 存储目录已就绪"
}

open_firewall_ports() {
    echo "[*] 正在配置防火墙端口..."
    if command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=8501/tcp 2>/dev/null || true
        firewall-cmd --permanent --add-port=8080/tcp 2>/dev/null || true
        firewall-cmd --reload 2>/dev/null || true
        echo "[✓] firewalld 端口已开放"
    elif command -v ufw &> /dev/null; then
        ufw allow 8501/tcp 2>/dev/null || true
        ufw allow 8080/tcp 2>/dev/null || true
        echo "[✓] ufw 端口已开放"
    else
        echo "[!] 未检测到防火墙工具，请手动确保 8501 和 8080 端口已开放"
        echo "[!] 同时请在云服务器控制台的安全组中放行这两个端口"
    fi
}

build_and_start() {
    cd "$PROJECT_DIR"
    echo "[*] 正在构建并启动 Docker 容器（首次构建可能需要几分钟）..."
    docker compose up -d --build
    echo "[✓] 容器启动完成"
}

show_status() {
    echo ""
    echo "============================================"
    echo "  部署完成！"
    echo "============================================"
    echo ""

    SERVER_IP=$(hostname -I | awk '{print $1}')

    echo "  Web 界面:  http://${SERVER_IP}:8501"
    echo "  API 接口:  http://${SERVER_IP}:8080/docs"
    echo ""
    echo "  项目目录:  ${PROJECT_DIR}"
    echo "  配置文件:  ${PROJECT_DIR}/config.toml"
    echo ""
    echo "  常用命令:"
    echo "    查看日志:    cd ${PROJECT_DIR} && docker compose logs -f"
    echo "    重启服务:    cd ${PROJECT_DIR} && docker compose restart"
    echo "    停止服务:    cd ${PROJECT_DIR} && docker compose down"
    echo "    更新部署:    cd ${PROJECT_DIR} && git pull && docker compose up -d --build"
    echo ""
    echo "  重要提示:"
    echo "    1. 请编辑 ${PROJECT_DIR}/config.toml 配置你的 API Key"
    echo "    2. 请确保阿里云安全组已放行 8501 和 8080 端口"
    echo ""

    docker compose ps
}

echo ""
install_docker
install_docker_compose
clone_or_update_repo
setup_config
setup_storage
open_firewall_ports
build_and_start
show_status
