"""
交互式可视化仪表盘 - 基于 Streamlit + Plotly
"""
import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    import streamlit as st
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install streamlit plotly pandas")
    st = None


def create_dashboard():
    """创建 Streamlit 仪表盘"""
    if st is None:
        print("Streamlit not available. Install with: pip install streamlit")
        return

    st.set_page_config(
        page_title="全球汽车市场 & 供应链风险分析",
        page_icon="🚗",
        layout="wide",
    )

    st.title("🚗 全球汽车市场调研与跨国供应链风险分析")

    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 控制面板")
        data_source = st.selectbox("数据来源", ["mobile.de", "所有平台"])
        brand_filter = st.multiselect("品牌筛选", ["BMW", "Mercedes-Benz", "Volkswagen", "Audi", "Toyota"])
        price_range = st.slider("价格范围 (EUR)", 0, 200000, (10000, 80000))

    # 主内容区
    tab1, tab2, tab3 = st.tabs(["📊 市场概览", "⚠️ 风险评估", "🌿 碳排放追踪"])

    with tab1:
        st.subheader("市场概览")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("在售车辆", "12,345", "+5.2%")
        with col2:
            st.metric("平均价格", "€28,500", "-1.3%")
        with col3:
            st.metric("品牌数量", "47", "+2")
        with col4:
            st.metric("数据更新", "2026-06-14", "")

        # 示例图表
        st.subheader("价格分布")
        # 实际使用时替换为真实数据
        sample_data = pd.DataFrame({
            "Brand": ["BMW", "Mercedes", "Audi", "VW", "Toyota"] * 20,
            "Price": [35000, 42000, 33000, 25000, 28000] * 20,
        })
        fig = px.box(sample_data, x="Brand", y="Price", title="各品牌价格分布")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("供应链风险评估")
        risk_data = pd.DataFrame({
            "风险类别": ["供应中断", "价格波动", "地缘政治", "法规变化", "物流风险", "环境风险"],
            "风险评分": [0.65, 0.72, 0.55, 0.40, 0.48, 0.35],
            "发生概率": [0.30, 0.50, 0.40, 0.25, 0.35, 0.20],
            "影响程度": [0.70, 0.60, 0.80, 0.55, 0.65, 0.50],
        })
        fig = px.bar(risk_data, x="风险类别", y="风险评分", color="风险评分",
                     color_continuous_scale="Reds", title="供应链风险评分")
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("碳排放追踪")
        st.info("🚧 零碳电力投资系统数据库升级中，功能开发中...")


if __name__ == "__main__":
    create_dashboard()
