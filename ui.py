import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
import threading
from controller import refresh_window_list, handle_start, handle_stop, handle_pick_mode, load_log_list_data, \
    delete_selected_items, delete_all_log, init_controller, handle_view_log_file
import os

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
combo_window = None
entry_x = None
entry_y = None
entry_radius = None
entry_threshold = None
status_label = None
color_canvas_before = None
color_hex_before = None
color_canvas_after = None
color_hex_after = None
tree = None


# =====================================
# HÀM CẬP NHẬT UI (Callback cho Controller/Autoclicker)
# =====================================
def update_status(text, color=None):
    """Cập nhật nhãn trạng thái"""
    global status_label, root
    if status_label:
        status_label.config(text=text)


def set_coordinate_entries(rel_x, rel_y):
    """Cập nhật ô nhập tọa độ"""
    global entry_x, entry_y
    if entry_x and entry_y:
        entry_x.delete(0, tk.END)
        entry_x.insert(0, rel_x)
        entry_y.delete(0, tk.END)
        entry_y.insert(0, rel_y)


def load_log_list():
    """Tải dữ liệu log vào Treeview"""
    global tree
    if not tree:
        return

    for item in tree.get_children():
        tree.delete(item)

    data = load_log_list_data()
    for row in data:
        tree.insert("", "end", values=row)


def draw_color_circle(canvas, color_hex):
    """Vẽ hình tròn màu lên canvas (hoặc làm trống nếu màu rỗng)"""
    canvas.delete("all")
    if color_hex and color_hex != "#XXXXXX" and color_hex != "":
        # Lấy kích thước canvas
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        radius = 9

        # Vẽ hình tròn chính giữa
        canvas.create_oval(
            width // 2 - radius,
            height // 2 - radius,
            width // 2 + radius,
            width // 2 + radius,
            fill=color_hex,
            outline="#444444"
        )
    else:
        # Đặt màu nền mặc định
        canvas.config(bg=root.cget("bg"))


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
# HÀM XỬ LÝ LOG VIEWER
# =====================================
def open_log_viewer(log_type):
    """Mở hộp thoại hiển thị nội dung file log"""
    global root

    # 1. Lấy nội dung log và đường dẫn thư mục
    log_content, log_folder_path = handle_view_log_file(log_type)

    # 2. Tạo hộp thoại Log Viewer Dialog
    log_dialog = tk.Toplevel(root)
    log_dialog.title(f"Log Viewer: {log_type}")
    log_dialog.geometry("1080x768")
    log_dialog.resizable(False, False)

    # Khung chứa các nút điều khiển
    frame_controls = tk.Frame(log_dialog)
    frame_controls.pack(fill="x", padx=10, pady=5)

    # Nút Open file location
    def open_folder():
        if os.path.isdir(log_folder_path):
            os.startfile(log_folder_path)
        else:
            messagebox.showerror("Lỗi", "Không tìm thấy thư mục log!")

    tk.Button(frame_controls, text="Open file location", command=open_folder).pack(side="left")

    # Nút Đóng (nằm cùng hàng ngang)
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
# HÀM XỬ LÝ SỰ KIỆN UI
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
    # Gửi giá trị cố định "0" cho radius (do đã bị loại bỏ khỏi UI nhưng controller cần tham số)
    radius = "0"
    threshold = entry_threshold.get()
    handle_start(title, x, y, radius, threshold)


def on_stop_click():
    """Xử lý nút Dừng lại"""
    handle_stop()


def on_pick_click():
    """Xử lý nút Chọn vị trí"""
    handle_pick_mode(combo_window.get())


def on_tree_click(event):
    """Đánh dấu chọn/bỏ chọn trong Treeview"""
    global tree
    row_id = tree.identify_row(event.y)
    if not row_id:
        return

    current = tree.set(row_id, "checkbox")
    tree.set(row_id, "checkbox", "☑" if current == "☐" else "☐")


def on_tree_double_click(event):
    """Tải tọa độ từ mục đã double-click"""
    global tree
    row_id = tree.identify_row(event.y)
    if not row_id:
        return

    values = tree.item(row_id, "values")
    if len(values) < 3:
        return

    _, window_title, coords, _ = values

    combo_window.set(window_title)
    on_window_selected()

    try:
        x, y = coords.split(",")
        set_coordinate_entries(x.strip(), y.strip())
        update_status(f"Tải lại tọa độ từ lịch sử: {window_title} ({coords})")
    except Exception:
        update_status("Lỗi khi đọc tọa độ từ lịch sử")


