# 🚗 全球汽车市场调研与跨国供应链风险研究

> 基于大模型的全球汽车市场数据调研与供应链风险分析系统

## 📋 项目简介

本项目是西浦校外导师科研项目，旨在利用大语言模型（LLM）能力，构建全球汽车市场数据调研与跨国供应链风险分析平台。核心方向包括：

- **全球汽车市场数据爬取与整合** — 覆盖欧洲（mobile.de等）、北美、亚太主流汽车交易平台
- **供应链风险分析与预警** — 基于大模型的智能风险评估与供应链中断预警
- **可视化交互展示** — 交互式数据仪表盘，支持多维度市场洞察
- **零碳电力投资系统** — 数据库升级与供应链碳排放追踪

## 🏗️ 项目结构

```
global-auto-supply-chain/
├── docs/                    # 项目文档
│   ├── meetings/            # 会议纪要
│   └── research/            # 调研报告
├── src/                     # 源代码
│   ├── crawler/             # 数据爬取模块
│   ├── analysis/            # 数据分析模块
│   ├── visualization/       # 可视化模块
│   └── llm/                 # 大模型集成模块
├── data/                    # 数据目录
│   ├── raw/                 # 原始数据
│   └── processed/           # 处理后数据
├── notebooks/               # Jupyter notebooks
├── config/                  # 配置文件
└── tests/                   # 测试代码
```

## 🔧 技术栈

| 类别 | 技术 |
|------|------|
| 爬虫 | Scrapy / Apify / Playwright |
| 数据处理 | Pandas / Polars |
| 大模型 | OpenAI API / Claude API / 本地部署 |
| 可视化 | Plotly / Streamlit / ECharts |
| 数据库 | PostgreSQL / MongoDB |
| 部署 | Docker / GitHub Actions |

## ⚠️ 已知挑战

### mobile.de 反爬机制
- mobile.de 部署了 **Akamai 级别** 的反爬虫防御
- 完全免费的全自动爬虫服务几乎不存在
- 建议方案：Apify 免费额度 / 半自动化浏览器插件 / 官方API

## 📅 里程碑

| 日期 | 里程碑 |
|------|--------|
| 2026-05-17 | 项目启动会，明确目标与分工 |
| 2026-06-15 | 正式启动开发 |
| 2026-06-13 | 进展同步会，讨论反爬突破方案 |
| TBD | Phase 1: 数据爬取管线搭建 |
| TBD | Phase 2: LLM分析模块开发 |
| TBD | Phase 3: 可视化与交互展示 |

## 👥 协作机制

- **同步频率**: 每3天一次进展同步
- **代码管理**: GitHub PR + Review
- **文档规范**: 所有决策写入 docs/meetings/

## 🚀 快速开始

```bash
# 克隆仓库
git clone https://github.com/Zephyr-Song/global-auto-supply-chain.git
cd global-auto-supply-chain

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp config/.env.example config/.env
# 编辑 config/.env 填入API密钥

# 运行爬虫（示例）
python -m src.crawler.mobile_de

# 启动可视化
streamlit run src/visualization/dashboard.py
```

## 📄 许可

本项目为学术研究用途。
