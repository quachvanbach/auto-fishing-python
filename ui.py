import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
import threading
import os
from datetime import datetime
from controller import (
    refresh_window_list, handle_start, handle_stop, handle_pick_mode,
    init_controller, handle_view_log_file, set_pixel_mode_on_off,
    load_last_known_state
)
from utils.file_io import log_activity, get_log_content_and_path
from utils.window_manager import (
    center_window_on_screen, position_main_app_right_center, center_toplevel_on_parent
)

# external libs (mouse/keyboard/pygetwindow)
try:
    import mouse
except ImportError:
    messagebox.showerror("Lỗi", "Thiếu module 'mouse'. Hãy cài bằng: pip install mouse")
    raise

try:
    import keyboard
except ImportError:
    messagebox.showerror("Lỗi", "Thiếu module 'keyboard'. Hãy cài bằng: pip install keyboard")
    raise

try:
    import pygetwindow as gw
except ImportError:
    messagebox.showerror("Lỗi", "Thiếu module 'pygetwindow'. Hãy cài bằng: pip install pygetwindow")
    raise

# Biến UI toàn cục
root = None
start_screen = None  # Cửa sổ Start
main_app_window = None  # Cửa sổ ứng dụng chính
combo_window = None
entry_x = None
entry_y = None
entry_threshold = None
entry_a = None  # Độ lệch A
# BIẾN MỚI: Độ trễ sau Click
entry_delay_after_click = None
status_label = None
color_canvas_before = None
color_hex_before = None
color_canvas_after = None
color_hex_after = None
tree = None  # Treeview cũ (loại bỏ)
activity_log_text = None  # Text widget mới cho Activity Log
pixel_mode_var = None  # Biến trạng thái cho chế độ 1/5 điểm


# =====================================
# HÀM CẬP NHẬT UI (Callback cho Controller/Autoclicker)
# =====================================

def update_status(text, color=None):
    """Cập nhật nhãn trạng thái"""
    global status_label
    if status_label and main_app_window:
        status_label.config(text=text, bg=color if color else main_app_window.cget("bg"))
        update_activity_log(f"{text}", color)


def update_activity_log(message, color=None):
    """Cập nhật nội dung Activity Log trong UI chính"""
    global activity_log_text
    if activity_log_text:
        current_time = datetime.now().strftime("[%H:%M:%S]")
        activity_log_text.config(state=tk.NORMAL)

        # Thêm tag màu nếu có
        activity_log_text.insert(tk.END, f"{current_time} {message}\n")

        # Tự động cuộn xuống cuối
        activity_log_text.see(tk.END)
        activity_log_text.config(state=tk.DISABLED)


def set_coordinate_entries(rel_x, rel_y):
    """Cập nhật ô nhập tọa độ"""
    global entry_x, entry_y
    if entry_x and entry_y:
        entry_x.delete(0, tk.END)
        entry_x.insert(0, rel_x)
        entry_y.delete(0, tk.END)
        entry_y.insert(0, rel_y)


def set_window_entry(window_title):
    """Cập nhật combobox cửa sổ"""
    global combo_window
    if combo_window:
        combo_window.set(window_title)


def load_log_list():
    """Tải dữ liệu log (Chức năng cũ không dùng nữa, giữ hàm rỗng)"""
    pass


def draw_color_circle(canvas, color_hex):
    """Vẽ hình tròn màu lên canvas (hoặc làm trống nếu màu rỗng)"""
    canvas.delete("all")
    if color_hex and color_hex != "#XXXXXX" and color_hex != "":
        # Lấy kích thước canvas
        def _draw():
            width = canvas.winfo_width()
            height = canvas.winfo_height()
            if width > 0 and height > 0 and main_app_window:
                radius = 9
                canvas.create_oval(
                    width // 2 - radius,
                    height // 2 - radius,
                    width // 2 + radius,
                    width // 2 + radius,
                    fill=color_hex,
                    outline="#444444"
                )
            elif main_app_window:  # Thử lại chỉ khi cửa sổ chính còn tồn tại
                canvas.after(50, _draw)

        # Sử dụng main_app_window để đảm bảo có cửa sổ chính
        if main_app_window:
            _draw()
    elif main_app_window:
        # Đặt màu nền mặc định
        canvas.config(bg=main_app_window.cget("bg"))


