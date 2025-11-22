import pyautogui
import threading
import time
import keyboard
import pygetwindow as gw
from utils.coords import clamp_coords, get_surrounding_pixels, rgb_to_hex, tinh_khoang_cach_weighted_rgb
from utils.file_io import log_activity  # IMPORT HÀM MỚI
from tkinter import messagebox

# Biến toàn cục để kiểm soát
running = False
selected_window = None  # Tên cửa sổ (string)
selected_window_rect = None  # (left, top, width, height)
status_callback = None
color_callback = None
log_save_callback = None

# BIẾN MỚI: Theo dõi thời điểm hành động cuối cùng
last_action_time = time.time()
# HẰNG SỐ MỚI: Thời gian chờ tối đa (60 giây)
IDLE_TIMEOUT = 60


def set_callbacks(status_cb, color_cb, log_save_cb):
    """Thiết lập các hàm callback để giao tiếp với UI/Controller"""
    global status_callback, color_callback, log_save_callback
    status_callback = status_cb
    color_callback = color_cb
    log_save_callback = log_save_cb


def update_status(text, color=None):
    """Cập nhật trạng thái qua callback"""
    if status_callback:
        status_callback(text, color)


# =====================================
# HÀM THEO DÕI & CLICK
# =====================================
def sleep_may_stop(seconds):
    """Dừng luồng an toàn, kiểm tra biến 'running'"""
    global running
    steps = int(seconds / 0.05) if seconds > 0 else 0
    for _ in range(steps):
        if not running:
            return False
        time.sleep(0.05)
    return True


# THÊM THAM SỐ threshold
def watch_pixel(rel_x, rel_y, window_title, radius, threshold):
    global running, selected_window_rect, last_action_time

    # Khởi tạo thời điểm hành động đầu tiên
    last_action_time = time.time()
    log_activity(f"START theo dõi. Cửa sổ: {window_title}, Tọa độ: ({rel_x},{rel_y}), Ngưỡng: {threshold}")

    while running:
        # Cố gắng lấy cửa sổ
        try:
            win = gw.getWindowsWithTitle(window_title)[0]
            win_left, win_top = win.left, win.top
            selected_window_rect = (win.left, win.top, win.width, win.height)
        except Exception:
            update_status("Cửa sổ bị đóng hoặc đổi tên!")
            log_activity(f"DỪNG: Cửa sổ '{window_title}' không được tìm thấy.")
            running = False
            break

        # Kiểm tra đầu vào
        try:
            rel_x = int(rel_x)
            rel_y = int(rel_y)
            radius = int(radius)
            # threshold đã được validate trong controller, nhưng nên ép kiểu float
            threshold = float(threshold)
        except Exception:
            update_status("Lỗi: tham số không hợp lệ!")
            log_activity("LỖI KHỞI TẠO: Tọa độ/Bán kính/Ngưỡng không phải là số.")
            running = False
            break

        abs_x = win_left + rel_x
        abs_y = win_top + rel_y
        abs_x, abs_y = clamp_coords(abs_x, abs_y)

        # Lấy màu pixel khởi tạo
        surrounding_pixels = get_surrounding_pixels(abs_x, abs_y, radius=radius)
        old_colors = surrounding_pixels
        old_hex = rgb_to_hex(old_colors[0])

        # Gửi màu hiện tại (Màu cũ) và màu rỗng (Màu mới) về UI
        if color_callback:
            color_callback(old_hex, "")

        update_status(f"Auto đang bật tại ({rel_x},{rel_y}) | Ngưỡng: {threshold}", old_hex)

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

            new_surrounding_pixels = get_surrounding_pixels(abs_x, abs_y, radius=radius)
            current_time = time.time()

            # ========================================================
            # LOGIC IDLE TIMEOUT
            # ========================================================
            if current_time - last_action_time >= IDLE_TIMEOUT:

                update_status(f"Hồi phục: Không click trong {IDLE_TIMEOUT}s. Chạy Space...", "#ff8800")
                log_activity(f"RECOVERY: IDLE TIMEOUT ({IDLE_TIMEOUT}s). Chạy hành động hồi phục.")

                # 1. Chạy nút "space"
                try:
                    keyboard.press_and_release("space")
                    log_activity("RECOVERY: Gửi lệnh 'space' thành công.")
                except Exception as e:
                    log_activity(f"LỖI RECOVERY: Gửi lệnh 'space' thất bại: {e}")

                # 2. Chờ 3 giây
                if not sleep_may_stop(3):
                    log_activity("RECOVERY: Dừng trong khi chờ 3s.")
                    break

                # 3. Chạy nút "space"
                try:
                    keyboard.press_and_release("space")
                    log_activity("RECOVERY: Gửi lệnh 'space' thành công.")
                except Exception as e:
                    log_activity(f"LỖI RECOVERY: Gửi lệnh 'space' thất bại: {e}")

                # 4. Chờ 5 giây
                if not sleep_may_stop(5):
                    log_activity("RECOVERY: Dừng trong khi chờ 5s.")
                    break

                # 5. Click chuột vào vị trí đang theo dõi
                try:
                    pyautogui.click(abs_x, abs_y)
                    log_activity(f"RECOVERY: Click tại ({abs_x}, {abs_y}) thành công.")
                except Exception as e:
                    log_activity(f"LỖI RECOVERY: Click thất bại: {e}")

                # Cập nhật thời điểm hành động cuối cùng
                last_action_time = time.time()

                if not sleep_may_stop(3):
                    log_activity("RECOVERY: Dừng trong khi chờ 3s.")
                    break

                # Thoát vòng lặp nhỏ để quay lại vòng lặp lớn (tải lại màu cũ)
                break
            # ========================================================

            # Logic kiểm tra: Nếu TẤT CẢ pixel đều khác màu cũ
            if all([new_color != old_color for new_color, old_color in zip(new_surrounding_pixels, old_colors)]):

                new_hex = rgb_to_hex(new_surrounding_pixels[0])

                # TÍNH KHOẢNG CÁCH MÀU
                khoang_cach_mau = tinh_khoang_cach_weighted_rgb(old_hex, new_hex)

                # Gửi màu cũ (trước click) và màu mới (sau click) về UI (Dù có click hay không)
                if color_callback:
                    color_callback(old_hex, new_hex)

                update_status(f"Phát hiện thay đổi! KC={khoang_cach_mau:.2f} | Ngưỡng: {threshold}", new_hex)

                # CHỈ CLICK KHI KHOẢNG CÁCH > NGƯỠNG
                if khoang_cach_mau > threshold:  # SỬ DỤNG THAM SỐ THRESHOLD

                    log_activity(
                        f"PHÁT HIỆN: {old_hex} -> {new_hex}: KC={khoang_cach_mau:.2f} > Ngưỡng={threshold} -> CLICK")

                    try:
                        pyautogui.click(abs_x, abs_y)
                        log_activity("ACTION 1: Click chính thành công.")
                    except Exception as e:
                        log_activity(f"LỖI ACTION 1: Click chính thất bại: {e}")

                    # Cập nhật màu cũ và hex mới
                    old_colors = new_surrounding_pixels
                    old_hex = new_hex

                    # Cập nhật thời gian hành động cuối cùng
                    last_action_time = time.time()

                    # Thực hiện các bước Auto sau click
                    if not sleep_may_stop(7):
                        log_activity("CHUỖI ACTION: Dừng trong khi chờ 7s.")
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
                        click_x, click_y = clamp_coords(abs_x + 100, abs_y + 10)
                        pyautogui.click(click_x, click_y)
                        log_activity(f"ACTION 3: Click phụ tại ({click_x}, {click_y}) thành công.")
                    except Exception as e:
                        log_activity(f"LỖI ACTION 3: Click phụ thất bại: {e}")

                    if not sleep_may_stop(2):
                        log_activity("CHUỖI ACTION: Dừng trong khi chờ 2s (cuối chuỗi).")
                        break

                else:
                    # Nếu khoảng cách màu NHỎ (chỉ thay đổi nhẹ)
                    log_activity(f"PHÁT HIỆN: {old_hex} -> {new_hex} KC={khoang_cach_mau:.2f} <= Ngưỡng={threshold} -> KHÔNG CLICK")

                    # Dừng nhẹ để tránh vòng lặp quá nhanh
                    time.sleep(0.5)

                # Sau khi xử lý xong (click hoặc không), cần cập nhật lại trạng thái màu ban đầu
                current_hex_after_check = rgb_to_hex(old_colors[0])
                if color_callback:
                    color_callback(current_hex_after_check, "")

                # Thoát vòng lặp nhỏ để lấy lại màu ban đầu
                break

            time.sleep(0.01)
        time.sleep(0.5)


