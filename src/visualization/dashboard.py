"""
全球汽车供应链风险可视化仪表盘 — Streamlit 版本
================================================
运行: streamlit run src/visualization/dashboard.py
"""

import json
import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from analysis.market_data import get_all_data
from analysis.risk_scorer import CountryRiskScorer, CountryRiskMetrics
from analysis.market_kpi import MarketKPIEngine
from optimization.market_allocator import MarketAllocator, MarketCandidate
from analysis.automotive_bom import AutomotiveBOMAnalyzer, EntryMode
import importlib

# 初始化数据
data = get_all_data()

# 安全检查：确保新数据字段存在（排查 Streamlit Cloud 缓存问题）
_EXPECTED_KEYS = ["china_brand_share_trend", "ev_penetration_trend", "trade_barriers", "import_dependency", "used_new_car_ratio"]
_MISSING_KEYS = [k for k in _EXPECTED_KEYS if k not in data or not data[k]]
if _MISSING_KEYS:
    # 尝试重新加载模块
    import analysis.market_data as _md_mod
    importlib.reload(_md_mod)
    data = _md_mod.get_all_data()
    _STILL_MISSING = [k for k in _EXPECTED_KEYS if k not in data or not data[k]]
    if _STILL_MISSING:
        _RELOAD_STATUS = f"reload failed, still missing: {_STILL_MISSING}"
    else:
        _RELOAD_STATUS = "reload OK, all keys present"
else:
    _RELOAD_STATUS = "all keys present on first load"
PROD = data["production"]
SALES = data["sales"]
BRANDS = data["brand_market_share"]
RISK = data["supply_chain_risk"]
EV = data["ev_penetration"]
EXPORT = data["china_export"]
CHINA_BRAND_TREND = data.get("china_brand_share_trend", {})
EV_TREND = data.get("ev_penetration_trend", {})
TRADE_BARRIERS = data.get("trade_barriers", {})
IMPORT_DEP = data.get("import_dependency", {})
USED_NEW_RATIO = data.get("used_new_car_ratio", {})
SOURCE_URLS = data.get("source_urls", {})

# DEBUG: 显示数据加载状态（排查 Cloud 部署问题，稳定后删除）
_DATA_KEYS = list(data.keys())
_NEW_DATA_STATUS = {k: ("✅" if data.get(k) else "❌") for k in ["china_brand_share_trend", "ev_penetration_trend", "trade_barriers", "import_dependency", "used_new_car_ratio", "source_urls"]}

# 计算本地 market_data.py 的 hash 来确认 Cloud 用的是否是最新版
try:
    import hashlib
    _md_path = os.path.join(os.path.dirname(__file__), "..", "analysis", "market_data.py")
    with open(_md_path, "rb") as _f:
        _MD_HASH = hashlib.md5(_f.read()).hexdigest()[:8]
except Exception as _e:
    _MD_HASH = f"err: {_e}"

# 国家顺序（统一）— 从数据动态生成，确保只在所有数据集都存在的国家才展示
_ALL_COUNTRIES = [
    "Brazil", "Mexico", "Russia", "Chile", "Kazakhstan", "Pakistan", "Peru",
    "Thailand", "Indonesia", "Turkey", "SaudiArabia", "Malaysia", "SouthAfrica"
]
COUNTRIES = [c for c in _ALL_COUNTRIES
             if c in PROD and c in SALES and c in BRANDS and c in RISK and c in EV]

COUNTRY_CN = {c: PROD[c].get("country_cn", c) for c in COUNTRIES}

# 默认颜色池，超出时自动循环
_BASE_COLORS = [
    "#1f77b4", "#ff7f0e", "#d62728", "#2ca02c", "#9467bd", "#8c564b",
    "#e377c2", "#17becf", "#bcbd22", "#e74c3c", "#27ae60", "#3498db",
    "#f39c12",
]
COUNTRY_COLORS = {c: _BASE_COLORS[i % len(_BASE_COLORS)] for i, c in enumerate(COUNTRIES)}


def source_caption(sources):
    """生成数据来源标注（Streamlit markdown格式，无需unsafe_allow_html）"""
    links = []
    for s in sources:
        if isinstance(s, dict) and "url" in s:
            links.append('[{}]({})'.format(s["name"], s["url"]))
        elif isinstance(s, dict):
            links.append(s.get("name", str(s)))
        elif isinstance(s, str) and s in SOURCE_URLS:
            info = SOURCE_URLS[s]
            links.append('[{}]({})'.format(info["name"], info["url"]))
        else:
            links.append(str(s))
    return '数据来源：' + ' · '.join(links)


# ============================================================
# 图表构建函数
# ============================================================

def fig_production_trend(active=None):
    """产量趋势图"""
    active = active or COUNTRIES
    fig = go.Figure()
    no_production_countries = []
    for c in active:
        p = PROD[c]
        has_production = any(v > 0 for v in p["production"])
        if not has_production:
            no_production_countries.append(p['country_cn'])
            continue
        # 对数坐标下0无定义，用None替代0值让线断开
        y_vals = [v if v > 0 else None for v in p["production"]]
        fig.add_trace(go.Scatter(
            x=p["years"], y=y_vals,
            mode="lines+markers",
            name=f"{p['country_cn']} ({c})",
            line=dict(color=COUNTRY_COLORS[c], width=2.5),
            marker=dict(size=6),
            hovertemplate="%{y:,.0f} 辆",
        ))
    # 零产量国家信息存到 fig._no_production 以便外部使用
    fig._no_production = no_production_countries
    fig.update_layout(
        title=dict(text="📊 目标国汽车产量趋势 (2020-2025)", font=dict(size=18)),
        xaxis=dict(title="年份", dtick=1),
        yaxis=dict(title="产量 (辆)", tickformat=","),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.20),
        template="plotly_white",
        height=500,
    )
    return fig


