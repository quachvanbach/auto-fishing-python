#autoclicker.py
import pyautogui
import threading
import time
import keyboard
import pygetwindow as gw
# CHỈ IMPORT HÀM CẦN THIẾT
from utils.coords import clamp_coords, rgb_to_hex, tinh_khoang_cach_weighted_rgb, get_single_pixel_color, \
    get_multi_pixel_colors
from utils.file_io import log_activity
from tkinter import messagebox
import numpy as np

# Biến toàn cục để kiểm soát
running = False
current_mode = "FISHING" # BIẾN MỚI: Theo dõi chế độ hiện tại
selected_window = None  # Tên cửa sổ (string)
selected_window_rect = None  # (left, top, width, height)
status_callback = None
color_callback = None
log_save_callback = None
pixel_mode_callback = None  # Callback mới để cập nhật chế độ pixel

# BIẾN MỚI: Theo dõi thời điểm hành động cuối cùng
last_action_time = time.time()
# HẰNG SỐ MỚI: Thời gian chờ tối đa (60 giây)
IDLE_TIMEOUT = 60

# BIẾN MỚI: Chế độ theo dõi pixel
is_five_points_mode = False
pixel_offset_a = 0  # Độ lệch A
# BIẾN MỚI: Độ trễ tùy chỉnh sau khi click
action_delay = 7.0


def set_callbacks(status_cb, color_cb, log_save_cb_param):
    """Thiết lập các hàm callback để giao tiếp với UI/Controller"""
    global status_callback, color_callback, log_save_callback
    status_callback = status_cb
    color_callback = color_cb
    log_save_callback = log_save_cb_param


def set_pixel_mode(is_five_points):
    """Cập nhật chế độ theo dõi pixel từ Controller"""
    global is_five_points_mode
    is_five_points_mode = is_five_points


def update_status(text, color=None):
    """Cập nhật trạng thái qua callback"""
    if status_callback:
        status_callback(text, color)


# =====================================
# HÀM DỪNG LUỒNG AN TOÀN (CHUNG)
# =====================================
def sleep_may_stop(seconds):
    """Dừng luồng an toàn, kiểm tra biến 'running'"""
    global running
    # GIẢM ĐỘ TRỄ kiểm tra xuống 0.01s
    steps = int(seconds / 0.01) if seconds > 0 else 0
    for _ in range(steps):
        if not running:
            return False
        time.sleep(0.01)  # TỐI ƯU
    return True

# =====================================
# HÀM CLICK THEO THỜI GIAN (CRUSH ROCKS)
# =====================================

def timer_click_loop(rel_x, rel_y, window_title, interval_seconds):
    """Luồng thực hiện click chuột theo chu kỳ thời gian cố định."""
    global running, selected_window_rect

    try:
        rel_x = int(rel_x)
        rel_y = int(rel_y)
        interval_seconds = float(interval_seconds)
        if interval_seconds <= 0.01:
            raise ValueError
    except Exception:
        update_status("Lỗi: Thời gian A (chu kỳ) phải là số thực dương (> 0.01s)!", "#ff0000")
        log_activity("LỖI KHỞI TẠO TIMER CLICK: Chu kỳ không hợp lệ.")
        running = False
        return

    update_status(f"TIMER CLICK MODE: Đang chờ click lần đầu sau {interval_seconds:.2f}s...", "#ffffcc")

    while running:
        # Cố gắng lấy cửa sổ (Chỉ cần để log, không cần tọa độ trong vòng lặp)
        try:
            win = gw.getWindowsWithTitle(window_title)[0]
            win_left, win_top = win.left, win.top
            selected_window_rect = (win.left, win.top, win.width, win.height)
            selected_window = window_title
        except Exception:
            update_status("Cửa sổ bị đóng hoặc đổi tên!", "#ff0000")
            log_activity(f"DỪNG TIMER CLICK: Cửa sổ '{window_title}' không được tìm thấy.")
            running = False
            break

        abs_x = win_left + rel_x
        abs_y = win_top + rel_y
        abs_x, abs_y = clamp_coords(abs_x, abs_y)

        # Ngủ theo chu kỳ
        if not sleep_may_stop(interval_seconds):
            log_activity("TIMER CLICK MODE: Dừng trong khi chờ chu kỳ.")
            break

        # Thực hiện click
        try:
            pyautogui.click(abs_x, abs_y)
            update_status(f"TIMER CLICK MODE: Click tại ({abs_x}, {abs_y}). Chu kỳ tiếp: {interval_seconds:.2f}s", "#ccffcc")
            log_activity(f"TIMER CLICK: Click tại ({abs_x}, {abs_y}) thành công.")
        except Exception as e:
            update_status("TIMER CLICK MODE: Lỗi Click!", "#ff0000")
            log_activity(f"LỖI TIMER CLICK: Click thất bại: {e}")


