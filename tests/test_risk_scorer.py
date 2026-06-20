"""Tests for the quantitative risk scorer."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.analysis.risk_scorer import CountryRiskScorer, CountryRiskMetrics, CountryRiskScore


class TestCountryRiskScorer:
    """量化风险评分测试"""

    def setup_method(self):
        self.scorer = CountryRiskScorer()

    def test_deterministic_scoring(self):
        """相同输入 → 相同输出（不像LLM随机）"""
        metrics = CountryRiskMetrics(
            country_id="Brazil",
            geopolitical_risk=0.2,
            supply_disruption_risk=0.3,
            tariff_risk=0.35,
            logistics_risk=0.4,
            regulatory_risk=0.25,
        )
        score1 = self.scorer.score_country(metrics)
        score2 = self.scorer.score_country(metrics)
        assert score1.overall_score == score2.overall_score

    def test_high_geopolitical_risk_classified_high(self):
        """地缘风险 > 0.7 → 总风险至少 medium"""
        metrics = CountryRiskMetrics(
            country_id="Russia",
            geopolitical_risk=0.82,
            supply_disruption_risk=0.5,
            tariff_risk=0.4,
            logistics_risk=0.5,
            regulatory_risk=0.4,
        )
        score = self.scorer.score_country(metrics)
        assert score.risk_level in ("medium", "high", "critical")

    def test_low_risk_classified_low(self):
        """所有因子低 → 低风险"""
        metrics = CountryRiskMetrics(
            country_id="Malaysia",
            geopolitical_risk=0.1,
            supply_disruption_risk=0.15,
            tariff_risk=0.1,
            logistics_risk=0.2,
            regulatory_risk=0.15,
        )
        score = self.scorer.score_country(metrics)
        assert score.risk_level == "low"

    def test_critical_risk_classification(self):
        """所有因子都很高 → critical"""
        metrics = CountryRiskMetrics(
            country_id="TestHigh",
            geopolitical_risk=0.9,
            supply_disruption_risk=0.85,
            tariff_risk=0.8,
            logistics_risk=0.7,
            regulatory_risk=0.75,
        )
        score = self.scorer.score_country(metrics)
        assert score.risk_level == "critical"
        assert score.overall_score >= 0.75

    def test_factor_breakdown_has_5_keys(self):
        """因子拆解应包含5个因子"""
        metrics = CountryRiskMetrics(country_id="Test")
        score = self.scorer.score_country(metrics)
        assert len(score.factor_breakdown) == 5
        assert "geopolitical" in score.factor_breakdown
        assert "tariff" in score.factor_breakdown

    def test_high_tariff_generates_recommendation(self):
        """高关税应触发CKD建议"""
        metrics = CountryRiskMetrics(
            country_id="Brazil",
            tariff_risk=0.6,
            localization_requirement=0.4,
        )
        score = self.scorer.score_country(metrics)
        recs_text = " ".join(score.recommendations)
        assert "CKD" in recs_text or "关税" in recs_text

    def test_score_all_sorted_by_risk(self):
        """批量评分应按风险从高到低排序"""
        countries = [
            CountryRiskMetrics(country_id="Low", geopolitical_risk=0.1, tariff_risk=0.1),
            CountryRiskMetrics(country_id="High", geopolitical_risk=0.8, tariff_risk=0.7),
            CountryRiskMetrics(country_id="Med", geopolitical_risk=0.4, tariff_risk=0.3),
        ]
        scores = self.scorer.score_all(countries)
        assert scores[0].country_id == "High"
        assert scores[-1].country_id == "Low"

    def test_custom_weights(self):
        """自定义权重应生效"""
        scorer = CountryRiskScorer(weights={
            "geopolitical": 0.5,  # 地缘权重加倍
            "supply_disruption": 0.1,
            "tariff": 0.15,
            "logistics": 0.1,
            "regulatory": 0.15,
        })
        metrics = CountryRiskMetrics(
            country_id="Test",
            geopolitical_risk=0.8,
            tariff_risk=0.1,
        )
        score = scorer.score_country(metrics)
        # 高地缘风险 + 高地缘权重 → 总分应偏高
        assert score.overall_score > 0.3

    def test_scores_clamped_to_0_1(self):
        """评分应在 0-1 范围内"""
        metrics = CountryRiskMetrics(
            country_id="Test",
            geopolitical_risk=1.5,  # 超出范围
            tariff_risk=-0.5,       # 负值
        )
        score = self.scorer.score_country(metrics)
        assert 0.0 <= score.overall_score <= 1.0