def fig_sales_trend(active=None):
    """销量趋势图 — 新车+二手车"""
    active = active or COUNTRIES
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        subplot_titles=("新车销量", "二手车销量"),
        vertical_spacing=0.12
    )
    for c in active:
        s = SALES[c]
        fig.add_trace(go.Scatter(
            x=s["years"], y=s["new_car_sales"],
            mode="lines+markers",
            name=COUNTRY_CN[c],
            line=dict(color=COUNTRY_COLORS[c], width=2.5),
            marker=dict(size=5),
            hovertemplate="%{y:,.0f} 辆",
            showlegend=True
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=s["years"], y=s["used_car_sales"],
            mode="lines+markers",
            name=COUNTRY_CN[c],
            line=dict(color=COUNTRY_COLORS[c], width=2, dash="dot"),
            hovertemplate="%{y:,.0f} 辆",
            showlegend=False
        ), row=2, col=1)

    fig.update_layout(
        title=dict(text="📈 目标国新车/二手车销量 (2020-2025)", font=dict(size=18)),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.12),
        template="plotly_white",
        height=650,
    )
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(tickformat=",", row=1, col=1)
    fig.update_yaxes(tickformat=",", row=2, col=1)
    return fig


def fig_brand_share(active=None):
    """品牌市场份额（环形图）"""
    active = active or COUNTRIES
    n = len(active)
    n_cols = 5
    n_rows = (n + n_cols - 1) // n_cols  # ceil division
    specs = [[{"type": "domain"}] * n_cols for _ in range(n_rows)]
    subplot_titles = [COUNTRY_CN[c] for c in COUNTRIES]
    # 补齐空标题
    while len(subplot_titles) < n_rows * n_cols:
        subplot_titles.append("")

    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        specs=specs,
        subplot_titles=subplot_titles,
        vertical_spacing=0.06,
        horizontal_spacing=0.02,
    )

    for i, c in enumerate(active):
        r = (i // n_cols) + 1
        col = (i % n_cols) + 1
        b = BRANDS[c]
        fig.add_trace(go.Pie(
            labels=b["brands"],
            values=b["shares"],
            name=COUNTRY_CN[c],
            textinfo="label",
            textposition="inside",
            insidetextfont=dict(size=8),
            hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
            marker=dict(line=dict(color="white", width=1)),
        ), r, col)

    fig.update_layout(
        title=dict(text="🏷️ 各国品牌市场份额 (2025)", font=dict(size=18)),
        height=900,
        template="plotly_white",
        showlegend=False,
    )
    return fig


def fig_ev_penetration(active=None):
    """电动车渗透率 — 条形图"""
    active = active or COUNTRIES
    ev_filtered = {k: v for k, v in EV.items() if k in active}
    sorted_items = sorted(ev_filtered.items(), key=lambda x: x[1], reverse=True)
    countries = [k for k, _ in sorted_items]
    values = [v * 100 for _, v in sorted_items]
    colors = [COUNTRY_COLORS[c] for c in countries]

    fig = go.Figure(go.Bar(
        x=countries,
        y=values,
        marker_color=colors,
        text=[f"{v:.1f}%" for v in values],
        textposition="outside",
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="🔋 电动车渗透率 (2025)", font=dict(size=18)),
        xaxis=dict(title="国家"),
        yaxis=dict(title="渗透率 (%)", ticksuffix="%"),
        template="plotly_white",
        height=400,
    )
    return fig


def fig_china_brand_trend():
    """中国品牌市场份额增长趋势"""
    years = [2020, 2021, 2022, 2023, 2024, 2025]
    fig = go.Figure()
    for c, shares in CHINA_BRAND_TREND.items():
        cn_name = COUNTRY_CN.get(c, c)
        fig.add_trace(go.Scatter(
            x=years, y=shares,
            mode="lines+markers",
            name=f"{cn_name} ({c})",
            line=dict(color=COUNTRY_COLORS.get(c, "#95a5a6"), width=2.5),
            marker=dict(size=6),
            hovertemplate="%{y:.1f}%",
        ))
    fig.update_layout(
        title=dict(text="📈 中国品牌市场份额增长趋势 (2020-2025)", font=dict(size=18)),
        xaxis=dict(title="年份", dtick=1),
        yaxis=dict(title="市场份额 (%)", ticksuffix="%"),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.20),
        template="plotly_white",
        height=500,
    )
    return fig


def fig_ev_trend():
    """电动车渗透率增长趋势"""
    years = [2020, 2021, 2022, 2023, 2024, 2025]
    fig = go.Figure()
    for c, rates in EV_TREND.items():
        cn_name = COUNTRY_CN.get(c, c)
        fig.add_trace(go.Scatter(
            x=years, y=[r * 100 for r in rates],
            mode="lines+markers",
            name=f"{cn_name} ({c})",
            line=dict(color=COUNTRY_COLORS.get(c, "#95a5a6"), width=2.5),
            marker=dict(size=6),
            hovertemplate="%{y:.1f}%",
        ))
    fig.update_layout(
        title=dict(text="🔋 电动车渗透率增长趋势 (2020-2025)", font=dict(size=18)),
        xaxis=dict(title="年份", dtick=1),
        yaxis=dict(title="渗透率 (%)", ticksuffix="%"),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.20),
        template="plotly_white",
        height=500,
    )
    return fig