# =====================================
# HÀM NHẤN PHÍM THEO THỜI GIAN (HARVEST MODE)
# =====================================

def timer_key_press_loop(interval_seconds):
    """Luồng thực hiện nhấn phím 'e' theo chu kỳ thời gian cố định."""
    global running

    try:
        interval_seconds = float(interval_seconds)
        if interval_seconds <= 0.01:
            raise ValueError
    except Exception:
        update_status("Lỗi: Thời gian nghỉ (chu kỳ) phải là số thực dương (> 0.01s)!", "#ff0000")
        log_activity("LỖI KHỞI TẠO TIMER KEY PRESS: Chu kỳ không hợp lệ.")
        running = False
        return

    update_status(f"TIMER KEY PRESS MODE: Đang chờ nhấn phím lần đầu sau {interval_seconds:.2f}s...", "#ffffcc")

    while running:
        # Ngủ theo chu kỳ
        if not sleep_may_stop(interval_seconds):
            log_activity("TIMER KEY PRESS MODE: Dừng trong khi chờ chu kỳ.")
            break

        # Thực hiện nhấn phím 'e'
        try:
            keyboard.press_and_release('e')
            update_status(f"TIMER KEY PRESS MODE: Đã nhấn phím 'E'. Chu kỳ tiếp: {interval_seconds:.2f}s", "#ccffcc")
            log_activity(f"TIMER KEY PRESS: Nhấn phím 'e' thành công.")
        except Exception as e:
            update_status("TIMER KEY PRESS MODE: Lỗi nhấn phím!", "#ff0000")
            log_activity(f"LỖI TIMER KEY PRESS: Nhấn phím 'e' thất bại: {e}")

# =====================================
# HÀM THEO DÕI & CLICK (FISHING MODE - Giữ nguyên)
# =====================================

