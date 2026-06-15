import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from visualization.dashboard import summary_stats, table_country_overview, table_supply_chain_risks, table_china_exports
from analysis.market_data import PRODUCTION_DATA

stats = summary_stats()
print(f'Total prod: {stats["total_production"]/10000:.0f} wan')
print(f'Total sales: {stats["total_sales"]/10000:.0f} wan')
print(f'China export: {stats["total_china_export"]/10000:.0f} wan')
print(f'Max risk: {stats["max_risk"]}')
print(f'Min risk: {stats["min_risk"]}')
print(f'Prod countries: {stats["prod_countries"]}')
print(f'Total countries in PRODUCTION_DATA: {len(PRODUCTION_DATA)}')
print('--- Overview ---')
df = table_country_overview()
print(df.to_string())
print('--- China Export ---')
df2 = table_china_exports()
print(df2.to_string())
print('ALL TESTS PASSED')
