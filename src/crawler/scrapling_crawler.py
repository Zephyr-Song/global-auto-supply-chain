"""
全球汽车市场 Scrapling 爬虫引擎
=================================
基于 Scrapling 框架，支持多个汽车交易平台的数据采集。

目标站点：
  - mobile.de（德国） → Akamai 反爬，建议 StealthyFetcher
  - olx.com.br（巴西）→ Cloudflare，建议 StealthyFetcher
  - sahibinden.com（土耳其）→ 中等反爬，Fetcher 可试
  - otomoto.pl（波兰）→ 中等反爬
  - Turbo.az（阿塞拜疆）→ 轻量反爬

运行条件：
  1. 海外网络环境（VPN 或海外服务器）
  2. pip install scrapling[all]
  3. patchright install（StealthyFetcher 需要）
  4. 或使用 Apify Token（环境变量 APIFY_TOKEN）

使用方法：
  python -m src.crawler.scrapling_crawler <site> <query> [--pages N] [--headless]

  示例：
    python -m src.crawler.scrapling_crawler mobile.de "BMW 3er" --pages 2
    python -m src.crawler.scrapling_crawler olx_br "VW Gol" --pages 1
    python -m src.crawler.scrapling_crawler sahibinden "BMW 3 Serisi" --pages 1
    python -m src.crawler.scrapling_crawler otomoto "Toyota" --pages 1 --headless
"""
import json
import os
import re
import sys
import logging
from typing import Optional
from datetime import datetime

from .base import BaseCrawler, CrawlResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scrapling_crawler")


# ============================================================
# 爬虫实现
# ============================================================

class MobileDeCrawler(BaseCrawler):
    """
    mobile.de 爬虫（德国最大的汽车交易平台）
    反爬级别：Akamai（强）
    推荐策略：StealthyFetcher > Apify > Fetcher
    """
    SOURCE_NAME = "mobile.de"
    BASE_URL = "https://www.mobile.de"
    ANTI_BOT_LEVEL = "akamai"
    SEARCH_PATH = "/fahrzeuge/search.html"

    def _build_url(self, query: str, page: int = 1) -> str:
        params = {
            "damageUnrepaired": "NO",
            "isSearchRequest": "true",
            "q": query,
            "pageNumber": page,
        }
        from urllib.parse import urlencode
        return f"{self.BASE_URL}{self.SEARCH_PATH}?{urlencode(params)}"

    def fetch(self, query: str = "", max_pages: int = 1) -> list[CrawlResult]:
        """使用 StealthyFetcher（推荐）"""
        logger.info(f"[mobile.de] Fetching '{query}', {max_pages} page(s)")
        all_results = []

        try:
            for page_num in range(1, max_pages + 1):
                url = self._build_url(query, page_num)
                logger.info(f"[mobile.de] Page {page_num}: {url}")

                response = self.stealthy_fetcher.fetch(
                    url,
                    headless=not self.config.get("headless", True),
                    network_idle=True,
                    timeout=60000,
                )

                if response.status != 200:
                    logger.warning(f"[mobile.de] HTTP {response.status}, skipping page")
                    continue

                results = self.parse(response)
                all_results.extend(results)
                logger.info(f"[mobile.de] Page {page_num}: got {len(results)} listings")

        except Exception as e:
            logger.error(f"[mobile.de] Fetch failed: {type(e).__name__}: {e}")

        return all_results

    def parse(self, page) -> list[CrawlResult]:
        """解析 mobile.de 搜索结果页"""
        results = []

        # 多种 CSS 选择器尝试（mobile.de 可能更新 DOM）
        selectors = [
            'article.rbt-listing',
            '[data-testid="search-result-item"]',
            '[data-ng-repeat="listing in result.listings"]',
            '.listing-item',
            'div[class*="listing"]',
        ]

        listings = []
        for sel in selectors:
            listings = page.css(sel)
            if listings:
                logger.info(f"[mobile.de] Found {len(listings)} listings via '{sel}'")
                break

        for item in listings:
            try:
                title_el = item.css('h2::text, [data-testid="title"]::text, a[class*="title"]::text')
                price_el = item.css('[data-testid="price"]::text, span[class*="price"]::text, .price::text')
                link_el = item.css('a[href]::attr(href)')
                detail_els = item.css('span[class*="mileage"]::text, span[class*="km"]::text')
                year_el = item.css('span[class*="year"]::text, span[class*="firstReg"]::text')
                location_el = item.css('span[class*="location"]::text, [data-testid="location"]::text')

                title = title_el[0].text.strip() if title_el else ""
                price_text = price_el[0].text.strip() if price_el else ""
                href = link_el[0].text.strip() if link_el else ""

                result = CrawlResult(
                    source=self.SOURCE_NAME,
                    url=href if href.startswith("http") else f"{self.BASE_URL}{href}" if href else "",
                    title=title,
                    price=self.extract_price(price_text),
                    currency="EUR",
                    year=self._extract_year(year_el[0].text if year_el else ""),
                    location=location_el[0].text.strip() if location_el else "",
                )

                # 里程
                for d in detail_els:
                    result.mileage = self.extract_mileage(d.text)
                    if result.mileage:
                        break

                results.append(result)
            except Exception as e:
                logger.debug(f"[mobile.de] Skip item: {e}")

        return results

    @staticmethod
    def _extract_year(text: str) -> Optional[int]:
        match = re.search(r'\b(19|20)\d{2}\b', str(text))
        return int(match.group()) if match else None


