#!/bin/bash
set -e

echo "======================================"
echo "  MoneyPrinterTurbo 一键部署脚本"
echo "======================================"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ======== 1. 检查系统 ========
log "检查系统环境..."
if [ "$(id -u)" != "0" ]; then
  error "请使用 root 用户运行此脚本"
fi

# ======== 2. 安装 Docker ========
if ! command -v docker &> /dev/null; then
  log "安装 Docker..."
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg lsb-release
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable docker
  systemctl start docker
  log "Docker 安装完成"
else
  log "Docker 已安装: $(docker --version)"
fi

# ======== 3. 检查 docker compose ========
if docker compose version &> /dev/null; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
  COMPOSE_CMD="docker-compose"
else
  log "安装 docker-compose..."
  curl -SL "https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-linux-x86_64" \
    -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  COMPOSE_CMD="docker-compose"
fi
log "使用: $COMPOSE_CMD"

# ======== 4. 下载项目 ========
INSTALL_DIR="/opt/MoneyPrinterTurbo"

if [ -d "$INSTALL_DIR" ]; then
  warn "目录已存在: $INSTALL_DIR，跳过克隆"
else
  log "下载项目代码..."
  if command -v git &> /dev/null; then
    git clone https://github.com/harry0703/MoneyPrinterTurbo.git "$INSTALL_DIR"
  else
    apt-get install -y git
    git clone https://github.com/harry0703/MoneyPrinterTurbo.git "$INSTALL_DIR"
  fi
fi

cd "$INSTALL_DIR"
log "项目目录: $INSTALL_DIR"

# ======== 5. 写入配置文件 ========
log "生成配置文件 config.toml..."
cat > config.toml << 'TOML_EOF'
[app]
video_source = "pexels"
hide_config = false

pexels_api_keys = ["Gov4RNHgJR8gcbQ8qI6r0rEvHGiWz3UbdsOpGZu876svBDqJHo4qbR1q"]
pixabay_api_keys = []

llm_provider = "deepseek"

pollinations_api_key = ""
pollinations_base_url = "https://pollinations.ai/api/v1"
pollinations_model_name = "openai-fast"

ollama_base_url = ""
ollama_model_name = ""

openai_api_key = ""
openai_base_url = ""
openai_model_name = "gpt-4o-mini"

moonshot_api_key = ""
moonshot_base_url = "https://api.moonshot.cn/v1"
moonshot_model_name = "moonshot-v1-8k"

oneapi_api_key = ""
oneapi_base_url = ""
oneapi_model_name = ""

g4f_model_name = "gpt-3.5-turbo"

azure_api_key = ""
azure_base_url = ""
azure_model_name = "gpt-35-turbo"
azure_api_version = "2024-02-15-preview"

gemini_api_key = ""
gemini_model_name = "gemini-2.5-flash"

qwen_api_key = ""
qwen_model_name = "qwen-max"

minimax_api_key = ""
minimax_base_url = "https://api.minimax.io/v1"
minimax_model_name = "MiniMax-M2.7"

deepseek_api_key = "sk-9ad749616f2a4272bdc8f9e10236390d"
deepseek_base_url = "https://api.deepseek.com"
deepseek_model_name = "deepseek-chat"

modelscope_api_key = ""
modelscope_base_url = "https://api-inference.modelscope.cn/v1/"
modelscope_model_name = "Qwen/Qwen3-32B"

litellm_model_name = "openai/gpt-4o-mini"

subtitle_provider = "edge"

endpoint = ""
material_directory = ""

enable_redis = false
redis_host = "localhost"
redis_port = 6379
redis_db = 0
redis_password = ""

max_concurrent_tasks = 5

[whisper]
model_size = "large-v3"
device = "CPU"
compute_type = "int8"

[proxy]

[azure]
speech_key = ""
speech_region = ""

[siliconflow]
api_key = ""

[ui]
hide_log = false
upload_post_enabled = false
upload_post_api_key = ""
upload_post_username = ""
upload_post_platforms = ["tiktok", "instagram"]
upload_post_auto_upload = false
TOML_EOF

log "配置文件写入完成"

# ======== 6. 开放防火墙端口 ========
log "配置防火墙..."
if command -v ufw &> /dev/null; then
  ufw allow 8501/tcp comment "MoneyPrinter WebUI" 2>/dev/null || true
  ufw allow 8080/tcp comment "MoneyPrinter API" 2>/dev/null || true
  log "ufw 端口已开放: 8501, 8080"
fi
if command -v iptables &> /dev/null; then
  iptables -I INPUT -p tcp --dport 8501 -j ACCEPT 2>/dev/null || true
  iptables -I INPUT -p tcp --dport 8080 -j ACCEPT 2>/dev/null || true
fi

# ======== 7. 启动服务 ========
log "拉取 Docker 镜像并启动服务（首次可能需要 5-10 分钟）..."
$COMPOSE_CMD pull
$COMPOSE_CMD up -d

# ======== 8. 检查状态 ========
sleep 5
log "检查容器状态..."
$COMPOSE_CMD ps

echo ""
echo "======================================"
echo -e "${GREEN}  部署完成！${NC}"
echo "======================================"
echo ""
echo "  访问地址："
SERVER_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo "  WebUI:   http://${SERVER_IP}:8501"
echo "  API 文档: http://${SERVER_IP}:8080/docs"
echo ""
echo "  管理命令："
echo "  查看日志: cd $INSTALL_DIR && $COMPOSE_CMD logs -f"
echo "  停止服务: cd $INSTALL_DIR && $COMPOSE_CMD down"
echo "  重启服务: cd $INSTALL_DIR && $COMPOSE_CMD restart"
echo "======================================"
