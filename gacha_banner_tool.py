import argparse
import csv
import json
import os
import stat
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime, timedelta


# ==========================================
# CẤU HÌNH PATH KHI ĐÓNG GÓI EXE
# ==========================================
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def create_hover_button(parent, text, bg, hover_bg, fg='white', command=None, font=('Segoe UI', 10, 'bold'), **kwargs):
    btn = tk.Button(parent, text=text, bg=bg, fg=fg, activebackground=hover_bg, activeforeground=fg, font=font, bd=0, command=command, cursor='hand2')
    for k, v in kwargs.items():
        btn[k] = v
    btn.bind('<Enter>', lambda e: btn.config(bg=hover_bg))
    btn.bind('<Leave>', lambda e: btn.config(bg=bg))
    return btn

def ensure_writable(filepath):
    if os.path.exists(filepath):
        try:
            os.chmod(filepath, stat.S_IWRITE)
        except Exception:
            pass


def normalize_newlines(text):
    return text.replace('\r\n', '\n').replace('\n', '\r\n')


def save_json(filepath, data):
    filepath = os.path.normpath(filepath)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_csv_rows(filepath):
    if not os.path.isfile(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
            next(reader)
        except StopIteration:
            return []

        rows = []
        for row in reader:
            if not row:
                continue
            if row[0].strip().lower() == 'index':
                continue
            row_data = {header: value for header, value in zip(headers, row)}
            rows.append(row_data)
        return rows


def parse_id_list(value):
    if not value:
        return []
    return [item.strip() for item in value.replace('|', ',').split(',') if item.strip()]


def extract_id(value):
    return value.split('|', 1)[0].strip() if value else ''


def find_gacha_type_matches(query, type_rows):
    query = (query or '').strip().lower()
    if not type_rows:
        return []

    matches = []
    for row in type_rows:
        label = row.get('o', '').strip().lower()
        internal = row.get('Name', '').strip().lower()
        pool_id = row.get('ID', '').strip().lower()

        if not query or query == pool_id or query in label or query in internal:
            matches.append(row)
    return matches


def get_branch_legendary_epic(type_row, branch_rows):
    branch_ids = parse_id_list(type_row.get('AllyGachaBranch'))
    if not branch_ids or not branch_rows:
        return None, None

    branch_map = {row.get('ID', '').strip(): row for row in branch_rows}
    for branch_id in branch_ids:
        branch = branch_map.get(branch_id)
        if not branch:
            continue
        gacha = branch.get('Gacha', '').strip()
        parts = [part.strip() for part in gacha.split(';') if part.strip()]
        if len(parts) >= 2:
            return extract_id(parts[0]), extract_id(parts[1])
        if len(parts) == 1:
            return extract_id(parts[0]), None
    return None, None


def find_gacha_type_matches_by_branch(query, type_rows, branch_rows):
    query = (query or '').strip().lower()
    if not query or not type_rows or not branch_rows:
        return []

    branch_ids = []
    for branch in branch_rows:
        branch_label = branch.get('o', '').strip().lower()
        branch_id = branch.get('ID', '').strip().lower()
        if query == branch_id or query in branch_label:
            branch_ids.append(branch_id)

    if not branch_ids:
        return []

    matches = []
    for row in type_rows:
        branches = parse_id_list(row.get('AllyGachaBranch'))
        if any(bid in [b.lower() for b in branches] for bid in branch_ids):
            matches.append(row)
    return matches


def build_jump_lines(data):
    banner_name = data.get('BannerName') or f"AllyGachaName{data['GachaTypeID']}"
    return [
        f"{data['GachaJumpId']},8,Skip to Gacha - {data['HeroName']},{data['GachaTypeID']},,,,,1,Corresponds to AllyGachaType table card pool ID,{banner_name},,1\n"
    ]


def build_ally_gacha_type_line(data):
    start_time = data['StartTime'].strip()
    end_time = data.get('EndTime', '').strip()
    if not end_time:
        end_time = format_time(parse_time(start_time) + timedelta(days=1))
    
    banner_name = data.get('BannerName') or f"AllyGachaName{data['GachaTypeID']}"
    pack_jump = data.get('PackJumpId', '1205')

    banner_type = data.get('BannerType', 'Legendary')
    if banner_type == 'Legendary':
        o_name = f"Legendary Event Gacha - {data['HeroName']}"
        type_val = "2"
        gacha1cost = "1120016"
        gacha1buycost = ""
        gacha10buycost = ""
        jump = "1502"
        rule_id = "34"
        tab_name = "AllyGachaTab32"
        back = "ui_drawcard_img_bg02"
        sort_val = "805"
        up_des = "Gacha_UpDes5"
    else:
        o_name = f"New Ally {data['HeroName']} UP Banner"
        type_val = "1"
        gacha1cost = "1120015"
        gacha1buycost = "200"
        gacha10buycost = "2000"
        jump = "1501"
        rule_id = "31"
        tab_name = "AllyGachaTab31"
        back = "ui_drawcard_img_bg03"
        sort_val = "907"
        up_des = "Gacha_UpDes4"

    return (
        f"{data['GachaTypeID']},{o_name},{data['GachaTypeID']}01,1,{type_val},1,1,{data['AllyId']},,,,"
        f"{start_time},{end_time},{gacha1cost},1,{gacha1buycost},{gacha10buycost},,,{jump},,,,,,"
        f"{rule_id},{banner_name},,,5,30,{tab_name},ui_drawcard_btn_{data['AllyId']},{back},ui_cardpool_{data['AllyId']},,{sort_val},{up_des},{pack_jump}\n"
    )


def build_ally_gacha_branch_line(data):
    gacha_leg = data.get('RewardData', {}).get('GachaLegendary', '').strip() or '1901380501'
    gacha_epic = data.get('RewardData', {}).get('GachaEpic', '').strip() or '1901380502'
    banner_type = data.get('BannerType', 'Legendary')
    
    if banner_type == 'Legendary':
        o_name = f"{data['HeroName']} Legendary Event Pool"
        o2_name = f"{data['HeroName']} Guaranteed Legendary"
        up_epic_id = "0"
        up_epic_rate = "0"
        inherit_key = "62"
        gacha_str = f"{gacha_leg}|504;{gacha_epic}|402"
        gacha_random = "1904002303|10000"
    else:  # Epic
        o_name = f"New Ally {data['HeroName']} UP Banner"
        o2_name = f"Better chance at {data['HeroName']}"
        up_epic_id = data.get('AllyId', '').strip()
        up_epic_rate = "3000"
        inherit_key = "63"
        gacha_str = f"{gacha_leg}|401;1904001304|301"
        gacha_random = "1904001204|3000;1904001104|4700"
    
    return (
        f"{data['GachaTypeID']}01,{o_name},{o2_name},1,{up_epic_id},{up_epic_rate},,,{inherit_key},,1,-1,{gacha_str},{gacha_random}\n"
    )


def select_from_list(root, title, items, label_func):
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.transient(root)
    dialog.grab_set()

    tk.Label(dialog, text=title, anchor='w').pack(fill='x', padx=12, pady=(8, 0))
    listbox = tk.Listbox(dialog, width=80, height=min(20, len(items)))
    listbox.pack(fill='both', expand=True, padx=12, pady=8)

    for item in items:
        listbox.insert(tk.END, label_func(item))
    if items:
        listbox.selection_set(0)

    selected = {'item': None}

    def choose():
        sel = listbox.curselection()
        if sel:
            selected['item'] = items[sel[0]]
        dialog.destroy()

    button_frame = tk.Frame(dialog)
    button_frame.pack(fill='x', pady=(0, 12))
    tk.Button(button_frame, text='OK', command=choose).pack(side='left', padx=8)
    tk.Button(button_frame, text='Cancel', command=dialog.destroy).pack(side='right', padx=8)

    dialog.wait_window()
    return selected['item']


def append_to_file(filepath, text):
    filepath = os.path.normpath(filepath)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    ensure_writable(filepath)
    with open(filepath, 'a', encoding='utf-8-sig', newline='') as f:
        f.write(normalize_newlines(text))


def parse_time(value):
    try:
        return datetime.strptime(value.strip(), "%Y%m%d_%H%M%S")
    except Exception:
        raise ValueError("Thời gian phải ở định dạng YYYYMMDD_HHMMSS")


def format_time(dt):
    return dt.strftime("%Y%m%d_%H%M%S")


def build_banner_line(data):
    start_time = data['StartTime'].strip()
    if not start_time:
        raise ValueError('Start Time không thể để trống')
    end_time = data.get('EndTime', '').strip()
    if not end_time:
        end_time = format_time(parse_time(start_time) + timedelta(days=1))
    return (
        f"{data['BannerID']},{data['HeroName']},{start_time},{end_time},2,530,"
        f"ui_banner_{data['AllyId']},{data['GachaJumpId']},,,0\n"
    )


def build_popup_line(data):
    start_time = data['StartTime'].strip()
    end_time = data.get('EndTime', '').strip()
    if not end_time:
        end_time = format_time(parse_time(start_time) + timedelta(days=1))
    ally = data['AllyId']
    return (
        f"{data['PopUpID']},{data['HeroName']},{start_time},{end_time},2,530,,,,,5,{data['GachaJumpId']},"
        f"1,1280,ui_popuppic_img_shuxing_bg,ui_popuppic_img_bg_{ally},ui_recharg_img_timetxtbg_{ally},{ally},Popup_{ally}_title,0e0e0e,ffffff,ffbb04,145c8f,"
        f"Popup_{ally}_text,Popup_{ally}_text_2,,\n"
    )


def print_usage_and_exit(parser):
    parser.print_help()
    print('\nChạy không tham số để mở GUI, hoặc dùng các tham số sau để tạo banner đơn.')
    sys.exit(0)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Gacha Banner Tool: GUI hoặc CLI để tạo AdsBanner và AdsPopUp.'
    )
    parser.add_argument('--gui', action='store_true', help='Mở GUI để tạo nhiều banner cùng lúc')
    parser.add_argument('--target-dir', help='Thư mục lưu AdsBanner.csv (CLI)')
    parser.add_argument('--banner-id', help='Banner ID mới (CLI)')
    parser.add_argument('--hero-name', help='Tên hero hiển thị (CLI)')
    parser.add_argument('--ally-id', help='Ally ID của hero (CLI)')
    parser.add_argument('--gacha-jump-id', help='Gacha Jump ID liên kết (CLI)')
    parser.add_argument('--start-time', help='Start Time, định dạng YYYYMMDD_HHMMSS (CLI)')
    parser.add_argument('--end-time', default='', help='End Time, định dạng YYYYMMDD_HHMMSS (CLI, optional)')
    parser.add_argument('--popup-id', default='', help='Popup ID nếu muốn tạo AdsPopUp.csv (CLI)')
    return parser


