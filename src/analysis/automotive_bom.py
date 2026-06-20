"""
汽车BOM模型 — CKD/CBU本地化率分析
===================================
回答核心问题：在某国建厂/出口，需要多少本地采购？CKD vs CBU 哪个更划算？

BOM (Bill of Materials) 层级:
  Level 0: 整车 (Vehicle)
  Level 1: 动力总成 / 底盘 / 车身 / 电气 / 内饰 (5大系统)
  Level 2: 子系统 (如: 发动机/变速箱/电池包/MCU等)

关键概念:
  - CKD (Completely Knocked Down): 全散件组装，本地化率低(15-30%)
  - SKD (Semi Knocked Down): 半散件组装，本地化率中(25-40%)
  - CBU (Completely Built Up): 整车出口，本地化率0%
  - 本地化率: 某国法规要求的最低本地采购比例

计算模型:
  各国成本 = CBU关税成本 vs CKD/SKD(本地采购+CKD套件+组装成本)
  收益 = 本地化率达标后享受的关税减免 + 市场准入
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

try:
    from ..config import settings
except ImportError:
    from config import settings

log = logging.getLogger(__name__)


# ============================================================
# 数据结构
# ============================================================

class EntryMode(str, Enum):
    """市场进入模式"""
    CBU = "cbu"       # 整车出口
    SKD = "skd"       # 半散件组装
    CKD = "ckd"       # 全散件组装
    LOCAL = "local"   # 本地化生产


@dataclass
class BOMItem:
    """BOM物料项"""
    item_id: str          # 如 "engine", "battery_pack"
    name_cn: str          # 如 "发动机总成"
    name_en: str          # 如 "Engine Assembly"
    category: str         # Level 1: powertrain / chassis / body / electrical / interior
    cost_ratio: float     # 占整车成本比例 (0-1)
    localization_ease: float  # 本地化难易度 (0=极难, 1=容易)
    typical_suppliers: List[str] = field(default_factory=list)


@dataclass
class CountryBOMProfile:
    """某国的BOM合规档案"""
    country_id: str
    country_cn: str
    entry_mode: EntryMode
    required_localization: float    # 法规要求最低本地化率
    achievable_localization: float  # 当前可达成本地化率
    cbu_tariff: float               # CBU进口关税
    skd_tariff: float               # SKD进口关税
    ckd_tariff: float               # CKD进口关税
    assembly_cost_ratio: float      # 组装成本占整车比例
    local_sourcing: Dict[str, float] = field(default_factory=dict)  # 各子系统本地采购比例


@dataclass
class LocalizationAnalysis:
    """本地化率分析结果"""
    country_id: str
    country_cn: str
    recommended_mode: EntryMode
    total_cost_index: float        # 总成本指数 (CBU=1.0基准)
    localization_rate: float       # 实际本地化率
    tariff_savings: float          # 关税节省率
    breakeven_years: float         # 回本年数
    component_breakdown: Dict[str, float] = field(default_factory=dict)  # 各子系统本地化率
    recommendations: List[str] = field(default_factory=list)


# ============================================================
# 默认BOM数据 — 典型燃油车
# ============================================================

DEFAULT_BOM: List[BOMItem] = [
    # ── 动力总成 (powertrain) ──
    BOMItem("engine", "发动机总成", "Engine Assembly", "powertrain", 0.15, 0.2, ["自研", "三菱"]),
    BOMItem("transmission", "变速箱", "Transmission", "powertrain", 0.08, 0.15, ["自研", "格特拉克", "爱信"]),
    BOMItem("exhaust", "排气系统", "Exhaust System", "powertrain", 0.02, 0.7, ["佛吉亚", "天纳格"]),
    BOMItem("fuel_system", "燃油系统", "Fuel System", "powertrain", 0.02, 0.5, ["博世", "德尔福"]),
    # ── 底盘 (chassis) ──
    BOMItem("suspension", "悬挂系统", "Suspension", "chassis", 0.06, 0.6, ["本特勒", "采埃孚"]),
    BOMItem("brakes", "制动系统", "Brake System", "chassis", 0.04, 0.5, ["博世", "大陆"]),
    BOMItem("steering", "转向系统", "Steering", "chassis", 0.03, 0.4, ["博世", "NSK"]),
    BOMItem("wheels", "轮毂轮胎", "Wheels & Tires", "chassis", 0.03, 0.8, ["中信戴卡", "米其林"]),
    # ── 车身 (body) ──
    BOMItem("body_in_white", "白车身", "Body in White", "body", 0.12, 0.7, ["本地冲压"]),
    BOMItem("closures", "开闭件", "Closures", "body", 0.04, 0.7, ["本地冲压"]),
    BOMItem("glass", "玻璃", "Glass", "body", 0.02, 0.9, ["福耀"]),
    BOMItem("paint", "涂装", "Paint", "body", 0.03, 0.8, ["PPG", "巴斯夫"]),
    # ── 电气 (electrical) ──
    BOMItem("ecu", "电子控制单元", "ECU", "electrical", 0.05, 0.1, ["博世", "大陆", "联合电子"]),
    BOMItem("wiring", "线束", "Wiring Harness", "electrical", 0.03, 0.6, ["安波福", "住友"]),
    BOMItem("lighting", "车灯", "Lighting", "electrical", 0.02, 0.5, ["小糸", "马瑞利"]),
    BOMItem("hvac", "空调系统", "HVAC", "electrical", 0.03, 0.5, ["电装", "法雷奥"]),
    # ── 内饰 (interior) ──
    BOMItem("seats", "座椅", "Seats", "interior", 0.05, 0.8, ["延锋", "李尔"]),
    BOMItem("dashboard", "仪表台", "Dashboard", "interior", 0.04, 0.7, ["延锋", "佛吉亚"]),
    BOMItem("trim", "内饰件", "Interior Trim", "interior", 0.03, 0.9, ["本地供应商"]),
    BOMItem("infotainment", "车机系统", "Infotainment", "interior", 0.04, 0.3, ["德赛西威", "哈曼"]),
]

# EV 额外/替换组件
EV_BOM_DIFF: Dict[str, BOMItem] = {
    "battery_pack": BOMItem("battery_pack", "动力电池包", "Battery Pack", "powertrain", 0.30, 0.15, ["宁德时代", "比亚迪", "LG"]),
    "motor": BOMItem("motor", "驱动电机", "Drive Motor", "powertrain", 0.06, 0.2, ["汇川", "博世"]),
    "inverter": BOMItem("inverter", "逆变器", "Inverter", "powertrain", 0.03, 0.15, ["汇川", "博世"]),
    "mcu": BOMItem("mcu", "整车控制器", "MCU", "electrical", 0.02, 0.2, ["联合电子"]),
}

# 各国BOM合规档案（基于贸易壁垒数据+行业经验）
DEFAULT_COUNTRY_PROFILES: Dict[str, CountryBOMProfile] = {
    "Brazil": CountryBOMProfile(
        country_id="Brazil", country_cn="巴西",
        entry_mode=EntryMode.CKD, required_localization=0.50,
        achievable_localization=0.45, cbu_tariff=0.35, skd_tariff=0.20,
        ckd_tariff=0.08, assembly_cost_ratio=0.08,
        local_sourcing={"body_in_white": 0.8, "glass": 0.9, "seats": 0.8, "trim": 0.9, "paint": 0.7, "wiring": 0.5, "wheels": 0.7},
    ),
    "Mexico": CountryBOMProfile(
        country_id="Mexico", country_cn="墨西哥",
        entry_mode=EntryMode.CKD, required_localization=0.30,
        achievable_localization=0.55, cbu_tariff=0.15, skd_tariff=0.08,
        ckd_tariff=0.02, assembly_cost_ratio=0.07,
        local_sourcing={"body_in_white": 0.8, "glass": 0.9, "seats": 0.7, "trim": 0.8, "paint": 0.8, "wiring": 0.6, "wheels": 0.8, "exhaust": 0.7},
    ),
    "Russia": CountryBOMProfile(
        country_id="Russia", country_cn="俄罗斯",
        entry_mode=EntryMode.CBU, required_localization=0.00,  # 制裁下无本地化要求
        achievable_localization=0.20, cbu_tariff=0.15, skd_tariff=0.10,
        ckd_tariff=0.05, assembly_cost_ratio=0.09,
        local_sourcing={"seats": 0.5, "trim": 0.7, "glass": 0.6, "wheels": 0.5},
    ),
    "Thailand": CountryBOMProfile(
        country_id="Thailand", country_cn="泰国",
        entry_mode=EntryMode.CKD, required_localization=0.40,
        achievable_localization=0.50, cbu_tariff=0.40, skd_tariff=0.20,
        ckd_tariff=0.05, assembly_cost_ratio=0.06,
        local_sourcing={"body_in_white": 0.8, "glass": 0.9, "seats": 0.7, "trim": 0.8, "wiring": 0.5, "wheels": 0.7, "hvac": 0.6},
    ),
    "Indonesia": CountryBOMProfile(
        country_id="Indonesia", country_cn="印尼",
        entry_mode=EntryMode.CKD, required_localization=0.30,
        achievable_localization=0.40, cbu_tariff=0.40, skd_tariff=0.20,
        ckd_tariff=0.05, assembly_cost_ratio=0.07,
        local_sourcing={"body_in_white": 0.7, "glass": 0.8, "seats": 0.6, "trim": 0.8, "wiring": 0.4},
    ),
    "Malaysia": CountryBOMProfile(
        country_id="Malaysia", country_cn="马来西亚",
        entry_mode=EntryMode.CKD, required_localization=0.50,
        achievable_localization=0.45, cbu_tariff=0.30, skd_tariff=0.15,
        ckd_tariff=0.05, assembly_cost_ratio=0.06,
        local_sourcing={"body_in_white": 0.7, "glass": 0.8, "seats": 0.7, "trim": 0.8, "wiring": 0.5, "paint": 0.7},
    ),
    "Turkey": CountryBOMProfile(
        country_id="Turkey", country_cn="土耳其",
        entry_mode=EntryMode.CKD, required_localization=0.30,
        achievable_localization=0.50, cbu_tariff=0.30, skd_tariff=0.15,
        ckd_tariff=0.05, assembly_cost_ratio=0.07,
        local_sourcing={"body_in_white": 0.8, "glass": 0.9, "seats": 0.7, "trim": 0.8, "wiring": 0.5, "exhaust": 0.6},
    ),
    "SaudiArabia": CountryBOMProfile(
        country_id="SaudiArabia", country_cn="沙特",
        entry_mode=EntryMode.SKD, required_localization=0.20,
        achievable_localization=0.25, cbu_tariff=0.05, skd_tariff=0.03,
        ckd_tariff=0.00, assembly_cost_ratio=0.08,
        local_sourcing={"glass": 0.5, "trim": 0.5, "seats": 0.4},
    ),
    "SouthAfrica": CountryBOMProfile(
        country_id="SouthAfrica", country_cn="南非",
        entry_mode=EntryMode.CKD, required_localization=0.40,
        achievable_localization=0.40, cbu_tariff=0.25, skd_tariff=0.12,
        ckd_tariff=0.03, assembly_cost_ratio=0.09,
        local_sourcing={"body_in_white": 0.7, "glass": 0.8, "seats": 0.5, "trim": 0.7, "wiring": 0.4},
    ),
    "Chile": CountryBOMProfile(
        country_id="Chile", country_cn="智利",
        entry_mode=EntryMode.CBU, required_localization=0.00,
        achievable_localization=0.15, cbu_tariff=0.06, skd_tariff=0.03,
        ckd_tariff=0.00, assembly_cost_ratio=0.10,
        local_sourcing={"trim": 0.5, "glass": 0.4},
    ),
    "Peru": CountryBOMProfile(
        country_id="Peru", country_cn="秘鲁",
        entry_mode=EntryMode.CBU, required_localization=0.00,
        achievable_localization=0.10, cbu_tariff=0.06, skd_tariff=0.03,
        ckd_tariff=0.00, assembly_cost_ratio=0.10,
        local_sourcing={"trim": 0.3},
    ),
    "Kazakhstan": CountryBOMProfile(
        country_id="Kazakhstan", country_cn="哈萨克斯坦",
        entry_mode=EntryMode.SKD, required_localization=0.15,
        achievable_localization=0.20, cbu_tariff=0.15, skd_tariff=0.07,
        ckd_tariff=0.02, assembly_cost_ratio=0.08,
        local_sourcing={"trim": 0.5, "glass": 0.4, "seats": 0.3},
    ),
    "Pakistan": CountryBOMProfile(
        country_id="Pakistan", country_cn="巴基斯坦",
        entry_mode=EntryMode.CKD, required_localization=0.30,
        achievable_localization=0.35, cbu_tariff=0.35, skd_tariff=0.18,
        ckd_tariff=0.05, assembly_cost_ratio=0.08,
        local_sourcing={"body_in_white": 0.6, "glass": 0.7, "seats": 0.5, "trim": 0.7, "wiring": 0.4},
    ),
}


# ============================================================
# BOM分析引擎
# ============================================================

class AutomotiveBOMAnalyzer:
    """汽车BOM本地化率分析引擎"""

    def __init__(self, bom: Optional[List[BOMItem]] = None,
                 country_profiles: Optional[Dict[str, CountryBOMProfile]] = None):
        self.bom = bom or DEFAULT_BOM
        self.country_profiles = country_profiles or DEFAULT_COUNTRY_PROFILES

    def _calc_localization_rate(self, profile: CountryBOMProfile,
                                 is_ev: bool = False) -> float:
        """计算某国可实现的本地化率"""
        bom = list(self.bom)
        if is_ev:
            # 替换燃油动力总成为EV组件
            ev_replace_ids = {"engine", "transmission", "fuel_system", "exhaust"}
            bom = [b for b in bom if b.item_id not in ev_replace_ids]
            bom.extend(EV_BOM_DIFF.values())

        total_weighted = 0.0
        for item in bom:
            local_ratio = profile.local_sourcing.get(item.item_id, 0.0)
            total_weighted += item.cost_ratio * local_ratio

        return min(1.0, total_weighted)

    def _calc_cost_index(self, profile: CountryBOMProfile,
                          local_rate: float) -> float:
        """计算总成本指数 (CBU=1.0基准)"""
        cbu_cost = 1.0 + profile.cbu_tariff  # CBU: 车价 + 关税

        # CKD/SKD成本 = CKD套件成本 + 本地采购 + 组装费 + CKD关税
        ckd_kit_cost = (1.0 - local_rate) * (1.0 + profile.ckd_tariff)
        local_cost = local_rate * 1.05  # 本地采购通常贵5%
        assembly_cost = profile.assembly_cost_ratio
        ckd_cost = ckd_kit_cost + local_cost + assembly_cost

        return ckd_cost / cbu_cost  # <1.0 表示CKD更划算

    def _calc_breakeven(self, profile: CountryBOMProfile,
                         cbu_cost: float, ckd_cost: float,
                         annual_volume: int = 50_000) -> float:
        """计算CKD产线投资回本年数"""
        # CKD产线投资估算: 年产能5万辆 → ~2亿美元
        base_investment = 200_000_000
        scale_factor = annual_volume / 50_000
        investment = base_investment * (scale_factor ** 0.7)  # 规模经济

        # 年节省
        per_unit_saving = (cbu_cost - ckd_cost) * 15_000  # 假设单车$15k基准
        annual_saving = per_unit_saving * annual_volume

        if annual_saving <= 0:
            return float('inf')

        return investment / annual_saving

    def analyze(self, country_id: str, is_ev: bool = False,
                annual_volume: int = 50_000) -> LocalizationAnalysis:
        """分析某国的最佳进入模式"""
        profile = self.country_profiles.get(country_id)
        if not profile:
            raise ValueError(f"No profile for {country_id}")

        # 计算本地化率
        local_rate = self._calc_localization_rate(profile, is_ev)

        # CBU成本
        cbu_cost = 1.0 + profile.cbu_tariff

        # CKD成本
        ckd_cost_index = self._calc_cost_index(profile, local_rate)
        ckd_cost = ckd_cost_index * cbu_cost

        # SKD成本（介于CBU和CKD之间）
        skd_cost = 1.0 + profile.skd_tariff + profile.assembly_cost_ratio * 0.5

        # 选择最优模式
        costs = {
            EntryMode.CBU: cbu_cost,
            EntryMode.SKD: skd_cost,
            EntryMode.CKD: ckd_cost,
        }
        best_mode = min(costs, key=costs.get)

        # 如果本地化率不达标，CKD不可选
        if local_rate < profile.required_localization and best_mode == EntryMode.CKD:
            # 降级到SKD
            best_mode = EntryMode.SKD if skd_cost < cbu_cost else EntryMode.CBU

        # 关税节省
        tariff_saving = profile.cbu_tariff - (
            profile.ckd_tariff if best_mode == EntryMode.CKD
            else profile.skd_tariff if best_mode == EntryMode.SKD
            else 0
        )

        # 回本年数
        breakeven = self._calc_breakeven(profile, cbu_cost, ckd_cost, annual_volume)

        # 各子系统本地化率
        breakdown = {}
        bom = list(self.bom)
        if is_ev:
            ev_replace_ids = {"engine", "transmission", "fuel_system", "exhaust"}
            bom = [b for b in bom if b.item_id not in ev_replace_ids]
            bom.extend(EV_BOM_DIFF.values())

        for item in bom:
            rate = profile.local_sourcing.get(item.item_id, 0.0)
            breakdown[item.name_cn] = rate

        # 建议
        recs = []
        if best_mode == EntryMode.CBU:
            recs.append(f"CBU出口最优：关税{profile.cbu_tariff:.0%}，但CKD/SKD组装不经济")
        elif best_mode == EntryMode.CKD:
            recs.append(f"CKD组装最优：本地化率{local_rate:.0%}（要求{profile.required_localization:.0%}），成本指数{ckd_cost_index:.2f}")
            if local_rate < profile.required_localization:
                recs.append(f"⚠ 本地化率未达标（{local_rate:.0%} < {profile.required_localization:.0%}），需加强本地采购")
        elif best_mode == EntryMode.SKD:
            recs.append(f"SKD组装最优：介于CBU和CKD之间")

        # 本地化率差距分析
        gap = profile.required_localization - local_rate
        if gap > 0.05:
            # 找出最容易本地化的短板组件
            easy_wins = sorted(
                [(item.name_cn, item.localization_ease, item.cost_ratio, profile.local_sourcing.get(item.item_id, 0))
                 for item in bom if profile.local_sourcing.get(item.item_id, 0) < 0.5],
                key=lambda x: -x[1]
            )[:3]
            if easy_wins:
                recs.append("优先本地化: " + ", ".join(f"{n}(难度{e:.0%})" for n, e, _, _ in easy_wins))

        return LocalizationAnalysis(
            country_id=country_id,
            country_cn=profile.country_cn,
            recommended_mode=best_mode,
            total_cost_index=costs[best_mode] / cbu_cost,
            localization_rate=local_rate,
            tariff_savings=max(0, tariff_saving),
            breakeven_years=breakeven,
            component_breakdown=breakdown,
            recommendations=recs,
        )

    def analyze_all(self, country_ids: Optional[List[str]] = None,
                    is_ev: bool = False) -> List[LocalizationAnalysis]:
        """批量分析所有国家"""
        ids = country_ids or list(self.country_profiles.keys())
        return [self.analyze(c, is_ev) for c in ids]
