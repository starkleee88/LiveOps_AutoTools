#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STANDALONE EVENT AUTO TOOL (Activity Type 6 - Collection Event)
Hỗ trợ tạo tự động toàn bộ cấu hình sự kiện Standalone / Fatal Exception:
- Activity & ActivityCollectionGroup (15 & 13 cột)
- ActivityCollectionReward (Sao chép 60 mốc chuẩn từ Event 8019, thay Activity ID)
- TaskActivity & TaskInfo (12 Nhiệm vụ: 5 Daily + 7 Weekly, kế thừa TaskName_8019xxx)
- AllyGachaBranch (14 cột: Gacha drop tỉ lệ 509|404 và GachaRandom 2660|2660)
- AllyGachaType (39 cột đầy đủ theo schema CL 360065 & Season 13)
- AdsBanner (11 cột) & AdsPopUp (27 cột với đầy đủ màu sắc và text keys)
- Item (26 cột) & ItemExpiration (9 cột)
- Jump (13 cột) & JumpSource (9 cột)
- Shop (20 cột) & ShopItem (28 cột chuẩn vị trí Col 13 BeforeItemID, danh sách Tướng tùy biến)
- SourceCommonUI: chỉ tạo AllyGachaTab{ActivityID} và AllyGachaName{ActivityID}

Tuân thủ nghiêm ngặt:
- os.chmod(filepath, stat.S_IWRITE) chống Read-Only của Perforce
- fix_newline (kiểm tra binary b'\\n'/b'\\r' chống dính dòng cuối)
- append mode ('a') không ghi đè dữ liệu cũ
- Mã hóa UTF-8 BOM ('utf-8-sig') chuẩn hóa \\r\\n
- Tự động nhận diện Standalone Event: The Campaign (dùng lại ID cũ) vs Special Edition (sinh ID mới không dấu cách)
"""

import sys
import os
import csv
import stat
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from tkinter.scrolledtext import ScrolledText
except ImportError:
    tk = None

# Kiểm tra xem app đang chạy bằng file .exe hay file .py
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(SCRIPT_DIR, "standalone_config.json")


# ==============================================================================
# 1. HÀM XỬ LÝ FILE AN TOÀN (PERFORCE SAFE APPEND & ENCODING)
# ==============================================================================

def unlock_file(filepath: str):
    """Bỏ thuộc tính Read-Only cho file trong Perforce workspace."""
    if os.path.exists(filepath):
        try:
            os.chmod(filepath, stat.S_IWRITE)
        except Exception:
            pass


def fix_newline(filepath: str):
    """Đảm bảo file kết thúc bằng ký tự xuống dòng (\\r\\n) để tránh dính dòng khi append."""
    if not os.path.exists(filepath):
        return
    unlock_file(filepath)
    try:
        with open(filepath, 'rb+') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size > 0:
                f.seek(-1, os.SEEK_END)
                last_char = f.read(1)
                if last_char not in [b'\n', b'\r']:
                    f.write(b'\r\n')
    except Exception:
        pass


def read_csv(filepath: str) -> List[List[str]]:
    """Đọc file CSV với mã hóa UTF-8-sig."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
            return list(csv.reader(f))
    except Exception:
        return []


def format_csv_row(row: List[Any], quote_all: bool = False) -> str:
    """Format một row CSV chuẩn theo RFC 4180 và loại bỏ ký tự ngắt dòng thừa."""
    import io
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL if quote_all else csv.QUOTE_MINIMAL)
    writer.writerow([str(cell) for cell in row])
    return output.getvalue().rstrip('\r\n')


def append_csv(filepath: str, rows: List[List[Any]], key_indices: List[int] = [0], quote_all: bool = False) -> int:
    """
    Append an toàn các rows vào file CSV:
    - Bỏ read-only
    - fix_newline (chống dính dòng cuối)
    - Deduplication theo khóa (key_indices) để không ghi lặp nếu đã tồn tại
    - Không bao giờ ghi đè file cũ
    - Trả về số dòng thực tế được thêm mới
    """
    if not rows:
        return 0

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    unlock_file(filepath)
    fix_newline(filepath)

    existing_rows = read_csv(filepath)
    existing_keys = set()
    if existing_rows:
        for r in existing_rows:
            if r:
                try:
                    k = tuple(str(r[idx]).strip() for idx in key_indices if idx < len(r))
                    existing_keys.add(k)
                except Exception:
                    pass

    new_rows_to_append = []
    for r in rows:
        if r:
            k = tuple(str(r[idx]).strip() for idx in key_indices if idx < len(r))
            if k not in existing_keys:
                new_rows_to_append.append(r)
                existing_keys.add(k)

    if not new_rows_to_append:
        return 0

    mode = 'a' if os.path.exists(filepath) and os.path.getsize(filepath) > 0 else 'w'
    with open(filepath, mode, encoding='utf-8-sig', newline='') as f:
        for r in new_rows_to_append:
            f.write(format_csv_row(r, quote_all=quote_all) + '\r\n')

    return len(new_rows_to_append)


# ==============================================================================
# 2. CẤU HÌNH (LOAD / SAVE CONFIG)
# ==============================================================================

def get_default_shop_characters() -> List[Dict[str, Any]]:
    """10 Hero fragments mặc định từ Season 13 / CL 360065."""
    return [
        {"name": "Madam Xanadu", "item_id": "1113241", "num": "10", "limit": "3", "price": "900", "featured": True},
        {"name": "Vandal Savage", "item_id": "1113240", "num": "10", "limit": "3", "price": "360", "featured": True},
        {"name": "Harley Quinn CJ", "item_id": "1113235", "num": "10", "limit": "1", "price": "850", "featured": False},
        {"name": "Batman Beyond", "item_id": "1113230", "num": "10", "limit": "1", "price": "850", "featured": False},
        {"name": "The Riddler", "item_id": "1113221", "num": "10", "limit": "1", "price": "850", "featured": False},
        {"name": "Absolute Batman", "item_id": "1113238", "num": "10", "limit": "1", "price": "850", "featured": False},
        {"name": "Absolute Wonder Woman", "item_id": "1113237", "num": "10", "limit": "1", "price": "850", "featured": False},
        {"name": "Absolute Superman", "item_id": "1113239", "num": "10", "limit": "1", "price": "850", "featured": False},
        {"name": "Booster Gold", "item_id": "1113228", "num": "10", "limit": "1", "price": "850", "featured": False},
        {"name": "Batwoman", "item_id": "1118121", "num": "10", "limit": "1", "price": "850", "featured": False}
    ]


def get_default_config() -> Dict[str, Any]:
    return {
        "target_dir": "H:/gear/Perforce/x.son.lengoc_Config_Dev/excel",
        "reward_file": "",
        "season": "13",
        "activity_id": "8029",
        "event_name": "Superheroes",
        "item_trade_name_text": "",
        "item_trade_desc_text": "",
        "item_encrypted_name_text": "",
        "item_encrypted_desc_text": "",
        "popup_title_text": "",
        "popup_subtitle_text": "",
        "popup_desc_text": "",
        "start_time": "20261211_000000",
        "end_time": "20261218_000000",
        "token_trade_id": "1111020",
        "token_encrypted_id": "1120054",
        "gacha_type_id": "8029",
        "gacha_leg_reward_id": "12000114",
        "gacha_epic_reward_id": "12000115",
        "gacha_elite_reward_id": "12000116",
        "gacha_rare_reward_id": "12000117",
        "task_rewards": [
            "21000111", "21000112", "21000113", "21000114", "21000115",
            "21000117", "21000118", "21000119", "21000120", "21000121",
            "21000122", "21000123"
        ],
        "shop_id": "9898",
        "substore_id": "9898",
        "rule_desc_key": "8029",
        "create_ruledesc": True,
        "rule_desc_text": "",
        "banner_id": "516",
        "popup_id": "518",
        "jump_activity_id": "18029",
        "jump_gacha_id": "80291",
        "jump_iap_id": "19898",
        "jumpsource_id": "598",
        "shop_characters": get_default_shop_characters(),
        "gen_activity": True,
        "gen_collection_reward": True,
        "gen_tasks": True,
        "gen_gacha_banner": True,
        "gen_items_jumps": True,
        "gen_shop": True,
        "gen_language": True
    }


def load_config() -> Dict[str, Any]:
    default_cfg = get_default_config()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_cfg.update(data)
                return default_cfg
        except Exception:
            pass
    return default_cfg


def save_config(cfg: Dict[str, Any]):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False


# ==============================================================================
# 3. HELPER: TỰ ĐỘNG TÍNH ID KẾ TIẾP (SCAN PERFORCE FILES)
# ==============================================================================

def scan_next_ids_from_target(target_dir: str, activity_id: str = "8029", substore_id: str = "9898") -> Dict[str, str]:
    """
    Quét tự động thư mục excel Perforce để tìm ID kế tiếp:
    - JumpSource ID: Max ID trong khoảng 500..899 + 1
    - AdsBanner ID: Max ID trong khoảng 500..599 + 1
    - AdsPopUp ID: Max ID trong khoảng 500..599 + 1
    - Token Trade ID: Max trong khoảng 1111000..1111099 + 1
    - Token Encrypted ID: Max trong khoảng 1120040..1120099 + 1
    - Jump Activity ID: 1{activity_id}
    - Jump Gacha ID: {activity_id}1
    - Jump IAP ID: 1{substore_id}
    """
    result = {
        "jumpsource_id": "598",
        "banner_id": "516",
        "popup_id": "518",
        "token_trade_id": "1111020",
        "token_encrypted_id": "1120054",
        "jump_activity_id": f"1{activity_id}",
        "jump_gacha_id": f"{activity_id}1",
        "jump_iap_id": f"1{substore_id}"
    }

    if not target_dir or not os.path.exists(target_dir):
        return result

    # 1. JumpSource.csv
    js_p = os.path.join(target_dir, "JumpSource.csv")
    if os.path.exists(js_p):
        js_max = 0
        for r in read_csv(js_p):
            if r and r[0].strip().isdigit():
                v = int(r[0].strip())
                if 500 <= v <= 899 and v > js_max:
                    js_max = v
        if js_max > 0:
            result["jumpsource_id"] = str(js_max + 1)

    # 2. AdsBanner.csv
    b_p = os.path.join(target_dir, "AdsBanner.csv")
    if os.path.exists(b_p):
        b_max = 0
        for r in read_csv(b_p):
            if r and r[0].strip().isdigit():
                v = int(r[0].strip())
                if 500 <= v <= 599 and v > b_max:
                    b_max = v
        if b_max > 0:
            result["banner_id"] = str(b_max + 1)

    # 3. AdsPopUp.csv
    pu_p = os.path.join(target_dir, "AdsPopUp.csv")
    if os.path.exists(pu_p):
        pu_max = 0
        for r in read_csv(pu_p):
            if r and r[0].strip().isdigit():
                v = int(r[0].strip())
                if 500 <= v <= 599 and v > pu_max:
                    pu_max = v
        if pu_max > 0:
            result["popup_id"] = str(pu_max + 1)

    # 4. Item.csv (Tokens)
    it_p = os.path.join(target_dir, "Item.csv")
    if os.path.exists(it_p):
        trade_max = 0
        enc_max = 0
        for r in read_csv(it_p):
            if r and r[0].strip().isdigit():
                v = int(r[0].strip())
                if 1111000 <= v <= 1111099 and v > trade_max:
                    trade_max = v
                if 1120040 <= v <= 1120099 and v > enc_max:
                    enc_max = v
        if trade_max > 0:
            result["token_trade_id"] = str(trade_max + 1)
        if enc_max > 0:
            result["token_encrypted_id"] = str(enc_max + 1)

    return result


# ==============================================================================
# 4. ĐỌC VÀ TRÍCH XUẤT REWARD FILE (TỰ ĐỘNG BÓC TÁCH ID)
# ==============================================================================

