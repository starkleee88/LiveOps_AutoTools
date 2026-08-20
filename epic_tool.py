#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import stat
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple



def find_original_bingo_row(target_dir: str, hero_name: str) -> Optional[List[str]]:
    path = os.path.join(target_dir, "ActivityBingo.csv")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > 1:
                    name = row[1].strip()
                    normalized_name = name.lower()
                    normalized_hero = hero_name.lower()
                    if normalized_hero in normalized_name and "bingo" in normalized_name and "rerun" not in normalized_name and "replica" not in normalized_name:
                        return row
    except Exception:
        pass
    return None


def find_original_newhero_row(target_dir: str, hero_name: str) -> Optional[List[str]]:
    path = os.path.join(target_dir, "ActivityNewHero.csv")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > 3:
                    hero = row[1].strip()
                    normalized_hero = hero.lower()
                    normalized_input = hero_name.lower()
                    if normalized_hero == normalized_input or (normalized_input in normalized_hero and "rerun" not in normalized_hero and "replica" not in normalized_hero):
                        return row
    except Exception:
        pass
    return None


def find_original_gacha_rows(target_dir: str, hero_name: str, ally_id: str, start_time: str) -> Tuple[Optional[List[str]], Optional[List[str]]]:
    type_path = os.path.join(target_dir, "AllyGachaType.csv")
    branch_path = os.path.join(target_dir, "AllyGachaBranch.csv")
    if not os.path.exists(type_path) or not os.path.exists(branch_path):
        return None, None
    try:
        with open(branch_path, "r", encoding="utf-8-sig", newline="") as f:
            branch_rows = list(csv.reader(f))
        branch_by_id = {row[0].strip(): row for row in branch_rows if len(row) > 0 and row[0].strip()}

        candidates = []
        with open(type_path, "r", encoding="utf-8-sig", newline="") as f:
            type_rows = list(csv.reader(f))

        hero_key = hero_name.lower().strip()
        for row in type_rows[1:]:
            if len(row) <= 11:
                continue
            display_name = row[1].strip()
            branch_id = row[2].strip()
            row_ally_id = row[7].strip()
            open_time = row[11].strip()

            display_lower = display_name.lower()
            if "rerun" in display_lower or "replica" in display_lower:
                continue
            if ally_id and row_ally_id != str(ally_id).strip():
                continue
            if hero_key not in display_lower:
                continue
            if not open_time or (start_time and open_time >= str(start_time).strip()):
                continue
            if branch_id not in branch_by_id:
                continue
            candidates.append((open_time, row, branch_by_id[branch_id]))

        if not candidates:
            return None, None

        candidates.sort(key=lambda item: item[0], reverse=True)
        latest_candidate = candidates[0]
        return latest_candidate[1], latest_candidate[2]
    except Exception:
        return None, None

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    from tkinter import ttk, font
except ImportError:
    tk = None

def get_config_file_path() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_name = "epic_tool_config.json"
    candidate = os.path.join(script_dir, config_name)
    if os.access(script_dir, os.W_OK):
        return candidate

    home_dir = os.path.expanduser("~")
    if home_dir and os.access(home_dir, os.W_OK):
        return os.path.join(home_dir, f".{config_name}")

    appdata_dir = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
    if appdata_dir and os.access(appdata_dir, os.W_OK):
        return os.path.join(appdata_dir, config_name)

    return candidate

CONFIG_FILE = get_config_file_path()


def load_config() -> Dict[str, str]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(data: Dict[str, object]) -> None:
    config_path = CONFIG_FILE
    try:
        config_dir = os.path.dirname(config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except PermissionError:
        # Fallback to user home if script folder is not writable.
        home_config = os.path.join(os.path.expanduser("~"), ".epic_tool_config.json")
        try:
            with open(home_config, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"Config saved to user home: {home_config}")
        except Exception as exc:
            print(f"Warning: failed to save config: {exc}")
    except Exception as exc:
        print(f"Warning: failed to save config: {exc}")

def parse_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except Exception:
        return default


@dataclass
class RewardRow:
    reward_id: str
    note: str
    item_id: str
    quantity: str
    extra: Dict[str, str] = field(default_factory=dict)


def parse_reward_csv(filepath: str) -> List[RewardRow]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Reward CSV not found: {filepath}")

    rows = []
    with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return rows
        # The reward files in this project have a second description row.
        second = next(reader, None)
        for row in reader:
            if not row or len(row) < 3:
                continue
            reward_id = row[1].strip() if len(row) > 1 else ""
            note = row[2].strip() if len(row) > 2 else ""
            if reward_id.lower() == "reward id" or reward_id.lower() == "int":
                continue
            item_id = row[6].strip() if len(row) > 6 else ""
            quantity = row[7].strip() if len(row) > 7 else ""
            extra = {header[i].strip(): row[i].strip() for i in range(min(len(header), len(row)))}
            rows.append(RewardRow(reward_id=reward_id, note=note, item_id=item_id, quantity=quantity, extra=extra))
    return rows


def find_reward(rows: Sequence[RewardRow], patterns: Sequence[str]) -> Optional[RewardRow]:
    lower = [p.lower() for p in patterns]
    for row in rows:
        note = row.note.lower()
        if all(p in note for p in lower):
            return row
    return None


def guess_gacha_epic_reward(rows: Sequence[RewardRow], hero_name: str) -> Optional[RewardRow]:
    hero_name = hero_name.lower()
    for row in rows:
        note = row.note.lower()
        if "banner" in note and hero_name in note and "epic" not in note:
            return row
        if "banner" in note and "epic" in note:
            return row
    return None


def normalize_activity_id(value: str) -> str:
    return str(value).strip()


def read_existing_row(path: str, row_id: str) -> Optional[List[str]]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].strip() == row_id:
                return row
    return None


def ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def write_csv_rows(path: str, rows: List[List[str]], header: Optional[List[str]] = None) -> None:
    ensure_dir(path)
    append_mode = os.path.exists(path)
    if append_mode and not os.access(path, os.W_OK):
        try:
            os.chmod(path, stat.S_IWRITE)
        except Exception:
            pass
    mode = "a" if append_mode else "w"
    try:
        with open(path, mode, encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, lineterminator="\r\n")
            if header and not append_mode:
                writer.writerow(header)
            elif header and append_mode and os.path.getsize(path) == 0:
                writer.writerow(header)
            writer.writerows(rows)
    except PermissionError:
        if os.path.exists(path):
            try:
                os.chmod(path, stat.S_IWRITE)
                with open(path, mode, encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f, lineterminator="\r\n")
                    if header and not append_mode:
                        writer.writerow(header)
                    elif header and append_mode and os.path.getsize(path) == 0:
                        writer.writerow(header)
                    writer.writerows(rows)
                return
            except Exception:
                pass
        raise


def make_activity_row(activity_id: str, activity_type: str, display_name: str, start_time: str, end_time: str, title_key: str, background: str, show_order: str, func_id: str = "", badge: str = "2") -> List[str]:
    return [
        activity_id,
        activity_type,
        display_name,
        start_time,
        end_time,
        "1",
        "530",
        show_order,
        title_key,
        background,
        badge,
        "",
        "",
        "",
        func_id,
    ]


def make_bingo_row(activity_id: str, hero_name: str, token1_id: str, token2_id: str, title_key: str, subtitle_key: str, title_img: str, rule_desc_id: str, locked_icon: str, unlocked_icon: str, mask_img: str, texture_img: str, frame_bg: str, frame_dec1: str, frame_dec2: str, frame_dec3: str, frame_icon1: str, frame_icon2: str, frame_icon3: str, frame_icon4: str, icon_bg1: str, icon_bg2: str, effect1: str, effect2: str, final_bg: str) -> List[str]:
    return [
        activity_id,
        hero_name,
        token1_id,
        token2_id,
        title_key,
        subtitle_key,
        title_img,
        rule_desc_id,
        locked_icon,
        unlocked_icon,
        mask_img,
        "",
        texture_img,
        frame_bg,
        frame_dec1,
        frame_dec2,
        frame_dec3,
        frame_icon1,
        frame_icon2,
        frame_icon3,
        frame_icon4,
        icon_bg1,
        icon_bg2,
        effect1,
        effect2,
        final_bg,
    ]


def make_newhero_row(activity_id: str, hero_name: str, title_key: str, hero_id: str, desc1: str, desc2: str, gacha_desc: str, gacha_jump: str, frame_bg: str, time_bg1: str, time_bg2: str, full_bg: str, other_icon1: str, other_name1: str, other_jump1: str) -> List[str]:
    return [
        activity_id,
        hero_name,
        title_key,
        hero_id,
        desc1,
        desc2,
        gacha_desc,
        "",
        "",
        "",
        "",
        gacha_jump,
        frame_bg,
        time_bg1,
        time_bg2,
        full_bg,
        other_icon1,
        other_name1,
        other_jump1,
        "",
        "",
        "",
    ]