class OlxBrasilCrawler(BaseCrawler):
    """
    OLX Brasil 爬虫（巴西最大分类广告平台）
    反爬级别：Cloudflare
    推荐策略：StealthyFetcher > Fetcher
    """
    SOURCE_NAME = "olx.com.br"
    BASE_URL = "https://www.olx.com.br"
    ANTI_BOT_LEVEL = "cloudflare"
    SEARCH_PATH = "/autos-e-pecas/carros-vans-e-utilitarios"

    def _build_url(self, query: str, page: int = 1) -> str:
        q = query.replace(" ", "-").lower()
        if page > 1:
            return f"{self.BASE_URL}{self.SEARCH_PATH}?o={page}&q={q}"
        return f"{self.BASE_URL}{self.SEARCH_PATH}?q={q}"

    def fetch(self, query: str = "", max_pages: int = 1) -> list[CrawlResult]:
        logger.info(f"[olx_br] Fetching '{query}', {max_pages} page(s)")
        all_results = []

        # 优先 StealthyFetcher（SttealthyFetcher 可能不可用则回退 Fetcher）
        for page_num in range(1, max_pages + 1):
            url = self._build_url(query, page_num)

            try:
                response = self.stealthy_fetcher.fetch(
                    url, headless=True, network_idle=True, timeout=60000
                )
            except Exception:
                logger.warning("[olx_br] StealthyFetcher failed, trying Fetcher")
                response = self.fetcher.get(url, stealthy_headers=True)

            if response.status != 200:
                logger.warning(f"[olx_br] HTTP {response.status} on page {page_num}")
                continue

            results = self.parse(response)
            all_results.extend(results)
            logger.info(f"[olx_br] Page {page_num}: got {len(results)} listings")

        return all_results

    def parse(self, page) -> list[CrawlResult]:
        results = []
        selectors = [
            'li.sc-1fcmfeb-0',
            '[data-ds-component="ad-card"]',
            'a[data-lurker_list_id]',
            'li[class*="ad"]',
        ]

        listings = []
        for sel in selectors:
            listings = page.css(sel)
            if listings:
                break

        for item in listings:
            try:
                title = item.css('h2::text, [data-ds-component="title"]::text')
                price = item.css('span[class*="price"]::text, p[class*="price"]::text')
                link = item.css('a::attr(href)')

                result = CrawlResult(
                    source=self.SOURCE_NAME,
                    url=link[0].text.strip() if link else "",
                    title=title[0].text.strip() if title else "",
                    price=self.extract_price(price[0].text) if price else None,
                    currency="BRL",
                )
                results.append(result)
            except Exception as e:
                logger.debug(f"[olx_br] Skip item: {e}")

        return results


