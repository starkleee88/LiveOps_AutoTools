# Hướng Dẫn Sử Dụng Tool Tự Động Merge Stream Theo Changelist (`merge_latest.py`)

Công cụ này giúp tự động tích hợp (merge/integrate) các file từ **Source Stream** sang **Target Stream** trên Perforce dựa trên danh sách Changelist (sao chép từ Excel/Google Sheets) dưới dạng phiên bản mới nhất (Latest), đồng thời hỗ trợ tự động tạo pending changelist riêng và quét thay đổi offline (reconcile) trong thư mục `excel/`.

---

## I. Điều Kiện Chuẩn Bị (Chỉ làm lần đầu)

Để người khác có thể chạy được kịch bản này, máy của họ cần đáp ứng các điều kiện sau:

1. **Cài đặt Python 3:**
   - Tải và cài đặt Python từ [python.org](https://www.python.org/).
   - Trong quá trình cài đặt, nhớ tích chọn vào ô **"Add Python to PATH"**.

2. **Perforce Command Line (P4 CLI):**
   - Phải có lệnh `p4` trong máy (thường đã được cài đặt sẵn đi kèm khi cài P4V).
   - Để kiểm tra, mở Command Prompt/PowerShell lên gõ: `p4 -V`. Nếu hiện ra thông tin phiên bản là đã thành công.

3. **Đăng nhập Perforce:**
   - Hãy chắc chắn rằng bạn đang kết nối VPN (nếu làm việc từ xa) và đã đăng nhập thành công vào P4V. Tool sẽ tự động nhận diện và sử dụng phiên đăng nhập (login ticket) hiện tại của P4V mà không yêu cầu nhập mật khẩu.

4. **Workspace đích (Target Workspace):**
   - Đảm bảo bạn **đã tạo sẵn một Workspace (Client) liên kết với Target Stream** trên P4V của mình.

---

## II. Các Bước Chạy Kịch Bản

Mở ứng dụng Terminal (Command Prompt hoặc PowerShell trên Windows) và làm theo hướng dẫn sau:

### Bước 1: Di chuyển tới thư mục chứa file tool
Dùng lệnh `cd` để đi đến thư mục chứa file `merge_latest.py`. Ví dụ:
```powershell
cd "đường_dẫn_thư_mục_chứa_tool"
```

### Bước 2: Chạy công cụ
Chạy lệnh sau:
```powershell
python merge_latest.py
```
*(Nếu dự án sử dụng môi trường ảo venv, hãy chạy đường dẫn python trong venv, ví dụ: `.venv\Scripts\python.exe merge_latest.py`)*

### Bước 3: Hoàn thành thông tin yêu cầu trên Console
Sau khi khởi chạy, tool sẽ dẫn dắt bạn qua các bước:

1. **Thiết lập kết nối Perforce (Chỉ hỏi lần đầu tiên):**
   - Tool sẽ tự động dò tìm cấu hình hiện tại của bạn và đề xuất các thông số mặc định: `P4PORT`, `P4USER`, và `P4CLIENT`.
   - Nếu thông tin hiển thị đã đúng, bạn chỉ cần **nhấn Enter liên tục** để xác nhận kết nối.
   - Khi kết nối thành công, tool sẽ tạo file cấu hình `p4_config.json` trong thư mục, ở các lần chạy sau tool sẽ tự động đọc từ file này và bỏ qua bước cấu hình.

2. **Dán danh sách Changelists:**
   - Copy cột danh sách Changelist từ Google Sheets hoặc Excel rồi dán (Ctrl+V) trực tiếp vào Terminal.
   - **Nhấn Enter 2 lần liên tiếp** khi dán xong để tool bắt đầu xử lý.
   - Tool sẽ tự động nhận diện các changelist hợp lệ và lọc bỏ các bản trùng.

3. **Nhập đường dẫn Source Stream:**
   - Copy đường dẫn depot của nhánh nguồn và dán vào (Ví dụ: `//dcwc/Gear_Character_Development_Config`).

4. **Nhập đường dẫn Target Stream:**
   - Copy đường dẫn depot của nhánh đích và dán vào (Ví dụ: `//dcwc/Gear_v1_1_17_2_Patch_A_Config`).

5. **Lựa chọn Tạo Changelist & Reconcile:**
   - Tool sẽ hỏi bạn có muốn tạo changelist mới và tự động reconcile không? Nhập `y` (hoặc chỉ cần nhấn **Enter**) để đồng ý.
   - Tool sẽ tự động:
     - Tạo một pending changelist mới mang tên: `"Auto Merge from source stream to target stream"`.
     - Tự động integrate toàn bộ các file nguồn vào changelist mới này.
     - Tự động quét và `reconcile` các thay đổi offline chỉ riêng trong thư mục `excel/` của nhánh đích vào chung changelist đó.

---

## III. Các Bước Hoàn Tất Trên P4V

Sau khi Terminal thông báo **"HOÀN TẤT!"**:

1. Mở phần mềm **P4V** lên.
2. Chuyển sang **Workspace** tương ứng của Target Stream (Client đích vừa hiển thị ở console).
3. Chuyển sang tab **Pending** và tìm đúng mã **Changelist ID** mà tool vừa tạo (Mô tả: *"Auto Merge from source stream to target stream"*).
4. Nhấp chuột phải vào changelist chọn **Resolve Files...** để xử lý xung đột (nếu có).
5. Thực hiện **Submit** changelist lên server Perforce để hoàn tất quá trình merge.
