"""
市场分配优化器 — CP-SAT MILP 中国汽车出口最优分配
==================================================
借鉴 ChainCommand optimization/cpsat_optimizer.py

数学模型:
  决策变量: x_i = 分配给国家 i 的出口量, y_i = 是否进入国家 i

  目标: max Σ(revenue_i × x_i) - λ × Σ(risk_i × x_i)

  约束:
    C1: Σ x_i ≤ total_export_capacity           (总出口产能)
    C2: x_i ≤ market_capacity_i × max_share_i    (单国容量上限)
    C3: x_i ≤ market_capacity_i × (1 - risk_i)   (风险约束)
    C4: x_i ≥ min_commitment_i × y_i              (最小承诺量)
    C5: Σ y_i ≤ max_countries                     (最多进入N国)
    C6: logistics_days_i ≤ max_logistics_days     (物流约束)

  无 ortools 时降级为贪心启发式
"""

from __future__ import annotations

import time as _time
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from ..config import settings
except ImportError:
    from config import settings

log = __import__("logging").getLogger(__name__)


# ── Data Models ──────────────────────────────────────────────

class MarketCandidate(BaseModel):
    """候选出口目标国"""
    country_id: str
    country_cn: str = ""
    market_size: float = 100_000.0       # 年市场销量（辆）
    china_brand_share: float = 0.05       # 中国品牌现有份额 0-1
    tariff_rate: float = 0.1              # 进口关税率 0-1
    risk_score: float = 0.3               # 供应链风险评分 0-1
    logistics_days: int = 30              # 物流周期（天）
    max_share: float = 0.30               # 中国品牌份额上限（政策/市场约束）
    min_commitment: float = 0.0           # 最小承诺出口量（如果进入）
    unit_margin: float = 1.0              # 单车利润系数
    localization_requirement: float = 0.0  # 本地化率要求 0-1


class AllocationResult(BaseModel):
    """优化结果"""
    allocations: Dict[str, float] = Field(default_factory=dict)  # country_id → 建议出口量
    total_revenue: float = 0.0
    total_risk: float = 0.0
    objective_value: float = 0.0
    solver_status: str = "unknown"
    solve_time_ms: float = 0.0
    method: str = "cpsat"


class SensitivityResult(BaseModel):
    """敏感性分析结果 — λ扫描"""
    lambda_values: List[float] = Field(default_factory=list)
    revenues: List[float] = Field(default_factory=list)
    risks: List[float] = Field(default_factory=list)
    elbow_lambda: float = 0.0
    elbow_revenue: float = 0.0
    elbow_risk: float = 0.0


# ── CP-SAT Optimizer ────────────────────────────────────────

