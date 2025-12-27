#!/bin/bash

# 获取脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "🚀 Starting NotebookLM Watermark Remover..."

# 检查虚拟环境是否存在
if [ -d "venv" ]; then
    echo "✅ Virtual environment found."
else
    echo "⚠️ Virtual environment not found. Creating one..."
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi

# 启动 Streamlit 应用
./venv/bin/streamlit run app.py