def ui_delete_selected_items():
    """Xóa các mục đã chọn"""
    global tree
    selected_data = []

    for item in tree.get_children():
        if tree.set(item, "checkbox") == "☑":
            values = tree.item(item, "values")
            if len(values) >= 3:
                selected_data.append((values[0], values[1], values[2]))

    success, msg = delete_selected_items(selected_data)
    messagebox.showinfo("Thông báo", msg)


def ui_delete_all_log():
    """Xóa toàn bộ log"""
    if messagebox.askyesno("Xác nhận", "Xóa toàn bộ log?"):
        success, msg = delete_all_log()
        messagebox.showinfo("Hoàn tất", msg)


# HÀM ABOUT ĐÃ ĐƯỢC CẬP NHẬT ĐỂ CÓ THANH CUỘN, GIỚI HẠN CHIỀU CAO NỘI DUNG VÀ HIỂN THỊ NÚT ĐÓNG BÊN NGOÀI
def show_about():
    """Hiển thị cửa sổ About"""
    global root
    about = tk.Toplevel(root)
    about.title("About")
    # Tăng chiều cao để chứa nội dung cuộn tốt hơn
    about.geometry("450x300")
    about.resizable(False, False)

    # Khung viền (Border is now the first thing packed into `about`)
    border = tk.Frame(about, highlightbackground="black", highlightcolor="black",
                      highlightthickness=1, bd=0)
    # Loại bỏ expand=True để nó không chiếm toàn bộ chiều cao, giải phóng không gian cho nút Đóng (đã bị loại bỏ)
    border.pack(fill="both", padx=10, pady=10, expand=True)  # Dùng expand=True để canvas chiếm hết không gian

    # Khung chứa Canvas và Scrollbar
    frame_scroll_container = tk.Frame(border)
    # Để frame_scroll_container expand bên trong border
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
    title_text = "Auto Clicker v1.1.2\nTác giả: Kevin Quach\n"
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

    # Thêm nhiều dòng hơn để kiểm tra thanh cuộn
    body_text = ("- Sửa lại vị trí lưu file log.\n"
                 "- Tối ưu hóa tốc độ theo dõi màu sắc (Chỉ xét 1 pixel).\n"
                 "- Cải thiện tính năng phát hiện thay đổi màu sắc.\n"
                 "- Thêm tính năng chọn ngưỡng khoảng cách màu thay đổi.\n"
                 "- Chặn hành vi thay đổi kích thước của cửa sổ làm việc.\n"
                 "- Thêm tính năng Hồi phục (Idle Timeout).\n"
                 "- Thêm Menu Diagnostics để xem Log.\n"
                 "- **Cập nhật:** Hộp thoại About đã có tính năng cuộn (scrollbar).\n"
                 "---------------------------------------------------\n")
    body_label = tk.Label(scroll_frame, text=body_text, justify="left",
                          anchor="nw", wraplength=400, height=15)
    body_label.pack(fill="both", expand=True, padx=5, pady=(0, 10))


# =====================================
# KHỞI TẠO UI
# =====================================

