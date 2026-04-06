#!/usr/bin/env python3
"""
QuickNote GUI - 浮动备忘录 for Obsidian
支持浮动窗口呼出、Markdown编辑、直接保存到 Obsidian 日记

依赖:
  - Python 3.x (内置 tkinter)

使用方法:
  python3 quicknote_gui.py

macOS 全局快捷键设置:
  系统设置 -> 键盘 -> 快捷键 -> 服务 -> 在服务中查找"运行Shell脚本"
  或使用 Alfred/Raycast 触发
"""

import os
import sys
import re
import subprocess
import threading
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

# ==================== 配置 ====================
OBSIDIAN_DIARY = Path("/Users/jiamingli_1/Library/Mobile Documents/iCloud~md~obsidian/Documents/01📘Diary")
OBSIDIAN_DIARY_2 = Path("/Users/jiamingli_1/Library/Mobile Documents/iCloud~md~obsidian/Documents/01📘Diary/26_04")

# 窗口配置
WINDOW_WIDTH = 500
WINDOW_HEIGHT = 400
WINDOW_ALPHA = 0.95

# 图片附件配置
ATTACHMENTS_DIR = OBSIDIAN_DIARY / "attachments"

# ==================== 图片处理 ====================
def ensure_attachments_dir():
    """确保附件目录存在"""
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
    return ATTACHMENTS_DIR

def copy_attachment(file_path: Path) -> str:
    """复制附件到附件目录并返回 Markdown 链接"""
    ensure_attachments_dir()
    
    ext = file_path.suffix.lower()
    timestamp = datetime.now().strftime("%H%M%S")
    file_hash = hashlib.md5(file_path.read_bytes()[:1024]).hexdigest()[:6]
    new_filename = f"{timestamp}_{file_hash}{ext}"
    dest_path = ATTACHMENTS_DIR / new_filename
    
    shutil.copy2(file_path, dest_path)
    
    image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.heic'}
    if ext in image_exts:
        return f"![{file_path.name}](attachments/{new_filename})"
    else:
        return f"[{file_path.name}](attachments/{new_filename})"

