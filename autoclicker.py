import pyautogui
import threading
import time
import keyboard
import pygetwindow as gw
from utils.coords import clamp_coords, get_surrounding_pixels, rgb_to_hex, tinh_khoang_cach_weighted_rgb
from tkinter import messagebox

# Biến toàn cục để kiểm soát
running = False
selected_window = None  # Tên cửa sổ (string)
selected_window_rect = None  # (left, top, width, height)
status_callback = None
color_callback = None
log_save_callback = None

# XÓA HẰNG SỐ NGUONG_CLICK. Bây giờ nó là tham số truyền vào từ UI


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
    global running, selected_window_rect

    while running:
        # Cố gắng lấy cửa sổ
        try:
            win = gw.getWindowsWithTitle(window_title)[0]
            win_left, win_top = win.left, win.top
            selected_window_rect = (win.left, win.top, win.width, win.height)
        except Exception:
            update_status("Cửa sổ bị đóng hoặc đổi tên!")
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
                running = False
                break

            abs_x = win_left + rel_x
            abs_y = win_top + rel_y
            abs_x, abs_y = clamp_coords(abs_x, abs_y)

            new_surrounding_pixels = get_surrounding_pixels(abs_x, abs_y, radius=radius)

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
                if khoang_cach_mau > threshold: # SỬ DỤNG THAM SỐ THRESHOLD

                    try:
                        pyautogui.click(abs_x, abs_y)
                        print(f"[AutoClicker] CLICK! KC={khoang_cach_mau:.2f}")
                    except Exception as e:
                        print("[watch_pixel] click failed 1:", e)

                    # Cập nhật màu cũ và hex mới
                    old_colors = new_surrounding_pixels
                    old_hex = new_hex

                    # Thực hiện các bước Auto sau click
                    if not sleep_may_stop(7):
                        break

                    try:
                        keyboard.press_and_release("space")
                    except Exception as e:
                        print("[watch_pixel] press space failed:", e)

                    if not sleep_may_stop(2):
                        break

                    try:
                        click_x, click_y = clamp_coords(abs_x - 50, abs_y - 50)
                        pyautogui.click(click_x, click_y)
                    except Exception as e:
                        print("[watch_pixel] click failed 2:", e)

                    if not sleep_may_stop(2):
                        break

                else:
                    # Nếu khoảng cách màu NHỎ (chỉ thay đổi nhẹ)
                    print(f"[AutoClicker] KHÔNG CLICK. KC={khoang_cach_mau:.2f} <= {threshold}")

                    # Dừng nhẹ để tránh vòng lặp quá nhanh
                    time.sleep(0.5)


                # Sau khi xử lý xong (click hoặc không), cần cập nhật lại trạng thái màu ban đầu
                current_hex_after_check = rgb_to_hex(old_colors[0])
                if color_callback:
                    color_callback(current_hex_after_check, "")

                # Thoát vòng lặp nhỏ để lấy lại màu ban đầu
                break

            time.sleep(0.05)
        time.sleep(0.1)


# =====================================
# HÀM BÊN NGOÀI (CẦN EXPORT CHO CONTROLLER)
# =====================================

# THÊM THAM SỐ threshold
def start_watching(rel_x, rel_y, window_title, radius, threshold):
    """Bắt đầu luồng theo dõi pixel và click"""
    global running

    if not window_title:
        update_status("Lỗi: Chưa chọn cửa sổ mục tiêu!", "#ffcccc")
        return

    running = True
    update_status(f"Auto đang bật tại ({rel_x},{rel_y}) | Ngưỡng: {threshold}", "#ccffcc")
    # TRUYỀN THAM SỐ THRESHOLD VÀO LUỒNG
    threading.Thread(target=watch_pixel, args=(rel_x, rel_y, window_title, radius, threshold), daemon=True).start()


def stop_watching():
    """Dừng luồng theo dõi"""
    global running
    running = False
    update_status("Auto Clicker tạm dừng", "") # Màu nền mặc định


# =====================================
# HÀM CHỌN TỌA ĐỘ (Đã bị thiếu, cần bổ sung lại)
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
        return

    waiting_for_click = True
    update_status("Chọn tọa độ: chờ chuột nhả, sau đó click vị trí cần chọn...")
    threading.Thread(target=wait_for_mouse_click, daemon=True).start()

def wait_for_mouse_click():
    """Luồng chờ chuột click để lấy tọa độ tương đối"""
    global waiting_for_click, selected_window_rect
    import mouse

    release_wait_start = time.time()
    # Chờ chuột nhả ra (để tránh lấy click bắt đầu)
    while mouse.is_pressed("left"):
        if time.time() - release_wait_start > 5:
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
                    waiting_for_click = False
                    return

                win_left, win_top, _, _ = selected_window_rect
                rel_x = abs_x - win_left
                rel_y = abs_y - win_top

                waiting_for_click = False

                # Gọi callback để UI cập nhật
                if log_save_callback:
                    log_save_callback(rel_x, rel_y)

                update_status("Đã chọn tọa độ")
                return
        except Exception as e:
            print("[wait_for_mouse_click] Lỗi:", e)
            waiting_for_click = False
            return

        time.sleep(0.01)