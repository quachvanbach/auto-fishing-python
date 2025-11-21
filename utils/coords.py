import pyautogui
import math


# =====================================
# HÀM XỬ LÝ TỌA ĐỘ
# =====================================

def clamp_coords(x, y):
    """Giới hạn tọa độ trong phạm vi màn hình"""
    screen_width, screen_height = pyautogui.size()

    # Đảm bảo x, y không nhỏ hơn 0
    x = max(0, x)
    y = max(0, y)

    # Đảm bảo x, y không vượt quá kích thước màn hình
    x = min(screen_width - 1, x)
    y = min(screen_height - 1, y)

    return x, y


def safe_get_pixel(x, y):
    """Lấy màu pixel an toàn, xử lý lỗi nếu có"""
    try:
        return pyautogui.pixel(x, y)
    except Exception:
        # Trả về màu đen nếu không thể lấy pixel (lỗi boundary, etc.)
        return (0, 0, 0)


def get_surrounding_pixels(abs_x, abs_y, radius=0):
    """
    Lấy màu của pixel tại (abs_x, abs_y) và các pixel xung quanh
    theo bán kính (radius). Trả về danh sách các bộ ba RGB.
    """
    pixels = []

    if radius == 0:
        # Trường hợp mặc định: chỉ lấy 1 pixel
        clamped_x, clamped_y = clamp_coords(abs_x, abs_y)
        pixels.append(safe_get_pixel(clamped_x, clamped_y))
        return pixels

    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            clamped_x, clamped_y = clamp_coords(abs_x + dx, abs_y + dy)
            pixels.append(safe_get_pixel(clamped_x, clamped_y))

    return pixels


# =====================================
# HÀM XỬ LÝ MÀU
# =====================================

def rgb_to_hex(rgb):
    """Chuyển bộ ba (R, G, B) sang mã Hex (#RRGGBB)"""
    return f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'


def hex_to_rgb(hex_color):
    """
    Chuyển đổi màu Hex (#RRGGBB) sang bộ ba (R, G, B)
    """
    if not hex_color or hex_color == "#XXXXXX":
        return 0, 0, 0
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def tinh_khoang_cach_weighted_rgb(hex_mau_1, hex_mau_2):
    """
    Tính khoảng cách Weighted RGB (có trọng số) giữa hai màu Hex
    Ngưỡng đề xuất: Khoảng 30-50.
    """
    # 1. Chuyển Hex sang RGB (0-255)
    r1, g1, b1 = hex_to_rgb(hex_mau_1)
    r2, g2, b2 = hex_to_rgb(hex_mau_2)

    # 2. Tính toán các thành phần cần thiết
    delta_r = r1 - r2
    delta_g = g1 - g2
    delta_b = b1 - b2

    mean_r = (r1 + r2) / 2

    # 3. Áp dụng công thức Weighted RGB (Mean RGB)
    if mean_r < 128:
        # Màu tối hơn: R và B có trọng số cao hơn G
        khoang_cach_binh_phuong = (2 * delta_r ** 2) + (4 * delta_g ** 2) + (3 * delta_b ** 2)
    else:
        # Màu sáng hơn: R và B có trọng số ít hơn G
        khoang_cach_binh_phuong = (3 * delta_r ** 2) + (4 * delta_g ** 2) + (2 * delta_b ** 2)

    # 4. Tính khoảng cách cuối cùng
    khoang_cach = math.sqrt(khoang_cach_binh_phuong)

    return khoang_cach