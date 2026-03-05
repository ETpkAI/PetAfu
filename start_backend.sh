#!/bin/bash
# 后端快速启动脚本
set -e

BACKEND_DIR="$(cd "$(dirname "$0")/backend" && pwd)"
cd "$BACKEND_DIR"

# 检查虚拟环境
if [ ! -d "venv" ]; then
  echo "⚙️  创建虚拟环境..."
  python3 -m venv venv
fi

# 激活
source venv/bin/activate

# 安装依赖
echo "📦 安装 Python 依赖..."
pip install -q -r requirements.txt

# 检查 .env
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "⚠️  已生成 .env 文件，请填写 OPENAI_API_KEY 后再启动！"
  echo "   编辑文件：$BACKEND_DIR/.env"
  exit 1
fi

echo "🚀 启动 FastAPI 服务..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
