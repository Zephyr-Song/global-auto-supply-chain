"""
市场 KPI 引擎 — 全球汽车出口市场机会量化评估
============================================
借鉴 ChainCommand kpi/engine.py，适配全球汽车出口场景

6大KPI:
  1. 市场机会指数 (Market Opportunity Index)
  2. 中国品牌渗透率 (China Brand Penetration)
  3. EV竞争力 (EV Competitiveness)
  4. 供应链韧性 (Supply Chain Resilience)
  5. 贸易开放度 (Trade Openness)
  6. 物流效率 (Logistics Efficiency)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import settings

log = __import__("logging").getLogger(__name__)

# 允许查询的KPI指标名
ALLOWED_KPI_METRICS: frozenset[str] = frozenset({
    "market_opportunity_index",
    "china_brand_penetration",
    "ev_competitiveness",
    "supply_chain_resilience",
    "trade_openness",
    "logistics_efficiency",
})


@dataclass
class MarketKPISnapshot:
    """市场KPI快照 — 单个时间点"""
    timestamp: datetime = None
    country_id: str = ""
    country_cn: str = ""

    # 6大KPI
    market_opportunity_index: float = 0.0   # 市场机会指数 0-1
    china_brand_penetration: float = 0.0    # 中国品牌渗透率 0-1
    ev_competitiveness: float = 0.0         # EV竞争力 0-1
    supply_chain_resilience: float = 0.0    # 供应链韧性 0-1
    trade_openness: float = 0.0             # 贸易开放度 0-1
    logistics_efficiency: float = 0.0       # 物流效率 0-1

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class KPIAlert:
    """KPI阈值告警"""
    metric: str
    value: float
    threshold: float
    severity: str   # "info", "warning", "critical"
    message: str


class MarketKPIEngine:
    """市场KPI计算引擎

    每个KPI有明确的计算公式和数据来源:
      market_opportunity_index = market_size_factor × (1 - tariff) × (1 - risk)
      china_brand_penetration  = china_brand_sales / total_sales
      ev_competitiveness       = ev_penetration × china_brand_ev_share
      supply_chain_resilience  = 1 - weighted_risk_score
      trade_openness           = 1 - (tariff_rate + non_tariff_barriers) / 2
      logistics_efficiency     = 1 - normalized_logistics_days
    """

    # 归一化参考值（用于跨国有可比性）
    MAX_MARKET_SIZE = 12_000_000   # 最大单国年销量（万辆级参考）
    MAX_LOGISTICS_DAYS = 60        # 最长物流周期参考值

    def calculate_snapshot(
        self,
        country_id: str,
        country_cn: str,
        market_size: float,
        tariff_rate: float = 0.0,
        non_tariff_barriers: float = 0.0,
        risk_score: float = 0.0,
        china_brand_share: float = 0.0,
        ev_penetration: float = 0.0,
        china_brand_ev_share: float = 0.0,
        logistics_days: float = 30.0,
    ) -> MarketKPISnapshot:
        """计算单个国家的市场KPI快照"""

        # 1. 市场机会指数 = 规模因子 × (1-关税) × (1-风险)
        size_factor = min(1.0, market_size / self.MAX_MARKET_SIZE) if self.MAX_MARKET_SIZE > 0 else 0
        market_opportunity_index = size_factor * (1 - self._clamp(tariff_rate)) * (1 - self._clamp(risk_score))

        # 2. 中国品牌渗透率
        china_brand_penetration = self._clamp(china_brand_share)

        # 3. EV竞争力 = EV渗透率 × 中国品牌EV份额
        ev_competitiveness = self._clamp(ev_penetration) * self._clamp(china_brand_ev_share)

        # 4. 供应链韧性 = 1 - 加权风险评分
        supply_chain_resilience = 1 - self._clamp(risk_score)

        # 5. 贸易开放度 = 1 - (关税 + 非关税壁垒)/2
        trade_openness = 1 - (self._clamp(tariff_rate) + self._clamp(non_tariff_barriers)) / 2

        # 6. 物流效率 = 1 - 归一化物流周期
        logistics_efficiency = 1 - min(1.0, max(0.0, logistics_days / self.MAX_LOGISTICS_DAYS))

        return MarketKPISnapshot(
            country_id=country_id,
            country_cn=country_cn,
            market_opportunity_index=round(market_opportunity_index, 4),
            china_brand_penetration=round(china_brand_penetration, 4),
            ev_competitiveness=round(ev_competitiveness, 4),
            supply_chain_resilience=round(supply_chain_resilience, 4),
            trade_openness=round(trade_openness, 4),
            logistics_efficiency=round(logistics_efficiency, 4),
        )

    def calculate_all(
        self,
        countries_data: List[Dict[str, Any]],
    ) -> List[MarketKPISnapshot]:
        """批量计算多国KPI"""
        snapshots = []
        for c in countries_data:
            snapshot = self.calculate_snapshot(
                country_id=c["country_id"],
                country_cn=c.get("country_cn", ""),
                market_size=c.get("market_size", 0),
                tariff_rate=c.get("tariff_rate", 0),
                non_tariff_barriers=c.get("non_tariff_barriers", 0),
                risk_score=c.get("risk_score", 0),
                china_brand_share=c.get("china_brand_share", 0),
                ev_penetration=c.get("ev_penetration", 0),
                china_brand_ev_share=c.get("china_brand_ev_share", 0),
                logistics_days=c.get("logistics_days", 30),
            )
            snapshots.append(snapshot)
        return snapshots

    def check_thresholds(self, snapshot: MarketKPISnapshot) -> List[KPIAlert]:
        """检查KPI是否超过阈值，返回告警列表"""
        alerts: List[KPIAlert] = []

        if snapshot.market_opportunity_index >= settings.kpi_opportunity_high:
            alerts.append(KPIAlert(
                metric="market_opportunity_index",
                value=snapshot.market_opportunity_index,
                threshold=settings.kpi_opportunity_high,
                severity="info",
                message=f"{snapshot.country_cn} 市场机会指数 {snapshot.market_opportunity_index:.1%} ≥ 高机会阈值 {settings.kpi_opportunity_high:.0%}",
            ))
        elif snapshot.market_opportunity_index < settings.kpi_opportunity_medium:
            alerts.append(KPIAlert(
                metric="market_opportunity_index",
                value=snapshot.market_opportunity_index,
                threshold=settings.kpi_opportunity_medium,
                severity="warning",
                message=f"{snapshot.country_cn} 市场机会指数 {snapshot.market_opportunity_index:.1%} < 中等阈值 {settings.kpi_opportunity_medium:.0%}，机会有限",
            ))

        if snapshot.supply_chain_resilience < settings.kpi_resilience_critical:
            alerts.append(KPIAlert(
                metric="supply_chain_resilience",
                value=snapshot.supply_chain_resilience,
                threshold=settings.kpi_resilience_critical,
                severity="critical",
                message=f"{snapshot.country_cn} 供应链韧性 {snapshot.supply_chain_resilience:.1%} < 危险阈值 {settings.kpi_resilience_critical:.0%}，强烈建议减少暴露",
            ))
        elif snapshot.supply_chain_resilience < settings.kpi_resilience_low:
            alerts.append(KPIAlert(
                metric="supply_chain_resilience",
                value=snapshot.supply_chain_resilience,
                threshold=settings.kpi_resilience_low,
                severity="warning",
                message=f"{snapshot.country_cn} 供应链韧性 {snapshot.supply_chain_resilience:.1%} < 低韧性阈值，需关注风险",
            ))

        if snapshot.china_brand_penetration >= settings.kpi_penetration_high:
            alerts.append(KPIAlert(
                metric="china_brand_penetration",
                value=snapshot.china_brand_penetration,
                threshold=settings.kpi_penetration_high,
                severity="info",
                message=f"{snapshot.country_cn} 中国品牌渗透率 {snapshot.china_brand_penetration:.1%} ≥ 高渗透阈值，市场地位稳固",
            ))
        elif snapshot.china_brand_penetration < settings.kpi_penetration_medium:
            alerts.append(KPIAlert(
                metric="china_brand_penetration",
                value=snapshot.china_brand_penetration,
                threshold=settings.kpi_penetration_medium,
                severity="info",
                message=f"{snapshot.country_cn} 中国品牌渗透率 {snapshot.china_brand_penetration:.1%} < {settings.kpi_penetration_medium:.0%}，增长空间大",
            ))

        return alerts

    def rank_by_opportunity(
        self, snapshots: List[MarketKPISnapshot]
    ) -> List[MarketKPISnapshot]:
        """按市场机会指数排序（降序）"""
        return sorted(snapshots, key=lambda s: -s.market_opportunity_index)

    @staticmethod
    def _clamp(v: float) -> float:
        return max(0.0, min(1.0, v))
