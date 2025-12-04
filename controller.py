#controller.py
import pygetwindow as gw
from utils.file_io import save_position_to_log, load_log_data, get_log_content_and_path, log_activity
# THAY ĐỔI: Thêm tham số mode vào start_watching trong autoclicker
from autoclicker import start_watching as ac_start, stop_watching as ac_stop, enable_pick_mode as ac_pick, \
    set_callbacks, set_pixel_mode
from tkinter import messagebox
from datetime import datetime

# =====================================
# Biến trạng thái toàn cục
# =====================================
last_saved_coords = None  # (rel_x, rel_y)
ui_callbacks = {}  # Lưu trữ các hàm cập nhật UI
current_is_five_points_mode = False  # Biến mới: Theo dõi chế độ 1/5 điểm
current_mode = "FISHING" # BIẾN MỚI: Theo dõi chế độ đang chạy/chuẩn bị chạy


def init_controller(update_status_cb, update_colors_cb, load_list_cb, set_coords_cb, pixel_mode_cb):
    """Thiết lập các hàm callback từ UI và Autoclicker"""
    global ui_callbacks
    ui_callbacks['update_status'] = update_status_cb
    ui_callbacks['update_colors'] = update_colors_cb
    ui_callbacks['load_list'] = load_list_cb
    ui_callbacks['set_coords'] = set_coords_cb
    ui_callbacks['set_pixel_mode'] = pixel_mode_cb

    set_callbacks(update_status_cb, update_colors_cb, handle_new_coordinates_from_pick)


# =====================================
# LOGIC TẢI TRẠNG THÁI CUỐI CÙNG (MỚI)
# =====================================

def load_last_known_state():
    """Tải trạng thái cửa sổ và tọa độ (X, Y) cuối cùng đã lưu trong positions.log"""
    data = load_log_data()
    if data:
        # Dữ liệu được lưu là: [time, window_title, rel_x, rel_y]
        last_row = data[-1]
        if len(last_row) >= 4:
            return (last_row[1], last_row[2], last_row[3])
    return None


# =====================================
# CHẾ ĐỘ PIXEL
# =====================================
def set_pixel_mode_on_off(is_five_points):
    """Cập nhật chế độ theo dõi pixel và chuyển tiếp cho Autoclicker"""
    global current_is_five_points_mode
    current_is_five_points_mode = is_five_points
    set_pixel_mode(is_five_points)


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
# LOGIC LƯU/TẢI LOG
# =====================================
def save_position(title, rel_x, rel_y):
    """Lưu tọa độ mới vào file positions.log và cập nhật UI"""
    global last_saved_coords

    if save_position_to_log(title, rel_x, rel_y):
        last_saved_coords = (rel_x, rel_y)
        return True
    return False


def load_log_list_data():
    """Tải dữ liệu log và định dạng cho Treeview (Không dùng)"""
    data = load_log_data()
    formatted_data = []
    for row in data:
        formatted_data.append((row[0], row[1], f"{row[2]},{row[3]}", "☐"))
    return formatted_data


def handle_view_log_file(log_type):
    """Lấy nội dung log và đường dẫn thư mục cho Log Viewer Dialog"""
    content, folder_path = get_log_content_and_path(log_type)
    return content, folder_path


# =====================================
# HÀM BÊN NGOÀI GỌI TỪ UI
# =====================================
# CẬP NHẬT: Thêm tham số 'mode', 'interval_str' và 'key_interval_str'
def handle_start(window_title="", x_str="0", y_str="0", mode="FISHING", threshold_str="0", a_str="0", delay_str="0", interval_str="0", key_interval_str="0.5"):
    """Xử lý nút Start cho cả 3 chế độ"""

    # --- CHẾ ĐỘ HARVEST (Đơn giản nhất, không cần cửa sổ hay tọa độ) ---
    if mode == "HARVEST":
        try:
            key_interval = float(key_interval_str)
            if key_interval <= 0.01:
                messagebox.showerror("Lỗi", "Thời gian nghỉ giữa phím phải là số thực dương (> 0.01 giây)!")
                return
        except:
            messagebox.showerror("Lỗi", "Thời gian nghỉ giữa phím phải là số thực dương!")
            return

        # Gọi hàm start cho chế độ HARVEST
        ac_start(mode=mode, key_interval=key_interval)
        return

    # --- CHẾ ĐỘ FISHING & CRUSH ROCKS (Cần cửa sổ và tọa độ) ---

    if not window_title:
        messagebox.showwarning("Thiếu cửa sổ", "Bạn chưa chọn cửa sổ mục tiêu!")
        return

    try:
        rel_x = int(x_str)
        rel_y = int(y_str)
    except:
        messagebox.showerror("Lỗi", "Tọa độ phải là số!")
        return

    # Lưu vị trí (Áp dụng cho cả 2 mode)
    if last_saved_coords != (rel_x, rel_y):
        save_position(window_title, rel_x, rel_y)

    if mode == "FISHING":
        # Logic kiểm tra cho chế độ Câu Cá (Pixel Mode)
        try:
            threshold = float(threshold_str)
            if threshold < 0: raise ValueError
        except:
            messagebox.showerror("Lỗi", "Ngưỡng khoảng cách màu phải là số không âm!")
            return

        is_five_points_mode = ui_callbacks['set_pixel_mode'] # Lấy trạng thái chế độ 5 điểm hiện tại (cần sửa UI để lấy biến)
        try:
            a = int(a_str)
            if a < 0 and is_five_points_mode: raise ValueError
        except:
            if is_five_points_mode:
                messagebox.showerror("Lỗi", "Độ lệch A phải là số nguyên không âm!")
                return
            a = 0

        try:
            delay = float(delay_str)
            if delay <= 0: raise ValueError
        except:
            messagebox.showerror("Lỗi", "Độ trễ sau Click phải là số thực dương!")
            return

        # Gọi hàm start cho chế độ FISHING
        ac_start(rel_x, rel_y, window_title, mode, threshold, a, delay)

    elif mode == "CRUSH_ROCKS":
        # Logic kiểm tra cho chế độ Đập Đá (Timer Mode)
        try:
            interval = float(interval_str)
            if interval <= 0.01: # Đảm bảo chu kỳ tối thiểu
                messagebox.showerror("Lỗi", "Thời gian A (Chu kỳ) phải là số thực dương (> 0.01 giây)!")
                return
        except:
            messagebox.showerror("Lỗi", "Thời gian A (Chu kỳ) phải là số thực dương!")
            return

        # Gọi hàm start cho chế độ CRUSH_ROCKS
        ac_start(rel_x, rel_y, window_title, mode, interval=interval)


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

    try:
        from autoclicker import selected_window
        window_title = selected_window if selected_window else "N/A"
    except ImportError:
        window_title = "N/A"

    save_position(window_title, rel_x, rel_y)