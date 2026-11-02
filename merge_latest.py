import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

import subprocess
import re
import os
import json
import xml.etree.ElementTree as ET
from collections import Counter

CONFIG_FILE = "p4_config.json"

def auto_detect_p4_settings():
    """Tự động phát hiện P4PORT, P4USER và P4CLIENT từ cấu hình P4V và project."""
    p4_port = ""
    p4_user = ""
    p4_client = ""
    
    # 1. Thử đọc từ config hiện tại trong workspace (ví dụ liveops_config.json, iap_config.json hoặc epic_tool_config.json)
    for cfg_file in ["liveops_config.json", "iap_config.json", "epic_tool_config.json"]:
        try:
            with open(cfg_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                target_dir = data.get("TargetDir") or data.get("target_dir")
                if target_dir:
                    # Ví dụ: "C:/Users/gear/Perforce/x.son.lengoc_Config_Dev/excel"
                    parts = target_dir.replace('\\', '/').split('/')
                    for part in parts:
                        if part.endswith("_Config_Dev") or part.endswith("_Config_Release") or part.startswith("x.son.lengoc"):
                            p4_client = part
                            break
        except Exception:
            pass
            
    # 2. Thử đọc connectionmap.xml của P4V để tìm Port và User
    try:
        user_profile = os.environ.get("USERPROFILE", "")
        conn_map_path = os.path.join(user_profile, ".p4qt", "connectionmap.xml")
        if os.path.exists(conn_map_path):
            tree = ET.parse(conn_map_path)
            root = tree.getroot()
            for conn in root.findall("ConnectionMap"):
                port = conn.find("P4Port").text if conn.find("P4Port") is not None else ""
                user = conn.find("User").text if conn.find("User") is not None else ""
                # Ưu tiên các port thực tế, không lấy port mặc định nếu có port khác
                if port and port != "perforce:1666":
                    p4_port = port
                    p4_user = user
                    break
    except Exception:
        pass
        
    return p4_port, p4_user, p4_client

def check_p4_connection(port, user, client):
    """Kiểm tra kết nối Perforce sử dụng lệnh 'p4 info'."""
    cmd = ['p4', '-p', port, '-u', user, '-c', client, 'info']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', timeout=5)
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr.strip() or result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Kết nối tới server Perforce bị quá giờ (Timeout)."
    except Exception as e:
        return False, str(e)

def get_p4_settings():
    """Lấy cấu hình Perforce từ file cache hoặc hỏi người dùng và kiểm tra kết nối."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                port = cfg.get("P4PORT")
                user = cfg.get("P4USER")
                client = cfg.get("P4CLIENT")
                
                # Kiểm tra kết nối
                ok, _ = check_p4_connection(port, user, client)
                if ok:
                    return port, user, client
                else:
                    print("\n[CẢNH BÁO] Cấu hình cũ không kết nối được Perforce. Tiến hành cấu hình lại...")
        except Exception:
            pass

    # Auto-detect cấu hình
    det_port, det_user, det_client = auto_detect_p4_settings()
    
    default_port = det_port or "sfo-perforce-01.wbiegames.com:1666"
    default_user = det_user or "x.son.lengoc"
    default_client = det_client or "x.son.lengoc_Config_Dev"
    
    print("======================================================")
    print("      CẤU HÌNH KẾT NỐI PERFORCE (CHỈ THIẾT LẬP LẦN ĐẦU)")
    print("======================================================\n")
    
    while True:
        port = input(f"1. Nhập P4PORT (Mặc định: {default_port}): ").strip() or default_port
        user = input(f"2. Nhập P4USER (Mặc định: {default_user}): ").strip() or default_user
        client = input(f"3. Nhập P4CLIENT (Mặc định: {default_client}): ").strip() or default_client
        
        print("\nĐang kiểm tra kết nối tới Perforce server...")
        ok, msg = check_p4_connection(port, user, client)
        if ok:
            print("[OK] Kết nối Perforce thành công!")
            # Lưu cấu hình vào file cache
            try:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump({"P4PORT": port, "P4USER": user, "P4CLIENT": client}, f, indent=4)
            except Exception as e:
                print(f"[CẢNH BÁO] Không thể lưu file cấu hình: {e}")
            return port, user, client
        else:
            print(f"[LỖI KẾT NỐI] {msg}")
            print("Vui lòng kiểm tra VPN hoặc thông số cấu hình và thử lại.\n")

def get_files_from_changelist(port, user, client, cl):
    """Lấy danh sách tệp tin bị ảnh hưởng trong một changelist."""
    cmd = ['p4', '-p', port, '-u', user, '-c', client, 'describe', '-s', cl]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        print(f"[LỖI] Không thể đọc changelist {cl}: {result.stderr.strip()}")
        return []
    
    files = []
    lines = result.stdout.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith('... //'):
            # Định dạng dòng: "... //depot/path/file.csv#rev action" -> tách lấy đường dẫn trước ký tự "#"
            path = line[4:].split('#')[0]
            files.append(path)
    return files

def get_clients_and_streams(port, user):
    """Lấy danh sách tất cả client và stream tương ứng của user."""
    cmd = ['p4', '-p', port, '-u', user, '-F', '%client% %Stream%', '-ztag', 'clients', '-u', user]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    stream_to_client = {}
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 2:
                client_name = parts[0]
                stream_path = parts[1]
                stream_to_client[stream_path] = client_name
    return stream_to_client

def create_p4_changelist(port, user, client, description):
    """Tạo một pending changelist mới với mô tả cho trước."""
    cmd_out = ['p4', '-p', port, '-u', user, '-c', client, 'change', '-o']
    result = subprocess.run(cmd_out, capture_output=True, text=True, encoding='utf-8')
    if result.returncode != 0:
        print(f"[LỖI] Không thể lấy template changelist: {result.stderr.strip()}")
        return None
    
    template = result.stdout
    # Thay thế dòng mô tả thụt lề ngay sau 'Description:' bằng mô tả mới
    lines = template.splitlines()
    new_lines = []
    in_desc = False
    for line in lines:
        if line.startswith("Description:"):
            new_lines.append(line)
            in_desc = True
            continue
        if in_desc:
            if line.startswith("\t") or line.startswith(" "):
                new_lines.append(f"\t{description}")
                in_desc = False
                continue
            else:
                in_desc = False
        new_lines.append(line)
    
    modified_template = "\n".join(new_lines)
    
    cmd_in = ['p4', '-p', port, '-u', user, '-c', client, 'change', '-i']
    res = subprocess.run(cmd_in, input=modified_template, capture_output=True, text=True, encoding='utf-8')
    if res.returncode == 0:
        match = re.search(r'Change (\d+) created', res.stdout)
        if match:
            return match.group(1)
            
    print(f"[LỖI] Không thể tạo changelist mới trên Perforce: {res.stderr.strip() or res.stdout.strip()}")
    return None

def run_p4_reconcile(port, user, client, cl_id, target_path):
    """Chạy lệnh p4 reconcile để tìm các thay đổi offline và cho vào changelist."""
    cmd = ['p4', '-p', port, '-u', user, '-c', client, 'reconcile', '-c', cl_id, target_path]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    return result.returncode == 0, result.stdout.strip() or result.stderr.strip()

def main():
    print("======================================================")
    print("  TOOL TỰ ĐỘNG LỌC FILE VÀ MERGE (KHÔNG CẦN SỬA CODE)")
    print("======================================================\n")

    # --- BƯỚC 1: XÁC THỰC CẤU HÌNH PERFORCE ---
    port, user, client = get_p4_settings()

    # --- BƯỚC 2: LẤY INPUT CHANGELISTS ---
    print("\n1. Hãy dán danh sách các changelist vào đây (có thể copy thẳng 1 cột từ Google Sheets/Excel).")
    print("   (Nhấn Enter 2 lần liên tiếp khi bạn đã dán xong để tiếp tục):")
    
    cl_input = ""
    while True:
        line = input()
        if line == "":
            break
        cl_input += line + " "

    # Tự động trích xuất các con số changelist (5 chữ số trở lên)
    raw_changelists = re.findall(r'\d{5,}', cl_input)
    duplicate_changelists = {
        cl: count for cl, count in Counter(raw_changelists).items() if count > 1
    }
    if duplicate_changelists:
        print("\n[CẢNH BÁO] Phát hiện changelist bị trùng:")
        for cl, count in duplicate_changelists.items():
            print(f"   - CL {cl}: xuất hiện {count} lần")

    # Loại bỏ trùng lặp và sắp xếp giảm dần (hoặc giữ nguyên)
    changelists = list(set(raw_changelists))

    if not changelists:
        print("\n[LỖI] Không tìm thấy mã số changelist nào hợp lệ. Đang thoát...")
        return

    print(f"\n=> Đã nhận diện được {len(changelists)} changelists: {', '.join(changelists)}")

    # --- BƯỚC 3: LẤY INPUT STREAMS ---
    # Thay thế dấu gạch chéo ngược '\' và loại bỏ ký tự gạch chéo thừa ở cuối đường dẫn
    source_stream = input("\n2. Nhập đường dẫn Source Stream (vd: //dcwc/Gear_Character_Development_Config):\n> ").strip().replace('\\', '/').rstrip('/')
    target_stream = input("3. Nhập đường dẫn Target Stream (vd: //dcwc/Gear_v1_1_17_2_Patch_A_Config):\n> ").strip().replace('\\', '/').rstrip('/')

    if not source_stream or not target_stream:
        print("\n[LỖI] Stream không được để trống. Đang thoát...")
        return

    # --- BƯỚC 4: QUÉT FILE VÀ TÌM CLIENT PHÙ HỢP ---
    print("\nĐang quét danh sách file trên Perforce server...")
    unique_files = set()
    for cl in changelists:
        files = get_files_from_changelist(port, user, client, cl)
        unique_files.update(files)
        
    print(f"Tìm thấy {len(unique_files)} files từ các changelist.")
    
    # Lọc các file thuộc Source Stream
    source_files_to_merge = [f for f in unique_files if f.startswith(source_stream + '/')]
    print(f"Tìm thấy {len(source_files_to_merge)} files thuộc Source Stream để merge.")
    
    if not source_files_to_merge:
        print("Không có file nào khớp để merge.")
        return

    # Truy vấn client phù hợp cho Target Stream để tránh lỗi "File(s) not in client view"
    print("\nĐang quét danh sách client workspace của bạn trên server...")
    stream_to_client = get_clients_and_streams(port, user)
    target_client = stream_to_client.get(target_stream)
    
    if not target_client:
        print(f"[CẢNH BÁO] Không tìm thấy Workspace nào được gán trực tiếp với Target Stream: '{target_stream}'.")
        print(f"Hệ thống sẽ chạy thử lệnh merge bằng Workspace mặc định: '{client}'.")
        target_client = client
    else:
        print(f"[OK] Đã tự động nhận diện được Workspace phù hợp với Target Stream: '{target_client}'")

    # --- BƯỚC 5: HỎI TẠO CHANGELIST VÀ RECONCILE ---
    opt_create_cl = input("\nBạn có muốn tạo changelist mới 'Auto Merge từ stream sang stream' và tự động reconcile không? (Y/n): ").strip().lower()
    
    changelist_id = None
    if opt_create_cl in ('', 'y', 'yes'):
        desc = "Auto Merge from source stream to target stream"
        print(f"\nĐang tạo changelist mới với mô tả '{desc}'...")
        changelist_id = create_p4_changelist(port, user, target_client, desc)
        if changelist_id:
            print(f"[OK] Đã tạo thành công pending changelist ID: {changelist_id}")
        else:
            print("[CẢNH BÁO] Không tạo được changelist mới, các file sẽ được đưa vào 'default' changelist.")

    # --- BƯỚC 6: TIẾN HÀNH MERGE ---
    print("\nBắt đầu chạy tích hợp (integrate) dữ liệu...")
    success_count = 0
    for source_file in source_files_to_merge:
        # Thay thế source stream bằng target stream ở đầu đường dẫn
        target_file = source_file.replace(source_stream, target_stream, 1)
        
        cmd = ['p4', '-p', port, '-u', user, '-c', target_client, 'integrate']
        if changelist_id:
            cmd += ['-c', changelist_id]
        cmd += [source_file, target_file]
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            output_msg = result.stdout.strip() or result.stderr.strip()
            print(f"[OK] {target_file}")
            if "already integrated" not in output_msg.lower():
                success_count += 1
        else:
            print(f"[LỖI] Không thể merge {source_file} -> {target_file}")
            print(f"      Chi tiết: {result.stderr.strip()}")

    # --- BƯỚC 7: RECONCILE OFFLINE WORK ---
    if changelist_id:
        print("\nĐang quét và chạy reconcile offline work cho target stream...")
        reconcile_path = f"{target_stream}/excel/..."
        ok, rec_msg = run_p4_reconcile(port, user, target_client, changelist_id, reconcile_path)
        if ok:
            if "no file(s) to reconcile" in rec_msg.lower() or not rec_msg:
                print("[OK] Không phát hiện thay đổi offline nào cần reconcile.")
            else:
                print(f"[OK] Đã reconcile xong các thay đổi offline vào changelist {changelist_id}.")
                # In tối đa 10 dòng đầu của reconcile
                lines = rec_msg.splitlines()
                for l in lines[:10]:
                    print(f"     {l}")
                if len(lines) > 10:
                    print(f"     ... và {len(lines) - 10} tệp tin khác.")
        else:
            print(f"[LỖI RECONCILE] Không thể chạy reconcile: {rec_msg}")

    print(f"\nHOÀN TẤT! Đã mở/tích hợp {success_count} files.")
    if changelist_id:
        print(f"Vui lòng mở workspace '{target_client}' trên P4V, kiểm tra Changelist ID '{changelist_id}' để tiến hành Resolve -> Submit các file đã merge.")
    else:
        print(f"Vui lòng mở workspace '{target_client}' trên P4V để kiểm tra lại và tiến hành Resolve -> Submit các file đã merge.")

if __name__ == "__main__":
    main()