def update_color_labels(old_hex, new_hex):
    """Callback để cập nhật màu và mã hex cho hai trạng thái (trước/sau)"""
    global color_canvas_before, color_hex_before, color_canvas_after, color_hex_after

    # 1. Màu trước khi thay đổi (Old Color)
    if color_canvas_before:
        draw_color_circle(color_canvas_before, old_hex)
    if color_hex_before:
        color_hex_before.config(state=tk.NORMAL)
        color_hex_before.delete(0, tk.END)
        color_hex_before.insert(0, old_hex if old_hex else "#XXXXXX")
        color_hex_before.config(state=tk.DISABLED)

    # 2. Màu sau khi thay đổi (New Color)
    if color_canvas_after:
        draw_color_circle(color_canvas_after, new_hex)
    if color_hex_after:
        color_hex_after.config(state=tk.NORMAL)
        color_hex_after.delete(0, tk.END)
        color_hex_after.insert(0, new_hex if new_hex else "#XXXXXX")
        color_hex_after.config(state=tk.DISABLED)


# =====================================
# HÀM XỬ LÝ LOG VIEWER (Cập nhật vị trí)
# =====================================
def open_log_viewer(log_type):
    """Mở hộp thoại hiển thị nội dung file log"""
    global main_app_window

    # 1. Lấy nội dung log và đường dẫn thư mục
    log_content, log_folder_path = handle_view_log_file(log_type)

    # 2. Tạo hộp thoại Log Viewer Dialog
    log_dialog = tk.Toplevel(main_app_window)
    log_dialog.title(f"Log Viewer: {log_type}")

    # Cập nhật vị trí
    LOG_WIDTH, LOG_HEIGHT = 800, 600
    if main_app_window:
        log_dialog.geometry(center_toplevel_on_parent(log_dialog, main_app_window, LOG_WIDTH, LOG_HEIGHT))
    else:
        log_dialog.geometry(center_window_on_screen(log_dialog, LOG_WIDTH, LOG_HEIGHT))

    log_dialog.resizable(True, True)

    # Khung chứa các nút điều khiển
    frame_controls = tk.Frame(log_dialog)
    frame_controls.pack(fill="x", padx=10, pady=5)

    # Label hiển thị đường dẫn thư mục
    tk.Label(frame_controls, text=f"Thư mục Log: {log_folder_path}", anchor="w").pack(side="left", fill="x",
                                                                                      expand=True)

    # Nút Đóng
    tk.Button(frame_controls, text="Close", command=log_dialog.destroy).pack(side="right")

    # Khung chứa Text widget và Scrollbar
    frame_text = tk.Frame(log_dialog)
    frame_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # Text widget để hiển thị nội dung log
    text_log = tk.Text(frame_text, wrap=tk.NONE, height=10, width=40)

    # Scrollbars
    vsb = tk.Scrollbar(frame_text, orient="vertical", command=text_log.yview)
    hsb = tk.Scrollbar(frame_text, orient="horizontal", command=text_log.xview)

    text_log.config(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    vsb.pack(side="right", fill="y")
    hsb.pack(side="bottom", fill="x")
    text_log.pack(side="left", fill="both", expand=True)

    # Chèn nội dung log
    text_log.insert(tk.END, log_content)
    text_log.config(state=tk.DISABLED)


# =====================================
# HÀM XỬ LÝ SỰ KIỆN UI CHÍNH (Giữ nguyên logic)
# =====================================

def ui_refresh_window_list():
    """Làm mới danh sách cửa sổ và cập nhật Combobox"""
    global combo_window
    windows = refresh_window_list()
    combo_window["values"] = windows
    if windows and not combo_window.get():
        combo_window.current(0)


def on_window_selected(event=None):
    """Xử lý khi cửa sổ được chọn"""
    window_title = combo_window.get()
    update_status(f"Đã chọn cửa sổ: {window_title}")


def on_start_click():
    """Xử lý nút Bắt đầu"""
    title = combo_window.get()
    x = entry_x.get()
    y = entry_y.get()
    threshold = entry_threshold.get()
    a_str = entry_a.get()
    # THAY ĐỔI: Lấy giá trị độ trễ
    delay_str = entry_delay_after_click.get()
    radius = "0"
    is_five_points_mode = pixel_mode_var.get()

    # THAY ĐỔI: Truyền giá trị độ trễ
    handle_start(title, x, y, radius, threshold, a_str, delay_str, is_five_points_mode)


def on_stop_click():
    """Xử lý nút Dừng lại"""
    handle_stop()


def on_pick_click():
    """Xử lý nút Chọn vị trí"""
    handle_pick_mode(combo_window.get())


def on_pixel_mode_toggle():
    """Xử lý khi nút chuyển đổi chế độ pixel được bấm"""
    global pixel_mode_var
    is_five_points = pixel_mode_var.get()

    if is_five_points:
        entry_a.config(state=tk.NORMAL)
        status_text = "Chế độ: 5 điểm pixel được BẬT."
    else:
        entry_a.config(state=tk.DISABLED)
        status_text = "Chế độ: 1 điểm pixel được BẬT."

    update_status(status_text)
    set_pixel_mode_on_off(is_five_points)


def ui_view_log_file():
    """Nút xem chi tiết log"""
    open_log_viewer('activity')


def ui_open_log_folder():
    """Nút mở thư mục chứa log"""
    _, log_folder_path = get_log_content_and_path('activity')
    try:
        if os.path.isdir(log_folder_path):
            os.startfile(log_folder_path)
        else:
            messagebox.showerror("Lỗi", "Không tìm thấy thư mục log!")
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không thể mở thư mục: {e}")


# =====================================
# HÀM XỬ LÝ THOÁT VÀ CHUYỂN CỬA SỔ
# =====================================

def go_to_start_screen(event=None):
    """Chuyển về cửa sổ Start Screen"""
    global main_app_window, start_screen
    handle_stop()

    if main_app_window:
        main_app_window.withdraw()
    if start_screen:
        start_screen.deiconify()


def quit_app():
    """Thoát hẳn ứng dụng (dùng cho Start Screen)"""
    global main_app_window, start_screen, root
    handle_stop()
    if main_app_window:
        main_app_window.destroy()
    if start_screen:
        start_screen.destroy()
    if root:
        root.destroy()


def ask_on_close():
    """Hộp thoại xác nhận thoát tùy chỉnh (Cập nhật vị trí)"""

    class CustomAskDialog(tk.Toplevel):
        def __init__(self, parent):
            super().__init__(parent)
            self.title("Xác nhận Thoát")
            ASK_WIDTH, ASK_HEIGHT = 400, 150

            # Cập nhật vị trí
            self.geometry(center_toplevel_on_parent(self, parent, ASK_WIDTH, ASK_HEIGHT))

            self.resizable(False, False)
            self.result = None

            tk.Label(self, text="Bạn muốn làm gì?", font=("Segoe UI", 10, "bold")).pack(pady=10)

            frame_buttons = tk.Frame(self)
            frame_buttons.pack(pady=10, padx=10)

            # Nút Về trang chính (Tương đương Yes)
            tk.Button(frame_buttons, text="Về trang chính", command=self.on_yes, width=12).pack(side=tk.LEFT, padx=5)

            # Nút Thoát ứng dụng (Tương đương No)
            tk.Button(frame_buttons, text="Thoát ứng dụng", command=self.on_no, width=12).pack(side=tk.LEFT, padx=5)

            # Nút Huỷ bỏ (Tương đương Cancel)
            tk.Button(frame_buttons, text="Huỷ bỏ", command=self.on_cancel, width=12).pack(side=tk.LEFT, padx=5)

            # Giữ cửa sổ con ở trên
            self.transient(parent)
            self.grab_set()
            parent.wait_window(self)

        def on_yes(self):
            self.result = "yes"
            self.destroy()

        def on_no(self):
            self.result = "no"
            self.destroy()

        def on_cancel(self):
            self.result = "cancel"
            self.destroy()

    dialog = CustomAskDialog(main_app_window)
    choice = dialog.result

    if choice == "yes":
        go_to_start_screen()
    elif choice == "no":
        quit_app()
    # Nếu chọn cancel, không làm gì


# =====================================
# HÀM ABOUT (Cập nhật vị trí)
# =====================================

def show_about():
    """Hiển thị cửa sổ About (Cập nhật vị trí)"""
    global root

    # Sử dụng main_app_window hoặc start_screen làm parent
    parent = main_app_window if main_app_window and main_app_window.winfo_exists() else start_screen

    about = tk.Toplevel(parent)
    about.title("About")

    # Cập nhật vị trí
    ABOUT_WIDTH, ABOUT_HEIGHT = 450, 300
    about.geometry(center_toplevel_on_parent(about, parent, ABOUT_WIDTH, ABOUT_HEIGHT))

    about.resizable(False, False)

    # Khung viền (Border)
    border = tk.Frame(about, highlightbackground="black", highlightcolor="black",
                      highlightthickness=1, bd=0)
    border.pack(fill="both", padx=10, pady=10, expand=True)

    # Khung chứa Canvas và Scrollbar
    frame_scroll_container = tk.Frame(border)
    frame_scroll_container.pack(fill="both", expand=True)

    # 1. Tạo Canvas
    canvas = tk.Canvas(frame_scroll_container, highlightthickness=0)
    canvas.pack(side="left", fill="both", expand=True)

    # 2. Tạo Scrollbar
    scrollbar = ttk.Scrollbar(frame_scroll_container, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")

    # Kết nối Scrollbar với Canvas
    canvas.configure(yscrollcommand=scrollbar.set)

    # 3. Tạo Frame để chứa nội dung bên trong Canvas
    scroll_frame = tk.Frame(canvas)

    # Gán scroll_frame vào Canvas
    scroll_frame_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

    # Cập nhật vùng cuộn khi kích thước scroll_frame thay đổi
    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    # Đảm bảo scroll_frame chiếm toàn bộ chiều rộng của canvas
    canvas.bind(
        "<Configure>",
        lambda e: canvas.itemconfig(scroll_frame_id, width=e.width)
    )

    # --- Nội dung About ---
    title_text = "Auto Clicker v1.1.2\nTác giả: Kevin Quach\n"  # Giữ nguyên tác giả
    title_label = tk.Label(
        scroll_frame,
        text=title_text,
        font=("Segoe UI", 10, "bold"),
        anchor="center",
        justify="center"
    )
    title_label.pack(fill="x", pady=(5, 5), anchor="center")

    separator = ttk.Separator(scroll_frame, orient="horizontal")
    separator.pack(fill="x", padx=10, pady=(0, 5))

    # Cập nhật phần Body theo yêu cầu
    body_text = ("- Sửa lại vị trí lưu file log.\n"
                 "- Tối ưu hóa tốc độ theo dõi màu sắc (Chỉ xét 1 pixel).\n"
                 "- Cải thiện tính năng phát hiện thay đổi màu sắc.\n"
                 "- Thêm tính năng chọn ngưỡng khoảng cách màu thay đổi (Ngưỡng mặc định 5).\n"
                 "- Chặn hành vi thay đổi kích thước của cửa sổ làm việc.\n"
                 "- Thêm tính năng Hồi phục (Idle Timeout).\n"
                 "- Thêm Menu Diagnostics để xem Log.\n"
                 "- **Cập nhật:**  Thêm chế độ theo dõi 5 điểm pixel với Độ lệch A.\n"
                 "- **Cập nhật:**  Thay đổi khung hiển thị log, positions.log → activity.log"
                 "- **Cập nhật:** Chế độ Start Screen và quản lý thoát ứng dụng linh hoạt.\n"
                 "- **Cập nhật:** Thêm tính năng chỉnh thời gian cất cá vào túi.\n"
                 "---------------------------------------------------\n")
    body_label = tk.Label(scroll_frame, text=body_text, justify="left",
                          anchor="nw", wraplength=400, height=15)
    body_label.pack(fill="both", expand=True, padx=5, pady=(0, 10))


# =====================================
# KHỞI TẠO CỬA SỔ CHÍNH (Cập nhật vị trí)
# =====================================

def create_main_app_window():
    """Tạo cửa sổ ứng dụng chính"""
    global main_app_window, combo_window, entry_x, entry_y, entry_threshold, entry_a, status_label
    global color_canvas_before, color_hex_before, color_canvas_after, color_hex_after, activity_log_text
    global pixel_mode_var, root, entry_delay_after_click

    # Kích thước cố định của cửa sổ chính
    MAIN_WIDTH, MAIN_HEIGHT = 450, 650

    if main_app_window:
        main_app_window.deiconify()
        # Nếu đã tạo, chỉ cần tải lại trạng thái cuối cùng
        load_and_set_last_state()
        return

    main_app_window = tk.Toplevel(root)
    main_app_window.title("Auto Clicker - Tự động câu cá")

    # Cập nhật vị trí (Sát cạnh phải + 5% đệm, giữa dọc)
    main_app_window.geometry(position_main_app_right_center(main_app_window, MAIN_WIDTH, MAIN_HEIGHT))

    main_app_window.resizable(False, False)
    main_app_window.config(padx=10, pady=10)

    main_app_window.protocol("WM_DELETE_WINDOW", ask_on_close)

    # KHỞI TẠO CONTROLLER (Cần gọi trước khi load_and_set_last_state)
    init_controller(update_status, update_color_labels, load_log_list, set_coordinate_entries, on_pixel_mode_toggle)

    # Menu bar
    menubar = tk.Menu(main_app_window)

    # Menu File
    menu_file = tk.Menu(menubar, tearoff=0)
    menu_file.add_command(label="Thoát về Trang chính", command=go_to_start_screen)
    menu_file.add_command(label="Thoát ứng dụng", command=quit_app)
    menubar.add_cascade(label="File", menu=menu_file)

    # Menu Tools -> Diagnostics -> View Log
    menu_tools = tk.Menu(menubar, tearoff=0)

    menu_diagnostics = tk.Menu(menu_tools, tearoff=0)

    menu_view_log = tk.Menu(menu_diagnostics, tearoff=0)
    menu_view_log.add_command(label="positions.log", command=lambda: open_log_viewer('positions'))
    menu_view_log.add_command(label="activity.log", command=lambda: open_log_viewer('activity'))

    menu_diagnostics.add_cascade(label="View Log", menu=menu_view_log)

    menu_tools.add_cascade(label="Diagnostics", menu=menu_diagnostics)
    menubar.add_cascade(label="Tools", menu=menu_tools)

    # Menu About
    menu_about = tk.Menu(menubar, tearoff=0)
    menu_about.add_command(label="About", command=show_about)
    menubar.add_cascade(label="About", menu=menu_about)

    main_app_window.config(menu=menubar)

    # --- Phần chính của UI ---

    tk.Label(main_app_window, text="Chọn cửa sổ mục tiêu:", font=("Segoe UI", 10, "bold")).pack(anchor="w")

    frame_winrow = tk.Frame(main_app_window)
    frame_winrow.pack(fill="x", pady=5)

    combo_window = ttk.Combobox(frame_winrow, state="readonly")
    combo_window.pack(side="left", fill="x", expand=True)
    combo_window.bind("<<ComboboxSelected>>", on_window_selected)

    tk.Button(frame_winrow, text="Làm mới", command=ui_refresh_window_list, width=10) \
        .pack(side="left", padx=5)

    # DÒNG CHỨA X VÀ Y
    frame_coords = tk.Frame(main_app_window)
    frame_coords.pack(fill="x", pady=5)

    tk.Label(frame_coords, text="Tọa độ tương đối X:").pack(side="left", anchor="w", expand=True)
    tk.Label(frame_coords, text="Tọa độ tương đối Y:").pack(side="left", anchor="w", expand=True, padx=(10, 0))

    frame_entry_coords = tk.Frame(main_app_window)
    frame_entry_coords.pack(fill="x")

    entry_x = tk.Entry(frame_entry_coords)
    entry_x.pack(side="left", fill="x", expand=True, pady=2)

    entry_y = tk.Entry(frame_entry_coords)
    entry_y.pack(side="left", fill="x", expand=True, pady=2, padx=(10, 0))

    # THAY ĐỔI: DÒNG CHỨA THRESHOLD, ĐỘ LỆCH A VÀ ĐỘ TRỄ SAU CLICK
    frame_params = tk.Frame(main_app_window)
    frame_params.pack(fill="x", pady=5)

    # Label cho Ngưỡng (Threshold)
    tk.Label(frame_params, text="Ngưỡng KC màu:").pack(side="left", anchor="w", expand=True)
    # Label cho Độ lệch A
    tk.Label(frame_params, text="Độ lệch pixel A:").pack(side="left", anchor="w", expand=True, padx=(10, 0))
    # Label MỚI cho Độ trễ sau click
    tk.Label(frame_params, text="Độ trễ sau Click (s):").pack(side="left", anchor="w", expand=True, padx=(10, 0))

    frame_entry_params = tk.Frame(main_app_window)
    frame_entry_params.pack(fill="x")

    # Entry Ngưỡng (Threshold)
    entry_threshold = tk.Entry(frame_entry_params)
    entry_threshold.insert(0, "5")
    entry_threshold.pack(side="left", fill="x", expand=True, pady=2)

    # Entry Độ lệch A
    entry_a = tk.Entry(frame_entry_params)
    entry_a.insert(0, "5")
    entry_a.pack(side="left", fill="x", expand=True, pady=2, padx=(10, 0))
    entry_a.config(state=tk.DISABLED)

    # Entry MỚI Độ trễ sau Click
    entry_delay_after_click = tk.Entry(frame_entry_params)
    entry_delay_after_click.insert(0, "7")  # Giá trị mặc định là 7 giây
    entry_delay_after_click.pack(side="left", fill="x", expand=True, pady=2, padx=(10, 0))

    # Toggle Button cho chế độ 1/5 điểm
    pixel_mode_var = tk.BooleanVar()
    pixel_mode_var.set(False)

    frame_pixel_mode = tk.Frame(main_app_window)
    frame_pixel_mode.pack(fill="x", pady=5)

    tk.Label(frame_pixel_mode, text="Chế độ theo dõi:", font=("Segoe UI", 9)).pack(side=tk.LEFT, anchor="w")

    rb_one = tk.Radiobutton(frame_pixel_mode, text="1 điểm", variable=pixel_mode_var, value=False,
                            command=on_pixel_mode_toggle)
    rb_one.pack(side=tk.LEFT, padx=10)

    rb_five = tk.Radiobutton(frame_pixel_mode, text="5 điểm (với A)", variable=pixel_mode_var, value=True,
                             command=on_pixel_mode_toggle)
    rb_five.pack(side=tk.LEFT)

    tk.Button(main_app_window, text="Chọn vị trí (F9)", command=on_pick_click).pack(pady=5, fill="x")

    frame_buttons = tk.Frame(main_app_window)
    frame_buttons.pack(pady=5, fill="x")

    btn_start = tk.Button(frame_buttons, text="Bắt đầu (F10)", command=on_start_click, bg="#9fdb9f", width=15)
    btn_start.pack(side="left", padx=5, expand=True, fill="x")

    btn_stop = tk.Button(frame_buttons, text="Dừng lại (F11)", command=on_stop_click, bg="#f08080", width=15)
    btn_stop.pack(side="left", padx=5, expand=True, fill="x")

    # TRẠNG THÁI
    status_label = tk.Label(main_app_window, text="Auto Clicker tạm dừng (Chế độ 1 điểm)", anchor="w", relief=tk.SUNKEN)
    status_label.pack(fill="x", pady=(5, 0))

    # PHẦN HIỂN THỊ MÀU
    frame_colors = tk.Frame(main_app_window)
    frame_colors.pack(fill="x", pady=(5, 5))

    frame_before = tk.Frame(frame_colors)
    frame_before.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
    tk.Label(frame_before, text="Màu trước thay đổi:", anchor="w").pack(fill="x")
    sub_frame_before = tk.Frame(frame_before)
    sub_frame_before.pack(fill="x")
    color_canvas_before = tk.Canvas(sub_frame_before, width=20, height=20, highlightthickness=0)
    color_canvas_before.pack(side=tk.LEFT, padx=(0, 5))
    color_hex_before = tk.Entry(sub_frame_before, width=10, justify='center')
    color_hex_before.insert(0, "#XXXXXX")
    color_hex_before.config(state=tk.DISABLED, relief=tk.FLAT)
    color_hex_before.pack(side=tk.LEFT, fill=tk.X, expand=True)

    frame_after = tk.Frame(frame_colors)
    frame_after.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))
    tk.Label(frame_after, text="Màu sau thay đổi:", anchor="w").pack(fill="x")
    sub_frame_after = tk.Frame(frame_after)
    sub_frame_after.pack(fill="x")
    color_canvas_after = tk.Canvas(sub_frame_after, width=20, height=20, highlightthickness=0)
    color_canvas_after.pack(side=tk.LEFT, padx=(0, 5))
    color_hex_after = tk.Entry(sub_frame_after, width=10, justify='center')
    color_hex_after.insert(0, "#XXXXXX")
    color_hex_after.config(state=tk.DISABLED, relief=tk.FLAT)
    color_hex_after.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # LỊCH SỬ HOẠT ĐỘNG (Activity Log)
    tk.Label(main_app_window, text="Lịch sử hoạt động (Phiên hiện tại):", font=("Segoe UI", 10, "bold")).pack(
        pady=(5, 0), anchor="w")

    frame_log = tk.Frame(main_app_window)
    frame_log.pack(fill="both", expand=True, padx=5, pady=5)

    # Đổi sang sử dụng font Segoe UI
    activity_log_text = tk.Text(frame_log, wrap=tk.WORD, height=8, state=tk.DISABLED, font=("Segoe UI", 9))

    log_scrollbar = ttk.Scrollbar(frame_log, orient="vertical", command=activity_log_text.yview)
    log_scrollbar.pack(side="right", fill="y")
    activity_log_text.config(yscrollcommand=log_scrollbar.set)
    activity_log_text.pack(side="left", fill="both", expand=True)

    # Nút mới: Xem chi tiết log & Mở thư mục
    frame_log_buttons = tk.Frame(main_app_window)
    frame_log_buttons.pack(pady=5, fill="x")

    btn_view_detail = tk.Button(frame_log_buttons, text="Xem chi tiết log", command=ui_view_log_file, bg="#cce0ff")
    btn_view_detail.pack(side="left", expand=True, fill="x", padx=5)

    btn_open_folder = tk.Button(frame_log_buttons, text="Mở thư mục", command=ui_open_log_folder, bg="#fff0cc")
    btn_open_folder.pack(side="left", expand=True, fill="x", padx=5)

    # THAY ĐỔI HOTKEY
    keyboard.add_hotkey('F9', on_pick_click)
    keyboard.add_hotkey('f10', on_start_click)
    keyboard.add_hotkey('f11', on_stop_click)

    # Load danh sách cửa sổ
    ui_refresh_window_list()

    # TẢI TRẠNG THÁI CUỐI CÙNG
    load_and_set_last_state()


