"""
Apify 云爬虫 — 终极备选方案
=============================
当本地 Scrapling 爬虫无法突破反爬时，使用 Apify 平台的免费额度。

免费额度：
  - 新注册账户 $5 免费额度
  - 足够爬取数千条数据

前置条件：
  - 注册 https://apify.com
  - 获取 API Token → 设置环境变量 APIFY_TOKEN

使用方法：
  python -m src.crawler.apify_crawler mobile.de "BMW" --pages 2
"""
import json
import os
import logging
from datetime import datetime
from typing import Optional

from .base import BaseCrawler, CrawlResult

logger = logging.getLogger("apify_crawler")


class ApifyMobileDeCrawler(BaseCrawler):
    """通过 Apify 爬取 mobile.de"""
    SOURCE_NAME = "mobile.de (via Apify)"
    BASE_URL = "https://www.mobile.de"
    ANTI_BOT_LEVEL = "none"  # Apify 处理反爬

    # Apify Actor ID：Czech Dev 的 mobile.de scraper
    ACTOR_ID = "czechdev~mobile-de-scraper"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.token = os.getenv("APIFY_TOKEN", "")
        if not self.token:
            logger.warning("APIFY_TOKEN 环境变量未设置！请先注册 https://apify.com 并获取 Token")

    def fetch(self, query: str = "", max_pages: int = 1) -> list[CrawlResult]:
        if not self.token:
            logger.error("缺少 APIFY_TOKEN，无法运行 Apify 爬虫")
            return []

        try:
            from apify_client import ApifyClient
        except ImportError:
            logger.error("请安装 apify-client: pip install apify-client")
            return []

        client = ApifyClient(self.token)
        results = []

        try:
            run_input = {
                "searchQuery": query,
                "maxPages": max_pages,
                "proxyConfiguration": {"useApifyProxy": True},
            }

            logger.info(f"[Apify/mobile.de] Starting actor {self.ACTOR_ID}")
            run = client.actor(self.ACTOR_ID).call(run_input=run_input)

            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                result = self._parse_item(item)
                if result:
                    results.append(result)

            logger.info(f"[Apify/mobile.de] Got {len(results)} results")

        except Exception as e:
            logger.error(f"[Apify/mobile.de] Failed: {type(e).__name__}: {e}")

        return results

    def parse(self, page) -> list[CrawlResult]:
        # Apify 不需要手动 parse
        return []

    def _parse_item(self, item: dict) -> Optional[CrawlResult]:
        try:
            return CrawlResult(
                source="mobile.de",
                url=item.get("url", ""),
                title=item.get("title", ""),
                price=self.extract_price(str(item.get("price", ""))),
                currency="EUR",
                brand=item.get("make", ""),
                model=item.get("model", ""),
                year=item.get("year"),
                mileage=item.get("mileage"),
                fuel_type=item.get("fuelType", ""),
                location=item.get("location", ""),
                seller_type=item.get("sellerType", ""),
                raw_data=item,
            )
        except Exception as e:
            logger.debug(f"[Apify/mobile.de] Skip item: {e}")
            return None


class ApifyWebScraper(BaseCrawler):
    """
    通用 Apify Web Scraper — 可用于任意网站
    使用 Apify 官方 Web Scraper Actor
    """
    SOURCE_NAME = "apify_web_scraper"
    BASE_URL = ""
    ANTI_BOT_LEVEL = "none"
    ACTOR_ID = "apify/web-scraper"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.token = os.getenv("APIFY_TOKEN", "")
        self.target_url = config.get("url", "") if config else ""

    def fetch(self, query: str = "", max_pages: int = 1) -> list[CrawlResult]:
        if not self.token:
            logger.error("缺少 APIFY_TOKEN")
            return []

        try:
            from apify_client import ApifyClient
        except ImportError:
            logger.error("pip install apify-client")
            return []

        client = ApifyClient(self.token)
        url = self.target_url or query

        if not url.startswith("http"):
            logger.error("需要提供完整URL，如 https://www.mobile.de/fahrzeuge/...")
            return []

        results = []

        try:
            run_input = {
                "startUrls": [{"url": url}],
                "maxPagesPerCrawl": max_pages,
                "linkSelector": "a[href]",
            }

            run = client.actor(self.ACTOR_ID).call(run_input=run_input)

            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                result = CrawlResult(
                    source=self.target_url,
                    url=item.get("url", ""),
                    title=item.get("title", item.get("pageTitle", "")),
                    raw_data=item,
                )
                results.append(result)

            logger.info(f"[Apify/WebScraper] Got {len(results)} results from {url}")

        except Exception as e:
            logger.error(f"[Apify/WebScraper] Failed: {e}")

        return results

    def parse(self, page) -> list[CrawlResult]:
        return []


APIFY_CRAWLER_REGISTRY = {
    "mobile.de": ApifyMobileDeCrawler,
    "mobile": ApifyMobileDeCrawler,
    "web_scraper": ApifyWebScraper,
    "generic": ApifyWebScraper,
}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Apify 云爬虫")
    parser.add_argument("site", help="站点或 'generic'")
    parser.add_argument("query", nargs="?", default="", help="搜索关键词或完整URL")
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--output", "-o", default="")

    args = parser.parse_args()

    cls = APIFY_CRAWLER_REGISTRY.get(args.site.lower())
    if not cls:
        print(f"Unknown site. Available: {list(APIFY_CRAWLER_REGISTRY.keys())}")
        exit(1)

    crawler = cls({"url": args.query} if cls == ApifyWebScraper else {})
    results = crawler.fetch(args.query, args.pages)

    if results:
        output = args.output or f"data/crawled/apify_{args.site}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        crawler.save(results, output)
        print(f"Saved {len(results)} results to {output}")
    else:
        print("No results")