class BannerSection:
    def __init__(self, master, remove_callback, lookup_callback=None):
        self.frame = tk.Frame(master, highlightbackground='#D0D3D4', highlightthickness=1, bd=0, bg='white')
        self.remove_callback = remove_callback
        self.lookup_callback = lookup_callback
        self.expanded = True

        self.header_frame = tk.Frame(self.frame, bg='#EBF5FB')
        self.header_frame.grid(row=0, column=0, sticky='we')
        self.frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(0, weight=0)
        self.header_frame.grid_columnconfigure(1, weight=1)
        self.header_frame.grid_columnconfigure(2, weight=0)

        self.toggle_button = create_hover_button(self.header_frame, '▼', '#EBF5FB', '#D6EAF8', fg='#2C3E50', font=('Segoe UI', 9), width=3, command=self.toggle)
        self.toggle_button.grid(row=0, column=0, sticky='w')

        self.title_label = tk.Label(self.header_frame, text='Banner', anchor='w', font=('Segoe UI', 10, 'bold'), bg='#EBF5FB', fg='#2C3E50')
        self.title_label.grid(row=0, column=1, sticky='w', padx=(6, 0))

        self.remove_button = create_hover_button(self.header_frame, '✕ Remove', '#EBF5FB', '#FADBD8', fg='#C0392B', font=('Segoe UI', 9, 'bold'), command=self.remove)
        self.remove_button.grid(row=0, column=2, sticky='e', padx=4)

        self.body_frame = tk.Frame(self.frame, padx=12, pady=12, bg='white')
        self.body_frame.grid(row=1, column=0, sticky='we')
        self.body_frame.grid_columnconfigure(1, weight=1)
        self.body_frame.grid_columnconfigure(2, weight=0)
        self.body_frame.grid_columnconfigure(3, weight=1)

        # Row 0
        self.banner_id = self._create_entry(self.body_frame, 'Banner ID:', '170', 0, 0)
        self.popup_id = self._create_entry(self.body_frame, 'Popup ID:', '', 0, 1)

        # Row 1
        self.hero_name = self._create_entry(self.body_frame, 'Hero Name:', 'BlackAdam', 1, 0)
        
        # Banner Type selector
        type_label = tk.Label(self.body_frame, text='Banner Type:', anchor='w', width=16, font=('Segoe UI', 9), bg='white', fg='#333333')
        type_label.grid(row=1, column=2, sticky='w', padx=(0, 4), pady=4)
        type_frame = tk.Frame(self.body_frame, bg='white')
        type_frame.grid(row=1, column=3, sticky='w', pady=4)
        self.banner_type = tk.StringVar(value='Legendary')
        tk.Radiobutton(type_frame, text='Legendary', variable=self.banner_type, value='Legendary', command=self._on_banner_type_change, font=('Segoe UI', 9), bg='white', activebackground='white').pack(side='left', padx=(0, 10))
        tk.Radiobutton(type_frame, text='Epic', variable=self.banner_type, value='Epic', command=self._on_banner_type_change, font=('Segoe UI', 9), bg='white', activebackground='white').pack(side='left')
        
        # Row 2
        self.lookup_button = create_hover_button(self.body_frame, '🔍 Auto Fill from AllyGachaType (Lookup)', '#F2F3F4', '#E5E8E8', fg='#2C3E50', font=('Segoe UI', 9, 'bold'), command=self.lookup_gacha_type)
        self.lookup_button.grid(row=2, column=0, columnspan=4, sticky='we', pady=(8, 8), ipady=2)

        # Row 3
        self.gacha_type_id = self._create_entry(self.body_frame, 'Gacha Type ID:', '', 3, 0)
        self.banner_name = self._create_entry(self.body_frame, 'Banner Name:', '', 3, 1)

        # Row 4
        self.pack_jump_id = self._create_entry(self.body_frame, 'Pack Jump ID:', '1205', 4, 0)
        self.ally_id = self._create_entry(self.body_frame, 'Ally ID:', '13110', 4, 1)

        # Row 5
        self.gacha_jump_id = self._create_entry(self.body_frame, 'Gacha Jump ID:', '1369', 5, 0)
        self.gacha_legendary = self._create_entry(self.body_frame, 'Gacha Legendary:', '1901380501', 5, 1)

        # Row 6
        self.start_time = self._create_entry(self.body_frame, 'Start Time:', '20260715_000000', 6, 0)
        self.gacha_epic = self._create_entry(self.body_frame, 'Gacha Epic Pool:', '1901380502', 6, 1)

        # Row 7
        self.end_time = self._create_entry(self.body_frame, 'End Time (Blank=1d):', '', 7, 0)

        self._on_banner_type_change()
        self.update_title()

    def _on_banner_type_change(self):
        if self.banner_type.get() == 'Legendary':
            self.gacha_legendary.label.config(text='Gacha Legendary:')
            self.gacha_epic.label.grid()
            self.gacha_epic.grid()
        else:
            self.gacha_legendary.label.config(text='Gacha Epic Pool:')
            self.gacha_epic.label.grid_remove()
            self.gacha_epic.grid_remove()

    def _create_entry(self, parent, label_text, default='', row=0, col=0):
        label = tk.Label(parent, text=label_text, anchor='w', width=16, font=('Segoe UI', 9), bg='white', fg='#333333')
        label.grid(row=row, column=col*2, sticky='w', padx=(0, 4), pady=4)
        entry = ttk.Entry(parent, font=('Segoe UI', 9))
        entry.insert(0, default)
        entry.grid(row=row, column=col*2+1, sticky='we', pady=4, padx=(0, 15))
        entry.bind('<KeyRelease>', lambda event: self.update_title())
        entry.bind('<FocusOut>', lambda event: self.update_title())
        entry.label = label
        return entry

    def lookup_gacha_type(self):
        if not self.lookup_callback:
            return

        query = self.hero_name.get().strip()
        result = self.lookup_callback(query)
        if not result:
            return

        if isinstance(result, tuple):
            row, gacha_legendary, gacha_epic = result
        else:
            row, gacha_legendary, gacha_epic = result, None, None

        if not self.hero_name.get().strip():
            hero_name = row.get('o', '').strip()
            if hero_name:
                self.hero_name.delete(0, tk.END)
                self.hero_name.insert(0, hero_name)

        self.gacha_type_id.delete(0, tk.END)
        self.gacha_type_id.insert(0, row.get('ID', '').strip())

        ally_list = parse_id_list(row.get('UpHero') or row.get('Up'))
        if ally_list:
            self.ally_id.delete(0, tk.END)
            self.ally_id.insert(0, ally_list[0])

        if gacha_legendary:
            self.gacha_legendary.delete(0, tk.END)
            self.gacha_legendary.insert(0, gacha_legendary)
        if gacha_epic:
            self.gacha_epic.delete(0, tk.END)
            self.gacha_epic.insert(0, gacha_epic)

        banner_name = ''
        for k, v in row.items():
            if str(v).startswith('AllyGachaName'):
                banner_name = str(v)
                break
        if banner_name:
            self.banner_name.delete(0, tk.END)
            self.banner_name.insert(0, banner_name)

        self.update_title()

    def grid(self, row):
        self.frame.grid(row=row, column=0, sticky='we', pady=(0, 10), padx=2)

    def remove(self):
        self.frame.destroy()
        self.remove_callback(self)

    def toggle(self):
        if self.expanded:
            self.body_frame.grid_remove()
            self.toggle_button.config(text='▶')
            self.expanded = False
        else:
            self.body_frame.grid()
            self.toggle_button.config(text='▼')
            self.expanded = True

    def update_title(self):
        banner_id = self.banner_id.get().strip() or 'New'
        hero_name = self.hero_name.get().strip() or 'Banner'
        self.title_label.config(text=f'{banner_id} - {hero_name}')

    def get_data(self):
        return {
            'BannerID': self.banner_id.get().strip(),
            'PopUpID': self.popup_id.get().strip(),
            'HeroName': self.hero_name.get().strip(),
            'BannerType': self.banner_type.get(),
            'GachaTypeID': self.gacha_type_id.get().strip(),
            'BannerName': self.banner_name.get().strip(),
            'PackJumpId': self.pack_jump_id.get().strip(),
            'AllyId': self.ally_id.get().strip(),
            'GachaJumpId': self.gacha_jump_id.get().strip(),
            'RewardData': {
                'GachaLegendary': self.gacha_legendary.get().strip(),
                'GachaEpic': self.gacha_epic.get().strip(),
            },
            'StartTime': self.start_time.get().strip(),
            'EndTime': self.end_time.get().strip(),
        }

    def set_data(self, data):
        self.banner_id.delete(0, tk.END)
        self.banner_id.insert(0, data.get('BannerID', ''))
        self.popup_id.delete(0, tk.END)
        self.popup_id.insert(0, data.get('PopUpID', ''))
        self.hero_name.delete(0, tk.END)
        self.hero_name.insert(0, data.get('HeroName', ''))
        self.banner_type.set(data.get('BannerType', 'Legendary'))
        self.gacha_type_id.delete(0, tk.END)
        self.gacha_type_id.insert(0, data.get('GachaTypeID', ''))
        self.banner_name.delete(0, tk.END)
        self.banner_name.insert(0, data.get('BannerName', ''))
        self.pack_jump_id.delete(0, tk.END)
        self.pack_jump_id.insert(0, data.get('PackJumpId', '1205'))
        self.ally_id.delete(0, tk.END)
        self.ally_id.insert(0, data.get('AllyId', ''))
        self.gacha_jump_id.delete(0, tk.END)
        self.gacha_jump_id.insert(0, data.get('GachaJumpId', ''))
        reward_data = data.get('RewardData', {}) or {}
        self.gacha_legendary.delete(0, tk.END)
        self.gacha_legendary.insert(0, reward_data.get('GachaLegendary', '1901380501'))
        self.gacha_epic.delete(0, tk.END)
        self.gacha_epic.insert(0, reward_data.get('GachaEpic', '1901380502'))
        self.start_time.delete(0, tk.END)
        self.start_time.insert(0, data.get('StartTime', ''))
        self.end_time.delete(0, tk.END)
        self.end_time.insert(0, data.get('EndTime', ''))
        self._on_banner_type_change()
        self.update_title()


class GachaBatchApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Gacha Banner Master Tool')
        self.root.geometry('780x680')
        
        style = ttk.Style()
        if 'vista' in style.theme_names():
            style.theme_use('vista')
        elif 'clam' in style.theme_names():
            style.theme_use('clam')

        self.sections = []

        header_lbl = ttk.Label(root, text="Gacha Banner Generator", font=("Segoe UI", 14, "bold"))
        header_lbl.pack(pady=(15, 5))

        top = ttk.Frame(root)
        top.pack(fill='x', padx=15, pady=5)

        ttk.Label(top, text='Target Folder:', width=15, font=('Segoe UI', 9)).pack(side='left')
        self.target_dir = ttk.Entry(top, font=('Segoe UI', 9))
        self.target_dir.insert(0, os.path.join(os.getcwd(), 'Test_Data'))
        self.target_dir.pack(side='left', fill='x', expand=True, padx=8)
        create_hover_button(top, 'Browse...', '#95A5A6', '#7F8C8D', font=('Segoe UI', 9), command=self.choose_target_dir).pack(side='left', ipady=2, ipadx=5)

        self.gacha_type_rows = []
        self.gacha_branch_rows = []
        self.load_gacha_tables()

        btn_frame = ttk.Frame(root)
        btn_frame.pack(fill='x', padx=15, pady=(10, 5))
        self.add_section_button = create_hover_button(btn_frame, '➕ Add Banner Request', '#2ECC71', '#27AE60', command=self.add_section)
        self.add_section_button.pack(side='left', ipady=4, ipadx=10)

        self.canvas_frame = ttk.Frame(root)
        self.canvas_frame.pack(fill='both', expand=True, padx=15, pady=5)
        
        bg_color = style.lookup('TFrame', 'background') or '#F0F0F0'
        self.canvas = tk.Canvas(self.canvas_frame, highlightthickness=0, bd=0, bg=bg_color)
        self.scrollbar = ttk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.sections_frame = ttk.Frame(self.canvas)
        self.sections_frame.grid_columnconfigure(0, weight=1)
        
        self.sections_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.sections_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            scroll_amount = int(-1 * (event.delta / 120)) if event.delta else 0
            if sys.platform == 'darwin':
                scroll_amount = int(-1 * event.delta)
            self.canvas.yview_scroll(scroll_amount, "units")
        self.root.bind_all("<MouseWheel>", _on_mousewheel)
        self.root.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.root.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

        bottom = tk.Frame(root, bg=bg_color)
        bottom.pack(fill='x', padx=15, pady=10)
        create_hover_button(bottom, '🚀 Generate All Gacha Files', '#3498DB', '#2980B9', command=self.generate_all).pack(side='left', padx=5, ipady=5, ipadx=10)
        create_hover_button(bottom, '🗑 Clear All', '#E67E22', '#D35400', command=self.clear_all).pack(side='right', padx=5, ipady=5, ipadx=10)

        json_path = os.path.join(SCRIPT_DIR, 'BannerData.json')
        if os.path.exists(json_path):
            self.load_json_from_path(json_path)
        else:
            self.add_section()

    def choose_target_dir(self):
        folder = filedialog.askdirectory(title='Chọn thư mục đích')
        if folder:
            self.target_dir.delete(0, tk.END)
            self.target_dir.insert(0, folder)
            self.load_gacha_tables()

    def get_data_dir(self):
        folder = self.target_dir.get().strip()
        if folder and os.path.isdir(folder):
            return folder
        default_dir = os.path.join(os.getcwd(), 'Test_Data')
        if os.path.isdir(default_dir):
            return default_dir
        return os.getcwd()

    def load_gacha_tables(self):
        data_dir = self.get_data_dir()
        self.gacha_type_rows = load_csv_rows(os.path.join(data_dir, 'AllyGachaType.csv'))
        self.gacha_branch_rows = load_csv_rows(os.path.join(data_dir, 'AllyGachaBranch.csv'))

    def lookup_gacha_type(self, query):
        if not self.gacha_type_rows:
            self.load_gacha_tables()
        if not self.gacha_type_rows:
            messagebox.showwarning('Thiếu file', 'Không tìm thấy AllyGachaType.csv trong thư mục đích hoặc Test_Data.')
            return None

        matches = find_gacha_type_matches(query, self.gacha_type_rows)
        if not matches:
            fallback = find_gacha_type_matches_by_branch(query, self.gacha_type_rows, self.gacha_branch_rows)
            if fallback:
                matches = fallback
            else:
                messagebox.showwarning('Không tìm thấy', f'Không tìm thấy gacha type tương ứng với "{query}" trong AllyGachaType.csv hoặc AllyGachaBranch.csv.')
                return None

        if len(matches) == 1:
            row = matches[0]
            return row, *get_branch_legendary_epic(row, self.gacha_branch_rows)

        selected = select_from_list(
            self.root,
            'Chọn Gacha Type',
            matches,
            lambda row: f"{row.get('ID','')} - {row.get('o','')} (Jump {row.get('PacksJump','')})"
        )
        if not selected:
            return None
        return selected, *get_branch_legendary_epic(selected, self.gacha_branch_rows)

    def add_section(self):
        section = BannerSection(self.sections_frame, self.remove_section, self.lookup_gacha_type)
        self.sections.append(section)
        section.grid(len(self.sections) - 1)

    def remove_section(self, section):
        self.sections.remove(section)
        for index, sec in enumerate(self.sections):
            sec.grid(index)

    def clear_sections(self):
        for section in list(self.sections):
            section.remove()
        self.sections.clear()

    def clear_all(self):
        self.clear_sections()
        self.add_section()

    def get_sections_data(self):
        return [section.get_data() for section in self.sections]

    def load_json_from_path(self, path):
        try:
            data = load_json(path)
        except Exception as ex:
            messagebox.showerror('Lỗi', 'Không thể đọc file JSON:\n' + str(ex))
            return

        target_dir = data.get('TargetDir', '')
        if target_dir:
            self.target_dir.delete(0, tk.END)
            self.target_dir.insert(0, target_dir)

        banners = data.get('Banners', [])
        self.clear_sections()
        if not banners:
            self.add_section()
            return

        for banner_data in banners:
            section = BannerSection(self.sections_frame, self.remove_section, self.lookup_gacha_type)
            section.set_data(banner_data)
            self.sections.append(section)
            section.grid(len(self.sections) - 1)

    def generate_all(self):
        target_dir = self.target_dir.get().strip()
        if not target_dir:
            messagebox.showwarning('Thiếu dữ liệu', 'Vui lòng chọn thư mục đích.')
            return

        target_dir = os.path.normpath(target_dir)
        os.makedirs(target_dir, exist_ok=True)

        banner_file = os.path.join(target_dir, 'AdsBanner.csv')
        popup_file = os.path.join(target_dir, 'AdsPopUp.csv')
        jump_file = os.path.join(target_dir, 'Jump.csv')
        gacha_type_file = os.path.join(target_dir, 'AllyGachaType.csv')
        gacha_branch_file = os.path.join(target_dir, 'AllyGachaBranch.csv')

        generated = 0
        errors = []

        for index, section in enumerate(self.sections, start=1):
            data = section.get_data()
            missing = [k for k, v in data.items() if k in ['BannerID', 'HeroName', 'AllyId', 'GachaJumpId', 'GachaTypeID', 'StartTime'] and not v]
            if missing:
                errors.append(f'Banner #{index}: Thiếu {", ".join(missing)}')
                continue

            try:
                banner_line = build_banner_line(data)
                jump_lines = build_jump_lines(data)
                gacha_type_line = build_ally_gacha_type_line(data)
                gacha_branch_line = build_ally_gacha_branch_line(data)
            except ValueError as ex:
                errors.append(f'Banner #{index}: {ex}')
                continue

            append_to_file(banner_file, banner_line)
            if data['PopUpID']:
                popup_line = build_popup_line(data)
                append_to_file(popup_file, popup_line)

            for line in jump_lines:
                append_to_file(jump_file, line)
            append_to_file(gacha_type_file, gacha_type_line)
            append_to_file(gacha_branch_file, gacha_branch_line)
            generated += 1

        if errors:
            message = 'Một số banner chưa được sinh:\n' + '\n'.join(errors)
            messagebox.showwarning('Lỗi dữ liệu', message)
        else:
            json_path = os.path.join(SCRIPT_DIR, 'BannerData.json')
            save_json(json_path, {'TargetDir': target_dir, 'Banners': self.get_sections_data()})
            messagebox.showinfo('Hoàn tất', f'Đã tạo {generated} gacha items vào {target_dir}\nĐã lưu JSON vào {json_path}')