def save_clipboard_image() -> str:
    """保存剪贴板图片，返回 Markdown 链接"""
    timestamp = datetime.now().strftime("%H%M%S")
    temp_png = f"/tmp/qn_clip_{timestamp}.png"
    
    # 使用 Python + AppKit 读取剪贴板图片 (macOS 原生)
    try:
        python_clipboard_script = f'''
import sys
try:
    from AppKit import NSPasteboard, NSBitmapImageRep
    from Foundation import NSData
    pb = NSPasteboard.generalPasteboard()
    types = pb.types()
    # 检查是否有图片类型
    image_types = [b"Apple TIFF pasteboard type", b"Apple PNG pasteboard type",
                   b"com.apple.cocoa TIFF", b"com.apple.cocoa PNG",
                   b"com.apple.Preview document", b"public.png", b"public.tiff"]
    has_image = any(t in types for t in image_types)
    if not has_image:
        sys.exit(1)
    # 尝试获取 PNG
    png_data = pb.dataForType_("public.png")
    tiff_data = pb.dataForType_("com.apple.cocoa TIFF") or pb.dataForType_("Apple TIFF pasteboard type")
    data = png_data if png_data else tiff_data
    if data is None:
        sys.exit(1)
    # 写入 PNG 文件
    success = data.writeToFile_atomically_("{temp_png}", True)
    if not success:
        sys.exit(1)
    print("ok")
except:
    sys.exit(1)
'''
        result = subprocess.run(
            ['python3', '-c', python_clipboard_script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and Path(temp_png).exists() and Path(temp_png).stat().st_size > 50:
            link = copy_attachment(Path(temp_png))
            Path(temp_png).unlink(missing_ok=True)
            return link
    except Exception as e:
        print(f"剪贴板图片保存失败: {e}")
    
    return None

# ==================== Obsidian 集成 ====================
def get_today_diary_path():
    """获取今天的日记文件路径"""
    today = datetime.now()
    date_str = today.strftime("%y-%m-%d")
    weekday_cn = ["一", "二", "三", "四", "五", "六", "日"][today.weekday()]

    # 优先使用月份子文件夹
    month_folder = f"26_{today.strftime('%m')}"
    month_path = OBSIDIAN_DIARY / month_folder

    if month_path.exists():
        diary_path = month_path / f"{date_str}.md"
    else:
        diary_path = OBSIDIAN_DIARY / f"{date_str}.md"

    return diary_path, weekday_cn

def read_today_diary():
    """读取今日日记内容"""
    diary_path, weekday = get_today_diary_path()
    if diary_path.exists():
        with open(diary_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, diary_path, weekday
    return "", diary_path, weekday

def save_to_diary(content: str, title: str = ""):
    """保存内容到日记"""
    if not content.strip():
        return False, "内容为空"

    existing_content, diary_path, weekday = read_today_diary()
    today = datetime.now()
    date_full = today.strftime("%Y-%m-%d")
    time_str = today.strftime("%H:%M")

    # 构建新条目
    if title.strip():
        header = f"## 📌 {title.strip()} {date_full} {time_str} ({weekday})"
    else:
        header = f"## 📝 {date_full} {time_str} ({weekday})"

    new_entry = f"\n{header}\n\n{content}\n"

    # 追加内容
    new_content = existing_content.rstrip() + new_entry

    # 确保目录存在
    diary_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入文件
    with open(diary_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True, str(diary_path)

# ==================== GUI 应用 ====================
class QuickNoteApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("QuickNote ✏️")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        # macOS 浮动窗口设置
        try:
            # macOS specific: floating window
            self.root.attributes('-topmost', True)
            self.root.attributes('-alpha', WINDOW_ALPHA)
        except:
            pass

        # 尝试设置窗口样式
        try:
            self.root.call('tk::scaling', 1.5)
        except:
            pass

        # 变量
        self.title_var = tk.StringVar()
        self.content_text = None
        self.status_label = None

        self.setup_ui()
        self.bind_shortcuts()

        # 居中显示
        self.center_window()

    def setup_ui(self):
        """设置 UI"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题栏
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(title_frame, text="标题 (可选):", font=('', 10)).pack(side=tk.LEFT)
        title_entry = ttk.Entry(title_frame, textvariable=self.title_var, width=30, font=('', 10))
        title_entry.pack(side=tk.LEFT, padx=(5, 0))

        # 内容文本框
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 5))

        # 滚动条
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 文本框
        self.content_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=('', 12),
            yscrollcommand=scrollbar.set,
            bg='#fefefe',
            fg='#333',
            insertbackground='#333',
            padx=10,
            pady=10,
            relief=tk.FLAT,
            highlightthickness=0
        )
        self.content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.content_text.yview)

        # 提示文字
        self.content_text.insert('1.0', "在这里输入笔记...\n\n支持 Markdown 格式\n\n快捷键:\n  Cmd+Enter: 保存并关闭\n  Cmd+N: 新建窗口\n  Esc: 关闭")
        self.content_text.tag.add('hint', '1.0', '5.0')
        self.content_text.tag_config('hint', foreground='#999')

        # 按钮栏
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        # 保存按钮
        save_btn = ttk.Button(
            btn_frame,
            text="💾 保存到日记",
            command=self.save_and_close,
            style='Accent.TButton'
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 5))

        # 清除按钮
        clear_btn = ttk.Button(
            btn_frame,
            text="🗑️ 清除",
            command=self.clear_content
        )
        clear_btn.pack(side=tk.LEFT)

        # 状态标签
        self.status_label = ttk.Label(btn_frame, text="", foreground='#666', font=('', 9))
        self.status_label.pack(side=tk.RIGHT)

        # 今日日记预览
        preview_frame = ttk.LabelFrame(main_frame, text="今日日记", padding="5")
        preview_frame.pack(fill=tk.X, pady=(10, 0))

        content, path, _ = read_today_diary()
        if content:
            preview_text = content[-300:] if len(content) > 300 else content
            preview_text = preview_text.replace('\n', ' ')
            preview_label = ttk.Label(
                preview_frame,
                text=f"📁 {path.name}\n最近: {preview_text}...",
                font=('', 8),
                foreground='#666',
                wraplength=WINDOW_WIDTH - 40
            )
            preview_label.pack(fill=tk.X)

    def center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - WINDOW_WIDTH) // 2
        y = (self.root.winfo_screenheight() - WINDOW_HEIGHT) // 2
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

    def bind_shortcuts(self):
        """绑定快捷键"""
        # Cmd+Enter 保存并关闭
        self.root.bind('<Command-Return>', lambda e: self.save_and_close())
        # Escape 关闭
        self.root.bind('<Escape>', lambda e: self.hide_window())
        # Cmd+N 新建 (在脚本中可调用)
        self.root.bind('<Command-n>', lambda e: self.new_note())
        # Cmd+V 粘贴 (处理图片粘贴)
        self.content_text.bind('<Command-v>', self.handle_paste)
        self.content_text.bind('<Command-V>', self.handle_paste)

        # 焦点丢失时隐藏 (可选)
        # self.root.bind('<FocusOut>', lambda e: self.hide_window())

    def handle_paste(self, event):
        """处理粘贴事件，支持图片粘贴"""
        # 尝试从剪贴板保存图片和
        image_link = save_clipboard_image()
        if image_link:
            # 如果有图片，插入 Markdown 链接
            self.content_text.insert(tk.INSERT, image_link)
            self.status_label.config(text="🖼️ 图片已插入", foreground='#2a9d2a')
            self.root.update()
            # 2秒后清除状态
            self.root.after(2000, lambda: self.status_label.config(text=""))
            return "break"  # 阻止默认粘贴行为
        
        # 如果不是图片，执行默认粘贴 (文本)
        return None

    def save_and_close(self):
        """保存并关闭"""
        content = self.content_text.get('1.0', tk.END).strip()

        # 检查是否是提示文字
        if content.startswith("在这里输入笔记"):
            content = ""

        title = self.title_var.get().strip()

        if content:
            success, msg = save_to_diary(content, title)
            if success:
                self.status_label.config(text="✅ 已保存!", foreground='#2a9d2a')
                self.root.update()
                self.root.after(800, self.hide_window)
            else:
                self.status_label.config(text=f"❌ {msg}", foreground='#d63031')
        else:
            self.hide_window()

    def clear_content(self):
        """清除内容"""
        self.content_text.delete('1.0', tk.END)
        self.title_var.set("")
        self.status_label.config(text="")

    def hide_window(self):
        """隐藏窗口"""
        self.root.withdraw()

    def show_window(self):
        """显示窗口"""
        self.clear_content()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.content_text.focus_set()

    def new_note(self):
        """新建笔记"""
        self.clear_content()
        self.show_window()

    def run(self):
        """运行应用"""
        # 启动时隐藏窗口，通过快捷键呼出
        self.root.withdraw()
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.root.mainloop()

# ==================== 入口 ====================
if __name__ == "__main__":
    # 检查 Obsidian 目录
    if not OBSIDIAN_DIARY.exists():
        print(f"警告: Obsidian 日记目录不存在: {OBSIDIAN_DIARY}")
        print("将自动创建...")

    # 确保目录存在
    OBSIDIAN_DIARY.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print("QuickNote 浮动备忘录")
    print("=" * 50)
    print("启动中...")

    app = QuickNoteApp()

    # 在新线程中运行 GUI
    gui_thread = threading.Thread(target=app.run, daemon=True)
    gui_thread.start()

    # 保持主线程运行
    print("\n💡 使用提示:")
    print("  - 窗口已最小化到后台")
    print("  - 需要设置全局快捷键来呼出窗口")
    print("\n设置 macOS 全局快捷键:")
    print("  1. 系统设置 -> 键盘 -> 快捷键")
    print("  2. App 快捷键 -> 添加快捷键")
    print("  3. 选择 'QuickNote' 或运行脚本的 App")
    print("  4. 设置快捷键如 Cmd+Shift+N")
    print("\n按 Enter 键显示窗口...")
    input()

    app.show_window()

    gui_thread.join()