def parse_standalone_reward_csv(filepath: str, event_name: str = "") -> Dict[str, Any]:
    """
    Đọc file Reward CSV (ví dụ: Reward_Standalone_s13.csv).
    Tự động trích xuất:
    - 12 Task Reward IDs (5 Daily + 7 Weekly)
    - 4 Gacha Motherbox Reward IDs (Legendary, Epic, Elite, Rare)
    """
    result = {
        "task_rewards": [""] * 12,
        "gacha_rewards": {
            "legendary": "",
            "epic": "",
            "elite": "",
            "rare": ""
        },
        "all_reward_ids": set()
    }

    if not os.path.exists(filepath):
        return result

    try:
        with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return result

            idx_reward = 1
            idx_note = 2
            for i, col in enumerate(header):
                c = col.strip().lower()
                if c in ['rewardid', 'reward id', 'reward_id']:
                    idx_reward = i
                    break

            for i, col in enumerate(header):
                c = col.strip().lower()
                if c in ['note', 'o']:
                    idx_note = i
                    break

            evt_clean = event_name.strip().lower() if event_name else ""

            for row in reader:
                if len(row) <= max(idx_reward, idx_note):
                    continue
                rid = str(row[idx_reward]).strip()
                note = str(row[idx_note]).strip().lower()

                if not rid or rid.lower() in ['reward id', 'int', 'rewardid']:
                    continue

                result["all_reward_ids"].add(rid)

                # 1. Quét Daily Tasks (5 tasks)
                if 'daily' in note or ' - d - ' in note:
                    if 'win 3 arena' in note and 'elite' not in note and not result["task_rewards"][0]:
                        result["task_rewards"][0] = rid
                    elif 'elite arena' in note and '35' not in note and '40' not in note and not result["task_rewards"][1]:
                        result["task_rewards"][1] = rid
                    elif 'evil falls' in note and not result["task_rewards"][2]:
                        result["task_rewards"][2] = rid
                    elif 'elseworld' in note and not result["task_rewards"][3]:
                        result["task_rewards"][3] = rid
                    elif 'equipment' in note and not result["task_rewards"][4]:
                        result["task_rewards"][4] = rid

                # 2. Quét Weekly / Seasonal Tasks (7 tasks)
                elif 'weekly' in note or ' - s - ' in note or 'seasonal' in note:
                    if 'token' in note and ('spend' in note or 'encrypted' in note) and not result["task_rewards"][5]:
                        result["task_rewards"][5] = rid
                    elif ('1 stage' in note or 'stage 1' in note) and not result["task_rewards"][6]:
                        result["task_rewards"][6] = rid
                    elif ('2 stage' in note or 'stage 2' in note) and not result["task_rewards"][7]:
                        result["task_rewards"][7] = rid
                    elif ('3 stage' in note or 'stage 3' in note) and not result["task_rewards"][8]:
                        result["task_rewards"][8] = rid
                    elif ('crisis watch' in note or '30 star' in note) and not result["task_rewards"][9]:
                        result["task_rewards"][9] = rid
                    elif 'login' in note and '7 day' in note and not result["task_rewards"][10]:
                        result["task_rewards"][10] = rid
                    elif ('win 35' in note or 'win 40' in note or '35 matches' in note or '40 matches' in note or 'elite arena' in note) and not result["task_rewards"][11]:
                        result["task_rewards"][11] = rid

                # 3. Quét Mother Box Pools (Ưu tiên pool chứa event_name nếu có)
                if 'mother box' in note or 'motherbox' in note:
                    matches_event = (not evt_clean) or (evt_clean in note)
                    if matches_event:
                        if 'legendary' in note and not result["gacha_rewards"]["legendary"]:
                            result["gacha_rewards"]["legendary"] = rid
                        elif 'epic' in note and not result["gacha_rewards"]["epic"]:
                            result["gacha_rewards"]["epic"] = rid
                        elif 'elite' in note and not result["gacha_rewards"]["elite"]:
                            result["gacha_rewards"]["elite"] = rid
                        elif 'rare' in note and not result["gacha_rewards"]["rare"]:
                            result["gacha_rewards"]["rare"] = rid

    except Exception:
        pass

    return result


# ==============================================================================
# 5. CÁC HÀM TẠO DỮ LIỆU TỪNG PHẦN (GENERATORS)
# ==============================================================================

def is_campaign_event(event_name: str) -> bool:
    """Kiểm tra xem sự kiện có phải là Campaign (The Campaign) hay Special Edition."""
    s = event_name.strip().lower()
    return not s or s == "campaign" or s == "the campaign" or s == "thecampaign"


def is_variant_event(cfg: Dict[str, Any]) -> bool:
    """Use explicit mode when set; infer it for older saved configurations."""
    if "event_variant" in cfg:
        return bool(cfg["event_variant"])
    event_name = str(cfg.get("event_name", "")).strip()
    return bool(event_name) and not is_campaign_event(event_name)


def get_clean_event_id(event_name: str) -> str:
    """Lấy tên định danh không dấu cách cho Text IDs (ví dụ: 'Villains Edition' -> 'VillainsEdition')."""
    return re.sub(r'[\s_]+', '', event_name.strip())


def get_main_motherbox_text_keys(event_id: str) -> Tuple[str, str]:
    """Trả về text keys của Motherbox chính, bao gồm alias đã có trong localization."""
    event_id = str(event_id).strip()
    return f"AllyGachaName{event_id}", f"AllyGachaTab{event_id}"


def get_seasonal_motherbox_templates(
    target_dir: str,
    activity_id: str,
    seasons: List[int]
) -> Dict[int, Tuple[List[str], List[str]]]:
    """Lấy cấu hình Motherbox season từ event hiện tại hoặc các event trước đó."""
    type_path = os.path.join(target_dir, "AllyGachaType.csv")
    branch_path = os.path.join(target_dir, "AllyGachaBranch.csv")
    branch_rows = {
        row[0].strip(): row
        for row in read_csv(branch_path)
        if row
    }
    templates: Dict[int, Tuple[List[str], List[str]]] = {}
    current_id = str(activity_id).strip()
    current_id_value = int(current_id) if current_id.isdigit() else -1

    for row in read_csv(type_path):
        if len(row) < 39:
            continue
        season_match = re.search(r"-\s*Season\s+(\d+)\s+Motherbox\b", row[1], re.IGNORECASE)
        if not season_match:
            continue
        pool_season = int(season_match.group(1))
        parent_id = row[0].strip()[:-1]
        if (
            pool_season not in seasons
            or not parent_id.isdigit()
            or int(parent_id) > current_id_value
        ):
            continue

        branch_row = branch_rows.get(row[0].strip())
        if branch_row:
            templates[pool_season] = (row, branch_row)

    missing = sorted(set(seasons) - set(templates))
    if missing:
        missing_seasons = ", ".join(str(value) for value in missing)
        raise ValueError(
            "Không tìm thấy cấu hình Motherbox cho season "
            f"{missing_seasons} trong AllyGachaType.csv và AllyGachaBranch.csv."
        )
    return templates


def generate_activity_files(target_dir: str, cfg: Dict[str, Any], log_cb) -> int:
    """
    Tạo cấu hình Activity.csv (15 cột), ActivityCollectionGroup.csv (13 cột), RuleDesc.csv (26 cột).
    """
    total_added = 0
    act_id = str(cfg["activity_id"]).strip()
    season = str(cfg["season"]).strip()
    event_name = str(cfg.get("event_name", "")).strip()
    start_time = str(cfg["start_time"]).strip()
    end_time = str(cfg["end_time"]).strip()
    shop_id = str(cfg["shop_id"]).strip()

    is_camp = not is_variant_event(cfg)
    if not is_camp and not event_name:
        raise ValueError("Event biến thể cần có Event Theme Name.")
    clean_name = get_clean_event_id(event_name)

    title_key = "StandAloneEventTitle" if is_camp else f"{clean_name}EventTitle"

    # RuleDesc Key: Nếu không phải Special Edition (The Campaign) thì ruledesc luôn để là 8019 thay vì lấy thẳng ID của Event
    if is_camp:
        rule_desc_key = "8019"
    else:
        rule_desc_key = str(cfg.get("rule_desc_key", "")).strip() or act_id

    # 1. Activity.csv (15 cột)
    act_path = os.path.join(target_dir, "Activity.csv")
    act_rows = [[
        act_id, '6', f'Standalone 1 s{season} Event',
        start_time, end_time, '1', '530', '8',
        title_key, 'ui_ActivityCollection_img_bigbg',
        '1', rule_desc_key, '', '1', '2300'
    ]]
    n = append_csv(act_path, act_rows, key_indices=[0])
    total_added += n
    log_cb(f"Activity.csv: Đã ghi thêm {n} dòng (ID {act_id}, RuleDescKey: {rule_desc_key}, 15 cột)")

    # 2. ActivityCollectionGroup.csv (13 cột)
    group_path = os.path.join(target_dir, "ActivityCollectionGroup.csv")
    group_rows = [[
        act_id, f'Standalone Event 1 s{season}', act_id,
        '1', '4', '', shop_id, shop_id, '1', '214', '', 'Collection_SE_214', '140'
    ]]
    n = append_csv(group_path, group_rows, key_indices=[0])
    total_added += n
    log_cb(f"ActivityCollectionGroup.csv: Đã ghi thêm {n} dòng (ID {act_id}, 13 cột)")

    # 3. RuleDesc.csv (26 cột)
    # Nếu là 8019 (Campaign) thì trong RuleDesc.csv đã có sẵn dòng 8019, không cần ghi thêm trừ khi người dùng bật ép tạo
    create_ruledesc = cfg.get("create_ruledesc", (rule_desc_key != "8019"))
    if create_ruledesc and rule_desc_key != "8019":
        rule_path = os.path.join(target_dir, "RuleDesc.csv")
        main_desc_key = f"RuleDescription{rule_desc_key}_1"
        comment_text = f"{event_name} Event " if event_name else "Standalone Event "

        rule_row = [rule_desc_key, comment_text, "RuleMainTitle_8001", main_desc_key] + [""] * 22
        n = append_csv(rule_path, [rule_row], key_indices=[0])
        total_added += n
        log_cb(f"RuleDesc.csv: Đã tạo bộ RuleDesc mới (ID {rule_desc_key}, 26 cột)")
    else:
        log_cb(f"RuleDesc.csv: Sự kiện Campaign sử dụng lại bộ RuleDesc {rule_desc_key} chuẩn có sẵn trong game.")

    return total_added


def generate_collection_rewards(target_dir: str, cfg: Dict[str, Any], log_cb) -> int:
    """
    Sao chép trọn vẹn 60 mốc phần thưởng từ Event 8019 trong ActivityCollectionReward.csv.
    Chỉ thay thế:
    - Cột 0: 8019 -> {activity_id}
    - Cột 1: 8019xxx -> {activity_id}xxx
    Toàn bộ các cột điểm, tier, reward ID giữ nguyên 100%.
    """
    col_path = os.path.join(target_dir, "ActivityCollectionReward.csv")
    if not os.path.exists(col_path):
        log_cb(f"CẢNH BÁO: Không tìm thấy file {col_path}!", "WARN")
        return 0

    act_id = str(cfg["activity_id"]).strip()
    all_rows = read_csv(col_path)

    template_rows = [r for r in all_rows if r and r[0].strip() == '8019']
    if not template_rows:
        for cand in ['8023', '8029']:
            template_rows = [r for r in all_rows if r and r[0].strip() == cand]
            if len(template_rows) == 60:
                break

    if not template_rows:
        log_cb("LỖI: Không tìm thấy 60 dòng mẫu của event 8019 trong ActivityCollectionReward.csv!", "ERROR")
        return 0

    new_rows = []
    base_id_str = template_rows[0][0].strip()
    for r in template_rows:
        new_row = list(r)
        new_row[0] = act_id
        new_row[1] = str(r[1]).replace(base_id_str, act_id)
        new_rows.append(new_row)

    n = append_csv(col_path, new_rows, key_indices=[0, 1])
    log_cb(f"ActivityCollectionReward.csv: Đã nhân bản {n}/60 mốc phần thưởng cho Activity ID {act_id}")
    return n


