"""
汽车协会统计数据爬虫 — 基于 Scrapling Fetcher
================================================
国内网络环境下可用的统计数据爬虫，专攻无反爬/轻反爬的汽车协会统计站点。

已验证可用的站点：
  - MAA 马来西亚：https://www.maa.org.my/statistics.html (HTML表格)
  - Gaikindo 印尼：https://www.gaikindo.or.id/ (文章正文+文件列表)
  - NAAMSA 南非：https://naamsa.net/ (PDF报告下载)
  - FTI 泰国：https://www.fti.or.th/ (需深挖)
  - ODD 土耳其：https://www.odd.org.tr/ (需深挖)
  - CAAM 中国：http://www.caam.org.cn/ (需登录/付费)

不可用（反爬拦截）：
  - mobile.de, OLX, sahibinden, otomoto → Akamai/Cloudflare
  - AMIA 墨西哥 → Cloudflare
  - INEGI 墨西哥 → 国内无法连接

使用方法：
  from src.crawler.stats_crawler import StatsCrawler
  crawler = StatsCrawler()
  maa_data = crawler.crawl_maa()
  gaikindo_data = crawler.crawl_gaikindo_sales()
  all_data = crawler.crawl_all()
"""
import json
import os
import re
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 数据输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "crawled")


class StatsCrawler:
    """汽车协会统计数据爬虫"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        self._fetcher = None

    @property
    def fetcher(self):
        """懒加载 Scrapling Fetcher"""
        if self._fetcher is None:
            from scrapling.fetchers import Fetcher
            self._fetcher = Fetcher
        return self._fetcher

    def _save_json(self, data: dict, filename: str):
        """保存 JSON 数据"""
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {filename} ({len(json.dumps(data))} bytes)")
        return path

    # ============================================================
    # MAA 马来西亚 — HTML 表格提取
    # ============================================================
    def crawl_maa(self) -> dict:
        """
        爬取 MAA 马来西亚汽车协会统计数据
        URL: https://www.maa.org.my/statistics.html
        数据: 2010-2023年产量+销量 (乘用车/商用车/合计)
        """
        url = "https://www.maa.org.my/statistics.html"
        logger.info(f"Crawling MAA Malaysia: {url}")

        try:
            r = self.fetcher.get(url, stealthy_headers=True, timeout=30000)
            if r.status != 200:
                logger.error(f"MAA returned status {r.status}")
                return {}

            tables = r.css('table')
            result = {"production": {}, "sales": {}, "crawled_at": datetime.now().isoformat(), "source_url": url}

            for i, table in enumerate(tables):
                rows = table.css('tr')
                for row in rows:
                    cells = row.css('td, th')
                    row_data = [cell.get_all_text().strip() for cell in cells]
                    row_data = [c for c in row_data if c]

                    if len(row_data) >= 4 and row_data[0].isdigit():
                        year = int(row_data[0])
                        try:
                            passenger = int(row_data[1].replace(',', ''))
                            commercial = int(row_data[2].replace(',', ''))
                            total = int(row_data[3].replace(',', ''))
                            entry = {"passenger": passenger, "commercial": commercial, "total": total}
                            if i == 0:
                                result["production"][year] = entry
                            else:
                                result["sales"][year] = entry
                        except (ValueError, IndexError) as e:
                            logger.warning(f"MAA table {i} year {row_data[0]}: parse error - {e}")

            path = self._save_json(result, "maa_malaysia_real_data.json")
            logger.info(f"MAA: {len(result['production'])} production years, {len(result['sales'])} sales years")
            return result

        except Exception as e:
            logger.error(f"MAA crawl failed: {e}")
            return {}

    # ============================================================
    # Gaikindo 印尼 — 文章正文 + 文件列表
    # ============================================================
    def crawl_gaikindo_sales(self) -> dict:
        """
        爬取 Gaikindo 印尼汽车工业协会最新品牌销量数据
        URL: https://www.gaikindo.or.id/ (新闻稿文章)
        数据: 2026年1-5月 Top10 品牌批发销量
        """
        url = "https://www.gaikindo.or.id/10-mobil-terlaris-whole-sales-januari-mei-2026-toyota-masih-teratas-byd-naik-peringkat/"
        logger.info(f"Crawling Gaikindo sales: {url}")

        try:
            r = self.fetcher.get(url, stealthy_headers=True, timeout=30000)
            if r.status != 200:
                logger.error(f"Gaikindo returned status {r.status}")
                return {}

            all_text = r.get_all_text()
            result = {
                "source": "Gaikindo",
                "period": "Jan-May 2026",
                "brands": {},
                "crawled_at": datetime.now().isoformat(),
                "source_url": url,
            }

            # 从文章正文提取品牌销量
            # 格式: "Toyota: 111.119 unit" 或 "BYD: 17.993 unit"
            brand_pattern = re.compile(r'(Toyota|Daihatsu|Suzuki|Mitsubishi Motors|Honda|BYD|Jaecoo|Mitsubishi Fuso|Isuzu|Hino|Chery|Wuling|Hyundai):\s*([\d.]+)\s*unit', re.IGNORECASE)
            for match in brand_pattern.finditer(all_text):
                brand = match.group(1)
                units = int(match.group(2).replace('.', ''))
                result["brands"][brand] = units

            # 提取总计数据
            total_pattern = re.compile(r'(\d[\d.]+)\s*unit.*?(?:whole sales|wholesale)', re.IGNORECASE)
            for match in total_pattern.finditer(all_text):
                val = int(match.group(1).replace('.', ''))
                if val > 100000:  # 总计数据
                    result["total_whole_sales"] = val
                    break

            path = self._save_json(result, "gaikindo_indonesia_real_data.json")
            logger.info(f"Gaikindo: {len(result['brands'])} brands extracted")
            return result

        except Exception as e:
            logger.error(f"Gaikindo crawl failed: {e}")
            return {}

    def crawl_gaikindo_files(self) -> list:
        """
        爬取 Gaikindo 文件服务器可用文件列表
        URL: https://files.gaikindo.or.id/list-files.php?lang=id
        数据: 2010-2026年 production/wholesale/export/import PDF文件
        """
        url = "https://files.gaikindo.or.id/list-files.php?lang=id"
        logger.info(f"Crawling Gaikindo file list: {url}")

        try:
            r = self.fetcher.get(url, stealthy_headers=True, timeout=30000)
            if r.status != 200:
                logger.error(f"Gaikindo files returned status {r.status}")
                return []

            all_text = r.get_all_text()
            files = []
            for line in all_text.split('\n'):
                line = line.strip()
                if line and ('2026' in line or '2025' in line or '2024' in line):
                    files.append({"name": line, "crawled_at": datetime.now().isoformat()})

            self._save_json({"files": files, "source_url": url, "crawled_at": datetime.now().isoformat()}, "gaikindo_file_links.json")
            logger.info(f"Gaikindo files: {len(files)} recent files found")
            return files

        except Exception as e:
            logger.error(f"Gaikindo files crawl failed: {e}")
            return []

    # ============================================================
    # NAAMSA 南非 — PDF 报告链接提取
    # ============================================================
    def crawl_naamsa_pdfs(self) -> dict:
        """
        爬取 NAAMSA 南非汽车协会 PDF 报告链接
        URL: https://naamsa.net/
        数据: 月度 Flash Report + Media Release PDF 链接
        """
        url = "https://naamsa.net/"
        logger.info(f"Crawling NAAMSA PDFs: {url}")

        try:
            r = self.fetcher.get(url, stealthy_headers=True, timeout=30000)
            if r.status != 200:
                logger.error(f"NAAMSA returned status {r.status}")
                return {}

            result = {"pdfs": [], "sales_pages": [], "crawled_at": datetime.now().isoformat(), "source_url": url}

            # 提取 PDF 链接
            pdf_links = r.css('a[href$=".pdf"]')
            for link in pdf_links:
                href = link.attrib.get('href', '')
                text = link.get_all_text().strip()
                if href:
                    result["pdfs"].append({"text": text, "url": href})

            # 提取数据页面链接
            all_links = r.css('a')
            for a in all_links:
                href = a.attrib.get('href', '')
                text = a.get_all_text().strip().lower()
                if any(kw in text for kw in ['sales', 'export', 'import', 'domestic']):
                    if href and not href.startswith('#'):
                        result["sales_pages"].append({"text": text, "url": href})

            self._save_json(result, "naamsa_south_africa_links.json")
            logger.info(f"NAAMSA: {len(result['pdfs'])} PDFs, {len(result['sales_pages'])} sales pages")
            return result

        except Exception as e:
            logger.error(f"NAAMSA crawl failed: {e}")
            return {}

    # ============================================================
    # 通用爬取：一次运行所有已验证站点
    # ============================================================
    def crawl_all(self) -> dict:
        """一次爬取所有已验证可用的站点"""
        results = {
            "crawled_at": datetime.now().isoformat(),
            "sites": {}
        }

        # MAA 马来西亚
        maa = self.crawl_maa()
        if maa:
            results["sites"]["MAA_Malaysia"] = {
                "status": "success",
                "production_years": len(maa.get("production", {})),
                "sales_years": len(maa.get("sales", {})),
            }
        else:
            results["sites"]["MAA_Malaysia"] = {"status": "failed"}

        # Gaikindo 印尼
        gaikindo = self.crawl_gaikindo_sales()
        if gaikindo:
            results["sites"]["Gaikindo_Indonesia"] = {
                "status": "success",
                "brands": len(gaikindo.get("brands", {})),
            }
        else:
            results["sites"]["Gaikindo_Indonesia"] = {"status": "failed"}

        # Gaikindo 文件列表
        gaikindo_files = self.crawl_gaikindo_files()
        results["sites"]["Gaikindo_Files"] = {
            "status": "success" if gaikindo_files else "failed",
            "files": len(gaikindo_files),
        }

        # NAAMSA 南非
        naamsa = self.crawl_naamsa_pdfs()
        if naamsa:
            results["sites"]["NAAMSA_South_Africa"] = {
                "status": "success",
                "pdfs": len(naamsa.get("pdfs", [])),
                "sales_pages": len(naamsa.get("sales_pages", [])),
            }
        else:
            results["sites"]["NAAMSA_South_Africa"] = {"status": "failed"}

        # 保存汇总
        self._save_json(results, "crawl_summary.json")
        return results


# ============================================================
# CLI 入口
# ============================================================
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    crawler = StatsCrawler()

    if len(sys.argv) > 1:
        target = sys.argv[1].lower()
        if target == "maa":
            data = crawler.crawl_maa()
            print(f"MAA: {len(data.get('production', {}))} prod years, {len(data.get('sales', {}))} sales years")
        elif target == "gaikindo":
            data = crawler.crawl_gaikindo_sales()
            print(f"Gaikindo: {len(data.get('brands', {}))} brands")
        elif target == "naamsa":
            data = crawler.crawl_naamsa_pdfs()
            print(f"NAAMSA: {len(data.get('pdfs', []))} PDFs")
        elif target == "all":
            results = crawler.crawl_all()
            for site, info in results.get("sites", {}).items():
                print(f"  {site}: {info}")
        else:
            print(f"Unknown target: {target}")
            print("Usage: python -m src.crawler.stats_crawler [maa|gaikindo|naamsa|all]")
    else:
        print("Usage: python -m src.crawler.stats_crawler [maa|gaikindo|naamsa|all]")
