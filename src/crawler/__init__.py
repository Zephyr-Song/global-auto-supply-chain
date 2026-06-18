"""
全球汽车市场调研 - 爬虫模块
=============================
支持三种爬虫引擎：
  1. StatsCrawler — 协会统计数据爬虫（国内可用，Scrapling Fetcher）
  2. Scrapling 交易类爬虫（需海外网络/住宅代理）
  3. Apify 云爬虫（需 APIFY_TOKEN）

快速使用：
  # 协会统计数据（国内可用）
  from src.crawler import StatsCrawler
  crawler = StatsCrawler()
  maa_data = crawler.crawl_maa()
  all_data = crawler.crawl_all()

  # 交易类数据（需海外网络）
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
from .stats_crawler import StatsCrawler
from .apify_crawler import ApifyMobileDeCrawler, ApifyWebScraper
__all__ = [
    # 统计数据爬虫（国内可用）
    "StatsCrawler",
    # 交易类爬虫（需海外网络）
    "BaseCrawler",
    "CrawlResult",
    "MobileDeCrawler",
    "OlxBrasilCrawler",
    "SahibindenCrawler",
    "OtomotoCrawler",
    # Apify 云爬虫
    "ApifyMobileDeCrawler",
    "ApifyWebScraper",
    # 工厂函数
    "CRAWLER_REGISTRY",
    "get_crawler",
    "run_crawl",
]
