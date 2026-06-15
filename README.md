# Global Auto Supply Chain Risk Analysis 🚗

> 西浦校外导师科研项目：全球汽车市场调研与跨国供应链风险研究

## 项目概述

基于大模型的全球汽车市场调研与供应链风险分析系统，覆盖 **7个目标国家**（巴西、墨西哥、俄罗斯、智利、哈萨克斯坦、巴基斯坦、秘鲁），实现数据采集→风险评估→可视化交互的全链路闭环。

## 数据来源（全部为公开真实数据）

| 来源 | 覆盖国家 | 数据类型 |
|------|----------|----------|
| OICA 2025全球报告 | 7国 | 宏观产量/销量 |
| ANFAVEA 巴西汽车制造商协会 | 巴西 | 月度产销/品牌份额 |
| AMIA/INEGI 墨西哥汽车工业协会 | 墨西哥 | 月度产销 |
| AUTOSTAT/AEB 俄罗斯汽车统计局 | 俄罗斯 | 年度产销/品牌份额 |
| ANAC Chile 智利汽车协会 | 智利 | 月度销量/品牌 |
| 哈萨克斯坦工业和建设部 | 哈萨克斯坦 | 官方产量数据 |
| PAMA 巴基斯坦汽车制造商协会 | 巴基斯坦 | 月度销量 |
| ARAPER 秘鲁汽车协会 | 秘鲁 | 年度销量估算 |
| 乘联分会/中汽协 | 中国→7国 | 出口数据 |
| 芝能汽车/崔东树 | 7国 | 品牌份额/行业分析 |

## 关键数据（2025年）

| 指标 | 数值 |
|------|------|
| 7国总产量 | ~713万辆 |
| 7国新车销量 | ~617万辆 |
| 中国出口7国 | ~173万辆（墨62.3万+俄57.9万+巴32.1万+哈21.1万） |
| 综合风险最高 | 俄罗斯（0.82） |
| 综合风险最低 | 智利（0.32） |
| EV渗透率最高 | 智利7.2% |
| 中国品牌份额最高 | 俄罗斯进口市场近80% |

## 快速启动

### 1. 交互式仪表盘（Streamlit）

```bash
pip install streamlit plotly pandas
streamlit run src/visualization/dashboard.py
```

浏览器打开 `http://localhost:8501`

### 2. 静态HTML仪表盘

直接打开 `docs/dashboard.html`（69KB，Plotly CDN加载，无需安装）

### 3. 原始数据

```bash
python src/analysis/market_data.py
# 输出: data/processed/global_auto_market_data.json
```

## 仪表盘功能

- 📊 **产量趋势图** — 5国2020-2025产量对比（智利/秘鲁无本土制造）
- 📈 **销量趋势图** — 7国新车+二手车双面板
- 🏷️ **品牌市场份额** — 7国环形图，标注中国品牌位置
- 🔋 **电动车渗透率** — 条形图排序对比
- 🇨🇳 **中国出口目标国** — TOP4出口量（总出口832万辆）
- ⚠️ **供应链风险雷达** — 5维度对比（地缘/供应/价格/物流/监管）
- 🔥 **风险热力图** — 矩阵视图，颜色映射风险等级

## 项目结构

```
global-auto-supply-chain/
├── src/
│   ├── analysis/
│   │   └── market_data.py          # 真实数据采集+处理模块
│   ├── visualization/
│   │   └── dashboard.py            # Streamlit交互式仪表盘
│   │   └── __init__.py
│   └── crawler/                    # mobile.de爬虫（Apify方案待实施）
├── data/
│   └ processed/
│   │   └ global_auto_market_data.json
├── docs/
│   └ dashboard.html               # 静态可视化备份
├── README.md
```

## 技术挑战

- **mobile.de反爬**：Akamai级别防护（动态住宅IP+浏览器指纹），建议Apify/Decodo或半自动化插件
- **数据采集**：Statista/CEIC等付费源不可用，已转向各国协会公开数据
- **俄罗斯数据**：受制裁影响，部分数据需估算推算

## 协作机制

每3天同步一次（项目会议纪要约定）

---

GitHub: https://github.com/Zephyr-Song/global-auto-supply-chain