def generate_tasks(target_dir: str, cfg: Dict[str, Any], task_reward_ids: List[str], log_cb) -> int:
    """
    Tạo 12 nhiệm vụ trong TaskActivity.csv (3 cột) và TaskInfo.csv (24 cột).
    Kế thừa đúng bộ Text Keys chuẩn từ 8019.
    """
    total_added = 0
    act_id = str(cfg["activity_id"]).strip()

    rewards = list(task_reward_ids) + [""] * (12 - len(task_reward_ids))

    task_definitions = [
        # (offset_id, name, type, cond1, cond2, cond3, task_name_key, jump_or_param, order)
        ("001", "Standalone 1 Event - D - Win 3 arena matches", "1", "45", "3", "", "TaskName_8019001", "107", "1"),
        ("002", "Standalone 1 Event - D - Win 3 elite arena matches", "1", "402", "3", "", "TaskName_8019002", "107", "2"),
        ("003", "Standalone 1 Event - D - Win/Participate Evil Falls 1 time", "1", "74", "1", "", "TaskName_8019003", "800", "3"),
        ("004", "Standalone 1 Event - D - Win/Participate Elseworld 1 time", "1", "32", "1", "", "TaskName_8019004", "105", "4"),
        ("005", "Standalone 1 Event - D - Level up equipment 5 times", "1", "91", "5", "", "TaskName_8019005", "103", "5"),
        ("006", "Standalone 1 Event - S - Spend 1 Fatal Encrypted Token", "0", "93", "1", act_id, "TaskName_8019007", f"{act_id}1", "3"),
        ("007", "Standalone 1 Event - S - Participate in 1 stage of League Challenge", "0", "701", "1", "", "TaskName_9030016", "600", "4"),
        ("008", "Standalone 1 Event - S - Participate in 2 stage of League Challenge", "0", "701", "2", "", "TaskName_9030014", "600", "5"),
        ("009", "Standalone 1 Event - S - Participate in 3 stage of League Challenge", "0", "701", "3", "", "TaskName_9030015", "600", "6"),
        ("010", "Standalone 1 Event - S - Gain 30 Stars from Crisis Watch", "0", "207", "1", "30", "TaskName_8019011", "99137", "7"),
        ("011", "Standalone 1 Event - S - Login for 7 Days in total", "0", "6", "7", "", "TaskName_8019012", "", "1"),
        ("012", "Standalone 1 Event - S - Win 35 Elite Arena Matches", "0", "402", "35", "", "TaskName_8019013", "107", "2"),
    ]

    # 1. TaskActivity.csv (3 cột)
    task_act_path = os.path.join(target_dir, "TaskActivity.csv")
    task_act_rows = []
    for t_def in task_definitions:
        t_id = f"{act_id}{t_def[0]}"
        task_act_rows.append([t_id, act_id, t_def[1]])

    n1 = append_csv(task_act_path, task_act_rows, key_indices=[0])
    total_added += n1
    log_cb(f"TaskActivity.csv: Đã ghi thêm {n1}/12 nhiệm vụ (prefix {act_id})")

    # 2. TaskInfo.csv (24 cột)
    task_info_path = os.path.join(target_dir, "TaskInfo.csv")
    task_info_rows = []
    for i, t_def in enumerate(task_definitions):
        t_id = f"{act_id}{t_def[0]}"
        r_id = rewards[i] if rewards[i] else f"21000{111 + i}"
        t_name = t_def[1]
        is_daily = t_def[2]
        c1 = t_def[3]
        c2 = t_def[4]
        c3 = t_def[5]
        t_key = t_def[6]
        jump_id = t_def[7]
        order = t_def[8]

        row = [
            t_id, t_name, "20", "7", is_daily, c1, c2, c3,
            "", "", "", "", "", "", "",
            r_id, t_key, "", "",
            "2", "1" if i not in [6, 7, 8, 9] else ("4" if i in [6, 7, 8] else "12"),
            "0" if i not in [6, 7, 8, 9] else ("9" if i in [6, 7, 8] else "30"),
            jump_id, order
        ]
        task_info_rows.append(row)

    n2 = append_csv(task_info_path, task_info_rows, key_indices=[0])
    total_added += n2
    log_cb(f"TaskInfo.csv: Đã ghi thêm {n2}/12 nhiệm vụ (đủ 24 cột)")

    return total_added


def generate_gacha_and_banners(target_dir: str, cfg: Dict[str, Any], gacha_rewards: Dict[str, str], log_cb) -> int:
    """
    Tạo card pools trong AllyGachaBranch.csv (14 cột), AllyGachaType.csv (39 cột), AdsBanner.csv (11 cột), AdsPopUp.csv (27 cột).
    Refine chính xác theo CL 360065 & Season 13 / 8029.
    """
    total_added = 0
    act_id = str(cfg["activity_id"]).strip()
    event_name = str(cfg.get("event_name", "")).strip()
    season = int(cfg.get("season", 13))
    start_time = str(cfg["start_time"]).strip()
    end_time = str(cfg["end_time"]).strip()
    token_encrypted_id = str(cfg["token_encrypted_id"]).strip()
    jump_iap_id = str(cfg.get("jump_iap_id", "19898")).strip()
    jump_activity_id = str(cfg.get("jump_activity_id", f"1{act_id}")).strip()
    jump_gacha_id = str(cfg.get("jump_gacha_id", f"{act_id}1")).strip()
    banner_id = str(cfg.get("banner_id", "516")).strip()
    popup_id = str(cfg.get("popup_id", "518")).strip()

    is_camp = not is_variant_event(cfg)
    if not is_camp and not event_name:
        raise ValueError("Event biến thể cần có Event Theme Name.")
    clean_name = get_clean_event_id(event_name)

    # Tính các mốc thời gian hồi quy:
    try:
        dt_start = datetime.strptime(start_time, "%Y%m%d_%H%M%S")
        t_2d = (dt_start + timedelta(days=2)).strftime("%Y%m%d_%H%M%S")
        t_4d = (dt_start + timedelta(days=4)).strftime("%Y%m%d_%H%M%S")
    except Exception:
        t_2d = start_time
        t_4d = start_time

    # Reward IDs cho main pool
    r_leg = gacha_rewards.get("legendary") or "12000114"
    r_epic = gacha_rewards.get("epic") or "12000115"
    r_elite = gacha_rewards.get("elite") or "12000116"
    r_rare = gacha_rewards.get("rare") or "12000117"

    main_motherbox_name = f"Standalone 1 Season {season} Motherbox" if is_camp else f"Standalone 1 {event_name} Motherbox"
    seasonal_seasons = [season - 1, season - 2, season - 3]
    seasonal_templates = get_seasonal_motherbox_templates(
        target_dir, act_id, seasonal_seasons
    )
    seasonal_windows = [(t_4d, end_time), (t_2d, t_4d), (start_time, t_2d)]
    seasonal_type_rows = []
    seasonal_branch_rows = []
    for offset, (pool_season, time_window) in enumerate(
        zip(seasonal_seasons, seasonal_windows), start=1
    ):
        template_type, template_branch = seasonal_templates[pool_season]
        pool_id = f"{act_id}{offset}"

        type_row = list(template_type)
        type_row[0] = pool_id
        type_row[2] = pool_id
        type_row[11], type_row[12] = time_window
        type_row[38] = jump_iap_id
        seasonal_type_rows.append(type_row)

        branch_row = list(template_branch)
        branch_row[0] = pool_id
        seasonal_branch_rows.append(branch_row)

    # 1. AllyGachaBranch.csv (14 cột chuẩn)
    # Col 12: Gacha (Leg & Epic) | Col 13: GachaRandom (Elite & Rare)
    branch_path = os.path.join(target_dir, "AllyGachaBranch.csv")
    branch_rows = [
        [act_id, main_motherbox_name, main_motherbox_name, "1", "", "", "", "", "72", "", "1", "-1", f"{r_leg}|509;{r_epic}|404", f"{r_elite}|2660;{r_rare}|2660"],
    ] + seasonal_branch_rows
    n = append_csv(branch_path, branch_rows, key_indices=[0])
    total_added += n
    log_cb(f"AllyGachaBranch.csv: Đã ghi thêm {n}/4 card pools (chuẩn 14 cột, tách drops Col 12 & 13)")

    # 2. AllyGachaType.csv (39 cột chuẩn theo CL 360065)
    gacha_name_key, gacha_tab_key = get_main_motherbox_text_keys(act_id)
    tab_btn_bg = "ui_drawcard_btn_season11" if is_camp else "ui_drawcard_btn_villain"
    back_ally_img = "ui_cardpool_new13_team11" if is_camp else "ui_cardpool_new16"

    type_path = os.path.join(target_dir, "AllyGachaType.csv")
    type_rows = [
        # Main pool (39 cols)
        [act_id, main_motherbox_name, act_id, "1", "2", "2", "", "", "", "", "", start_time, end_time, token_encrypted_id, "1", "", "", "", "", jump_iap_id, "", "", "", "", "", "1000", gacha_name_key, "", "", "5", "30", gacha_tab_key, tab_btn_bg, "ui_drawcard_img_bg04", back_ally_img, "", "1", "Gacha_UpDes5", jump_iap_id],
    ] + seasonal_type_rows
    n = append_csv(type_path, type_rows, key_indices=[0])
    total_added += n
    log_cb(f"AllyGachaType.csv: Đã ghi thêm {n}/4 card pools (chuẩn 39 cột)")

    # 3. AdsBanner.csv (11 cột chuẩn)
    banner_path = os.path.join(target_dir, "AdsBanner.csv")
    banner_rows = [[banner_id, f"Standalone 1 Event season {season}", start_time, end_time, "2", "530", "ui_banner_Fatal_01", jump_gacha_id, "", "", "0"]]
    n = append_csv(banner_path, banner_rows, key_indices=[0])
    total_added += n
    log_cb(f"AdsBanner.csv: Đã ghi thêm {n} dòng (Banner {banner_id}, 11 cột)")

    # 4. AdsPopUp.csv (27 cột chuẩn)
    popup_text1 = "Popup_Standalone1_Title" if is_camp else f"Popup_{clean_name}_Title"
    popup_text2 = "Popup_Standalone1_Subtitle" if is_camp else f"Popup_{clean_name}_Subtitle"
    popup_text3 = "Popup_Standalone1_Desc" if is_camp else f"Popup_{clean_name}_Desc"

    popup_path = os.path.join(target_dir, "AdsPopUp.csv")
    popup_rows = [[
        popup_id, f"Standalone Event 1 S{season}", start_time, end_time, "2", "530",
        "", "", "", "", "8", jump_activity_id, "1", "1400",
        "ui_popuppic_img_shuxing_bg", "ui_fatal01_popuppic_img_bg01", "ui_recharg_img_timetxtbg_FatalException2026deal", "",
        popup_text1, "2e17a0", "ffffff", "84f5ff", "0164b9",
        popup_text2, popup_text3, "", "Popup_Button_GoNow"
    ]]
    n = append_csv(popup_path, popup_rows, key_indices=[0])
    total_added += n
    log_cb(f"AdsPopUp.csv: Đã ghi thêm {n} dòng (PopUp {popup_id}, 27 cột đầy đủ màu & text)")

    return total_added


