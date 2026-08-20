import csv

# Simulate the actual generation functions
def tao_data_cho_file_item(data):
    danh_sach = []
    tokens = data['Tokens'].split('|')
    
    # Determine if we reuse old text keys
    old_tokens = data.get('OldTokens', '').split('|') if data.get('OldTokens', '') else []
    use_old_keys = len(old_tokens) >= len(tokens)
    
    for i, tid in enumerate(tokens):
        t_type = "Common" if i == 0 else "Rare"
        name = f"{data['HeroName']} Event - {t_type} token"
        desc = f"Used in {data['HeroName']} Legendary Event"
        quality = 4 if i == 0 else 5
        
        # Use old text key if available and reusing
        if use_old_keys and i < len(old_tokens):
            name_key = f"ItemName{old_tokens[i]}"
            desc_key = f"ItemDesc{old_tokens[i]}"
        else:
            name_key = f"ItemName{tid}"
            desc_key = f"ItemDesc{tid}"
        
        danh_sach.append(f"{tid},{name},{name_key},{desc_key},{desc},1,,,,1,,,,,,4,4,{quality},15,ui_item_{tid},,,,,,3600\n")
    return "".join(danh_sach)

def tao_data_cho_file_local(data):
    base = int(data.get('RuleBaseID', '9000')) if str(data.get('RuleBaseID', '')).isdigit() else 9000
    r_boss = data.get('RBoss', str(base * 10 + 1))
    r_rank = data.get('RRank', str(base * 10 + 2))
    r_tower = data.get('RTower', str(base * 10 + 3))
    act_id = data['ActivityMainID']
    local_root = data.get('LocalRoot', f"AllyActivity_Info{data['AllyId']}")
    main_act_link = data.get('MainActLink', f"AllyActivity_{act_id}01")
    return f"{act_id},{data['HeroName']},{base},{r_boss},{r_rank},{r_tower},{local_root},{main_act_link},,,,VX_ActivityAllyBossWindow_151_01,VX_ActivityAllyBossWindow_151_02\n"

def tao_data_cho_file_source_item_desc(data):
    danh_sach = []
    hero = data['HeroName']
    evt = f"{hero} Legendary Event"
    
    # Item text - reuse old keys if available
    tokens = data.get('Tokens', '').split('|')
    old_tokens = data.get('OldTokens', '').split('|') if data.get('OldTokens', '') else []
    use_old_keys = len(old_tokens) >= len(tokens)
    
    for i in range(len(tokens)):
        if not tokens[i]:
            continue
        
        # Use old token key if reusing, otherwise use new token key
        key_token = old_tokens[i] if use_old_keys and i < len(old_tokens) else tokens[i]
        t_type = "Common Token" if i == 0 else "Rare Token"
        
        danh_sach.append(f"ItemName{key_token},Item Name,{evt},[NOT FINAL] {t_type},\n")
        danh_sach.append(f"ItemDesc{key_token},Item Desc,{evt},[NOT FINAL] Used in event\n")
    
    return "".join(danh_sach)

# Test data
test_data = {
    'ActivityMainID': '117',
    'HeroName': 'Superman DCU Re-Run',
    'AllyId': '13236',
    'Tokens': '1110025|1110026',
    'OldTokens': '1110015|1110016',
    'RuleBaseID': '9214',
    'RBoss': '92141',
    'RRank': '92142',
    'RTower': '92143',
    'LocalRoot': 'AllyActivity_Info13236',
    'MainActLink': 'AllyActivity_11701'
}

print("=" * 60)
print("SUPERMAN 117 RERUN OUTPUT TEST")
print("=" * 60)

print("\n[1] Item.csv OUTPUT:")
print("-" * 60)
item_out = tao_data_cho_file_item(test_data)
print(item_out)

print("[2] ActivityAllyLocal.csv OUTPUT:")
print("-" * 60)
local_out = tao_data_cho_file_local(test_data)
print(local_out)

print("[3] SourceItemDesc.csv OUTPUT:")
print("-" * 60)
source_out = tao_data_cho_file_source_item_desc(test_data)
print(source_out)

print("\n" + "=" * 60)
print("VERIFICATION RESULTS")
print("=" * 60)

checks = [
    ("Item uses old token keys", "ItemName1110015" in item_out and "ItemName1110016" in item_out),
    ("Local has new hero name", "Superman DCU Re-Run" in local_out),
    ("Local reuses config IDs", "9214,92141,92142,92143" in local_out),
    ("SourceItemDesc uses old keys", "ItemName1110015" in source_out and "ItemName1110016" in source_out),
]

for desc, result in checks:
    status = "✅ PASS" if result else "❌ FAIL"
    print(f"{status}: {desc}")

print("\nAll checks passed!" if all(r for _, r in checks) else "\nSome checks FAILED!")
