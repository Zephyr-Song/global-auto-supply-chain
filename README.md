# Global Auto Supply Chain Risk Analysis 🚗

> 西浦校外导师科研项目：全球汽车市场调研与跨国供应链风险研究

## 🌐 在线仪表盘

👉 **[点击访问在线仪表盘](https://zephyr-song-global-auto-supply-srcvisualizationdashboard-ptrx7z.streamlit.app/)**

> 推送代码到 `main` 分支后自动部署，1-2分钟生效。

## 项目概述

基于大模型的全球汽车市场调研与供应链风险分析系统，覆盖 **13个目标国家**（巴西、墨西哥、俄罗斯、智利、哈萨克斯坦、巴基斯坦、秘鲁、泰国、印尼、土耳其、沙特、马来西亚、南非），实现数据采集→风险评估→可视化交互的全链路闭环。

## 数据来源（全部为公开真实数据）

| 来源 | 覆盖国家 | 数据类型 |
|------|----------|----------|
| OICA 2025全球报告 | 13国 | 宏观产量/销量 |
| ANFAVEA 巴西汽车制造商协会 | 巴西 | 月度产销/品牌份额 |
| AMIA/INEGI 墨西哥汽车工业协会 | 墨西哥 | 月度产销 |
| AUTOSTAT/AEB 俄罗斯汽车统计局 | 俄罗斯 | 年度产销/品牌份额 |
| ANAC Chile 智利汽车协会 | 智利 | 月度销量/品牌 |
| 哈萨克斯坦工业和建设部 | 哈萨克斯坦 | 官方产量数据 |
| PAMA 巴基斯坦汽车制造商协会 | 巴基斯坦 | 月度销量 |
| ARAPER 秘鲁汽车协会 | 秘鲁 | 年度销量估算 |
| FTI 泰国工业联合会 | 泰国 | 月度产销/品牌份额 |
| Gaikindo 印尼汽车工业协会 | 印尼 | 月度产销/品牌份额 |
| ODD/OSD 土耳其汽车经销商与制造商协会 | 土耳其 | 月度产销/品牌份额 |
| 沙特工业发展基金 | 沙特 | CKD组装数据 |
| MAA 马来西亚汽车协会 | 马来西亚 | 月度产销/品牌份额 |
| NAAMSA 南非汽车制造商协会 | 南非 | 月度产销/品牌份额 |
| 乘联分会/中汽协 | 中国→13国 | 出口数据 |
| 芝能汽车/崔东树 | 13国 | 品牌份额/行业分析 |

## 关键数据（2025年）

| 指标 | 数值 |
|------|------|
| 13国总产量 | ~1,263万辆 |
| 13国新车销量 | ~1,105万辆 |
| 中国出口目标国 | ~276万辆（墨62.3万+俄57.9万+阿联酋42.8万+沙特34.5万+巴32.1万+土25.6万+哈21.1万） |
| 综合风险最高 | 俄罗斯（0.82） |
| 综合风险最低 | 马来西亚（0.27） |
| EV渗透率最高 | 泰国22.2% |
| 中国品牌份额最高 | 俄罗斯进口市场近80% |
| 进口依赖度最高 | 智利/秘鲁100% |
| 关税壁垒最高 | 巴基斯坦45-75% / 泰国/印尼/土耳其40% |
| 二手车/新车比率最高 | 巴基斯坦5.78x |

## 快速启动

### 1. 交互式仪表盘（Streamlit）

```bash
pip install streamlit plotly pandas
streamlit run src/visualization/dashboard.py
```

浏览器打开 `http://localhost:8501`

### 2. 静态HTML仪表盘

直接打开 `docs/dashboard.html`（Plotly CDN加载，无需安装）

### 3. 原始数据

```bash
python src/analysis/market_data.py
# 输出: data/processed/global_auto_market_data.json
```

## 仪表盘功能

### Tab 1: 📊 市场概览
- 📊 **产量趋势图** — 11国2020-2025产量对比（智利/秘鲁无本土制造，沙特仅有CKD）
- 📈 **销量趋势图** — 13国新车+二手车双面板
- 📋 **国家概览表** — 13国产量/销量/EV/风险/数据质量一览

### Tab 2: 🏷️ 品牌与EV
- 🏷️ **品牌市场份额** — 13国环形图，标注中国品牌位置
- 🔋 **电动车渗透率** — 条形图排序对比（泰国22.2%领先）

### Tab 3: ⚠️ 供应链风险
- ⚠️ **供应链风险雷达** — 5维度对比（地缘/供应/价格/物流/监管）
- 🔥 **风险热力图** — 矩阵视图，颜色映射风险等级
- 📋 **供应链风险详情** — 各国关键风险项展开

### Tab 4: 🇨🇳 中国出口
- 🇨🇳 **中国出口目标国** — 7个有数据的目标国出口量
- 📋 **中国出口数据表** — 目标国出口量+占比

### Tab 5: 🇨🇳 中国品牌出海
- 📈 **中国品牌市场份额增长趋势** — 13国2020-2025年中国品牌份额变化（俄罗斯58.7%领跑）
- 🔋 **电动车渗透率增长趋势** — 13国2020-2025年EV渗透率年度变化

### Tab 6: 📉 贸易壁垒与进口
- 🛡️ **各国贸易壁垒对比** — 进口关税/本地化率/EV激励政策对比
- 🌐 **各国汽车进口依赖度** — 低/中/高三档颜色区分

### Tab 7: 📊 市场深度
- 🔄 **二手车/新车市场比率** — 13国二手市场规模对比（巴基斯坦5.78x最高）

## 项目结构

```
global-auto-supply-chain/
├── src/
│   ├── analysis/
│   │   ├── market_data.py          # 真实数据采集+处理模块（13国，7大维度）
│   │   ├── market_trend.py         # 市场趋势分析（价格/品牌/异常检测）
│   │   └── supply_chain_risk.py    # 供应链风险评估（LLM+规则双引擎）
│   ├── visualization/
│   │   ├── dashboard.py            # Streamlit交互式仪表盘（7个Tab，12个图表）
│   │   └── __init__.py
│   ├── crawler/
│   │   ├── base.py                # 爬虫基类（Scrapling框架）
│   │   ├── scrapling_crawler.py   # Scrapling爬虫（4站点：mobile.de/OLX/sahibinden/otomoto）
│   │   ├── apify_crawler.py       # Apify云爬虫备选方案
│   │   └── __init__.py
│   └── llm/
│       └── client.py              # 大模型统一客户端（OpenAI/Claude/本地）
├── data/
│   └ processed/
│   │   └ global_auto_market_data.json
├── docs/
│   ├── dashboard.html              # 静态可视化备份
│   ├── dashboard_13countries.png   # 13国仪表盘截图
│   ├── 有免费的爬虫服务可以来做吗.docx
│   └── 能帮忙看一下 mobile.de 网站是否有反扒机制.docx
├── scripts/
│   └── run_crawlers.py            # 一键爬虫运行脚本
├── README.md
└── requirements.txt
```

## 爬虫使用指南

### 环境要求
- **海外网络环境**（VPN或海外服务器），国内网络无法访问大部分目标站点
- Python 3.10+

### 安装
```bash
pip install scrapling[all]          # 核心爬虫框架
patchright install                  # 下载浏览器驱动（首次运行）
pip install apify-client            # Apify备选（可选）
```

### 运行
```bash
# 检查环境
python scripts/run_crawlers.py --check

# 列出支持站点
python scripts/run_crawlers.py --list

# 爬取 mobile.de
python scripts/run_crawlers.py --site mobile.de --query "BYD" --pages 2

# 爬取 OLX 巴西
python scripts/run_crawlers.py --site olx_br --query "Chery" --pages 1

# 使用 Apify（需设置 APIFY_TOKEN 环境变量）
python scripts/run_crawlers.py --apify --site mobile.de --query "VW Golf"

# 一键全量爬取
python scripts/run_crawlers.py --all
```

### 支持的站点
| 站点 | 国家 | 反爬级别 | 推荐策略 |
|------|------|----------|----------|
| mobile.de | 德国 | Akamai | StealthyFetcher / Apify |
| olx.com.br | 巴西 | Cloudflare | StealthyFetcher |
| sahibinden.com | 土耳其 | Cloudflare | Fetcher+StealthyFetcher |
| otomoto.pl | 波兰 | Cloudflare | StealthyFetcher |

## 技术挑战

- **mobile.de反爬**：Akamai级别防护，StealthyFetcher可绕过（需海外环境），Apify作为备选
- **数据采集**：Statista/CEIC等付费源不可用，已转向各国协会公开数据
- **俄罗斯数据**：受制裁影响，部分数据需估算推算
- **沙特数据**：无本土制造，仅CKD组装，大部分数据依赖行业报告估算
- **国内网络限制**：浏览器级爬取海外站点需VPN，否则超时/被拦截

## 协作机制

每3天同步一次（项目会议纪要约定）

---

GitHub: https://github.com/Zephyr-Song/global-auto-supply-chain