# CẬP NHẬT THAM SỐ: Thêm 'delay'
def watch_pixel(rel_x, rel_y, window_title, threshold, a, delay, is_five_points_mode):
    global running, selected_window_rect, last_action_time, pixel_offset_a, action_delay

    pixel_offset_a = a
    action_delay = delay # Gán giá trị độ trễ từ UI

    # Lấy màu/mã HEX BAN ĐẦU (chỉ lấy 1 điểm center để làm màu gốc)
    def get_initial_color(win_left, win_top, rel_x, rel_y):
        abs_x = win_left + rel_x
        abs_y = win_top + rel_y
        abs_x, abs_y = clamp_coords(abs_x, abs_y)
        old_color_rgb = get_single_pixel_color(abs_x, abs_y)
        old_hex = rgb_to_hex(old_color_rgb)
        return old_color_rgb, old_hex, abs_x, abs_y

    old_color_rgb = None
    old_hex = "#XXXXXX"
    abs_x, abs_y = 0, 0

    while running:
        # Cố gắng lấy cửa sổ
        try:
            win = gw.getWindowsWithTitle(window_title)[0]
            win_left, win_top = win.left, win.top
            selected_window_rect = (win.left, win.top, win.width, win.height)
            selected_window = window_title  # Lưu lại tên cửa sổ
        except Exception:
            update_status("Cửa sổ bị đóng hoặc đổi tên!")
            log_activity(f"DỪNG: Cửa sổ '{window_title}' không được tìm thấy.")
            running = False
            break

        # Kiểm tra đầu vào
        try:
            rel_x = int(rel_x)
            rel_y = int(rel_y)
            threshold = float(threshold)
            a = int(a)
            # THAY ĐỔI: Kiểm tra delay
            delay = float(delay)
        except Exception:
            update_status("Lỗi: tham số không hợp lệ!")
            log_activity("LỖI KHỞI TẠO: Tọa độ/Ngưỡng/Độ lệch/Độ trễ không phải là số.")
            running = False
            break

        # Khởi tạo thời điểm hành động đầu tiên
        if last_action_time == 0:
            last_action_time = time.time()

        # Lấy màu ban đầu
        old_color_rgb, old_hex, abs_x, abs_y = get_initial_color(win_left, win_top, rel_x, rel_y)

        # Gửi màu hiện tại (Màu cũ) và màu rỗng (Màu mới) về UI
        if color_callback:
            color_callback(old_hex, "")

        # --- Vòng lặp theo dõi nhỏ ---
        while running:
            # Kiểm tra lại cửa sổ trong vòng lặp nhỏ
            try:
                win = gw.getWindowsWithTitle(window_title)[0]
                win_left, win_top = win.left, win.top
            except Exception:
                update_status("Cửa sổ bị đóng hoặc đổi tên!")
                log_activity(f"DỪNG: Cửa sổ '{window_title}' không được tìm thấy (vòng lặp nhỏ).")
                running = False
                break

            abs_x = win_left + rel_x
            abs_y = win_top + rel_y
            abs_x, abs_y = clamp_coords(abs_x, abs_y)

            current_time = time.time()

            # ========================================================
            # LOGIC IDLE TIMEOUT
            # ========================================================
            if current_time - last_action_time >= IDLE_TIMEOUT:
                # ... (Logic Recovery giữ nguyên) ...
                update_status(f"Hồi phục: Không click trong {IDLE_TIMEOUT}s. Chạy Space...", "#ff8800")
                log_activity(f"RECOVERY: IDLE TIMEOUT ({IDLE_TIMEOUT}s). Chạy hành động hồi phục.")

                # 1. Chạy nút "space"
                try:
                    keyboard.press_and_release("space")
                    log_activity("RECOVERY: Gửi lệnh 'space' thành công.")
                except Exception as e:
                    log_activity(f"LỖI RECOVERY: Gửi lệnh 'space' thất bại: {e}")

                if not sleep_may_stop(3):
                    log_activity("RECOVERY: Dừng trong khi chờ 3s.")
                    break

                # 2. Chạy nút "space"
                try:
                    keyboard.press_and_release("space")
                    log_activity("RECOVERY: Gửi lệnh 'space' thành công.")
                except Exception as e:
                    log_activity(f"LỖI RECOVERY: Gửi lệnh 'space' thất bại: {e}")

                if not sleep_may_stop(5):
                    log_activity("RECOVERY: Dừng trong khi chờ 5s.")
                    break

                # 3. Click chuột vào vị trí đang theo dõi
                try:
                    pyautogui.click(abs_x, abs_y)
                    log_activity(f"RECOVERY: Click tại ({abs_x}, {abs_y}) thành công.")
                except Exception as e:
                    log_activity(f"LỖI RECOVERY: Click thất bại: {e}")

                last_action_time = time.time()

                if not sleep_may_stop(3):
                    log_activity("RECOVERY: Dừng trong khi chờ 3s.")
                    break

                # Thoát vòng lặp nhỏ để quay lại vòng lặp lớn (tải lại màu cũ)
                break
            # ========================================================

            # --- LOGIC KIỂM TRA PIXEL MỚI ---

            # Khai báo biến tạm thời để lưu màu mới có KC lớn nhất
            new_color_to_log_hex = None
            new_color_to_log_rgb = None
            khoang_cach_mau = 0.0

            # Lấy màu pixel hiện tại (Tùy theo chế độ 1 hay 5 điểm)
            if is_five_points_mode:
                # Lấy 5 màu (center, x+a, x-a, y+a, y-a)
                new_color_rgbs = get_multi_pixel_colors(abs_x, abs_y, a)

                max_khoang_cach_mau = 0.0
                new_hex_of_max_diff = None
                new_rgb_of_max_diff = None

                # Duyệt qua 5 điểm để tìm điểm có KC lớn nhất so với old_hex
                for rgb in new_color_rgbs:
                    current_new_hex = rgb_to_hex(rgb)
                    # So sánh TỪNG điểm mới VỚI màu GỐC (center) cũ (old_hex)
                    current_khoang_cach_mau = tinh_khoang_cach_weighted_rgb(old_hex, current_new_hex)

                    if current_khoang_cach_mau > max_khoang_cach_mau:
                        max_khoang_cach_mau = current_khoang_cach_mau
                        new_hex_of_max_diff = current_new_hex
                        new_rgb_of_max_diff = rgb

                khoang_cach_mau = max_khoang_cach_mau  # Dùng khoảng cách MAX trong 5 điểm

                # Gán màu và KC tối đa cho biến chung
                new_color_to_log_hex = new_hex_of_max_diff
                new_color_to_log_rgb = new_rgb_of_max_diff

                # Kiểm tra nếu KC không thay đổi (giống hệt logic 1 điểm)
                if khoang_cach_mau <= 0.0:
                    # Nếu không khác biệt, tiếp tục vòng lặp nhỏ (không tạo log chi tiết)
                    time.sleep(0.01)
                    continue

            else:
                # Chế độ 1 điểm
                center_new_rgb = get_single_pixel_color(abs_x, abs_y)
                new_hex_for_ui = rgb_to_hex(center_new_rgb)

                if center_new_rgb == old_color_rgb:
                    # Chế độ 1 điểm đã có logic này, chỉ cần continue
                    continue

                # TÍNH KHOẢNG CÁCH MÀU (Chế độ 1 điểm)
                khoang_cach_mau = tinh_khoang_cach_weighted_rgb(old_hex, new_hex_for_ui)

                # Gán màu và KC cho biến chung
                new_color_to_log_hex = new_hex_for_ui
                new_color_to_log_rgb = center_new_rgb

            # --- LOGIC XỬ LÝ CHUNG (CÓ THAY ĐỔI / CHUNG CHO CẢ 1 ĐIỂM VÀ 5 ĐIỂM) ---

            # Chỉ chạy khi có khoang_cach_mau > 0.0

            if color_callback:
                # Gửi màu cũ và màu mới (màu có KC lớn nhất) về UI
                color_callback(old_hex, new_color_to_log_hex)

            update_status(f"{old_hex} ⇨ {new_color_to_log_hex} ⟹ KC={khoang_cach_mau:.2f} | Ngưỡng: {threshold}",
                          new_color_to_log_hex)

            # CHỈ CLICK KHI KHOẢNG CÁCH > NGƯỠNG
            if khoang_cach_mau > threshold:

                log_activity(
                    f"{old_hex} ⇨ {new_color_to_log_hex} ⟹ KC={khoang_cach_mau:.2f} > Ngưỡng={threshold}. Bắt đầu chuỗi hành động.")

                try:
                    pyautogui.click(abs_x, abs_y)
                    log_activity("ACTION 1: Click chính thành công.")
                except Exception as e:
                    log_activity(f"LỖE ACTION 1: Click chính thất bại: {e}")

                # Cập nhật màu cũ và hex mới (dùng màu mới được phát hiện)
                old_color_rgb = new_color_to_log_rgb  # Cập nhật màu RGB cũ
                old_hex = new_color_to_log_hex

                # Cập nhật thời gian hành động cuối cùng
                last_action_time = time.time()

                # Thực hiện các bước Auto sau click
                # THAY ĐỔI: Sử dụng biến action_delay thay vì hằng số 7
                if not sleep_may_stop(action_delay):
                    log_activity(f"CHUỖI ACTION: Dừng trong khi chờ {action_delay}s.")
                    break

                try:
                    keyboard.press_and_release("space")
                    log_activity("ACTION 2: Gửi lệnh 'space' thành công.")
                except Exception as e:
                    log_activity(f"LỖI ACTION 2: Gửi lệnh 'space' thất bại: {e}")

                if not sleep_may_stop(2):
                    log_activity("CHUỖI ACTION: Dừng trong khi chờ 2s (sau space).")
                    break

                try:
                    click_x, click_y = clamp_coords(abs_x + 10, abs_y + 100)
                    pyautogui.click(click_x, click_y)
                    log_activity(f"ACTION 3: Click phụ tại ({click_x}, {click_y}) thành công.")
                except Exception as e:
                    log_activity(f"LỖI ACTION 3: Click phụ thất bại: {e}")

                if not sleep_may_stop(2):
                    log_activity("CHUỖI ACTION: Dừng trong khi chờ 2s (cuối chuỗi).")
                    break

            else:
                # Nếu khoảng cách màu NHỎ (KC > 0.0 nhưng <= Ngưỡng)
                log_activity(f"{old_hex} ⇨ {new_color_to_log_hex} ⟹ KC={khoang_cach_mau:.2f} <= Ngưỡng={threshold}")

                # Cập nhật màu cũ và hex mới (Nếu không click, màu hiện tại là màu mới được phát hiện)
                old_color_rgb = new_color_to_log_rgb  # Cập nhật màu RGB cũ
                old_hex = new_color_to_log_hex

            # Sau khi xử lý xong (click hoặc không), cần cập nhật lại trạng thái màu ban đầu
            current_hex_after_check = rgb_to_hex(old_color_rgb)
            if color_callback:
                color_callback(current_hex_after_check, "")

            # Thoát vòng lặp nhỏ để lấy lại màu ban đầu
            break

        time.sleep(0.01)  # TỐI ƯU (Đảm bảo độ trễ tối thiểu giữa các lần kiểm tra lớn)