def make_task_activity_rows(activity_id: str, task_base: int, hero_name: str, rerun: bool, token1_note: str, token2_note: str) -> List[List[str]]:
    rows = []
    prefix = f" {hero_name} Rerun" if rerun else f" {hero_name}"
    base_id = int(task_base)
    notes = [
        f"Bingo -{prefix} - D - Spend 6 {token1_note}",
        f"Bingo -{prefix} - D - Challenge a Convergence stage 1 time",
        f"Bingo -{prefix} - D - Challenge any Evil Falls enemy 1 time",
        f"Bingo -{prefix} - D - Win 15 Times in The Arena",
        f"Bingo -{prefix} - D - Use Quick Collect 2 times",
        f"Bingo -{prefix} - D - Level up a Character 5 times",
        f"Bingo -{prefix} - D - Upgrade a Reinforcement 5 times",
        f"Bingo -{prefix} - D - Upgrade Equipment 5 Times",
        f"Bingo -{prefix} - D - Recruit 1 Time in Limited Characters",
        f"Bingo -{prefix} - D - Recruit 10 Times in Limited Characters",
        f"Bingo -{prefix} - S - Spend 40 {token1_note}",
        f"Bingo -{prefix} - S - Challenge Convergence stages 10 times",
        f"Bingo -{prefix} - S - Clear Elseworld 4 times",
        f"Bingo -{prefix} - S - Win 15 Times in The Arena",
        f"Bingo -{prefix} - S - Collect Squad Dispatch rewards 20 times",
        f"Bingo -{prefix} - S - Recruit 100 Times in Limited Characters",
        f"Bingo -{prefix} - S - Rank up {hero_name} to Rank 4",
        f"Bingo -{prefix} - S - Rank up {hero_name} to Rank 5",
        f"Bingo -{prefix} - S - Rank up {hero_name} to Rank 6",
        f"Bingo -{prefix} - S - Rank up {hero_name} to Rank 7",
    ]
    for offset, note in enumerate(notes, start=1):
        rows.append([str(base_id + offset), activity_id, note])
    return rows


def make_task_info_rows(config: argparse.Namespace) -> List[List[str]]:
    rows = []
    base_id = int(config.task_base_id)
    notes = make_task_notes(config.hero_name, config.rerun, config.bingo_token1_name, config.bingo_token2_name)
    blueprint = [
        ("1", "103", "6", config.bingo_token1_id, config.task_reward_d_id, "", notes[0], "2", "5", "30", "", "1"),
        ("1", "12", "1", "2", config.task_reward_d_other_id, "", notes[1], "2", "4", "3", "300", "2"),
        ("1", "74", "1", "", config.task_reward_d_other_id, "", notes[2], "2", "3", "6", "800", "3"),
        ("1", "45", "3", "", config.task_reward_d_other_id, "", notes[3], "2", "5", "3", "107", "4"),
        ("1", "11", "2", "", config.task_reward_d_other_id, "", notes[4], "2", "1", "0", "202", "5"),
        ("1", "14", "5", "", config.task_reward_d_other_id, "", notes[5], "2", "1", "0", "103", "6"),
        ("1", "92", "5", "", config.task_reward_d_other_id, "", notes[6], "2", "4", "15", "113", "7"),
        ("1", "91", "5", "", config.task_reward_d_other_id, "", notes[7], "2", "2", "6", "103", "8"),
        ("1", "93", "1", config.gacha_type_id, config.task_reward_d_other_id, "", notes[8], "2", "1", "0", config.gacha_jump_id, "9"),
        ("1", "93", "10", config.gacha_type_id, config.task_reward_d_tenth_id, "", notes[9], "2", "1", "0", config.gacha_jump_id, "10"),
        ("0", "103", "30", config.bingo_token1_id, config.task_reward_s_id, "", notes[10], "2", "5", "30", "", "1"),
        ("0", "12", "7", "2", config.task_reward_s_id, "", notes[11], "2", "4", "3", "300", "2"),
        ("0", "313", "4", "", config.task_reward_s_id, "", notes[12], "2", "5", "9", "105", "3"),
        ("0", "45", "15", "", config.task_reward_s_id, "", notes[13], "2", "5", "3", "107", "4"),
        ("0", "105", "30", "", config.task_reward_s_id, "", notes[14], "2", "2", "6", "991801", "5"),
        ("0", "93", "100", config.gacha_type_id, config.task_reward_s_id, "", notes[15], "2", "1", "0", config.gacha_jump_id, "6"),
        ("0", "20", "4", config.ally_id, config.task_reward_s_id, "", notes[16], "2", "1", "0", "103", "7"),
        ("0", "20", "5", config.ally_id, config.task_reward_s_id, "", notes[17], "2", "1", "0", "103", "8"),
        ("0", "20", "6", config.ally_id, config.task_reward_s_id, "", notes[18], "2", "1", "0", "103", "9"),
        ("0", "20", "7", config.ally_id, config.task_reward_s_id, "", notes[19], "2", "1", "0", "103", "10"),
    ]
    for offset, entry in enumerate(blueprint, start=1):
        rst, cond, tgt, prm, reward_id, _, note, acc, chapter, point, dest, order = entry
        task_id = str(base_id + offset)
        task_name = f"TaskName_{task_id}"
        rows.append([
            task_id,
            note,
            "20",
            "7",
            rst,
            cond,
            tgt,
            prm,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            reward_id,
            task_name,
            "",
            "",
            acc,
            chapter,
            point,
            dest,
            order,
        ])
    return rows


def make_bingo_reward_rows(activity_id: str, reward_list: List[str]) -> List[List[str]]:
    rows = []
    for order, reward_id in enumerate(reward_list, start=1):
        rows.append([activity_id, str(order), "", reward_id])
    return rows


def make_bingo_stamp_rows(activity_id: str, token1_id: str, token2_id: str, reward_id: str) -> List[List[str]]:
    pattern = [token1_id, token2_id, token1_id, token2_id, token1_id, token2_id, token1_id, token2_id, token1_id]
    quantities = [6, 2, 6, 3, 6, 3, 6, 2, 6]
    rows = []
    for order, (token_id, quantity) in enumerate(zip(pattern, quantities), start=1):
        rows.append([activity_id, str(order), "", token_id, str(quantity), reward_id])
    return rows


def make_task_notes(hero_name: str, rerun: bool, token1_note: str, token2_note: str) -> List[str]:
    prefix = f" {hero_name} Rerun" if rerun else f" {hero_name}"
    return [
        f"Bingo -{prefix} - D - Spend 6 {token1_note}",
        f"Bingo -{prefix} - D - Challenge a Convergence stage 1 time",
        f"Bingo -{prefix} - D - Challenge any Evil Falls enemy 1 time",
        f"Bingo -{prefix} - D - Win 3 Times in The Arena",
        f"Bingo -{prefix} - D - Use Quick Collect 2 times",
        f"Bingo -{prefix} - D - Level up a Character 5 times",
        f"Bingo -{prefix} - D - Upgrade a Reinforcement 5 times",
        f"Bingo -{prefix} - D - Upgrade Equipment 5 Times",
        f"Bingo -{prefix} - D - Recruit 1 Time in Limited Characters",
        f"Bingo -{prefix} - D - Recruit 10 Times in Limited Characters",
        f"Bingo -{prefix} - S - Spend 40 {token1_note}",
        f"Bingo -{prefix} - S - Challenge Convergence stages 10 times",
        f"Bingo -{prefix} - S - Clear Elseworld 5 times",
        f"Bingo -{prefix} - S - Win 15 Times in The Arena",
        f"Bingo -{prefix} - S - Collect Squad Dispatch rewards 20 times",
        f"Bingo -{prefix} - S - Recruit 100 Times in Limited Characters",
        f"Bingo -{prefix} - S - Rank up {hero_name} to Rank 4",
        f"Bingo -{prefix} - S - Rank up {hero_name} to Rank 5",
        f"Bingo -{prefix} - S - Rank up {hero_name} to Rank 6",
        f"Bingo -{prefix} - S - Rank up {hero_name} to Rank 7",
    ]


def make_source_activity_ui_rows(config: argparse.Namespace, task_ids: List[str], task_notes: List[str]) -> List[List[str]]:
    rows = []
    bingo_title_key = f"ActivityBingoTitle{config.ally_id}"
    bingo_subtitle_key = f"ActivityBingoSubtitle{config.ally_id}"
    bingo_rule_key = f"ActivityBingoRuleDesc{config.ally_id}"
    
    rows.append([bingo_title_key, "Bingo", f"{config.hero_name} Event", f"[NOT FINAL] Bingo Title", ""])
    rows.append([bingo_subtitle_key, "Bingo Subtitle", f"{config.hero_name} Event", f"[NOT FINAL] Bingo Subtitle", ""])
    rows.append([bingo_rule_key, "Bingo Rule", f"{config.hero_name} Event", f"[NOT FINAL] Bingo Rule", ""])
    
    suffix = str(config.newhero_activity_id)[-2:]
    activity_newhero_title = f"ActivityNewHeroTitle{suffix}"
    rows.append([activity_newhero_title, "New Hero Activity", f"{config.hero_name} Event", "[NOT FINAL] New Hero Title", ""])
    
    popup_title = f"Popup_{config.ally_id}_title"
    popup_text = f"Popup_{config.ally_id}_text"
    popup_text_2 = f"Popup_{config.ally_id}_text_2"
    rows.append([popup_title, "Pop Up Title", f"{config.hero_name} Event", f"[NOT FINAL] {config.hero_name} Pop Up Title", ""])
    rows.append([popup_text, "Pop Up Description", f"{config.hero_name} Event", f"[NOT FINAL] {config.hero_name} Pop Up Text", ""])
    rows.append([popup_text_2, "Pop Up Description 2", f"{config.hero_name} Event", f"[NOT FINAL] {config.hero_name} Pop Up Text 2", ""])
    return rows


