"""
全球汽车市场爬虫 - 一键运行脚本
=================================
在海外/VPN环境下运行此脚本，自动爬取多个站点的汽车市场数据。

使用方法：
  # 爬取所有站点
  python scripts/run_crawlers.py --all

  # 爬取指定站点
  python scripts/run_crawlers.py --site mobile.de --query "BMW"
  python scripts/run_crawlers.py --site olx_br --query "BYD"

  # 使用 Apify（需 APIFY_TOKEN）
  python scripts/run_crawlers.py --apify --site mobile.de --query "VW Golf"

  # 列出支持站点
  python scripts/run_crawlers.py --list
"""
import argparse
import json
import os
import sys
import logging
from datetime import datetime

# 确保项目根目录在 sys.path 中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_crawlers")


# 默认爬取任务
DEFAULT_TASKS = [
    # 欧洲
    {"site": "mobile.de", "query": "BYD", "pages": 2},
    {"site": "mobile.de", "query": "Chery", "pages": 1},
    {"site": "otomoto", "query": "MG", "pages": 1},
    # 南美
    {"site": "olx_br", "query": "BYD", "pages": 2},
    {"site": "olx_br", "query": "Chery", "pages": 1},
    # 中东/土耳其
    {"site": "sahibinden", "query": "Chery", "pages": 1},
]


def main():
    parser = argparse.ArgumentParser(description="全球汽车市场爬虫一键运行")
    parser.add_argument("--all", action="store_true", help="运行所有默认爬取任务")
    parser.add_argument("--site", help="指定站点")
    parser.add_argument("--query", default="", help="搜索关键词")
    parser.add_argument("--pages", type=int, default=1, help="每站爬取页数")
    parser.add_argument("--apify", action="store_true", help="使用 Apify 云爬虫")
    parser.add_argument("--output-dir", default="data/crawled", help="输出目录")
    parser.add_argument("--list", action="store_true", help="列出支持的站点")
    parser.add_argument("--no-headless", action="store_true", help="显示浏览器窗口")
    parser.add_argument("--check", action="store_true", help="检查环境是否就绪")

    args = parser.parse_args()

    if args.list:
        print("\n支持的站点：")
        print(f"{'Key':<16} {'站点':<25} {'反爬级别':<12} {'推荐策略'}")
        print("-" * 70)
        from src.crawler.scrapling_crawler import CRAWLER_REGISTRY

        seen = set()
        for key, cls in CRAWLER_REGISTRY.items():
            canon = cls.SOURCE_NAME
            if canon in seen:
                continue
            seen.add(canon)
            inst = cls()
            strategy = "StealthyFetcher" if inst.ANTI_BOT_LEVEL in ("akamai", "cloudflare") else "Fetcher"
            print(f"{key:<16} {canon:<25} {inst.ANTI_BOT_LEVEL:<12} {strategy}")
        print("\nApify 备选：mobile.de, generic（任意URL）")
        return

    if args.check:
        print("\n环境检查：")
        # Python 版本
        print(f"  Python: {sys.version}")
        # Scrapling
        try:
            import scrapling
            print(f"  scrapling: ✓ ({scrapling.__version__})")
        except ImportError:
            print("  scrapling: ✗ (pip install scrapling[all])")
        # patchright
        try:
            import patchright
            print(f"  patchright: ✓")
        except ImportError:
            print("  patchright: ✗ (pip install patchright && patchright install)")
        # apify-client
        try:
            import apify_client
            print(f"  apify-client: ✓")
        except ImportError:
            print("  apify-client: ✗ (pip install apify-client)")
        # APIFY_TOKEN
        if os.getenv("APIFY_TOKEN"):
            print("  APIFY_TOKEN: ✓ (已设置)")
        else:
            print("  APIFY_TOKEN: ✗ (未设置，Apify不可用)")
        # 网络（简单测试）
        try:
            from scrapling.fetchers import Fetcher
            resp = Fetcher.get("https://httpbin.org/ip", stealthy_headers=True)
            if resp.status == 200:
                ip_info = json.loads(resp.text)
                print(f"  出口IP: {ip_info.get('origin', 'unknown')}")
            else:
                print(f"  出口IP: HTTP {resp.status}")
        except Exception as e:
            print(f"  出口IP: 检查失败 ({e})")
        return

    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_results = {}

    if args.apify:
        # Apify 模式
        from src.crawler.apify_crawler import ApifyMobileDeCrawler, ApifyWebScraper
        if args.site:
            crawler = ApifyMobileDeCrawler()
            results = crawler.fetch(args.query, args.pages)
            all_results[args.site] = [r.to_dict() for r in results]
        else:
            print("Apify 模式需要指定 --site")
            return
    elif args.site:
        # 单站点模式
        from src.crawler.scrapling_crawler import run_crawl
        output = os.path.join(args.output_dir, f"{args.site}_{timestamp}.json")
        results = run_crawl(args.site, args.query, args.pages, not args.no_headless, output)
        all_results[args.site] = [r.to_dict() for r in results]
    elif args.all:
        # 全量模式
        from src.crawler.scrapling_crawler import run_crawl
        for task in DEFAULT_TASKS:
            site = task["site"]
            query = task["query"]
            pages = task.get("pages", 1)
            output = os.path.join(args.output_dir, f"{site}_{query.replace(' ', '_')}_{timestamp}.json")
            try:
                results = run_crawl(site, query, pages, not args.no_headless, output)
                all_results[f"{site}:{query}"] = [r.to_dict() for r in results]
            except Exception as e:
                logger.error(f"Failed: {site}:{query} - {e}")
                all_results[f"{site}:{query}"] = []
    else:
        parser.print_help()
        return

    # 汇总报告
    print(f"\n{'='*50}")
    print(f"爬取汇总 ({timestamp})")
    print(f"{'='*50}")
    total = 0
    for key, items in all_results.items():
        count = len(items)
        total += count
        print(f"  {key}: {count} 条")
    print(f"{'='*50}")
    print(f"  总计: {total} 条")

    # 保存汇总
    summary_path = os.path.join(args.output_dir, f"crawl_summary_{timestamp}.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "total": total,
            "breakdown": {k: len(v) for k, v in all_results.items()},
            "results": all_results,
        }, f, ensure_ascii=False, indent=2)
    print(f"  汇总文件: {summary_path}")


if __name__ == "__main__":
    main()
