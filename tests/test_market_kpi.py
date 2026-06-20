"""Tests for the market KPI engine."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.analysis.market_kpi import MarketKPIEngine, MarketKPISnapshot, KPIAlert


class TestMarketKPIEngine:
    """市场KPI引擎测试"""

    def setup_method(self):
        self.engine = MarketKPIEngine()

    def test_market_opportunity_index_formula(self):
        """市场机会指数 = 规模因子 × (1-关税) × (1-风险)"""
        snapshot = self.engine.calculate_snapshot(
            country_id="Test",
            country_cn="测试",
            market_size=1_000_000,
            tariff_rate=0.2,
            risk_score=0.3,
        )
        # size_factor = 1_000_000 / 12_000_000 ≈ 0.0833
        # opportunity = 0.0833 × 0.8 × 0.7 ≈ 0.0467
        assert 0 < snapshot.market_opportunity_index < 1
        assert snapshot.market_opportunity_index < 0.1

    def test_large_market_high_opportunity(self):
        """大市场+低关税+低风险 → 高机会指数"""
        snapshot = self.engine.calculate_snapshot(
            country_id="BigMarket",
            country_cn="大市场",
            market_size=6_000_000,
            tariff_rate=0.05,
            risk_score=0.15,
        )
        assert snapshot.market_opportunity_index > 0.3

    def test_small_market_low_opportunity(self):
        """小市场+高关税+高风险 → 低机会指数"""
        snapshot = self.engine.calculate_snapshot(
            country_id="SmallMarket",
            country_cn="小市场",
            market_size=100_000,
            tariff_rate=0.5,
            risk_score=0.7,
        )
        assert snapshot.market_opportunity_index < 0.05

    def test_supply_chain_resilience_inverse_risk(self):
        """供应链韧性 = 1 - 风险评分"""
        snapshot = self.engine.calculate_snapshot(
            country_id="Test",
            country_cn="测试",
            market_size=500_000,
            risk_score=0.35,
        )
        assert abs(snapshot.supply_chain_resilience - 0.65) < 0.01

    def test_trade_openness_formula(self):
        """贸易开放度 = 1 - (关税 + 非关税壁垒)/2"""
        snapshot = self.engine.calculate_snapshot(
            country_id="Test",
            country_cn="测试",
            market_size=500_000,
            tariff_rate=0.3,
            non_tariff_barriers=0.2,
        )
        # openness = 1 - (0.3 + 0.2)/2 = 1 - 0.25 = 0.75
        assert abs(snapshot.trade_openness - 0.75) < 0.01

    def test_ev_competitiveness(self):
        """EV竞争力 = EV渗透率 × 中国品牌EV份额"""
        snapshot = self.engine.calculate_snapshot(
            country_id="Test",
            country_cn="测试",
            market_size=500_000,
            ev_penetration=0.3,
            china_brand_ev_share=0.2,
        )
        assert abs(snapshot.ev_competitiveness - 0.06) < 0.01

    def test_logistics_efficiency(self):
        """物流效率 = 1 - 归一化物流周期"""
        snapshot = self.engine.calculate_snapshot(
            country_id="Test",
            country_cn="测试",
            market_size=500_000,
            logistics_days=15,
        )
        # efficiency = 1 - 15/60 = 0.75
        assert abs(snapshot.logistics_efficiency - 0.75) < 0.01

    def test_threshold_alerts(self):
        """低韧性应触发告警"""
        snapshot = self.engine.calculate_snapshot(
            country_id="RiskyCountry",
            country_cn="高风险国",
            market_size=500_000,
            risk_score=0.85,  # 韧性 = 0.15 < 0.3
        )
        alerts = self.engine.check_thresholds(snapshot)
        risk_alerts = [a for a in alerts if a.metric == "supply_chain_resilience"]
        assert len(risk_alerts) > 0
        assert risk_alerts[0].severity in ("warning", "critical")

    def test_high_opportunity_alert(self):
        """高机会指数应触发正向告警"""
        snapshot = self.engine.calculate_snapshot(
            country_id="GreatMarket",
            country_cn="优质市场",
            market_size=10_000_000,  # 超大市场
            tariff_rate=0.02,
            risk_score=0.05,
        )
        alerts = self.engine.check_thresholds(snapshot)
        opp_alerts = [a for a in alerts if a.metric == "market_opportunity_index"]
        assert len(opp_alerts) > 0

    def test_rank_by_opportunity(self):
        """排序应按机会指数降序"""
        snapshots = [
            self.engine.calculate_snapshot("Low", "低", market_size=100_000, tariff_rate=0.4, risk_score=0.5),
            self.engine.calculate_snapshot("High", "高", market_size=5_000_000, tariff_rate=0.05, risk_score=0.1),
            self.engine.calculate_snapshot("Mid", "中", market_size=1_000_000, tariff_rate=0.2, risk_score=0.3),
        ]
        ranked = self.engine.rank_by_opportunity(snapshots)
        assert ranked[0].country_id == "High"
        assert ranked[-1].country_id == "Low"

    def test_calculate_all(self):
        """批量计算应返回正确数量"""
        countries = [
            {"country_id": "A", "country_cn": "国A", "market_size": 500_000, "tariff_rate": 0.1},
            {"country_id": "B", "country_cn": "国B", "market_size": 800_000, "tariff_rate": 0.2},
        ]
        snapshots = self.engine.calculate_all(countries)
        assert len(snapshots) == 2
