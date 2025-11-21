import os
import csv
from datetime import datetime

# =====================================
# Cấu hình đường dẫn LOG
# =====================================
def get_log_path():
    """Trả về đường dẫn positions.log tại AppData (an toàn khi đóng gói)"""
    folder = os.path.join(os.getenv("LOCALAPPDATA"), "AutoClicker")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "positions.log")

log_file = get_log_path()

# =====================================
# HÀM ĐỌC/GHI CSV
# =====================================
def save_position_to_log(title, rel_x, rel_y):
    """Lưu tọa độ vào log"""
    timestamp = datetime.now().strftime("%d/%m/%y %H:%M")
    row_data = [timestamp, title, str(rel_x), str(rel_y)]

    try:
        with open(log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row_data)
        return True
    except Exception as e:
        print("[save_position_to_log] Lỗi ghi file:", e)
        return False

def load_log_data():
    """Tải toàn bộ dữ liệu log từ file"""
    if not os.path.exists(log_file):
        open(log_file, "w", encoding="utf-8").close()
        return []

    data = []
    try:
        with open(log_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    data.append(row)
    except Exception as e:
        print("[load_log_data] Lỗi đọc file:", e)
    return data

def overwrite_log_data(rows_to_keep):
    """Ghi đè file log với dữ liệu mới"""
    try:
        with open(log_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows_to_keep)
        return True
    except Exception as e:
        print("[overwrite_log_data] Lỗi ghi file:", e)
        return False

def clear_log_file():
    """Xóa toàn bộ nội dung file log"""
    try:
        open(log_file, "w", encoding="utf-8").close()
        return True
    except Exception as e:
        print("[clear_log_file] Lỗi xóa file:", e)
        return False