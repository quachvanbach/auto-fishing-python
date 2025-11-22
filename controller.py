import pygetwindow as gw
from utils.file_io import save_position_to_log, load_log_data, overwrite_log_data, clear_log_file, \
    get_log_content_and_path, log_activity
from autoclicker import start_watching as ac_start, stop_watching as ac_stop, enable_pick_mode as ac_pick, set_callbacks
from tkinter import messagebox
from datetime import datetime

# =====================================
# Biến trạng thái toàn cục (Dùng để đồng bộ giữa UI và Controller)
# =====================================
last_saved_coords = None  # (rel_x, rel_y)
ui_callbacks = {}  # Lưu trữ các hàm cập nhật UI


def init_controller(update_status_cb, update_colors_cb, load_list_cb, set_coords_cb):
    """Thiết lập các hàm callback từ UI và Autoclicker"""
    global ui_callbacks
    ui_callbacks['update_status'] = update_status_cb
    ui_callbacks['update_colors'] = update_colors_cb
    ui_callbacks['load_list'] = load_list_cb
    ui_callbacks['set_coords'] = set_coords_cb

    # Thiết lập callbacks cho Autoclicker.
    set_callbacks(update_status_cb, update_colors_cb, handle_new_coordinates_from_pick)


# =====================================
# CỬA SỔ
# =====================================
def refresh_window_list():
    """Lấy danh sách tên cửa sổ đang mở"""
    try:
        windows = gw.getAllTitles()
    except:
        windows = [w.title for w in gw.getAllWindows()]
    return [w for w in windows if w and w.strip() != ""]


def get_window_rect(title):
    """Lấy tọa độ và kích thước cửa sổ"""
    try:
        win = gw.getWindowsWithTitle(title)[0]
        return (win.left, win.top, win.width, win.height)
    except Exception:
        return None


# =====================================
# LOGIC LƯU/TẢI LOG (Giữ nguyên)
# =====================================
def save_position(title, rel_x, rel_y):
    """Lưu tọa độ mới vào file positions.log và cập nhật UI"""
    global last_saved_coords

    if save_position_to_log(title, rel_x, rel_y):
        last_saved_coords = (rel_x, rel_y)
        if ui_callbacks.get('load_list'):
            ui_callbacks['load_list']()
        return True
    return False


def load_log_list_data():
    """Tải dữ liệu log và định dạng cho Treeview"""
    data = load_log_data()
    formatted_data = []
    for row in data:
        # timestamp, win, x, y -> (timestamp, win, f"{x},{y}", "☐")
        formatted_data.append((row[0], row[1], f"{row[2]},{row[3]}", "☐"))
    return formatted_data


def delete_selected_items(selected_data):
    """Xóa các mục đã chọn khỏi log"""
    if not selected_data:
        return False, "Không có mục nào được chọn!"

    all_rows = load_log_data()
    new_rows = []

    for r in all_rows:
        if len(r) < 4:
            continue
        timestamp, win, x, y = r[0], r[1], r[2], r[3]
        keep = True

        current_row_id = (timestamp, win, f"{x},{y}")

        for t, w, coords in selected_data:
            if current_row_id == (t, w, coords):
                keep = False
                break

        if keep:
            new_rows.append(r)

    if overwrite_log_data(new_rows):
        if ui_callbacks.get('load_list'):
            ui_callbacks['load_list']()
        log_activity("LOG: Đã xóa các mục positions.log đã chọn.")
        return True, "Đã xóa các mục đã chọn!"
    return False, "Lỗi khi ghi file log!"


def delete_all_log():
    """Xóa toàn bộ log vị trí"""
    if clear_log_file():
        if ui_callbacks.get('load_list'):
            ui_callbacks['load_list']()
        log_activity("LOG: Đã xóa toàn bộ positions.log.")
        return True, "Đã xóa toàn bộ!"
    return False, "Lỗi khi xóa file log!"


# =====================================
# HÀM XỬ LÝ LOG MỚI (Giữ nguyên)
# =====================================
def handle_view_log_file(log_type):
    """Lấy nội dung log và đường dẫn thư mục cho Log Viewer Dialog"""
    # log_type sẽ là 'positions' hoặc 'activity'
    content, folder_path = get_log_content_and_path(log_type)
    return content, folder_path


# =====================================
# HÀM BÊN NGOÀI GỌI TỪ UI
# =====================================
# BỎ LOGIC KIỂM TRA RADIUS VÀ KHÔNG TRUYỀN NÓ VÀO ac_start
def handle_start(window_title, x_str, y_str, radius_str, threshold_str):
    """Xử lý nút Start"""

    if not window_title:
        messagebox.showwarning("Thiếu cửa sổ", "Bạn chưa chọn cửa sổ mục tiêu!")
        return

    try:
        rel_x = int(x_str)
        rel_y = int(y_str)
    except:
        messagebox.showerror("Lỗi", "Tọa độ phải là số!")
        return

    # Logic kiểm tra radius đã bị loại bỏ ở đây

    try:
        threshold = float(threshold_str)
        if threshold < 0:
            raise ValueError
    except:
        messagebox.showerror("Lỗi", "Ngưỡng khoảng cách màu phải là số không âm!")
        return

    # Lưu lại vị trí nếu khác lần cuối đã lưu
    if last_saved_coords != (rel_x, rel_y):
        save_position(window_title, rel_x, rel_y)

    # BỎ THAM SỐ RADIUS KHI GỌI ac_start
    ac_start(rel_x, rel_y, window_title, threshold)


def handle_stop():
    """Xử lý nút Stop"""
    ac_stop()


def handle_pick_mode(window_title):
    """Xử lý nút Chọn vị trí"""
    ac_pick(window_title)


def handle_new_coordinates_from_pick(rel_x, rel_y):
    """Callback được gọi từ Autoclicker sau khi lấy được tọa độ mới"""
    if ui_callbacks.get('set_coords'):
        ui_callbacks['set_coords'](rel_x, rel_y)

    # Lấy tên cửa sổ từ UI (đã được chọn)
    from ui import combo_window
    window_title = combo_window.get()

    # Lưu vào log
    save_position(window_title, rel_x, rel_y)