# =====================================
# HÀM BÊN NGOÀI (CẦN EXPORT CHO CONTROLLER)
# =====================================

# CẬP NHẬT THAM SỐ: Thêm 'mode' và 'key_interval'
def start_watching(rel_x=0, rel_y=0, window_title="", mode="FISHING", threshold=0, a=0, delay=0, interval=0, key_interval=0.5):
    """Bắt đầu luồng theo dõi pixel/click/nhấn phím"""
    global running, last_action_time, selected_window, current_mode

    # CHẾ ĐỘ HARVEST KHÔNG CẦN CỬA SỔ
    if mode != "HARVEST" and not window_title:
        update_status("Lỗi: Chưa chọn cửa sổ mục tiêu!", "#ffcccc")
        return

    # Gán tên cửa sổ và chế độ trước khi bắt đầu
    selected_window = window_title
    current_mode = mode

    running = True
    last_action_time = time.time()  # Reset thời gian khi bắt đầu

    # Cập nhật trạng thái và log dựa trên chế độ
    if mode == "FISHING":
        current_mode_text = '5 điểm' if is_five_points_mode else '1 điểm'
        log_activity(
            f"START (FISHING). Cửa sổ: {window_title}, Tọa độ: ({rel_x},{rel_y}), Ngưỡng: {threshold}, Độ trễ: {delay}s, Chế độ: {current_mode_text}")
        update_status(f"Auto Câu Cá đang bật ({current_mode_text}) | Ngưỡng: {threshold} | Trễ: {delay}s", "#ccffcc")

        # CHUYỂN SANG HÀM GỐC watch_pixel
        threading.Thread(target=watch_pixel, args=(rel_x, rel_y, window_title, threshold, a, delay, is_five_points_mode),
                         daemon=True).start()

    elif mode == "CRUSH_ROCKS":
        log_activity(
            f"START (CRUSH ROCKS). Cửa sổ: {window_title}, Tọa độ: ({rel_x},{rel_y}), Chu kỳ: {interval}s")
        update_status(f"Auto Đập Đá đang bật | Chu kỳ: {interval}s", "#ccffcc")

        # CHUYỂN SANG HÀM MỚI timer_click_loop
        threading.Thread(target=timer_click_loop, args=(rel_x, rel_y, window_title, interval),
                         daemon=True).start()

    elif mode == "HARVEST":
        log_activity(f"START (HARVEST). Chu kỳ nhấn phím 'e': {key_interval}s")
        update_status(f"Auto Thu Hoạch đang bật | Chu kỳ: {key_interval}s", "#ccffcc")

        # CHUYỂN SANG HÀM MỚI timer_key_press_loop
        threading.Thread(target=timer_key_press_loop, args=(key_interval,),
                         daemon=True).start()


