#file_io.py
import csv
import os
import sys
from datetime import datetime

# =====================================
# CẤU HÌNH FILE: Dùng thư mục AppData
# =====================================

APP_NAME = "AutoClicker"
BASE_DIR = None

# Xác định thư mục Local AppData trên Windows
if sys.platform == 'win32':
    BASE_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), APP_NAME)
else:
    # Dự phòng cho Linux/Mac
    BASE_DIR = os.path.join(os.path.expanduser('~'), f'.{APP_NAME}')

# Tạo thư mục nếu chưa tồn tại
try:
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
except Exception as e:
    # Nếu không tạo được, dùng thư mục tạm thời, nhưng đây là trường hợp hiếm
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Đường dẫn cuối cùng cho các file log
POSITIONS_FILE = os.path.join(BASE_DIR, 'positions.log')
ACTIVITY_FILE = os.path.join(BASE_DIR, 'activity.log')


# =====================================
# XỬ LÝ LOG HOẠT ĐỘNG (activity.log)
# =====================================

def log_activity(message):
    """Ghi thông báo hoạt động vào file activity.log"""
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{current_time}] {message}"

        # Ghi vào file
        with open(ACTIVITY_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')

        # KHÔNG in ra console nữa, thay bằng callback UI để chỉ hiển thị trong UI (nếu cần in, phải dùng print)
        # print(log_entry)

    except Exception as e:
        print(f"LỖI HỆ THỐNG (Không ghi được activity.log): {e}")


# =====================================
# XỬ LÝ LOG VỊ TRÍ (positions.log)
# =====================================

def save_position_to_log(window_title, rel_x, rel_y):
    """Ghi tọa độ mới vào file positions.log"""
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        all_rows = load_log_data()
        is_duplicate = False
        if all_rows:
            last_row = all_rows[-1]
            # Kiểm tra nếu dòng cuối cùng khớp với tọa độ/cửa sổ hiện tại
            if len(last_row) >= 4 and last_row[1] == window_title and last_row[2] == str(rel_x) and last_row[3] == str(rel_y):
                is_duplicate = True

        if is_duplicate:
            return True

        with open(POSITIONS_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([current_time, window_title, rel_x, rel_y])
        return True
    except Exception as e:
        log_activity(f"Lỗi khi ghi positions.log: {e}")
        return False


def load_log_data():
    """Tải dữ liệu log vị trí từ file positions.log"""
    data = []
    if not os.path.exists(POSITIONS_FILE):
        return data

    try:
        with open(POSITIONS_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) == 4:
                    data.append(row)
    except Exception as e:
        log_activity(f"Lỗi khi đọc positions.log: {e}")
    return data


def overwrite_log_data(rows):
    """Ghi đè toàn bộ dữ liệu log vị trí (Giữ nguyên logic file io)"""
    try:
        with open(POSITIONS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        return True
    except Exception as e:
        log_activity(f"Lỗi khi ghi đè positions.log: {e}")
        return False


def clear_log_file():
    """Xóa toàn bộ nội dung file positions.log (Giữ nguyên logic file io)"""
    try:
        with open(POSITIONS_FILE, 'w', newline='', encoding='utf-8') as f:
            pass
        return True
    except Exception as e:
        log_activity(f"Lỗi khi xóa positions.log: {e}")
        return False


# =====================================
# HÀM MỚI: ĐỌC NỘI DUNG LOG VÀ TRẢ VỀ ĐƯỜNG DẪN
# =====================================
def get_log_content_and_path(log_type):
    """Trả về nội dung của file log và đường dẫn thư mục chứa nó."""

    file_path = ACTIVITY_FILE if log_type == 'activity' else POSITIONS_FILE
    folder_path = BASE_DIR
    content = f"--- File {log_type}.log không tồn tại hoặc trống ---\n\n"

    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            content = f"--- Lỗi khi đọc file {log_type}.log: {e} ---"

    return content, folder_path