def generate_items_and_jumps(target_dir: str, cfg: Dict[str, Any], log_cb) -> int:
    """
    Tạo Item.csv (26 cột), ItemExpiration.csv (9 cột), Jump.csv (13 cột), JumpSource.csv (9 cột).
    """
    total_added = 0
    season = str(cfg.get("season", "13")).strip()
    act_id = str(cfg["activity_id"]).strip()
    event_name = str(cfg.get("event_name", "")).strip()
    end_time = str(cfg["end_time"]).strip()
    token_trade_id = str(cfg["token_trade_id"]).strip()
    token_encrypted_id = str(cfg["token_encrypted_id"]).strip()
    substore_id = str(cfg.get("substore_id", "9898")).strip()

    jump_activity_id = str(cfg.get("jump_activity_id", f"1{act_id}")).strip()
    jump_gacha_id = str(cfg.get("jump_gacha_id", f"{act_id}1")).strip()
    jump_iap_id = str(cfg.get("jump_iap_id", f"1{substore_id}")).strip()
    jumpsource_id = str(cfg.get("jumpsource_id", "598")).strip()

    is_camp = not is_variant_event(cfg)
    if not is_camp and not event_name:
        raise ValueError("Event biến thể cần có Event Theme Name.")

    # 1. Item.csv (26 cột)
    item_trade_name_key = "ItemName1111011" if is_camp else f"ItemName{token_trade_id}"
    item_trade_desc_key = "ItemDesc1111011" if is_camp else f"ItemDesc{token_trade_id}"
    item_enc_name_key = "ItemName1120021" if is_camp else f"ItemName{token_encrypted_id}"
    item_enc_desc_key = "ItemDesc1120021" if is_camp else f"ItemDesc{token_encrypted_id}"

    enc_note = "For pulling Fatal Exception Characters Motherbox"
    display_name = "Hero" if get_clean_event_id(event_name).lower() in ["superheroes", "hero"] else event_name
    enc_col1 = f"Fatal Encrypted Token s{season}" if is_camp else f"{display_name} Encrypted Token s{season}"

    item_path = os.path.join(target_dir, "Item.csv")
    item_rows = [
        # Col: 0..25 = 26 cols
        [token_trade_id, f"Fatal Trade Token 1(s{season})", item_trade_name_key, item_trade_desc_key, "Fatal Exception Milestone Point", "1", "", "", "", "1", "", "", "", "", "", "4", "4", "5", "65", "ui_item_1111011", "", "0", "", "", "", "3600"],
        [token_encrypted_id, enc_col1, item_enc_name_key, item_enc_desc_key, enc_note, "1", "", "", "", "1", "", "", "", "", "", "2", "1", "5", "75", "ui_item_1120021", "", "0", "", "", "", "470"],
    ]
    n = append_csv(item_path, item_rows, key_indices=[0])
    total_added += n
    log_cb(f"Item.csv: Đã ghi thêm {n}/2 tokens (1 Trade Token và 1 Encrypted Token)")

    # 2. ItemExpiration.csv (9 cột)
    exp_path = os.path.join(target_dir, "ItemExpiration.csv")
    exp_rows = [
        [token_trade_id, f"Fatal Trade Token 1 s{season}", "1", end_time, "1980170017", "56", "Expired Item Reclamation Compensation", "11", ""],
        [token_encrypted_id, enc_col1, "1", end_time, "1980170018", "56", "Expired Item Reclamation Compensation", "11", ""]
    ]
    n = append_csv(exp_path, exp_rows, key_indices=[0])
    total_added += n
    log_cb(f"ItemExpiration.csv: Đã ghi thêm {n}/2 dòng thu hồi token (9 cột)")

    # 3. Jump.csv (13 cột)
    jump_path = os.path.join(target_dir, "Jump.csv")
    jump_rows = [
        [jump_activity_id, "18", f"Jump to the corresponding subpage of the activity center Standalone 1 Event", act_id, "", "", "", "", "1", "Corresponding activity table corresponding activity ID", "ActivityCenter", "", "1"],
        [jump_gacha_id, "8", f"Skip to gacha - {event_name if event_name else 'Standalone S' + season} Motherbox", act_id, "", "", "", "", "1", "Corresponds to AllyGachaType table card pool ID", get_main_motherbox_text_keys(act_id)[0], "", "1"],
        [jump_iap_id, "25", f"Skip to IAP - Standalone IAP", "4", substore_id, "", "", "", "1", "Func Corresponding to PayStoreSub table", "Func_fufeishangcheng", "COMMON_Ended", "1"]
    ]
    n = append_csv(jump_path, jump_rows, key_indices=[0])
    total_added += n
    log_cb(f"Jump.csv: Đã ghi thêm {n}/3 jumps (chuẩn 13 cột)")

    # 4. JumpSource.csv (9 cột)
    js_path = os.path.join(target_dir, "JumpSource.csv")
    js_rows = [[jumpsource_id, token_encrypted_id, "Fatal Encrypted Token", jump_activity_id, jump_iap_id, "", "", "", ""]]
    n = append_csv(js_path, js_rows, key_indices=[0])
    total_added += n
    log_cb(f"JumpSource.csv: Đã ghi thêm {n} dòng (Source {jumpsource_id}, 9 cột)")

    return total_added


def generate_shop(target_dir: str, cfg: Dict[str, Any], log_cb) -> int:
    """
    Tạo Shop.csv (20 cột) và các mặt hàng trong ShopItem.csv (28 cột).
    - Cột 13 (BeforeItemID) được chèn đúng giá trị rỗng ("") chống xô lệch cột.
    - Hỗ trợ danh sách Tướng tùy biến trong cấu hình (shop_characters).
    """
    total_added = 0
    shop_id = str(cfg["shop_id"]).strip()
    act_id = str(cfg["activity_id"]).strip()
    season = str(cfg.get("season", "13")).strip()
    token_trade_id = str(cfg["token_trade_id"]).strip()
    token_encrypted_id = str(cfg["token_encrypted_id"]).strip()

    # 1. Shop.csv (20 cột)
    shop_path = os.path.join(target_dir, "Shop.csv")
    shop_note = f"Standalone 1 s{season}"
    existing_shop_rows = read_csv(shop_path)
    existing_shop = next(
        (r for r in existing_shop_rows if r and r[0].strip() == shop_id), None
    )
    if existing_shop and (
        len(existing_shop) <= 19
        or existing_shop[6].strip() != act_id
        or existing_shop[19].strip() != shop_note
    ):
        raise ValueError(
            f"Shop ID {shop_id} đã được dùng bởi shop khác trong Shop.csv. "
            "Hãy nhập một Shop ID chưa được sử dụng; tool không tự đổi ID để bảo đảm "
            "khớp với ActivityCollectionGroup.csv."
        )

    shop_rows = [[shop_id, "14", "200", "shopnameStandalone", "ui_shop_img_blackbox_", "", act_id, "", "", "", "", "", "", "", "", "", "", "", "0", shop_note]]
    n = append_csv(shop_path, shop_rows, key_indices=[0])
    total_added += n
    log_cb(f"Shop.csv: Đã ghi thêm {n} dòng (Shop {shop_id}, 20 cột)")

    # 2. Xây dựng danh sách Shop Items linh hoạt
    # Danh mục vật phẩm cố định (Materials)
    fixed_materials = [
        {"name": "Inertron Aloy (Universal)", "item_id": "1121003", "num": "10", "limit": "5", "price": "400", "open": "1230", "label": ""},
        {"name": "Inertron Alloy - Mighty", "item_id": "1121004", "num": "10", "limit": "5", "price": "300", "open": "1230", "label": ""},
        {"name": "Inertron Alloy - Agile", "item_id": "1121005", "num": "10", "limit": "5", "price": "300", "open": "1230", "label": ""},
        {"name": "Inertron Alloy - Tactical", "item_id": "1121006", "num": "10", "limit": "5", "price": "300", "open": "1230", "label": ""},
        {"name": "Inertronite", "item_id": "1121002", "num": "15", "limit": "5", "price": "200", "open": "1230", "label": ""},
        {"name": "Inertron Fragment", "item_id": "1121001", "num": "30", "limit": "5", "price": "200", "open": "1230", "label": ""},
        {"name": "Reinforcement Rank Up Chip", "item_id": "1120031", "num": "5", "limit": "5", "price": "400", "open": "", "label": ""},
        {"name": "Random Coordinates", "item_id": "1123100", "num": "5", "limit": "5", "price": "200", "open": "1830", "label": ""}
    ]

    # Lấy danh sách tướng từ config (hoặc mặc định)
    char_list = cfg.get("shop_characters", get_default_shop_characters())
    featured_chars = [c for c in char_list if c.get("featured", False)]
    regular_chars = [c for c in char_list if not c.get("featured", False)]

    # Sắp xếp các mục theo đúng thứ tự logic game:
    # 1..3: Tokens (FET, SET, ET)
    # 4..(3+len(featured)): Tướng Featured
    # Tiếp theo: 8 Materials
    # Tiếp theo: Các tướng còn lại
    all_items_to_generate = []

    # Item 1: FET
    all_items_to_generate.append({
        "name": "Fatal Encrypted Token", "item_id": token_encrypted_id, "num": "1",
        "limit": "5", "price": "2500", "open": "", "label": "StoreDiscount_Label_Hot"
    })
    # Item 2: SET
    all_items_to_generate.append({
        "name": "SET", "item_id": "1120016", "num": "1",
        "limit": "10", "price": "100", "open": "", "label": "StoreDiscount_Label_Hot"
    })
    # Item 3: ET
    all_items_to_generate.append({
        "name": "ET", "item_id": "1120015", "num": "1",
        "limit": "5", "price": "40", "open": "", "label": "StoreDiscount_Label_Hot"
    })

    # Featured Chars
    for fc in featured_chars:
        all_items_to_generate.append({
            "name": f"{fc['name']} Fragments", "item_id": fc["item_id"], "num": fc.get("num", "10"),
            "limit": fc.get("limit", "3"), "price": fc.get("price", "900"), "open": "", "label": "StoreDiscount_Label_Hot"
        })

    # 8 Materials
    for mat in fixed_materials:
        all_items_to_generate.append(mat)

    # Regular Chars
    for rc in regular_chars:
        all_items_to_generate.append({
            "name": f"{rc['name']} Fragments", "item_id": rc["item_id"], "num": rc.get("num", "10"),
            "limit": rc.get("limit", "1"), "price": rc.get("price", "850"), "open": "", "label": "StoreDiscount_Label_Hot"
        })

    # 3. Tạo row ShopItem.csv (28 cột chuẩn vị trí)
    # Cấu trúc 28 cột:
    # 0: ID
    # 1: Name
    # 2: Season Note
    # 3: ""
    # 4: Remove ("")
    # 5: ShopType
    # 6: Position
    # 7: PositionWeight (100)
    # 8: ItemType ("")
    # 9: OpenLevel
    # 10: CloseLevel ("")
    # 11: TotalLimits ("")
    # 12: InheritLimits ("")
    # 13: BeforeItemID ("") <--- Đây là cột trước đó bị thiếu!
    # 14: LimitTimes
    # 15: Item (Item ID)
    # 16: Num
    # 17: CostId (Token ID)
    # 18: Price
    # 19: PriceGrow ("")
    # 20: GrowDiscount ("")
    # 21: FixDiscount ("10000")
    # 22: RandomDiscount ("")
    # 23: StartTime ("")
    # 24: EndTime ("")
    # 25: Version ("1")
    # 26: DiscountRarity ("")
    # 27: DiscountLabel
    shop_item_path = os.path.join(target_dir, "ShopItem.csv")
    shop_item_rows = []
    season_note = f"Standalone 1 - Season {season}"

    for idx, item in enumerate(all_items_to_generate, start=1):
        # ShopItem.ID follows the event ID pattern; ShopType links to Shop.csv.
        item_id_code = f"{act_id}{idx:02d}01"
        pos_str = str(idx)
        open_lvl = item.get("open", "")
        limit_str = str(item.get("limit", "1"))
        reward_item_id = str(item.get("item_id", ""))
        num_str = str(item.get("num", "10"))
        price_str = str(item.get("price", "850"))
        label_str = item.get("label", "")

        row = [
            item_id_code, item["name"], season_note, "", "",
            shop_id, pos_str, "100", "", open_lvl,
            "", "", "", "", limit_str,
            reward_item_id, num_str, token_trade_id, price_str, "",
            "", "10000", "", "", "",
            "1", "", label_str
        ]
        shop_item_rows.append(row)

    n = append_csv(shop_item_path, shop_item_rows, key_indices=[0])
    total_added += n
    log_cb(f"ShopItem.csv: Đã ghi thêm {n}/{len(all_items_to_generate)} mặt hàng (chuẩn 28 cột, khớp vị trí Col 13 BeforeItemID)")

    return total_added