# =====================================
# HÀM BÊN NGOÀI (CẦN EXPORT CHO CONTROLLER)
# =====================================

# THÊM THAM SỐ threshold
def start_watching(rel_x, rel_y, window_title, radius, threshold):
    """Bắt đầu luồng theo dõi pixel và click"""
    global running, last_action_time

    if not window_title:
        update_status("Lỗi: Chưa chọn cửa sổ mục tiêu!", "#ffcccc")
        return

    running = True
    last_action_time = time.time()  # Reset thời gian khi bắt đầu
    update_status(f"Auto đang bật tại ({rel_x},{rel_y}) | Ngưỡng: {threshold}", "#ccffcc")
    # TRUYỀN THAM SỐ THRESHOLD VÀO LUỒNG
    threading.Thread(target=watch_pixel, args=(rel_x, rel_y, window_title, radius, threshold), daemon=True).start()


def stop_watching():
    """Dừng luồng theo dõi"""
    global running
    running = False
    log_activity("STOP: Auto Clicker đã dừng.")
    update_status("Auto Clicker tạm dừng", "")  # Màu nền mặc định


# =====================================
# HÀM CHỌN TỌA ĐỘ
# =====================================
waiting_for_click = False


def enable_pick_mode(window_title):
    """Bắt đầu quá trình chờ người dùng click để lấy tọa độ"""
    global waiting_for_click, selected_window_rect, selected_window
    import mouse

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
    global waiting_for_click, selected_window_rect
    import mouse

    release_wait_start = time.time()
    # Chờ chuột nhả ra (để tránh lấy click bắt đầu)
    while mouse.is_pressed("left"):
        if time.time() - release_wait_start > 5:
            log_activity("PICK MODE: Quá 5s chờ chuột nhả, thoát.")
            break
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
