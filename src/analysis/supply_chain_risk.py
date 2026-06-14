"""
供应链风险分析模块 - 基于大模型的风险评估与预警
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(Enum):
    """风险类别"""
    SUPPLY_DISRUPTION = "supply_disruption"    # 供应中断
    PRICE_VOLATILITY = "price_volatility"      # 价格波动
    GEOPOLITICAL = "geopolitical"              # 地缘政治
    REGULATORY = "regulatory"                  # 法规变化
    LOGISTICS = "logistics"                    # 物流风险
    ENVIRONMENTAL = "environmental"            # 环境风险（碳排放等）


@dataclass
class RiskAssessment:
    """风险评估结果"""
    category: RiskCategory
    level: RiskLevel
    description: str
    probability: float  # 0-1
    impact: float       # 0-1
    mitigation: str
    data_sources: list[str]
    assessed_at: datetime = None

    def __post_init__(self):
        if self.assessed_at is None:
            self.assessed_at = datetime.now()

    @property
    def risk_score(self) -> float:
        """综合风险评分 = 概率 × 影响"""
        return self.probability * self.impact


class SupplyChainRiskAnalyzer:
    """供应链风险分析器"""

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: 大模型客户端（OpenAI/Claude等）
        """
        self.llm = llm_client
        self.logger = logging.getLogger(self.__class__.__name__)

    async def assess_risk(
        self,
        category: RiskCategory,
        context: str,
        data: dict = None
    ) -> RiskAssessment:
        """
        评估指定类别的供应链风险

        Args:
            category: 风险类别
            context: 上下文描述（如"德国汽车零部件供应"）
            data: 辅助数据
        """
        if self.llm is None:
            return self._rule_based_assessment(category, context, data)

        # LLM 驱动的风险评估
        prompt = self._build_risk_prompt(category, context, data)
        response = await self.llm.analyze(prompt)
        return self._parse_risk_response(response, category)

    async def assess_all_risks(
        self,
        context: str,
        data: dict = None
    ) -> list[RiskAssessment]:
        """评估所有类别的风险"""
        assessments = []
        for category in RiskCategory:
            assessment = await self.assess_risk(category, context, data)
            assessments.append(assessment)
        return sorted(assessments, key=lambda x: x.risk_score, reverse=True)

    def _rule_based_assessment(
        self,
        category: RiskCategory,
        context: str,
        data: dict = None
    ) -> RiskAssessment:
        """基于规则的风险评估（LLM不可用时的降级方案）"""
        rules = {
            RiskCategory.SUPPLY_DISRUPTION: RiskAssessment(
                category=category,
                level=RiskLevel.MEDIUM,
                description=f"供应中断风险：{context}",
                probability=0.3,
                impact=0.7,
                mitigation="建立多供应商备份，增加安全库存",
                data_sources=["trade_data", "news"],
            ),
            RiskCategory.PRICE_VOLATILITY: RiskAssessment(
                category=category,
                level=RiskLevel.HIGH,
                description=f"价格波动风险：{context}",
                probability=0.5,
                impact=0.6,
                mitigation="期货对冲，长期合同锁定价格",
                data_sources=["market_data", "historical_prices"],
            ),
            RiskCategory.GEOPOLITICAL: RiskAssessment(
                category=category,
                level=RiskLevel.MEDIUM,
                description=f"地缘政治风险：{context}",
                probability=0.4,
                impact=0.8,
                mitigation="多元化供应链布局，关注政策动态",
                data_sources=["news", "policy_documents"],
            ),
        }
        return rules.get(category, RiskAssessment(
            category=category,
            level=RiskLevel.LOW,
            description=f"风险待评估：{context}",
            probability=0.1,
            impact=0.1,
            mitigation="持续监控",
            data_sources=[],
        ))

    def _build_risk_prompt(self, category: RiskCategory, context: str, data: dict) -> str:
        """构建LLM风险评估提示词"""
        return f"""你是一个全球供应链风险分析专家。请基于以下信息评估风险：

风险类别: {category.value}
分析对象: {context}
辅助数据: {data or '无'}

请返回JSON格式：
{{
    "level": "low/medium/high/critical",
    "description": "风险描述",
    "probability": 0.0-1.0,
    "impact": 0.0-1.0,
    "mitigation": "缓解措施建议",
    "data_sources": ["数据源1", "数据源2"]
}}"""

    def _parse_risk_response(self, response: str, category: RiskCategory) -> RiskAssessment:
        """解析LLM返回的风险评估结果"""
        import json
        try:
            data = json.loads(response)
            return RiskAssessment(
                category=category,
                level=RiskLevel(data.get("level", "medium")),
                description=data.get("description", ""),
                probability=float(data.get("probability", 0.3)),
                impact=float(data.get("impact", 0.5)),
                mitigation=data.get("mitigation", ""),
                data_sources=data.get("data_sources", []),
            )
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.warning(f"Failed to parse LLM response: {e}")
            return self._rule_based_assessment(category, "")