def make_source_common_ui_rows(config: argparse.Namespace) -> List[List[str]]:
    rows = []
    suffix = str(config.newhero_activity_id)[-2:]
    newhero_title_key = f"NewHeroTitle{suffix}"
    rows.append([newhero_title_key, "New Hero", f"{config.hero_name} Event", f"[NOT FINAL] New Hero Title"])
    rows.append([f"NewHeroDescribe{suffix}_1", "Gacha Skill Desc1", f"{config.hero_name} Event", f"[NOT FINAL] {config.hero_name} Gacha Skill Description 1"])
    rows.append([f"NewHeroDescribe{suffix}_2", "Gacha Skill Desc2", f"{config.hero_name} Event", f"[NOT FINAL] {config.hero_name} Gacha Skill Description 2"])
    rows.append([f"NewHeroGachaDescribe{suffix}", "Gacha Desc", f"{config.hero_name} Event", f"[NOT FINAL] {config.hero_name} Gacha Description"])
    return rows


def make_source_common_desc_rows(task_ids: List[str], task_notes: List[str]) -> List[List[str]]:
    rows = []
    for task_id, task_note in zip(task_ids, task_notes):
        task_note = re.sub(r"^Bingo -[^-]+ - [DS] -\s*", "", task_note)
        if "Spend 6" in task_note:
            task_note = f"[NOT FINAL] {task_note}"
        rows.append([f"TaskName_{task_id}", "Task", "Task description", task_note, "OBT版本"])
    return rows


def make_source_item_desc_rows(token1_id: str, token2_id: str, hero_name: str) -> List[List[str]]:
    rows = []
    rows.append([f"ItemName{token1_id}", f"{hero_name} Event", f"{hero_name} Common Token", f"[NOT FINAL] {hero_name} Token 1", ""])
    rows.append([f"ItemDesc{token1_id}", f"{hero_name} Event", f"{hero_name} Common Token", f"[NOT FINAL] Event currency used in {hero_name} Bingo", ""])
    rows.append([f"ItemName{token2_id}", f"{hero_name} Event", f"{hero_name} Rare Token", f"[NOT FINAL] {hero_name} Token 2", ""])
    rows.append([f"ItemDesc{token2_id}", f"{hero_name} Event", f"{hero_name} Rare Token", f"[NOT FINAL] Event currency used in {hero_name} Bingo", ""])
    return rows


def make_ads_banner_row(banner_id: str, hero_name: str, start_time: str, end_time: str, ally_id: str, gacha_jump_id: str) -> List[str]:
    return [banner_id, hero_name, start_time, end_time, "2", "530", f"ui_banner_{ally_id}", gacha_jump_id, "", "", "0"]


def make_ads_popup_row(popup_id: str, hero_name: str, start_time: str, end_time: str, ally_id: str, gacha_jump_id: str, show_order: str = "7", legal_text_key: str = "", button_key: str = "") -> List[str]:
    return [
        popup_id,
        hero_name,
        start_time,
        end_time,
        "2",
        "530",
        "",
        "",
        "",
        "",
        show_order,
        gacha_jump_id,
        "1",
        "1",
        "ui_popuppic_img_shuxing_bg",
        f"ui_popuppic_img_bg_{ally_id}_b",
        f"ui_recharg_img_timetxtbg_{ally_id}",
        ally_id,
        f"Popup_{ally_id}_title",
        "0e0e0e",
        "ffffff",
        "ffbb04",
        "145c8f",
        f"Popup_{ally_id}_text",
        f"Popup_{ally_id}_text_2",
        legal_text_key,
        button_key,
    ]


def make_jump_rows(hero_name: str, gacha_jump_id: str, gacha_type_id: str, shop_jump_id: str, shop_store_id: str, gacha_jump_text_key: Optional[str] = None) -> List[List[str]]:
    text_key = gacha_jump_text_key or f"AllyGachaName{gacha_type_id}"
    rows = [
        [
            gacha_jump_id,
            "8",
            f"Skip to Motherbox - {hero_name}",
            gacha_type_id,
            "",
            "",
            "",
            "",
            "1",
            "Corresponds to AllyGachaType table card pool ID",
            text_key,
            "",
            "1",
        ],
        [
            shop_jump_id,
            "25",
            f"[Store] - {hero_name} Offer",
            "4",
            shop_store_id,
            "",
            "",
            "",
            "0",
            "",
            "Func_fufeishangcheng",
            "COMMON_Ended",
            "1",
        ],
    ]
    return rows


def make_ally_gacha_type_row(gacha_type_id: str, hero_name: str, ally_id: str, start_time: str, end_time: str, gift_jump_id: str) -> List[str]:
    return [
        gacha_type_id,
        f"New Ally {hero_name} UP Banner",
        f"{gacha_type_id}1",
        "1",
        "1",
        "1",
        "1",
        ally_id,
        "",
        "",
        "",
        start_time,
        end_time,
        "1120015",
        "1",
        "200",
        "2000",
        "",
        "",
        "1501",
        "",
        "",
        "",
        "",
        "",
        "31",
        f"AllyGachaName{gacha_type_id}",
        "",
        "",
        "5",
        "30",
        "AllyGachaTab31",
        f"ui_drawcard_btn_{ally_id}",
        "ui_drawcard_img_bg03",
        f"ui_cardpool_{ally_id}",
        "",
        "907",
        "Gacha_UpDes4",
        gift_jump_id,
    ]


def make_ally_gacha_branch_row(gacha_branch_id: str, hero_name: str, ally_id: str) -> List[str]:
    return [
        gacha_branch_id,
        f"New Ally {hero_name} UP Banner",
        f"Better chance at {hero_name}",
        "1",
        ally_id,
        "3000",
        "5",
        "",
        "31",
        "31",
        "1",
        "-1",
        "1930001031|401;1904001304|301",
        "1904001204|3000;1904001104|4700",
    ]


def make_item_rows(token1_id: str, token2_id: str, hero_name: str, ally_id: str, target_dir: str, old_token1_id: Optional[str] = None, old_token2_id: Optional[str] = None) -> List[List[str]]:
    t1_name = f"ItemName{token1_id}"
    t1_desc = f"ItemDesc{token1_id}"
    t1_icon = f"ui_Bingo_icon01_{ally_id}"

    t2_name = f"ItemName{token2_id}"
    t2_desc = f"ItemDesc{token2_id}"
    t2_icon = f"ui_Bingo_icon02_{ally_id}"

    if old_token1_id:
        t1_name = f"ItemName{old_token1_id}"
        t1_desc = f"ItemDesc{old_token1_id}"
        old_row = read_existing_row(os.path.join(target_dir, "Item.csv"), old_token1_id)
        if old_row:
            t1_name = old_row[2] if len(old_row) > 2 else t1_name
            t1_desc = old_row[3] if len(old_row) > 3 else t1_desc
            t1_icon = old_row[19] if len(old_row) > 19 else t1_icon

    if old_token2_id:
        t2_name = f"ItemName{old_token2_id}"
        t2_desc = f"ItemDesc{old_token2_id}"
        old_row = read_existing_row(os.path.join(target_dir, "Item.csv"), old_token2_id)
        if old_row:
            t2_name = old_row[2] if len(old_row) > 2 else t2_name
            t2_desc = old_row[3] if len(old_row) > 3 else t2_desc
            t2_icon = old_row[19] if len(old_row) > 19 else t2_icon

    return [
        [
            token1_id,
            f"Bingo Token 1 - {hero_name}",
            t1_name,
            t1_desc,
            f"Used in {hero_name} Epic Event",
            "1",
            "",
            "",
            "",
            "1",
            "",
            "",
            "",
            "",
            "",
            "4",
            "4",
            "3",
            "17",
            t1_icon,
            "",
            "0",
            "",
            "",
            "",
            "9806",
        ],
        [
            token2_id,
            f"Bingo Token 2 - {hero_name}",
            t2_name,
            t2_desc,
            f"Used in {hero_name} Epic Event",
            "1",
            "",
            "",
            "",
            "1",
            "",
            "",
            "",
            "",
            "",
            "4",
            "4",
            "4",
            "18",
            t2_icon,
            "",
            "0",
            "",
            "",
            "",
            "9806",
        ],
    ]


def make_item_expiration_rows(token1_id: str, token2_id: str, end_time: str, activity_id: str) -> List[List[str]]:
    return [
        [token1_id, f"Bingo Token 1 - Ruthye", "1", end_time, "19120014", "10071", "Expire item for compensation", token1_id, activity_id],
        [token2_id, f"Bingo Token 2 - Ruthye", "1", end_time, "19120015", "10072", "Expire item for compensation", token2_id, activity_id],
    ]


