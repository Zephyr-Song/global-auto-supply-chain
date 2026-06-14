"""
mobile.de 爬虫 - 基于 Apify + Playwright 的混合方案

mobile.de 部署了 Akamai 级别反爬机制，需要特殊处理。
推荐分阶段策略：
1. Apify 免费额度获取样本数据
2. Playwright 半自动化扩展数据量
"""
import asyncio
import os
from typing import Optional
from .base import BaseCrawler, CrawlResult


class MobileDeCrawler(BaseCrawler):
    """mobile.de 爬虫"""

    BASE_URL = "https://www.mobile.de"
    SEARCH_URL = f"{BASE_URL}/fahrzeuge/search.html"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.apify_token = os.getenv("APIFY_TOKEN", "")
        self.headless = self.config.get("headless", True)

    async def fetch_via_apify(self, query: str, max_pages: int = 1) -> list[CrawlResult]:
        """
        通过 Apify 平台爬取 - 使用免费额度
        需要 APIFY_TOKEN 环境变量
        """
        if not self.apify_token:
            self.logger.warning("APIFY_TOKEN not set, falling back to Playwright")
            return await self.fetch_via_playwright(query, max_pages)

        # Apify Actor 调用示例
        # 实际使用时替换为具体的 Actor ID
        try:
            from apify_client import ApifyClient
            client = ApifyClient(self.apify_token)
            # 运行 Web Scraper Actor
            run = client.actor("apify/web-scraper").call(run_input={
                "startUrls": [{"url": f"{self.SEARCH_URL}?damageUnrepaired=NO&isSearchRequest=true&q={query}"}],
                "maxPagesPerCrawl": max_pages,
                "linkSelector": "a[href]",
                "pseudoUrls": [{"purl": "https://www.mobile.de/fahrzeuge/details/.*"}],
            })
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                result = self._parse_apify_item(item)
                if result:
                    results.append(result)
            return results
        except ImportError:
            self.logger.error("apify-client not installed. Run: pip install apify-client")
            return []
        except Exception as e:
            self.logger.error(f"Apify crawl failed: {e}")
            return []

    async def fetch_via_playwright(self, query: str, max_pages: int = 1) -> list[CrawlResult]:
        """
        通过 Playwright 半自动化爬取
        适合中等规模数据采集，需人工介入验证码
        """
        results = []
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=not self.headless)
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()

                for page_num in range(1, max_pages + 1):
                    url = f"{self.SEARCH_URL}?damageUnrepaired=NO&isSearchRequest=true&q={query}&page={page_num}"
                    self.logger.info(f"Fetching page {page_num}: {url}")
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    
                    # 等待内容加载
                    await page.wait_for_selector('[data-testid="search-results"]', timeout=10000)
                    
                    # 解析列表页
                    listings = await page.query_selector_all('[data-testid="search-result-item"]')
                    for listing in listings:
                        result = await self._parse_listing_element(listing)
                        if result:
                            results.append(result)

                await browser.close()
        except ImportError:
            self.logger.error("playwright not installed. Run: pip install playwright && playwright install")
        except Exception as e:
            self.logger.error(f"Playwright crawl failed: {e}")
        
        return results

    async def fetch(self, query: str, max_pages: int = 1) -> list[CrawlResult]:
        """统一爬取入口 - 优先 Apify，回退 Playwright"""
        if self.apify_token:
            return await self.fetch_via_apify(query, max_pages)
        return await self.fetch_via_playwright(query, max_pages)

    async def parse(self, raw_html: str) -> list[CrawlResult]:
        """解析 HTML 内容（备用方法）"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw_html, 'html.parser')
        results = []
        # TODO: 实现具体的 HTML 解析逻辑
        return results

    def _parse_apify_item(self, item: dict) -> Optional[CrawlResult]:
        """解析 Apify 返回的数据项"""
        try:
            return CrawlResult(
                source="mobile.de",
                url=item.get("url", ""),
                title=item.get("title", ""),
                price=self._extract_price(item.get("priceText", "")),
                currency="EUR",
                raw_data=item,
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse Apify item: {e}")
            return None

    async def _parse_listing_element(self, element) -> Optional[CrawlResult]:
        """解析 Playwright 获取的列表元素"""
        try:
            title_el = await element.query_selector('[data-testid="title"]')
            price_el = await element.query_selector('[data-testid="price"]')
            link_el = await element.query_selector('a[href]')
            
            title = await title_el.inner_text() if title_el else ""
            price_text = await price_el.inner_text() if price_el else ""
            href = await link_el.get_attribute("href") if link_el else ""

            return CrawlResult(
                source="mobile.de",
                url=f"{self.BASE_URL}{href}" if href.startswith("/") else href,
                title=title.strip(),
                price=self._extract_price(price_text),
                currency="EUR",
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse listing: {e}")
            return None

    @staticmethod
    def _extract_price(price_text: str) -> Optional[float]:
        """从价格文本中提取数字"""
        import re
        match = re.search(r'[\d.,]+', price_text.replace('.', '').replace(',', '.'))
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None


if __name__ == "__main__":
    crawler = MobileDeCrawler()
    results = asyncio.run(crawler.fetch("BMW", max_pages=1))
    print(f"Crawled {len(results)} results")
    for r in results:
        print(f"  {r.title} - {r.price} {r.currency}")
