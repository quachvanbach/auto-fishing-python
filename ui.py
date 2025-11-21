import tkinter as tk
from tkinter import ttk, messagebox
import keyboard
import threading
from controller import refresh_window_list, handle_start, handle_stop, handle_pick_mode, load_log_list_data, \
    delete_selected_items, delete_all_log, init_controller

# external libs (mouse/keyboard/pygetwindow)
# Đặt kiểm tra tại đây để đảm bảo khởi động chương trình có đủ module
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
status_label = None

# BIẾN MỚI THAY THẾ color_label
color_canvas_before = None
color_hex_before = None
color_canvas_after = None
color_hex_after = None
# HẾT BIẾN MỚI

tree = None


# =====================================
# HÀM CẬP NHẬT UI (Callback cho Controller/Autoclicker)
# =====================================

def update_status(text, color=None):
    """Cập nhật nhãn trạng thái"""
    global status_label, root
    if status_label:
        status_label.config(text=text)
    # Không dùng color_label nữa, màu được quản lý bởi update_color_labels


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


# HÀM MỚI HIỂN THỊ MÀU
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
            height // 2 + radius,
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


# HẾT HÀM MỚI

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
    radius = entry_radius.get()
    handle_start(title, x, y, radius)


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


def show_about():
    """Hiển thị cửa sổ About"""
    global root
    about = tk.Toplevel(root)
    about.title("About")
    about.geometry("400x200")
    about.resizable(False, False)

    border = tk.Frame(about, highlightbackground="black", highlightcolor="black",
                      highlightthickness=1, bd=0)
    border.pack(fill="both", expand=True, padx=10, pady=10)

    frame = tk.Frame(border)
    frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(frame, highlightthickness=0)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas)

    scroll_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.bind(
        "<Configure>",
        lambda e: canvas.itemconfig(scroll_frame_id, width=e.width)
    )

    scroll_frame_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # --- Nội dung ---
    title_text = "Auto Clicker v1.1.1\nTác giả: Kevin Quach\n"
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

    body_text = ("- Sửa lại vị trí lưu file log.\n"
                 "- Thêm tính năng chọn số điểm ảnh theo dõi.")
    body_label = tk.Label(scroll_frame, text=body_text, justify="left",
                          anchor="nw", wraplength=380)
    body_label.pack(fill="both", expand=True, padx=5, pady=(0, 10))

    tk.Button(about, text="Đóng", command=about.destroy).pack(pady=3)


# =====================================
# KHỞI TẠO UI
# =====================================

def start_ui():
    """Khởi tạo và chạy giao diện chính"""
    global root, combo_window, entry_x, entry_y, entry_radius, status_label, tree
    global color_canvas_before, color_hex_before, color_canvas_after, color_hex_after  # Biến mới

    root = tk.Tk()
    root.title("Auto Clicker theo cửa sổ")
    root.geometry("400x700")
    root.resizable(False, False)
    root.config(padx=10, pady=10)

    # KHỞI TẠO CONTROLLER: Dùng callback mới: update_color_labels
    init_controller(update_status, update_color_labels, load_log_list, set_coordinate_entries)

    # Menu bar
    menubar = tk.Menu(root)

    menu_file = tk.Menu(menubar, tearoff=0)
    menu_file.add_command(label="Thoát", command=root.destroy)
    menubar.add_cascade(label="File", menu=menu_file)

    menu_about = tk.Menu(menubar, tearoff=0)
    menu_about.add_command(label="About", command=show_about)
    menubar.add_cascade(label="About", menu=menu_about)

    root.config(menu=menubar)

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

    tk.Label(root, text="Bán kính kiểm tra pixel (mặc định: 0):").pack(anchor="w")
    entry_radius = tk.Entry(root, width=5)
    entry_radius.insert(0, "0")
    entry_radius.pack(pady=2, anchor="w")

    tk.Button(root, text="Chọn vị trí (Ctrl + F10)", command=on_pick_click).pack(pady=5, fill="x")

    frame_buttons = tk.Frame(root)
    frame_buttons.pack(pady=5, fill="x")

    btn_start = tk.Button(frame_buttons, text="Bắt đầu (F11)", command=on_start_click, bg="#9fdb9f", width=15)
    btn_start.pack(side="left", padx=5, expand=True, fill="x")

    btn_stop = tk.Button(frame_buttons, text="Dừng lại (F12)", command=on_stop_click, bg="#f08080", width=15)
    btn_stop.pack(side="left", padx=5, expand=True, fill="x")

    # TRẠNG THÁI (vẫn giữ nguyên)
    status_label = tk.Label(root, text="Auto Clicker tạm dừng", anchor="w")
    status_label.pack(fill="x", pady=(5, 0))

    # BẮT ĐẦU PHẦN HIỂN THỊ MÀU MỚI (THAY THẾ color_label cũ)
    frame_colors = tk.Frame(root)
    frame_colors.pack(fill="x", pady=(5, 5))

    # KHỐI 1: MÀU TRƯỚC KHI THAY ĐỔI
    frame_before = tk.Frame(frame_colors)
    frame_before.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

    tk.Label(frame_before, text="Màu trước thay đổi:", anchor="w").pack(fill="x")

    sub_frame_before = tk.Frame(frame_before)
    sub_frame_before.pack(fill="x")

    # Canvas hình tròn
    color_canvas_before = tk.Canvas(sub_frame_before, width=20, height=20, highlightthickness=0)
    color_canvas_before.pack(side=tk.LEFT, padx=(0, 5))

    # Ô nhập mã Hex (DISABLED)
    color_hex_before = tk.Entry(sub_frame_before, width=10, justify='center')
    color_hex_before.insert(0, "#XXXXXX")
    color_hex_before.config(state=tk.DISABLED, relief=tk.FLAT)
    color_hex_before.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # KHỐI 2: MÀU SAU KHI THAY ĐỔI
    frame_after = tk.Frame(frame_colors)
    frame_after.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

    tk.Label(frame_after, text="Màu sau thay đổi:", anchor="w").pack(fill="x")

    sub_frame_after = tk.Frame(frame_after)
    sub_frame_after.pack(fill="x")

    # Canvas hình tròn
    color_canvas_after = tk.Canvas(sub_frame_after, width=20, height=20, highlightthickness=0)
    color_canvas_after.pack(side=tk.LEFT, padx=(0, 5))

    # Ô nhập mã Hex (DISABLED)
    color_hex_after = tk.Entry(sub_frame_after, width=10, justify='center')
    color_hex_after.insert(0, "#XXXXXX")
    color_hex_after.config(state=tk.DISABLED, relief=tk.FLAT)
    color_hex_after.pack(side=tk.LEFT, fill=tk.X, expand=True)
    # KẾT THÚC PHẦN HIỂN THỊ MÀU MỚI

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