class MarketAllocator:
    """CP-SAT MILP 市场分配优化器

    目标: max Σ(revenue_i × x_i) - λ × Σ(risk_i × x_i)

    无 ortools 时降级为贪心启发式
    """

    def __init__(self) -> None:
        self._has_ortools = False
        try:
            from ortools.sat.python import cp_model  # noqa: F401
            self._has_ortools = True
        except ImportError:
            log.info("ortools_unavailable", fallback="greedy_heuristic")

    def optimize(
        self,
        candidates: List[MarketCandidate],
        total_export_capacity: Optional[float] = None,
        risk_lambda: Optional[float] = None,
        max_countries: Optional[int] = None,
        max_logistics_days: Optional[int] = None,
        time_limit_ms: Optional[int] = None,
    ) -> AllocationResult:
        """执行市场分配优化"""
        capacity = total_export_capacity or settings.optimizer_total_export_capacity
        lam = risk_lambda if risk_lambda is not None else settings.optimizer_risk_lambda
        max_c = max_countries if max_countries is not None else settings.optimizer_max_countries
        tl = time_limit_ms if time_limit_ms is not None else settings.optimizer_time_limit_ms

        if not candidates:
            log.warning("optimize_empty_candidates")
            return AllocationResult(solver_status="no_candidates")

        if self._has_ortools:
            return self._solve_cpsat(candidates, capacity, lam, max_c, max_logistics_days, tl)
        return self._solve_greedy(candidates, capacity, lam, max_c, max_logistics_days)

    def _solve_cpsat(
        self,
        candidates: List[MarketCandidate],
        total_capacity: float,
        risk_lambda: float,
        max_countries: int,
        max_logistics_days: Optional[int],
        time_limit_ms: int,
    ) -> AllocationResult:
        """CP-SAT 精确求解"""
        from ortools.sat.python import cp_model

        model = cp_model.CpModel()
        n = len(candidates)
        scale = 100  # 浮点→整数缩放

        # 决策变量
        x = [model.new_int_var(0, round(c.market_size * c.max_share * scale), f"x_{i}")
             for i, c in enumerate(candidates)]
        y = [model.new_bool_var(f"y_{i}") for i in range(n)]

        # C1: 总出口产能约束
        model.add(sum(x) <= round(total_capacity * scale))

        for i, c in enumerate(candidates):
            # x_i 与 y_i 关联: x_i <= capacity_i * y_i
            model.add(x[i] <= round(c.market_size * c.max_share * scale) * y[i])

            # 最小承诺量
            if c.min_commitment > 0:
                model.add(x[i] >= round(c.min_commitment * scale) * y[i])

            # 物流约束
            if max_logistics_days is not None and c.logistics_days > max_logistics_days:
                model.add(y[i] == 0)

        # C5: 最多进入国家数
        model.add(sum(y) <= max_countries)

        # 目标: max Σ(revenue_i × x_i) - λ × Σ(risk_i × x_i)
        # CP-SAT 只支持 min，所以取负
        revenue_terms = []
        risk_terms = []
        for i, c in enumerate(candidates):
            revenue_terms.append(round(c.unit_margin * (1 - c.tariff_rate) * 1000) * x[i])
            risk_terms.append(round(c.risk_score * risk_lambda * 1000) * x[i])

        model.minimize(sum(risk_terms) - sum(revenue_terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_ms / 1000.0

        t0 = _time.monotonic()
        status = solver.solve(model)
        solve_ms = (_time.monotonic() - t0) * 1000

        status_name = {
            cp_model.OPTIMAL: "optimal",
            cp_model.FEASIBLE: "feasible",
            cp_model.INFEASIBLE: "infeasible",
            cp_model.MODEL_INVALID: "invalid",
        }.get(status, "unknown")

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            allocations = {}
            total_revenue = 0.0
            total_risk = 0.0
            for i, c in enumerate(candidates):
                qty = solver.value(x[i]) / scale
                if qty > 0:
                    allocations[c.country_id] = round(qty, 0)
                    total_revenue += qty * c.unit_margin * (1 - c.tariff_rate)
                    total_risk += qty * c.risk_score

            return AllocationResult(
                allocations=allocations,
                total_revenue=round(total_revenue, 2),
                total_risk=round(total_risk, 4),
                objective_value=round(total_revenue - risk_lambda * total_risk, 2),
                solver_status=status_name,
                solve_time_ms=round(solve_ms, 1),
                method="cpsat",
            )

        log.warning("cpsat_infeasible", status=status_name)
        return AllocationResult(solver_status=status_name, solve_time_ms=round(solve_ms, 1))

    def _solve_greedy(
        self,
        candidates: List[MarketCandidate],
        total_capacity: float,
        risk_lambda: float,
        max_countries: int,
        max_logistics_days: Optional[int],
    ) -> AllocationResult:
        """贪心启发式降级方案"""
        filtered = candidates
        if max_logistics_days is not None:
            filtered = [c for c in candidates if c.logistics_days <= max_logistics_days]

        # 按 (收益 - λ×风险) 排序
        scored = sorted(
            filtered,
            key=lambda c: c.unit_margin * (1 - c.tariff_rate) - risk_lambda * c.risk_score,
            reverse=True,
        )

        allocations: Dict[str, float] = {}
        remaining = total_capacity
        total_revenue = 0.0
        total_risk = 0.0

        for c in scored[:max_countries]:
            if remaining <= 0:
                break

            max_qty = c.market_size * c.max_share
            qty = min(remaining, max_qty)

            if c.min_commitment > 0 and qty < c.min_commitment:
                continue  # 达不到最小承诺量，跳过

            allocations[c.country_id] = round(qty, 0)
            total_revenue += qty * c.unit_margin * (1 - c.tariff_rate)
            total_risk += qty * c.risk_score
            remaining -= qty

        solver_status = "greedy_partial" if remaining > 0 else "greedy_optimal"

        return AllocationResult(
            allocations=allocations,
            total_revenue=round(total_revenue, 2),
            total_risk=round(total_risk, 4),
            objective_value=round(total_revenue - risk_lambda * total_risk, 2),
            solver_status=solver_status,
            method="greedy",
        )

    def sensitivity_analysis(
        self,
        candidates: List[MarketCandidate],
        total_export_capacity: Optional[float] = None,
        steps: int = 11,
    ) -> SensitivityResult:
        """λ从0→1扫描，找收益-风险拐点

        λ=0: 纯利润最大化（激进策略）
        λ=1: 纯风险最小化（保守策略）
        拐点 → 推荐平衡策略
        """
        lambdas = [i / max(1, steps - 1) for i in range(steps)]
        revenues: List[float] = []
        risks: List[float] = []

        for lam in lambdas:
            result = self.optimize(candidates, total_export_capacity, risk_lambda=lam)
            revenues.append(result.total_revenue)
            risks.append(result.total_risk)

        # 拐点检测 — 综合二阶导数 + 百分比变化
        elbow_idx = 0
        if len(lambdas) >= 3:
            composite = [r - l * rk for r, rk, l in zip(revenues, risks, lambdas)]

            second_derivs = []
            for i in range(1, len(composite) - 1):
                d2 = composite[i + 1] - 2 * composite[i] + composite[i - 1]
                second_derivs.append(abs(d2))

            sd_max = max(second_derivs) if second_derivs else 1.0
            sd_norm = [v / sd_max if sd_max > 0 else 0.0 for v in second_derivs]

            pct_changes = []
            for i in range(1, len(composite) - 1):
                prev_delta = composite[i] - composite[i - 1]
                next_delta = composite[i + 1] - composite[i]
                denom = abs(prev_delta) if abs(prev_delta) > 1e-9 else 1e-9
                pct_changes.append(abs((next_delta - prev_delta) / denom))

            pc_max = max(pct_changes) if pct_changes else 1.0
            pc_norm = [v / pc_max if pc_max > 0 else 0.0 for v in pct_changes]

            combined = [0.5 * s + 0.5 * p for s, p in zip(sd_norm, pc_norm)]
            if combined:
                elbow_idx = combined.index(max(combined)) + 1

        return SensitivityResult(
            lambda_values=lambdas,
            revenues=revenues,
            risks=risks,
            elbow_lambda=lambdas[elbow_idx],
            elbow_revenue=revenues[elbow_idx],
            elbow_risk=risks[elbow_idx],
        )

    def compare_strategies(
        self,
        candidates: List[MarketCandidate],
        total_export_capacity: Optional[float] = None,
    ) -> Dict[str, AllocationResult]:
        """一键对比三种策略：激进/平衡/保守"""
        cap = total_export_capacity or settings.optimizer_total_export_capacity

        # 找拐点
        sens = self.sensitivity_analysis(candidates, cap)

        return {
            "aggressive": self.optimize(candidates, cap, risk_lambda=0.0),
            "balanced": self.optimize(candidates, cap, risk_lambda=sens.elbow_lambda),
            "conservative": self.optimize(candidates, cap, risk_lambda=1.0),
            "sensitivity": sens,
        }
