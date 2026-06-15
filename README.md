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

- 📊 **产量趋势图** — 11国2020-2025产量对比（智利/秘鲁无本土制造，沙特仅有CKD）
- 📈 **销量趋势图** — 13国新车+二手车双面板
- 🏷️ **品牌市场份额** — 13国环形图，标注中国品牌位置
- 🔋 **电动车渗透率** — 条形图排序对比（泰国22.2%领先）
- 🇨🇳 **中国出口目标国** — 7个有数据的目标国出口量
- ⚠️ **供应链风险雷达** — 5维度对比（地缘/供应/价格/物流/监管）
- 🔥 **风险热力图** — 矩阵视图，颜色映射风险等级
- 📋 **国家概览表** — 13国产量/销量/EV/风险/数据质量一览
- 📋 **供应链风险详情** — 各国关键风险项展开
- 📋 **中国出口数据表** — 目标国出口量+占比

## 项目结构

```
global-auto-supply-chain/
├── src/
│   ├── analysis/
│   │   └── market_data.py          # 真实数据采集+处理模块（13国）
│   ├── visualization/
│   │   ├── dashboard.py            # Streamlit交互式仪表盘（13国）
│   │   └── __init__.py
│   └── crawler/                    # mobile.de爬虫（Apify方案待实施）
├── data/
│   └ processed/
│   │   └ global_auto_market_data.json
├── docs/
│   ├── dashboard.html              # 静态可视化备份
│   ├── dashboard_13countries.png   # 13国仪表盘截图
│   ├── 有免费的爬虫服务可以来做吗.docx
│   └── 能帮忙看一下 mobile.de 网站是否有反扒机制.docx
├── README.md
└── requirements.txt
```

## 技术挑战

- **mobile.de反爬**：Akamai级别防护（动态住宅IP+浏览器指纹），建议Apify/Decodo或半自动化插件
- **数据采集**：Statista/CEIC等付费源不可用，已转向各国协会公开数据
- **俄罗斯数据**：受制裁影响，部分数据需估算推算
- **沙特数据**：无本土制造，仅CKD组装，大部分数据依赖行业报告估算

## 协作机制

每3天同步一次（项目会议纪要约定）

---

GitHub: https://github.com/Zephyr-Song/global-auto-supply-chain
