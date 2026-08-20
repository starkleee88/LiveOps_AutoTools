import csv
import os
import re

def normalize_event_name(name):
    if not name:
        return ""
    normalized = name.strip().lower()
    normalized = re.sub(r"\s*\(re-?run(?:\s*s\d+)?\)$", "", normalized)
    normalized = re.sub(r"\s*re-?run(?:\s*s\d+)?$", "", normalized)
    normalized = re.sub(r"\s*\(replica\)$", "", normalized)
    return normalized.strip()

def tim_old_activity_main_id(hero_name, ally_id, current_main_id):
    main_file = r'excel\ActivityAllyFuncMain.csv'
    try:
        current_id = int(current_main_id)
    except:
        return None
    
    current_key = normalize_event_name(hero_name)
    previous_ids = []
    with open(main_file, 'r', encoding='utf-8-sig') as f:
        for row in csv.reader(f):
            if len(row) < 8:
                continue
            row_id = row[0].strip()
            row_hero = row[1].strip()
            row_ally = row[7].strip()
            if not row_id.isdigit():
                continue
            
            row_id_int = int(row_id)
            if row_id_int >= current_id:
                continue
            
            if row_ally == ally_id or normalize_event_name(row_hero) == current_key:
                previous_ids.append(row_id_int)
                print(f"  Found match: ID={row_id}, Hero={row_hero}, Ally={row_ally}")
    
    if not previous_ids:
        return None
    return str(max(previous_ids))

# Test Superman rerun
print("=== TEST: Superman DCU Re-Run (Activity 117) ===")
hero_name = "Superman DCU Re-Run"
ally_id = "13236"
current_main_id = "117"

print(f"\nInput:")
print(f"  Hero: {hero_name}")
print(f"  AllyId: {ally_id}")
print(f"  Current ActivityID: {current_main_id}")

print(f"\nNormalized hero name: '{normalize_event_name(hero_name)}'")

print(f"\nSearching for old activity...")
old_id = tim_old_activity_main_id(hero_name, ally_id, current_main_id)
print(f"Old activity ID found: {old_id}")

if old_id:
    # Extract old tokens
    old_func_file = r'excel\ActivityAllyFuncMain.csv'
    with open(old_func_file, 'r', encoding='utf-8-sig') as f:
        for row in csv.reader(f):
            if len(row) > 0 and row[0].strip() == old_id:
                old_tokens = row[11].strip() if len(row) > 11 else ''
                print(f"\nOld activity row found:")
                print(f"  ID: {row[0]}")
                print(f"  Hero: {row[1]}")
                print(f"  Tokens: {old_tokens}")
                
                # Simulate current tokens
                current_tokens = "1110025|1110026"
                print(f"\nCurrent tokens: {current_tokens}")
                
                if old_tokens:
                    old_tokens_list = old_tokens.split('|')
                    current_tokens_list = current_tokens.split('|')
                    
                    print(f"\nItem rows that would be generated:")
                    for i, tid in enumerate(current_tokens_list):
                        t_type = "Common" if i == 0 else "Rare"
                        old_token = old_tokens_list[i] if i < len(old_tokens_list) else tid
                        name_key = f"ItemName{old_token}"
                        desc_key = f"ItemDesc{old_token}"
                        print(f"  Token {tid}: {name_key}, {desc_key}")
                break

print("\n=== ActivityAllyLocal generation test ===")
local_file = r'excel\ActivityAllyLocal.csv'
with open(local_file, 'r', encoding='utf-8-sig') as f:
    for row in csv.reader(f):
        if len(row) > 1 and row[0].strip() == '111':
            print(f"\nOrigin (Activity 111):")
            print(f"  Activity: {row[0]}, Hero: {row[1]}")
            print(f"  Config: RuleBase={row[2]}, RBoss={row[3]}, RRank={row[4]}, RTower={row[5]}")
            base_config = (row[2], row[3], row[4], row[5])
        elif len(row) > 1 and row[0].strip() == '117':
            print(f"\nRerun (Activity 117) - current data:")
            print(f"  Activity: {row[0]}, Hero: {row[1]}")
            print(f"  Config: RuleBase={row[2]}, RBoss={row[3]}, RRank={row[4]}, RTower={row[5]}")
            
print(f"\nExpected rerun generation (activity 117):")
print(f"  New Hero: Superman DCU Re-Run")
print(f"  Reused Config: RuleBase={base_config[0]}, RBoss={base_config[1]}, RRank={base_config[2]}, RTower={base_config[3]}")
