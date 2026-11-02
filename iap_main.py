import os
import csv
import re
import sys
import json
import stat
from decimal import Decimal, InvalidOperation
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ==========================================
# CẤU HÌNH PATH & LƯU TRỮ TỰ ĐỘNG
# ==========================================
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(SCRIPT_DIR, "iap_config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

# ==========================================
# HÀM BỔ TRỢ UI: FIX LỖI GHI ĐÈ ĐƯỜNG DẪN
# ==========================================
def chon_thu_muc(entry):
    path = filedialog.askdirectory()
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)

def chon_file(entry):
    path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)

# ==========================================
# HÀM XỬ LÝ FILE (CHỐNG READ-ONLY, SAI FORMAT & XUỐNG DÒNG)
# ==========================================
def unlock_file(filepath):
    if os.path.exists(filepath):
        os.chmod(filepath, stat.S_IWRITE)

def read_csv(filepath):
    if not os.path.exists(filepath): return []
    try:
        with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
            return list(csv.reader(f))
    except:
        return []

def format_csv_row(row, quote_all=False):
    output = csv.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL if quote_all else csv.QUOTE_MINIMAL)
    writer.writerow([str(cell) for cell in row])
    return output.getvalue().rstrip('\r\n')


def write_csv(filepath, rows, quote_all=False):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    unlock_file(filepath)
    if rows:
        max_len = max(len(row) for row in rows)
        rows = [row + [""] * (max_len - len(row)) if len(row) < max_len else row for row in rows]
    with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
        for row in rows:
            f.write(format_csv_row(row, quote_all=quote_all) + '\r\n')


def append_csv(filepath, rows, quote_all=False):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    unlock_file(filepath)
    if os.path.exists(filepath):
        with open(filepath, 'rb+') as f:
            f.seek(0, os.SEEK_END)
            if f.tell() > 0:
                f.seek(-1, os.SEEK_END)
                last_char = f.read(1)
                if last_char not in [b'\n', b'\r']:
                    f.write(b'\r\n')

    existing_rows = read_csv(filepath)
    if not existing_rows:
        write_csv(filepath, rows, quote_all=quote_all)
        return

    existing_keys = set()
    for row in existing_rows:
        if row:
            key = f"{row[0]}_{row[1]}" if len(row) > 1 else str(row[0])
            existing_keys.add(key)
            
    new_rows_to_append = []
    for new_row in rows:
        if new_row:
            key = f"{new_row[0]}_{new_row[1]}" if len(new_row) > 1 else str(new_row[0])
            if key not in existing_keys:
                new_rows_to_append.append(new_row)
                existing_keys.add(key)
                
    if new_rows_to_append:
        with open(filepath, 'a', encoding='utf-8-sig', newline='') as f:
            for row in new_rows_to_append:
                f.write(format_csv_row(row, quote_all=quote_all) + '\r\n')


def write_text_csv(filepath, rows, quote_all=False):
    write_csv(filepath, rows, quote_all=quote_all)


def append_text_csv(filepath, rows, quote_all=False):
    append_csv(filepath, rows, quote_all=quote_all)


def convert_date(d_str):
    if not d_str: return ""
    try:
        if "/" in d_str:
            parts = d_str.split('/')
            if len(parts) == 3:
                m, d, y = parts
                return f"{y}{int(m):02d}{int(d):02d}_000000"
    except: pass
    return d_str

def get_val(r, col, header):
    if col in header:
        idx = header.index(col)
        if idx < len(r): return str(r[idx]).strip()
    return ""


def normalize_int_string(value):
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    text = re.sub(r"[\s,]+", "", text)
    try:
        return str(int(float(text)))
    except:
        return text


def is_false_value(val):
    if not val:
        return True
    v = str(val).strip().lower()
    return v == "false" or v in {"#n/a", "n/a", "na", "none"}

def looks_like_pack_data(r, header):
    price = get_val(r, "Price", header)
    if price and not is_false_value(price):
        return True
    for i in range(1, 10):
        item_id = get_val(r, f"Item {i} ID", header)
        if item_id and not is_false_value(item_id):
            return True
    return False

def normalize_for_func_key(text):
    """Convert text to CamelCase for Func_... keys. E.g., 'Step up' -> 'StepUp'"""
    words = text.replace("-", " ").replace("_", " ").split()
    return "".join(w[0].upper() + w[1:] for w in words if w)

def normalize_for_ui_key(text):
    """Convert text to lowercase with underscores for UI text keys."""
    if not text:
        return ""
    slug = str(text).strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")


def get_legendary_daily_shop_icon(category, pack_index, character_id, character_class):
    """Return the LocalKey2 icon used by Legendary Event daily Token/Badge shops.

    The source sheet already contains one row per pack per day.  Icons therefore
    repeat by the pack position within each shop: six packs for Token Shop and
    four packs for Badge Shop.
    """
    category_key = (category or "").strip().lower()
    if "token shop" in category_key:
        token_icons = ("1A", "1A", "1B", "1B", "1C", "1C")
        return f"ui_store_EventCoinToken_{token_icons[(pack_index - 1) % len(token_icons)]}_{character_id}"
    if "badge shop" in category_key:
        badge_icons = ("1", f"2{character_class}", f"3{character_class}", f"4{character_class}")
        return f"ui_store_EventBadge_{badge_icons[(pack_index - 1) % len(badge_icons)]}"
    return ""