def generate_language_files(target_dir: str, cfg: Dict[str, Any], log_cb) -> int:
    """Generate gacha labels and, for variants, popup and token item text."""
    event_name = str(cfg.get("event_name", "")).strip()
    event_id = str(cfg["activity_id"]).strip()
    season = str(cfg.get("season", "")).strip()
    variant = is_variant_event(cfg)
    if variant and not event_name:
        raise ValueError("Event biến thể cần có Event Theme Name.")

    clean_name = get_clean_event_id(event_name)
    is_hero_theme = clean_name.lower() in ["superheroes", "hero"]
    display_name = (("Super Hero" if is_hero_theme else event_name) if variant else f"Season {season}")
    gacha_name_key, gacha_tab_key = get_main_motherbox_text_keys(event_id)
    gacha_tab_text = f"Fatal Recruitment: {event_name}" if variant else f"Fatal Recruitment: Season {season}"

    # SourceCommonUI only receives the two main gacha strings.
    common_ui_rows = [
        [gacha_tab_key, "Gacha Tab", "Standalone Event", gacha_tab_text],
        [gacha_name_key, "Gacha Name", "Standalone Event", f"Increased chance to obtain {display_name} characters"],
    ]
    common_ui_path = os.path.join(target_dir, "Language", "SourceCommonUI.csv")
    total_added = append_csv(common_ui_path, common_ui_rows, key_indices=[0])
    log_cb(f"Language/SourceCommonUI.csv: Added {total_added}/2 AllyGachaTab and AllyGachaName rows")

    if not variant:
        return total_added

    recruitment_name = "heroes" if is_hero_theme else event_name.lower()
    popup_rows = [
        [f"Popup_{clean_name}_Title", "Pop Up Text", "Standalone Event", str(cfg.get("popup_title_text", "")).strip() or f"<size=90>Fatal Exception: {event_name}</size>", ""],
        [f"Popup_{clean_name}_Subtitle", "Pop Up Text", "Standalone Event", str(cfg.get("popup_subtitle_text", "")).strip() or "The ultimate trial has arrived!", ""],
        [f"Popup_{clean_name}_Desc", "Pop Up Text", "Standalone Event", str(cfg.get("popup_desc_text", "")).strip() or f"Face brutal challenges, earn epic rewards, and recruit powerful {recruitment_name} from the all-new Mother Box.", ""],
    ]
    activity_ui_path = os.path.join(target_dir, "Language", "SourceActivityUI.csv")
    popup_added = append_csv(activity_ui_path, popup_rows, key_indices=[0])
    total_added += popup_added
    log_cb(f"Language/SourceActivityUI.csv: Added {popup_added}/3 variant popup text rows")

    token_trade_id = str(cfg["token_trade_id"]).strip()
    token_encrypted_id = str(cfg["token_encrypted_id"]).strip()
    item_rows = [
        [f"ItemName{token_trade_id}", "Standalone Event", "Event Token Name", str(cfg.get("item_trade_name_text", "")).strip() or f"{display_name} Trade Token", ""],
        [f"ItemDesc{token_trade_id}", "Standalone Event", "Event Token Description", str(cfg.get("item_trade_desc_text", "")).strip() or f"A token forged from the chaos of Fatal Exception: {event_name}. Use it to claim exclusive rewards from the event shop.", ""],
        [f"ItemName{token_encrypted_id}", "Standalone Event", "Fatal Encrypted Token", str(cfg.get("item_encrypted_name_text", "")).strip() or f"{display_name} Encrypted Token", ""],
        [f"ItemDesc{token_encrypted_id}", "Standalone Event", "Fatal Encrypted Token Description", str(cfg.get("item_encrypted_desc_text", "")).strip() or "Can be used to recruit heroes up to legendary tier in <color=#FAA520>**Fatal Exception Mother Box - Character Recruitment**</color>.", ""],
    ]
    item_desc_path = os.path.join(target_dir, "Language", "SourceItemDesc.csv")
    item_added = append_csv(item_desc_path, item_rows, key_indices=[0])
    total_added += item_added
    log_cb(f"Language/SourceItemDesc.csv: Added {item_added}/4 variant item text rows")
    return total_added


