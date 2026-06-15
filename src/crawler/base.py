"""
爬虫基类 - 基于Scrapling框架
================================
提供统一的爬虫接口，支持多种数据源和反爬策略。
架构：
  - Fetcher（curl_cffi TLS指纹模拟）→ 轻度反爬站点
  - StealthyFetcher（patchright浏览器）→ 强反爬站点
  - Apify云爬虫 → 终极备选

运行要求：
  - 海外网络环境（VPN/海外服务器）
  - pip install scrapling[all]
  - patchright install（StealthyFetcher需要）
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """爬取结果数据结构"""
    source: str                       # 数据来源平台
    url: str                          # 原始链接
    title: str                        # 标题
    price: Optional[float] = None     # 价格
    currency: Optional[str] = None    # 货币
    brand: Optional[str] = None       # 品牌
    model: Optional[str] = None       # 型号
    year: Optional[int] = None        # 年份
    mileage: Optional[int] = None     # 里程(km)
    fuel_type: Optional[str] = None   # 燃料类型
    location: Optional[str] = None    # 位置
    seller_type: Optional[str] = None # 卖家类型（经销商/个人）
    raw_data: Optional[dict] = field(default_factory=dict)
    crawled_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d['crawled_at'] = d['crawled_at'].isoformat()
        return d


class BaseCrawler(ABC):
    """爬虫基类"""

    # 子类覆盖
    SOURCE_NAME: str = "unknown"
    BASE_URL: str = ""
    ANTI_BOT_LEVEL: str = "none"  # none / cloudflare / akamai / custom

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._fetcher = None
        self._stealthy = None

    @property
    def fetcher(self):
        """懒加载 Scrapling Fetcher（curl_cffi，无需浏览器）"""
        if self._fetcher is None:
            from scrapling.fetchers import Fetcher
            self._fetcher = Fetcher
        return self._fetcher

    @property
    def stealthy_fetcher(self):
        """懒加载 Scrapling StealthyFetcher（需patchright浏览器）"""
        if self._stealthy is None:
            from scrapling.fetchers import StealthyFetcher
            self._stealthy = StealthyFetcher
        return self._stealthy

    @abstractmethod
    def fetch(self, query: str = "", max_pages: int = 1) -> list[CrawlResult]:
        """执行爬取任务"""
        pass

    @abstractmethod
    def parse(self, page) -> list[CrawlResult]:
        """解析页面内容"""
        pass

    def save(self, results: list[CrawlResult], output_path: str):
        """保存爬取结果为JSON"""
        data = [r.to_dict() for r in results]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Saved {len(results)} results to {output_path}")

    @staticmethod
    def extract_price(price_text: str) -> Optional[float]:
        """从价格文本中提取数字"""
        import re
        # 去掉千分位分隔符（欧洲用.，美国用,）
        cleaned = price_text.replace('.', '').replace(',', '.')
        match = re.search(r'[\d]+(?:\.\d+)?', cleaned)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None

    @staticmethod
    def extract_mileage(text: str) -> Optional[int]:
        """从里程文本提取公里数"""
        import re
        match = re.search(r'([\d.,]+)\s*(?:km|км)', text, re.IGNORECASE)
        if match:
            num_str = match.group(1).replace('.', '').replace(',', '')
            try:
                return int(num_str)
            except ValueError:
                return None
        return None
