import os
import csv
import sys
import json
import stat
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog

# ==========================================
# CẤU HÌNH PATH & LƯU TRỮ TỰ ĐỘNG
# ==========================================
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(SCRIPT_DIR, "hs_config.json")

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
# HÀM BỔ TRỢ UI & FILE
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

def unlock_file(filepath):
    if os.path.exists(filepath):
        os.chmod(filepath, stat.S_IWRITE)

def read_csv(filepath):
    if not os.path.exists(filepath): return []
    try:
        with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
            return list(csv.reader(f))
    except: return []

def write_csv(filepath, rows):
    unlock_file(filepath)
    with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerows(rows)

def append_csv(filepath, rows):
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
        write_csv(filepath, rows)
        return
    data_map = {str(row[0]): row for row in existing_rows if row}
    for new_row in rows:
        if new_row:
            data_map[str(new_row[0])] = new_row
    write_csv(filepath, list(data_map.values()))

# ==========================================
# CHUẨN HÓA NGÀY THÁNG
# ==========================================
def parse_to_dt(d_str):
    if not d_str: return None
    clean_str = str(d_str).strip().split()[0]
    formats = ["%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            return datetime.strptime(clean_str, fmt)
        except: continue
    return None

def convert_date(d_str):
    dt = parse_to_dt(d_str)
    if dt:
        return dt.strftime("%Y%m%d_000000")
    return str(d_str).strip()

def get_val(r, col, header):
    if col in header:
        idx = header.index(col)
        if idx < len(r): 
            return str(r[idx]).strip()
    return ""

def safe_lower(val):
    try:
        if val is None: return ""
        return str(val).strip().lower()
    except: return ""

def resolve_pack_id(pack_id, existing_ids):
    pack_id = str(pack_id).strip()
    while pack_id in existing_ids:
        if len(pack_id) >= 2 and pack_id[:2].isdigit():
            prefix = int(pack_id[:2])
            prefix += 1
            pack_id = str(prefix) + pack_id[2:]
        else:
            pack_id = str(int(pack_id) + 1) if pack_id.isdigit() else pack_id + "_1"
    existing_ids.add(pack_id)
    return pack_id

# ==========================================
# CORE LOGIC: SMART FILTER EDITION
# ==========================================
def process_homescreen():
    target_dir = entry_target_dir.get()
    csv_path = entry_csv.get()
    
    if not os.path.exists(target_dir): raise Exception("Thư mục Perforce không tồn tại!")
    if not os.path.exists(csv_path): raise Exception("File CSV PackCreator không tồn tại!")

    # 1. QUÉT GROUP ID & TỰ ĐỘNG LẤY ĐỘ DÀI CỘT TỪ GAME
    group_path = os.path.join(target_dir, "RechargeRecPackGroup.csv")
    group_rows = read_csv(group_path)
    
    expected_group_cols = len(group_rows[0]) if group_rows and len(group_rows) > 0 else 353
    
    max_group_id, max_everylogin = 0, 0
    for r in group_rows[1:]:
        if not r: continue
        try:
            gid = int(r[0])
            if gid > max_group_id: max_group_id = gid
        except: pass
        if len(r) > 2:
            note = str(r[2]).strip()
            if safe_lower(note).startswith("everylogin"):
                try:
                    num = int(note.split()[-1])
                    if num > max_everylogin: max_everylogin = num
                except: pass
    if max_group_id == 0:
        try: max_group_id = int(entry_hs_group.get()) - 1
        except: max_group_id = 109919

    # 2. QUÉT PACK ID TRÁNH TRÙNG & ĐO ĐỘ DÀI CỘT
    pack_path = os.path.join(target_dir, "RechargeRecPack.csv")
    existing_pack_rows = read_csv(pack_path)
    
    expected_pack_cols = len(existing_pack_rows[0]) if existing_pack_rows and len(existing_pack_rows) > 0 else 35
    existing_ids = {str(r[0]).strip() for r in existing_pack_rows if r}

    # 3. LẤY MỐC NGÀY ĐỂ LỌC
    filter_start_dt = parse_to_dt(entry_hs_start.get().strip())
    filter_end_dt = parse_to_dt(entry_hs_end.get().strip())
    
    if not filter_start_dt or not filter_end_dt:
        raise Exception("Vui lòng nhập đúng định dạng ngày Start/End để lọc Pack!")

    # 4. ĐỌC FILE PACK CREATOR
    rows = read_csv(csv_path)
    header_idx = -1
    for i, r in enumerate(rows):
        if "Pack Name" in r and ("Pack ID" in r or "Pack IDs" in r):
            header_idx = i; break
    if header_idx == -1: raise Exception("Không tìm thấy dòng Header chuẩn!")
    
    header = rows[header_idx]
    data_rows = rows[header_idx+1:]
    pack_id_col = "Pack IDs" if "Pack IDs" in header else "Pack ID"
    
    # Tìm linh hoạt cột Open Level
    open_lvl_col = ""
    for h in header:
        if "OpenLvl" in h or "Open Level" in h:
            open_lvl_col = h
            break
    
    new_group_rows, pack_rows = [], []
    processed_count = 0
    
    for r in data_rows:
        pack_id = get_val(r, pack_id_col, header)
        if not pack_id or safe_lower(pack_id) == "false": continue
        
        csv_start_raw = get_val(r, "Start Date (UTC)", header)
        csv_end_raw = get_val(r, "End Date (UTC)", header)
        csv_dt = parse_to_dt(csv_start_raw)
        
        if not csv_dt: continue
        if not (filter_start_dt <= csv_dt <= filter_end_dt):
            continue
            
        pack_id = resolve_pack_id(pack_id, existing_ids)
        pack_name = get_val(r, "Pack Name", header)
        final_start = convert_date(csv_start_raw)
        final_end = convert_date(csv_end_raw)
        
       # --- LOGIC OPEN LEVEL (Lấy trực tiếp từ cột OpenLvl) ---
        open_lvl_raw = get_val(r, open_lvl_col, header) if open_lvl_col else ""
        open_lvl = str(open_lvl_raw).strip()
        
        # Xử lý quy luật riêng cho Open Level
        if open_lvl == "":
            open_lvl = "1001"  # Bỏ trống mặc định là 1001
        elif open_lvl == "101":
            open_lvl = "1001"  # Đổi 101 thành 1001
        elif open_lvl == "102":
            open_lvl = "1002"  # Mở rộng thêm nếu có 102
        elif open_lvl == "103":
            open_lvl = "1003"  # Mở rộng thêm nếu có 103
        # --- XỬ LÝ SỐ ITEM QUANTITY ---
        items = []
        for i in range(1, 10):
            i_id, i_qty = get_val(r, f"Item {i} ID", header), get_val(r, f"Item {i} Qty", header)
            if i_id and i_qty:
                try: 
                    clean_qty = str(i_qty).replace(",", "").strip()
                    i_qty = str(int(float(clean_qty)))
                except: pass
                items.append((i_id, i_qty))
                
        # --- XỬ LÝ PRICE ---
        price_val = str(get_val(r, "Price", header)).replace("$", "").replace(",", "").strip()
        try: p_float = float(price_val)
        except: p_float = 0.0
        
        if p_float <= 0: pay_num, sku_id = "0", ""
        else:
            pay_num = f"10{str(int(round(p_float * 100))).zfill(4)}"
            sku_id = f"diamondcombo{int(round(p_float))}"
            
        # --- HỆ THỐNG 6 TIER LABEL VÀ BACKGROUND ---
        if p_float <= 4.99:
            bg, lbl = "ui_recharge_img_role01", "ContextualIAP_Label_Good"
        elif p_float <= 9.99:
            bg, lbl = "ui_recharge_img_role02", "ContextualIAP_Label_Sweet"
        elif p_float <= 19.99:
            bg, lbl = "ui_recharge_img_role01", "ContextualIAP_Label_Great"
        elif p_float <= 29.99:
            bg, lbl = "ui_recharge_img_role02", "ContextualIAP_Label_Amazing"
        elif p_float <= 49.99:
            bg, lbl = "ui_recharge_img_role01", "ContextualIAP_Label_Huge"
        else:
            bg, lbl = "ui_recharge_img_role01", "ContextualIAP_Label_SuperDuper"
        
        max_group_id += 1
        max_everylogin += 1
        name_idx = (max_everylogin % 5) or 5
        
        g_row = [str(max_group_id), f"RechargeRecPack_Name00{name_idx}", f"Everylogin {max_everylogin}", "510260253"]
        while len(g_row) < expected_group_cols:
            g_row.append("")
        new_group_rows.append(g_row)
        
        p_row = [str(pack_id), str(max_group_id), pack_name, final_start, "", "0", pay_num, open_lvl, ""]
        item_cols = []
        for j in range(5):
            if j < len(items): item_cols.extend(["", items[j][0], items[j][1]])
            else: item_cols.extend(["", "", ""])
        p_row.extend(item_cols + ["86400", "1", "0", "0", "", bg, "1", lbl, sku_id, final_start, final_end])
        
        while len(p_row) < expected_pack_cols:
            p_row.append("")
            
        pack_rows.append(p_row)
        processed_count += 1
        
    if processed_count == 0:
        raise Exception(f"Không tìm thấy gói nào trong khoảng {entry_hs_start.get()} đến {entry_hs_end.get()}!")
        
    append_csv(os.path.join(target_dir, "RechargeRecPackGroup.csv"), new_group_rows)
    append_csv(os.path.join(target_dir, "RechargeRecPack.csv"), pack_rows)
    return processed_count

def run_tool():
    try:
        count = process_homescreen()
        save_config({"TargetDir": entry_target_dir.get(), "SourceCSV": entry_csv.get(), "HS_Group": entry_hs_group.get(), "HS_Start": entry_hs_start.get(), "HS_End": entry_hs_end.get()})
        messagebox.showinfo("SUCCESS", f"GENERATED {count} Packs!")
    except Exception as e: messagebox.showerror("Lỗi", str(e))

# ==========================================
# GIAO DIỆN
# ==========================================
window = tk.Tk(); window.title("📱 Homescreen Offers Master Tool V15.7"); window.geometry("650x480")
def tao_o(parent, nhan, val=""):
    f = tk.Frame(parent); f.pack(pady=5, fill='x', padx=20)
    tk.Label(f, text=nhan, width=35, anchor='w', font=("Arial", 9, "bold")).pack(side='left')
    e = tk.Entry(f); e.insert(0, val); e.pack(side='right', expand=True, fill='x'); return e

tk.Label(window, text="🏠 HOMESCREEN OFFERS GENERATOR", font=("Arial", 14, "bold"), fg="#D35400").pack(pady=15)
f_dir = tk.Frame(window); f_dir.pack(fill='x', padx=20, pady=5)
entry_target_dir = tk.Entry(f_dir); entry_target_dir.pack(side='left', expand=True, fill='x')
tk.Button(f_dir, text="Perforce Folder", command=lambda: chon_thu_muc(entry_target_dir)).pack(side='right')
f_csv = tk.Frame(window); f_csv.pack(fill='x', padx=20, pady=5)
entry_csv = tk.Entry(f_csv); entry_csv.pack(side='left', expand=True, fill='x')
tk.Button(f_csv, text="PackCreator CSV", command=lambda: chon_file(entry_csv)).pack(side='right')

frame_filter = tk.LabelFrame(window, text="DATE FILTER (ONLY GEN PACK WITHIN THIS RANGE)", fg="red", font=("Arial", 9, "bold"))
frame_filter.pack(fill='x', padx=20, pady=15, ipady=10)
entry_hs_start = tao_o(frame_filter, "Start Date (MM/DD/YYYY):")
entry_hs_end = tao_o(frame_filter, "End Date (MM/DD/YYYY):")
entry_hs_group = tao_o(window, "Group ID Provision (If file is empty):", "109920")

tk.Button(window, text="🚀 GENRATE DATA", bg="#D35400", fg="white", font=("Arial", 12, "bold"), command=run_tool).pack(pady=15, fill='x', padx=60)

sv = load_config()
if sv:
    if "TargetDir" in sv: entry_target_dir.insert(0, sv["TargetDir"])
    if "SourceCSV" in sv: entry_csv.insert(0, sv["SourceCSV"])
    if "HS_Group" in sv: entry_hs_group.delete(0, tk.END); entry_hs_group.insert(0, sv["HS_Group"])
    if "HS_Start" in sv: entry_hs_start.insert(0, sv["HS_Start"])
    if "HS_End" in sv: entry_hs_end.insert(0, sv["HS_End"])

window.mainloop()