def fig_trade_barriers():
    """各国贸易壁垒对比"""
    if not TRADE_BARRIERS:
        return go.Figure()

    countries = list(TRADE_BARRIERS.keys())
    cn_names = [COUNTRY_CN.get(c, c) for c in countries]
    tariffs = [TRADE_BARRIERS[c]["import_tariff"] * 100 for c in countries]
    localization = [TRADE_BARRIERS[c]["localization_requirement"] * 100 for c in countries]
    ev_incentive_labels = ["✅" if TRADE_BARRIERS[c].get("ev_incentive") else "❌" for c in countries]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=cn_names,
        x=tariffs,
        orientation="h",
        name="进口关税 (%)",
        marker_color="#e74c3c",
        text=[f"{v:.0f}%" for v in tariffs],
        textposition="outside",
        hovertemplate="%{y}: 进口关税 %{x:.0f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=cn_names,
        x=localization,
        orientation="h",
        name="本地化率要求 (%)",
        marker_color="#3498db",
        text=[f"{v:.0f}%" for v in localization],
        textposition="outside",
        hovertemplate="%{y}: 本地化率要求 %{x:.0f}%<extra></extra>",
    ))
    # ev_incentive 标记用 annotation 方式标注在 y 轴标签旁
    fig.update_layout(
        title=dict(text="🛡️ 各国贸易壁垒对比", font=dict(size=18)),
        xaxis=dict(title="百分比 (%)", ticksuffix="%"),
        yaxis=dict(title="国家"),
        barmode="group",
        template="plotly_white",
        height=500,
        legend=dict(orientation="h", y=-0.15),
    )
    # 在图表上标注 ev_incentive
    for i, label in enumerate(ev_incentive_labels):
        fig.add_annotation(
            x=max(tariffs[i], localization[i]) + 2,
            y=cn_names[i],
            text=f"EV激励: {label}",
            showarrow=False,
            font=dict(size=10),
        )
    return fig


def fig_import_dependency():
    """各国汽车进口依赖度"""
    if not IMPORT_DEP:
        return go.Figure()

    sorted_items = sorted(IMPORT_DEP.items(), key=lambda x: x[1], reverse=True)
    countries = [k for k, _ in sorted_items]
    cn_names = [COUNTRY_CN.get(c, c) for c in countries]
    values = [v * 100 for _, v in sorted_items]

    colors = []
    for v in sorted_items:
        val = v[1]
        if val <= 0.3:
            colors.append("#27ae60")  # 绿色 - 低依赖
        elif val <= 0.6:
            colors.append("#f39c12")  # 黄色 - 中依赖
        else:
            colors.append("#e74c3c")  # 红色 - 高依赖

    fig = go.Figure(go.Bar(
        y=cn_names,
        x=values,
        orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}%" for v in values],
        textposition="outside",
        hovertemplate="%{y}: 进口依赖度 %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="🌐 各国汽车进口依赖度", font=dict(size=18)),
        xaxis=dict(title="进口依赖度 (%)", ticksuffix="%"),
        yaxis=dict(title="国家"),
        template="plotly_white",
        height=450,
    )
    return fig


def fig_used_new_ratio():
    """二手车/新车市场比率"""
    if not USED_NEW_RATIO:
        return go.Figure()

    sorted_items = sorted(USED_NEW_RATIO.items(), key=lambda x: x[1], reverse=True)
    countries = [k for k, _ in sorted_items]
    cn_names = [COUNTRY_CN.get(c, c) for c in countries]
    values = [v for _, v in sorted_items]
    colors = [COUNTRY_COLORS.get(c, "#95a5a6") for c in countries]

    fig = go.Figure(go.Bar(
        y=cn_names,
        x=values,
        orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}x" for v in values],
        textposition="outside",
        hovertemplate="%{y}: %{x:.1f}x<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="🔄 二手车/新车市场比率 (2025)", font=dict(size=18)),
        xaxis=dict(title="比率 (倍)"),
        yaxis=dict(title="国家"),
        template="plotly_white",
        height=450,
    )
    return fig


def fig_china_export(active=None):
    """中国出口到目标国 — 条形图（始终显示所有有数据的出口目标国，不受侧边栏筛选限制）"""
    meta_keys = {'total_china_export_2025', 'source'}
    export_data = [(k, v) for k, v in EXPORT.items() if isinstance(v, (int, float)) and k not in meta_keys]
    export_data.sort(key=lambda x: x[1], reverse=True)
    cn_names = {c: COUNTRY_CN[c] for c in COUNTRIES}
    cn_names["UAE"] = "阿联酋"
    countries = [cn_names.get(e[0], e[0]) for e in export_data]
    values = [e[1] for e in export_data]
    colors = [COUNTRY_COLORS.get(e[0], "#95a5a6") for e in export_data]

    fig = go.Figure(go.Bar(
        x=countries,
        y=values,
        marker_color=colors,
        text=[f"{v/10000:.1f}万辆" for v in values],
        textposition="outside",
        hovertemplate="%{x}<br>出口量: %{y:,.0f} 辆<extra></extra>",
    ))
    fig.update_layout(
        title=dict(
            text=f"🇨🇳 2025年中国汽车出口目标国 (总出口{EXPORT.get('total_china_export_2025', 8320000)/10000:.0f}万辆)",
            font=dict(size=16)
        ),
        xaxis=dict(title="目标国"),
        yaxis=dict(title="出口量 (辆)", tickformat=","),
        template="plotly_white",
        height=450,
    )
    return fig