def start_ui():
    """Khởi tạo và chạy giao diện chính"""
    global root, combo_window, entry_x, entry_y, entry_radius, entry_threshold, status_label, tree
    global color_canvas_before, color_hex_before, color_canvas_after, color_hex_after

    root = tk.Tk()
    root.title("Auto Clicker")
    root.geometry("450x700")
    root.resizable(False, False)
    root.config(padx=10, pady=10)

    # KHỞI TẠO CONTROLLER
    init_controller(update_status, update_color_labels, load_log_list, set_coordinate_entries)

    # Menu bar
    menubar = tk.Menu(root)

    # Menu File
    menu_file = tk.Menu(menubar, tearoff=0)
    menu_file.add_command(label="Thoát", command=root.destroy)
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

    root.config(menu=menubar)

    # --- Phần chính của UI ---

    tk.Label(root, text="Chọn cửa sổ mục tiêu:", font=("Segoe UI", 10, "bold")).pack(anchor="w")

    frame_winrow = tk.Frame(root)
    frame_winrow.pack(fill="x", pady=5)

    combo_window = ttk.Combobox(frame_winrow, state="readonly")
    combo_window.pack(side="left", fill="x", expand=True)
    combo_window.bind("<<ComboboxSelected>>", on_window_selected)

    tk.Button(frame_winrow, text="Làm mới", command=ui_refresh_window_list, width=10) \
        .pack(side="left", padx=5)

    tk.Label(root, text="Tọa độ tương đối X:").pack(anchor="w")
    entry_x = tk.Entry(root)
    entry_x.pack(fill="x", pady=2)

    tk.Label(root, text="Tọa độ tương đối Y:").pack(anchor="w")
    entry_y = tk.Entry(root)
    entry_y.pack(fill="x", pady=2)

    # KHUNG CHỨA NGƯỠNG MÀU
    frame_params = tk.Frame(root)
    frame_params.pack(fill="x", pady=5)

    frame_threshold = tk.Frame(frame_params)
    frame_threshold.pack(side=tk.LEFT, fill="x", expand=True)

    tk.Label(frame_threshold, text="Ngưỡng khoảng cách màu:").pack(anchor="w")
    entry_threshold = tk.Entry(frame_threshold, width=5)
    entry_threshold.insert(0, "10")
    entry_threshold.pack(pady=2, anchor="w", fill="x")

    tk.Button(root, text="Chọn vị trí (Ctrl + F10)", command=on_pick_click).pack(pady=5, fill="x")

    frame_buttons = tk.Frame(root)
    frame_buttons.pack(pady=5, fill="x")

    btn_start = tk.Button(frame_buttons, text="Bắt đầu (F11)", command=on_start_click, bg="#9fdb9f", width=15)
    btn_start.pack(side="left", padx=5, expand=True, fill="x")

    btn_stop = tk.Button(frame_buttons, text="Dừng lại (F12)", command=on_stop_click, bg="#f08080", width=15)
    btn_stop.pack(side="left", padx=5, expand=True, fill="x")

    # TRẠNG THÁI
    status_label = tk.Label(root, text="Auto Clicker tạm dừng", anchor="w")
    status_label.pack(fill="x", pady=(5, 0))

    # PHẦN HIỂN THỊ MÀU
    frame_colors = tk.Frame(root)
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

    tk.Label(root, text="Lịch sử tọa độ:", font=("Segoe UI", 10, "bold")).pack(pady=(5, 0), anchor="w")

    frame_tree = tk.Frame(root)
    frame_tree.pack(fill="both", expand=True, padx=5, pady=5)

    columns = ("time", "window", "coords", "checkbox")
    tree = ttk.Treeview(frame_tree, columns=columns, show="headings", selectmode="browse")
    tree.heading("time", text="Thời gian")
    tree.heading("window", text="Cửa sổ")
    tree.heading("coords", text="Tọa độ (rel)")
    tree.heading("checkbox", text="Chọn")

    tree.column("time", width=120, anchor="center")
    tree.column("window", width=150, anchor="center")
    tree.column("coords", width=100, anchor="center")
    tree.column("checkbox", width=50, anchor="center")

    tree.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(frame_tree, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scrollbar.set)

    tree.bind("<Button-1>", on_tree_click)
    tree.bind("<Double-1>", on_tree_double_click)

    frame_delete = tk.Frame(root)
    frame_delete.pack(pady=5, fill="x")

    btn_delete_selected = tk.Button(frame_delete, text="Xóa mục đã chọn", bg="#f08080",
                                    command=ui_delete_selected_items)
    btn_delete_selected.pack(side="left", expand=True, fill="x", padx=5)

    btn_delete_all = tk.Button(frame_delete, text="Xóa toàn bộ log", bg="#f08080", command=ui_delete_all_log)
    btn_delete_all.pack(side="left", expand=True, fill="x", padx=5)

    keyboard.add_hotkey('ctrl+f10', on_pick_click)
    keyboard.add_hotkey('f11', on_start_click)
    keyboard.add_hotkey('f12', on_stop_click)

    ui_refresh_window_list()
    load_log_list()

    root.mainloop()