def load_and_set_last_state():
    """Tải và cập nhật trạng thái cuối cùng vào UI"""
    last_state = load_last_known_state()
    if last_state:
        last_title, last_x, last_y = last_state
        set_window_entry(last_title)
        set_coordinate_entries(last_x, last_y)
        update_status(f"Đã tải trạng thái cuối cùng: {last_title} ({last_x},{last_y})")


# =====================================
# KHỞI TẠO CỬA SỔ START (Đã loại bỏ Menubar)
# =====================================

def start_main_app_mode(mode_name):
    """Xử lý nút Start Screen để mở ứng dụng chính"""
    global start_screen

    if start_screen:
        start_screen.withdraw()

    if mode_name == "fishing":
        create_main_app_window()
        handle_stop()


def create_start_screen():
    """Tạo cửa sổ khởi động (Đã loại bỏ Menubar)"""
    global root, start_screen

    root = tk.Tk()
    root.withdraw()

    start_screen = tk.Toplevel(root)
    start_screen.title("Auto Clicker - Select Mode")

    # Kích thước cố định của Start Screen
    START_WIDTH, START_HEIGHT = 300, 200

    # Cập nhật vị trí (Căn giữa màn hình)
    start_screen.geometry(center_window_on_screen(start_screen, START_WIDTH, START_HEIGHT))

    start_screen.resizable(False, False)
    start_screen.config(padx=20, pady=20)

    start_screen.protocol("WM_DELETE_WINDOW", quit_app)  # Dùng quit_app để thoát hẳn

    # --- KHÔNG CÒN MENUBAR CHO START SCREEN ---

    tk.Label(start_screen, text="Chọn Chế độ:", font=("Segoe UI", 12, "bold")).pack(pady=10)

    tk.Button(start_screen,
              text="🎣 Tự động câu cá",
              command=lambda: start_main_app_mode("fishing"),
              font=("Segoe UI", 10, "bold"),
              bg="#ccffcc").pack(fill="x", pady=5)


def start_main_app():
    """Khởi tạo và chạy ứng dụng chính"""
    create_start_screen()
    root.mainloop()
