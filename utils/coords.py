#coord.py
import pyautogui
import numpy as np


# Giả định: Bạn đã có hàm này để giới hạn tọa độ tuyệt đối trong phạm vi màn hình
def clamp_coords(x, y):
    """Giới hạn tọa độ tuyệt đối trong phạm vi màn hình."""
    screen_width, screen_height = pyautogui.size()
    x = max(0, min(x, screen_width - 1))
    y = max(0, min(y, screen_height - 1))
    return x, y


def rgb_to_hex(rgb):
    """Chuyển đổi RGB tuple sang mã HEX (ví dụ: (255, 0, 0) -> #FF0000)"""
    if rgb is None:
        return "#XXXXXX"
    # Kiểm tra nếu rgb không phải tuple hợp lệ
    if not isinstance(rgb, tuple) or len(rgb) < 3:
        return "#XXXXXX"

    return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2]).upper()


def hex_to_rgb(hex_color):
    """Chuyển đổi mã HEX sang RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def tinh_khoang_cach_weighted_rgb(hex1, hex2):
    """
    Tính khoảng cách màu RGB có trọng số (weighted Euclidean distance).
    Sử dụng trọng số (3, 4, 2) cho R, G, B để mô phỏng sự nhạy cảm của mắt người.
    """
    try:
        rgb1 = np.array(hex_to_rgb(hex1))
        rgb2 = np.array(hex_to_rgb(hex2))
    except ValueError:
        return 999.0  # Trả về giá trị lớn nếu có lỗi chuyển đổi

    diff = rgb1 - rgb2
    weights = np.array([3, 4, 2])  # Trọng số cho R, G, B

    # Công thức khoảng cách có trọng số: sqrt(w_r*dr^2 + w_g*dg^2 + w_b*db^2)
    distance = np.sqrt(np.sum(weights * diff ** 2))

    # Chia cho 9 (tổng trọng số) để chuẩn hóa
    return float(distance / 9.0)


# HÀM MỚI/CẬP NHẬT: Chỉ lấy một pixel
def get_single_pixel_color(abs_x, abs_y):
    """
    Chỉ trả về màu RGB của một pixel duy nhất tại tọa độ tuyệt đối.
    """
    try:
        # Lấy màu tại pixel (abs_x, abs_y)
        r, g, b = pyautogui.pixel(abs_x, abs_y)
        return (r, g, b)
    except Exception as e:
        # Xử lý lỗi nếu việc đọc pixel thất bại
        return (0, 0, 0)


# HÀM MỚI: Lấy 5 màu pixel
def get_multi_pixel_colors(center_x, center_y, a):
    """
    Trả về màu RGB của 5 pixel: trung tâm, (x+a, y), (x-a, y), (x, y+a), (x, y-a).
    a là độ lệch.
    """
    points = [
        (center_x, center_y),  # Center
        (center_x + a, center_y),  # Right
        (center_x - a, center_y),  # Left
        (center_x, center_y + a),  # Down
        (center_x, center_y - a)  # Up
    ]

    colors = []

    for x, y in points:
        # Đảm bảo tọa độ nằm trong màn hình
        clamped_x, clamped_y = clamp_coords(x, y)
        colors.append(get_single_pixel_color(clamped_x, clamped_y))

    return colors