def build_default_bingo_assets(ally_id: str) -> Dict[str, str]: 
    return {
        "bingo_title": f"ActivityBingoTitle{ally_id}",
        "subtitle": "BingoSubtitle01",
        "bg": "ui_Bingo_img_bg02",
        "rule_desc": "501",
        "locked_icon": f"ui_icon_heroheadillustration{ally_id}",
        "unlocked_icon": f"ui_icon_heroheadillustration{ally_id}",
        "mask_img": f"ui_Bingo_img_bg08_{ally_id}",
        "texture_img": f"ui_Bingo_img_bg09_{ally_id}",
        "frame_bg": f"ui_Bingo_img_bg04_{ally_id}",
        "frame_dec1": f"ui_Bingo_img_bg07_{ally_id}",
        "frame_dec2": f"ui_Bingo_img_bg06_{ally_id}",
        "frame_dec3": f"ui_Bingo_img_bg05_{ally_id}",
        "frame_icon1": f"ui_Bingo_icon06_{ally_id}",
        "frame_icon2": f"ui_Bingo_icon05_{ally_id}",
        "frame_icon3": f"ui_Bingo_icon04_{ally_id}",
        "frame_icon4": f"ui_Bingo_icon03_{ally_id}",
        "icon_bg1": f"ui_Bingo_img_bg01_{ally_id}",
        "icon_bg2": f"ui_Bingo_img_bg02_{ally_id}",
        "effect1": "VX_BingoRootPart_active_06",
        "effect2": "VX_BingoRootPart_Loop_red",
        "final_bg": f"ui_Bingo_img_bg03_{ally_id}",
    }


def build_default_newhero_assets(ally_id: str, activity_id: str) -> Dict[str, str]:
    suffix = str(activity_id)[-2:]
    return {
        "title": f"NewHeroTitle{suffix}" if suffix.isdigit() else "NewHeroTitleXX",
        "desc1": f"NewHeroDescribe{suffix}_1",
        "desc2": f"NewHeroDescribe{suffix}_2",
        "gacha_desc": f"NewHeroGachaDescribe{suffix}" if suffix.isdigit() else "NewHeroGachaDescribeXX",
        "frame_bg": f"ui_recharg_img_rightpanelbg_{ally_id}",
        "time_bg1": f"ui_recharg_img_timetxtbg01_{ally_id}",
        "time_bg2": f"ui_recharg_img_timetxtbg02_{ally_id}",
        "full_bg": "",
        "other_icon1": "ui_recharg_btn_xianshilibao",
        "other_name1": "NewHeroEventName2",
        "other_jump1": "",
    }

def collect_row_values(row: Optional[List[str]]) -> Dict[str, str]:
    if not row:
        return {}
    return {str(i): row[i] if i < len(row) else "" for i in range(len(row))}


