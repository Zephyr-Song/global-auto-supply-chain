"""
量化风险评分模块 — 基于规则+ML混合的多因子国家风险评估
======================================================
借鉴 ChainCommand risk/scorer.py，适配全球汽车出口场景
替代原 supply_chain_risk.py 的 LLM 定性方案

5大因子:
  1. 地缘风险 (25%) — 制裁/冲突/政策不确定性
  2. 供应中断 (20%) — 进口依赖度/产能波动
  3. 关税风险 (25%) — 进口关税/非关税壁垒
  4. 物流风险 (15%) — 距离/周期/运输可靠性
  5. 法规风险 (15%) — EV政策/本地化率/环保标准
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

try:
    from ..config import settings
except ImportError:
    from config import settings

log = logging.getLogger(__name__)

try:
    from sklearn.ensemble import RandomForestClassifier  # noqa: F401
    HAS_SKLEARN = True
except Exception:
    HAS_SKLEARN = False


# ── Data Models ──────────────────────────────────────────────

@dataclass
class CountryRiskMetrics:
    """国家风险输入指标 — 每个因子 0-1，越高越危险"""
    country_id: str
    country_cn: str = ""

    # 5大因子
    geopolitical_risk: float = 0.3        # 0-1, 地缘政治风险
    supply_disruption_risk: float = 0.3   # 0-1, 供应中断风险
    tariff_risk: float = 0.2              # 0-1, 关税壁垒风险
    logistics_risk: float = 0.3           # 0-1, 物流风险
    regulatory_risk: float = 0.2          # 0-1, 法规风险

    # 补充信息（用于建议生成）
    tariff_rate: Optional[float] = None          # 实际关税率
    localization_requirement: Optional[float] = None  # 本地化率要求
    ev_incentive_level: Optional[float] = None    # EV补贴力度 0-1
    import_dependency: Optional[float] = None     # 进口依赖度 0-1
    logistics_days: Optional[int] = None          # 物流周期（天）


@dataclass
class CountryRiskScore:
    """国家风险评分输出"""
    country_id: str
    country_cn: str = ""
    overall_score: float = 0.0             # 0-1, 加权综合评分
    risk_level: str = "low"                # low/medium/high/critical
    factor_breakdown: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    # ML 补充（可选）
    ml_risk_probability: Optional[float] = None


# ── Risk Scorer ──────────────────────────────────────────────

class CountryRiskScorer:
    """多因子国家风险评分器

    核心逻辑:
      composite = Σ(weight_i × factor_i)
      risk_level = _classify(composite)

    可选 ML 混合:
      final = (1 - blend) × composite + blend × ml_predict
    """

    DEFAULT_WEIGHTS = {
        "geopolitical": 0.25,
        "supply_disruption": 0.20,
        "tariff": 0.25,
        "logistics": 0.15,
        "regulatory": 0.15,
    }

    FACTOR_KEYS = [
        "geopolitical", "supply_disruption", "tariff", "logistics", "regulatory"
    ]

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self._weights = weights or settings.risk_weights or self.DEFAULT_WEIGHTS
        self._ml_model: Optional[RandomForestClassifier] = None
        self._ml_trained = False

    def score_country(self, metrics: CountryRiskMetrics) -> CountryRiskScore:
        """计算单个国家的量化风险评分"""
        factors = {
            "geopolitical": self._clamp(metrics.geopolitical_risk),
            "supply_disruption": self._clamp(metrics.supply_disruption_risk),
            "tariff": self._clamp(metrics.tariff_risk),
            "logistics": self._clamp(metrics.logistics_risk),
            "regulatory": self._clamp(metrics.regulatory_risk),
        }

        # 加权综合评分
        composite = sum(
            self._weights.get(k, 0.2) * v for k, v in factors.items()
        )

        # ML 混合（如果已训练）
        ml_prob = None
        if self._ml_trained and self._ml_model is not None:
            ml_prob = self._ml_predict(metrics)
            blend = settings.risk_ml_blend_ratio
            composite = (1 - blend) * composite + blend * ml_prob

        composite = self._clamp(composite)
        risk_level = self._classify(composite)
        recommendations = self._generate_recommendations(metrics, factors)

        return CountryRiskScore(
            country_id=metrics.country_id,
            country_cn=metrics.country_cn,
            overall_score=round(composite, 4),
            risk_level=risk_level,
            factor_breakdown={k: round(v, 4) for k, v in factors.items()},
            recommendations=recommendations,
            ml_risk_probability=round(ml_prob, 4) if ml_prob is not None else None,
        )

    def score_all(self, countries: List[CountryRiskMetrics]) -> List[CountryRiskScore]:
        """批量评分，按风险从高到低排序"""
        scores = [self.score_country(c) for c in countries]
        scores.sort(key=lambda s: -s.overall_score)
        return scores

    # ── ML Training ──────────────────────────────────────────

    def train_ml_model(self, historical_data: List[Dict], seed: int = 42) -> float:
        """训练 ML 风险模型（需历史数据 + disrupted 标签）"""
        if not HAS_SKLEARN or len(historical_data) < 20:
            reason = "sklearn_unavailable" if not HAS_SKLEARN else "insufficient_data"
            log.info("ml_risk_skipped", reason=reason)
            return 0.0

        X, y = [], []
        for record in historical_data:
            features = [
                record.get("geopolitical_risk", 0.3),
                record.get("supply_disruption_risk", 0.3),
                record.get("tariff_risk", 0.2),
                record.get("logistics_risk", 0.3),
                record.get("regulatory_risk", 0.2),
            ]
            X.append(features)
            y.append(1 if record.get("disrupted", False) else 0)

        X, y = np.array(X), np.array(y)
        unique_classes, class_counts = np.unique(y, return_counts=True)

        if len(unique_classes) < 2:
            log.info("ml_risk_skipped", reason="single_class")
            return 0.0

        from sklearn.model_selection import train_test_split
        use_stratify = int(class_counts.min()) >= 2

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=seed,
            stratify=y if use_stratify else None,
        )

        self._ml_model = RandomForestClassifier(
            n_estimators=50, max_depth=5, random_state=seed
        )
        self._ml_model.fit(X_train, y_train)
        self._ml_trained = True

        accuracy = float(self._ml_model.score(X_test, y_test))
        log.info("ml_risk_trained", accuracy=accuracy, samples=len(y))
        return accuracy

    # ── 内部方法 ─────────────────────────────────────────────

    @staticmethod
    def _clamp(v: float) -> float:
        return max(0.0, min(1.0, v))

    @staticmethod
    def _classify(score: float) -> str:
        if score >= 0.75:
            return "critical"
        if score >= 0.50:
            return "high"
        if score >= 0.25:
            return "medium"
        return "low"

    def _ml_predict(self, metrics: CountryRiskMetrics) -> float:
        if not self._ml_model:
            return 0.5
        features = np.array([[[
            metrics.geopolitical_risk,
            metrics.supply_disruption_risk,
            metrics.tariff_risk,
            metrics.logistics_risk,
            metrics.regulatory_risk,
        ]]])
        prob = self._ml_model.predict_proba(features[0])[0]
        if len(prob) < 2:
            return 0.5
        classes = list(self._ml_model.classes_)
        return float(prob[classes.index(1)]) if 1 in classes else float(prob[-1])

    @staticmethod
    def _generate_recommendations(
        metrics: CountryRiskMetrics, factors: Dict[str, float]
    ) -> List[str]:
        recs = []

        if factors["geopolitical"] > 0.6:
            recs.append(
                f"地缘风险偏高({factors['geopolitical']:.0%})，"
                "建议降低该国出口占比或采用CKD本地化方案"
            )
        if factors["tariff"] > 0.5:
            strategy = "CKD组装" if (metrics.localization_requirement or 0) > 0.3 else "期货对冲"
            recs.append(
                f"关税壁垒较高({factors['tariff']:.0%})，"
                f"建议评估{strategy}以规避整车进口关税"
            )
        if factors["supply_disruption"] > 0.5:
            recs.append(
                f"供应中断风险({factors['supply_disruption']:.0%})，"
                "建议建立多供应商备份或增加安全库存"
            )
        if factors["logistics"] > 0.6:
            recs.append(
                f"物流风险偏高({factors['logistics']:.0%})，"
                "建议增加安全库存或寻找近岸替代方案"
            )
        if factors["regulatory"] > 0.5:
            recs.append(
                f"法规风险({factors['regulatory']:.0%})，"
                "建议关注本地化率要求及EV政策变化"
            )
        if metrics.localization_requirement and metrics.localization_requirement > 0.35:
            recs.append(
                f"本地化率要求{metrics.localization_requirement:.0%}，"
                "CKD组装方案可降低关税并满足合规"
            )

        return recs