def stop_watching():
    """Dừng luồng theo dõi"""
    global running, current_mode
    if running:
        running = False
        log_activity(f"STOP ({current_mode}): Auto Clicker đã dừng.")
        update_status("Auto Clicker tạm dừng", "")  # Màu nền mặc định


# =====================================
# HÀM CHỌN TỌA ĐỘ (Giữ nguyên)
# =====================================
waiting_for_click = False


def enable_pick_mode(window_title):
    """Bắt đầu quá trình chờ người dùng click để lấy tọa độ"""
    global waiting_for_click, selected_window_rect, selected_window
    import mouse

    # Cần kiểm tra lại cửa sổ trước khi vào pick mode
    try:
        win = gw.getWindowsWithTitle(window_title)[0]
        selected_window_rect = (win.left, win.top, win.width, win.height)
        selected_window = window_title
    except Exception:
        if status_callback:
            messagebox.showwarning("Chưa chọn cửa sổ", "Bạn chưa chọn cửa sổ mục tiêu!")
        log_activity("LỖI PICK MODE: Chưa chọn cửa sổ mục tiêu.")
        return

    waiting_for_click = True
    update_status("Chọn tọa độ: chờ chuột nhả, sau đó click vị trí cần chọn...")
    log_activity("PICK MODE: Chế độ chọn tọa độ được kích hoạt.")
    threading.Thread(target=wait_for_mouse_click, daemon=True).start()