def make_output_rows(config: argparse.Namespace, reward_rows: List[RewardRow]) -> Dict[str, List[List[str]]]:
    rows: Dict[str, List[List[str]]] = {}
    orig_gacha_type = None
    orig_gacha_branch = None
    
    # 1. Search for original rows by Hero Name in Rerun Mode
    if config.rerun:
        orig_bingo = find_original_bingo_row(config.target_dir, config.hero_name)
        if orig_bingo:
            config.reuse_source_bingo_id = orig_bingo[0]
        orig_newhero = find_original_newhero_row(config.target_dir, config.hero_name)
        if orig_newhero:
            config.reuse_source_newhero_id = orig_newhero[0]

        # Find closest gacha type and branch rows
        orig_gacha_type, orig_gacha_branch = find_original_gacha_rows(config.target_dir, config.hero_name, config.ally_id, config.start_time)

    reuse_bingo = None
    reuse_newhero = None

    if config.reuse_source_bingo_id:
        reuse_bingo = read_existing_row(os.path.join(config.target_dir, "ActivityBingo.csv"), config.reuse_source_bingo_id)
    if config.reuse_source_newhero_id:
        reuse_newhero = read_existing_row(os.path.join(config.target_dir, "ActivityNewHero.csv"), config.reuse_source_newhero_id)

    # Bingo Assets setup
    bingo_assets = build_default_bingo_assets(config.ally_id)
    if reuse_bingo:
        reuse_map = collect_row_values(reuse_bingo)
        old_ally_match = re.search(r'\d+', reuse_map.get("4", ""))
        old_ally_id = old_ally_match.group() if old_ally_match else "13268"

        def clean_bingo_val(val: str) -> str:
            if not val:
                return val
            if config.rerun:
                return val
            return val.replace(old_ally_id, config.ally_id)

        bingo_assets.update({
            "bingo_title": clean_bingo_val(reuse_map.get("4", bingo_assets["bingo_title"])),
            "subtitle": clean_bingo_val(reuse_map.get("5", bingo_assets["subtitle"])),
            "bg": clean_bingo_val(reuse_map.get("6", bingo_assets["bg"])),
            "rule_desc": clean_bingo_val(reuse_map.get("7", bingo_assets["rule_desc"])),
            "locked_icon": clean_bingo_val(reuse_map.get("8", bingo_assets["locked_icon"])),
            "unlocked_icon": clean_bingo_val(reuse_map.get("9", bingo_assets["unlocked_icon"])),
            "mask_img": clean_bingo_val(reuse_map.get("10", bingo_assets["mask_img"])),
            "texture_img": clean_bingo_val(reuse_map.get("12", bingo_assets["texture_img"])),
            "frame_bg": clean_bingo_val(reuse_map.get("13", bingo_assets["frame_bg"])),
            "frame_dec1": clean_bingo_val(reuse_map.get("14", bingo_assets["frame_dec1"])),
            "frame_dec2": clean_bingo_val(reuse_map.get("15", bingo_assets["frame_dec2"])),
            "frame_dec3": clean_bingo_val(reuse_map.get("16", bingo_assets["frame_dec3"])),
            "frame_icon1": clean_bingo_val(reuse_map.get("17", bingo_assets["frame_icon1"])),
            "frame_icon2": clean_bingo_val(reuse_map.get("18", bingo_assets["frame_icon2"])),
            "frame_icon3": clean_bingo_val(reuse_map.get("19", bingo_assets["frame_icon3"])),
            "frame_icon4": clean_bingo_val(reuse_map.get("20", bingo_assets["frame_icon4"])),
            "icon_bg1": clean_bingo_val(reuse_map.get("21", bingo_assets["icon_bg1"])),
            "icon_bg2": clean_bingo_val(reuse_map.get("22", bingo_assets["icon_bg2"])),
            "effect1": clean_bingo_val(reuse_map.get("23", bingo_assets["effect1"])),
            "effect2": clean_bingo_val(reuse_map.get("24", bingo_assets["effect2"])),
            "final_bg": clean_bingo_val(reuse_map.get("25", bingo_assets["final_bg"])),
        })

    # NewHero Assets setup
    newhero_assets = build_default_newhero_assets(config.ally_id, config.newhero_activity_id)
    if reuse_newhero:
        reuse_map = collect_row_values(reuse_newhero)
        old_ally_id = reuse_newhero[3].strip() if len(reuse_newhero) > 3 else "13268"
        old_suffix = str(reuse_newhero[0])[-2:]
        new_suffix = str(config.newhero_activity_id)[-2:]

        def clean_newhero_val(val: str) -> str:
            if not val:
                return val
            if config.rerun:
                return val
            val = val.replace(old_ally_id, config.ally_id)
            val = re.sub(r'(\w*)' + old_suffix, r'\g<1>' + new_suffix, val)
            return val

        newhero_assets.update({
            "title": clean_newhero_val(reuse_map.get("2", newhero_assets["title"])),
            "desc1": clean_newhero_val(reuse_map.get("4", newhero_assets["desc1"])),
            "desc2": clean_newhero_val(reuse_map.get("5", newhero_assets["desc2"])),
            "gacha_desc": clean_newhero_val(reuse_map.get("6", newhero_assets["gacha_desc"])),
            "frame_bg": clean_newhero_val(reuse_map.get("12", newhero_assets["frame_bg"])),
            "time_bg1": clean_newhero_val(reuse_map.get("13", newhero_assets["time_bg1"])),
            "time_bg2": clean_newhero_val(reuse_map.get("14", newhero_assets["time_bg2"])),
            "full_bg": clean_newhero_val(reuse_map.get("15", newhero_assets["full_bg"])),
            "other_icon1": clean_newhero_val(reuse_map.get("16", newhero_assets["other_icon1"])),
            "other_name1": clean_newhero_val(reuse_map.get("17", newhero_assets["other_name1"])),
            "other_jump1": clean_newhero_val(reuse_map.get("18", newhero_assets["other_jump1"])),
        })

    reward_map = {
        "token1": find_reward(reward_rows, ["reward 1 bingo", "token 1"]),
        "token2": find_reward(reward_rows, ["reward 2 bingo", "token 2"]),
        "full_board": find_reward(reward_rows, ["full board reward"]),
        "gacha_epic": guess_gacha_epic_reward(reward_rows, config.hero_name),
    }

    if not config.bingo_token1_id and reward_map["token1"]:
        config.bingo_token1_id = reward_map["token1"].item_id
    if not config.bingo_token2_id and reward_map["token2"]:
        config.bingo_token2_id = reward_map["token2"].item_id
    if not getattr(config, "gacha_epic_id", "") and reward_map["gacha_epic"]:
        config.gacha_epic_id = reward_map["gacha_epic"].reward_id

    bingo_activity_display_name = f"Bingo – {config.hero_name} Rerun" if config.rerun else f"Bingo – {config.hero_name}"
    newhero_display_name = f"New Hero - {config.hero_name} Rerun" if config.rerun else f"New Hero - {config.hero_name}"
    bingo_sheet_name = f"Bingo - {config.hero_name} Rerun" if config.rerun else f"Bingo - {config.hero_name}"

    activity_newhero_title = f"ActivityNewHeroTitle{str(config.newhero_activity_id)[-2:]}"
    newhero_background = config.newhero_background or f"ui_recharg_img_bg_{config.ally_id}"
    
    activity_bingo_title = bingo_assets["bingo_title"]
    bingo_background = config.bingo_background or f"ui_Bingo_img_bg_{config.ally_id}_01"

    if config.rerun:
        if config.reuse_source_newhero_id:
            old_act_newhero = read_existing_row(os.path.join(config.target_dir, "Activity.csv"), config.reuse_source_newhero_id)
            if old_act_newhero:
                activity_newhero_title = old_act_newhero[8] if len(old_act_newhero) > 8 else activity_newhero_title
                newhero_background = old_act_newhero[9] if len(old_act_newhero) > 9 else newhero_background
        
        if config.reuse_source_bingo_id:
            old_act_bingo = read_existing_row(os.path.join(config.target_dir, "Activity.csv"), config.reuse_source_bingo_id)
            if old_act_bingo:
                activity_bingo_title = old_act_bingo[8] if len(old_act_bingo) > 8 else activity_bingo_title
                bingo_background = old_act_bingo[9] if len(old_act_bingo) > 9 else bingo_background

    rows["Activity.csv"] = [make_activity_row(
        config.newhero_activity_id,
        "2",
        newhero_display_name,
        config.start_time,
        config.end_time,
        activity_newhero_title,
        newhero_background,
        "5",
        "",
    ), make_activity_row(
        config.bingo_activity_id,
        "1",
        bingo_activity_display_name,
        config.start_time,
        config.end_time,
        activity_bingo_title,
        bingo_background,
        "6",
        config.bingo_func_id,
    )]

    if config.rerun and reuse_bingo:
        bingo_row = list(reuse_bingo)
        bingo_row[0] = config.bingo_activity_id
        bingo_row[1] = bingo_sheet_name
        if len(bingo_row) > 2:
            bingo_row[2] = config.bingo_token1_id
        if len(bingo_row) > 3:
            bingo_row[3] = config.bingo_token2_id
        rows["ActivityBingo.csv"] = [bingo_row]
    else:
        rows["ActivityBingo.csv"] = [make_bingo_row(
            config.bingo_activity_id,
            bingo_sheet_name,
            config.bingo_token1_id,
            config.bingo_token2_id,
            bingo_assets["bingo_title"],
            bingo_assets["subtitle"],
            bingo_assets["bg"],
            bingo_assets["rule_desc"],
            bingo_assets["locked_icon"],
            bingo_assets["unlocked_icon"],
            bingo_assets["mask_img"],
            bingo_assets["texture_img"],
            bingo_assets["frame_bg"],
            bingo_assets["frame_dec1"],
            bingo_assets["frame_dec2"],
            bingo_assets["frame_dec3"],
            bingo_assets["frame_icon1"],
            bingo_assets["frame_icon2"],
            bingo_assets["frame_icon3"],
            bingo_assets["frame_icon4"],
            bingo_assets["icon_bg1"],
            bingo_assets["icon_bg2"],
            bingo_assets["effect1"],
            bingo_assets["effect2"],
            bingo_assets["final_bg"],
        )]

    other_jump1 = config.shop_jump_id or config.newhero_other_jump1_id or newhero_assets["other_jump1"]
    if config.rerun and not other_jump1 and config.gacha_jump_id.isdigit():
        other_jump1 = str(int(config.gacha_jump_id) + 1)

    if config.rerun and reuse_newhero:
        newhero_row = list(reuse_newhero)
        newhero_row[0] = config.newhero_activity_id
        if len(newhero_row) > 11:
            newhero_row[11] = config.gacha_jump_id
        if len(newhero_row) > 18:
            newhero_row[18] = other_jump1
        rows["ActivityNewHero.csv"] = [newhero_row]
    else:
        rows["ActivityNewHero.csv"] = [make_newhero_row(
            config.newhero_activity_id,
            config.hero_name,
            newhero_assets["title"],
            config.ally_id,
            newhero_assets["desc1"],
            newhero_assets["desc2"],
            newhero_assets["gacha_desc"],
            config.gacha_jump_id,
            newhero_assets["frame_bg"],
            newhero_assets["time_bg1"],
            newhero_assets["time_bg2"],
            newhero_assets["full_bg"],
            newhero_assets["other_icon1"],
            newhero_assets["other_name1"],
            other_jump1,
        )]

    if config.generate_task_files:
        rows["TaskActivity.csv"] = make_task_activity_rows(config.bingo_activity_id, config.task_base_id, config.hero_name, config.rerun, config.bingo_token1_name, config.bingo_token2_name)
        rows["TaskInfo.csv"] = make_task_info_rows(config)

    if config.bingo_reward_base_id:
        reward_ids = [str(config.bingo_reward_base_id + i) for i in range(7)]
        rows["ActivityBingoReward.csv"] = make_bingo_reward_rows(config.bingo_activity_id, reward_ids)

    if config.bingo_stamp_reward_id:
        rows["ActivityBingoStamp.csv"] = make_bingo_stamp_rows(config.bingo_activity_id, config.bingo_token1_id, config.bingo_token2_id, config.bingo_stamp_reward_id)

    rows["AdsBanner.csv"] = [make_ads_banner_row(
        config.ads_banner_id,
        config.hero_name,
        config.start_time,
        config.end_time,
        config.ally_id,
        config.gacha_jump_id,
    )]

    legal_text_key = config.popup_legal_text_key.format(ally_id=config.ally_id)
    popup_rows = [make_ads_popup_row(
        config.ads_popup_id,
        config.hero_name,
        config.start_time,
        config.end_time,
        config.ally_id,
        config.gacha_jump_id,
        legal_text_key=legal_text_key,
    )]
    rows["AdsPopUp.csv"] = popup_rows

    rows["Jump.csv"] = make_jump_rows(
        config.hero_name,
        config.gacha_jump_id,
        config.gacha_type_id,
        config.shop_jump_id,
        config.shop_store_id,
        gacha_jump_text_key=config.gacha_jump_text_key or None,
    )

    if config.rerun and orig_gacha_type and orig_gacha_branch:
        gtype_row = list(orig_gacha_type)
        gtype_row[0] = config.gacha_type_id
        if len(gtype_row) > 2:
            gtype_row[2] = config.gacha_branch_id
        if len(gtype_row) > 11:
            gtype_row[11] = config.start_time
        if len(gtype_row) > 12:
            gtype_row[12] = config.end_time
        if len(gtype_row) > 38:
            gtype_row[38] = config.gift_jump_id
        rows["AllyGachaType.csv"] = [gtype_row]

        gbranch_row = list(orig_gacha_branch)
        gbranch_row[0] = config.gacha_branch_id
        rows["AllyGachaBranch.csv"] = [gbranch_row]
    else:
        rows["AllyGachaType.csv"] = [make_ally_gacha_type_row(
            config.gacha_type_id,
            config.hero_name,
            config.ally_id,
            config.start_time,
            config.end_time,
            config.gift_jump_id,
        )]

        rows["AllyGachaBranch.csv"] = [make_ally_gacha_branch_row(
            config.gacha_branch_id,
            config.hero_name,
            config.ally_id,
        )]

    old_token1_id = None
    old_token2_id = None
    if config.rerun and reuse_bingo:
        old_token1_id = reuse_bingo[2] if len(reuse_bingo) > 2 else None
        old_token2_id = reuse_bingo[3] if len(reuse_bingo) > 3 else None

    rows["Item.csv"] = make_item_rows(
        config.bingo_token1_id,
        config.bingo_token2_id,
        config.hero_name,
        config.ally_id,
        config.target_dir,
        old_token1_id,
        old_token2_id,
    )

    rows["ItemExpiration.csv"] = make_item_expiration_rows(
        config.bingo_token1_id,
        config.bingo_token2_id,
        config.end_time,
        config.bingo_activity_id,
    )

    return rows


