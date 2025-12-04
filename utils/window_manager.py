#window_manager.py
import tkinter as tk


def get_screen_dimensions(window):
    """Lấy kích thước màn hình làm việc (có tính đến các thanh tác vụ,...)"""
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    return screen_width, screen_height


def center_window_on_screen(window, width, height):
    """Tính toán tọa độ để căn giữa cửa sổ trên MÀN HÌNH"""
    screen_width, screen_height = get_screen_dimensions(window)

    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)

    return f"{width}x{height}+{x}+{y}"


def position_main_app_right_center(window, width, height):
    """
    Tính toán tọa độ để đặt cửa sổ chính ở:
    - Cạnh phải màn hình
    - Căn giữa theo chiều dọc
    - CÁCH CẠNH MÀN HÌNH 3% (khoảng đệm)
    """
    screen_width, screen_height = get_screen_dimensions(window)

    # Tính khoảng đệm 3% chiều rộng màn hình
    padding_x = int(screen_width * 0.03)

    # Vị trí X: Chiều rộng màn hình - Chiều rộng cửa sổ - Khoảng đệm 3%
    x = screen_width - width - padding_x

    # Căn giữa dọc: Tọa độ Y = (Chiều cao màn hình - Chiều cao cửa sổ) / 2
    y = (screen_height // 2) - (height // 2)

    # Đảm bảo x không nhỏ hơn 0
    x = max(0, x)

    return f"{width}x{height}+{x}+{y}"


def center_toplevel_on_parent(child_window, parent_window, width, height):
    """
    Tính toán tọa độ để căn giữa cửa sổ con (Toplevel) trên CỬA SỔ CHA (Parent)
    """
    if not parent_window or not parent_window.winfo_exists():
        # Nếu cửa sổ cha không tồn tại, căn giữa trên màn hình
        return center_window_on_screen(child_window, width, height)

    # Lấy tọa độ và kích thước của cửa sổ cha
    parent_x = parent_window.winfo_x()
    parent_y = parent_window.winfo_y()
    parent_width = parent_window.winfo_width()
    parent_height = parent_window.winfo_height()

    # Tính toán tọa độ X và Y mới
    x = parent_x + (parent_width // 2) - (width // 2)
    y = parent_y + (parent_height // 2) - (height // 2)

    # Đảm bảo cửa sổ con không bị trồi ra ngoài màn hình (optional, but good practice)
    screen_width, screen_height = get_screen_dimensions(child_window)
    x = max(0, min(x, screen_width - width))
    y = max(0, min(y, screen_height - height))

    return f"{width}x{height}+{x}+{y}"