def fig_supply_chain_radar(active=None):
    """供应链风险雷达图"""
    active = active or COUNTRIES
    risk_dims = ["geopolitical_risk", "supply_disruption", "price_volatility", "logistics_risk", "regulatory_risk"]
    dim_labels = ["地缘政治", "供应中断", "价格波动", "物流风险", "监管风险"]

    fig = go.Figure()
    for c in active:
        r = RISK[c]
        values = [r[d] for d in risk_dims]
        # 闭合
        values_closed = values + [values[0]]
        labels_closed = dim_labels + [dim_labels[0]]

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=labels_closed,
            name=COUNTRY_CN[c],
            fill="toself",
            opacity=0.25,
            line=dict(color=COUNTRY_COLORS[c], width=2),
            hovertemplate="%{theta}: %{r:.0%}<extra>%{legend}</extra>"
        ))

    fig.update_layout(
        title=dict(text="⚠️ 各国供应链风险雷达图", font=dict(size=18)),
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], tickformat="%"),
            angularaxis=dict(tickfont=dict(size=11)),
        ),
        template="plotly_white",
        height=550,
        legend=dict(orientation="h", y=-0.1),
    )
    return fig


def fig_risk_heatmap(active=None):
    """供应链风险热力图"""
    active = active or COUNTRIES
    risk_dims = ["geopolitical_risk", "supply_disruption", "price_volatility", "logistics_risk", "regulatory_risk"]
    dim_labels = ["地缘政治", "供应中断", "价格波动", "物流风险", "监管风险"]

    z_values = []
    for c in active:
        r = RISK[c]
        z_values.append([r[d] for d in risk_dims])

    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=dim_labels,
        y=[COUNTRY_CN[c] for c in active],
        colorscale="RdYlGn_r",
        texttemplate="%{z:.0%}",
        textfont=dict(size=11),
        hovertemplate="%{y}<br>%{x}: %{z:.0%}<extra></extra>",
        zmin=0,
        zmax=1,
    ))
    fig.update_layout(
        title=dict(text="🔥 供应链风险热力图 (0=低风险, 1=高风险)", font=dict(size=16)),
        xaxis=dict(title="风险维度"),
        yaxis=dict(title="国家"),
        template="plotly_white",
        height=400,
    )
    return fig


def table_country_overview(active=None):
    """国家概览表"""
    active = active or COUNTRIES
    rows = []
    for c in active:
        p = PROD[c]
        s = SALES[c]
        prod_latest = p["production"][-1]
        sales_latest = s["new_car_sales"][-1]
        prod_chg = (p["production"][-1] / p["production"][-2] - 1) * 100 if p["production"][-2] > 0 else 0
        sales_chg = (s["new_car_sales"][-1] / s["new_car_sales"][-2] - 1) * 100 if s["new_car_sales"][-2] > 0 else 0
        ev_rate = EV[c] * 100
        risk_dims = ["geopolitical_risk", "supply_disruption", "price_volatility", "logistics_risk", "regulatory_risk"]
        risk_avg = sum(RISK[c][d] for d in risk_dims) / len(risk_dims)

        rows.append({
            "国家": COUNTRY_CN[c],
            "2025产量": f"{prod_latest:,.0f}" if prod_latest > 0 else "无本土制造",
            "产量变动": f"{prod_chg:+.1f}%" if prod_latest > 0 else "—",
            "2025新车销量": f"{sales_latest:,.0f}",
            "销量变动": f"{sales_chg:+.1f}%",
            "EV渗透率": f"{ev_rate:.1f}%",
            "综合风险": f"{risk_avg:.0%}",
            "数据质量": p["data_quality"],
        })

    return pd.DataFrame(rows)


def table_supply_chain_risks(active=None):
    """供应链风险详情表"""
    active = active or COUNTRIES
    rows = []
    risk_dims = ["geopolitical_risk", "supply_disruption", "price_volatility", "logistics_risk", "regulatory_risk"]
    for c in active:
        r = RISK[c]
        for risk_text in r["key_risks"]:
            rows.append({
                "国家": COUNTRY_CN[c],
                "风险项": risk_text,
                "综合得分": f"{sum(r[d] for d in risk_dims) / len(risk_dims):.0%}",
            })

    return pd.DataFrame(rows)


def table_china_exports():
    """中国出口数据表"""
    meta_keys = {'total_china_export_2025', 'source'}
    export_data = [(k, v) for k, v in EXPORT.items() if isinstance(v, (int, float)) and k not in meta_keys]
    export_data.sort(key=lambda x: x[1], reverse=True)
    cn_names = {c: COUNTRY_CN[c] for c in COUNTRIES}
    cn_names["UAE"] = "阿联酋"

    total = sum(e[1] for e in export_data)
    rows = []
    for country, volume in export_data:
        rows.append({
            "目标国": cn_names.get(country, country),
            "出口量": f"{volume:,} 辆",
            "占比": f"{volume/total*100:.1f}%",
        })

    return pd.DataFrame(rows)


def summary_stats(active=None):
    """关键统计摘要"""
    active = active or COUNTRIES
    total_prod = sum(PROD[c]["production"][-1] for c in active if PROD[c]["production"][-1] > 0)
    total_sales = sum(SALES[c]["new_car_sales"][-1] for c in active)
    meta_keys = {'total_china_export_2025', 'source'}
    active_set = set(active)
    total_export = sum(v for k, v in EXPORT.items() if isinstance(v, (int, float)) and k not in meta_keys and k in active_set)

    prod_with_manu = [COUNTRY_CN[c] for c in active if PROD[c]["production"][-1] > 0]
    risk_dims = ["geopolitical_risk", "supply_disruption", "price_volatility", "logistics_risk", "regulatory_risk"]
    def avg_risk(c): return sum(RISK[c][d] for d in risk_dims) / len(risk_dims)
    max_risk_country = max(active, key=avg_risk)
    min_risk_country = min(active, key=avg_risk)

    return {
        "total_production": total_prod,
        "total_sales": total_sales,
        "total_china_export": total_export,
        "n_countries": len(active),
        "prod_countries": ", ".join(prod_with_manu),
        "max_risk": COUNTRY_CN[max_risk_country],
        "min_risk": COUNTRY_CN[min_risk_country],
    }


