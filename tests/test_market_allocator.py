"""Tests for the CP-SAT market allocator."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.optimization.market_allocator import (
    MarketAllocator, MarketCandidate, AllocationResult, SensitivityResult,
)


class TestMarketAllocator:
    """市场分配优化器测试"""

    def setup_method(self):
        self.allocator = MarketAllocator()
        self.candidates = [
            MarketCandidate(
                country_id="Brazil", country_cn="巴西",
                market_size=2_480_000, china_brand_share=0.05,
                tariff_rate=0.35, risk_score=0.35, logistics_days=45,
                max_share=0.20, unit_margin=1.0,
            ),
            MarketCandidate(
                country_id="Malaysia", country_cn="马来西亚",
                market_size=790_000, china_brand_share=0.15,
                tariff_rate=0.05, risk_score=0.15, logistics_days=7,
                max_share=0.30, unit_margin=1.2,
            ),
            MarketCandidate(
                country_id="Russia", country_cn="俄罗斯",
                market_size=1_330_000, china_brand_share=0.50,
                tariff_rate=0.15, risk_score=0.82, logistics_days=25,
                max_share=0.60, unit_margin=0.8,
            ),
            MarketCandidate(
                country_id="Thailand", country_cn="泰国",
                market_size=620_000, china_brand_share=0.10,
                tariff_rate=0.10, risk_score=0.25, logistics_days=10,
                max_share=0.25, unit_margin=1.1,
            ),
        ]

    def test_optimize_returns_result(self):
        """优化应返回非空结果"""
        result = self.allocator.optimize(self.candidates, total_export_capacity=500_000)
        assert result.solver_status in ("optimal", "feasible", "greedy_optimal", "greedy_partial")
        assert len(result.allocations) > 0

    def test_high_risk_country_limited(self):
        """高风险国家（俄罗斯0.82）应被限制分配"""
        result = self.allocator.optimize(
            self.candidates,
            total_export_capacity=500_000,
            risk_lambda=0.5,
        )
        russia_alloc = result.allocations.get("Russia", 0)
        malaysia_alloc = result.allocations.get("Malaysia", 0)
        # 俄罗斯风险远高于马来西亚，高lambda时分配应更少
        assert russia_alloc < malaysia_alloc * 3  # 不应大幅超过

    def test_zero_lambda_ignores_risk(self):
        """λ=0（激进策略）时，高风险高利润国家可获更多分配"""
        result_aggressive = self.allocator.optimize(
            self.candidates, total_export_capacity=500_000, risk_lambda=0.0,
        )
        # 激进策略下，俄罗斯因份额上限高(0.6)且利润系数虽低但市场大，应有分配
        assert len(result_aggressive.allocations) > 0

    def test_max_countries_constraint(self):
        """最多进入国家数约束应生效"""
        result = self.allocator.optimize(
            self.candidates,
            total_export_capacity=500_000,
            max_countries=2,
        )
        assert len(result.allocations) <= 2

    def test_total_export_within_capacity(self):
        """总出口量不超过产能上限"""
        capacity = 300_000
        result = self.allocator.optimize(
            self.candidates, total_export_capacity=capacity,
        )
        total = sum(result.allocations.values())
        assert total <= capacity * 1.01  # 允许1%舍入误差

    def test_sensitivity_analysis(self):
        """敏感性分析应返回正确的lambda范围"""
        sens = self.allocator.sensitivity_analysis(
            self.candidates, total_export_capacity=500_000, steps=5,
        )
        assert len(sens.lambda_values) == 5
        assert sens.lambda_values[0] == 0.0
        assert sens.lambda_values[-1] == 1.0
        assert 0 <= sens.elbow_lambda <= 1

    def test_compare_strategies(self):
        """三种策略对比应返回4个结果"""
        strategies = self.allocator.compare_strategies(
            self.candidates, total_export_capacity=500_000,
        )
        assert "aggressive" in strategies
        assert "balanced" in strategies
        assert "conservative" in strategies
        assert "sensitivity" in strategies

    def test_empty_candidates(self):
        """空候选列表应返回 no_candidates"""
        result = self.allocator.optimize([], total_export_capacity=500_000)
        assert result.solver_status == "no_candidates"

    def test_logistics_constraint(self):
        """物流周期约束应排除远距离国家"""
        result = self.allocator.optimize(
            self.candidates,
            total_export_capacity=500_000,
            max_logistics_days=15,
        )
        # 巴西45天、俄罗斯25天 → 应被排除
        assert "Brazil" not in result.allocations
        assert "Russia" not in result.allocations
        assert "Malaysia" in result.allocations  # 7天
        assert "Thailand" in result.allocations  # 10天