def get_holiday_pack_icon_name(banner_suffix, event_name, cat_name, pack_name, pack_id):
    # 1. Clean event name (remove "deal" and trailing suffixes like _01, _02, etc.)
    event_clean = re.sub(r'deal(_\d+)?$', '', banner_suffix or event_name, flags=re.IGNORECASE)
    event_clean = re.sub(r'[^A-Za-z0-9]+', '', event_clean)

    # 2. Map category type
    cat_lower = cat_name.lower()
    if "step" in cat_lower or "daily" in cat_lower:
        cat_type = "daily"
    else:
        cat_type = "special"

    # 3. Clean pack name
    name = pack_name.replace(event_name, "")
    name = re.sub(r'^.*?\-\s*', '', name)
    name = name.strip()
    # Ensure "Fragment", "Fragments", "Free", "Character/s", and Roman numerals (I, II, etc.) are separated by an underscore
    name = re.sub(r'(?<!^)(?<!_)\b(free|fragments?|characters?|i|ii|iii|iv|v|vi|vii|viii|ix|x)\b', r'_\1', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*[\+\-]\s*', '_', name)

    parts = []
    for part in name.split('_'):
        words_in_part = [w.strip() for w in part.split() if w.strip()]
        if words_in_part:
            parts.append("".join(words_in_part))
    pack_name_clean = "_".join(parts)

    if not pack_name_clean:
        pack_name_clean = str(pack_id)

    return f"ui_store_{event_clean}_{cat_type}_{pack_name_clean}"


def get_substore_open_level(packs, default="530"):
    """Return the lowest valid OpenLvl used by packs in a substore."""
    open_levels = []
    for pack in packs:
        raw_level = normalize_int_string(pack.get("OpenLvl", ""))
        try:
            open_levels.append((int(raw_level), raw_level))
        except (TypeError, ValueError):
            continue
    return min(open_levels, key=lambda item: item[0])[1] if open_levels else default


def build_text_key(*parts):
    pieces = []
    for part in parts:
        if not part:
            continue
        slug = re.sub(r"[^A-Za-z0-9]+", "", str(part))
        if slug:
            pieces.append(slug)
    return "".join(pieces)


def is_step_up_type(value):
    return bool(re.search(r"\bstep\s*-?\s*up\b", str(value or "").lower()))


def build_substore_text_keys(event_name, banner_suffix, sub_type, index=1):
    event_id = normalize_for_func_key(banner_suffix or event_name)
    sub_id = normalize_for_func_key(sub_type)
    suffix = f"_{index}" if index > 1 else ""
    pack_key_base = f"{event_id}_{sub_id}_Pack{suffix}"
    func_key_base = f"Func_{event_id}_{sub_id}{suffix}"
    desc_key = f"StoreDesc_{event_id}_{sub_id}{suffix}"
    return {
        "sub_key": func_key_base,
        "pack_key_base": pack_key_base,
        "pack_key": pack_key_base,
        "desc_key": desc_key,
        "func_key_base": func_key_base,
        "type": sub_type,
        "index": index,
    }


def build_popup_text_keys(event_name, banner_suffix, is_extra_sale=False, extra_sale_type="Extra Deal"):
    if is_extra_sale:
        if extra_sale_type == "Extra Step-up":
            return {
                "title_key": "Popup_ExtradealsStepup_Title",
                "subtitle_key": "Popup_ExtradealsStepup_Subtitle",
                "desc_key": "Popup_ExtradealsStepup_Desc",
                "text_key": "Popup_ExtradealsStepup_Subtitle",
                "text_key_2": "Popup_ExtradealsStepup_Desc",
            }
        else:
            return {
                "title_key": "FlashSale_Popup_Title",
                "subtitle_key": "FlashSale_Popup_Subtitle",
                "desc_key": "FlashSale_Popup_Description",
                "text_key": "FlashSale_Popup_Subtitle",
                "text_key_2": "FlashSale_Popup_Description",
            }
    event_id = normalize_for_func_key(banner_suffix or event_name)
    return {
        "title_key": f"Popup_{event_id}_Title",
        "subtitle_key": f"Popup_{event_id}_Subtitle",
        "desc_key": f"Popup_{event_id}_Desc",
        "text_key": f"Popup_{event_id}_Subtitle",
        "text_key_2": f"Popup_{event_id}_Desc",
    }


def generate_stepup_variants(text, step_count):
    if not text:
        return []
    match = re.search(r"\b1\s*/\s*(\d+)\b", text)
    if match and step_count:
        total_steps = int(match.group(1))
        if step_count != total_steps:
            total_steps = max(step_count, total_steps)
        variants = []
        for step in range(1, step_count + 1):
            variants.append(re.sub(r"\b1\s*/\s*\d+\b", f"{step}/{total_steps}", text, count=1))
        return variants
    if step_count and step_count > 1:
        return [text] * step_count
    return [text]


def export_text_assets(target_dir, event_name="", banner_suffix="", popup_title="", popup_subtitle="", popup_desc="", main_store_text="", substores=None, substore_pack_counts=None, is_extra_sale=False):
    if not target_dir:
        return
    os.makedirs(target_dir, exist_ok=True)

    shop_rows = [["Key", "Module", "Explanation", "en"]]
    activity_rows = [["Key", "Module", "Explanation", "en"]]

    if main_store_text:
        main_key = f"Func_{normalize_for_func_key(banner_suffix or event_name)}"
        shop_rows.append([main_key, "IAP Main Store", event_name or "IAP", main_store_text])

    substore_entries = substores or []
    type_counts = {}
    for idx, sub in enumerate(substore_entries, start=1):
        sub_type = (sub.get("type") or "Daily").strip() or "Daily"
        pack_name = (sub.get("pack_name") or "").strip()
        sub_name = (sub.get("substore_name") or "").strip()
        sub_desc = (sub.get("substore_desc") or "").strip()
        if not any([pack_name, sub_name, sub_desc]):
            continue

        type_counts[sub_type] = type_counts.get(sub_type, 0) + 1
        type_idx = type_counts[sub_type]
        text_keys = build_substore_text_keys(event_name, banner_suffix, sub_type, type_idx)
        pack_count = 1
        if is_step_up_type(sub_type):
            if substore_pack_counts and idx - 1 < len(substore_pack_counts):
                pack_count = substore_pack_counts[idx - 1]
            elif "1/" in pack_name:
                m = re.search(r"\b1\s*/\s*(\d+)\b", pack_name)
                pack_count = int(m.group(1)) if m else 1

        if is_step_up_type(sub_type):
            pack_texts = generate_stepup_variants(pack_name, pack_count)
            for step_idx, text in enumerate(pack_texts, start=1):
                shop_rows.append([f"{text_keys['pack_key_base']}_{step_idx}", "IAP Pack Name", event_name or "IAP", text])
        elif pack_name:
            shop_rows.append([text_keys["pack_key"], "IAP Pack Name", event_name or "IAP", pack_name])

        if sub_name:
            shop_rows.append([text_keys["sub_key"], "IAP Substore Name", event_name or "IAP", sub_name])
        if sub_desc:
            shop_rows.append([text_keys["desc_key"], "IAP Substore Desc", event_name or "IAP", sub_desc])

    if not is_extra_sale and (popup_title or popup_subtitle or popup_desc):
        popup_keys = build_popup_text_keys(event_name, banner_suffix)
        if popup_title:
            activity_rows.append([popup_keys["title_key"], "Pop Up Text", event_name or "IAP", popup_title, ""])
        if popup_subtitle:
            activity_rows.append([popup_keys["subtitle_key"], "Pop Up Text", event_name or "IAP", popup_subtitle, ""])
        if popup_desc:
            activity_rows.append([popup_keys["desc_key"], "Pop Up Text", event_name or "IAP", popup_desc, ""])

    shop_path = os.path.join(target_dir, "Language", "SourceShopUI.csv")
    activity_path = os.path.join(target_dir, "Language", "SourceActivityUI.csv")
    lang_dir = os.path.dirname(shop_path)
    os.makedirs(lang_dir, exist_ok=True)

    if os.path.exists(shop_path):
        if len(shop_rows) > 1:
            append_csv(shop_path, shop_rows[1:])
    else:
        write_csv(shop_path, shop_rows)

    if os.path.exists(activity_path):
        if len(activity_rows) > 1:
            append_text_csv(activity_path, activity_rows[1:])
    else:
        write_text_csv(activity_path, activity_rows)

# ==========================================
# CORE LOGIC: IAP PACKS
# ==========================================
def process_iap_csv(csv_path):
    filter_keyword = entry_csv_filter.get().strip().lower()
    selected_event = entry_event_name.get().strip().lower()
    # Extract root prefix of selected_event (before first '(' or '-') to detect sibling sections
    event_root = re.split(r'[\(\-]', selected_event)[0].strip() if selected_event else ""

    if not filter_keyword and not selected_event:
        raise Exception("Vui lòng nhập 'Từ khóa lọc Pack' hoặc 'Event/Sale Name'!")

    rows = read_csv(csv_path)
    header_idx = -1
    for i, r in enumerate(rows):
        if "Pack Name" in r and "Pack ID" in r:
            header_idx = i; break
            
    if header_idx == -1: raise Exception("Không tìm thấy dòng Header chuẩn!")
    
    header = rows[header_idx]
    data_rows = rows[header_idx+1:]

    # Detect the actual OpenLvl column name (handles "OpenLvl", "Open Level", "Open level", etc.)
    open_lvl_col = "OpenLvl"
    for h in header:
        h_clean = re.sub(r"[\s_]+", "", str(h)).lower()
        if h_clean == "openlvl":
            open_lvl_col = h
            break

    # First pass: collect raw rows and detect categories without assigning generated IDs
    raw_entries = []
    existing_sub_ids = set()
    existing_pack_ids = set()
    current_event = ""
    current_category = ""

    for r in data_rows:
        # An entirely empty CSV row is an explicit boundary between sections.
        # Clear the inherited event/category so following headers cannot be
        # accidentally treated as subsections of the previously selected event.
        if not any(str(cell).strip() for cell in r):
            current_event = None
            current_category = ""
            continue

        pack_id_raw = get_val(r, "Pack ID", header)

        # category/section row
        if is_false_value(pack_id_raw) and not looks_like_pack_data(r, header):
            cat_text = get_val(r, "Pack Name", header)
            if not cat_text and len(r) > 0:
                cat_text = str(r[0]).strip()
            if cat_text and len(cat_text) > 3:
                clean_cat = re.sub(r'^[-=\s]+|[-=\s]+$', '', cat_text).strip()
                if clean_cat:
                    if selected_event:
                        clean_cat_lower = clean_cat.lower()
                        if selected_event in clean_cat_lower:
                            current_event = clean_cat
                            current_category = ""
                        elif event_root and clean_cat.lower().startswith(event_root):
                            # Sibling section sharing same root prefix (e.g. "Extra deals - Step up (July 21)")
                            # but not matching selected event -> reset so its packs are excluded
                            current_event = None
                            current_category = ""
                        elif current_event:
                            current_category = clean_cat
                        else:
                            current_category = ""
                    else:
                        if any(token in clean_cat.lower() for token in ["season", "event", "sale", "holiday", "rerun"]):
                            current_event = clean_cat
                            current_category = ""
                        elif not current_event:
                            current_event = clean_cat
                            current_category = ""
                        else:
                            current_category = clean_cat
            continue

        # collect raw pack info
        pack_name = get_val(r, "Pack Name", header)
        items = []
        for i in range(1, 10):
            i_id = get_val(r, f"Item {i} ID", header)
            i_qty = get_val(r, f"Item {i} Qty", header)
            if i_id and i_qty:
                i_qty = normalize_int_string(i_qty)
                items.append((i_id, i_qty))
        sku = get_val(r, "SKU ID", header)
        price = get_val(r, "Price", header)
        if not sku:
            p_map = {"4.99":"motherbox5", "9.99":"motherbox10", "19.99":"motherbox20", "49.99":"motherbox50", "99.99":"motherbox100"}
            sku = p_map.get(price, "")

        raw_pack_id = None
        if pack_id_raw and not is_false_value(pack_id_raw):
            try:
                raw_pack_id = str(int(float(pack_id_raw)))
                existing_pack_ids.add(raw_pack_id)
                existing_sub_ids.add(raw_pack_id[:4])
            except:
                raw_pack_id = pack_id_raw

        if selected_event and not current_event:
            continue

        raw_entries.append({
            "RawPackID": raw_pack_id,
            "PackName": pack_name,
            "Items": items,
            "SkuID": sku,
            "Price": price,
            "Start": get_val(r, "Start Date (UTC)", header),
            "End": get_val(r, "End Date (UTC)", header),
            "Order": get_val(r, "Order", header),
            "Limit": get_val(r, "Limit", header),
            "BuyPrePack": get_val(r, "BuyPrePack", header),
            "OpenLvl": get_val(r, open_lvl_col, header),
            "LabelID": get_val(r, "Label ID", header),
            "Event": current_event,
            "Category": current_category or current_event
        })

    # Build category -> existing sub id map from raw entries that have IDs
    category_existing_sub = {}
    for e in raw_entries:
        if e["RawPackID"]:
            sid = e["RawPackID"][0:4]
            if e["Category"] not in category_existing_sub:
                category_existing_sub[e["Category"]] = sid

    # prepare generators, initialize counters to avoid collisions with existing packs
    generated_sub_ids = {}
    generated_sub_counters = {}
    next_generated_sub_id = 9000

    def get_generated_pack_id(category):
        nonlocal next_generated_sub_id
        # if this category already has an existing sub id, reuse it
        if category in category_existing_sub:
            sub_id = category_existing_sub[category]
            if category not in generated_sub_ids:
                generated_sub_ids[category] = sub_id
                # compute starting counter to be after existing packs of this sub_id
                max_counter = 0
                for pid in existing_pack_ids:
                    if pid.startswith(sub_id):
                        try:
                            c = int(pid[4:])
                            if c > max_counter: max_counter = c
                        except: pass
                generated_sub_counters[category] = max_counter
        else:
            if category not in generated_sub_ids:
                while str(next_generated_sub_id) in existing_sub_ids or str(next_generated_sub_id) in generated_sub_ids.values():
                    next_generated_sub_id += 1
                generated_sub_ids[category] = str(next_generated_sub_id)
                generated_sub_counters[category] = 0
                next_generated_sub_id += 1

        generated_sub_counters[category] += 1
        counter = generated_sub_counters[category]
        sub_id = generated_sub_ids[category]
        while f"{sub_id}{counter:03d}" in existing_pack_ids:
            counter += 1
        generated_sub_counters[category] = counter
        return f"{sub_id}{counter:03d}"

    # Finalize parsed list using raw_entries and generator
    parsed = []
    for e in raw_entries:
        if e["RawPackID"]:
            pack_id = e["RawPackID"]
        else:
            pack_id = get_generated_pack_id(e["Category"])

        if not e["PackName"]: continue
        if filter_keyword and filter_keyword not in e["PackName"].lower(): continue
        if selected_event:
            if e["Event"]:
                if selected_event not in e["Event"].lower():
                    continue
            else:
                if selected_event not in e["Category"].lower():
                    continue

        try: pack_id = str(int(float(pack_id)))
        except: pass
        sub_id = pack_id[:4]

        parsed.append({
            "SubStoreID": sub_id, "PackID": pack_id, "PackName": e["PackName"],
            "Start": e["Start"], "End": e["End"],
            "Order": e["Order"], "Limit": e["Limit"], "Price": e["Price"],
            "BuyPrePack": e["BuyPrePack"], "OpenLvl": e["OpenLvl"],
            "LabelID": e["LabelID"], "SkuID": e["SkuID"], "Items": e["Items"],
            "Category": e["Category"]
        })

    return parsed

def price_to_cents(value):
    text = str(value or "").strip().replace("$", "").replace(",", "")
    if text.lower() in {"", "free"}:
        return 0
    try:
        return int(Decimal(text) * 100)
    except (InvalidOperation, ValueError):
        return None


def validate_and_replace_pack_skus(packs, target_dir):
    if packs and all(price_to_cents(pack.get("Price")) == 0 for pack in packs):
        return []

    sku_path = os.path.join(target_dir, "RechargeSKU.csv")
    sku_rows = read_csv(sku_path)
    if not sku_rows:
        raise Exception(f"Không tìm thấy hoặc không đọc được file {sku_path}!")

    available_skus = []
    for row in sku_rows[1:]:
        if len(row) < 2:
            continue
        sku_id = str(row[0]).strip()
        sku_price = price_to_cents(row[1])
        if sku_id and sku_price is not None:
            available_skus.append((sku_id, sku_price))

    valid_sku_ids = {sku_id for sku_id, _ in available_skus}
    replacements = []
    for pack in packs:
        pack_price = price_to_cents(pack.get("Price"))
        if pack_price == 0:
            continue

        requested_sku = str(pack.get("SkuID") or "").strip()
        if requested_sku in valid_sku_ids:
            continue

        if pack_price is None:
            raise Exception(f"Không xác định được giá của pack '{pack['PackName']}' để thay SKU '{requested_sku}'.")

        candidates = [sku_id for sku_id, sku_price in available_skus if sku_price == pack_price]
        if not candidates:
            raise Exception(
                f"SKU '{requested_sku or '(trống)'}' của pack '{pack['PackName']}' không tồn tại trong RechargeSKU.csv "
                f"và không có SKU nào cùng giá {pack.get('Price', '')}."
            )

        requested_suffix = re.search(r"(\d+)$", requested_sku)
        if requested_suffix:
            suffix = requested_suffix.group(1)
            requested_family = re.sub(r"\d+$", "", requested_sku).lower()
            fallback_family = {"motherbox": "progress", "progress": "motherbox"}.get(requested_family)
            preferred_family = [
                sku_id for sku_id in candidates
                if fallback_family and sku_id.lower() == f"{fallback_family}{suffix}"
            ]
            matching_suffix = [sku_id for sku_id in candidates if sku_id.endswith(suffix)]
            if preferred_family:
                candidates = preferred_family
            elif matching_suffix:
                candidates = matching_suffix

        replacement_sku = candidates[0]
        pack["SkuID"] = replacement_sku
        replacements.append({
            "PackID": pack.get("PackID", ""),
            "PackName": pack.get("PackName", ""),
            "Price": pack.get("Price", ""),
            "OldSkuID": requested_sku,
            "NewSkuID": replacement_sku,
        })

    return replacements


def collect_text_config(is_holiday=False):
    # Text generation is intentionally limited to Mode 2 (Holiday Sales).
    if not is_holiday:
        return None

    substores = []
    # Always collect substores configuration to ensure key generation logic is unified
    for widget in substore_text_widgets:
        sub_type = widget["type_var"].get().strip() or "Daily"
        pack_name = widget["pack_var"].get().strip()
        sub_name = widget["sub_var"].get().strip()
        sub_desc = widget["desc_var"].get().strip()
        if any([pack_name, sub_name, sub_desc]):
            substores.append({
                "type": sub_type,
                "pack_name": pack_name,
                "substore_name": sub_name,
                "substore_desc": sub_desc,
            })
    main_store_text = entry_main_store_text.get().strip() if entry_main_store_text else ""

    return {
        "enabled": bool(var_generate_text and var_generate_text.get()),
        "event_name": entry_event_name.get().strip(),
        "banner_suffix": entry_banner_suffix.get().strip(),
        "popup_title": entry_popup_title.get().strip() if entry_popup_title else "",
        "popup_subtitle": entry_popup_subtitle.get().strip() if entry_popup_subtitle else "",
        "popup_desc": entry_popup_desc.get().strip() if entry_popup_desc else "",
        "main_store_text": main_store_text,
        "substores": substores,
    }


def process_pack(target_dir, is_holiday, is_extra_sale=False, extra_sale_type="Extra Deal"):
    parsed = process_iap_csv(entry_csv.get())
    if not parsed:
        raise Exception("Không tìm thấy dữ liệu! Kiểm tra lại file CSV, 'Từ khóa lọc' và 'Event/Sale Name'.")
    sku_adjustments = validate_and_replace_pack_skus(parsed, target_dir)
    event_name = entry_event_name.get()
    
    if is_holiday:
        banner_suffix = event_name.replace(" ", "")
        sale_type = "Holiday"
    else:
        banner_suffix = entry_banner_suffix.get().strip() if entry_banner_suffix else "" 
        sale_type = combo_sale_type.get() if combo_sale_type else "Legendary Event"

    is_legendary_character_pack = (
        not is_holiday
        and not is_extra_sale
        and sale_type == "Legendary Event"
    )
    character_id = banner_suffix if is_legendary_character_pack else ""
    character_class = var_character_class.get().strip() if is_legendary_character_pack else ""

    text_config = collect_text_config(is_holiday=is_holiday)
    if text_config and text_config.get("enabled"):
        export_text_assets(
            target_dir,
            event_name=event_name,
            banner_suffix=banner_suffix,
            popup_title=text_config["popup_title"],
            popup_subtitle=text_config["popup_subtitle"],
            popup_desc=text_config["popup_desc"],
            main_store_text=text_config["main_store_text"],
            substores=text_config["substores"],
            is_extra_sale=is_extra_sale,
        )
    
    grouped = {}
    category_map = {}
    for p in parsed:
        sid = p['SubStoreID']
        if sid not in grouped: 
            grouped[sid] = []
            category_map[sid] = p['Category']
        grouped[sid].append(p)
    
    sub_ids = list(grouped.keys())
    
    # 1. PAYSTORE MAIN
    main_path = os.path.join(target_dir, "PayStoreMain.csv")
    main_rows = read_csv(main_path)
    if len(main_rows) >= 3:
        h1, h2 = main_rows[0], main_rows[1]
        target_idx = -1
        
        if is_extra_sale:
            # Đối với Extra Sale (Extra Deal / Extra Step-up): KHÔNG tạo mainstore mới, ghi vào substore/row có sẵn
            target_name = "Extra Deals - Step up" if extra_sale_type == "Extra Step-up" else "Flash Sale"
            for i, r in enumerate(main_rows):
                if len(r) > 1 and target_name.lower() in str(r[1]).strip().lower():
                    target_idx = i; break
                    
            if target_idx == -1:
                # Tìm tương đối nếu không khớp chính xác
                for i, r in enumerate(main_rows):
                    if len(r) > 1:
                        c_name = str(r[1]).strip().lower()
                        if extra_sale_type == "Extra Step-up" and "step up" in c_name:
                            target_idx = i; break
                        elif extra_sale_type != "Extra Step-up" and "flash" in c_name:
                            target_idx = i; break
                            
            if target_idx != -1:
                row = main_rows[target_idx]
                current_ids_in_row = [str(x).strip() for x in row]
                ids_to_add = [sid for sid in sub_ids if sid not in current_ids_in_row]
                
                if ids_to_add:
                    empty_slots = [i for i in range(8, len(row)) if not str(row[i]).strip()]
                    while len(empty_slots) < len(ids_to_add):
                        new_idx = len(h1) - 8
                        h1.append("SubStore")
                        h2.append(f"SubStore{new_idx}")
                        for r_idx, r_val in enumerate(main_rows):
                            if r_idx == 2: r_val.append("int")
                            elif r_idx > 2: r_val.append("")
                        empty_slots.append(len(h1) - 1)
                    for i, sid in enumerate(ids_to_add): 
                        row[empty_slots[i]] = sid
            else:
                raise Exception(f"Không tìm thấy dòng '{target_name}' trong PayStoreMain.csv!")
        elif is_holiday:
            for i, r in enumerate(main_rows):
                if len(r) > 1 and "Limited Time Event Store" in str(r[1]):
                    target_idx = i; break
            if target_idx != -1:
                if any(len(r) > 1 and str(r[1]).strip().lower() == event_name.strip().lower() and i >= 3 for i, r in enumerate(main_rows)):
                    pass
                else:
                    take_id = main_rows[target_idx][0]
                    template = main_rows[target_idx - 1] if target_idx - 1 >= 3 else main_rows[target_idx]
                    open_style = template[2] if len(template) > 2 else "2"
                    open_param = template[3] if len(template) > 3 else "530"
                    func_str = f"Func_{normalize_for_func_key(banner_suffix or event_name)}"
                    func_param = template[5] if len(template) > 5 else "9400"
                    need_show = template[6] if len(template) > 6 else ""
                    priority = template[7] if len(template) > 7 else "3"
                    new_row = [take_id, event_name, open_style, open_param, func_str, func_param, need_show, priority] + sub_ids
                    while len(new_row) < len(h1): new_row.append("")
                    for i in range(target_idx, len(main_rows)):
                        if i >= 3 and len(main_rows[i]) > 0 and str(main_rows[i][0]).isdigit():
                            main_rows[i][0] = str(int(main_rows[i][0]) + 1)
                    main_rows.insert(target_idx, new_row)
        else:
            for i, r in enumerate(main_rows):
                if len(r) > 1 and "Limited Time Event Store" in str(r[1]):
                    target_idx = i; break
            if target_idx != -1:
                row = main_rows[target_idx]
                if text_config and text_config["main_store_text"]:
                    row[4] = f"Func_{normalize_for_func_key(banner_suffix or event_name)}"
                current_ids_in_row = [str(x).strip() for x in row]
                ids_to_add = [sid for sid in sub_ids if sid not in current_ids_in_row]
                
                if ids_to_add:
                    empty_slots = [i for i in range(8, len(row)) if not str(row[i]).strip()]
                    while len(empty_slots) < len(ids_to_add):
                        new_idx = len(h1) - 8
                        h1.append("SubStore")
                        h2.append(f"SubStore{new_idx}")
                        for r_idx, r_val in enumerate(main_rows):
                            if r_idx == 2: r_val.append("int")
                            elif r_idx > 2: r_val.append("")
                        empty_slots.append(len(h1) - 1)
                    for i, sid in enumerate(ids_to_add): 
                        row[empty_slots[i]] = sid
                        
        write_csv(main_path, main_rows)

    # Build UI substores keys list, tracking type, index and name
    ui_substore_keys = []
    if text_config and text_config["substores"]:
        type_counts = {}
        for idx, sub in enumerate(text_config["substores"], start=1):
            sub_type = (sub.get("type") or "Daily").strip()
            if sub_type not in ["Daily", "Step-up", "Special"]:
                sub_type = "Daily"
            type_counts[sub_type] = type_counts.get(sub_type, 0) + 1
            type_idx = type_counts[sub_type]
            keys = build_substore_text_keys(event_name, banner_suffix, sub_type, type_idx)
            keys["substore_name"] = sub.get("substore_name", "").strip()
            keys["type"] = sub_type
            keys["ui_index"] = idx
            keys["assigned"] = False
            ui_substore_keys.append(keys)

    # Pre-map each CSV SubStore ID to its corresponding UI text keys based on name matching, falling back to absolute order
    def normalize_name_match(s):
        if not s: return ""
        return re.sub(r'\s+', ' ', str(s).strip().lower())

    sid_to_text_keys = {}
    for sid in sub_ids:
        cat_name = category_map[sid]
        
        text_keys = None
        if ui_substore_keys:
            candidate_configs = [cfg for cfg in ui_substore_keys if not cfg["assigned"]]
            if candidate_configs:
                norm_cat = normalize_name_match(cat_name)
                best_match = None
                
                # 1. Try exact match by substore_name
                for cfg in candidate_configs:
                    if normalize_name_match(cfg["substore_name"]) == norm_cat:
                        best_match = cfg
                        break
                
                # 2. Try partial matching
                if not best_match:
                    for cfg in candidate_configs:
                        norm_sub = normalize_name_match(cfg["substore_name"])
                        if norm_sub and norm_cat and (norm_sub in norm_cat or norm_cat in norm_sub):
                            best_match = cfg
                            break
                
                # 3. Fallback to the first available unassigned config in absolute order
                if not best_match:
                    best_match = candidate_configs[0]
                
                best_match["assigned"] = True
                text_keys = best_match
            else:
                text_keys = ui_substore_keys[-1]
        sid_to_text_keys[sid] = text_keys

    # 2. PAYSTORE SUB
    sub_rows = []
    for idx, sid in enumerate(sub_ids, start=1):
        order = "1" if (is_holiday or is_extra_sale) else "2"
        cat_name = category_map[sid]
        display_name = f"{event_name} {cat_name}".strip() if event_name else cat_name
        if is_extra_sale:
            if extra_sale_type == "Extra Step-up":
                local_key = f"Func_ExtradealsStepup_{normalize_for_func_key(cat_name)}"
            else:
                local_key = "FlashSale_Popup_Title"
        else:
            local_key = f"Func_{normalize_for_func_key(banner_suffix or event_name)}_{normalize_for_func_key(cat_name)}"
            text_keys = sid_to_text_keys.get(sid)
            if text_keys:
                local_key = text_keys["sub_key"]
        open_level = get_substore_open_level(grouped[sid])
        sub_rows.append([sid, display_name, local_key, "2", open_level, order, "2", "RechargePack", "1", ""])
    append_csv(os.path.join(target_dir, "PayStoreSub.csv"), sub_rows)

    # 3. RECHARGE PACK RULES, PACKS & REWARDS
    rules_rows, pack_rows, reward_rows = [], [], []
    for sid, packs in grouped.items():
        start, end = convert_date(packs[0]['Start']), convert_date(packs[-1]['End'])
        if is_holiday:
            banner = f"ui_recharge_banner_{banner_suffix}"
            t_pic = f"ui_recharg_img_timetxtbg01_{banner_suffix}_01"
            t_back = f"ui_recharg_img_timetxtbg02_{banner_suffix}_01"
            backpack_suffix = re.sub(r'(_\d+)?$', '', banner_suffix)
            b_pic = f"ui_recharge_packback_{backpack_suffix}"
        else:
            banner = f"ui_recharge_banner_{banner_suffix}"
            t_pic, t_back = f"ui_recharg_img_timetxtbg01_{banner_suffix}", f"ui_recharg_img_timetxtbg02_{banner_suffix}"
            b_pic = f"ui_recharge_packback_{banner_suffix}"
        cat_name = category_map[sid]
        display_name = f"{event_name} {cat_name}".strip() if event_name else cat_name
        cat_only = cat_name.replace(event_name, "").strip() or cat_name
        
        if is_extra_sale:
            if extra_sale_type == "Extra Step-up":
                local_key_des = "StoreDesc_ExtradealsStepup"
            else:
                local_key_des = "FlashSale_Popup_Title"
        else:
            if is_holiday:
                local_key_des = f"StoreDesc_{normalize_for_func_key(banner_suffix or event_name)}_{normalize_for_func_key(cat_name)}"
            else:
                local_key_des = f"StoreDesc_{normalize_for_func_key(event_name)}"
            text_keys = sid_to_text_keys.get(sid)
            if text_keys:
                local_key_des = text_keys["desc_key"]
        
        is_step_up_group = is_step_up_type(cat_name)
        
        # ĐÃ SỬA: Đủ 6 số 1 trong các flag
        rules_rows.append([sid, display_name, "4", start, end, "", "", "1", "1", "1", "1", "1", "1", "", banner, t_pic, t_back, "StoreTitle9402", local_key_des, b_pic])
        
        for pack_index, p in enumerate(packs, start=1):
            p_start, p_end = convert_date(p['Start']), convert_date(p['End'])
            rwd_id = f"1{p['PackID']}"
            
            price_str = str(p['Price']).replace("$", "").strip().lower()
            if price_str in ["0", "0.00", "free", ""]: 
                pay_num = "0"
                price_type = "3"
            else:
                try: pay_num = f"10{str(int(round(float(price_str)*100))).zfill(4)}"
                except: pay_num = "104999"
                price_type = "1"

            order_str = str(p['Order']).replace(".0", "")
            local_key_2 = f"ui_store_{normalize_for_ui_key(banner_suffix)}_{normalize_for_ui_key(p['PackID'])}"
            if is_holiday:
                local_key_2 = get_holiday_pack_icon_name(banner_suffix, event_name, cat_name, p['PackName'], p['PackID'])
            elif is_legendary_character_pack:
                daily_shop_icon = get_legendary_daily_shop_icon(cat_name, pack_index, character_id, character_class)
                if daily_shop_icon:
                    local_key_2 = daily_shop_icon
            if is_extra_sale and extra_sale_type == "Extra Step-up":
                local_key = (
                    "ExtradealsStepup_StepUp_Pack_Free"
                    if price_str in ["0", "0.00", "free", ""]
                    else "ExtradealsStepup_StepUp_Pack"
                )
            elif text_keys:
                if is_step_up_type(text_keys["type"]):
                    local_key = f"{text_keys['pack_key_base']}_{pack_index}"
                else:
                    local_key = text_keys["pack_key"]
            else:
                if is_holiday:
                    fallback_base = f"{normalize_for_func_key(banner_suffix or event_name)}_{normalize_for_func_key(cat_name)}_Pack"
                    if is_step_up_group:
                        local_key = f"{fallback_base}_{pack_index}"
                    else:
                        local_key = fallback_base
                else:
                    local_key = local_key_des
            step_flag = "1" if is_step_up_group else ""
            price_is_free = price_str in ["0", "0.00", "free", ""]
            
            next_is_free = False
            if is_step_up_group and pack_index < len(packs):
                next_pack = packs[pack_index]
                next_price_str = str(next_pack.get('Price', '')).replace("$", "").strip().lower()
                if next_price_str in ["0", "0.00", "free", ""]:
                    next_is_free = True

            label_val = p['LabelID']
            if is_step_up_group:
                label_val = ""
                if price_is_free:
                    label_val = "StoreDiscount_Label_Hot"
                elif next_is_free:
                    label_val = "StoreDiscount_Label_Free"

            pack_rows.append([
                p['PackID'], sid, p['PackName'], p_start, p_end, "", p['Limit'], 
                p['OpenLvl'], "", p['BuyPrePack'], "", price_type, pay_num, rwd_id, 
                local_key, local_key_2, order_str, "", label_val, "", "", p['SkuID'], "", "", "", "", step_flag
            ])
            
            r_row = [rwd_id, f"{p['PackName']}", "1", ""]
            for item in p['Items'][:8]:
                r_row.extend(["", item[0], normalize_int_string(item[1])])
            while len(r_row) < 28:
                r_row.append("")
            reward_rows.append(r_row)

    append_csv(os.path.join(target_dir, "RechargePackRules.csv"), rules_rows)
    append_csv(os.path.join(target_dir, "RechargePack.csv"), pack_rows)
    append_csv(os.path.join(target_dir, "RechargePackReward.csv"), reward_rows)

    popup = entry_popup.get().strip() if entry_popup else ""
    jump = entry_jump.get().strip() if entry_jump else ""
    # Marketing output is a Mode 2-only feature.  Existing values from a saved
    # config must not cause Mode 1 to append AdsPopUp or Jump rows.
    if is_holiday and (popup or jump):
        h_start, h_end = convert_date(parsed[0]['Start']), convert_date(parsed[-1]['End'])
        popup_keys = build_popup_text_keys(event_name, banner_suffix, is_extra_sale=is_extra_sale, extra_sale_type=extra_sale_type)
        if popup:
            append_csv(os.path.join(target_dir, "AdsPopUp.csv"), [[
                popup, event_name, h_start, h_end, "2", "530", "", "", "", "", "5", jump, "1", "1",
                "ui_popuppic_img_shuxing_bg",
                f"ui_popuppic_img_bg_{banner_suffix}" if banner_suffix else "ui_popuppic_img_bg_memorialday2026deal",
                f"ui_recharg_img_timetxtbg_{banner_suffix}" if banner_suffix else "ui_recharg_img_timetxtbg_memorialday2026deal",
                "", popup_keys["title_key"], "3b2da4", "ffff45", "ffb13d", "dc2e14",
                popup_keys["text_key"], popup_keys["text_key_2"], "", "Popup_Button_GoNow"
            ]])
        if jump:
            append_csv(os.path.join(target_dir, "Jump.csv"), [[
                jump, "25", f"Holiday Sale - {event_name}", "4", sub_ids[0], "", "", "", "1",
                "Func Corresponding to PayStoreSub table", "Func_fufeishangcheng", "COMMON_Ended", "1"
            ]])
    return sku_adjustments

# ==========================================
# LOGIC BATTLE PASS (BP)
# ==========================================
def build_bp_paystore_name(hero):
    hero = (hero or "").strip()
    if not hero:
        return "Hero BP"
    return hero if hero.lower().startswith("hero bp") else f"Hero BP-{hero}"


def build_bp_order(bp_id):
    try:
        bp_num = int(str(bp_id).strip())
        if 9901 <= bp_num <= 9914:
            return str(200 + (bp_num - 9900))
        if 9941 <= bp_num <= 9949:
            return str(500 + (bp_num - 9940))
    except:
        pass
    return "200"


def sync_bp_paystore_entry(target_dir, bp_id, hero, ally):
    bp_id = str(bp_id).strip()
    hero = (hero or "").strip()
    ally = str(ally).strip()
    if not bp_id:
        return

    sub_path = os.path.join(target_dir, "PayStoreSub.csv")
    sub_rows = read_csv(sub_path)
    if not sub_rows:
        sub_rows = [["SubStoreID", "O", "LocalKey", "OpenStyle", "OpenParam", "Order", "Functype", "ProductType", "Open", "Priority"]]

    display_name = build_bp_paystore_name(hero)
    local_key = f"CharacterName_{ally}" if ally else ""
    desired_sub_row = [bp_id, display_name, local_key, "2", "530", build_bp_order(bp_id), "23", "", "1", ""]

    found = False
    for i in range(1, len(sub_rows)):
        row = sub_rows[i]
        if len(row) > 0 and str(row[0]).strip() == bp_id:
            sub_rows[i] = desired_sub_row[:len(sub_rows[0])] + [""] * max(0, len(sub_rows[0]) - len(desired_sub_row))
            found = True
            break

    if not found:
        sub_rows.append(desired_sub_row[:len(sub_rows[0])] + [""] * max(0, len(sub_rows[0]) - len(desired_sub_row)))

    write_csv(sub_path, sub_rows)

    main_path = os.path.join(target_dir, "PayStoreMain.csv")
    main_rows = read_csv(main_path)
    if not main_rows:
        return

    target_idx = None
    for i, row in enumerate(main_rows):
        if len(row) > 1 and "Character Growth Packs" in str(row[1]).strip():
            target_idx = i
            break
    if target_idx is None:
        return

    row = main_rows[target_idx]
    if any(len(r) > 0 and str(r).strip() == bp_id for r in row[8:]):
        return

    empty_slots = [i for i in range(8, len(row)) if not str(row[i]).strip()]
    if empty_slots:
        row[empty_slots[0]] = bp_id
    else:
        row.append(bp_id)
        while len(main_rows[0]) < len(row):
            main_rows[0].append(f"SubStore{len(main_rows[0])}")
        if len(main_rows) > 1:
            while len(main_rows[1]) < len(row):
                main_rows[1].append("")
        for other_idx in range(2, len(main_rows)):
            while len(main_rows[other_idx]) < len(row):
                main_rows[other_idx].append("")

    write_csv(main_path, main_rows)


def process_bp(target_dir):
    bp_id, hero, ally, r_file = entry_bp_id.get(), entry_bp_hero.get(), entry_bp_ally.get(), entry_bp_reward_csv.get()
    if not os.path.exists(r_file): raise Exception("Thiếu file Reward!")
    r_rows = read_csv(r_file)
    r_h = r_rows[0] if r_rows else []
    c_rwd, c_note = r_h.index("RewardID") if "RewardID" in r_h else 1, r_h.index("O") if "O" in r_h else 2
    f_ids, p_ids = [], []
    for row in r_rows[1:]:
        if len(row) <= max(c_rwd, c_note): continue
        if "hero bp" in str(row[c_note]).lower():
            rid = str(row[c_rwd]).strip()
            if rid.startswith(f"1{bp_id}01") or rid.startswith(f"1{bp_id}02"): f_ids.append(rid)
            elif rid.startswith(f"1{bp_id}03") or rid.startswith(f"1{bp_id}04"): p_ids.append(rid)
    f_ids, p_ids = sorted(list(set(f_ids))), sorted(list(set(p_ids)))
    if len(f_ids) < 11: f_ids = [f"1{bp_id}0{11+i}" for i in range(11)]
    if len(p_ids) < 11: p_ids = [f"1{bp_id}0{31+i}" for i in range(11)]
    append_csv(os.path.join(target_dir, "RechargeBP.csv"), [[bp_id, f"Hero BP - {hero}", "1", ally, entry_bp_start.get(), entry_bp_end.get(), "0", "60", bp_id, "RechargeBpTitle_1", "RechargeBpDes_1", "RechargeBpTips1", f"ui_recharge_banner_{ally}", "ui_recharg_img_dailyreward_bg"]])
    
    lvls, params = [11, 21, 31, 41, 51, 61, 71, 81, 91, 101, 111], [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    info_shows = [61, 61, 61, 61, 61, 111, 111, 111, 111, 111, 111]
    pay_price_shows = [31, 41, 51, 61, 61, 81, 91, 101, 111, 111, 111]
    paynums = [100499, 100999, 101999, 104999, 104999, 104999, 104999, 109999, 109999, 109999, 109999]
    limits = [6, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    skus = ["characterupgrade5"] + ["characterupgrade10"] + ["characterupgrade20"] + ["characterupgrade50"]*4 + ["characterupgrade100"]*4
    bp_data = []
    for i in range(11): bp_data.append([bp_id, lvls[i], f"Hero BP - {hero}", params[i], info_shows[i], pay_price_shows[i], f_ids[i], p_ids[i], paynums[i], limits[i], skus[i]])
    append_csv(os.path.join(target_dir, "RechargeBPReward.csv"), bp_data)
    sync_bp_paystore_entry(target_dir, bp_id, hero, ally)

def run_tool():
    try:
        sku_adjustments = []
        tg = entry_target_dir.get()
        if not os.path.exists(tg): raise Exception("Thư mục Perforce không tồn tại!")
        m = combo_mode.get()
        is_extra = (
            m == "Mode 2: Holiday Sales" and bool(var_is_extra_sale.get())
        ) if var_is_extra_sale else False
        extra_type = var_extra_sale_type.get() if var_extra_sale_type else "Extra Deal"
        is_legendary_character_pack = (
            m == "Mode 1: Normal Event Pack"
            and not is_extra
            and combo_sale_type.get() == "Legendary Event"
        )
        if is_legendary_character_pack:
            character_id = entry_banner_suffix.get().strip()
            character_class = var_character_class.get().strip()
            if not character_id.isdigit():
                raise Exception("Legendary Character Pack cần Character ID là số.")
            if character_class not in {"A", "B", "C"}:
                raise Exception("Legendary Character Pack cần chọn hệ Strength (A), Agility (B) hoặc Intellect (C).")
        if m == "Mode 3: Character BP":
            process_bp(tg)
        else:
            if m == "Mode 2: Holiday Sales":
                popup_id = entry_popup.get().strip() if entry_popup else ""
                popup_title = entry_popup_title.get().strip() if entry_popup_title else ""
                popup_subtitle = entry_popup_subtitle.get().strip() if entry_popup_subtitle else ""
                popup_desc = entry_popup_desc.get().strip() if entry_popup_desc else ""
                if not popup_id or not popup_title or not popup_subtitle or not popup_desc:
                    raise Exception("Mode 2 Holiday Sales yêu cầu PopUp ID và tất cả các trường popup text (Title, Subtitle, Desc).")
            sku_adjustments = process_pack(tg, is_holiday=(m == "Mode 2: Holiday Sales"), is_extra_sale=is_extra, extra_sale_type=extra_type)
        cfg = {"TargetDir": tg, "SourceCSV": entry_csv.get(), "Mode": m, "SaleType": combo_sale_type.get(), "FilterKeyword": entry_csv_filter.get(), "EventName": entry_event_name.get(), "BannerSuffix": entry_banner_suffix.get(), "CharacterClass": var_character_class.get(), "PopUpID": entry_popup.get(), "JumpID": entry_jump.get(), "BP_ID": entry_bp_id.get(), "BP_Hero": entry_bp_hero.get(), "BP_Ally": entry_bp_ally.get(), "BP_Start": entry_bp_start.get(), "BP_End": entry_bp_end.get(), "BP_RewardCSV": entry_bp_reward_csv.get(), "GenerateText": bool(var_generate_text.get()) if var_generate_text else False, "MainStoreText": entry_main_store_text.get() if entry_main_store_text else "", "PopupTitleText": entry_popup_title.get() if entry_popup_title else "", "PopupSubtitleText": entry_popup_subtitle.get() if entry_popup_subtitle else "", "PopupDescText": entry_popup_desc.get() if entry_popup_desc else "", "IsExtraSale": is_extra, "ExtraSaleType": extra_type}
        cfg["Substores"] = [{"type": w["type_var"].get(), "pack_name": w["pack_var"].get(), "substore_name": w["sub_var"].get(), "substore_desc": w["desc_var"].get()} for w in substore_text_widgets]
        save_config(cfg)
        completion_message = f"Đã gen data cho {m}!"
        if sku_adjustments:
            replacement_lines = [
                f"- {item['PackName']} ({item['PackID']}): {item['OldSkuID'] or '(trống)'} -> {item['NewSkuID']} ({item['Price']})"
                for item in sku_adjustments
            ]
            completion_message += "\n\nSKU không tồn tại đã được thay bằng SKU cùng giá:\n" + "\n".join(replacement_lines)
        messagebox.showinfo("BINGO!", completion_message)
    except Exception as e: messagebox.showerror("Lỗi", str(e))

# ==========================================
# GIAO DIỆN (UI)
# ==========================================
def main():
    global window, entry_target_dir, entry_csv, entry_csv_filter, entry_event_name, entry_banner_suffix, var_character_class, combo_mode, combo_sale_type, entry_popup, entry_jump, entry_bp_reward_csv, entry_bp_id, entry_bp_hero, entry_bp_ally, entry_bp_start, entry_bp_end, var_generate_text, entry_main_store_text, entry_popup_title, entry_popup_subtitle, entry_popup_desc, substore_text_widgets, var_is_extra_sale, var_extra_sale_type

    window = tk.Tk(); window.title("DC IAP Master - Monetization Tool V13.9.2 Hotfix"); window.geometry("750x820")
    def tao_o(parent, nhan, val=""):
        f = tk.Frame(parent); f.pack(pady=3, fill='x', padx=10)
        tk.Label(f, text=nhan, width=20, anchor='w', font=("Arial", 9, "bold")).pack(side='left')
        e = tk.Entry(f); e.insert(0, val); e.pack(side='right', expand=True, fill='x'); return e

    canvas = tk.Canvas(window, borderwidth=0)
    vsb = tk.Scrollbar(window, orient='vertical', command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side='right', fill='y')
    canvas.pack(side='left', fill='both', expand=True)

    scroll_frame = tk.Frame(canvas)
    canvas_frame = canvas.create_window((0, 0), window=scroll_frame, anchor='nw')

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox('all'))
    scroll_frame.bind('<Configure>', on_frame_configure)

    def on_canvas_configure(event):
        canvas.itemconfigure(canvas_frame, width=event.width)
    canvas.bind('<Configure>', on_canvas_configure)

    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
    canvas.bind_all('<MouseWheel>', on_mousewheel)

    tk.Label(scroll_frame, text="💰 IAP & BATTLE PASS GENERATOR", font=("Arial", 14, "bold"), fg="#2E86C1").pack(pady=10)

    f_dir = tk.Frame(scroll_frame); f_dir.pack(fill='x', padx=20, pady=5)
    entry_target_dir = tk.Entry(f_dir); entry_target_dir.pack(side='left', expand=True, fill='x')
    tk.Button(f_dir, text="Perforce", command=lambda: chon_thu_muc(entry_target_dir)).pack(side='right')

    f_mode = tk.Frame(scroll_frame); f_mode.pack(fill='x', padx=20, pady=10)
    combo_mode = ttk.Combobox(f_mode, values=["Mode 1: Normal Event Pack", "Mode 2: Holiday Sales", "Mode 3: Character BP"], state="readonly", width=35)
    combo_mode.set("Mode 1: Normal Event Pack"); combo_mode.pack(side='left', padx=10)

    frame_iap = tk.Frame(scroll_frame)
    f_csv = tk.Frame(frame_iap); f_csv.pack(fill='x', pady=5, padx=10)
    entry_csv = tk.Entry(f_csv); entry_csv.pack(side='left', expand=True, fill='x')
    tk.Button(f_csv, text="Google Sheet CSV", command=lambda: chon_file(entry_csv)).pack(side='right')

    entry_csv_filter = tao_o(frame_iap, "Từ khóa lọc:")
    entry_event_name = tao_o(frame_iap, "Event/Sale Name:")

    f_banner_suffix = tk.Frame(frame_iap)
    entry_banner_suffix = tao_o(f_banner_suffix, "Ally ID / Suffix:")
    f_banner_suffix.pack(pady=3, fill='x', padx=10)

    f_type = tk.Frame(frame_iap); f_type.pack(pady=3, fill='x', padx=10)
    tk.Label(f_type, text="Loại Sale (Type):", width=20, anchor='w', font=("Arial", 9, "bold"), fg="red").pack(side='left')
    combo_sale_type = ttk.Combobox(f_type, values=["Legendary Event", "Epic Event", "Reinforcement Event"], state="readonly")
    combo_sale_type.set("Legendary Event"); combo_sale_type.pack(side='right', expand=True, fill='x')

    frame_character_class = tk.Frame(frame_iap)
    f_character_class = tk.Frame(frame_character_class); f_character_class.pack(fill='x', padx=10, pady=(2, 4))
    tk.Label(f_character_class, text="Character Trait:", width=20, anchor='w', font=("Arial", 9, "bold")).pack(side='left')
    var_character_class = tk.StringVar(value="A")
    tk.Radiobutton(f_character_class, text="Strength (A)", variable=var_character_class, value="A").pack(side='left')
    tk.Radiobutton(f_character_class, text="Agility (B)", variable=var_character_class, value="B").pack(side='left', padx=8)
    tk.Radiobutton(f_character_class, text="Intellect (C)", variable=var_character_class, value="C").pack(side='left')

    # --- Extra Sale checkbox ---
    frame_extra_sale = tk.LabelFrame(frame_iap, text="⚡ Extra Sale (Mode 2)", fg="#C0392B")
    var_is_extra_sale = tk.BooleanVar(value=False)
    var_extra_sale_type = tk.StringVar(value="Extra Deal")

    f_extra_check = tk.Frame(frame_extra_sale); f_extra_check.pack(fill='x', padx=10, pady=(4, 0))
    cb_extra = tk.Checkbutton(f_extra_check, text="Đây là Extra Sale (không tạo dòng mới trong PayStoreMain)",
                              variable=var_is_extra_sale, font=("Arial", 9), fg="#C0392B")
    cb_extra.pack(side='left')

    frame_extra_radio = tk.Frame(frame_extra_sale)
    tk.Radiobutton(frame_extra_radio, text="Extra Deal  (điền vào row Flash Sale)",
                   variable=var_extra_sale_type, value="Extra Deal", font=("Arial", 9)).pack(side='left', padx=10)
    tk.Radiobutton(frame_extra_radio, text="Extra Step-up  (điền vào row Extra Deals - Step up)",
                   variable=var_extra_sale_type, value="Extra Step-up", font=("Arial", 9)).pack(side='left', padx=10)

    def toggle_extra_sale_radio(*_):
        if var_is_extra_sale.get():
            frame_extra_radio.pack(fill='x', padx=10, pady=(0, 6))
        else:
            frame_extra_radio.pack_forget()
    var_is_extra_sale.trace_add("write", toggle_extra_sale_radio)
    toggle_extra_sale_radio()  # init state

    frame_marketing = tk.LabelFrame(frame_iap, text="Marketing", fg="#27AE60")
    entry_popup, entry_jump = tao_o(frame_marketing, "PopUp ID:"), tao_o(frame_marketing, "Jump ID:")

    frame_popup_text = tk.LabelFrame(frame_iap, text="Popup Text (Mode 2 Holiday Sales)", fg="#D35400")
    f_popup_title = tk.Frame(frame_popup_text); f_popup_title.pack(fill='x', padx=10, pady=2)
    tk.Label(f_popup_title, text="Title:", width=16, anchor='w').pack(side='left')
    entry_popup_title = tk.Entry(f_popup_title); entry_popup_title.pack(side='left', expand=True, fill='x')
    f_popup_subtitle = tk.Frame(frame_popup_text); f_popup_subtitle.pack(fill='x', padx=10, pady=2)
    tk.Label(f_popup_subtitle, text="Subtitle:", width=16, anchor='w').pack(side='left')
    entry_popup_subtitle = tk.Entry(f_popup_subtitle); entry_popup_subtitle.pack(side='left', expand=True, fill='x')
    f_popup_desc = tk.Frame(frame_popup_text); f_popup_desc.pack(fill='x', padx=10, pady=2)
    tk.Label(f_popup_desc, text="Desc:", width=16, anchor='w').pack(side='left')
    entry_popup_desc = tk.Entry(f_popup_desc); entry_popup_desc.pack(side='left', expand=True, fill='x')

    frame_text_settings = tk.LabelFrame(frame_iap, text="📝 Optional IAP Text Generation", fg="#8E44AD")
    var_generate_text = tk.BooleanVar(value=False)
    tk.Checkbutton(frame_text_settings, text="Điền text và sinh SourceShopUI / SourceActivityUI", variable=var_generate_text, command=lambda: update_text_frame_visibility()).pack(anchor='w', padx=10, pady=5)

    frame_iap_text = tk.Frame(frame_text_settings)
    f_main_store_text = tk.Frame(frame_iap_text); f_main_store_text.pack(fill='x', padx=10, pady=3)
    tk.Label(f_main_store_text, text="Main Store Text:", width=20, anchor='w', font=("Arial", 9, "bold")).pack(side='left')
    entry_main_store_text = tk.Entry(f_main_store_text); entry_main_store_text.pack(side='right', expand=True, fill='x')

    frame_substores = tk.Frame(frame_iap_text); frame_substores.pack(fill='x', padx=10, pady=5)
    substore_text_widgets = []

    def remove_substore_row(widget_dict, row_frame):
        if len(substore_text_widgets) <= 1:
            messagebox.showwarning("Lưu ý", "Phải giữ lại ít nhất 1 Substore!")
            return
        row_frame.destroy()
        substore_text_widgets.remove(widget_dict)
        for idx, w in enumerate(substore_text_widgets, start=1):
            w["frame"].config(text=f"Substore {idx}")

    def add_substore_row():
        idx = len(substore_text_widgets) + 1
        row = tk.LabelFrame(frame_substores, text=f"Substore {idx}", padx=10, pady=6)
        row.pack(fill='x', pady=4)

        f_type = tk.Frame(row); f_type.pack(fill='x', pady=2)
        tk.Label(f_type, text="Type:", width=16, anchor='w').pack(side='left')
        type_var = tk.StringVar(value="Daily")
        ttk.Combobox(f_type, values=["Daily", "Step-up", "Special"], state="readonly", width=18, textvariable=type_var).pack(side='left', padx=2)

        widget_dict = {"type_var": type_var}
        btn_del = tk.Button(f_type, text="❌ Delete", fg="red", font=("Arial", 8, "bold"), command=lambda: remove_substore_row(widget_dict, row))
        btn_del.pack(side='right', padx=5)

        f_pack = tk.Frame(row); f_pack.pack(fill='x', pady=2)
        tk.Label(f_pack, text="Pack name:", width=16, anchor='w').pack(side='left')
        pack_var = tk.StringVar()
        tk.Entry(f_pack, textvariable=pack_var).pack(side='left', expand=True, fill='x')
        tk.Label(row, text="RechargePack", fg="#555", anchor='w', justify='left').pack(fill='x', padx=26, pady=(0, 4))

        f_sub = tk.Frame(row); f_sub.pack(fill='x', pady=2)
        tk.Label(f_sub, text="Substore name:", width=16, anchor='w').pack(side='left')
        sub_var = tk.StringVar()
        tk.Entry(f_sub, textvariable=sub_var).pack(side='left', expand=True, fill='x')
        tk.Label(row, text="PayStoreSub.csv", fg="#555", anchor='w', justify='left').pack(fill='x', padx=26, pady=(0, 4))

        f_desc = tk.Frame(row); f_desc.pack(fill='x', pady=2)
        tk.Label(f_desc, text="Substore desc:", width=16, anchor='w').pack(side='left')
        desc_var = tk.StringVar()
        tk.Entry(f_desc, textvariable=desc_var).pack(side='left', expand=True, fill='x')
        tk.Label(row, text="RechargePackRules", fg="#555", anchor='w', justify='left').pack(fill='x', padx=26, pady=(0, 4))

        widget_dict.update({
            "pack_var": pack_var, 
            "sub_var": sub_var, 
            "desc_var": desc_var,
            "frame": row
        })
        substore_text_widgets.append(widget_dict)

    add_substore_row()
    tk.Button(frame_iap_text, text="+ Add Substore", command=add_substore_row).pack(anchor='e', padx=10, pady=3)

    def update_text_frame_visibility():
        if var_generate_text.get():
            frame_iap_text.pack(fill='x', padx=10, pady=5)
        else:
            frame_iap_text.pack_forget()

    def update_popup_frame_visibility():
        if combo_mode.get() == "Mode 2: Holiday Sales" and not var_is_extra_sale.get():
            frame_popup_text.pack(fill='x', padx=10, pady=5)
        else:
            frame_popup_text.pack_forget()

    frame_bp = tk.LabelFrame(scroll_frame, text="🎁 HERO BATTLE PASS SETTINGS (MODE 3)", font=("Arial", 10, "bold"), fg="#E67E22", padx=15, pady=10)
    
    f_bp_csv = tk.Frame(frame_bp); f_bp_csv.pack(fill='x', pady=5, padx=10)
    tk.Label(f_bp_csv, text="Reward CSV File:", width=18, anchor='w', font=("Arial", 9, "bold")).pack(side='left')
    entry_bp_reward_csv = tk.Entry(f_bp_csv); entry_bp_reward_csv.pack(side='left', expand=True, fill='x', padx=5)
    tk.Button(f_bp_csv, text="Select File", command=lambda: chon_file(entry_bp_reward_csv), bg="#D4E6F1").pack(side='right')

    entry_bp_id = tao_o(frame_bp, "BP ID (e.g. 9904):")
    entry_bp_hero = tao_o(frame_bp, "Hero Name (e.g. Doctor Fate):")
    entry_bp_ally = tao_o(frame_bp, "Ally ID (e.g. 13108):")
    entry_bp_start = tao_o(frame_bp, "Start (YYYYMMDD_HHMMSS):")
    entry_bp_end = tao_o(frame_bp, "End (YYYYMMDD_HHMMSS):")

    def update_ui(e=None):
        mode = combo_mode.get()
        if mode == "Mode 3: Character BP":
            frame_iap.pack_forget()
            frame_bp.pack(fill='x', padx=20)
        else:
            frame_bp.pack_forget()
            frame_iap.pack(fill='x', padx=20)
            if mode == "Mode 2: Holiday Sales":
                frame_marketing.pack(fill='x', padx=10, pady=5)
                frame_extra_sale.pack(fill='x', padx=10, pady=4)
                frame_text_settings.pack(fill='x', padx=10, pady=5)
                f_banner_suffix.pack_forget()
                f_type.pack_forget()
            else:
                frame_marketing.pack_forget()
                frame_extra_sale.pack_forget()
                frame_text_settings.pack_forget()
                f_banner_suffix.pack(pady=3, fill='x', padx=10)
                f_type.pack(pady=3, fill='x', padx=10)

        should_show_legendary_character = (
            mode == "Mode 1: Normal Event Pack"
            and combo_sale_type.get() == "Legendary Event"
            and not var_is_extra_sale.get()
        )
        if should_show_legendary_character:
            frame_character_class.pack(fill='x', padx=10, pady=2, before=f_type)
        else:
            frame_character_class.pack_forget()

    combo_mode.bind("<<ComboboxSelected>>", lambda e: [update_ui(), update_popup_frame_visibility()])
    combo_sale_type.bind("<<ComboboxSelected>>", update_ui)
    var_is_extra_sale.trace_add("write", lambda *_: [update_ui(), update_popup_frame_visibility()])
    update_ui(); update_text_frame_visibility(); update_popup_frame_visibility()

    tk.Button(scroll_frame, text="🚀GENERATE", bg="#28B463", fg="white", font=("Arial", 12, "bold"), command=run_tool).pack(pady=20, fill='x', padx=50)

    sv = load_config()
    if sv:
        e_map = {entry_target_dir: "TargetDir", entry_csv: "SourceCSV", entry_csv_filter: "FilterKeyword", entry_event_name: "EventName", entry_banner_suffix: "BannerSuffix", entry_popup: "PopUpID", entry_jump: "JumpID", entry_bp_id: "BP_ID", entry_bp_hero: "BP_Hero", entry_bp_ally: "BP_Ally", entry_bp_start: "BP_Start", entry_bp_end: "BP_End", entry_bp_reward_csv: "BP_RewardCSV"}
        for e, k in e_map.items():
            if k in sv:
                e.delete(0, tk.END)
                e.insert(0, sv[k])
        if "GenerateText" in sv and var_generate_text:
            var_generate_text.set(bool(sv["GenerateText"]))
        if "MainStoreText" in sv and entry_main_store_text:
            entry_main_store_text.delete(0, tk.END)
            entry_main_store_text.insert(0, sv["MainStoreText"])
        if "PopupTitleText" in sv and entry_popup_title:
            entry_popup_title.delete(0, tk.END)
            entry_popup_title.insert(0, sv["PopupTitleText"])
        if "PopupSubtitleText" in sv and entry_popup_subtitle:
            entry_popup_subtitle.delete(0, tk.END)
            entry_popup_subtitle.insert(0, sv["PopupSubtitleText"])
        if "PopupDescText" in sv and entry_popup_desc:
            entry_popup_desc.delete(0, tk.END)
            entry_popup_desc.insert(0, sv["PopupDescText"])
        if "Substores" in sv:
            saved_subs = sv["Substores"]
            while len(substore_text_widgets) < len(saved_subs):
                add_substore_row()
            for i, sub_data in enumerate(saved_subs):
                w = substore_text_widgets[i]
                if "type" in sub_data: w["type_var"].set(sub_data["type"])
                if "pack_name" in sub_data: w["pack_var"].set(sub_data["pack_name"])
                if "substore_name" in sub_data: w["sub_var"].set(sub_data["substore_name"])
                if "substore_desc" in sub_data: w["desc_var"].set(sub_data["substore_desc"])
        if "Mode" in sv:
            combo_mode.set(sv["Mode"])
            update_ui()
        if "SaleType" in sv:
            combo_sale_type.set(sv["SaleType"])
        if "CharacterClass" in sv and sv["CharacterClass"] in {"A", "B", "C"}:
            var_character_class.set(sv["CharacterClass"])
        update_text_frame_visibility()
        update_popup_frame_visibility()
        update_ui()

    window.mainloop()

if __name__ == "__main__":
    main()