def wait_for_mouse_click():
    """Luồng chờ chuột click để lấy tọa độ tương đối"""
    global waiting_for_click, selected_window_rect, selected_window
    import mouse

    release_wait_start = time.time()
    # Chờ chuột nhả ra (để tránh lấy click bắt đầu)
    while mouse.is_pressed("left"):
        if time.time() - release_wait_start > 5:
            log_activity("PICK MODE: Quá 5s chờ chuột nhả, thoát.")
            waiting_for_click = False
            return
        time.sleep(0.01)

    time.sleep(0.01)

    while waiting_for_click:
        try:
            if mouse.is_pressed("left"):
                abs_x, abs_y = pyautogui.position()

                if not selected_window_rect:
                    if status_callback:
                        messagebox.showwarning("Lỗi", "Không xác định được cửa sổ mục tiêu khi lấy tọa độ.")
                    log_activity("LỖI PICK MODE: Không xác định được cửa sổ khi lấy tọa độ.")
                    waiting_for_click = False
                    return

                win_left, win_top, _, _ = selected_window_rect
                rel_x = abs_x - win_left
                rel_y = abs_y - win_top

                waiting_for_click = False

                # Gọi callback để UI cập nhật
                if log_save_callback:
                    log_save_callback(rel_x, rel_y)  # Controller sẽ tự động lưu vào positions.log

                update_status("Đã chọn tọa độ")
                log_activity(f"PICK MODE: Đã chọn tọa độ tương đối ({rel_x},{rel_y}).")
                return
        except Exception as e:
            log_activity(f"LỖI PICK MODE: Lỗi trong quá trình chờ click: {e}")
            waiting_for_click = False
            return

        time.sleep(0.01)