# Scrapling 爬虫使用指南 — 全球汽车供应链项目

> 版本：v1.0 | 更新日期：2026-06-18 | 项目：global-auto-supply-chain

---

## 一、Scrapling 是什么

[Scrapling](https://github.com/D4Vinci/Scrapling) 是一个 Python 网页抓取框架（v0.4.9），核心能力：

| 能力 | 说明 | 对项目的价值 |
|------|------|-------------|
| **Fetcher** | 基于 curl_cffi 的 HTTP 客户端，自动模拟 TLS 指纹 | 国内网络下可直接用，绕过基础指纹检测 |
| **StealthyFetcher** | 基于 patchright（Chromium）的浏览器自动化 | 海外/VPS 环境下可绕过 Akamai/Cloudflare |
| **CSS 选择器** | `page.css('selector')` 一行提取 | 协会统计页面表格提取极高效 |
| **`get_all_text()`** | 自动提取元素全部文本 | 文章型页面数据提取无需逐标签解析 |
| **自动编码/解析** | 底层用 lxml，自动处理编码 | 东南亚/中东多语言站点无乱码 |

**核心判断**：Scrapling 的价值在**数据提取能力**，不在反爬绕过。国内网络环境下 Fetcher 和 requests 差不多，但提取 API 远比 BeautifulSoup 好用。

---

## 二、项目中的爬虫架构

```
src/crawler/
├── __init__.py           # 统一导出
├── base.py               # 爬虫基类 + CrawlResult 数据结构
├── stats_crawler.py      # ✅ 协会统计数据爬虫（国内可用）
├── scrapling_crawler.py  # ⚠️ 交易类平台爬虫（需海外网络）
└── apify_crawler.py      # 💰 Apify 云爬虫备选（需付费 Token）
```

**三种爬虫，三种使用场景：**

| 爬虫 | 网络要求 | 目标站点 | 当前状态 |
|------|---------|---------|---------|
| `StatsCrawler` | 国内直连 | 协会统计网站 | ✅ 已验证可用 |
| `MobileDeCrawler` 等 | 海外/VPS + 住宅IP | 交易平台 | ⚠️ 国内被拦截 |
| `ApifyCrawler` | 无限制（云端执行） | 任意网站 | 💰 需付费 |

---

## 三、StatsCrawler 使用方法（推荐）

### 3.1 安装

```bash
# 基础安装（Fetcher 模式，国内可用）
pip install scrapling

# 完整安装（含 StealthyFetcher，需海外网络下载浏览器驱动）
pip install scrapling[all]
```

### 3.2 快速开始

**Python API：**

```python
from src.crawler.stats_crawler import StatsCrawler

crawler = StatsCrawler()

# 单站点爬取
maa_data = crawler.crawl_maa()           # 马来西亚 MAA
gaikindo_data = crawler.crawl_gaikindo_sales()  # 印尼 Gaikindo
naamsa_data = crawler.crawl_naamsa_pdfs()       # 南非 NAAMSA

# 一键全站爬取
results = crawler.crawl_all()
# 输出示例：
# MAA_Malaysia: {'status': 'success', 'production_years': 14, 'sales_years': 14}
# Gaikindo_Indonesia: {'status': 'success', 'brands': 10}
# Gaikindo_Files: {'status': 'success', 'files': 21}
# NAAMSA_South_Africa: {'status': 'success', 'pdfs': 2, 'sales_pages': 6}
```

**命令行：**

```bash
# 单站点
python -m src.crawler.stats_crawler maa
python -m src.crawler.stats_crawler gaikindo
python -m src.crawler.stats_crawler naamsa

# 全站
python -m src.crawler.stats_crawler all
```

### 3.3 各站点爬取详情

#### MAA 马来西亚 — HTML 表格提取

```
URL:     https://www.maa.org.my/statistics.html
方法:    Fetcher.get() → r.css('table') → 逐行解析 td/th
输出:    data/crawled/maa_malaysia_real_data.json
数据:    2010-2023年 产量+销量（乘用车/商用车/合计）
验证:    ✅ 14年产量 + 14年销量，数据与官网完全一致
```

**提取逻辑核心代码：**

```python
r = Fetcher.get(url, stealthy_headers=True, timeout=30000)
tables = r.css('table')
for table in tables:
    rows = table.css('tr')
    for row in rows:
        cells = row.css('td, th')
        row_data = [cell.get_all_text().strip() for cell in cells]
        # 解析: [年份, 乘用车, 商用车, 合计]
        year = int(row_data[0])
        passenger = int(row_data[1].replace(',', ''))
        commercial = int(row_data[2].replace(',', ''))
        total = int(row_data[3].replace(',', ''))
```

**数据示例（2023年）：**

```json
{
  "production": {
    "2023": {"passenger": 719160, "commercial": 80571, "total": 799731}
  },
  "sales": {
    "2023": {"passenger": 724891, "commercial": 49709, "total": 774600}
  }
}
```

#### Gaikindo 印尼 — 文章正文提取

```
URL:     https://www.gaikindo.or.id/（新闻稿文章页面）
方法:    Fetcher.get() → r.get_all_text() → 正则提取品牌+销量
输出:    data/crawled/gaikindo_indonesia_real_data.json
数据:    2026年1-5月 Top10 品牌批发销量
验证:    ✅ 10个品牌，总批发量 359,015 辆（YoY +14%）
```

**提取逻辑核心代码：**

```python
r = Fetcher.get(url, stealthy_headers=True, timeout=30000)
all_text = r.get_all_text()
# 正则匹配 "Toyota: 111.119 unit" 格式（印尼数字用.作千分位）
brand_pattern = re.compile(r'(Toyota|BYD|...):\s*([\d.]+)\s*unit', re.IGNORECASE)
for match in brand_pattern.finditer(all_text):
    brand = match.group(1)
    units = int(match.group(2).replace('.', ''))  # 111.119 → 111119
```

**数据示例：**

```json
{
  "brands": {
    "Toyota": 111119, "Daihatsu": 59420, "Suzuki": 30262,
    "Mitsubishi Motors": 28445, "Honda": 18271, "BYD": 17993,
    "Jaecoo": 14284, "Mitsubishi Fuso": 13459, "Isuzu": 10820, "Hino": 8341
  },
  "total_whole_sales_jan_may_2026": 359015,
  "yoy_growth_pct": 14.0
}
```

**文件列表爬取：**

```python
# 获取 Gaikindo 历年 PDF 文件列表（production/wholesale/export/import）
files = crawler.crawl_gaikindo_files()
# 输出: data/crawled/gaikindo_file_links.json（21个2024-2026年文件）
```

> ⚠️ 文件下载链接是 JS 动态生成的，Fetcher 只能获取文件名列表，实际下载 PDF 需 StealthyFetcher + 海外 IP。

#### NAAMSA 南非 — PDF 报告链接提取

```
URL:     https://naamsa.net/
方法:    Fetcher.get() → r.css('a[href$=".pdf"]') + r.css('a')
输出:    data/crawled/naamsa_south_africa_links.json
数据:    月度 Flash Report + Media Release PDF 链接 + 数据页面链接
验证:    ✅ 2个PDF + 6个数据页面
```

**提取逻辑核心代码：**

```python
r = Fetcher.get(url, stealthy_headers=True, timeout=30000)
# PDF 链接
pdf_links = r.css('a[href$=".pdf"]')
for link in pdf_links:
    href = link.attrib.get('href', '')
    text = link.get_all_text().strip()
# 数据页面链接（含 sales/export/import/domestic 关键词）
all_links = r.css('a')
for a in all_links:
    if any(kw in a.get_all_text().lower() for kw in ['sales', 'export', 'import']):
        ...
```

> ⚠️ NAAMSA 数据页面是 SPA/JS 渲染，Fetcher 只能获取导航链接和 PDF 地址，表格数据需要 StealthyFetcher 或 PDF 解析。

---

## 四、数据集成到项目

### 4.1 数据流向

```
Scrapling Fetcher → data/crawled/*.json → market_data.py → dashboard.py
     (爬取)          (原始数据存储)      (数据清洗+结构化)   (可视化)
```

### 4.2 已集成的真实数据

在 `src/analysis/market_data.py` 中：

| 国家 | 数据维度 | 爬取来源 | 集成方式 |
|------|---------|---------|---------|
| 马来西亚 | 产量 2020-2023 | MAA 官网 | 直接替换估算值 |
| 马来西亚 | 销量 2020-2023 | MAA 官网 | 直接替换估算值 |
| 印尼 | 品牌份额 Top10 | Gaikindo 新闻稿 | 更新为 2026 年最新数据 |

**`CRAWLED_DATA_SOURCES` 字典**记录所有爬取数据的来源、方法、日期，可追溯：

```python
CRAWLED_DATA_SOURCES = {
    "MAA_Malaysia": {
        "source": "MAA 官网统计页",
        "crawl_date": "2026-06-18",
        "method": "Scrapling Fetcher (HTML表格提取)",
        "raw_file": "data/crawled/maa_malaysia_real_data.json",
    },
    "Gaikindo_Indonesia": { ... },
    "Gaikindo_Files": { ... },
}
```

### 4.3 手动更新数据流程

```bash
# 1. 运行爬虫获取最新数据
python -m src.crawler.stats_crawler all

# 2. 检查输出
ls data/crawled/

# 3. 如果数据有变化，更新 market_data.py 中对应的数据
#    （将新年份的数据添加到 PRODUCTION_DATA / SALES_DATA 等）
#    已爬取的数据标记 data_quality = "crawled_verified"

# 4. 提交推送，Streamlit Cloud 自动重部署
git add -A && git commit -m "data: update crawled data" && git push
```

---

## 五、实测站点清单

### 5.1 ✅ 国内网络可用（Fetcher 模式）

| 站点 | URL | 数据类型 | 提取难度 | 输出 |
|------|-----|---------|---------|------|
| MAA 马来西亚 | maa.org.my/statistics.html | 产量/销量 HTML 表格 | ⭐ 简单 | 14年×2表 |
| Gaikindo 印尼 | gaikindo.or.id/（新闻稿） | 品牌销量文章正文 | ⭐⭐ 中等 | 10品牌 |
| Gaikindo 文件 | files.gaikindo.or.id | PDF 文件列表 | ⭐ 简单 | 21文件 |
| NAAMSA 南非 | naamsa.net | PDF 链接+导航链接 | ⭐ 简单 | 2PDF+6页 |
| CAAM 中国 | caam.org.cn | 新闻标题列表 | ⭐⭐ 中等 | 无结构化数据 |
| FTI 泰国 | fti.or.th | 首页可达 | ⭐⭐⭐ 需深挖 | 暂无 |
| ODD 土耳其 | oddd.org.tr | 统计页可达 | ⭐⭐⭐ 需深挖 | 暂无 |

### 5.2 ❌ 国内网络不可用

| 站点 | 拦截类型 | 状态码 | 说明 |
|------|---------|-------|------|
| mobile.de | Akamai JS Challenge | 200 (2576B 空壳) | 需住宅代理 IP |
| OLX Brasil | Cloudflare | 200 (2MB 拦截页) | 需住宅代理 IP |
| sahibinden.com | WAF 403 | 403 | 需住宅代理 IP |
| otomoto.pl | Cloudflare | 403 | 需住宅代理 IP |
| AMIA 墨西哥 | Cloudflare | 403 | 需海外 IP |
| INEGI 墨西哥 | 超时 | — | 国内无法连接 |
| ANFAVEA 巴西 | 404 | 404 | URL 已失效 |
| AUTOSTAT 俄罗斯 | 404 | 404 | URL 已失效 |
| ANAC 智利 | 404 | 404 | URL 已失效 |
| OICA 全球 | 403 | 403 | 需海外 IP |

### 5.3 部分可用（需进一步处理）

| 站点 | 说明 |
|------|------|
| NAAMSA 南非 | 数据页面是 SPA/JS 渲染，Fetcher 只获取空壳，需 StealthyFetcher 或 PDF 解析 |
| Gaikindo 印尼 | PDF 下载链接 JS 动态生成，需 StealthyFetcher |
| CAAM 中国 | 数据需登录/付费，公开页只有新闻标题 |

---

## 六、Fetcher vs StealthyFetcher 选择指南

```
目标站点是否有反爬？
├── 否（协会统计网站）→ Fetcher（国内直连可用）
│   ├── HTML 表格 → r.css('table')
│   ├── 文章正文 → r.get_all_text()
│   └── 链接列表 → r.css('a')
│
└── 是（交易平台/高安全站点）
    ├── 国内网络 → ❌ 放弃，换数据源或用 Apify
    └── 海外/VPS
        ├── Akamai/Cloudflare → StealthyFetcher + 住宅代理 IP
        └── 中等反爬 → StealthyFetcher（可能够用）
```

**关键结论**：

- **Fetcher**：国内直接用，零配置，适合协会/政府统计网站
- **StealthyFetcher**：需海外环境 + 浏览器驱动（~300MB），仍可能被 Akamai 拦截
- 国内 IP 是硬伤：Akamai/Cloudflare 检测的是 IP 信誉而非浏览器指纹

---

## 七、扩展新站点的步骤

以添加 "AMIA 墨西哥" 为例：

### 步骤 1：确认站点可达性

```python
from scrapling.fetchers import Fetcher
r = Fetcher.get("https://amia.com.mx/", stealthy_headers=True, timeout=30000)
print(f"Status: {r.status}, Length: {len(r.text)}")
# 如果 403 或内容异常 → 该站点国内不可用
```

### 步骤 2：在 StatsCrawler 中添加方法

```python
def crawl_amia(self) -> dict:
    """爬取 AMIA 墨西哥汽车工业协会数据"""
    url = "https://amia.com.mx/"
    r = self.fetcher.get(url, stealthy_headers=True, timeout=30000)
    if r.status != 200:
        return {}
    
    # 分析页面结构，编写提取逻辑
    tables = r.css('table')
    # ... 解析逻辑 ...
    
    self._save_json(result, "amia_mexico_real_data.json")
    return result
```

### 步骤 3：注册到 crawl_all()

```python
def crawl_all(self) -> dict:
    # ... 现有站点 ...
    
    # AMIA 墨西哥
    amia = self.crawl_amia()
    if amia:
        results["sites"]["AMIA_Mexico"] = {"status": "success", ...}
    else:
        results["sites"]["AMIA_Mexico"] = {"status": "failed"}
    
    return results
```

### 步骤 4：集成到 market_data.py

```python
# 在 CRAWLED_DATA_SOURCES 添加
"AMIA_Mexico": {
    "source": "AMIA 墨西哥汽车工业协会",
    "url": "https://amia.com.mx/",
    "crawl_date": "2026-06-XX",
    "method": "Scrapling Fetcher",
    "raw_file": "data/crawled/amia_mexico_real_data.json",
}

# 更新 PRODUCTION_DATA["Mexico"] 中的真实数据
# 修改 data_quality 为 "crawled_verified"
```

---

## 八、定时爬取方案（建议）

### 方案 A：GitHub Actions（推荐）

在 `.github/workflows/crawl.yml` 中配置定时任务：

```yaml
name: Monthly Data Crawl
on:
  schedule:
    - cron: '0 2 1 * *'  # 每月1号 UTC 02:00
  workflow_dispatch:       # 手动触发

jobs:
  crawl:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install scrapling
      - run: python -m src.crawler.stats_crawler all
      - name: Commit & Push
        run: |
          git config user.name "Crawl Bot"
          git config user.email "bot@example.com"
          git add data/crawled/
          git diff --cached --quiet || git commit -m "data: monthly crawl update"
          git push
```

**优势**：GitHub Actions 服务器在海外，Fetch 和 StealthyFetcher 都能用。

### 方案 B：本地定时任务

```bash
# Windows Task Scheduler
schtasks /create /tn "AutoDataCrawl" /tr "python -m src.crawler.stats_crawler all" /sc monthly /d 1 /st 10:00

# Linux cron
0 10 1 * * cd /path/to/project && python -m src.crawler.stats_crawler all
```

---

## 九、常见问题

### Q1: Fetcher 返回 503/403 怎么办？
- 确认站点是否在国内可访问（浏览器先试）
- 尝试加 `stealthy_headers=True` 参数
- 如果仍然被拦截，该站点国内不可用，换海外环境或换数据源

### Q2: StealthyFetcher 进程被 SIGKILL？
- 检查内存：浏览器实例约 200-500MB，确保系统有足够 RAM
- 检查浏览器驱动：运行 `python -c "from scrapling.fetchers import StealthyFetcher; StealthyFetcher.fetch('https://httpbin.org/ip')"` 测试
- 国内下载浏览器驱动可能失败，需手动安装 patchright

### Q3: 数据提取结果为空？
- 先 `print(r.text[:1000])` 查看实际返回内容
- 可能是 JS 渲染页面，Fetcher 只拿到空壳 → 需要 StealthyFetcher
- 可能是 URL 变更或页面结构变化 → 手动浏览器检查

### Q4: 如何获取交易类平台数据（mobile.de 等）？
- **方案 1**：海外 VPS + StealthyFetcher + 住宅代理 IP
- **方案 2**：Apify 云爬虫（付费，约 $5/月起）
- **方案 3**：直接购买数据（MarkLines 等平台）

---

## 十、文件索引

| 文件 | 说明 |
|------|------|
| `src/crawler/stats_crawler.py` | 协会统计数据爬虫（主要使用） |
| `src/crawler/scrapling_crawler.py` | 交易类平台爬虫（需海外网络） |
| `src/crawler/base.py` | 爬虫基类 + 数据结构定义 |
| `src/crawler/apify_crawler.py` | Apify 云爬虫备选 |
| `src/analysis/market_data.py` | 数据存储 + CRAWLED_DATA_SOURCES |
| `data/crawled/maa_malaysia_real_data.json` | MAA 爬取原始数据 |
| `data/crawled/gaikindo_indonesia_real_data.json` | Gaikindo 爬取原始数据 |
| `data/crawled/gaikindo_file_links.json` | Gaikindo 文件列表 |
| `data/crawled/naamsa_south_africa_links.json` | NAAMSA 链接数据 |
| `data/crawled/crawl_summary.json` | 最近一次全站爬取汇总 |
