"""
全球汽车市场调研 - 爬虫模块
=============================
支持两种爬虫引擎：
  1. Scrapling（本地运行，需海外网络）
  2. Apify（云爬虫，需 APIFY_TOKEN）

快速使用：
  from src.crawler import run_crawl
  results = run_crawl("mobile.de", "BMW 3er", max_pages=2)
"""

from .base import BaseCrawler, CrawlResult
from .scrapling_crawler import (
    MobileDeCrawler,
    OlxBrasilCrawler,
    SahibindenCrawler,
    OtomotoCrawler,
    CRAWLER_REGISTRY,
    get_crawler,
    run_crawl,
)
from .apify_crawler import ApifyMobileDeCrawler, ApifyWebScraper
__all__ = [
    "BaseCrawler",
    "CrawlResult",
    "MobileDeCrawler",
    "OlxBrasilCrawler",
    "SahibindenCrawler",
    "OtomotoCrawler",
    "ApifyMobileDeCrawler",
    "ApifyWebScraper",
    "CRAWLER_REGISTRY",
    "get_crawler",
    "run_crawl",
]
