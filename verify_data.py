import sys
sys.path.insert(0, r'C:\Users\song\Projects\global-auto-supply-chain\src\analysis')
from market_data import PRODUCTION_DATA, SALES_DATA, CHINA_EXPORT_TO_TARGET, BRAND_MARKET_SHARE, SUPPLY_CHAIN_RISK, EV_PENETRATION

countries = set(PRODUCTION_DATA.keys())
print(f'PRODUCTION_DATA: {len(countries)} countries: {sorted(countries)}')
print(f'SALES_DATA: {len(SALES_DATA)} countries: {sorted(SALES_DATA.keys())}')
skip_keys = {"source", "total_china_export_2025"}
export_keys = [k for k in CHINA_EXPORT_TO_TARGET if k not in skip_keys]
print(f'CHINA_EXPORT_TO_TARGET: {len(export_keys)} entries: {export_keys}')
print(f'BRAND_MARKET_SHARE: {len(BRAND_MARKET_SHARE)} countries: {sorted(BRAND_MARKET_SHARE.keys())}')
print(f'SUPPLY_CHAIN_RISK: {len(SUPPLY_CHAIN_RISK)} countries: {sorted(SUPPLY_CHAIN_RISK.keys())}')
print(f'EV_PENETRATION: {len(EV_PENETRATION)} countries: {sorted(EV_PENETRATION.keys())}')

missing_sales = countries - set(SALES_DATA.keys())
missing_ev = countries - set(EV_PENETRATION.keys())
missing_brand = countries - set(BRAND_MARKET_SHARE.keys())
missing_risk = countries - set(SUPPLY_CHAIN_RISK.keys())

if missing_sales or missing_ev or missing_brand or missing_risk:
    print(f'INCONSISTENCY: sales={missing_sales} ev={missing_ev} brand={missing_brand} risk={missing_risk}')
else:
    print('All data structures consistent across 13 countries')