# ===============================================================================
# 6. GRAPHICAL USER INTERFACE
# ===============================================================================
class StandaloneEventToolApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Standalone Event Auto Tool - DCWC LiveOps")
        self.root.geometry("1080x880")
        self.root.minsize(980, 780)

        self.config_data = load_config()

        # Biến trạng thái
        self.var_target_dir = tk.StringVar(value=self.config_data.get("target_dir", ""))
        self.var_reward_file = tk.StringVar(value=self.config_data.get("reward_file", ""))
        self.var_season = tk.StringVar(value=self.config_data.get("season", "13"))
        self.var_activity_id = tk.StringVar(value=self.config_data.get("activity_id", "8029"))
        self.var_event_name = tk.StringVar(value=self.config_data.get("event_name", "Superheroes"))
        inferred_variant = bool(self.var_event_name.get().strip()) and not is_campaign_event(self.var_event_name.get())
        self.var_event_variant = tk.BooleanVar(value=self.config_data.get("event_variant", inferred_variant))
        self.var_start_time = tk.StringVar(value=self.config_data.get("start_time", "20261211_000000"))
        self.var_end_time = tk.StringVar(value=self.config_data.get("end_time", "20261218_000000"))
        self.var_item_trade_name_text = tk.StringVar(value=self.config_data.get("item_trade_name_text", ""))
        self.var_item_trade_desc_text = tk.StringVar(value=self.config_data.get("item_trade_desc_text", ""))
        self.var_item_encrypted_name_text = tk.StringVar(value=self.config_data.get("item_encrypted_name_text", ""))
        self.var_item_encrypted_desc_text = tk.StringVar(value=self.config_data.get("item_encrypted_desc_text", ""))
        self.var_popup_title_text = tk.StringVar(value=self.config_data.get("popup_title_text", ""))
        self.var_popup_subtitle_text = tk.StringVar(value=self.config_data.get("popup_subtitle_text", ""))
        self.var_popup_desc_text = tk.StringVar(value=self.config_data.get("popup_desc_text", ""))
        self.variant_text_entries = []

        # Tokens & Jumps
        self.var_token_trade = tk.StringVar(value=self.config_data.get("token_trade_id", "1111020"))
        self.var_token_encrypted = tk.StringVar(value=self.config_data.get("token_encrypted_id", "1120054"))
        self.var_gacha_type = tk.StringVar(value=self.config_data.get("gacha_type_id", "8029"))
        self.var_shop_id = tk.StringVar(value=self.config_data.get("shop_id", "9898"))
        self.var_substore_id = tk.StringVar(value=self.config_data.get("substore_id", "9898"))
        self.var_banner_id = tk.StringVar(value=self.config_data.get("banner_id", "516"))
        self.var_popup_id = tk.StringVar(value=self.config_data.get("popup_id", "518"))
        self.var_jump_activity = tk.StringVar(value=self.config_data.get("jump_activity_id", "18029"))
        self.var_jump_gacha = tk.StringVar(value=self.config_data.get("jump_gacha_id", "80291"))
        self.var_jump_iap = tk.StringVar(value=self.config_data.get("jump_iap_id", "19898"))
        self.var_jumpsource = tk.StringVar(value=self.config_data.get("jumpsource_id", "598"))

        # RuleDesc Key & Set
        is_camp = not self.var_event_variant.get()
        default_rule_key = "8019" if is_camp else self.var_activity_id.get()
        self.var_rule_desc_key = tk.StringVar(value=self.config_data.get("rule_desc_key", default_rule_key))
        self.chk_create_ruledesc = tk.BooleanVar(value=self.config_data.get("create_ruledesc", not is_camp))
        self.var_rule_desc_text = tk.StringVar(value=self.config_data.get("rule_desc_text", ""))

        self.var_event_name.trace_add("write", self.on_event_info_change)
        self.var_activity_id.trace_add("write", self.on_event_info_change)
        self.var_event_variant.trace_add("write", self.on_variant_mode_change)

        # Gacha Rewards
        self.var_leg_reward = tk.StringVar(value=self.config_data.get("gacha_leg_reward_id", "12000114"))
        self.var_epic_reward = tk.StringVar(value=self.config_data.get("gacha_epic_reward_id", "12000115"))
        self.var_elite_reward = tk.StringVar(value=self.config_data.get("gacha_elite_reward_id", "12000116"))
        self.var_rare_reward = tk.StringVar(value=self.config_data.get("gacha_rare_reward_id", "12000117"))

        # 12 Task Rewards
        saved_tasks = self.config_data.get("task_rewards", [])
        if len(saved_tasks) < 12:
            saved_tasks = saved_tasks + [""] * (12 - len(saved_tasks))
        self.var_task_rewards = [tk.StringVar(value=saved_tasks[i]) for i in range(12)]

        # Danh sách tướng Shop
        self.shop_characters: List[Dict[str, Any]] = self.config_data.get("shop_characters", get_default_shop_characters())

        # Checkboxes
        self.chk_activity = tk.BooleanVar(value=self.config_data.get("gen_activity", True))
        self.chk_milestones = tk.BooleanVar(value=self.config_data.get("gen_collection_reward", True))
        self.chk_tasks = tk.BooleanVar(value=self.config_data.get("gen_tasks", True))
        self.chk_gacha = tk.BooleanVar(value=self.config_data.get("gen_gacha_banner", True))
        self.chk_items = tk.BooleanVar(value=self.config_data.get("gen_items_jumps", True))
        self.chk_shop = tk.BooleanVar(value=self.config_data.get("gen_shop", True))
        self.chk_lang = tk.BooleanVar(value=self.config_data.get("gen_language", True))

        self.build_ui()

    def build_ui(self):
        style = ttk.Style()
        style.theme_use('clam')

        # 1. Header
        header_frame = tk.Frame(self.root, bg="#1E293B", pady=10)
        header_frame.pack(fill="x")
        title_lbl = tk.Label(
            header_frame, text="STANDALONE EVENT AUTO GENERATOR (ACTIVITY TYPE 6)",
            font=("Segoe UI", 13, "bold"), fg="#F8FAFC", bg="#1E293B"
        )
        title_lbl.pack()
        sub_lbl = tk.Label(
            header_frame, text="Tự động tạo sự kiện Standalone / Fatal Exception - Chuẩn Perforce, UTF-8 BOM, không xô lệch cột",
            font=("Segoe UI", 9), fg="#94A3B8", bg="#1E293B"
        )
        sub_lbl.pack()

        # 2. Top File Bar
        top_bar = ttk.LabelFrame(self.root, text=" 1. Thư mục đích & File Reward CSV ", padding=8)
        top_bar.pack(fill="x", padx=12, pady=6)

        # Target Dir
        ttk.Label(top_bar, text="Target Dir (Perforce /excel):").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(top_bar, textvariable=self.var_target_dir, width=75).grid(row=0, column=1, sticky="ew", padx=4, pady=3)
        ttk.Button(top_bar, text="Chọn thư mục...", command=self.browse_target_dir).grid(row=0, column=2, padx=4, pady=3)

        # Reward File
        ttk.Label(top_bar, text="Reward File CSV:").grid(row=1, column=0, sticky="w", padx=4, pady=3)
        ttk.Entry(top_bar, textvariable=self.var_reward_file, width=75).grid(row=1, column=1, sticky="ew", padx=4, pady=3)
        ttk.Button(top_bar, text="Chọn file Reward...", command=self.browse_reward_file).grid(row=1, column=2, padx=4, pady=3)
        top_bar.columnconfigure(1, weight=1)

        # 3. Main Notebook (Tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=12, pady=4)

        # Tab 1: Event & Tokens
        tab1 = ttk.Frame(notebook, padding=10)
        notebook.add(tab1, text="  Thông tin Sự kiện & Tokens  ")
        self.build_tab_event(tab1)

        # Tab 2: Quà & Nhiệm vụ & Gacha
        tab2 = ttk.Frame(notebook, padding=10)
        notebook.add(tab2, text="  Quà Nhiệm Vụ & Gacha Pools  ")
        self.build_tab_rewards(tab2)

        # Tab 3: Shop & Tướng Shop
        tab3 = ttk.Frame(notebook, padding=10)
        notebook.add(tab3, text="  Cửa Hàng (Shop) & Tướng Đổi Thưởng  ")
        self.build_tab_shop(tab3)

        tab4 = ttk.Frame(notebook, padding=10)
        notebook.add(tab4, text="  Text Event Biến Thể  ")
        self.build_tab_variant_text(tab4)

        # 4. Checkbox Options Bar
        opt_frame = ttk.LabelFrame(self.root, text=" Tùy chọn sinh dữ liệu (Checkboxes) ", padding=6)
        opt_frame.pack(fill="x", padx=12, pady=4)

        c1 = ttk.Checkbutton(opt_frame, text="Activity & Group (15/13 cols)", variable=self.chk_activity)
        c1.grid(row=0, column=0, sticky="w", padx=8)
        c2 = ttk.Checkbutton(opt_frame, text="Milestones (Copy 60 mốc từ 8019)", variable=self.chk_milestones)
        c2.grid(row=0, column=1, sticky="w", padx=8)
        c3 = ttk.Checkbutton(opt_frame, text="Tasks (12 Nhiệm vụ, 24 cols)", variable=self.chk_tasks)
        c3.grid(row=0, column=2, sticky="w", padx=8)
        c4 = ttk.Checkbutton(opt_frame, text="Gacha & Banners (14/39/27 cols)", variable=self.chk_gacha)
        c4.grid(row=0, column=3, sticky="w", padx=8)

        c5 = ttk.Checkbutton(opt_frame, text="Tokens & Jumps (26/13 cols)", variable=self.chk_items)
        c5.grid(row=1, column=0, sticky="w", padx=8, pady=3)
        c6 = ttk.Checkbutton(opt_frame, text="Shop & ShopItems (28 cols chuẩn)", variable=self.chk_shop)
        c6.grid(row=1, column=1, sticky="w", padx=8, pady=3)
        c7 = ttk.Checkbutton(opt_frame, text="Gacha, Popup & Item Text", variable=self.chk_lang)
        c7.grid(row=1, column=2, sticky="w", padx=8, pady=3)

        # 5. Buttons Bar
        btn_frame = tk.Frame(self.root, pady=4)
        btn_frame.pack(fill="x", padx=12)

        btn_run = tk.Button(
            btn_frame, text="▶ THỰC THI (GENERATE ALL)",
            font=("Segoe UI", 10, "bold"), bg="#10B981", fg="white",
            padx=16, pady=6, relief="flat", command=self.run_generation
        )
        btn_run.pack(side="left", padx=4)

        btn_val = tk.Button(
            btn_frame, text="🔍 KIỂM TRA TRƯỚC (DRY RUN)",
            font=("Segoe UI", 9, "bold"), bg="#3B82F6", fg="white",
            padx=12, pady=6, relief="flat", command=self.run_dry_run
        )
        btn_val.pack(side="left", padx=4)

        btn_save = tk.Button(
            btn_frame, text="💾 Lưu Cấu Hình",
            font=("Segoe UI", 9), bg="#64748B", fg="white",
            padx=10, pady=6, relief="flat", command=self.save_current_config
        )
        btn_save.pack(side="left", padx=4)

        btn_clear = tk.Button(
            btn_frame, text="🧹 Xóa Log",
            font=("Segoe UI", 9), bg="#94A3B8", fg="white",
            padx=10, pady=6, relief="flat", command=self.clear_log
        )
        btn_clear.pack(side="right", padx=4)

        # 6. Console / Log Box
        log_frame = ttk.LabelFrame(self.root, text=" Nhật ký Thực thi (Log Console) ", padding=4)
        log_frame.pack(fill="both", expand=True, padx=12, pady=6)

        self.log_text = ScrolledText(log_frame, height=7, font=("Consolas", 9), bg="#0F172A", fg="#E2E8F0")
        self.log_text.pack(fill="both", expand=True)

        self.log_text.tag_config("INFO", foreground="#38BDF8")
        self.log_text.tag_config("SUCCESS", foreground="#4ADE80", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("WARN", foreground="#FBBF24")
        self.log_text.tag_config("ERROR", foreground="#F87171", font=("Consolas", 9, "bold"))

        self.log("Tool Standalone Event đã khởi động sẵn sàng!", "INFO")

    def build_tab_event(self, parent):
        grid_opts = {"sticky": "w", "padx": 6, "pady": 4}

        # Row 0: Season & Activity ID & Event Name
        ttk.Label(parent, text="Season (Ví dụ: 13):").grid(row=0, column=0, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_season, width=15).grid(row=0, column=1, **grid_opts)

        ttk.Label(parent, text="Activity ID (Ví dụ: 8029):").grid(row=0, column=2, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_activity_id, width=15).grid(row=0, column=3, **grid_opts)

        ttk.Label(parent, text="Event Theme Name:").grid(row=0, column=4, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_event_name, width=22).grid(row=0, column=5, **grid_opts)

        ttk.Checkbutton(
            parent, text="Event biến thể (bỏ chọn = Event gốc)",
            variable=self.var_event_variant
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=6, pady=1)
        ttk.Label(
            parent, text="Event gốc dùng lại text có sẵn; biến thể cần tên Event.",
            font=("Segoe UI", 8, "italic"), foreground="#64748B"
        ).grid(row=1, column=3, columnspan=3, sticky="w", padx=6, pady=1)

        # Row 2: Start Time & End Time
        ttk.Label(parent, text="Start Time (YYYYMMDD_000000):").grid(row=2, column=0, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_start_time, width=22).grid(row=2, column=1, columnspan=2, **grid_opts)

        ttk.Label(parent, text="End Time (YYYYMMDD_000000):").grid(row=2, column=3, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_end_time, width=22).grid(row=2, column=4, columnspan=2, **grid_opts)

        # Separator & Smart Auto Calculate Button
        sep_frame = tk.Frame(parent)
        sep_frame.grid(row=3, column=0, columnspan=6, sticky="ew", pady=8)
        ttk.Separator(sep_frame, orient="horizontal").pack(side="left", fill="x", expand=True)

        btn_auto_id = tk.Button(
            sep_frame, text="⚡ TỰ ĐỘNG TÍNH ID KẾ TIẾP (+1 TỪ TARGET EXCEL)",
            font=("Segoe UI", 8, "bold"), bg="#8B5CF6", fg="white",
            padx=10, pady=2, relief="flat", command=self.auto_fill_next_ids
        )
        btn_auto_id.pack(side="right", padx=6)

        # Row 4: Token IDs
        ttk.Label(parent, text="Hero/Fatal Trade Token ID:").grid(row=4, column=0, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_token_trade, width=15).grid(row=4, column=1, **grid_opts)

        ttk.Label(parent, text="Fatal Encrypted Token (FET):").grid(row=4, column=2, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_token_encrypted, width=15).grid(row=4, column=3, **grid_opts)

        # Row 5: Banners & Jumps
        ttk.Label(parent, text="Ads Banner ID:").grid(row=5, column=0, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_banner_id, width=15).grid(row=5, column=1, **grid_opts)

        ttk.Label(parent, text="Ads PopUp ID:").grid(row=5, column=2, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_popup_id, width=15).grid(row=5, column=3, **grid_opts)

        ttk.Label(parent, text="Jump Activity ID:").grid(row=5, column=4, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_jump_activity, width=15).grid(row=5, column=5, **grid_opts)

        # Row 6: Jumps continued
        ttk.Label(parent, text="Jump Gacha ID:").grid(row=6, column=0, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_jump_gacha, width=15).grid(row=6, column=1, **grid_opts)

        ttk.Label(parent, text="Jump IAP ID:").grid(row=6, column=2, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_jump_iap, width=15).grid(row=6, column=3, **grid_opts)

        ttk.Label(parent, text="JumpSource ID:").grid(row=6, column=4, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_jumpsource, width=15).grid(row=6, column=5, **grid_opts)

        # Row 7: RuleDesc Key & Checkbox
        ttk.Label(parent, text="RuleDesc Key (Activity Col 11):").grid(row=7, column=0, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_rule_desc_key, width=15).grid(row=7, column=1, **grid_opts)

        chk_rd = ttk.Checkbutton(
            parent,
            text="Tạo bộ RuleDesc mới (ID & Text trong SourceCommonUI)",
            variable=self.chk_create_ruledesc
        )
        chk_rd.grid(row=7, column=2, columnspan=4, sticky="w", padx=6, pady=4)

        # Row 8: Rule Description text
        ttk.Label(parent, text="Custom Rule Text (Dấu ?):").grid(row=8, column=0, **grid_opts)
        ttk.Entry(parent, textvariable=self.var_rule_desc_text, width=70).grid(row=8, column=1, columnspan=5, sticky="ew", padx=6, pady=4)

    def build_tab_variant_text(self, parent):
        ttk.Label(
            parent,
            text="Các nội dung này chỉ được sinh khi chọn Event biến thể. Để trống từng ô sẽ dùng nội dung mẫu theo tên Event.",
            wraplength=900
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=8)

        fields = [
            ("Trade Token Name", self.var_item_trade_name_text),
            ("Trade Token Description", self.var_item_trade_desc_text),
            ("Encrypted Token Name", self.var_item_encrypted_name_text),
            ("Encrypted Token Description", self.var_item_encrypted_desc_text),
            ("PopUp Title", self.var_popup_title_text),
            ("PopUp Subtitle", self.var_popup_subtitle_text),
            ("PopUp Description", self.var_popup_desc_text),
        ]
        for row, (label, variable) in enumerate(fields, start=1):
            ttk.Label(parent, text=label + ":").grid(row=row, column=0, sticky="w", padx=6, pady=5)
            entry = ttk.Entry(parent, textvariable=variable, width=100)
            entry.grid(row=row, column=1, sticky="ew", padx=6, pady=5)
            self.variant_text_entries.append(entry)
        parent.columnconfigure(1, weight=1)
        self.update_variant_text_state()

    def update_variant_text_state(self):
        state = "normal" if self.var_event_variant.get() else "disabled"
        for entry in self.variant_text_entries:
            entry.configure(state=state)

    def on_variant_mode_change(self, *args):
        self.update_variant_text_state()
        self.on_event_info_change()

    def on_event_info_change(self, *args):
        evt = self.var_event_name.get().strip()
        act = self.var_activity_id.get().strip()
        if not self.var_event_variant.get():
            self.var_rule_desc_key.set("8019")
            self.chk_create_ruledesc.set(False)
        else:
            self.var_rule_desc_key.set(act if act else "8029")
            self.chk_create_ruledesc.set(True)

    def build_tab_rewards(self, parent):
        grid_opts = {"sticky": "w", "padx": 6, "pady": 3}

        # Header Gacha Rewards
        gacha_frame = ttk.LabelFrame(parent, text=" 4 Gacha Motherbox Reward IDs (Tự trích xuất từ file Reward) ", padding=6)
        gacha_frame.pack(fill="x", pady=4)

        ttk.Label(gacha_frame, text="Legendary Pool:").grid(row=0, column=0, **grid_opts)
        ttk.Entry(gacha_frame, textvariable=self.var_leg_reward, width=16).grid(row=0, column=1, **grid_opts)

        ttk.Label(gacha_frame, text="Epic Pool:").grid(row=0, column=2, **grid_opts)
        ttk.Entry(gacha_frame, textvariable=self.var_epic_reward, width=16).grid(row=0, column=3, **grid_opts)

        ttk.Label(gacha_frame, text="Elite Pool:").grid(row=0, column=4, **grid_opts)
        ttk.Entry(gacha_frame, textvariable=self.var_elite_reward, width=16).grid(row=0, column=5, **grid_opts)

        ttk.Label(gacha_frame, text="Rare Pool:").grid(row=0, column=6, **grid_opts)
        ttk.Entry(gacha_frame, textvariable=self.var_rare_reward, width=16).grid(row=0, column=7, **grid_opts)

        # Header Task Rewards
        task_frame = ttk.LabelFrame(parent, text=" 12 Nhiệm Vụ (5 Daily + 7 Weekly Task Reward IDs) ", padding=6)
        task_frame.pack(fill="both", expand=True, pady=4)

        task_labels = [
            ("D1. Win 3 arena matches:", 0, 0),
            ("D2. Win 3 elite arena matches:", 1, 0),
            ("D3. Evil Falls 1 time:", 2, 0),
            ("D4. Clear Elseworld 1 time:", 3, 0),
            ("D5. Upgrade equipment 5 times:", 4, 0),
            ("W1. Spend 1 Fatal Token:", 0, 2),
            ("W2. LC Stage 1:", 1, 2),
            ("W3. LC Stage 2:", 2, 2),
            ("W4. LC Stage 3:", 3, 2),
            ("W5. 30 Stars Crisis Watch:", 4, 2),
            ("W6. Login 7 Days:", 5, 2),
            ("W7. Win 35 Elite Arena:", 6, 2),
        ]

        for i, (text, r, c) in enumerate(task_labels):
            ttk.Label(task_frame, text=text).grid(row=r, column=c, **grid_opts)
            ttk.Entry(task_frame, textvariable=self.var_task_rewards[i], width=18).grid(row=r, column=c+1, **grid_opts)

        btn_rescan = ttk.Button(task_frame, text="🔄 Quét lại file Reward", command=self.rescan_reward_file)
        btn_rescan.grid(row=5, column=0, columnspan=2, padx=6, pady=6, sticky="ew")

    def build_tab_shop(self, parent):
        grid_opts = {"sticky": "w", "padx": 6, "pady": 4}

        # Top Shop / SubStore IDs
        top_frame = ttk.LabelFrame(parent, text=" Thông tin Shop & SubStore liên kết ", padding=6)
        top_frame.pack(fill="x", pady=4)

        ttk.Label(top_frame, text="Shop ID (Ví dụ: 9898):").grid(row=0, column=0, **grid_opts)
        ttk.Entry(top_frame, textvariable=self.var_shop_id, width=15).grid(row=0, column=1, **grid_opts)

        ttk.Label(top_frame, text="SubStore ID (Dùng cho Jump & Tham chiếu):").grid(row=0, column=2, **grid_opts)
        ttk.Entry(top_frame, textvariable=self.var_substore_id, width=15).grid(row=0, column=3, **grid_opts)

        ttk.Label(top_frame, text="Gacha Type ID:").grid(row=0, column=4, **grid_opts)
        ttk.Entry(top_frame, textvariable=self.var_gacha_type, width=15).grid(row=0, column=5, **grid_opts)

        # Character Fragment Manager
        mgr_frame = ttk.LabelFrame(parent, text=" Quản lý Danh sách Tướng đổi trong Shop (Character Fragments) ", padding=6)
        mgr_frame.pack(fill="both", expand=True, pady=4)

        # Treeview
        tree_cols = ("name", "item_id", "num", "limit", "price", "featured")
        self.tree_chars = ttk.Treeview(mgr_frame, columns=tree_cols, show="headings", height=8, selectmode="browse")
        self.tree_chars.heading("name", text="Tên Tướng / Mảnh")
        self.tree_chars.heading("item_id", text="Item ID")
        self.tree_chars.heading("num", text="Số lượng")
        self.tree_chars.heading("limit", text="Giới hạn mua")
        self.tree_chars.heading("price", text="Giá Token")
        self.tree_chars.heading("featured", text="Featured (Trước Material)")

        self.tree_chars.column("name", width=220)
        self.tree_chars.column("item_id", width=110, anchor="center")
        self.tree_chars.column("num", width=80, anchor="center")
        self.tree_chars.column("limit", width=100, anchor="center")
        self.tree_chars.column("price", width=90, anchor="center")
        self.tree_chars.column("featured", width=140, anchor="center")

        tree_scroll = ttk.Scrollbar(mgr_frame, orient="vertical", command=self.tree_chars.yview)
        self.tree_chars.configure(yscrollcommand=tree_scroll.set)

        self.tree_chars.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        tree_scroll.pack(side="left", fill="y", padx=(0, 4), pady=4)

        # Side controls for editing characters
        ctrl_frame = ttk.Frame(mgr_frame, padding=4)
        ctrl_frame.pack(side="right", fill="y", padx=4)

        self.var_char_name = tk.StringVar()
        self.var_char_id = tk.StringVar()
        self.var_char_num = tk.StringVar(value="10")
        self.var_char_limit = tk.StringVar(value="1")
        self.var_char_price = tk.StringVar(value="850")
        self.var_char_feat = tk.BooleanVar(value=False)

        ttk.Label(ctrl_frame, text="Tên Tướng:").pack(anchor="w", pady=(2, 0))
        ttk.Entry(ctrl_frame, textvariable=self.var_char_name, width=22).pack(fill="x", pady=2)

        ttk.Label(ctrl_frame, text="Item ID:").pack(anchor="w", pady=(2, 0))
        ttk.Entry(ctrl_frame, textvariable=self.var_char_id, width=22).pack(fill="x", pady=2)

        ttk.Label(ctrl_frame, text="Số lượng mảnh (Num):").pack(anchor="w", pady=(2, 0))
        ttk.Entry(ctrl_frame, textvariable=self.var_char_num, width=22).pack(fill="x", pady=2)

        ttk.Label(ctrl_frame, text="Giới hạn mua (Limit):").pack(anchor="w", pady=(2, 0))
        ttk.Entry(ctrl_frame, textvariable=self.var_char_limit, width=22).pack(fill="x", pady=2)

        ttk.Label(ctrl_frame, text="Giá Token (Price):").pack(anchor="w", pady=(2, 0))
        ttk.Entry(ctrl_frame, textvariable=self.var_char_price, width=22).pack(fill="x", pady=2)

        ttk.Checkbutton(ctrl_frame, text="Featured (Top Shop)", variable=self.var_char_feat).pack(anchor="w", pady=4)

        ttk.Button(ctrl_frame, text="➕ Thêm / Lưu Tướng", command=self.add_or_update_char).pack(fill="x", pady=2)
        ttk.Button(ctrl_frame, text="❌ Xóa Tướng Đang Chọn", command=self.delete_selected_char).pack(fill="x", pady=2)
        ttk.Button(ctrl_frame, text="🔄 Mặc định S13 (10 Tướng)", command=self.reset_default_chars).pack(fill="x", pady=(6, 2))

        self.tree_chars.bind("<<TreeviewSelect>>", self.on_char_select)
        self.refresh_chars_tree()

    # --------------------------------------------------------------------------
    # Character Management Handlers
    # --------------------------------------------------------------------------
    def refresh_chars_tree(self):
        for item in self.tree_chars.get_children():
            self.tree_chars.delete(item)
        for idx, c in enumerate(self.shop_characters):
            feat_text = "⭐ Có (Vị trí 4-5)" if c.get("featured", False) else "Không (Sau Material)"
            self.tree_chars.insert("", "end", iid=str(idx), values=(
                c.get("name", ""),
                c.get("item_id", ""),
                c.get("num", "10"),
                c.get("limit", "1"),
                c.get("price", "850"),
                feat_text
            ))

    def on_char_select(self, event):
        selected = self.tree_chars.selection()
        if not selected:
            return
        idx = int(selected[0])
        if 0 <= idx < len(self.shop_characters):
            c = self.shop_characters[idx]
            self.var_char_name.set(c.get("name", ""))
            self.var_char_id.set(c.get("item_id", ""))
            self.var_char_num.set(str(c.get("num", "10")))
            self.var_char_limit.set(str(c.get("limit", "1")))
            self.var_char_price.set(str(c.get("price", "850")))
            self.var_char_feat.set(bool(c.get("featured", False)))

    def add_or_update_char(self):
        name = self.var_char_name.get().strip()
        item_id = self.var_char_id.get().strip()
        num = self.var_char_num.get().strip() or "10"
        limit = self.var_char_limit.get().strip() or "1"
        price = self.var_char_price.get().strip() or "850"
        feat = self.var_char_feat.get()

        if not name or not item_id:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập Tên Tướng và Item ID!")
            return

        selected = self.tree_chars.selection()
        if selected:
            idx = int(selected[0])
            self.shop_characters[idx] = {
                "name": name, "item_id": item_id, "num": num, "limit": limit, "price": price, "featured": feat
            }
            self.log(f"Đã cập nhật Tướng: {name} (ID {item_id})")
        else:
            self.shop_characters.append({
                "name": name, "item_id": item_id, "num": num, "limit": limit, "price": price, "featured": feat
            })
            self.log(f"Đã thêm mới Tướng vào Shop: {name} (ID {item_id})")

        self.refresh_chars_tree()

    def delete_selected_char(self):
        selected = self.tree_chars.selection()
        if not selected:
            messagebox.showinfo("Thông báo", "Vui lòng chọn 1 dòng tướng trong danh sách để xóa!")
            return
        idx = int(selected[0])
        removed = self.shop_characters.pop(idx)
        self.log(f"Đã xóa Tướng khỏi Shop: {removed.get('name')}")
        self.refresh_chars_tree()

    def reset_default_chars(self):
        self.shop_characters = get_default_shop_characters()
        self.refresh_chars_tree()
        self.log("Đã khôi phục danh sách 10 Tướng mặc định Season 13!", "SUCCESS")

    # --------------------------------------------------------------------------
    # Log Helper
    # --------------------------------------------------------------------------
    def log(self, msg: str, tag: str = "INFO"):
        time_str = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{time_str}] {msg}\n"
        self.log_text.insert(tk.END, formatted, tag)
        self.log_text.see(tk.END)

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)

    # --------------------------------------------------------------------------
    # Browse & Rescan Handlers
    # --------------------------------------------------------------------------
    def browse_target_dir(self):
        curr = self.var_target_dir.get().strip() or SCRIPT_DIR
        chosen = filedialog.askdirectory(title="Chọn thư mục excel Perforce", initialdir=curr)
        if chosen:
            self.var_target_dir.set(chosen.replace('\\', '/'))
            self.log(f"Đã chọn Target Dir: {chosen}")
            self.auto_fill_next_ids()

    def browse_reward_file(self):
        curr = os.path.dirname(self.var_reward_file.get().strip()) if self.var_reward_file.get() else self.var_target_dir.get()
        chosen = filedialog.askopenfilename(
            title="Chọn file Reward CSV của Event",
            initialdir=curr,
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if chosen:
            self.var_reward_file.set(chosen.replace('\\', '/'))
            self.rescan_reward_file()

    def rescan_reward_file(self):
        filepath = self.var_reward_file.get().strip()
        if not filepath or not os.path.exists(filepath):
            self.log(f"File Reward không tồn tại: {filepath}", "WARN")
            return

        self.log(f"Đang quét file Reward: {filepath} ...")
        parsed = parse_standalone_reward_csv(filepath, event_name=self.var_event_name.get().strip())

        # Update Gacha
        if parsed["gacha_rewards"]["legendary"]:
            self.var_leg_reward.set(parsed["gacha_rewards"]["legendary"])
        if parsed["gacha_rewards"]["epic"]:
            self.var_epic_reward.set(parsed["gacha_rewards"]["epic"])
        if parsed["gacha_rewards"]["elite"]:
            self.var_elite_reward.set(parsed["gacha_rewards"]["elite"])
        if parsed["gacha_rewards"]["rare"]:
            self.var_rare_reward.set(parsed["gacha_rewards"]["rare"])

        # Update Tasks
        found_task_count = 0
        for i in range(12):
            if parsed["task_rewards"][i]:
                self.var_task_rewards[i].set(parsed["task_rewards"][i])
                found_task_count += 1

        self.log(f"-> Đã bóc tách tự động: {found_task_count}/12 Task Rewards và {sum(1 for v in parsed['gacha_rewards'].values() if v)}/4 Gacha Pools!", "SUCCESS")

    def auto_fill_next_ids(self):
        """Quét thư mục target và tự động điền các ID kế tiếp."""
        td = self.var_target_dir.get().strip()
        act_id = self.var_activity_id.get().strip() or "8029"
        sub_id = self.var_substore_id.get().strip() or "9898"

        self.log("Đang quét các file Perforce để tự động tìm ID kế tiếp...")
        scanned = scan_next_ids_from_target(td, activity_id=act_id, substore_id=sub_id)

        self.var_jumpsource.set(scanned["jumpsource_id"])
        self.var_banner_id.set(scanned["banner_id"])
        self.var_popup_id.set(scanned["popup_id"])
        self.var_token_trade.set(scanned["token_trade_id"])
        self.var_token_encrypted.set(scanned["token_encrypted_id"])
        self.var_jump_activity.set(scanned["jump_activity_id"])
        self.var_jump_gacha.set(scanned["jump_gacha_id"])
        self.var_jump_iap.set(scanned["jump_iap_id"])

        if not self.var_event_variant.get():
            self.var_rule_desc_key.set("8019")
            self.chk_create_ruledesc.set(False)
        else:
            self.var_rule_desc_key.set(act_id)
            self.chk_create_ruledesc.set(True)

        self.log(f"-> Đã tự động cập nhật: JumpSource={scanned['jumpsource_id']}, Banner={scanned['banner_id']}, "
                 f"PopUp={scanned['popup_id']}, TradeToken={scanned['token_trade_id']}, EncryptedToken={scanned['token_encrypted_id']}", "SUCCESS")

    # --------------------------------------------------------------------------
    # Collect Config
    # --------------------------------------------------------------------------
    def collect_config(self) -> Dict[str, Any]:
        return {
            "target_dir": self.var_target_dir.get().strip().replace('\\', '/'),
            "reward_file": self.var_reward_file.get().strip().replace('\\', '/'),
            "season": self.var_season.get().strip(),
            "activity_id": self.var_activity_id.get().strip(),
            "event_name": self.var_event_name.get().strip(),
            "event_variant": self.var_event_variant.get(),
            "item_trade_name_text": self.var_item_trade_name_text.get().strip(),
            "item_trade_desc_text": self.var_item_trade_desc_text.get().strip(),
            "item_encrypted_name_text": self.var_item_encrypted_name_text.get().strip(),
            "item_encrypted_desc_text": self.var_item_encrypted_desc_text.get().strip(),
            "popup_title_text": self.var_popup_title_text.get().strip(),
            "popup_subtitle_text": self.var_popup_subtitle_text.get().strip(),
            "popup_desc_text": self.var_popup_desc_text.get().strip(),
            "start_time": self.var_start_time.get().strip(),
            "end_time": self.var_end_time.get().strip(),
            "token_trade_id": self.var_token_trade.get().strip(),
            "token_encrypted_id": self.var_token_encrypted.get().strip(),
            "gacha_type_id": self.var_gacha_type.get().strip(),
            "gacha_leg_reward_id": self.var_leg_reward.get().strip(),
            "gacha_epic_reward_id": self.var_epic_reward.get().strip(),
            "gacha_elite_reward_id": self.var_elite_reward.get().strip(),
            "gacha_rare_reward_id": self.var_rare_reward.get().strip(),
            "task_rewards": [v.get().strip() for v in self.var_task_rewards],
            "shop_id": self.var_shop_id.get().strip(),
            "substore_id": self.var_substore_id.get().strip(),
            "rule_desc_key": self.var_rule_desc_key.get().strip(),
            "create_ruledesc": self.chk_create_ruledesc.get(),
            "rule_desc_text": self.var_rule_desc_text.get().strip(),
            "banner_id": self.var_banner_id.get().strip(),
            "popup_id": self.var_popup_id.get().strip(),
            "jump_activity_id": self.var_jump_activity.get().strip(),
            "jump_gacha_id": self.var_jump_gacha.get().strip(),
            "jump_iap_id": self.var_jump_iap.get().strip(),
            "jumpsource_id": self.var_jumpsource.get().strip(),
            "shop_characters": self.shop_characters,
            "gen_activity": self.chk_activity.get(),
            "gen_collection_reward": self.chk_milestones.get(),
            "gen_tasks": self.chk_tasks.get(),
            "gen_gacha_banner": self.chk_gacha.get(),
            "gen_items_jumps": self.chk_items.get(),
            "gen_shop": self.chk_shop.get(),
            "gen_language": self.chk_lang.get()
        }

    def save_current_config(self):
        cfg = self.collect_config()
        if save_config(cfg):
            self.log(f"Đã lưu cấu hình vào {CONFIG_FILE} thành công!", "SUCCESS")
            messagebox.showinfo("Thông báo", "Đã lưu cấu hình thành công!")
        else:
            self.log(f"Không thể lưu file cấu hình {CONFIG_FILE}!", "ERROR")

    # --------------------------------------------------------------------------
    # Dry Run / Validation
    # --------------------------------------------------------------------------
    def run_dry_run(self):
        cfg = self.collect_config()
        target_dir = cfg["target_dir"]

        self.log("=" * 60)
        self.log("BẮT ĐẦU KIỂM TRA TRƯỚC (DRY RUN / VALIDATION)...", "INFO")

        if not target_dir or not os.path.exists(target_dir):
            self.log(f"LỖI: Thư mục target không tồn tại: {target_dir}", "ERROR")
            messagebox.showerror("Lỗi", "Thư mục đích không tồn tại!")
            return

        # Check required files (Không còn các file IAP)
        req_files = [
            "Activity.csv", "ActivityCollectionGroup.csv", "ActivityCollectionReward.csv",
            "TaskActivity.csv", "TaskInfo.csv", "AllyGachaBranch.csv", "AllyGachaType.csv",
            "AdsBanner.csv", "AdsPopUp.csv", "Item.csv", "ItemExpiration.csv",
            "Jump.csv", "JumpSource.csv", "Shop.csv", "ShopItem.csv", "RuleDesc.csv"
        ]

        missing = []
        for fn in req_files:
            p = os.path.join(target_dir, fn)
            if not os.path.exists(p):
                missing.append(fn)

        if missing:
            self.log(f"CẢNH BÁO: Thiếu các file sau trong target_dir: {missing}", "WARN")
        else:
            self.log("Kiểm tra thư mục: Toàn bộ 16 file CSV đích đều tồn tại đầy đủ!", "SUCCESS")

        # Check template 8019 in ActivityCollectionReward.csv
        col_path = os.path.join(target_dir, "ActivityCollectionReward.csv")
        if os.path.exists(col_path):
            rows = read_csv(col_path)
            t_rows = [r for r in rows if r and r[0].strip() == "8019"]
            self.log(f"ActivityCollectionReward.csv: Tìm thấy {len(t_rows)} dòng mẫu của event gốc 8019.")

        variant_mode = is_variant_event(cfg)
        if variant_mode and not cfg.get("event_name", "").strip():
            self.log("LỖI: Event biến thể cần có Event Theme Name.", "ERROR")
            messagebox.showerror("Lỗi", "Event biến thể cần có Event Theme Name.")
            return
        self.log(f"Chế độ Event: {'Event biến thể: ' + cfg['event_name'] if variant_mode else 'Event gốc (dùng lại text có sẵn)'}", "INFO")
        self.log(f"Số lượng Tướng cấu hình trong Shop: {len(self.shop_characters)} tướng.", "INFO")
        self.log("Kiểm tra hoàn tất! Bạn có thể bấm nút THỰC THI để sinh dữ liệu an toàn.", "SUCCESS")

    # --------------------------------------------------------------------------
    # Execution (Generate All)
    # --------------------------------------------------------------------------
    def run_generation(self):
        cfg = self.collect_config()
        target_dir = cfg["target_dir"]

        if cfg["event_variant"] and not cfg["event_name"]:
            messagebox.showerror("Lỗi", "Event biến thể cần có Event Theme Name.")
            return

        if not target_dir or not os.path.exists(target_dir):
            messagebox.showerror("Lỗi", "Vui lòng chọn Thư mục đích hợp lệ trước khi thực thi!")
            return

        confirm = messagebox.askyesno(
            "Xác nhận Thực thi",
            f"Bạn có chắc muốn sinh cấu hình Standalone Event cho Activity ID: {cfg['activity_id']} (Season {cfg['season']})?\n\n"
            "Dữ liệu sẽ được ghi nối tiếp an toàn vào dòng cuối cùng các file CSV (Append mode, chống dính dòng, không ghi đè)."
        )
        if not confirm:
            return

        self.save_current_config()

        self.log("=" * 60)
        self.log(f"BẮT ĐẦU SINH CẤU HÌNH STANDALONE EVENT (ID: {cfg['activity_id']})...", "INFO")

        grand_total = 0
        try:
            # 1. Activity & Group (15 & 13 cols)
            if cfg["gen_activity"]:
                grand_total += generate_activity_files(target_dir, cfg, self.log)

            # 2. Milestones (60 mốc)
            if cfg["gen_collection_reward"]:
                grand_total += generate_collection_rewards(target_dir, cfg, self.log)

            # 3. Tasks (12 tasks, 24 cols)
            if cfg["gen_tasks"]:
                grand_total += generate_tasks(target_dir, cfg, cfg["task_rewards"], self.log)

            # 4. Gacha & Banners (14 / 39 / 27 cols)
            if cfg["gen_gacha_banner"]:
                gacha_rwds = {
                    "legendary": cfg["gacha_leg_reward_id"],
                    "epic": cfg["gacha_epic_reward_id"],
                    "elite": cfg["gacha_elite_reward_id"],
                    "rare": cfg["gacha_rare_reward_id"]
                }
                grand_total += generate_gacha_and_banners(target_dir, cfg, gacha_rwds, self.log)

            # 5. Items & Jumps (26 & 13 cols)
            if cfg["gen_items_jumps"]:
                grand_total += generate_items_and_jumps(target_dir, cfg, self.log)

            # 6. Shop & ShopItems (28 cols chuẩn Col 13 BeforeItemID)
            if cfg["gen_shop"]:
                grand_total += generate_shop(target_dir, cfg, self.log)

            # 7. Language (Chỉ sinh nếu là Special Edition)
            if cfg["gen_language"]:
                grand_total += generate_language_files(target_dir, cfg, self.log)

            self.log("=" * 60)
            self.log(f"THỰC THI HOÀN TẤT THÀNH CÔNG! Tổng cộng {grand_total} dòng đã được ghi thêm an toàn.", "SUCCESS")
            messagebox.showinfo("Thành công", f"Đã sinh cấu hình sự kiện Standalone thành công!\nTổng cộng {grand_total} dòng đã được thêm mới an toàn.")

        except Exception as e:
            self.log(f"LỖI NGOẠI LỆ: {str(e)}", "ERROR")
            messagebox.showerror("Lỗi thực thi", f"Đã xảy ra lỗi trong quá trình sinh dữ liệu:\n{str(e)}")


# ==============================================================================
# 7. MAIN RUNNER (HỖ TRỢ CẢ CLI LẪN GUI)
# ==============================================================================

def main():
    if "--cli" in sys.argv:
        print("Running in CLI mode...")
        cfg = load_config()
        target_dir = cfg["target_dir"]

        def console_log(msg, tag="INFO"):
            print(f"[{tag}] {msg}")

        print("Executing Standalone Event generation...")
        generate_activity_files(target_dir, cfg, console_log)
        generate_collection_rewards(target_dir, cfg, console_log)
        generate_tasks(target_dir, cfg, cfg["task_rewards"], console_log)
        gacha_rwds = {
            "legendary": cfg["gacha_leg_reward_id"],
            "epic": cfg["gacha_epic_reward_id"],
            "elite": cfg["gacha_elite_reward_id"],
            "rare": cfg["gacha_rare_reward_id"]
        }
        generate_gacha_and_banners(target_dir, cfg, gacha_rwds, console_log)
        generate_items_and_jumps(target_dir, cfg, console_log)
        generate_shop(target_dir, cfg, console_log)
        generate_language_files(target_dir, cfg, console_log)
        print("Done!")
    else:
        if tk is None:
            print("Lỗi: Tkinter không khả dụng trên môi trường này!")
            sys.exit(1)
        root = tk.Tk()
        app = StandaloneEventToolApp(root)
        root.mainloop()


if __name__ == "__main__":
    main()


