"""Tests for the automotive BOM model."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.analysis.automotive_bom import (
    AutomotiveBOMAnalyzer, BOMItem, CountryBOMProfile,
    EntryMode, DEFAULT_BOM, DEFAULT_COUNTRY_PROFILES, EV_BOM_DIFF,
)


class TestBOMAnalyzer:
    """BOM分析引擎测试"""

    def setup_method(self):
        self.analyzer = AutomotiveBOMAnalyzer()

    def test_default_bom_cost_ratios_sum_near_one(self):
        """BOM各组件成本比例之和应接近1.0"""
        total = sum(item.cost_ratio for item in DEFAULT_BOM)
        assert abs(total - 1.0) < 0.10, f"BOM cost ratios sum to {total}"

    def test_ev_bom_cost_ratios_sum_near_one(self):
        """EV BOM替换后成本比例之和应接近1.0"""
        ev_replace_ids = {"engine", "transmission", "fuel_system", "exhaust"}
        ev_bom = [b for b in DEFAULT_BOM if b.item_id not in ev_replace_ids]
        ev_bom.extend(EV_BOM_DIFF.values())
        total = sum(item.cost_ratio for item in ev_bom)
        assert abs(total - 1.0) < 0.10, f"EV BOM cost ratios sum to {total}"

    def test_all_13_countries_have_profiles(self):
        """13国都应有BOM档案"""
        assert len(DEFAULT_COUNTRY_PROFILES) == 13

    def test_brazil_ckd_preferred(self):
        """巴西高关税+高本地化要求 → CKD最优"""
        result = self.analyzer.analyze("Brazil")
        assert result.recommended_mode in (EntryMode.CKD, EntryMode.SKD)
        assert result.tariff_savings > 0  # CBU关税35%远高于CKD

    def test_chile_cbu_preferred(self):
        """智利低关税+无本地化要求 → CBU最优"""
        result = self.analyzer.analyze("Chile")
        assert result.recommended_mode == EntryMode.CBU

    def test_localization_rate_between_0_and_1(self):
        """本地化率应在0-1之间"""
        for cid in DEFAULT_COUNTRY_PROFILES:
            result = self.analyzer.analyze(cid)
            assert 0 <= result.localization_rate <= 1.0, f"{cid}: {result.localization_rate}"

    def test_cost_index_positive(self):
        """成本指数应大于0"""
        for cid in DEFAULT_COUNTRY_PROFILES:
            result = self.analyzer.analyze(cid)
            assert result.total_cost_index > 0, f"{cid}: {result.total_cost_index}"

    def test_ev_lower_localization_than_ice(self):
        """EV本地化率应低于燃油车（电池难本地化）"""
        for cid in ["Brazil", "Thailand", "Malaysia"]:
            ice = self.analyzer.analyze(cid, is_ev=False)
            ev = self.analyzer.analyze(cid, is_ev=True)
            assert ev.localization_rate <= ice.localization_rate, \
                f"{cid}: EV({ev.localization_rate:.0%}) > ICE({ice.localization_rate:.0%})"

    def test_analyze_all_returns_13(self):
        """批量分析应返回13个结果"""
        results = self.analyzer.analyze_all()
        assert len(results) == 13

    def test_breakeven_years_reasonable(self):
        """回本年数应在合理范围，或inf（CBU最优无投资需求）"""
        for cid in DEFAULT_COUNTRY_PROFILES:
            result = self.analyzer.analyze(cid)
            if result.recommended_mode != EntryMode.CBU:
                assert result.breakeven_years < 30, f"{cid}: {result.breakeven_years:.1f} years"
            # CBU最优时breakeven=inf是合理的，不做限制

    def test_component_breakdown_has_items(self):
        """子系统本地化率明细非空"""
        result = self.analyzer.analyze("Thailand")
        assert len(result.component_breakdown) >= 10

    def test_recommendations_not_empty(self):
        """分析结果应有建议"""
        for cid in DEFAULT_COUNTRY_PROFILES:
            result = self.analyzer.analyze(cid)
            assert len(result.recommendations) > 0, f"{cid}: no recommendations"