def main():
    parser = parse_args()
    args = parser.parse_args()

    if len(sys.argv) == 1 or args.gui:
        root = tk.Tk()
        app = GachaBatchApp(root)
        root.mainloop()
        return

    required = ['target_dir', 'banner_id', 'hero_name', 'ally_id', 'gacha_jump_id', 'start_time']
    missing = [name for name in required if not getattr(args, name)]
    if missing:
        print('Thiếu tham số CLI:', ', '.join(missing))
        print_usage_and_exit(parser)

    data = {
        'BannerID': args.banner_id,
        'HeroName': args.hero_name,
        'AllyId': args.ally_id,
        'GachaJumpId': args.gacha_jump_id,
        'StartTime': args.start_time,
        'EndTime': args.end_time,
        'PopUpID': args.popup_id,
    }

    banner_line = build_banner_line(data)
    banner_file = os.path.join(os.path.normpath(args.target_dir), 'AdsBanner.csv')
    append_to_file(banner_file, banner_line)
    print(f'🟢 Created banner line in {banner_file}')

    if args.popup_id:
        popup_line = build_popup_line(data)
        popup_file = os.path.join(os.path.normpath(args.target_dir), 'AdsPopUp.csv')
        append_to_file(popup_file, popup_line)
        print(f'🟢 Created popup line in {popup_file}')

    print('Done.')


if __name__ == '__main__':
    main()
