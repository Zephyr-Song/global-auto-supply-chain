"""
全球汽车供应链项目 — 统一配置管理
==================================
基于 Pydantic Settings，环境变量前缀 GASC_
运行时通过 .env 文件或环境变量覆盖默认值
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

_config_log = logging.getLogger(__name__)

_DEFAULT_API_KEY = "dev-key-change-me"


class Settings(BaseSettings):
    """Application-wide settings loaded from env / .env file."""

    model_config = {"env_file": ".env", "env_prefix": "GASC_"}

    # ── Environment ──────────────────────────────────────
    env: str = "development"

    # ── Crawler ──────────────────────────────────────────
    crawl_timeout_seconds: int = 30
    crawl_retry_count: int = 3
    use_stealthy_fetcher: bool = False

    # ── LLM ──────────────────────────────────────────────
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"

    # ── Risk Scorer ──────────────────────────────────────
    risk_weights: Dict[str, float] = Field(default={
        "geopolitical": 0.25,
        "supply_disruption": 0.20,
        "tariff": 0.25,
        "logistics": 0.15,
        "regulatory": 0.15,
    })
    risk_ml_blend_ratio: float = 0.3  # 30% ML + 70% rule-based

    # ── Market Allocator (CP-SAT) ────────────────────────
    optimizer_risk_lambda: float = 0.3
    optimizer_max_countries: int = 13
    optimizer_time_limit_ms: int = 10_000
    optimizer_total_export_capacity: float = 5_000_000  # 年出口产能上限（辆）

    # ── KPI Thresholds ───────────────────────────────────
    kpi_opportunity_high: float = 0.6
    kpi_opportunity_medium: float = 0.3
    kpi_resilience_critical: float = 0.15
    kpi_resilience_low: float = 0.3
    kpi_penetration_high: float = 0.15
    kpi_penetration_medium: float = 0.05

    # ── Logging ──────────────────────────────────────────
    log_level: str = "INFO"

    # ── Reproducibility ──────────────────────────────────
    random_seed: int = 42

    @field_validator("env", mode="before")
    @classmethod
    def _normalize_env(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("risk_weights", mode="before")
    @classmethod
    def _parse_risk_weights(cls, v: object) -> Dict[str, float]:
        """Accept JSON string from env var."""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v  # type: ignore[return-value]

    @model_validator(mode="after")
    def _validate_risk_weights(self) -> "Settings":
        """Ensure risk weights sum to ~1.0."""
        if self.risk_weights:
            total = sum(self.risk_weights.values())
            if abs(total - 1.0) > 0.05:
                _config_log.warning(
                    "risk_weights_sum_not_one",
                    weight_sum=total,
                    msg="Risk weights should sum to ~1.0; results may be unexpected",
                )
        return self


settings = Settings()
