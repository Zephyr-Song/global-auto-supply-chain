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

# 初始化数据
data = get_all_data()
PROD = data["production"]
SALES = data["sales"]
BRANDS = data["brand_market_share"]
RISK = data["supply_chain_risk"]
EV = data["ev_penetration"]
EXPORT = data["china_export"]

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


# ============================================================
# 图表构建函数
# ============================================================

def fig_production_trend(active=None):
    """产量趋势图"""
    active = active or COUNTRIES
    fig = go.Figure()
    for c in active:
        p = PROD[c]
        has_production = any(v > 0 for v in p["production"])
        # 对数坐标下0无定义，用None替代0值让线断开
        y_vals = [v if v > 0 else None for v in p["production"]]
        fig.add_trace(go.Scatter(
            x=p["years"], y=y_vals,
            mode="lines+markers",
            name=f"{p['country_cn']} ({c})" + (" ⚠无本土制造" if not has_production else ""),
            line=dict(
                color=COUNTRY_COLORS[c],
                width=2.5 if has_production else 1.5,
                dash="solid" if has_production else "dash",
            ),
            marker=dict(size=6 if has_production else 4),
            hovertemplate="%{y:,.0f} 辆",
            opacity=1.0 if has_production else 0.5,
        ))
    fig.update_layout(
        title=dict(text="📊 目标国汽车产量趋势 (2020-2025)", font=dict(size=18)),
        xaxis=dict(title="年份", dtick=1),
        yaxis=dict(title="产量 (辆)", tickformat=","),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
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


def fig_china_export(active=None):
    """中国出口到目标国 — 条形图"""
    active = active or COUNTRIES
    meta_keys = {'total_china_export_2025', 'source'}
    # 只显示选中的国家 + UAE（如果被选中）
    active_set = set(active)
    export_data = [(k, v) for k, v in EXPORT.items() if isinstance(v, (int, float)) and k not in meta_keys and k in active_set]
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
            st.markdown(f"- {s}")

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
    tab1, tab2, tab3, tab4 = st.tabs(["📊 产量与销量", "🏷️ 品牌与EV", "⚠️ 供应链风险", "📋 数据明细"])

    with tab1:
        # 产量趋势图
        col1, col2 = st.columns(2)
        with col1:
            log_prod = st.checkbox("对数坐标（对比小国产量）", value=True, key="log_prod")
            prod_fig = fig_production_trend(selected_country_codes)
            if log_prod:
                prod_fig.update_yaxes(type="log")
            st.plotly_chart(prod_fig, use_container_width=True)
        with col2:
            st.plotly_chart(fig_china_export(selected_country_codes), use_container_width=True)

        # 销量趋势图
        log_sales = st.checkbox("对数坐标（对比小国销量）", value=True, key="log_sales")
        sales_fig = fig_sales_trend(selected_country_codes)
        if log_sales:
            sales_fig.update_yaxes(type="log", row=1, col=1)
            sales_fig.update_yaxes(type="log", row=2, col=1)
        st.plotly_chart(sales_fig, use_container_width=True)

    with tab2:
        col1, col2 = st.columns([3, 2])
        with col1:
            st.plotly_chart(fig_brand_share(selected_country_codes), use_container_width=True)
        with col2:
            st.plotly_chart(fig_ev_penetration(selected_country_codes), use_container_width=True)

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_supply_chain_radar(selected_country_codes), use_container_width=True)
        with col2:
            st.plotly_chart(fig_risk_heatmap(selected_country_codes), use_container_width=True)

        # 风险详情表
        st.subheader("📝 各国供应链关键风险")
        risk_df = table_supply_chain_risks(selected_country_codes)
        st.dataframe(risk_df, use_container_width=True, height=400)

    with tab4:
        st.subheader("📋 国家概览表")
        overview_df = table_country_overview(selected_country_codes)
        st.dataframe(overview_df, use_container_width=True, hide_index=True)

        st.subheader("🇨🇳 中国出口目标国")
        st.dataframe(table_china_exports(), use_container_width=True, hide_index=True)

        if show_raw_data:
            st.subheader("🔧 原始数据 (JSON)")
            with st.expander("点击展开原始数据"):
                st.json(data)


if __name__ == "__main__":
    run()
