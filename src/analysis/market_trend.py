"""
市场趋势分析模块 - 汽车市场数据分析与趋势预测
"""
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class MarketInsight:
    """市场洞察"""
    brand: str
    model: str
    avg_price: Optional[float] = None
    price_trend: Optional[str] = None    # "up" / "down" / "stable"
    supply_volume: Optional[int] = None
    demand_indicator: Optional[str] = None
    region: Optional[str] = None
    confidence: float = 0.0


class MarketTrendAnalyzer:
    """市场趋势分析器"""

    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.logger = logging.getLogger(self.__class__.__name__)

    def analyze_price_distribution(self, data: list[dict]) -> dict:
        """分析价格分布"""
        import statistics
        
        prices = [d.get("price") for d in data if d.get("price")]
        if not prices:
            return {"error": "No price data available"}

        return {
            "count": len(prices),
            "mean": statistics.mean(prices),
            "median": statistics.median(prices),
            "stdev": statistics.stdev(prices) if len(prices) > 1 else 0,
            "min": min(prices),
            "max": max(prices),
            "q25": sorted(prices)[len(prices) // 4],
            "q75": sorted(prices)[3 * len(prices) // 4],
        }

    def analyze_by_brand(self, data: list[dict]) -> dict[str, list]:
        """按品牌分组分析"""
        brands = {}
        for item in data:
            brand = item.get("brand", "Unknown")
            if brand not in brands:
                brands[brand] = []
            brands[brand].append(item)
        return brands

    def detect_price_anomalies(self, data: list[dict], threshold: float = 2.0) -> list[dict]:
        """检测价格异常值（Z-score方法）"""
        import math
        
        prices = [d.get("price", 0) for d in data if d.get("price")]
        if len(prices) < 3:
            return []

        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        std = math.sqrt(variance)

        if std == 0:
            return []

        anomalies = []
        for item in data:
            price = item.get("price", 0)
            if price and abs((price - mean) / std) > threshold:
                anomalies.append({**item, "z_score": (price - mean) / std})
        
        return anomalies

    async def generate_insight(self, data: list[dict], context: str = "") -> str:
        """使用LLM生成市场洞察报告"""
        if self.llm is None:
            return self._generate_basic_insight(data)
        
        prompt = f"""基于以下汽车市场数据生成分析洞察：

数据摘要: {self.analyze_price_distribution(data)}
上下文: {context}

请分析：
1. 价格趋势
2. 供需关系
3. 值得关注的市场信号
4. 供应链影响"""
        
        return await self.llm.analyze(prompt)

    def _generate_basic_insight(self, data: list[dict]) -> str:
        """基础洞察（无LLM时的降级方案）"""
        stats = self.analyze_price_distribution(data)
        if "error" in stats:
            return "数据不足，无法生成洞察"
        
        brands = self.analyze_by_brand(data)
        return (
            f"数据概览: 共 {stats['count']} 条记录\n"
            f"均价: €{stats['mean']:.0f} | 中位数: €{stats['median']:.0f}\n"
            f"价格区间: €{stats['min']:.0f} - €{stats['max']:.0f}\n"
            f"品牌分布: {', '.join(f'{k}({len(v)})' for k, v in sorted(brands.items(), key=lambda x: -len(x[1]))[:10])}"
        )
