"""Streamlit Cloud 入口文件 — 转发到实际 dashboard"""
import sys
import os

# 确保项目 src 目录在 Python 路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# 直接导入并运行 dashboard
from visualization.dashboard import run

if __name__ == "__main__":
    run()
