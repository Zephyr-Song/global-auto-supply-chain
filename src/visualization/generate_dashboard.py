"""
全球汽车市场可视化仪表盘
生成独立的 HTML 文件，包含所有交互式图表
"""
import json
import os
import sys

# 确保项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.analysis.market_data import (
    PRODUCTION_DATA, SALES_DATA, BRAND_MARKET_SHARE,
    SUPPLY_CHAIN_RISK, EV_PENETRATION
)

COUNTRIES = ["Brazil", "Mexico", "Russia", "Chile", "Kazakhstan", "Pakistan", "Peru"]
COUNTRIES_CN = {
    "Brazil": "巴西", "Mexico": "墨西哥", "Russia": "俄罗斯",
    "Chile": "智利", "Kazakhstan": "哈萨克斯坦", "Pakistan": "巴基斯坦", "Peru": "秘鲁"
}

COLORS = {
    "Brazil": "#009c3b", "Mexico": "#006847", "Russia": "#d52b1e",
    "Chile": "#ef3340", "Kazakhstan": "#00afca", "Pakistan": "#01411c",
    "Peru": "#d91023"
}


def generate_html():
    """生成完整的可视化 HTML"""
    years = PRODUCTION_DATA["Brazil"]["years"]
    
    # 产量序列
    prod_series = []
    for c in COUNTRIES:
        prod_series.append({
            "type": "line",
            "name": COUNTRIES_CN[c],
            "data": PRODUCTION_DATA[c]["production"],
            "smooth": True,
            "itemStyle": {"color": COLORS[c]}
        })
    
    # 销量序列（万辆）
    sales_series = []
    for c in COUNTRIES:
        sales_series.append({
            "type": "bar",
            "name": COUNTRIES_CN[c],
            "data": [round(x / 10000, 1) for x in SALES_DATA[c]["new_car_sales"]],
            "itemStyle": {"color": COLORS[c]}
        })
    
    # 风险雷达图数据
    risk_data = {}
    for c in COUNTRIES:
        r = SUPPLY_CHAIN_RISK[c]
        risk_data[c] = [
            r["geopolitical_risk"], r["supply_disruption"],
            r["price_volatility"], r["logistics_risk"], r["regulatory_risk"]
        ]
    
    radar_series_data = []
    for c in COUNTRIES:
        radar_series_data.append({
            "value": risk_data[c],
            "name": COUNTRIES_CN[c],
            "itemStyle": {"color": COLORS[c]},
            "areaStyle": {"opacity": 0.15}
        })
    
    # 综合风险评分
    risk_scores = {}
    for c in COUNTRIES:
        r = SUPPLY_CHAIN_RISK[c]
        risk_scores[c] = round(
            (r["geopolitical_risk"] + r["supply_disruption"] + r["price_volatility"] + 
             r["logistics_risk"] + r["regulatory_risk"]) / 5 * 100, 1
        )
    
    # 电动车渗透率
    ev_bar_data = []
    for c in COUNTRIES:
        ev_bar_data.append({
            "value": round(EV_PENETRATION[c] * 100, 1),
            "itemStyle": {"color": COLORS[c]}
        })
    
    # 品牌市场份额
    brand_brazil = [{"value": v, "name": n} for n, v in zip(
        BRAND_MARKET_SHARE["Brazil"]["brands"], BRAND_MARKET_SHARE["Brazil"]["shares"])]
    brand_russia = [{"value": v, "name": n} for n, v in zip(
        BRAND_MARKET_SHARE["Russia"]["brands"], BRAND_MARKET_SHARE["Russia"]["shares"])]
    
    # 风险详情柱状图
    risk_detail_series = []
    for c in COUNTRIES:
        risk_detail_series.append({
            "type": "bar",
            "name": COUNTRIES_CN[c],
            "data": risk_data[c],
            "itemStyle": {"color": COLORS[c]}
        })

    # ---- 风险卡片 HTML ----
    risk_cards_html = ""
    for c in COUNTRIES:
        score = risk_scores[c]
        level = "low" if score < 30 else "medium" if score < 50 else "high" if score < 70 else "critical"
        risk_cards_html += '<div class="risk-card"><div class="score risk-{}">{}</div><div class="label">{}</div></div>\n'.format(
            level, score, COUNTRIES_CN[c])
    
    # ---- 风险洞察 HTML ----
    risk_insights_html = ""
    for c in COUNTRIES:
        risk_insights_html += '<div class="insights"><h3>{} 关键风险</h3><ul>'.format(COUNTRIES_CN[c])
        for risk in SUPPLY_CHAIN_RISK[c]["key_risks"]:
            risk_insights_html += '<li>{}</li>'.format(risk)
        risk_insights_html += '</ul></div>\n'

    # ---- 构建完整 HTML ----
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>全球汽车市场调研与跨国供应链风险分析</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; }
.header { background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%); padding: 2rem; text-align: center; border-bottom: 1px solid #1e293b; }
.header h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
.header p { color: #94a3b8; font-size: 0.95rem; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; padding: 1.5rem; max-width: 1600px; margin: 0 auto; }
.card { background: #1e293b; border-radius: 12px; padding: 1.5rem; border: 1px solid #334155; }
.card.full { grid-column: 1 / -1; }
.card h2 { font-size: 1.1rem; margin-bottom: 1rem; color: #f1f5f9; }
.chart { width: 100%; height: 420px; }
.chart-sm { width: 100%; height: 350px; }
.risk-cards { display: grid; grid-template-columns: repeat(7, 1fr); gap: 0.75rem; margin-bottom: 1rem; }
.risk-card { background: #0f172a; border-radius: 8px; padding: 1rem; text-align: center; border: 1px solid #334155; }
.risk-card .score { font-size: 1.5rem; font-weight: 700; }
.risk-card .label { font-size: 0.8rem; color: #94a3b8; margin-top: 0.25rem; }
.risk-low { color: #10b981; }
.risk-medium { color: #f59e0b; }
.risk-high { color: #ef4444; }
.risk-critical { color: #dc2626; }
.insights-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin-top: 1rem; }
.insights { background: #0f172a; border-radius: 8px; padding: 1rem; }
.insights h3 { font-size: 0.95rem; color: #f59e0b; margin-bottom: 0.5rem; }
.insights ul { list-style: none; padding: 0; }
.insights li { padding: 0.4rem 0; color: #cbd5e1; font-size: 0.85rem; border-bottom: 1px solid #1e293b; }
.insights li::before { content: "⚠️ "; }
.footer { text-align: center; padding: 2rem; color: #64748b; font-size: 0.8rem; }
@media (max-width: 1024px) { .grid { grid-template-columns: 1fr; } .risk-cards { grid-template-columns: repeat(4, 1fr); } }
</style>
</head>
<body>

<div class="header">
    <h1>🚗 全球汽车市场调研与跨国供应链风险分析</h1>
    <p>巴西 · 墨西哥 · 俄罗斯 · 智利 · 哈萨克斯坦 · 巴基斯坦 · 秘鲁 | 数据来源：OICA/各国汽车协会/行业公开报告</p>
</div>

<div class="grid">
<div class="card full">
    <h2>⚡ 供应链风险总览（综合评分 0-100）</h2>
    <div class="risk-cards">
""" + risk_cards_html + """    </div>
    <div id="risk_radar" class="chart-sm"></div>
</div>

<div class="card">
    <h2>📊 各国汽车产量趋势 (2019-2024)</h2>
    <div id="production_chart" class="chart"></div>
</div>

<div class="card">
    <h2>📈 各国新车销量趋势 (2019-2024, 万辆)</h2>
    <div id="sales_chart" class="chart"></div>
</div>

<div class="card">
    <h2>🔋 2024年电动车渗透率 (%)</h2>
    <div id="ev_chart" class="chart-sm"></div>
</div>

<div class="card">
    <h2>🏷️ 巴西汽车品牌市场份额 (2024)</h2>
    <div id="brand_brazil" class="chart-sm"></div>
</div>

<div class="card">
    <h2>🏷️ 俄罗斯汽车品牌市场份额 (2024)</h2>
    <div id="brand_russia" class="chart-sm"></div>
</div>

<div class="card">
    <h2>🏷️ 墨西哥汽车品牌市场份额 (2024)</h2>
    <div id="brand_mexico" class="chart-sm"></div>
</div>

<div class="card full">
    <h2>🔍 各国供应链风险对比</h2>
    <div id="risk_detail" class="chart"></div>
</div>

<div class="card full">
    <h2>📋 各国供应链关键风险</h2>
    <div class="insights-grid">
""" + risk_insights_html + """    </div>
</div>
</div>

<div class="footer">
    <p>全球汽车市场调研与跨国供应链风险分析 | 数据截至2024年 | 基于OICA/ANFAVEA/AMIA/AEB/ANAC/KAZAUTO/PAMA/ARAPER公开数据</p>
    <p>GitHub: https://github.com/Zephyr-Song/global-auto-supply-chain</p>
</div>

<script>
var years = """ + json.dumps(years) + """;
var countryNames = """ + json.dumps([COUNTRIES_CN[c] for c in COUNTRIES]) + """;

// ============ 产量趋势图 ============
var prodChart = echarts.init(document.getElementById('production_chart'));
prodChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: countryNames, top: 0, textStyle: { color: '#94a3b8' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: years, axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#94a3b8' } },
    yAxis: { type: 'value', name: '产量（辆）', nameTextStyle: { color: '#94a3b8' }, axisLine: { lineStyle: { color: '#334155' } }, splitLine: { lineStyle: { color: '#1e293b' } }, axisLabel: { color: '#94a3b8', formatter: function(v) { return (v/10000).toFixed(0) + '万'; } } },
    series: """ + json.dumps(prod_series) + """
});

// ============ 销量趋势图 ============
var salesChart = echarts.init(document.getElementById('sales_chart'));
salesChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: countryNames, top: 0, textStyle: { color: '#94a3b8' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: years, axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#94a3b8' } },
    yAxis: { type: 'value', name: '销量（万辆）', nameTextStyle: { color: '#94a3b8' }, axisLine: { lineStyle: { color: '#334155' } }, splitLine: { lineStyle: { color: '#1e293b' } }, axisLabel: { color: '#94a3b8' } },
    series: """ + json.dumps(sales_series) + """
});

// ============ 风险雷达图 ============
var radarChart = echarts.init(document.getElementById('risk_radar'));
radarChart.setOption({
    tooltip: {},
    legend: { data: countryNames, bottom: 0, textStyle: { color: '#94a3b8', fontSize: 11 } },
    radar: {
        indicator: [
            { name: '地缘政治', max: 1 },
            { name: '供应中断', max: 1 },
            { name: '价格波动', max: 1 },
            { name: '物流风险', max: 1 },
            { name: '法规风险', max: 1 }
        ],
        axisName: { color: '#94a3b8' },
        splitArea: { areaStyle: { color: ['rgba(16,185,129,0.05)', 'rgba(245,158,11,0.05)', 'rgba(239,68,68,0.1)'] } }
    },
    series: [{
        type: 'radar',
        data: """ + json.dumps(radar_series_data) + """
    }]
});

// ============ 电动车渗透率 ============
var evChart = echarts.init(document.getElementById('ev_chart'));
evChart.setOption({
    tooltip: { trigger: 'axis', formatter: '{b}: {c}%' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: countryNames, axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#94a3b8' } },
    yAxis: { type: 'value', name: '渗透率(%)', nameTextStyle: { color: '#94a3b8' }, axisLine: { lineStyle: { color: '#334155' } }, splitLine: { lineStyle: { color: '#1e293b' } }, axisLabel: { color: '#94a3b8' } },
    series: [{
        type: 'bar',
        data: """ + json.dumps(ev_bar_data) + """,
        barWidth: '50%',
        label: { show: true, position: 'top', formatter: '{c}%', color: '#e2e8f0' }
    }]
});

// ============ 品牌市场份额 - 巴西 ============
var brandBR = echarts.init(document.getElementById('brand_brazil'));
brandBR.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {d}%' },
    color: ['#2563eb','#f59e0b','#10b981','#ef4444','#8b5cf6','#ec4899','#06b6d4','#f97316','#6366f1','#9ca3af'],
    series: [{
        type: 'pie', radius: ['35%', '65%'],
        data: """ + json.dumps(brand_brazil) + """,
        label: { color: '#94a3b8', fontSize: 11 },
        itemStyle: { borderColor: '#1e293b', borderWidth: 2 }
    }]
});

// ============ 品牌市场份额 - 俄罗斯 ============
var brandRU = echarts.init(document.getElementById('brand_russia'));
brandRU.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {d}%' },
    color: ['#2563eb','#f59e0b','#10b981','#ef4444','#8b5cf6','#ec4899','#06b6d4','#f97316','#6366f1','#9ca3af'],
    series: [{
        type: 'pie', radius: ['35%', '65%'],
        data: """ + json.dumps(brand_russia) + """,
        label: { color: '#94a3b8', fontSize: 11 },
        itemStyle: { borderColor: '#1e293b', borderWidth: 2 }
    }]
});

// ============ 品牌市场份额 - 墨西哥 ============
var brandMX = echarts.init(document.getElementById('brand_mexico'));
var brandMexicoData = """ + json.dumps([{"value": v, "name": n} for n, v in zip(
        BRAND_MARKET_SHARE["Mexico"]["brands"], BRAND_MARKET_SHARE["Mexico"]["shares"])]) + """;
brandMX.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {d}%' },
    color: ['#2563eb','#f59e0b','#10b981','#ef4444','#8b5cf6','#ec4899','#06b6d4','#f97316','#6366f1','#9ca3af'],
    series: [{
        type: 'pie', radius: ['35%', '65%'],
        data: brandMexicoData,
        label: { color: '#94a3b8', fontSize: 11 },
        itemStyle: { borderColor: '#1e293b', borderWidth: 2 }
    }]
});

// ============ 风险详情 ============
var riskDetail = echarts.init(document.getElementById('risk_detail'));
riskDetail.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: countryNames, textStyle: { color: '#94a3b8' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['地缘政治', '供应中断', '价格波动', '物流风险', '法规风险'], axisLine: { lineStyle: { color: '#334155' } }, axisLabel: { color: '#94a3b8' } },
    yAxis: { type: 'value', max: 1, nameTextStyle: { color: '#94a3b8' }, axisLine: { lineStyle: { color: '#334155' } }, splitLine: { lineStyle: { color: '#1e293b' } }, axisLabel: { color: '#94a3b8' } },
    series: """ + json.dumps(risk_detail_series) + """
});

// 响应式
window.addEventListener('resize', function() {
    prodChart.resize(); salesChart.resize(); radarChart.resize();
    evChart.resize(); brandBR.resize(); brandRU.resize(); brandMX.resize(); riskDetail.resize();
});
</script>
</body>
</html>"""
    return html


if __name__ == "__main__":
    html_content = generate_html()
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "dashboard.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Dashboard generated: " + output_path)
    
    from src.analysis.market_data import get_all_data
    data = get_all_data()
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "processed", "global_auto_market_data.json")
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Data saved: " + data_path)
