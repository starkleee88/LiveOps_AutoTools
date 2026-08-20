import csv
import os

func_file = r'excel\ActivityAllyFuncMain.csv'
print("=== ActivityAllyFuncMain - Superman pairs ===")
with open(func_file, 'r', encoding='utf-8-sig') as f:
    for i, row in enumerate(csv.reader(f)):
        if i < 3: continue  # Skip headers
        if len(row) > 4 and 'Superman' in row[4]:
            activity_id = row[0]
            hero_name = row[4]
            text_id = row[11] if len(row) > 11 else 'N/A'
            print(f"Activity_ID={activity_id}, Hero={hero_name}, TextID={text_id}")

print("\n=== Item.csv - Superman token mappings ===")
item_file = r'excel\Item.csv'
if os.path.exists(item_file):
    with open(item_file, 'r', encoding='utf-8-sig') as f:
        for row in csv.reader(f):
            if len(row) > 0 and row[0] in ['1110015', '1110025']:
                name_key = row[2] if len(row) > 2 else 'N/A'
                desc_key = row[3] if len(row) > 3 else 'N/A'
                print(f"Token {row[0]}: ItemName={name_key}, ItemDesc={desc_key}")

print("\n=== ActivityAllyLocal - Superman config ===")
local_file = r'excel\ActivityAllyLocal.csv'
if os.path.exists(local_file):
    with open(local_file, 'r', encoding='utf-8-sig') as f:
        for row in csv.reader(f):
            if len(row) > 1 and 'Superman' in row[1]:
                print(f"Activity_ID={row[0]}, HeroName={row[1]}, RuleBase={row[2]}, RBoss={row[3]}, RRank={row[4]}, RTower={row[5]}")