# ============================================================
# Streamlit 主应用
# ============================================================

def run():
    import streamlit as st

    st.set_page_config(
        page_title="全球汽车供应链风险看板",
        page_icon="🚗",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # CSS 样式
    st.markdown("""
    <style>
        .main-header { font-size: 2rem; font-weight: 700; margin-bottom: 0; }
        .sub-header { font-size: 1rem; color: #666; margin-bottom: 1.5rem; }
        .stat-card { 
            background: #f8f9fa; border-radius: 10px; padding: 1rem; 
            text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .stat-value { font-size: 1.8rem; font-weight: 700; }
        .stat-label { font-size: 0.85rem; color: #666; }
    </style>
    """, unsafe_allow_html=True)

    # ======== 侧边栏筛选（必须先于 stats 和卡片） ========
    with st.sidebar:
        st.markdown("## 🔍 数据筛选")
        selected_countries = st.multiselect(
            "选择目标国家",
            options=[f"{COUNTRY_CN[c]} ({c})" for c in COUNTRIES],
            default=[f"{COUNTRY_CN[c]} ({c})" for c in COUNTRIES],
        )

        show_raw_data = st.checkbox("显示原始数据表", value=False)

        st.divider()
        st.markdown("### 📚 数据来源")
        sources = data["data_sources"]
        for s in sources:
            if isinstance(s, dict) and "url" in s:
                st.markdown(f'- [{s["name"]}]({s["url"]})')
            elif isinstance(s, dict):
                st.markdown(f'- {s.get("name", s)}')
            else:
                st.markdown(f'- {s}')

        st.divider()
        st.markdown(f"🕐 最后更新: {data['last_updated'][:19]}")

    selected_country_codes = [s.split("(")[-1].rstrip(")") if "(" in s else s for s in selected_countries]

    # 计算筛选后的统计数据
    stats = summary_stats(selected_country_codes)

    # ======== 顶部标题 ========
    st.markdown('<p class="main-header">🚗 全球汽车市场供应链风险看板</p>', unsafe_allow_html=True)
    n_sel = len(selected_country_codes)
    st.markdown(
        f'<p class="sub-header">'
        f'当前筛选：{n_sel}个国家 ｜ '
        f'数据来源：OICA · ANFAVEA · AMIA · AEB · FTI · Gaikindo · ODD · NAAMSA · MAA · 乘联分会 ｜ '
        f'更新：2025年数据'
        f'</p>',
        unsafe_allow_html=True
    )

    # DEBUG: 数据加载诊断（稳定后删除）
    with st.expander("🔧 数据加载诊断", expanded=False):
        st.write(f"data keys ({len(_DATA_KEYS)}): {_DATA_KEYS}")
        st.json(_NEW_DATA_STATUS)
        st.write(f"market_data.py MD5: {_MD_HASH}")
        st.write(f"Python: {sys.version}")
        st.write(f"Reload status: {_RELOAD_STATUS}")

    # ======== 关键指标卡片 ========
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['total_production']/10000:.0f}万</div>
            <div class="stat-label">{n_sel}国总产量(2025)</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['total_sales']/10000:.0f}万</div>
            <div class="stat-label">{n_sel}国新车销量(2025)</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['total_china_export']/10000:.0f}万</div>
            <div class="stat-label">中国出口筛选国(2025)</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['max_risk']}</div>
            <div class="stat-label">风险最高(筛选内)</div>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{stats['min_risk']}</div>
            <div class="stat-label">风险最低(筛选内)</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ======== 主内容区 ========
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["📊 产量与销量", "🏷️ 品牌与EV", "⚠️ 供应链风险", "🎯 优化决策", "📋 数据明细", "🇨🇳 中国品牌出海", "📉 贸易壁垒与进口", "📊 市场深度"])

    with tab1:
        # 产量趋势图
        col1, col2 = st.columns(2)
        with col1:
            log_prod = st.checkbox("对数坐标（对比小国产量）", value=True, key="log_prod")
            prod_fig = fig_production_trend(selected_country_codes)
            if log_prod:
                prod_fig.update_yaxes(type="log")
            st.plotly_chart(prod_fig, use_container_width=True)
            if getattr(prod_fig, '_no_production', None):
                st.error('⚠ 无本土制造: ' + ', '.join(prod_fig._no_production))
            st.markdown(f'📚 {source_caption(["OICA", "ANFAVEA", "AMIA", "AUTOSTAT"])}')
        with col2:
            st.plotly_chart(fig_china_export(selected_country_codes), use_container_width=True)
            st.markdown(f'📚 {source_caption(["CPCA", "CAAM"])}')

        # 销量趋势图
        log_sales = st.checkbox("对数坐标（对比小国销量）", value=True, key="log_sales")
        sales_fig = fig_sales_trend(selected_country_codes)
        if log_sales:
            sales_fig.update_yaxes(type="log", row=1, col=1)
            sales_fig.update_yaxes(type="log", row=2, col=1)
        st.plotly_chart(sales_fig, use_container_width=True)
        st.markdown(f'📚 {source_caption(["ANFAVEA", "AMIA", "AUTOSTAT", "ANAC", "PAMA", "ARAPER", "FTI", "Gaikindo"])}')

    with tab2:
        col1, col2 = st.columns([3, 2])
        with col1:
            st.plotly_chart(fig_brand_share(selected_country_codes), use_container_width=True)
            st.markdown(f'📚 {source_caption(["MarkLines", "ANFAVEA", "AMIA", "AUTOSTAT"])}')
        with col2:
            st.plotly_chart(fig_ev_penetration(selected_country_codes), use_container_width=True)
            st.markdown(f'📚 {source_caption(["MarkLines", "CEIC"])}')

    with tab3:
        # ── 量化风险评分 ──
        scorer = CountryRiskScorer()
        risk_metrics_list = []
        for c in selected_country_codes:
            r = RISK[c]
            b = TRADE_BARRIERS.get(c, {})
            ev_val = EV.get(c, 0)
            imp_dep = IMPORT_DEP.get(c, 0.5)
            metrics = CountryRiskMetrics(
                country_id=c,
                country_cn=COUNTRY_CN.get(c, c),
                geopolitical_risk=r.get("geopolitical_risk", 0.3),
                supply_disruption_risk=r.get("supply_disruption", 0.3),
                tariff_risk=min(1.0, b.get("import_tariff", 0.1) * 2),  # 关税越高风险越高
                logistics_risk=r.get("logistics_risk", 0.3),
                regulatory_risk=r.get("regulatory_risk", 0.2),
                tariff_rate=b.get("import_tariff"),
                localization_requirement=b.get("localization_requirement"),
                ev_incentive_level=0.5 if b.get("ev_incentive") else 0.0,
                import_dependency=imp_dep,
            )
            risk_metrics_list.append(metrics)

        risk_scores = scorer.score_all(risk_metrics_list)

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_supply_chain_radar(selected_country_codes), use_container_width=True)
        with col2:
            st.plotly_chart(fig_risk_heatmap(selected_country_codes), use_container_width=True)
        st.markdown(f'📚 {source_caption(["CEIC", "MarkLines"])}')

        # 量化风险评分表
        st.subheader("📊 量化风险评分")
        risk_rows = []
        for s in risk_scores:
            level_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(s.risk_level, "⚪")
            risk_rows.append({
                "国家": s.country_cn,
                "综合评分": f"{s.overall_score:.1%}",
                "风险等级": f"{level_emoji} {s.risk_level}",
                "地缘": f"{s.factor_breakdown.get('geopolitical', 0):.0%}",
                "关税": f"{s.factor_breakdown.get('tariff', 0):.0%}",
                "供应": f"{s.factor_breakdown.get('supply_disruption', 0):.0%}",
                "物流": f"{s.factor_breakdown.get('logistics', 0):.0%}",
                "法规": f"{s.factor_breakdown.get('regulatory', 0):.0%}",
            })
        st.dataframe(pd.DataFrame(risk_rows), use_container_width=True, hide_index=True)

        # 建议区
        st.subheader("💡 风险应对建议")
        for s in risk_scores:
            if s.recommendations:
                with st.expander(f"{s.country_cn} — {s.overall_score:.0%} ({s.risk_level})"):
                    for rec in s.recommendations:
                        st.markdown(f"- {rec}")

        # 原有风险详情表
        st.subheader("📝 各国供应链关键风险")
        risk_df = table_supply_chain_risks(selected_country_codes)
        st.dataframe(risk_df, use_container_width=True, height=400)

    with tab4:
        # ── 优化决策 Tab ──
        st.subheader("🎯 中国汽车出口市场分配优化")
        st.caption("基于 CP-SAT 混合整数规划，回答“去哪里、去多少”的核心问题")

        # 构建候选国数据
        allocator = MarketAllocator()
        candidates = []
        for c in selected_country_codes:
            s_data = SALES.get(c, {})
            b = TRADE_BARRIERS.get(c, {})
            brand = BRANDS.get(c, {})
            r = RISK.get(c, {})
            # 从风险评分获取综合风险
            rs = next((x for x in risk_scores if x.country_id == c), None)
            risk_val = rs.overall_score if rs else sum(r.get(d, 0.3) for d in ["geopolitical_risk", "supply_disruption", "price_volatility", "logistics_risk", "regulatory_risk"]) / 5

            # 物流天数估算
            logistics_days_map = {
                "Malaysia": 7, "Thailand": 10, "Indonesia": 12, "Pakistan": 18,
                "Kazakhstan": 20, "Turkey": 22, "Russia": 25, "SaudiArabia": 25,
                "SouthAfrica": 30, "Peru": 35, "Chile": 38, "Mexico": 40, "Brazil": 45,
            }

            market_size = s_data.get("new_car_sales", [0])[-1] if s_data else 100_000
            china_share = 0.0
            if brand and "brands" in brand and "shares" in brand:
                for bname, share in zip(brand["brands"], brand["shares"]):
                    if any(kw in bname for kw in ["中国品牌", "Chinese", "Chery", "BYD", "MG", "Geely", "Haval", "Great Wall"]):
                        china_share = max(china_share, share / 100)

            candidates.append(MarketCandidate(
                country_id=c,
                country_cn=COUNTRY_CN.get(c, c),
                market_size=market_size,
                china_brand_share=china_share,
                tariff_rate=b.get("import_tariff", 0.1),
                risk_score=risk_val,
                logistics_days=logistics_days_map.get(c, 30),
                max_share=0.30 if b.get("localization_requirement", 0) < 0.3 else 0.20,
                localization_requirement=b.get("localization_requirement", 0),
            ))

        # 侧边控制
        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
        with col_ctrl1:
            risk_lambda = st.slider(
                "风险厌恶系数 λ", 0.0, 1.0, 0.3, 0.05,
                help="λ=0 激进策略（纯利润最大化），λ=1 保守策略（风险最小化）",
            )
        with col_ctrl2:
            export_capacity = st.number_input(
                "年出口产能上限（万辆）", 50, 1000, 500, 50,
            ) * 10_000
        with col_ctrl3:
            max_countries = st.slider("最多进入国家数", 3, 13, 10)

        # 优化
        result = allocator.optimize(
            candidates,
            total_export_capacity=export_capacity,
            risk_lambda=risk_lambda,
            max_countries=max_countries,
        )

        # 策略标签
        if risk_lambda <= 0.15:
            strategy_label = "🔥 激进策略"
        elif risk_lambda <= 0.5:
            strategy_label = "⚖️ 平衡策略"
        else:
            strategy_label = "🛡️ 保守策略"

        # 结果概览
        st.markdown(f"**{strategy_label}** | 求解器: `{result.method}` | 状态: `{result.solver_status}` | 耗时: {result.solve_time_ms:.0f}ms")
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.metric("预期总收益", f"{result.total_revenue/10000:.1f}万辆")
        with mc2:
            st.metric("总风险暴露", f"{result.total_risk/10000:.1f}万辆当量")
        with mc3:
            st.metric("目标国数", f"{len(result.allocations)}")

        # 分配柱状图
        if result.allocations:
            alloc_sorted = sorted(result.allocations.items(), key=lambda x: -x[1])
            alloc_countries = [COUNTRY_CN.get(c, c) for c, _ in alloc_sorted]
            alloc_values = [v for _, v in alloc_sorted]
            alloc_colors = [COUNTRY_COLORS.get(c, "#95a5a6") for c, _ in alloc_sorted]

            fig_alloc = go.Figure(go.Bar(
                x=alloc_countries,
                y=alloc_values,
                marker_color=alloc_colors,
                text=[f"{v/10000:.1f}万" for v in alloc_values],
                textposition="outside",
                hovertemplate="%{x}<br>建议出口: %{y:,.0f} 辆<extra></extra>",
            ))
            fig_alloc.update_layout(
                title=dict(text=f"🎯 建议出口分配方案 (λ={risk_lambda:.2f})", font=dict(size=16)),
                xaxis=dict(title="目标国"),
                yaxis=dict(title="出口量 (辆)", tickformat=","),
                template="plotly_white",
                height=450,
            )
            st.plotly_chart(fig_alloc, use_container_width=True)

            # 分配详情表
            st.subheader("📋 分配详情")
            alloc_rows = []
            for c_id, qty in alloc_sorted:
                cand = next((x for x in candidates if x.country_id == c_id), None)
                rs = next((x for x in risk_scores if x.country_id == c_id), None)
                alloc_rows.append({
                    "目标国": COUNTRY_CN.get(c_id, c_id),
                    "建议出口量": f"{qty:,.0f} 辆",
                    "市场容量": f"{cand.market_size:,.0f}" if cand else "—",
                    "份额": f"{qty/cand.market_size:.1%}" if cand and cand.market_size > 0 else "—",
                    "关税": f"{cand.tariff_rate:.0%}" if cand else "—",
                    "风险评分": f"{rs.overall_score:.1%}" if rs else "—",
                    "风险等级": rs.risk_level if rs else "—",
                })
            st.dataframe(pd.DataFrame(alloc_rows), use_container_width=True, hide_index=True)

        # 三策略对比
        st.divider()
        st.subheader("📊 三策略一键对比")
        if st.button("🔄 生成对比", key="compare_strategies"):
            with st.spinner("计算中..."):
                strategies = allocator.compare_strategies(candidates, export_capacity)
                c1, c2, c3 = st.columns(3)

                for col, label, key in [(c1, "🔥 激进 (λ=0)", "aggressive"), (c2, "⚖️ 平衡 (λ=拐点)", "balanced"), (c3, "🛡️ 保守 (λ=1)", "conservative")]:
                    with col:
                        res = strategies[key]
                        st.markdown(f"**{label}**")
                        st.metric("目标国数", f"{len(res.allocations)}")
                        st.metric("预期收益", f"{res.total_revenue/10000:.1f}万")
                        st.metric("风险暴露", f"{res.total_risk/10000:.1f}万")
                        top3 = sorted(res.allocations.items(), key=lambda x: -x[1])[:3]
                        for c_id, qty in top3:
                            st.caption(f"  {COUNTRY_CN.get(c_id, c_id)}: {qty/10000:.1f}万")

                # 敏感性曲线
                sens = strategies["sensitivity"]
                fig_sens = go.Figure()
                fig_sens.add_trace(go.Scatter(
                    x=sens.lambda_values, y=[r/10000 for r in sens.revenues],
                    mode="lines+markers", name="预期收益(万辆)",
                    line=dict(color="#2ca02c", width=2.5),
                ))
                fig_sens.add_trace(go.Scatter(
                    x=sens.lambda_values, y=[r/10000 for r in sens.risks],
                    mode="lines+markers", name="风险暴露(万辆)",
                    line=dict(color="#d62728", width=2.5),
                ))
                # 拐点标注
                fig_sens.add_vline(x=sens.elbow_lambda, line_dash="dash", line_color="gray",
                                   annotation_text=f"拐点 λ={sens.elbow_lambda:.2f}")
                fig_sens.update_layout(
                    title="收益-风险敏感性曲线",
                    xaxis=dict(title="风险厌恶系数 λ"),
                    yaxis=dict(title="万辆"),
                    template="plotly_white",
                    height=350,
                    legend=dict(orientation="h", y=-0.2),
                )
                st.plotly_chart(fig_sens, use_container_width=True)

        # ── CKD/CBU 本地化率分析 ──
        st.divider()
        st.subheader("🏭 CKD vs CBU 进入模式分析")
        st.caption("基于BOM物料清单 + 各国关税/本地化率法规 → 推荐最优进入模式")

        bom_analyzer = AutomotiveBOMAnalyzer()
        is_ev_bom = st.toggle("分析EV车型", value=False, key="bom_ev_toggle")

        bom_results = bom_analyzer.analyze_all(selected_country_codes, is_ev=is_ev_bom)

        # 模式分布柱状图
        mode_colors = {EntryMode.CBU: "#e74c3c", EntryMode.SKD: "#f39c12", EntryMode.CKD: "#27ae60"}
        fig_bom = go.Figure()
        for mode in [EntryMode.CKD, EntryMode.SKD, EntryMode.CBU]:
            mode_results = [r for r in bom_results if r.recommended_mode == mode]
            if mode_results:
                fig_bom.add_trace(go.Bar(
                    x=[r.country_cn for r in mode_results],
                    y=[r.total_cost_index for r in mode_results],
                    name=mode.value.upper(),
                    marker_color=mode_colors[mode],
                    text=[f"{r.total_cost_index:.2f}" for r in mode_results],
                    textposition="outside",
                    hovertemplate="%{x}: 成本指数 %{y:.2f}<extra></extra>",
                ))
        fig_bom.update_layout(
            title=dict(text="🏭 各国推荐进入模式 & 成本指数 (CBU=1.0基准)", font=dict(size=16)),
            xaxis=dict(title="国家"),
            yaxis=dict(title="成本指数"),
            template="plotly_white",
            height=400,
        )
        st.plotly_chart(fig_bom, use_container_width=True)

        # BOM详情表
        bom_rows = []
        mode_emoji = {EntryMode.CBU: "🔴", EntryMode.SKD: "🟡", EntryMode.CKD: "🟢"}
        for r in sorted(bom_results, key=lambda x: x.total_cost_index):
            bom_rows.append({
                "国家": r.country_cn,
                "推荐模式": f"{mode_emoji.get(r.recommended_mode, '')} {r.recommended_mode.value.upper()}",
                "成本指数": f"{r.total_cost_index:.2f}",
                "本地化率": f"{r.localization_rate:.0%}",
                "要求本地化率": f"{DEFAULT_COUNTRY_PROFILES[r.country_id].required_localization:.0%}" if r.country_id in DEFAULT_COUNTRY_PROFILES else "—",
                "关税节省": f"{r.tariff_savings:.0%}",
                "回本年数": f"{r.breakeven_years:.1f}年" if r.breakeven_years < 100 else "CBU最优",
            })
        st.dataframe(pd.DataFrame(bom_rows), use_container_width=True, hide_index=True)

        # 本地化率差距分析
        with st.expander("📋 各国子系统本地化率明细"):
            for r in bom_results:
                st.markdown(f"**{r.country_cn}** — {r.recommended_mode.value.upper()}")
                for rec in r.recommendations:
                    st.caption(f"  {rec}")

    with tab5:
        st.subheader("📋 国家概览表")
        overview_df = table_country_overview(selected_country_codes)
        st.dataframe(overview_df, use_container_width=True, hide_index=True)

        st.subheader("🇨🇳 中国出口目标国")
        st.dataframe(table_china_exports(), use_container_width=True, hide_index=True)

        if show_raw_data:
            st.subheader("🔧 原始数据 (JSON)")
            with st.expander("点击展开原始数据"):
                st.json(data)

    with tab6:
        # 中国品牌市场份额增长趋势
        if CHINA_BRAND_TREND:
            st.plotly_chart(fig_china_brand_trend(), use_container_width=True)
            st.markdown(f'📚 {source_caption(["MarkLines", "CPCA", "Zhinen"])}')
        else:
            st.warning("暂无中国品牌趋势数据")

        # 电动车渗透率增长趋势
        if EV_TREND:
            st.plotly_chart(fig_ev_trend(), use_container_width=True)
            st.markdown(f'📚 {source_caption(["MarkLines", "CEIC"])}')
        else:
            st.warning("暂无EV渗透率趋势数据")

    with tab7:
        # 各国贸易壁垒对比
        if TRADE_BARRIERS:
            st.plotly_chart(fig_trade_barriers(), use_container_width=True)
            st.markdown(f'📚 {source_caption(["CEIC", "MarkLines"])}')
            # 标注各国 notes — 用 expandable section
            with st.expander("📋 各国贸易政策详情"):
                for c, info in TRADE_BARRIERS.items():
                    cn_name = COUNTRY_CN.get(c, c)
                    notes = info.get("notes", "")
                    ev_status = "✅ 有" if info.get("ev_incentive") else "❌ 无"
                    tariff = info.get("import_tariff", 0) * 100
                    local_req = info.get("localization_requirement", 0) * 100
                    st.markdown(f"**{cn_name}** — 进口关税 {tariff:.0f}% | 本地化率要求 {local_req:.0f}% | EV激励: {ev_status}")
                    if notes:
                        st.caption(f"  ↳ {notes}")
        else:
            st.warning("暂无贸易壁垒数据")

        # 各国汽车进口依赖度
        if IMPORT_DEP:
            st.plotly_chart(fig_import_dependency(), use_container_width=True)
            st.markdown(f'📚 {source_caption(["OICA", "MarkLines"])}')
        else:
            st.warning("暂无进口依赖度数据")

    with tab8:
        # 二手车/新车市场比率
        if USED_NEW_RATIO:
            st.plotly_chart(fig_used_new_ratio(), use_container_width=True)
            st.markdown(f'📚 {source_caption(["ANFAVEA", "AMIA", "AUTOSTAT", "ANAC", "FTI", "Gaikindo", "NAAMSA", "MAA"])}')
        else:
            st.warning("暂无二手车/新车比率数据")


if __name__ == "__main__":
    run()
