import os
import stat
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime, timedelta


def ensure_writable(filepath):
    if os.path.exists(filepath):
        try:
            os.chmod(filepath, stat.S_IWRITE)
        except Exception:
            pass


def normalize_newlines(text):
    return text.replace('\r\n', '\n').replace('\n', '\r\n')


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
    end_time = data['EndTime']
    if not end_time:
        end_time = format_time(parse_time(data['StartTime']) + timedelta(hours=24))
    end_time_som = format_time(parse_time(end_time) - timedelta(days=1))
    return (
        f"{data['BannerID']},{data['HeroName']},{data['StartTime']},{end_time_som},2,530,"
        f"ui_banner_{data['AllyId']},{data['GachaJumpId']},,,0\n"
    )


def build_popup_line(data):
    end_time = data['EndTime']
    if not end_time:
        end_time = format_time(parse_time(data['StartTime']) + timedelta(hours=24))
    end_time_som = format_time(parse_time(end_time) - timedelta(days=1))
    ally = data['AllyId']
    return (
        f"{data['PopUpID']},{data['HeroName']},{data['StartTime']},{end_time_som},2,530,,,,,5,{data['GachaJumpId']},"
        f"1,1,ui_popuppic_img_shuxing_bg,ui_popuppic_img_bg_{ally},ui_recharg_img_timetxtbg_{ally},{ally},Popup_{ally}_title,0e0e0e,ffffff,ffbb04,145c8f,"
        f"Popup_{ally}_text,Popup_{ally}_text_2,,\n"
    )


class BannerSection:
    def __init__(self, master, remove_callback):
        self.frame = tk.Frame(master, bd=1, relief='groove', padx=6, pady=6)
        self.remove_callback = remove_callback

        self.banner_id = self._create_entry('Banner ID:', '170')
        self.popup_id = self._create_entry('Popup ID:', '')
        self.hero_name = self._create_entry('Hero Name:', 'BlackAdam')
        self.ally_id = self._create_entry('Ally ID:', '13110')
        self.gacha_jump_id = self._create_entry('Gacha Jump ID:', '1369')
        self.start_time = self._create_entry('Start Time:', '20260715_000000')
        self.end_time = self._create_entry('End Time (blank => +24h):', '')

        self.remove_button = tk.Button(self.frame, text='Remove', fg='white', bg='#d9534f', command=self.remove)
        self.remove_button.grid(row=0, column=4, rowspan=2, padx=6, pady=2)

    def _create_entry(self, label_text, default=''):
        row = len(self.frame.grid_slaves()) // 2
        label = tk.Label(self.frame, text=label_text, anchor='w')
        label.grid(row=row, column=0, sticky='w', padx=(0, 4), pady=2)
        entry = tk.Entry(self.frame)
        entry.insert(0, default)
        entry.grid(row=row, column=1, sticky='we', pady=2)
        self.frame.grid_columnconfigure(1, weight=1)
        return entry

    def grid(self, row):
        self.frame.grid(row=row, column=0, sticky='we', pady=4, padx=4)

    def remove(self):
        self.frame.destroy()
        self.remove_callback(self)

    def get_data(self):
        return {
            'BannerID': self.banner_id.get().strip(),
            'PopUpID': self.popup_id.get().strip(),
            'HeroName': self.hero_name.get().strip(),
            'AllyId': self.ally_id.get().strip(),
            'GachaJumpId': self.gacha_jump_id.get().strip(),
            'StartTime': self.start_time.get().strip(),
            'EndTime': self.end_time.get().strip(),
        }


class GachaBatchApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Gacha Banner Batch Generator')
        self.sections = []

        top = tk.Frame(root, pady=8)
        top.pack(fill='x')

        tk.Label(top, text='Target Folder:', width=12, anchor='w').pack(side='left', padx=(8, 0))
        self.target_dir = tk.Entry(top)
        self.target_dir.insert(0, os.path.join(os.getcwd(), 'Test_Data'))
        self.target_dir.pack(side='left', fill='x', expand=True, padx=4)
        tk.Button(top, text='Browse', command=self.choose_target_dir).pack(side='left', padx=4)

        self.sections_frame = tk.Frame(root)
        self.sections_frame.pack(fill='both', expand=True, padx=8)

        self.add_section_button = tk.Button(root, text='+ Add Banner Request', bg='#5cb85c', fg='white', command=self.add_section)
        self.add_section_button.pack(fill='x', padx=8, pady=(0, 8))

        bottom = tk.Frame(root, pady=8)
        bottom.pack(fill='x')
        tk.Button(bottom, text='Generate All Banners', bg='#0275d8', fg='white', command=self.generate_all).pack(side='left', padx=8)
        tk.Button(bottom, text='Clear All', bg='#f0ad4e', fg='white', command=self.clear_all).pack(side='right', padx=8)

        self.add_section()

    def choose_target_dir(self):
        folder = filedialog.askdirectory(title='Chọn thư mục đích')
        if folder:
            self.target_dir.delete(0, tk.END)
            self.target_dir.insert(0, folder)

    def add_section(self):
        section = BannerSection(self.sections_frame, self.remove_section)
        self.sections.append(section)
        section.grid(len(self.sections) - 1)

    def remove_section(self, section):
        self.sections.remove(section)
        for index, sec in enumerate(self.sections):
            sec.grid(index)

    def clear_all(self):
        for section in list(self.sections):
            section.remove()
        self.sections.clear()
        self.add_section()

    def generate_all(self):
        target_dir = self.target_dir.get().strip()
        if not target_dir:
            messagebox.showwarning('Thiếu dữ liệu', 'Vui lòng chọn thư mục đích.')
            return

        target_dir = os.path.normpath(target_dir)
        os.makedirs(target_dir, exist_ok=True)

        banner_file = os.path.join(target_dir, 'AdsBanner.csv')
        popup_file = os.path.join(target_dir, 'AdsPopUp.csv')

        generated = 0
        errors = []

        for index, section in enumerate(self.sections, start=1):
            data = section.get_data()
            missing = [k for k, v in data.items() if k in ['BannerID', 'HeroName', 'AllyId', 'GachaJumpId', 'StartTime'] and not v]
            if missing:
                errors.append(f'Banner #{index}: Thiếu {", ".join(missing)}')
                continue

            try:
                build_banner_line(data)
            except ValueError as ex:
                errors.append(f'Banner #{index}: {ex}')
                continue

            banner_line = build_banner_line(data)
            append_to_file(banner_file, banner_line)
            if data['PopUpID']:
                popup_line = build_popup_line(data)
                append_to_file(popup_file, popup_line)
            generated += 1

        if errors:
            message = 'Một số banner chưa được sinh:\n' + '\n'.join(errors)
            messagebox.showwarning('Lỗi dữ liệu', message)
        else:
            messagebox.showinfo('Hoàn tất', f'Đã tạo {generated} banner vào {target_dir}')


if __name__ == '__main__':
    root = tk.Tk()
    app = GachaBatchApp(root)
    root.mainloop()
