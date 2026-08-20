import os
import csv
import re
import stat 
import json 
import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime, timedelta

import sys

# Kiểm tra xem app đang chạy bằng file .exe hay file .py
if getattr(sys, 'frozen', False):
    # Nếu là .exe, lấy thư mục chứa file .exe đó
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    # Nếu là .py, lấy thư mục chứa file .py
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(SCRIPT_DIR, "liveops_config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Lỗi lưu config:", e)


def tim_enemy_group_cu(thu_muc_goc, boss_id):
    group_file = os.path.join(thu_muc_goc, "EnemyGroup.csv")
    if not os.path.exists(group_file):
        return None

    with open(group_file, 'r', encoding='utf-8-sig') as f:
        for row in csv.reader(f):
            if len(row) > 5 and row[5].strip() == boss_id:
                return row[0].strip()
    return None


def tim_boss_cu(thu_muc_goc, hero_name, ally_id):
    boss_file = os.path.join(thu_muc_goc, "Enemies", "EnemyEventBoss.csv")
    if not os.path.exists(boss_file):
        return None, None, None, None

    matched = None
    hero_key = normalize_hero_key(hero_name)
    with open(boss_file, 'r', encoding='utf-8-sig') as f:
        for row in csv.reader(f):
            if len(row) < 12:
                continue
            row_ally = row[1].strip()
            row_hero = row[3].strip()
            if is_rerun_event(row_hero):
                continue
            if row_ally == ally_id:
                matched = row
                break
            if normalize_hero_key(row_hero) == hero_key and not matched:
                matched = row

    if not matched:
        return None, None, None, None

    boss_id = matched[0].strip()
    boss_skill = matched[10].strip()
    boss_warning = matched[11].strip()
    group_id = tim_enemy_group_cu(thu_muc_goc, boss_id)
    return boss_id, boss_skill, boss_warning, group_id


def tim_boss_skill_show_cu(thu_muc_goc, boss_id, hero_name):
    """Get both BossSkillShow fields from the original (non-rerun) BossInfo row."""
    boss_info_file = os.path.join(thu_muc_goc, "ActivityAllyBossInfo.csv")
    if not os.path.exists(boss_info_file) or not boss_id:
        return "", ""

    hero_key = normalize_hero_key(hero_name)
    with open(boss_info_file, "r", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) <= 13 or row[1].strip() != str(boss_id).strip():
                continue
            row_hero = row[4].strip()
            if is_rerun_event(row_hero):
                continue
            if hero_key and normalize_hero_key(row_hero) != hero_key:
                continue
            return row[12].strip(), row[13].strip()
    return "", ""


def tim_item_icons_cu(thu_muc_goc, item_ids):
    """Return the actual icon values for reused item IDs from Item.csv."""
    item_file = os.path.join(thu_muc_goc, "Item.csv")
    wanted_ids = {str(item_id).strip() for item_id in item_ids if str(item_id).strip()}
    if not wanted_ids or not os.path.exists(item_file):
        return {}

    icons = {}
    with open(item_file, "r", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) > 19 and row[0].strip() in wanted_ids:
                icons[row[0].strip()] = row[19].strip()
    return icons


def tim_shop_text_ids_cu(thu_muc_goc, old_activity_id):
    """Find the original free/paid shopname IDs for an activity."""
    shop_file = os.path.join(thu_muc_goc, "Shop.csv")
    if not old_activity_id or not os.path.exists(shop_file):
        return "", ""

    free_shop_text_id, paid_shop_text_id = "", ""
    activity_link = f"{old_activity_id}02"
    with open(shop_file, "r", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) <= 6 or row[6].strip() != activity_link:
                continue
            shop_type = row[1].strip()
            text_key = row[3].strip()
            if not text_key.startswith("shopname"):
                continue
            text_id = text_key[len("shopname"):]
            if shop_type == "6":
                free_shop_text_id = text_id
            elif shop_type == "8":
                paid_shop_text_id = text_id
    return free_shop_text_id, paid_shop_text_id