class SahibindenCrawler(BaseCrawler):
    """
    sahibinden.com 爬虫（土耳其最大分类平台）
    反爬级别：中等（WAF）
    推荐策略：Fetcher 可试，失败回退 StealthyFetcher
    """
    SOURCE_NAME = "sahibinden.com"
    BASE_URL = "https://www.sahibinden.com"
    ANTI_BOT_LEVEL = "cloudflare"

    def _build_url(self, query: str, page: int = 1) -> str:
        base = f"{self.BASE_URL}/arama?query={query.replace(' ', '%20')}"
        if page > 1:
            base += f"&pagingOffset={(page - 1) * 20}&pagingSize=20"
        return base

    def fetch(self, query: str = "", max_pages: int = 1) -> list[CrawlResult]:
        logger.info(f"[sahibinden] Fetching '{query}', {max_pages} page(s)")
        all_results = []

        for page_num in range(1, max_pages + 1):
            url = self._build_url(query, page_num)

            try:
                response = self.fetcher.get(url, stealthy_headers=True)
            except Exception:
                logger.warning("[sahibinden] Fetcher failed, trying StealthyFetcher")
                response = self.stealthy_fetcher.fetch(url, headless=True, timeout=60000)

            if response.status != 200:
                logger.warning(f"[sahibinden] HTTP {response.status}")
                continue

            results = self.parse(response)
            all_results.extend(results)

        return all_results

    def parse(self, page) -> list[CrawlResult]:
        results = []
        listings = page.css('tr[class*="searchResultItem"], .search-results-item, [data-id]')

        for item in listings:
            try:
                title_el = item.css('a[class*="title"]::text, a::text')
                price_el = item.css('span[class*="price"]::text, td[class*="price"]::text')
                link_el = item.css('a[href]::attr(href)')

                title = title_el[0].text.strip() if title_el else ""
                result = CrawlResult(
                    source=self.SOURCE_NAME,
                    url=f"{self.BASE_URL}{link_el[0].text.strip()}" if link_el else "",
                    title=title,
                    price=self.extract_price(price_el[0].text) if price_el else None,
                    currency="TRY",
                )
                results.append(result)
            except Exception as e:
                logger.debug(f"[sahibinden] Skip: {e}")

        return results


class OtomotoCrawler(BaseCrawler):
    """otomoto.pl 爬虫（波兰最大汽车交易平台）"""
    SOURCE_NAME = "otomoto.pl"
    BASE_URL = "https://www.otomoto.pl"
    ANTI_BOT_LEVEL = "cloudflare"

    def _build_url(self, query: str, page: int = 1) -> str:
        q = query.replace(" ", "+").lower()
        return f"{self.BASE_URL}/osobowe/{q}?page={page}"

    def fetch(self, query: str = "", max_pages: int = 1) -> list[CrawlResult]:
        logger.info(f"[otomoto] Fetching '{query}', {max_pages} page(s)")
        all_results = []

        for page_num in range(1, max_pages + 1):
            url = self._build_url(query, page_num)
            try:
                response = self.stealthy_fetcher.fetch(url, headless=True, network_idle=True, timeout=60000)
                if response.status == 200:
                    results = self.parse(response)
                    all_results.extend(results)
                    logger.info(f"[otomoto] Page {page_num}: {len(results)} listings")
                else:
                    logger.warning(f"[otomoto] HTTP {response.status}")
            except Exception as e:
                logger.warning(f"[otomoto] Page {page_num} failed: {e}")

        return all_results

    def parse(self, page) -> list[CrawlResult]:
        results = []
        selectors = [
            'article[class*="offer-item"]',
            '[data-testid="offer-card"]',
            'div[class*="offer"]',
        ]

        listings = []
        for sel in selectors:
            listings = page.css(sel)
            if listings:
                break

        for item in listings:
            try:
                title = item.css('h2::text, a[class*="title"]::text')
                price = item.css('span[class*="price"]::text, [data-testid="price"]::text')
                link = item.css('a[href]::attr(href)')

                result = CrawlResult(
                    source=self.SOURCE_NAME,
                    url=link[0].text.strip() if link else "",
                    title=title[0].text.strip() if title else "",
                    price=self.extract_price(price[0].text) if price else None,
                    currency="PLN",
                )
                results.append(result)
            except Exception as e:
                logger.debug(f"[otomoto] Skip: {e}")

        return results


