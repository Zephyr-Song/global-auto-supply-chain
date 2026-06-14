"""
爬虫基类 - 定义统一的爬虫接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """爬取结果数据结构"""
    source: str                    # 数据来源平台
    url: str                       # 原始链接
    title: str                     # 标题
    price: Optional[float] = None  # 价格
    currency: Optional[str] = None # 货币
    brand: Optional[str] = None    # 品牌
    model: Optional[str] = None    # 型号
    year: Optional[int] = None     # 年份
    mileage: Optional[int] = None  # 里程(km)
    fuel_type: Optional[str] = None # 燃料类型
    location: Optional[str] = None  # 位置
    raw_data: Optional[dict] = field(default_factory=dict)  # 原始数据
    crawled_at: datetime = field(default_factory=datetime.now)


class BaseCrawler(ABC):
    """爬虫基类"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def fetch(self, query: str, max_pages: int = 1) -> list[CrawlResult]:
        """执行爬取任务"""
        pass

    @abstractmethod
    async def parse(self, raw_html: str) -> list[CrawlResult]:
        """解析页面内容"""
        pass

    async def save(self, results: list[CrawlResult], output_path: str):
        """保存爬取结果"""
        import json
        data = [r.__dict__ for r in results]
        # Convert datetime to string
        for item in data:
            item['crawled_at'] = item['crawled_at'].isoformat()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Saved {len(results)} results to {output_path}")