def tim_gacha_text_key_cu(thu_muc_goc, old_activity_id):
    """Find the AllyGachaType localization key belonging to an original event."""
    main_file = os.path.join(thu_muc_goc, "ActivityAllyFuncMain.csv")
    gacha_type_file = os.path.join(thu_muc_goc, "AllyGachaType.csv")
    if not old_activity_id or not os.path.exists(main_file) or not os.path.exists(gacha_type_file):
        return ""

    old_start, old_ally_id = "", ""
    with open(main_file, "r", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) > 7 and row[0].strip() == str(old_activity_id).strip():
                old_start, old_ally_id = row[2].strip(), row[7].strip()
                break
    if not old_start or not old_ally_id:
        return ""

    with open(gacha_type_file, "r", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if len(row) <= 26:
                continue
            if not row[1].strip().lower().startswith("legendary event") or is_rerun_event(row[1].strip()):
                continue
            if row[7].strip() == old_ally_id and row[11].strip() == old_start:
                return row[26].strip()
    return ""


def tim_local_cu(thu_muc_goc, hero_name, ally_id):
    local_file = os.path.join(thu_muc_goc, "ActivityAllyLocal.csv")
    if not os.path.exists(local_file):
        return None

    with open(local_file, 'r', encoding='utf-8-sig') as f:
        for row in csv.reader(f):
            if len(row) < 8:
                continue
            row_hero = row[1].strip()
            row_info = row[6].strip()
            if is_rerun_event(row_hero):
                continue
            if row_hero == hero_name or row_info == f"AllyActivity_Info{ally_id}":
                return {
                    "RuleBaseID": row[2].strip(),
                    "RBoss": row[3].strip(),
                    "RRank": row[4].strip(),
                    "RTower": row[5].strip(),
                    "LocalRoot": row[6].strip(),
                    "MainActLink": row[7].strip()
                }
    return None

def normalize_event_name(name):
    if not name:
        return ""
    normalized = name.strip().lower()
    normalized = re.sub(r"\s*\(re-?run(?:\s*s\d+)?\)$", "", normalized)
    normalized = re.sub(r"\s*re-?run(?:\s*s\d+)?$", "", normalized)
    normalized = re.sub(r"\s*\(replica\)$", "", normalized)
    return normalized.strip()


def is_rerun_event(name):
    """True for display names such as 'Black Lightning Rerun' or '_Rerun'."""
    normalized = re.sub(r"[_()\-]+", " ", str(name or "").strip().lower()).strip()
    return bool(re.search(r"re\s*run(?:\s*s\d+)?$", normalized))


def normalize_hero_key(name):
    """Normalize display names so 'Black Lightning' matches 'BlackLightning'."""
    normalized = str(name or "").replace("_", " ").strip().lower()
    normalized = re.sub(r"\s*re-?run(?:\s*s\d+)?$", "", normalized)
    return re.sub(r"[^a-z0-9]+", "", normalized)


def tim_banner_reward_rerun(thu_muc_goc, hero_name, ally_id, start_time):
    """Return the Legendary/Epic reward IDs from the nearest earlier event for a hero.

    The lookup joins AllyGachaType to AllyGachaBranch by sub-card-pool ID.
    Only rows named 'Legendary Event ...' are eligible, preventing a 24hr
    Mother Box for the same hero from being selected as the rerun source.
    """
    type_path = os.path.join(thu_muc_goc, "AllyGachaType.csv")
    branch_path = os.path.join(thu_muc_goc, "AllyGachaBranch.csv")
    if not os.path.exists(type_path) or not os.path.exists(branch_path):
        return None

    try:
        with open(branch_path, "r", encoding="utf-8-sig", newline="") as f:
            branch_rows = list(csv.reader(f))
        branch_by_id = {
            row[0].strip(): row[12].strip()
            for row in branch_rows
            if len(row) > 12 and row[0].strip() and "|" in row[12]
        }

        hero_key = normalize_hero_key(hero_name)
        candidates = []
        with open(type_path, "r", encoding="utf-8-sig", newline="") as f:
            type_rows = list(csv.reader(f))

        for row in type_rows[1:]:
            # ID, display name, branch ID, UpHero, and OpenTime are required.
            if len(row) <= 11:
                continue
            display_name = row[1].strip()
            branch_id = row[2].strip()
            row_ally_id = row[7].strip()
            open_time = row[11].strip()
            display_key = normalize_hero_key(display_name.replace("Legendary Event", "", 1))

            if not display_name.lower().startswith("legendary event"):
                continue
            if is_rerun_event(display_name):
                continue
            if ally_id and row_ally_id != str(ally_id).strip():
                continue
            if hero_key and hero_key not in display_key:
                continue
            if not open_time or (start_time and open_time >= str(start_time).strip()):
                continue
            if branch_id not in branch_by_id:
                continue
            candidates.append((open_time, branch_by_id[branch_id]))

        if not candidates:
            return None

        _, gacha_value = max(candidates, key=lambda item: item[0])
        entries = gacha_value.split(";")
        if len(entries) < 2:
            return None
        legendary_id = entries[0].split("|", 1)[0].strip()
        epic_id = entries[1].split("|", 1)[0].strip()
        return (legendary_id, epic_id) if legendary_id and epic_id else None
    except (OSError, csv.Error):
        return None


def tim_old_activity_main_id(thu_muc_goc, hero_name, ally_id, current_main_id):
    main_file = os.path.join(thu_muc_goc, "ActivityAllyFuncMain.csv")
    if not os.path.exists(main_file):
        return None

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
            if is_rerun_event(row_hero):
                continue

            row_id_int = int(row_id)
            if row_id_int >= current_id:
                continue

            if row_ally == ally_id or normalize_event_name(row_hero) == current_key:
                previous_ids.append(row_id_int)

    if not previous_ids:
        return None
    return str(max(previous_ids))

# ==========================================
# PHẦN 1: BỘ QUÉT REWARD SIÊU CẤP (MANUAL SCANNER)
# ==========================================
def doc_file_reward(filepath):
    bo_suu_tap_reward = {
        "Sign": {},       
        "BossRank": {},   
        "BossScore": {},
        "GachaLegendary": "", 
        "GachaEpic": "",      
        "Tasks": [],
        "TowerRwd1": "", 
        "TowerRwd2": "", 
        "TowerRwd3": ""   
    }
    
    if not os.path.exists(filepath):
        return bo_suu_tap_reward

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            return bo_suu_tap_reward
            
        try:
            idx_reward = headers.index('RewardID')
            idx_note = headers.index('O')
        except ValueError:
            return bo_suu_tap_reward 
            
        for row in reader:
            if len(row) <= max(idx_reward, idx_note):
                continue
                
            note = str(row[idx_note]).lower()
            reward_id = str(row[idx_reward]).strip()
            
            if not reward_id or reward_id in ('Reward ID', 'int'):
                continue

            if ('check in' in note or 'sign in' in note) and 'day' in note:
                match = re.search(r'day\s*(\d+)', note)
                if match: bo_suu_tap_reward["Sign"][int(match.group(1))] = reward_id
            
            elif 'boss score' in note:
                match = re.search(r'score\s*(\d+)', note)
                if match: bo_suu_tap_reward["BossScore"][int(match.group(1))] = reward_id
            
            elif 'boss rank' in note:
                if '3001-5000' in note: bo_suu_tap_reward["BossRank"][5000] = reward_id
                elif '2001-3000' in note: bo_suu_tap_reward["BossRank"][3000] = reward_id
                elif '1001-2000' in note: bo_suu_tap_reward["BossRank"][2000] = reward_id
                elif '501-1000' in note: bo_suu_tap_reward["BossRank"][1000] = reward_id
                elif '201-500' in note: bo_suu_tap_reward["BossRank"][500] = reward_id
                elif '51-200' in note: bo_suu_tap_reward["BossRank"][200] = reward_id
                elif '11-50' in note: bo_suu_tap_reward["BossRank"][50] = reward_id
                elif '4-10' in note: bo_suu_tap_reward["BossRank"][10] = reward_id
                elif 'rank 3' in note: bo_suu_tap_reward["BossRank"][3] = reward_id
                elif 'rank 2' in note: bo_suu_tap_reward["BossRank"][2] = reward_id
                elif 'rank 1 ' in note or note.endswith('rank 1'): bo_suu_tap_reward["BossRank"][1] = reward_id
                    
            elif 'banner - legendary' in note:
                bo_suu_tap_reward["GachaLegendary"] = reward_id
            elif 'banner - epic' in note:
                bo_suu_tap_reward["GachaEpic"] = reward_id
                
            elif 'legendary event - d' in note or 'legendary event - s' in note:
                bo_suu_tap_reward["Tasks"].append(reward_id)
                
            elif 'tower reward 1' in note:
                bo_suu_tap_reward["TowerRwd1"] = reward_id
            elif 'tower reward 2' in note:
                bo_suu_tap_reward["TowerRwd2"] = reward_id
            elif 'tower reward 3' in note:
                bo_suu_tap_reward["TowerRwd3"] = reward_id

    return bo_suu_tap_reward

# ==========================================
# PHẦN 2: CÁC HÀM XỬ LÝ NGÀY THÁNG
# ==========================================
def tinh_thoi_gian_som(end_time_str):
    # Ở season mới không cần kết thúc sớm 1 ngày nữa
    return end_time_str

def tinh_thoi_gian_thap(start_time_str):
    try:
        dt = datetime.strptime(start_time_str, "%Y%m%d_%H%M%S")
        t2 = (dt + timedelta(days=1)).strftime("%Y%m%d_%H%M%S")
        t3 = (dt + timedelta(days=2)).strftime("%Y%m%d_%H%M%S")
        return start_time_str, t2, t3
    except:
        return start_time_str, start_time_str, start_time_str

# ==========================================
# PHẦN 3: CÁC HÀM ĐỊNH DẠNG DATA (25 MODULES)
# ==========================================
def tao_data_cho_file_main(data):
    hero_id = data['HeroName'].replace(' ', '')
    text_main_id = data.get('TextActivityMainID', data['ActivityMainID'])
    return f"{data['ActivityMainID']},{data['HeroName']},{data['StartTime']},{data['EndTime']},AllyActivity_{text_main_id},1,530,{data['AllyId']},{data['GachaJumpId']},{data['GiftJumpId']},ActivityAllyWindow_{hero_id},{data['Tokens']},\n"

def tao_data_cho_file_sub(data):
    hero_id = data['HeroName'].replace(' ', '')
    danh_sach = []
    end_time_som = tinh_thoi_gian_som(data['EndTime'])
    text_base = int(data.get('TextActivityMainID', data['ActivityMainID']))
    config_type = {
        1: ("Sign In", f"ActivityAllySignInPanel_{hero_id}"),
        2: ("Store", ""),
        3: ("Mission", f"ActivityAllyTaskWindow_{hero_id}"),
        5: ("Boss Fight", f"ActivityAllyBossWindow_{hero_id}"),
        6: ("Tower", f"ActivityAllyTowerMapWindow_{hero_id}")
    }
    for t in [1, 2, 3, 5, 6]:
        act_id = int(data['ActivityMainID']) * 100 + t
        text_act_id = text_base * 100 + t
        note = f"{data['HeroName']} - {config_type[t][0]}"
        if t in [5, 6]:
            end_t = end_time_som
            end_time_show = data['EndTime'] if t == 5 else "" 
        else:
            end_t = data['EndTime']
            end_time_show = ""
        link_p = data['StoreLinkParam'] if t == 2 else ""
        root_prefab = config_type[t][1]
        danh_sach.append(f"{act_id},{data['ActivityMainID']},{t},{note},{data['StartTime']},{end_t},AllyActivity_{text_act_id},{end_time_show},1,530,{link_p},,{root_prefab}\n")
    return "".join(danh_sach)

def tao_data_cho_file_sign(data):
    danh_sach = []
    act_id = int(data['ActivityMainID']) * 100 + 1 
    dict_sign = data['RewardData'].get('Sign', {})
    sign_days = len(dict_sign)
    if sign_days == 0: sign_days = 5
    for day in range(1, sign_days + 1):
        reward_id = dict_sign.get(day, "") 
        danh_sach.append(f"{act_id},{day},{data['HeroName']} - Check In,{reward_id}\n")
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

def tao_data_cho_file_item(data):
    danh_sach = []
    tokens = data['Tokens'].split('|')
    
    # Determine if we reuse old text keys (from previous event)
    old_tokens = data.get('OldTokens', '').split('|') if data.get('OldTokens', '') else []
    old_item_icons = data.get('OldItemIcons', {})
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

        old_token_id = old_tokens[i] if use_old_keys and i < len(old_tokens) else ""
        icon = old_item_icons.get(old_token_id) or (f"ui_item_{old_token_id}" if old_token_id else f"ui_item_{tid}")
        danh_sach.append(f"{tid},{name},{name_key},{desc_key},{desc},1,,,,1,,,,,,4,4,{quality},15,{icon},,,,,,3600\n")
    return "".join(danh_sach)

def tao_data_cho_file_boss_info(data):
    hero_id = data['HeroName'].replace(' ', '')
    act_id = f"{data['ActivityMainID']}05"
    end_time_som = tinh_thoi_gian_som(data['EndTime'])
    scene = "Battle_Digital_1|Battle_Digital_StarSky"
    
    enemy_group = data.get('AutoGroupID', '')
    if not enemy_group:
        enemy_group = "201001" 
        
    sk1 = data.get('BossSkillShow1', '') or data.get('BossWarningStr', '')
    if not sk1:
        sk1 = "431130101|431130201|431130301|431130601"
        
    sk2 = data.get('BossSkillShow2', '') or "212100101|212100301|212100401|212100501"
    
    return f"{act_id},{data['BossID']},1,{enemy_group},{data['HeroName']},ActivityBossName_{hero_id},ActivityBossInfo_{hero_id},{data['StartTime']},{end_time_som},{scene},11,22,{sk1},{sk2},ActivityBossSpeak1_{hero_id}|ActivityBossSpeak2_{hero_id}|ActivityBossSpeak3_{hero_id}|ActivityBossSpeak4_{hero_id},207\n"

def tao_data_cho_file_boss_rank(data):
    danh_sach = []
    act_id = f"{data['ActivityMainID']}05"
    dict_rank = data['RewardData'].get('BossRank', {})

    sorted_ranks = sorted(dict_rank.keys())
    for r in sorted_ranks:
        reward_id = dict_rank[r]
        if r == 1: note = "1st Place"
        elif r == 2: note = "2nd Place"
        elif r == 3: note = "3rd Place"
        else: note = f"Top {r}"
        danh_sach.append(f"{act_id},{data['HeroName']},{data['BossID']},{r},{note},{reward_id}\n")
    return "".join(danh_sach)

def tao_data_cho_file_boss_score(data):
    danh_sach = []
    act_id = f"{data['ActivityMainID']}05"
    dict_score = data['RewardData'].get('BossScore', {})
    
    sorted_scores = sorted(dict_score.keys())
    for i, score in enumerate(sorted_scores, 1): 
        reward_id = dict_score[score] 
        danh_sach.append(f"{act_id},{data['HeroName']},{data['BossID']},{i},{score},{reward_id}\n")
    return "".join(danh_sach)

def tao_data_cho_file_tower_chapter(data):
    danh_sach = []
    act_id = f"{data['ActivityMainID']}06"
    end_time_som = tinh_thoi_gian_som(data['EndTime'])
    t1, t2, t3 = tinh_thoi_gian_thap(data['StartTime']) 
    thong_so_thap = [("01", t1, 120, 5, "220010101"), ("02", t2, 180, 7, "220010102"), ("03", t3, 240, 10, "220010103")]
    
    for m, start, lv, star, tbuff in thong_so_thap:
        danh_sach.append(f"{act_id},{act_id}{m},TowerName_{data['AllyId']}_{m},{data['HeroName']} Tower {int(m)},{start},{end_time_som},{data['AllyId']},{lv},{star},{tbuff},7\n")
    return "".join(danh_sach)

def tao_data_cho_file_tower_level(data):
    danh_sach = []
    act_id = f"{data['ActivityMainID']}06"
    scene = "Battle_Hephaestus_1"
    
    rwd_1 = data['RewardData'].get('TowerRwd1', '') 
    rwd_2 = data['RewardData'].get('TowerRwd2', '') 
    rwd_3 = data['RewardData'].get('TowerRwd3', '') 
    
    dict_buffs = {
        (1, 4): "220110101,220110102,220110103",
        (1, 8): "220110201,220110202,220110203",
        (1, 12): "220110301,220110302,220110303",
        (2, 4): "220120101,220120102,220120103",
        (2, 8): "220120201,220120202,220120203",
        (2, 12): "220120301,220120302,220120303",
        (3, 4): "220130101,220130102,",     
        (3, 8): "220130201,,",              
        (3, 12): "220130301,220130302,220130303",
        (3, 16): "220130401,,"              
    }
    
    for m in [1, 2, 3]:
        tower_id = f"{act_id}0{m}"
        so_tang = 17 if m == 3 else 13
        
        for lvl in range(1, so_tang + 1):
            if lvl % 4 == 0:
                buff_str = dict_buffs.get((m, lvl), ",,")
                danh_sach.append(f"{tower_id},{data['HeroName']} Tower {m},{lvl},2,,,{buff_str},,,\n")
            else:
                prefix_quai = "6153"
                enemy_grp = f"{prefix_quai}{m}{lvl:02d}"
                
                if lvl == so_tang:
                    current_rwd = rwd_3 
                elif lvl in [3, 7, 11, 15]:
                    current_rwd = rwd_2 
                else:
                    current_rwd = rwd_1 
                    
                danh_sach.append(f"{tower_id},{data['HeroName']} Tower {m},{lvl},1,{enemy_grp},{current_rwd},,,,2,2,{scene}\n")
                
    return "".join(danh_sach)

def tao_data_cho_file_ads_banner(data):
    end_time_som = tinh_thoi_gian_som(data['EndTime'])
    return f"{data['BannerID']},{data['HeroName']},{data['StartTime']},{end_time_som},2,530,ui_banner_{data['AllyId']},{data['GachaJumpId']},,,0\n"

def tao_data_cho_file_ads_popup(data):
    ally = data['AllyId']
    end_time_som = tinh_thoi_gian_som(data['EndTime'])
    rows = []
    rows.append(f"{data['PopUpID']},{data['HeroName']},{data['StartTime']},{end_time_som},2,530,,,,,5,{data['GachaJumpId']},1,1,ui_popuppic_img_shuxing_bg,ui_popuppic_img_bg_{ally},ui_recharg_img_timetxtbg_{ally},{ally},Popup_{ally}_title,0e0e0e,ffffff,ffbb04,145c8f,Popup_{ally}_text,Popup_{ally}_text_2,,\n")
    return "".join(rows)

def tao_data_cho_file_jump(data):
    danh_sach = []
    # Jump to Gacha (dùng chung cho AdsBanner, AdsPopUp, ActivityNewHero)
    danh_sach.append(f"{data['GachaJumpId']},8,Skip to Gacha - {data['HeroName']},{data['GachaTypeID']},,,,,1,Corresponds to AllyGachaType table card pool ID,AllyGachaName11,,1\n")
    # Jump to IAP (dùng cho AllyGachaType)
    danh_sach.append(f"{data['GiftJumpId']},25,[Shop] - Special Gift Pack - {data['HeroName']},4,{data['PayStoreSubID']},,,,1,Func Corresponding to PayStoreSub table,Func_fufeishangcheng,COMMON_Ended,1\n")
    return "".join(danh_sach)

def tao_data_cho_file_ally_gacha_type(data):
    end_time_som = tinh_thoi_gian_som(data['EndTime'])
    gacha_text_key = data.get('OldGachaTextKey') or f"AllyGachaName{data['GachaTypeID']}"
    return f"{data['GachaTypeID']},Legendary Event {data['HeroName']},{data['GachaTypeID']},1,2,2,1,{data['AllyId']},,,,{data['StartTime']},{end_time_som},1120016,1,,,,,1502,,,,,,34,{gacha_text_key},,,5,30,AllyGachaTab32,ui_drawcard_btn_{data['AllyId']},ui_drawcard_img_bg04,ui_cardpool_{data['AllyId']},,805,Gacha_UpDes5,{data['GiftJumpId']}\n"

def tao_data_cho_file_ally_gacha_branch(data):
    gacha_leg = data['RewardData'].get('GachaLegendary', '')
    if not gacha_leg: gacha_leg = '1901380501' 
    gacha_epic = data['RewardData'].get('GachaEpic', '')
    if not gacha_epic: gacha_epic = '1901380502' 
    gacha_str = f"{gacha_leg}|504;{gacha_epic}|402"
    gacha_random = "1904002303|10000" 
    return f"{data['GachaTypeID']},Legendary Event {data['HeroName']},Legendary Event {data['HeroName']},1,0,0,5,,32,,1,-1,{gacha_str},{gacha_random}\n"

def tao_data_cho_file_task_activity(data):
    danh_sach = []
    base_id = int(data['TaskBaseID'])
    act_id = f"{data['ActivityMainID']}03"
    sign_days = len(data['RewardData'].get('Sign', {}))
    if sign_days == 0: sign_days = 5 
    suffixes = [
        "D - Complete 1 Daily Login", f"D - Challenge {data['HeroName']} once", "D - Recruit 1 Time in Featured Recruitment",
        "D - Win 1 Time in the Arena", "D - Challenge any Evil Falls enemy 1 time", "D - Recruit 5 times in Featured Recruitment",
        "D - Upgrade Equipment 1 time", "D - Level up a Character 5 times", f"S - Log in for {sign_days} Days in total",
        "S - Spend a total of 200 Event Currency 1", "S - Spend a total of 100 Event Currency 2", "S - Clear Elseworld 5 times",
        "S - Collect Squad Dispatch rewards 21 times", "S - Hire League Mercenaries to Clear Any Stage 2 Times",
        f"S - Clear the 3 areas in {data['HeroName']} Tower Mode", "S - Obtain 10 victories in the Elite Arena",
        f"S - Obtain {data['HeroName']}", "S - Recruit 20 times in Featured Recruitment", f"S - Rank up {data['HeroName']} to Rank 6",
        f"S - Rank up {data['HeroName']} to Rank 8", f"S - Rank up {data['HeroName']} to Rank 10"
    ]
    for i, suf in enumerate(suffixes, 1):
        task_id = base_id + i
        note = f"{data['HeroName']} Legendary Event - {suf}".format(HeroName=data['HeroName'])
        danh_sach.append(f"{task_id},{act_id},{note}\n")
    return "".join(danh_sach)

def tao_data_cho_file_task_info(data):
    danh_sach = []
    base_id = int(data['TaskBaseID'])
    tokens = data['Tokens'].split('|')
    tok1 = tokens[0] if len(tokens) > 0 else ""
    tok2 = tokens[1] if len(tokens) > 1 else ""
    tower_act = f"{data['ActivityMainID']}06"
    sign_days = len(data['RewardData'].get('Sign', {}))
    if sign_days == 0: sign_days = 5
    blueprint = [
        ('1', 90, 1, 2, 1, "", "", "D - Complete 1 Daily Login"),
        ('1', 101, 1, 2, 2, "", 3001, f"D - Challenge {data['HeroName']} once"),
        ('1', 93, 1, 2, 3, data['GachaTypeID'], data['GachaJumpId'], "D - Recruit 1 Time in Featured Recruitment"),
        ('1', 45, 1, 2, 4, "", 107, "D - Win 1 Time in the Arena"),
        ('1', 74, 1, 2, 5, "", 800, "D - Challenge any Evil Falls enemy 1 time"),
        ('1', 93, 5, 2, 6, data['GachaTypeID'], data['GachaJumpId'], "D - Recruit 5 times in Featured Recruitment"),
        ('1', 91, 1, 2, 7, "", 103, "D - Upgrade Equipment 1 time"),
        ('1', 14, 5, 2, 8, "", 103, "D - Level up a Character 5 times"),
        ('0', 6, sign_days, 2, 1, "", "", f"S - Log in for {sign_days} Days in total"),
        ('0', 103, 200, 1, 2, tok1, 3002, "S - Spend a total of 200 Event Currency 1"),
        ('0', 103, 100, 2, 3, tok2, 3002, "S - Spend a total of 100 Event Currency 2"),
        ('0', 32, 5, 2, 4, "", 105, "S - Clear Elseworld 5 times"),
        ('0', 105, 21, 2, 5, "", 991801, "S - Collect Squad Dispatch rewards 21 times"),
        ('0', 68, 2, 2, 6, "", 603, "S - Hire League Mercenaries to Clear Any Stage 2 Times"),
        ('0', 110, 3, 2, 7, tower_act, 3003, f"S - Clear the 3 areas in {data['HeroName']} Tower Mode"),
        ('0', 402, 10, 2, 8, "", 107, "S - Obtain 10 victories in the Elite Arena"),
        ('0', 53, 1, 1, 9, data['AllyId'], data['GachaJumpId'], f"S - Obtain {data['HeroName']}"),
        ('0', 93, 20, 2, 10, data['GachaTypeID'], data['GachaJumpId'], "S - Recruit 20 times in Featured Recruitment"),
        ('0', 20, 6, 1, 11, data['AllyId'], 103, f"S - Rank up {data['HeroName']} to Rank 6"),
        ('0', 20, 8, 1, 12, data['AllyId'], 103, f"S - Rank up {data['HeroName']} to Rank 8"),
        ('0', 20, 10, 1, 13, data['AllyId'], 103, f"S - Rank up {data['HeroName']} to Rank 10")
    ]
    task_rewards = data['RewardData'].get('Tasks', [])
    for i, bp in enumerate(blueprint, 1):
        rst, cond, tgt, acc, order, prm, dest, suf = bp
        task_id = base_id + i
        note = f"{data['HeroName']} Legendary Event - {suf}"
        tname = f"TaskName_{task_id}"
        reward_id = task_rewards[i-1] if i-1 < len(task_rewards) else ""
        danh_sach.append(f"{task_id},{note},20,7,{rst},{cond},{tgt},{prm},,,,,,,,{reward_id},{tname},,,{acc},1,0,{dest},{order}\n")
    return "".join(danh_sach)

def tao_data_cho_file_shop(data):
    free_shop_text_id = data.get('OldFreeShopTextID') or data['FreeShopID']
    paid_shop_text_id = data.get('OldPaidShopTextID') or data['PaidShopID']
    shop1 = f"{data['FreeShopID']},6,100,shopname{free_shop_text_id},ui_shop_img_blackbox_,,{data['ActivityMainID']}02,,,,,,,,,,,,0,{data['HeroName']}\n"
    shop2 = f"{data['PaidShopID']},8,101,shopname{paid_shop_text_id},ui_shop_img_blackbox_,,{data['ActivityMainID']}02,,,,,,,,,,,,0,{data['HeroName']}\n"
    return shop1 + shop2

def tao_data_cho_file_shop_item(data):
    danh_sach = []
    tokens = data['Tokens'].split('|')
    tok1 = tokens[0] if len(tokens) > 0 else ""
    tok2 = tokens[1] if len(tokens) > 1 else ""
    
    ally_frag_id = f"11{data['AllyId']}" 
    
    leg = data['PrevLegId']       
    epic = data['LatestEpicId']   
    epic1 = data['PrevEpic1']     
    epic2 = data['PrevEpic2']     
    
    # Xây dựng danh sách free_items động
    epic1_lim = '4' if not epic2.strip() else '2'
    raw_free_items = [
        ('10', '1120016', '1', '300', 'StoreDiscount_Label_Hot', 'Super Encrypted Token'),
        ('1', ally_frag_id, '10', '2200', 'StoreDiscount_Label_Hot', f"Legendary Fragment - {data['HeroName']}"),
        ('1', leg, '10', '2000', 'StoreDiscount_Label_Hot', 'Last Legend'),
        ('2', epic, '20', '2200', 'StoreDiscount_Label_Hot', 'Latest Epic'),
        (epic1_lim, epic1, '10', '1000', '', 'Previous Season Epic 1')
    ]
    
    # Chỉ thêm item Epic 2 nếu biến epic2 không bị để trống
    if epic2.strip():
        raw_free_items.append(('2', epic2, '10', '1000', '', 'Previous Season Epic 2'))
        
    raw_free_items.extend([
        ('5', '1120015', '1', '150', '', 'Encrypted Token'),
        ('3', '1120015', '5', '750', '', 'Encrypted Token'),
        ('2', '1121001', '10', '400', '', 'Inertron Fragment'),
        ('2', '1121002', '10', '800', '', 'Inertronite'),
        ('1', '1121003', '10', '1300', '', 'Inertron Alloy - Uni'),
        ('5', '1112132', '6', '250', '', '1hr Titanium Supply'),
        ('5', '1116009', '10', '160', '', 'Rare Fragment'),
        ('5', '111207', '1000', '150', '', 'Equipment Enhancement Part'),
        ('3', '1112102', '10', '400', '', '1hr Coin Supply')
    ])

    # Tự động đánh số thứ tự từ 1 trở đi cho danh sách
    free_items = [(str(i), *item) for i, item in enumerate(raw_free_items, 1)]
    
    raw_paid_items = [
        ('5', '1120016', '3', '60', 'StoreDiscount_Label_Hot', 'Super Encrypted Token'),
        ('5', '1120015', '8', '60', 'StoreDiscount_Label_Hot', 'Encrypted Token'),
        ('5', ally_frag_id, '5', '100', 'StoreDiscount_Label_Hot', f"Legendary Fragment - {data['HeroName']}"),
        ('3', ally_frag_id, '10', '200', 'StoreDiscount_Label_Hot', f"Legendary Fragment - {data['HeroName']}"),
        ('5', leg, '5', '100', 'StoreDiscount_Label_Hot', 'Last Legend'),
        ('3', leg, '10', '200', 'StoreDiscount_Label_Hot', 'Last Legend'),
        ('5', epic, '7', '50', '', 'Latest Epic'),
        ('3', epic, '18', '125', '', 'Latest Epic'),
        ('5', '1120031', '2', '50', '', 'Universal Fragment'),
        ('5', '1123901', '50', '60', '', 'Basic Energy Cell'),
        ('5', '1123902', '50', '75', '', 'Rare Energy Cell'),
        ('5', '1123903', '25', '100', '', 'Ultimate Energy Cell'),
        ('5', '1121001', '30', '100', '', 'Inertron Fragment'),
        ('5', '1121002', '15', '100', '', 'Inertronite'),
        ('3', '1121004', '15', '150', '', 'Inertron Alloy - Strength'),
        ('3', '1121005', '15', '150', '', 'Inertron Alloy - Agility'),
        ('3', '1121006', '15', '150', '', 'Inertron Alloy - Intellect'),
        ('5', '1116009', '20', '20', '', 'Rare Character Fragment'),
        ('3', '111207', '6500', '60', '', 'Equipment Enhancement Part'),
        ('3', '1112106', '1', '50', '', '24h Coin Supply'),
        ('3', '1112136', '1', '50', '', '24h Tit Supply'),
        ('3', '1112306', '1', '50', '', '24h EXP Supply'),
        ('3', '1123100', '3', '50', '', 'Random Coordinates'),
        ('3', '1116007', '1', '100', '', 'Epic Hero Chest'),
    ]
    
    paid_items = [(str(i), *item) for i, item in enumerate(raw_paid_items, 1)]
    
    for items, shop_id, cost_id in [(free_items, data['FreeShopID'], tok1), (paid_items, data['PaidShopID'], tok2)]:
        for pos, lim, item, num, price, label, name in items:
            item_id_str = f"{shop_id}{int(pos):02d}01"
            final_name = "" if name in [str(leg), str(epic), str(epic1), str(epic2)] else f"{name} x {num}"
            
            open_level = ""
            if item.startswith("1121"):
                open_level = "1230"
            elif item.startswith("1123"):
                open_level = "1830"
                
            danh_sach.append(f"{item_id_str},{final_name},Legendary Event - {data['HeroName']},,,{shop_id},{pos},100,,{open_level},,,,,{lim},{item},{num},{cost_id},{price},,,10000,,,,1,,{label}\n")
            
    return "".join(danh_sach)

def tao_data_cho_file_activity(data):
    act_id = data.get('TrailerActID', '')
    if not act_id: return ""
    try:
        dt_start = datetime.strptime(data['StartTime'], "%Y%m%d_%H%M%S")
        trailer_start = (dt_start - timedelta(days=3)).strftime("%Y%m%d_%H%M%S")
        trailer_end = data['StartTime']
    except:
        trailer_start = data['StartTime']
        trailer_end = data['StartTime']
    return f"{act_id},4,{data['HeroName']} Trailer,{trailer_start},{trailer_end},1,530,5,ActivityTrailerTitle01,ui_trailer_img_bg_{data['AllyId']},2,,,,\n"

def tao_data_cho_file_activity_trailer(data):
    act_id = data.get('TrailerActID', '')
    if not act_id: return ""
    ally = data['AllyId']
    return f"{act_id},{data['HeroName']} Trailer,TrailerTitle_{ally},TrailerSubTitle_DFRH,ui_trailer_img_subtitlebg_{ally},ui_comm_touming_img,ui_comm_touming_img,ui_trailer_img_rewardLeft_df,ui_trailer_img_rewardright_df,CharacterName_{ally},TrailerShareSubTitle,ui_trailer_img_subtitlebg_{ally},TrailerTitle_{ally},ui_trailer_img_unreveal_{ally},ui_trailer_img_sharebg_{ally},ui_trailer_img_sharebg_{ally},19040011,TrailerFuncInfo_{ally}_01,19040011,TrailerFuncInfo_{ally}_02,19040011,TrailerFuncInfo_{ally}_03,\n"

def tao_data_cho_file_item_expiration(data):
    danh_sach = []
    tokens = data['Tokens'].split('|')
    rel_act = f"{data['ActivityMainID']}06"
    for i, tid in enumerate(tokens):
        t_type = "Common" if i == 0 else "Rare"
        conv_id = "19160150" if i == 0 else "19160196"
        mail_id = "51" if i == 0 else "51"
        danh_sach.append(f"{tid},{data['HeroName']} Token {t_type},1,{data['EndTime']},{conv_id},{mail_id},Expired Item Reclamation Compensation,11,\n")
    return "".join(danh_sach)

def tao_data_cho_file_skill_monster(data):
    if not data.get('SkillMonsterRows'): return ""
    danh_sach = []
    for row in data['SkillMonsterRows']:
        danh_sach.append(",".join(row) + "\n")
    return "".join(danh_sach)

def tao_data_cho_file_enemy_event_boss(data):
    if not data.get('BossSkillStr'): return ""
    boss_id, ally_id, hero_name = data['BossID'], data['AllyId'], data['HeroName']
    skills, warnings = data['BossSkillStr'], data['BossWarningStr']
    stats = "6,100,,2,10000,6|3936;10|1013;2|39743;18|310;152|4000;26|5000;331|5000,,,1,,,,,,,,"
    return f"{boss_id},{ally_id},{hero_name} Boss,{hero_name},2,0,2,0,5,1,{skills},{warnings},{stats}\n"

def tao_data_cho_file_enemy_group(data):
    group_id, boss_id = data.get('AutoGroupID'), data.get('BossID')
    if not group_id or not boss_id or not data.get('BossSkillStr'): return ""
    return f"{group_id},Event Boss,Event Boss {data['HeroName']},116158,4,{boss_id},Boss {data['HeroName']},,,,,,,,,,,,,,,,,,,,,\n"


def tao_data_cho_file_source_common_ui(data):
    danh_sach = []
    hero = data['HeroName']
    hero_id = hero.replace(' ', '')
    ally = data['AllyId']
    act = data['ActivityMainID']
    text_act = data.get('TextActivityMainID', act)
    rule = data['RuleBaseID']
    f_shop = data.get('OldFreeShopTextID') or data['FreeShopID']
    p_shop = data.get('OldPaidShopTextID') or data['PaidShopID']
    gacha = data.get('OldGachaTextKey') or f"AllyGachaName{data['GachaTypeID']}"
    
    evt = f"{hero} Legendary Event"
    
    # 1. Popups
    danh_sach.append(f"Popup_{ally}_title,Pop Up Title,{evt},[NOT FINAL] Pop Up Title\n")
    danh_sach.append(f"Popup_{ally}_text,Pop Up Description,{evt},[NOT FINAL] Pop Up Text\n")
    danh_sach.append(f"Popup_{ally}_text_2,Pop Up Description 2,{evt},[NOT FINAL] Pop Up Text 2\n")
    
    # 2. Rules
    danh_sach.append(f"RuleDescription{rule}_1,Missions Rules,{evt},[NOT FINAL] Missions Rules\n")
    danh_sach.append(f"RuleDescriptionBoss_{text_act},Boss Fight Desc,{evt},[NOT FINAL] Boss Fight Desc\n")
    danh_sach.append(f"RuleDescriptionTower_{text_act},Tower Desc,{evt},[NOT FINAL] Tower Desc\n")
    danh_sach.append(f"RuleDescriptionShop_{text_act},Event Shop Desc,{evt},[NOT FINAL] Event Shop Desc\n")
    
    # 3. Shops
    danh_sach.append(f"shopname{f_shop},Common Currency Shop Title,{evt},[NOT FINAL] Survivors' Shop\n")
    danh_sach.append(f"shopname{p_shop},Premium Currency Shop Title,{evt},[NOT FINAL] Settlers' Shop\n")
    
    # 4. Gacha
    danh_sach.append(f"{gacha},Gacha Name,{evt},[NOT FINAL] Increased chance to obtain {hero}\n")
    
    # 5. Trailer
    if data.get('TrailerActID'):
        danh_sach.append(f"TrailerTitle_{ally},Trailer Title,{evt},[NOT FINAL] {hero} Trailer Title\n")
        danh_sach.append(f"TrailerFuncInfo_{ally}_01,Trailer Hint #1,{evt},[NOT FINAL] Hint 1\n")
        danh_sach.append(f"TrailerFuncInfo_{ally}_02,Trailer Hint #2,{evt},[NOT FINAL] Hint 2\n")
        danh_sach.append(f"TrailerFuncInfo_{ally}_03,Trailer Hint #3,{evt},[NOT FINAL] Hint 3\n")
        
    # 6. Activity
    danh_sach.append(f"AllyActivity_{text_act},Main Event Title,{evt},[NOT FINAL] Main Title\n")
    danh_sach.append(f"AllyActivity_{text_act}01,Sign In Title,{evt},[NOT FINAL] Sign In Title\n")
    danh_sach.append(f"AllyActivity_{text_act}02,Store Title,{evt},[NOT FINAL] Store Title\n")
    danh_sach.append(f"AllyActivity_{text_act}03,Missions Title,{evt},[NOT FINAL] Missions Title\n")
    danh_sach.append(f"AllyActivity_{text_act}05,Boss Fight Title,{evt},[NOT FINAL] Boss Fight Title\n")
    danh_sach.append(f"AllyActivity_{text_act}06,Tower Title,{evt},[NOT FINAL] Tower Title\n")
    
    # 7. Boss
    danh_sach.append(f"ActivityBossInfo_{hero_id},Boss Fight Info,{evt},[NOT FINAL] Boss Fight Info\n")
    danh_sach.append(f"ActivityBossName_{hero_id},Boss Fight Title,{evt},[NOT FINAL] Boss Fight Title\n")
    
    # 8. Character Files
    danh_sach.append(f"AllyActivity_Info{ally},Character Files Title,{evt},[NOT FINAL] Character Files Title\n")
    
    # 9. Tower
    danh_sach.append(f"TowerName_{ally}_01,Tower 1 Title,{evt},[NOT FINAL] Tower 1 Title\n")
    danh_sach.append(f"TowerName_{ally}_02,Tower 2 Title,{evt},[NOT FINAL] Tower 2 Title\n")
    danh_sach.append(f"TowerName_{ally}_03,Tower 3 Title,{evt},[NOT FINAL] Tower 3 Title\n")
    
    return "".join(danh_sach)

def tao_data_cho_file_source_drama(data):
    danh_sach = []
    hero = data['HeroName']
    hero_id = hero.replace(' ', '')
    evt = f"{hero} Legendary Event"

    # Boss Speaks
    danh_sach.append(f"ActivityBossSpeak1_{hero_id},Boss Speak,{evt},[NOT FINAL] Boss Speak 1,\n")
    danh_sach.append(f"ActivityBossSpeak2_{hero_id},Boss Speak,{evt},[NOT FINAL] Boss Speak 2,\n")
    danh_sach.append(f"ActivityBossSpeak3_{hero_id},Boss Speak,{evt},[NOT FINAL] Boss Speak 3,\n")
    danh_sach.append(f"ActivityBossSpeak4_{hero_id},Boss Speak,{evt},[NOT FINAL] Boss Speak 4,\n")

    # Revolve Dialogs (AllySpeak) - same key for same character, auto-reused on rerun
    danh_sach.append(f"ActivityAlly_{hero_id}1,Revolve Dialog,{evt},[NOT FINAL] Revolve Dialog 1,\n")
    danh_sach.append(f"ActivityAlly_{hero_id}2,Revolve Dialog,{evt},[NOT FINAL] Revolve Dialog 2,\n")
    danh_sach.append(f"ActivityAlly_{hero_id}3,Revolve Dialog,{evt},[NOT FINAL] Revolve Dialog 3,\n")
    danh_sach.append(f"ActivityAlly_{hero_id}4,Revolve Dialog,{evt},[NOT FINAL] Revolve Dialog 4,\n")

    return "".join(danh_sach)

def tao_data_cho_file_rule_desc(data):
    """Sinh 4 rows vào RuleDesc.csv cho Legendary Event.
    - Main Rule (RuleBaseID): Rules tổng hợp cho event
    - Boss Rule (RuleBaseID*10+1): Rules riêng Boss Fight  [skip nếu reuse_local]
    - BossRank Rule (RuleBaseID*10+2): Boss Ranking Preview [skip nếu reuse_local]
    - Tower Rule (RuleBaseID*10+3): Rules Tower Climb       [skip nếu reuse_local]
    """
    danh_sach = []
    base = int(data.get('RuleBaseID', '9000')) if str(data.get('RuleBaseID', '')).isdigit() else 9000
    act  = data['ActivityMainID']
    text_act = data.get('TextActivityMainID', act)
    hero = data['HeroName']
    reuse_local = data.get('ReuseLocal', False)

    # RuleDesc has 26 columns: ID, Comment, MainTitle, MainDesc, then 11 SubTitle/SubDesc pairs
    def pad_row(cols):
        while len(cols) < 26:
            cols.append('')
        return ','.join(cols)

    # 1. Main Rule — always created (new per event OR per rerun)
    main_cols = [
        str(base),
        f'{hero} Event - Main Interface Activities Rules',
        'RuleMainTitle_9206', '',
        f'AllyActivity_{text_act}01', 'RuleDescription9206_1',
        f'AllyActivity_{text_act}03', f'RuleDescription{base}_1',
        f'AllyActivity_{text_act}05', f'RuleDescriptionBoss_{text_act}',
        f'AllyActivity_{text_act}06', f'RuleDescriptionTower_{text_act}',
        f'AllyActivity_{text_act}02', f'RuleDescriptionShop_{text_act}',
    ]
    danh_sach.append(pad_row(main_cols) + '\n')

    # 2-4. Boss / BossRank / Tower rules — only for fresh events
    # Rerun events reuse these rule IDs from the original (via reuse_local)
    if not reuse_local:
        boss_cols = [
            str(base * 10 + 1),
            f'{hero} Event - Boss Rules',
            f'AllyActivity_{text_act}05', '',
            'RuleSubTitle92121_1', f'RuleDescriptionBoss_{text_act}',
            'RuleSubTitle92121_2', 'RuleDescription92121_2',
        ]
        danh_sach.append(pad_row(boss_cols) + '\n')

        rank_cols = [
            str(base * 10 + 2),
            f'{hero} Event - Boss Ranking Rules',
            'ActivityBossRank01', 'ActivityBossRank_Notice',
        ]
        danh_sach.append(pad_row(rank_cols) + '\n')

        tower_cols = [
            str(base * 10 + 3),
            f'{hero} Event - Tower Climbing Rules',
            f'AllyActivity_{text_act}06', f'RuleDescriptionTower_{text_act}',
        ]
        danh_sach.append(pad_row(tower_cols) + '\n')

    return ''.join(danh_sach)

def tao_data_cho_file_activity_ally_speak(data):
    """Sinh 4 rows mới vào ActivityAllySpeak.csv.
    Key ID tự động tăng từ max hiện tại.
    Dialog key = ActivityAlly_{hero_id}{n} — tự nhiên reuse cho cùng character (rerun).
    """
    danh_sach = []
    hero    = data['HeroName']
    hero_id = hero.replace(' ', '')
    act     = data['ActivityMainID']
    max_key = int(data.get('SpeakMaxKey', 1000))
    desc    = f'{hero} Rotating landing page dialogue'

    for i in range(1, 5):
        key    = max_key + i
        dialog = f'ActivityAlly_{hero_id}{i}'
        danh_sach.append(f'{key},{act},{dialog},{desc}\n')

    return ''.join(danh_sach)

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
        danh_sach.append(f"ItemDesc{key_token},Item Desc,{evt},[NOT FINAL] Used in event,\n")

    return "".join(danh_sach)

def tao_data_cho_file_source_common_desc(data):
    danh_sach = []
    base_id = int(data['TaskBaseID'])
    hero = data['HeroName']
    sign_days = len(data['RewardData'].get('Sign', {}))
    if sign_days == 0: sign_days = 5
    
    tasks = [
        "Complete 1 Daily Login", 
        f"Challenge {hero} once", 
        "Recruit 1 Time in Featured Recruitment",
        "Win 1 Time in the Arena", 
        "Challenge any Evil Falls enemy 1 time", 
        "Recruit 5 times in Featured Recruitment",
        "Upgrade Equipment 1 time", 
        "Level up a Character 5 times", 
        f"Log in for {sign_days} Days in total",
        "[NOT FINAL] Spend a total of 200 Event Currency 1", 
        "[NOT FINAL] Spend a total of 100 Event Currency 2", 
        "Clear Elseworld 5 times",
        "Collect Squad Dispatch rewards 21 times", 
        "Hire League Mercenaries to Clear Any Stage 2 Times",
        f"Clear the 3 areas in {hero} Tower Mode", 
        "Obtain 10 victories in the Elite Arena",
        f"Obtain {hero}", 
        "Recruit 20 times in Featured Recruitment", 
        f"Rank up {hero} to Rank 6",
        f"Rank up {hero} to Rank 8", 
        f"Rank up {hero} to Rank 10"
    ]
    
    for i, t_str in enumerate(tasks, 1):
        task_id = base_id + i
        if i <= 8:
            mission_type = "Daily Mission Text"
        else:
            mission_type = "Seasonal Mission Text"
        text_en = t_str
            
        t_name = f"TaskName_{task_id}"
        danh_sach.append(f"{t_name},Legendary Event - {hero} - {mission_type},{hero} Event,{text_en},\n")
        
    return "".join(danh_sach)

# ==========================================
# PHẦN 4: HÀM GHI FILE THÔNG MINH
# ==========================================
# PHẦN 4: HÀM GHI FILE THÔNG MINH (CHỐNG LỖI XUỐNG DÒNG)
# ==========================================
def ghi_file_thong_minh(filepath, chuoi_data, is_insert_mode=False, marker_str=""):
    filepath = os.path.normpath(filepath)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if os.path.exists(filepath):
        os.chmod(filepath, stat.S_IWRITE)
    
    chuoi_data = chuoi_data.replace('\r\n', '\n').replace('\n', '\r\n')
    
    def fix_newline(path):
        if not os.path.exists(path): return
        with open(path, 'rb+') as f:
            f.seek(0, os.SEEK_END)
            if f.tell() > 0:
                f.seek(-1, os.SEEK_END)
                last_char = f.read(1)
                if last_char not in [b'\n', b'\r']: 
                    f.write(b'\r\n')

    if not is_insert_mode:
        fix_newline(filepath)
        with open(filepath, 'a', encoding='utf-8-sig', newline='') as f:
            f.write(chuoi_data)
    else:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
                lines = f.readlines()
            
            if lines and not lines[-1].endswith('\n') and not lines[-1].endswith('\r'):
                lines[-1] += '\r\n'
                
            insert_idx = len(lines)
            for i in range(len(lines)-1, -1, -1):
                if marker_str == "ID212":
                    if lines[i].split(',')[0].startswith("212"):
                        insert_idx = i + 1
                        break
                else:
                    if marker_str in lines[i]:
                        insert_idx = i + 1
                        break
            lines.insert(insert_idx, chuoi_data)
            
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                f.writelines(lines)
        else:
            with open(filepath, 'a', encoding='utf-8-sig', newline='') as f:
                f.write(chuoi_data)

# ==========================================
# PHẦN 5: THỰC THI (ROUTER)
# ==========================================
def chon_file_reward():
    filepath = filedialog.askopenfilename(title="Chọn file Reward CSV", filetypes=[("CSV files", "*.csv")])
    if filepath:
        entry_reward_file.delete(0, tk.END)
        entry_reward_file.insert(0, filepath)

def chon_thu_muc_perforce():
    folderpath = filedialog.askdirectory(title="Chọn thư mục Perforce chứa các file CSV")
    if folderpath:
        entry_target_dir.delete(0, tk.END)
        entry_target_dir.insert(0, folderpath)

def chay_tool_xu_ly():
    try:
        thu_muc_goc = entry_target_dir.get()
        if not os.path.exists(thu_muc_goc):
            messagebox.showwarning("Lưu ý", "Thư mục đích không tồn tại! Hãy kiểm tra lại đường dẫn.")
            return

        ally_id_str = entry_ally.get()
        reuse_event = bool(entry_reuse_event_var.get())
        reuse_text = bool(entry_reuse_text_var.get())
        reuse_boss = bool(entry_reuse_boss_var.get())
        reuse_local = bool(entry_reuse_local_var.get())
        skill_monster_rows = []
        boss_skill_str = ""
        boss_warning_str = ""
        auto_boss_id = ""
        auto_group_id = ""

        # Auto-detect max Key hiện tại trong ActivityAllySpeak để tăng đúng
        speak_max_key = 1000
        speak_file = os.path.join(thu_muc_goc, "ActivityAllySpeak.csv")
        if os.path.exists(speak_file):
            with open(speak_file, 'r', encoding='utf-8-sig') as f:
                for row in csv.reader(f):
                    if len(row) > 0 and row[0].strip().isdigit():
                        speak_max_key = max(speak_max_key, int(row[0].strip()))

        if not reuse_event:
            skill_file = os.path.join(thu_muc_goc, "Skill.csv")
        else:
            skill_file = None

        if skill_file and os.path.exists(skill_file):
            with open(skill_file, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) > 0 and row[0].startswith(ally_id_str):
                        new_row = row[:3] + [""] + row[3:]
                        new_row[0] = "4" + new_row[0][1:]
                        if len(new_row) > 10:
                            new_row[10] = ""
                        skill_monster_rows.append(new_row)

            if skill_monster_rows:
                max_skills_dict = {}
                for row in skill_monster_rows:
                    sid = row[0]
                    prefix = sid[:7]
                    if prefix not in max_skills_dict or sid > max_skills_dict[prefix]:
                        max_skills_dict[prefix] = sid

                max_skills_list = [max_skills_dict[k] for k in sorted(max_skills_dict.keys())]
                boss_warning_str = "|".join(max_skills_list)
                boss_skill_str = boss_warning_str + "|212000102"

                boss_file = os.path.join(thu_muc_goc, "Enemies", "EnemyEventBoss.csv")
                max_boss_id = 2120000
                if os.path.exists(boss_file):
                    with open(boss_file, "r", encoding="utf-8-sig") as f:
                        for row in csv.reader(f):
                            if row and len(row) > 0 and row[0].startswith("212") and row[0].isdigit():
                                max_boss_id = max(max_boss_id, int(row[0]))
                auto_boss_id = str(max_boss_id + 100)

                group_file = os.path.join(thu_muc_goc, "EnemyGroup.csv")
                max_group_id = 202000
                if os.path.exists(group_file):
                    with open(group_file, "r", encoding="utf-8-sig") as f:
                        for row in csv.reader(f):
                            if row and len(row) > 0 and row[0].startswith("202") and row[0].isdigit():
                                max_group_id = max(max_group_id, int(row[0]))
                auto_group_id = str(max_group_id + 1)
                
        boss_id_input = entry_boss_id.get().strip()
        final_boss_id = boss_id_input if boss_id_input else auto_boss_id

        # A rerun always shares the original boss. Ignore a manually entered
        # Boss ID in this mode so a typo cannot create a mismatched boss setup.
        if reuse_event or reuse_boss:
            old_boss_id, old_boss_skill, old_boss_warning, old_group_id = tim_boss_cu(thu_muc_goc, entry_hero_name.get(), entry_ally.get())
            if old_boss_id:
                final_boss_id = old_boss_id
                entry_boss_id.delete(0, tk.END)
                entry_boss_id.insert(0, old_boss_id)
                boss_skill_str = old_boss_skill or boss_skill_str
                boss_warning_str = old_boss_warning or boss_warning_str
                auto_group_id = old_group_id or auto_group_id
                boss_skill_show_1, boss_skill_show_2 = tim_boss_skill_show_cu(
                    thu_muc_goc, old_boss_id, entry_hero_name.get()
                )
            else:
                boss_skill_show_1, boss_skill_show_2 = "", ""
                if reuse_event:
                    messagebox.showwarning(
                        "Rerun Boss",
                        "Không tìm thấy Boss gốc. Tool sẽ không thể dùng lại Boss ID và BossSkillShow cũ.",
                    )
        else:
            boss_skill_show_1, boss_skill_show_2 = "", ""

        if not boss_warning_str and final_boss_id:
            boss_file_path = os.path.join(thu_muc_goc, "Enemies", "EnemyEventBoss.csv")
            if os.path.exists(boss_file_path):
                with open(boss_file_path, "r", encoding="utf-8-sig") as f:
                    for row in csv.reader(f):
                        if len(row) > 11 and row[0] == final_boss_id:
                            boss_warning_str = row[11]
                            break

        reward_filepath = entry_reward_file.get()
        reward_data = doc_file_reward(reward_filepath)

        # Rerun fallback: if Reward.csv does not supply Banner rewards, reuse
        # the nearest earlier Legendary Event banner for this hero.
        if reuse_event and (not reward_data["GachaLegendary"] or not reward_data["GachaEpic"]):
            rerun_banner_rewards = tim_banner_reward_rerun(
                thu_muc_goc,
                entry_hero_name.get(),
                entry_ally.get(),
                entry_start.get(),
            )
            if rerun_banner_rewards:
                legendary_id, epic_id = rerun_banner_rewards
                if not reward_data["GachaLegendary"]:
                    reward_data["GachaLegendary"] = legendary_id
                if not reward_data["GachaEpic"]:
                    reward_data["GachaEpic"] = epic_id
                print(f"Rerun banner fallback: Legendary={reward_data['GachaLegendary']}, Epic={reward_data['GachaEpic']}")
            else:
                messagebox.showwarning(
                    "Rerun Banner",
                    "Không tìm thấy Legendary Event cũ phù hợp để lấy Banner rewards. "
                    "AllyGachaBranch sẽ dùng giá trị fallback mặc định.",
                )
        
        input_data = {
            "ActivityMainID": entry_main_id.get(), "HeroName": entry_hero_name.get(), "StartTime": entry_start.get(), "EndTime": entry_end.get(), "GachaJumpId": entry_gacha.get(), "GiftJumpId": entry_gift.get(), "StoreLinkParam": entry_store.get(), "AllyId": entry_ally.get(), 
            "BossID": final_boss_id,
            "RuleBaseID": entry_rule.get(), "Tokens": entry_tokens.get(), "BannerID": entry_banner.get(), "PopUpID": entry_popup.get(), "GachaTypeID": entry_gacha_type.get(), "PayStoreSubID": entry_paystore_sub.get(), "TaskBaseID": entry_task_id.get(), "FreeShopID": entry_free_shop.get(), "PaidShopID": entry_paid_shop.get(), "PrevLegId": entry_prev_leg.get(), "LatestEpicId": entry_latest_epic.get(), "PrevEpic1": entry_epic_1.get(), "PrevEpic2": entry_epic_2.get(), "TrailerActID": entry_trailer_id.get(), "RewardData": reward_data,
            "SkillMonsterRows": skill_monster_rows,
            "BossSkillStr": boss_skill_str,
            "BossWarningStr": boss_warning_str,
            "BossSkillShow1": boss_skill_show_1,
            "BossSkillShow2": boss_skill_show_2,
            "AutoGroupID": auto_group_id,
            "SpeakMaxKey": speak_max_key,
            "ReuseEvent": reuse_event,
            "ReuseText": reuse_text,
            "ReuseBoss": reuse_boss,
            "ReuseLocal": reuse_local
        }

        if reuse_text:
            old_text_main_id = tim_old_activity_main_id(thu_muc_goc, entry_hero_name.get(), entry_ally.get(), entry_main_id.get())
            if old_text_main_id:
                input_data["TextActivityMainID"] = old_text_main_id
                # Also extract old tokens for item text key reuse
                old_func_file = os.path.join(thu_muc_goc, "ActivityAllyFuncMain.csv")
                if os.path.exists(old_func_file):
                    with open(old_func_file, 'r', encoding='utf-8-sig') as f:
                        for row in csv.reader(f):
                            if len(row) > 0 and row[0].strip() == old_text_main_id:
                                if len(row) > 11:
                                    input_data['OldTokens'] = row[11].strip()
                                break

        if reuse_local:
            old_local = tim_local_cu(thu_muc_goc, entry_hero_name.get(), entry_ally.get())
            if old_local:
                input_data.update(old_local)
        
        if reuse_text:
            old_tokens_str = ""
            old_func = tim_old_activity_main_id(thu_muc_goc, entry_hero_name.get(), entry_ally.get(), entry_main_id.get())
            if old_func:
                old_func_file = os.path.join(thu_muc_goc, "ActivityAllyFuncMain.csv")
                if os.path.exists(old_func_file):
                    with open(old_func_file, 'r', encoding='utf-8-sig') as f:
                        for row in csv.reader(f):
                            if len(row) > 0 and row[0].strip() == old_func:
                                if len(row) > 11:
                                    old_tokens_str = row[11].strip()
                                break
            if old_tokens_str:
                input_data['OldTokens'] = old_tokens_str

        if input_data.get('OldTokens'):
            input_data['OldItemIcons'] = tim_item_icons_cu(
                thu_muc_goc, input_data['OldTokens'].split('|')
            )

        if reuse_text and input_data.get('TextActivityMainID'):
            old_activity_id = input_data['TextActivityMainID']
            old_free_shop_text_id, old_paid_shop_text_id = tim_shop_text_ids_cu(
                thu_muc_goc, old_activity_id
            )
            if old_free_shop_text_id:
                input_data['OldFreeShopTextID'] = old_free_shop_text_id
            if old_paid_shop_text_id:
                input_data['OldPaidShopTextID'] = old_paid_shop_text_id

            old_gacha_text_key = tim_gacha_text_key_cu(thu_muc_goc, old_activity_id)
            if old_gacha_text_key:
                input_data['OldGachaTextKey'] = old_gacha_text_key

        if auto_boss_id and not boss_id_input:
            entry_boss_id.delete(0, tk.END)
            entry_boss_id.insert(0, auto_boss_id)

        cac_file_can_sua = [
            "ActivityAllyFuncMain.csv", "ActivityAllyFuncSub.csv", "ActivityAllySign.csv", "ActivityAllyLocal.csv", "ActivityAllyBossInfo.csv", "ActivityAllyBossRank.csv", "ActivityAllyBossScore.csv", "ActivityAllyTowerChapter.csv", "ActivityAllyTowerLevel.csv", "AdsBanner.csv", "AdsPopUp.csv", "Jump.csv", "AllyGachaType.csv", "AllyGachaBranch.csv", "TaskActivity.csv", "TaskInfo.csv", "ShopItem.csv", "Shop.csv", "Activity.csv", "ActivityTrailer.csv", "Item.csv", "ItemExpiration.csv",
            "SkillMonster.csv", "Enemies/EnemyEventBoss.csv", "EnemyGroup.csv",
            "RuleDesc.csv", "ActivityAllySpeak.csv",
            "Language/SourceCommonUI.csv", "Language/SourceCommonDesc.csv", "Language/SourceDrama.csv", "Language/SourceItemDesc.csv"
        ]

        router = {
            "ActivityAllyFuncMain.csv": tao_data_cho_file_main, "ActivityAllyFuncSub.csv": tao_data_cho_file_sub, "ActivityAllySign.csv": tao_data_cho_file_sign, "ActivityAllyLocal.csv": tao_data_cho_file_local, "ActivityAllyBossInfo.csv": tao_data_cho_file_boss_info, "ActivityAllyBossRank.csv": tao_data_cho_file_boss_rank, "ActivityAllyBossScore.csv": tao_data_cho_file_boss_score, "ActivityAllyTowerChapter.csv": tao_data_cho_file_tower_chapter, "ActivityAllyTowerLevel.csv": tao_data_cho_file_tower_level, "AdsBanner.csv": tao_data_cho_file_ads_banner, "AdsPopUp.csv": tao_data_cho_file_ads_popup, "Jump.csv": tao_data_cho_file_jump, "AllyGachaType.csv": tao_data_cho_file_ally_gacha_type, "AllyGachaBranch.csv": tao_data_cho_file_ally_gacha_branch, "TaskActivity.csv": tao_data_cho_file_task_activity, "TaskInfo.csv": tao_data_cho_file_task_info, "ShopItem.csv": tao_data_cho_file_shop_item, "Shop.csv": tao_data_cho_file_shop, "ActivityTrailer.csv": tao_data_cho_file_activity_trailer, "Activity.csv": tao_data_cho_file_activity, "Item.csv": tao_data_cho_file_item, "ItemExpiration.csv": tao_data_cho_file_item_expiration,
            "SkillMonster.csv": tao_data_cho_file_skill_monster, "Enemies/EnemyEventBoss.csv": tao_data_cho_file_enemy_event_boss, "EnemyGroup.csv": tao_data_cho_file_enemy_group,
            "RuleDesc.csv": tao_data_cho_file_rule_desc, "ActivityAllySpeak.csv": tao_data_cho_file_activity_ally_speak,
            "Language/SourceCommonUI.csv": tao_data_cho_file_source_common_ui, "Language/SourceCommonDesc.csv": tao_data_cho_file_source_common_desc,
            "Language/SourceDrama.csv": tao_data_cho_file_source_drama, "Language/SourceItemDesc.csv": tao_data_cho_file_source_item_desc
        }

        reuse_files = set()
        if reuse_text:
            reuse_files.update({
                "Language/SourceCommonUI.csv",
                "Language/SourceDrama.csv",
                "Language/SourceItemDesc.csv"
            })
        if reuse_boss or reuse_event:
            reuse_files.update({"Enemies/EnemyEventBoss.csv", "EnemyGroup.csv"})
        if reuse_event:
            reuse_files.add("SkillMonster.csv")
        if reuse_local:
            reuse_files.add("RuleDesc.csv")

        for fname, func in router.items():
            if fname in reuse_files:
                continue
            chuoi_data = func(input_data)
            if not chuoi_data: continue
            
            is_insert = ("EnemyGroup.csv" in fname or "EnemyEventBoss.csv" in fname)
            marker = "Event Boss" if "EnemyGroup.csv" in fname else ("ID212" if "EnemyEventBoss.csv" in fname else "")
            
            ghi_file_thong_minh(os.path.join(thu_muc_goc, fname), chuoi_data, is_insert, marker)

        config_to_save = {k: v for k, v in input_data.items() if k not in ["RewardData", "SkillMonsterRows", "BossSkillStr", "BossWarningStr", "AutoGroupID"]}
        config_to_save["TargetDir"] = entry_target_dir.get()
        config_to_save["RewardFile"] = entry_reward_file.get()
        save_config(config_to_save)

        messagebox.showinfo("BINGO!", f"DATA GENERATED ({thu_muc_goc})!!")
    except Exception as e:
        messagebox.showerror("Lỗi", f"Chi tiết: {e}")

# ==========================================
# PHẦN 6: GIAO DIỆN (UI)
# ==========================================
window = tk.Tk()
window.title("DC LiveOps Tool - Auto Event Configurator")

tk.Label(window, text="⚙️ EVENT GENERATOR ENGINE", font=("Arial", 14, "bold"), fg="#111").pack(pady=10)

def tao_o_nhap(parent, ten_nhan, gia_tri_mau=""):
    frame = tk.Frame(parent)
    frame.pack(pady=4, fill='x', padx=10)
    tk.Label(frame, text=ten_nhan, width=28, anchor='w', font=("Arial", 9, "bold")).pack(side='left')
    o_nhap = tk.Entry(frame, font=("Arial", 10))
    o_nhap.insert(0, gia_tri_mau)
    o_nhap.pack(side='right', expand=True, fill='x')
    return o_nhap

frame_reward = tk.Frame(window)
frame_reward.pack(pady=4, fill='x', padx=30)
tk.Label(frame_reward, text="File Reward CSV:", width=28, anchor='w', font=("Arial", 9, "bold")).pack(side='left')
entry_reward_file = tk.Entry(frame_reward, font=("Arial", 10))
entry_reward_file.insert(0, "Reward_BlackAdam.csv")
entry_reward_file.pack(side='left', expand=True, fill='x', padx=(0, 5))
btn_browse = tk.Button(frame_reward, text="...", command=chon_file_reward, width=3)
btn_browse.pack(side='right')

frame_dir = tk.Frame(window)
frame_dir.pack(pady=4, fill='x', padx=30)
tk.Label(frame_dir, text="Folder Excel:", width=28, anchor='w', font=("Arial", 9, "bold")).pack(side='left')
entry_target_dir = tk.Entry(frame_dir, font=("Arial", 10))
entry_target_dir.insert(0, "Test_Data") 
entry_target_dir.pack(side='left', expand=True, fill='x', padx=(0, 5))
btn_browse_dir = tk.Button(frame_dir, text="...", command=chon_thu_muc_perforce, width=3)
btn_browse_dir.pack(side='right')

frame_reuse = tk.Frame(window)
frame_reuse.pack(pady=4, fill='x', padx=30)
entry_reuse_event_var = tk.IntVar(value=0)
entry_reuse_text_var = tk.IntVar(value=0)
entry_reuse_boss_var = tk.IntVar(value=0)
entry_reuse_local_var = tk.IntVar(value=0)

chk_reuse_event = tk.Checkbutton(frame_reuse, text="Rerun: reuse original assets / Boss (no SkillMonster)", variable=entry_reuse_event_var, anchor='w')
chk_reuse_event.pack(side='left', padx=(0, 10))
chk_reuse_text = tk.Checkbutton(frame_reuse, text="Reuse text IDs / language files", variable=entry_reuse_text_var, anchor='w')
chk_reuse_text.pack(side='left', padx=(0, 10))
chk_reuse_boss = tk.Checkbutton(frame_reuse, text="Reuse boss / enemy group", variable=entry_reuse_boss_var, anchor='w')
chk_reuse_boss.pack(side='left', padx=(0, 10))
chk_reuse_local = tk.Checkbutton(frame_reuse, text="Reuse ActivityAllyLocal", variable=entry_reuse_local_var, anchor='w')
chk_reuse_local.pack(side='left')

frame_cols = tk.Frame(window)
frame_cols.pack(fill='both', expand=True, padx=20, pady=10)

left_col = tk.Frame(frame_cols)
left_col.pack(side='left', fill='both', expand=True, padx=5)

right_col = tk.Frame(frame_cols)
right_col.pack(side='right', fill='both', expand=True, padx=5)

# --- Cột Trái (Event Core Info & Trailer) ---
entry_main_id = tao_o_nhap(left_col, "Activity Main ID:", "129")
entry_hero_name = tao_o_nhap(left_col, "Tên Hero:", "BlackAdam")
entry_start = tao_o_nhap(left_col, "Start Time:", "20260715_000000")
entry_end = tao_o_nhap(left_col, "End Time:", "20260729_000000")
entry_ally = tao_o_nhap(left_col, "Hero Ally ID:", "13110")
entry_rule = tao_o_nhap(left_col, "Rule Base ID:", "9211")      
entry_boss_id = tao_o_nhap(left_col, "Boss ID (Trống=Auto):", "") 
tk.Label(left_col, text="(Tự động lấy ID tiếp theo nếu để trống)", font=("Arial", 8, "italic"), fg="gray").pack(pady=0)
entry_tokens = tao_o_nhap(left_col, "Tokens ID (cách |):", "1110043|1110044")
entry_task_id = tao_o_nhap(left_col, "Task Base ID \n(lấy từ số 0):", "5110000") 

tk.Label(left_col, text="--- TRAILER (ALLIES PREVIEW) ---", font=("Arial", 9, "italic"), fg="blue").pack(pady=2)
entry_trailer_id = tao_o_nhap(left_col, "Trailer Activity ID:", "4023")

# --- Cột Phải (Marketing, Gacha & Shop Info) ---
entry_gacha = tao_o_nhap(right_col, "Gacha Jump ID:", "1369")
entry_gift = tao_o_nhap(right_col, "Gift Jump ID:", "1370")
entry_gacha_type = tao_o_nhap(right_col, "Gacha Type ID:", "114")        
entry_paystore_sub = tao_o_nhap(right_col, "PayStore Sub ID:", "9529")    
entry_store = tao_o_nhap(right_col, "Store Link (rare):", "3056")
entry_banner = tao_o_nhap(right_col, "Ads Banner ID:", "160")
entry_popup = tao_o_nhap(right_col, "Ads PopUp ID:", "164")

tk.Label(right_col, text="--- SHOP ID ---", font=("Arial", 9, "italic"), fg="blue").pack(pady=2)
entry_free_shop = tao_o_nhap(right_col, "Free Shop ID:", "3053")
entry_paid_shop = tao_o_nhap(right_col, "Paid Shop ID:", "3054")

tk.Label(right_col, text="--- TƯỚNG PHỤ TRONG SHOP ---", font=("Arial", 9, "italic"), fg="blue").pack(pady=2)
entry_prev_leg = tao_o_nhap(right_col, "Last Legend:", "1113134")
entry_latest_epic = tao_o_nhap(right_col, "Latest Epic:", "1113232") 
entry_epic_1 = tao_o_nhap(right_col, "Prev Season Epic 1:", "1113214")
entry_epic_2 = tao_o_nhap(right_col, "Prev Season Epic 2:", "1113217")

btn_run = tk.Button(window, text="🔥 GENERATE DATA", bg="#d9534f", fg="white", font=("Arial", 12, "bold"), command=chay_tool_xu_ly)
btn_run.pack(pady=10, fill='x', padx=50)

saved_config = load_config()
if saved_config:
    def restore_val(entry_widget, key):
        if key in saved_config:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, saved_config[key])
            
    restore_val(entry_main_id, "ActivityMainID")
    restore_val(entry_hero_name, "HeroName")
    restore_val(entry_start, "StartTime")
    restore_val(entry_end, "EndTime")
    restore_val(entry_ally, "AllyId")
    restore_val(entry_rule, "RuleBaseID")
    restore_val(entry_boss_id, "BossID")
    restore_val(entry_tokens, "Tokens")
    restore_val(entry_task_id, "TaskBaseID")
    restore_val(entry_trailer_id, "TrailerActID")
    restore_val(entry_free_shop, "FreeShopID")
    restore_val(entry_paid_shop, "PaidShopID")
    
    restore_val(entry_gacha, "GachaJumpId")
    restore_val(entry_gift, "GiftJumpId")
    restore_val(entry_gacha_type, "GachaTypeID")
    restore_val(entry_paystore_sub, "PayStoreSubID")
    restore_val(entry_store, "StoreLinkParam")
    restore_val(entry_banner, "BannerID")
    restore_val(entry_popup, "PopUpID")
    restore_val(entry_prev_leg, "PrevLegId")
    restore_val(entry_latest_epic, "LatestEpicId")
    restore_val(entry_epic_1, "PrevEpic1")
    restore_val(entry_epic_2, "PrevEpic2")
    
    restore_val(entry_target_dir, "TargetDir")
    restore_val(entry_reward_file, "RewardFile")
    
    entry_reuse_event_var.set(saved_config.get("ReuseEvent", 0))
    entry_reuse_text_var.set(saved_config.get("ReuseText", 0))
    entry_reuse_boss_var.set(saved_config.get("ReuseBoss", 0))
    entry_reuse_local_var.set(saved_config.get("ReuseLocal", 0))

window.geometry("800x820") 
window.mainloop()