# ============================================================
# 爬虫工厂
# ============================================================

CRAWLER_REGISTRY = {
    "mobile.de": MobileDeCrawler,
    "mobile": MobileDeCrawler,
    "olx.com.br": OlxBrasilCrawler,
    "olx_br": OlxBrasilCrawler,
    "olx": OlxBrasilCrawler,
    "sahibinden.com": SahibindenCrawler,
    "sahibinden": SahibindenCrawler,
    "otomoto.pl": OtomotoCrawler,
    "otomoto": OtomotoCrawler,
}

def get_crawler(site: str, config: dict = None) -> Optional[BaseCrawler]:
    """获取指定站点的爬虫实例"""
    site_key = site.lower().strip()
    cls = CRAWLER_REGISTRY.get(site_key)
    if cls:
        return cls(config or {})
    logger.warning(f"Unknown site: {site}. Available: {list(CRAWLER_REGISTRY.keys())}")
    return None

def run_crawl(site: str, query: str = "", max_pages: int = 1, headless: bool = True, output: str = ""):
    """通用爬取入口"""
    crawler = get_crawler(site, {"headless": headless})
    if not crawler:
        return []

    logger.info(f"Starting crawl on {crawler.SOURCE_NAME} (anti-bot level: {crawler.ANTI_BOT_LEVEL})")
    results = crawler.fetch(query, max_pages)

    if not output and results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = query.replace(" ", "_")[:20] if query else "all"
        output = f"data/crawled/{crawler.SOURCE_NAME.replace('.', '_')}_{safe_query}_{timestamp}.json"
        os.makedirs(os.path.dirname(output), exist_ok=True)

    if output and results:
        crawler.save(results, output)
        logger.info(f"Results saved to {output}")
    elif results:
        print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
    else:
        logger.warning("No results obtained")

    return results


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="全球汽车市场 Scrapling 爬虫引擎")
    parser.add_argument("site", help="目标站点 (mobile.de / olx_br / sahibinden / otomoto)")
    parser.add_argument("query", nargs="?", default="", help="搜索关键词")
    parser.add_argument("--pages", type=int, default=1, help="爬取页数")
    parser.add_argument("--headless", action="store_true", help="浏览器无头模式（默认启用）")
    parser.add_argument("--no-headless", action="store_true", help="显示浏览器窗口")
    parser.add_argument("--output", "-o", default="", help="输出文件路径")
    parser.add_argument("--list-sites", action="store_true", help="列出支持的站点")

    args = parser.parse_args()

    if args.list_sites:
        print("\n支持的站点：")
        print(f"{'站点名':<20} {'级别':<12} {'适合策略'}")
        print("-" * 60)
        for key, cls in sorted(CRAWLER_REGISTRY.items()):
            if key.replace('.', '_') != key:  # 只显示唯一key
                continue
            instance = cls()
            print(f"{key:<20} {instance.ANTI_BOT_LEVEL:<12} {'StealthyFetcher' if instance.ANTI_BOT_LEVEL in ('akamai', 'cloudflare') else 'Fetcher'}")
        sys.exit(0)

    headless = not args.no_headless
    run_crawl(args.site, args.query, args.pages, headless, args.output)
