#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'c:\Users\gear\Desktop\LiveOps_AutoTool')

from main import tao_data_cho_file_item, tao_data_cho_file_local, tao_data_cho_file_source_item_desc
import datetime

# Simulate Superman 117 rerun data
test_data = {
    'ActivityMainID': '117',
    'HeroName': 'Superman DCU Re-Run',
    'AllyId': '13236',
    'Tokens': '1110025|1110026',
    'OldTokens': '1110015|1110016',  # From Superman 111
    'TextActivityMainID': '111',  # Old activity ID for text keys
    'RuleBaseID': '9214',
    'RBoss': '92141',
    'RRank': '92142',
    'RTower': '92143',
    'LocalRoot': 'AllyActivity_Info13236',
    'MainActLink': 'AllyActivity_11701',
    'EndTime': '20260201_235959'
}

print("=== TEST OUTPUT: Superman 117 Rerun ===\n")

print("1. Item.csv output:")
print("-" * 50)
item_output = tao_data_cho_file_item(test_data)
print(item_output[:200] + "..." if len(item_output) > 200 else item_output)

print("\n2. ActivityAllyLocal.csv output:")
print("-" * 50)
local_output = tao_data_cho_file_local(test_data)
print(local_output)

print("3. SourceItemDesc.csv output (partial):")
print("-" * 50)
source_output = tao_data_cho_file_source_item_desc(test_data)
print(source_output[:200] + "..." if len(source_output) > 200 else source_output)

# Verify the critical parts
print("\n=== VERIFICATION ===")
print("\n✓ Item.csv uses OLD text keys:")
if "ItemName1110015" in item_output and "ItemName1110016" in item_output:
    print("  ✅ Token 1110025 → ItemName1110015")
    print("  ✅ Token 1110026 → ItemName1110016")
else:
    print("  ❌ FAIL: Old text keys not found")

print("\n✓ ActivityAllyLocal has new hero name:")
if "Superman DCU Re-Run" in local_output:
    print("  ✅ Hero name: Superman DCU Re-Run")
else:
    print("  ❌ FAIL: New hero name not found")

print("\n✓ ActivityAllyLocal reuses config IDs:")
if "9214,92141,92142,92143" in local_output:
    print("  ✅ Config IDs reused: 9214,92141,92142,92143")
else:
    print("  ❌ FAIL: Config IDs mismatch")

print("\n✓ SourceItemDesc uses old token keys:")
if "ItemName1110015" in source_output and "ItemName1110016" in source_output:
    print("  ✅ Text entries use old token keys")
else:
    print("  ❌ FAIL: Old token keys not found in SourceItemDesc")