def default_headers() -> Dict[str, List[str]]:
    return {
        "Activity.csv": ["ActivityID", "ActivityType", "O", "StartTime", "EndTime", "Unlock", "UnlockParam", "ShowOrder", "ActivityTitle", "BackGround", "Badge", "RuleDescKey", "OpenType", "OpenParam", "FuncId"],
        "ActivityBingo.csv": [
            "ActivityID", "Name", "Activity Token 1", "Activity Token 2", "BingoTitle", "BingoSubtitle", "BingoTitleImg", "BingoRuleDescID", "BingoPicLocked", "BingoPicUnlocked", "MaskImg", "MaskGradient", "TextureImg", "BingoFrame", "FrameDec1", "FrameDec2", "FrameDec3", "FrameIcon1", "FrameIcon2", "FrameIcon3", "FrameIcon4", "IconBg01", "IconBg02", "Effect1", "Effect2", "FinalRewardBg01",
        ],
        "ActivityNewHero.csv": [
            "ActivityID", "Hero", "Title", "Hero", "Describe1", "Describe2", "GachaDescribe", "GachaPride1", "GachaPrideDescribe1", "GachaPride2", "GachaPrideDescribe2", "GachaJump", "FrameBackground", "TimeBackground1", "TimeBackground2", "FullScreenBackground", "OtherEventIcon1", "OtherEventName1", "OtherEventJump1", "OtherEventIcon2", "OtherEventName2", "OtherEventJump2",
        ],
        "TaskActivity.csv": ["ID", "ActivityID", "O"],
        "TaskInfo.csv": ["Id", "O", "TaskGroup", "TaskType", "RestartType", "Condition", "TargetPoint", "Param", "Param", "Param", "Param", "Param", "Param", "DateParam", "DateParam", "Reward", "TaskName", "Front", "Next", "Accumulation", "OpenAdventureChapter", "OpenAdventurePoint", "Destination", "ShowOrder"],
        "ActivityBingoReward.csv": ["ActivityID", "RewardOrder", "O", "RewardID"],
        "ActivityBingoStamp.csv": ["ActivityID", "StampOrder", "O", "TokenID", "TokenNum", "RewardID"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Epic event CSV rows for Ruthye-like events.")
    parser.add_argument("--target-dir", default="excel", help="Excel folder root")
    parser.add_argument("--reward-file", default="excel/Rewards/Reward_Ruthye.csv", help="Reward CSV source file")
    parser.add_argument("--hero-name", default="Ruthye", help="Hero name")
    parser.add_argument("--ally-id", default="13268", help="Hero ally ID")
    parser.add_argument("--bingo-activity-id", default="1024", help="New Bingo ActivityID")
    parser.add_argument("--newhero-activity-id", default="2024", help="New NewHero ActivityID")
    parser.add_argument("--start-time", default="20260620_000000", help="Event start time")
    parser.add_argument("--end-time", default="20260625_000000", help="Event end time")
    parser.add_argument("--gacha-jump-id", default="1143", help="Gacha Jump ID for New Hero row")
    parser.add_argument("--ads-banner-id", default="61", help="Banner ID for AdsBanner.csv")
    parser.add_argument("--ads-popup-id", default="65", help="Popup ID for AdsPopUp.csv")
    parser.add_argument("--shop-jump-id", default="1362", help="Jump ID for store offers in Jump.csv")
    parser.add_argument("--shop-store-id", default="9459", help="Store ID for shop offers in Jump.csv")
    parser.add_argument("--gacha-type-id", default="116", help="Gacha type ID for AllyGachaType.csv")
    parser.add_argument("--gacha-branch-id", default="11601", help="Gacha branch ID for AllyGachaBranch.csv")
    parser.add_argument("--gift-jump-id", default="1362", help="Gift Jump ID for AllyGachaType.csv")
    parser.add_argument("--popup-legal-text-key", default="Popup_{ally_id}_legal_text", help="Legal text key for AdsPopUp.csv; use {ally_id} placeholder")
    parser.add_argument("--gacha-jump-text-key", default="", help="Text key for the Gacha Jump row in Jump.csv")
    parser.add_argument("--bingo-func-id", default="9806", help="FuncId for Bingo Activity.csv row")
    parser.add_argument("--task-base-id", default="4090170", help="Task base ID for TaskActivity/TaskInfo")
    parser.add_argument("--task-reward-d-id", default="19120548", help="Reward ID used for the first D task in TaskInfo")
    parser.add_argument("--task-reward-d-other-id", default="19120570", help="Reward ID used for other D tasks in TaskInfo")
    parser.add_argument("--task-reward-d-tenth-id", default="19120549", help="Reward ID used for the 10th D task in TaskInfo")
    parser.add_argument("--task-reward-s-id", default="19120571", help="Reward ID used for S tasks in TaskInfo")
    parser.add_argument("--bingo-reward-base-id", type=int, default=0, help="Optional base reward ID for ActivityBingoReward rows")
    parser.add_argument("--bingo-stamp-reward-id", default="19120510", help="RewardID used for all ActivityBingoStamp entries")
    parser.add_argument("--bingo-token1-id", default="11114048", help="Item ID for bingo token 1")
    parser.add_argument("--bingo-token2-id", default="11114049", help="Item ID for bingo token 2")
    parser.add_argument("--bingo-token1-name", default="Ruthye Token 1 Name", help="Display name for bingo token 1 in task text")
    parser.add_argument("--bingo-token2-name", default="Ruthye Token 2 Name", help="Display name for bingo token 2 in task text")
    parser.add_argument("--newhero-other-jump1-id", default="1362", help="Other event jump ID for NewHero row")
    parser.add_argument("--bingo-background", default="", help="Optional Bingo Activity background override")
    parser.add_argument("--newhero-background", default="", help="Optional NewHero Activity background override")
    parser.add_argument("--reuse-source-bingo-id", default="1024", help="Source Bingo event ID to copy text IDs and assets from")
    parser.add_argument("--reuse-source-newhero-id", default="2024", help="Source NewHero event ID to copy text IDs and assets from")
    parser.add_argument("--generate-task-files", action="store_true", help="Generate TaskActivity.csv and TaskInfo.csv rows")
    parser.add_argument("--generate-language-files", action="store_true", help="Generate placeholder language CSV files")
    parser.add_argument("--rerun", action="store_true", help="Generate rerun-style task names and text references")
    parser.add_argument("--debug", action="store_true", help="Print parsed reward values for debugging")
    parser.add_argument("--validate-source", action="store_true", help="Validate generated outputs against target excel files in --target-dir")
    return parser.parse_args()


def get_writable_output_dir(target_dir: str) -> str:
    resolved_target = os.path.abspath(target_dir)
    try:
        os.makedirs(resolved_target, exist_ok=True)
    except Exception:
        pass
    return resolved_target


def get_fallback_output_dir() -> str:
    fallback_dir = os.path.join(tempfile.gettempdir(), "epic_event_output")
    try:
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir
    except Exception:
        pass

    backup_dir = os.path.join(os.path.expanduser("~"), "EpicEventOutput")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def is_writable_path(path: str) -> bool:
    if os.path.exists(path):
        return os.access(path, os.W_OK)
    directory = os.path.dirname(path) or "."
    return os.access(directory, os.W_OK)


def attempt_write_outputs(target_dir: str, outputs: Dict[str, List[List[str]]], headers: Dict[str, List[str]]) -> None:
    for name, rows in outputs.items():
        path = os.path.join(target_dir, name)
        header_row = headers.get(name) if name.startswith("Language/") else None
        try:
            write_csv_rows(path, rows, header=header_row)
        except PermissionError as exc:
            print(f"Permission denied writing {path}: {exc}")
            raise
        except OSError as exc:
            print(f"OS error writing {path}: {exc}")
            raise
        print(f" - {name}: {len(rows)} rows")


def write_generated_outputs(config: argparse.Namespace, reward_rows: List[RewardRow]) -> str:
    outputs = make_output_rows(config, reward_rows)
    headers = default_headers()
    target_dir = get_writable_output_dir(config.target_dir)
    original_target = os.path.abspath(config.target_dir)
    if target_dir != original_target:
        print(f"Warning: target directory '{original_target}' is not writable. Using fallback output folder '{target_dir}'.")
    else:
        print(f"Writing generated CSVs to {target_dir}")

    try:
        attempt_write_outputs(target_dir, outputs, headers)
    except (PermissionError, OSError) as exc:
        fallback_dir = get_fallback_output_dir()
        print(f"Warning: unable to write to '{target_dir}' ({exc}). Falling back to '{fallback_dir}'.")
        target_dir = fallback_dir
        attempt_write_outputs(target_dir, outputs, headers)

    if config.generate_language_files:
        task_ids = [str(int(config.task_base_id) + i) for i in range(1, 21)]
        task_notes = make_task_notes(config.hero_name, config.rerun, config.bingo_token1_name, config.bingo_token2_name)
        if not config.rerun:
            write_csv_rows(os.path.join(target_dir, "Language/SourceActivityUI.csv"), make_source_activity_ui_rows(config, task_ids, task_notes), header=["Key", "Module", "Explanation", "en", ""])
            write_csv_rows(os.path.join(target_dir, "Language/SourceCommonUI.csv"), make_source_common_ui_rows(config), header=["Key", "Module", "Explanation", "en"])
            write_csv_rows(os.path.join(target_dir, "Language/SourceItemDesc.csv"), make_source_item_desc_rows(config.bingo_token1_id, config.bingo_token2_id, config.hero_name), header=["Key", "Module", "Explanation", "en", "Version"])
            print(" - Language/SourceActivityUI.csv: generated")
            print(" - Language/SourceCommonUI.csv: generated")
            print(" - Language/SourceItemDesc.csv: generated")
        write_csv_rows(os.path.join(target_dir, "Language/SourceCommonDesc.csv"), make_source_common_desc_rows(task_ids, task_notes), header=["Key", "Module", "Explanation", "en", "Version"])
        print(" - Language/SourceCommonDesc.csv: generated")

    print("Generated Epic event rows successfully.")

    if getattr(config, "validate_source", False):
        validate_generated_outputs(config, outputs)

    return target_dir


def validate_generated_outputs(config: argparse.Namespace, outputs: Dict[str, List[List[str]]]) -> None:
    """Validate generated CSV rows against source files in config.target_dir.

    Comparison strategies:
    - Default: compare rows grouped by the first column (ID). If multiple rows share the same ID, compare lists elementwise in source order.
    - For ActivityBingoStamp.csv: compare by (ActivityID, StampOrder) to ensure stamp ordering and values match.
    """
    def rows_to_map(rows: List[List[str]], key_idx: int = 0) -> Dict[str, List[List[str]]]:
        m: Dict[str, List[List[str]]] = {}
        for r in rows:
            if not r:
                continue
            k = r[key_idx] if len(r) > key_idx else ""
            m.setdefault(k, []).append(r)
        return m

    def compare_groups(name: str, gen_group: List[List[str]], src_group: List[List[str]]) -> None:
        if len(gen_group) != len(src_group):
            print(f"VALIDATE {name}: count mismatch for ID {gen_group[0][0] if gen_group else ''} src={len(src_group)} gen={len(gen_group)}")
        # Compare elementwise up to the shorter length
        for i, (g, s) in enumerate(zip(gen_group, src_group), start=1):
            if g != s:
                print(f"VALIDATE {name}: row #{i} for ID {g[0]} differs")
                for j, (sv, gv) in enumerate(zip(s, g)):
                    if sv != gv:
                        print(f"  col {j}: src={sv!r} gen={gv!r}")
                        break

    tgt_dir = os.path.abspath(config.target_dir)
    print(f"Validating generated CSVs in {tgt_dir}")

    for name, gen_rows in outputs.items():
        src_path = os.path.join(config.target_dir, name)
        gen_path = os.path.join(config.target_dir, name)
        if not os.path.exists(gen_path):
            print(f"VALIDATE {name}: generated file missing: {gen_path}")
            continue
        if not os.path.exists(src_path):
            print(f"VALIDATE {name}: source file missing: {src_path}")
            continue
        with open(gen_path, encoding="utf-8-sig", newline="") as f:
            gen = [r for r in csv.reader(f) if r]
        with open(src_path, encoding="utf-8-sig", newline="") as f:
            src = [r for r in csv.reader(f) if r]

        # Special handling for ActivityBingoStamp: use (ActivityID, StampOrder)
        if name == "ActivityBingoStamp.csv":
            # build maps keyed by composite key
            gen_map: Dict[str, List[List[str]]] = {}
            src_map: Dict[str, List[List[str]]] = {}
            for r in gen:
                if len(r) > 1:
                    key = f"{r[0]}|{r[1]}"
                    gen_map.setdefault(key, []).append(r)
            for r in src:
                if len(r) > 1:
                    key = f"{r[0]}|{r[1]}"
                    src_map.setdefault(key, []).append(r)
            # compare each generated composite key
            for key, grows in gen_map.items():
                srows = src_map.get(key)
                if srows is None:
                    print(f"VALIDATE {name}: generated key {key} not in source")
                else:
                    compare_groups(name, grows, srows)
            continue

        # Default: group by first column and compare lists
        gen_map = rows_to_map(gen, 0)
        src_map = rows_to_map(src, 0)
        for k, grows in gen_map.items():
            srows = src_map.get(k)
            if srows is None:
                print(f"VALIDATE {name}: generated ID {k} not in source")
                continue
            compare_groups(name, grows, srows)



def build_config_from_gui(values: Dict[str, str], flags: Dict[str, bool]) -> argparse.Namespace:
    # Derive gacha branch by appending '1' to the gacha type id (e.g. 116 -> 1161)
    gtype = values.get("gacha_type_id", "116")
    gtype_str = str(gtype).strip()
    gbranch = values.get("gacha_branch_id") or (gtype_str + "1")
    return argparse.Namespace(
        target_dir=values.get("target_dir", "excel"),
        reward_file=values.get("reward_file", "excel/Rewards/Reward_Ruthye.csv"),
        hero_name=values.get("hero_name", "Ruthye"),
        ally_id=values.get("ally_id", "13268"),
        bingo_activity_id=values.get("bingo_activity_id", "11024"),
        newhero_activity_id=values.get("newhero_activity_id", "12024"),
        start_time=values.get("start_time", "20260718_000000"),
        end_time=values.get("end_time", "20260721_000000"),
        gacha_jump_id=values.get("gacha_jump_id", "1374"),
        ads_banner_id=values.get("ads_banner_id", "61"),
        ads_popup_id=values.get("ads_popup_id", "65"),
        shop_jump_id=values.get("iap_jump_id", values.get("shop_jump_id", "1362")),
        shop_store_id=values.get("iap_store_id", values.get("shop_store_id", "9459")),
        gift_jump_id=values.get("iap_jump_id", values.get("gift_jump_id", "1362")),
        # Bingo FuncId is fixed to 9806 per convention; GUI does not provide it
        bingo_func_id="9806",
        # include gacha type and derived branch
        gacha_type_id=gtype_str,
        gacha_branch_id=gbranch,
        task_base_id=values.get("task_base_id", "4090170"),
        task_reward_d_id=values.get("task_reward_d_id", "19120548"),
        task_reward_d_other_id=values.get("task_reward_d_other_id", "19120570"),
        task_reward_d_tenth_id=values.get("task_reward_d_tenth_id", "19120549"),
        task_reward_s_id=values.get("task_reward_s_id", "19120571"),
        bingo_reward_base_id=int(values.get("bingo_reward_base_id", "0") or 0),
        bingo_stamp_reward_id=values.get("bingo_stamp_reward_id", "19120510"),
        bingo_token1_id=values.get("bingo_token1_id", ""),
        bingo_token2_id=values.get("bingo_token2_id", ""),
        bingo_token1_name=values.get("bingo_token1_name") or f"{values.get('hero_name', 'Ruthye')} Token 1 Name",
        bingo_token2_name=values.get("bingo_token2_name") or f"{values.get('hero_name', 'Ruthye')} Token 2 Name",
        newhero_other_jump1_id=values.get("newhero_other_jump1_id", ""),
        bingo_background=values.get("bingo_background", ""),
        newhero_background=values.get("newhero_background", ""),
        popup_legal_text_key=values.get("popup_legal_text_key", "Popup_{ally_id}_legal_text"),
        gacha_jump_text_key=values.get("gacha_jump_text_key", ""),
        reuse_source_bingo_id=values.get("reuse_source_bingo_id", "1024"),
        reuse_source_newhero_id=values.get("reuse_source_newhero_id", "2024"),
        generate_task_files=flags.get("generate_task_files", False),
        generate_language_files=flags.get("generate_language_files", False),
        rerun=flags.get("rerun", False),
        debug=False,
    )


def main() -> None:
    config = parse_args()
    reward_rows = parse_reward_csv(config.reward_file)
    write_generated_outputs(config, reward_rows)


def run_gui() -> None:
    if tk is None:
        print("Tkinter is not available. Use CLI instead.")
        main()
        return

    window = tk.Tk()
    window.title("Epic Event Generator")
    window.geometry("820x650")

    def choose_reward_file(entry_widget: tk.Entry) -> None:
        filepath = filedialog.askopenfilename(title="Chọn file Reward CSV", filetypes=[("CSV files", "*.csv")])
        if filepath:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filepath)

    def choose_target_dir(entry_widget: tk.Entry) -> None:
        path = filedialog.askdirectory(title="Chọn thư mục đích")
        if path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)

    def create_row(parent: tk.Widget, label: str, default: str, browse_callback=None) -> tk.Entry:
        frame = ttk.Frame(parent)
        frame.pack(fill='x', padx=12, pady=6)
        lbl = ttk.Label(frame, text=label)
        lbl.grid(row=0, column=0, sticky='w')
        entry = ttk.Entry(frame)
        entry.insert(0, default)
        entry.grid(row=0, column=1, sticky='ew', padx=(8, 0))
        if browse_callback:
            btn = ttk.Button(frame, text="Browse", command=lambda: browse_callback(entry))
            btn.grid(row=0, column=2, padx=(8, 0))
        frame.columnconfigure(1, weight=1)
        return entry

    def make_scrollable(parent: tk.Widget) -> tk.Widget:
        canvas = tk.Canvas(parent, borderwidth=0, background='#f6f7fb', highlightthickness=0)
        vscroll = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=inner, anchor='nw')

        def _on_configure(event):
            canvas.configure(scrollregion=canvas.bbox('all'))

        def _on_canvas_size(event):
            canvas.itemconfigure(inner_id, width=event.width)

        inner.bind('<Configure>', _on_configure)
        canvas.bind('<Configure>', _on_canvas_size)

        # mouse wheel scrolling (Windows)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        canvas.bind_all('<MouseWheel>', _on_mousewheel)
        return inner

    # Basic style
    try:
        style = ttk.Style(window)
        style.theme_use('clam')
        style.configure('TLabel', background='#f6f7fb')
        style.configure('TFrame', background='#f6f7fb')
        style.configure('TButton', padding=6)
    except Exception:
        pass

    header_font = font.Font(window, family="Segoe UI", size=16, weight="bold")
    ttk.Label(window, text="Epic Event Generator", font=header_font).pack(pady=(12, 6))

    frame_main = make_scrollable(window)

    entry_reward_file = create_row(frame_main, "Reward CSV:", "excel/Rewards/Reward_Ruthye.csv", browse_callback=choose_reward_file)

    entry_target_dir = create_row(frame_main, "Excel Folder:", "excel", browse_callback=choose_target_dir)

    option_frame = ttk.Frame(frame_main)
    option_frame.pack(fill='x', padx=12, pady=(6, 2))
    ttk.Label(option_frame, text="Options:", font=("Segoe UI", 10, "bold")).pack(anchor='w')

    generate_task_var = tk.IntVar(value=1)
    generate_lang_var = tk.IntVar(value=1)
    rerun_var = tk.IntVar(value=0)

    checkbox_frame = ttk.Frame(frame_main)
    checkbox_frame.pack(fill='x', padx=12, pady=(0, 12))
    ttk.Checkbutton(checkbox_frame, text="Generate Task Files", variable=generate_task_var).pack(side='left', padx=6)
    ttk.Checkbutton(checkbox_frame, text="Generate Language Files", variable=generate_lang_var).pack(side='left', padx=6)
    ttk.Checkbutton(checkbox_frame, text="Rerun Mode", variable=rerun_var).pack(side='left', padx=6)

    # --- 2-column layout ---
    col_frame = ttk.Frame(frame_main)
    col_frame.pack(fill='x', padx=4, pady=4)
    col_frame.columnconfigure(0, weight=1)
    col_frame.columnconfigure(1, weight=1)

    left_col = ttk.Frame(col_frame)
    left_col.grid(row=0, column=0, sticky='nsew', padx=(0, 4))
    right_col = ttk.Frame(col_frame)
    right_col.grid(row=0, column=1, sticky='nsew', padx=(4, 0))

    def create_col_row(parent: tk.Widget, label: str, default: str, row_idx: int = None) -> tk.Entry:
        frame = ttk.Frame(parent)
        if row_idx is not None:
            frame.grid(row=row_idx, column=0, sticky='ew', padx=6, pady=4)
            parent.columnconfigure(0, weight=1)
        else:
            frame.pack(fill='x', padx=6, pady=4)
        # Fixed label width (28 chars) keeps all entry boxes left-aligned together
        ttk.Label(frame, text=label, width=28, anchor='w').grid(row=0, column=0, sticky='w')
        entry = ttk.Entry(frame)
        entry.insert(0, default)
        entry.grid(row=0, column=1, sticky='ew', padx=(6, 0))
        frame.columnconfigure(0, minsize=0)
        frame.columnconfigure(1, weight=1)
        entry.frame = frame
        return entry

    # --- LEFT COLUMN: Event Info ---
    ttk.Label(left_col, text="--- EVENT INFO ---", font=("Segoe UI", 9, "bold"), foreground="#1a6bb5").pack(anchor='w', padx=6, pady=(4, 2))
    entry_hero_name = create_col_row(left_col, "Hero Name:", "Ruthye")
    entry_ally_id = create_col_row(left_col, "Ally ID:", "13268")
    entry_start_time = create_col_row(left_col, "Start Time:", "20260620_000000")
    entry_end_time = create_col_row(left_col, "End Time:", "20260625_000000")
    entry_bingo_activity_id = create_col_row(left_col, "Bingo Activity ID:", "1024")
    entry_newhero_activity_id = create_col_row(left_col, "NewHero Activity ID:", "2024")
    entry_task_base_id = create_col_row(left_col, "Task Base ID:", "4090170")
    ttk.Label(left_col, text="--- BINGO TOKENS ---", font=("Segoe UI", 9, "bold"), foreground="#1a6bb5").pack(anchor='w', padx=6, pady=(8, 2))
    entry_bingo_token1_id = create_col_row(left_col, "Bingo Token 1 ID:", "")
    entry_bingo_token2_id = create_col_row(left_col, "Bingo Token 2 ID:", "")

    # --- RIGHT COLUMN: Jump / Ads / Gacha IDs ---
    lbl_jump = ttk.Label(right_col, text="--- JUMP IDs ---", font=("Segoe UI", 9, "bold"), foreground="#1a6bb5")
    lbl_jump.grid(row=0, column=0, sticky='w', padx=6, pady=(4, 2))
    entry_gacha_jump_id = create_col_row(right_col, "Gacha Jump ID:", "1143", row_idx=1)
    entry_iap_jump_id = create_col_row(right_col, "IAP Jump ID:", "1362", row_idx=2)
    entry_iap_store_id = create_col_row(right_col, "IAP Store ID:", "9459", row_idx=3)
    
    lbl_ads = ttk.Label(right_col, text="--- ADS / GACHA IDs ---", font=("Segoe UI", 9, "bold"), foreground="#1a6bb5")
    lbl_ads.grid(row=5, column=0, sticky='w', padx=6, pady=(8, 2))
    entry_gacha_type_id = create_col_row(right_col, "Gacha Type ID:", "116", row_idx=6)
    entry_ads_banner_id = create_col_row(right_col, "AdsBanner ID:", "61", row_idx=7)
    entry_ads_popup_id = create_col_row(right_col, "AdsPopUp ID:", "65", row_idx=8)

    saved_config = load_config()
    if saved_config:
        def restore_val(entry_widget: tk.Entry, key: str) -> None:
            if key in saved_config:
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, saved_config[key])

        restore_val(entry_reward_file, "reward_file")
        restore_val(entry_target_dir, "target_dir")
        restore_val(entry_hero_name, "hero_name")
        restore_val(entry_ally_id, "ally_id")
        restore_val(entry_bingo_activity_id, "bingo_activity_id")
        restore_val(entry_newhero_activity_id, "newhero_activity_id")
        restore_val(entry_start_time, "start_time")
        restore_val(entry_end_time, "end_time")
        restore_val(entry_gacha_jump_id, "gacha_jump_id")
        restore_val(entry_gacha_type_id, "gacha_type_id")
        restore_val(entry_ads_banner_id, "ads_banner_id")
        restore_val(entry_ads_popup_id, "ads_popup_id")
        restore_val(entry_iap_jump_id, "iap_jump_id")
        # backward-compat: also try old keys
        if not entry_iap_jump_id.get():
            restore_val(entry_iap_jump_id, "shop_jump_id")
        restore_val(entry_iap_store_id, "iap_store_id")
        if not entry_iap_store_id.get():
            restore_val(entry_iap_store_id, "shop_store_id")
        restore_val(entry_task_base_id, "task_base_id")
        restore_val(entry_bingo_token1_id, "bingo_token1_id")
        restore_val(entry_bingo_token2_id, "bingo_token2_id")
        generate_task_var.set(parse_int(saved_config.get("generate_task_files", 1), 1))
        generate_lang_var.set(parse_int(saved_config.get("generate_language_files", 1), 1))
        rerun_var.set(parse_int(saved_config.get("rerun", 0), 0))

    def on_generate() -> None:
        values = {
            "reward_file": entry_reward_file.get(),
            "target_dir": entry_target_dir.get(),
            "hero_name": entry_hero_name.get(),
            "ally_id": entry_ally_id.get(),
            "bingo_activity_id": entry_bingo_activity_id.get(),
            "newhero_activity_id": entry_newhero_activity_id.get(),
            "start_time": entry_start_time.get(),
            "end_time": entry_end_time.get(),
            "gacha_jump_id": entry_gacha_jump_id.get(),
            "gacha_type_id": entry_gacha_type_id.get(),
            "ads_banner_id": entry_ads_banner_id.get(),
            "ads_popup_id": entry_ads_popup_id.get(),
            "iap_jump_id": entry_iap_jump_id.get(),
            "iap_store_id": entry_iap_store_id.get(),
            "task_base_id": entry_task_base_id.get(),
            "bingo_token1_id": entry_bingo_token1_id.get(),
            "bingo_token2_id": entry_bingo_token2_id.get(),
        }
        flags = {
            "generate_task_files": bool(generate_task_var.get()),
            "generate_language_files": bool(generate_lang_var.get()),
            "rerun": bool(rerun_var.get()),
        }
        config = build_config_from_gui(values, flags)
        try:
            reward_rows = parse_reward_csv(config.reward_file)
            output_dir = write_generated_outputs(config, reward_rows)
            save_config({**values, **flags})
            messagebox.showinfo("Success", f"Generated files to {output_dir}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    btn_frame = ttk.Frame(frame_main)
    btn_frame.pack(fill='x', padx=12, pady=(8, 16))
    generate_btn = ttk.Button(btn_frame, text="Generate", command=on_generate)
    generate_btn.pack(fill='x', expand=True)
    window.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        run_gui()
