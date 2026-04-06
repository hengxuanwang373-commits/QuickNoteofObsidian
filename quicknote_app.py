#!/usr/bin/env python3
"""
QuickNote App - 状态栏备忘录
后台运行，点击菜单栏图标随时记录

依赖: pip3 install pynput (用于全局快捷键)
或仅使用菜单栏点击

使用方法:
  python3 quicknote_app.py
  设为登录项: 系统设置 -> 用户与群组 -> 登录项
"""

import os
import sys
import re
import subprocess
import threading
from datetime import datetime
from pathlib import Path

# ==================== 配置 ====================
OBSIDIAN_DIARY = Path("/Users/jiamingli_1/Library/Mobile Documents/iCloud~md~obsidian/Documents/01📘Diary")
MENU_BAR_ICON = "📝"  # 或使用 "✏️"

# ==================== 尝试导入状态栏库 ====================
try:
    import rumps
    HAS_RUMPS = True
except ImportError:
    HAS_RUMPS = False
    print("注意: rumps 未安装，菜单栏功能受限")
    print("安装命令: pip3 install rumps")

# ==================== Obsidian 集成 ====================
def get_today_diary_path():
    """获取今天的日记文件路径"""
    today = datetime.now()
    date_str = today.strftime("%y-%m-%d")
    month_folder = f"26_{today.strftime('%m')}"
    month_path = OBSIDIAN_DIARY / month_folder

    if month_path.exists():
        diary_path = month_path / f"{date_str}.md"
    else:
        diary_path = OBSIDIAN_DIARY / f"{date_str}.md"

    return diary_path

def get_chinese_weekday():
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    return weekdays[datetime.now().weekday()]

def save_to_diary(content: str, title: str = ""):
    """保存内容到日记"""
    if not content.strip():
        return False, "内容为空"

    diary_path = get_today_diary_path()
    today = datetime.now()
    date_full = today.strftime("%Y-%m-%d")
    time_str = today.strftime("%H:%M")
    weekday = get_chinese_weekday()

    # 读取现有内容
    try:
        if diary_path.exists():
            existing_content = diary_path.read_text(encoding='utf-8')
        else:
            existing_content = f"# 日记 {date_full}\n\n"
    except:
        existing_content = f"# 日记 {date_full}\n\n"

    # 构建新条目
    if title.strip():
        header = f"## 📌 {title.strip()} {date_full} {time_str} ({weekday})"
    else:
        header = f"## 📝 {date_full} {time_str} ({weekday})"

    new_entry = f"\n{header}\n\n{content}\n"
    new_content = existing_content.rstrip() + new_entry

    # 确保目录存在
    diary_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入文件
    diary_path.write_text(new_content, encoding='utf-8')

    return True, str(diary_path)

# ==================== Rumps 状态栏版本 ====================
@rumps.appserver
class QuickNoteApp(rumps.App):
    """QuickNote 状态栏应用"""

    def __init__(self):
        super().__init__("QuickNote")
        self.menu = [
            rumps.MenuItem("📝 新建笔记", callback=self.show_note_window),
            None,  # 分隔线
            rumps.MenuItem("📖 今日日记", callback=self.show_today_diary),
            None,
            rumps.MenuItem("⚙️ 设置", callback=self.show_settings),
            None,
            rumps.MenuItem("❌ 退出", callback=self.quit_app),
        ]

    @rumps.clicked("📝 新建笔记")
    def show_note_window(self, _):
        """显示新建笔记窗口"""
        # 使用 macOS 的 osascript 显示输入框
        script = '''
        set theInput to text returned of (display dialog "📝 快速笔记" & return & return & "输入内容将保存到今日日记" default answer "" buttons {"取消", "保存"} default button 2 giving up after 300)
        '''

        try:
            result = subprocess.run(['osascript', '-e', script],
                                 capture_output=True, text=True, timeout=300)

            if result.returncode == 0 and result.stdout.strip():
                content = result.stdout.strip()
                success, msg = save_to_diary(content)
                if success:
                    subprocess.run(['osascript', '-e',
                                  f'display notification "已保存到日记 ✓" with title "QuickNote"'])
                else:
                    subprocess.run(['osascript', '-e',
                                  f'display dialog "保存失败: {msg}" buttons {{"OK"}}'])
        except Exception as e:
            print(f"Error: {e}")

    @rumps.clicked("📖 今日日记")
    def show_today_diary(self, _):
        """打开今日日记"""
        diary_path = get_today_diary_path()
        subprocess.run(['open', '-a', 'Obsidian', str(diary_path)])

    @rumps.clicked("⚙️ 设置")
    def show_settings(self, _):
        """显示设置"""
        subprocess.run(['open', '/Users/jiamingli_1/QuickNote'])

    def quit_app(self, _):
        """退出应用"""
        rumps.quit_application()

# ==================== 无 Rumps 的简化版本 ====================
def simple_macos_note():
    """使用 osascript 的简单版本"""
    print("QuickNote 状态栏应用")
    print("=" * 40)

    while True:
        print("\n选择操作:")
        print("1. 📝 新建笔记")
        print("2. 📖 打开今日日记")
        print("3. ❌ 退出")

        choice = input("\n请输入 (1/2/3): ").strip()

        if choice == "1":
            script = '''
            set theInput to text returned of (display dialog "📝 快速笔记" & return & return & "输入内容将保存到今日日记" default answer "" buttons {"取消", "保存"} default button 2 giving up after 300)
            '''
            try:
                result = subprocess.run(['osascript', '-e', script],
                                     capture_output=True, text=True, timeout=300)
                if result.returncode == 0 and result.stdout.strip():
                    content = result.stdout.strip()
                    success, msg = save_to_diary(content)
                    if success:
                        print("✅ 已保存到日记!")
                    else:
                        print(f"❌ {msg}")
            except Exception as e:
                print(f"Error: {e}")

        elif choice == "2":
            diary_path = get_today_diary_path()
            print(f"📖 打开: {diary_path}")
            subprocess.run(['open', '-a', 'Obsidian', str(diary_path)])

        elif choice == "3":
            print("👋 再见!")
            break

# ==================== 入口 ====================
if __name__ == "__main__":
    # 确保目录存在
    OBSIDIAN_DIARY.mkdir(parents=True, exist_ok=True)

    if HAS_RUMPS:
        # 使用 rumps 状态栏版本
        app = QuickNoteApp()
        app.run()
    else:
        # 降级为命令行版本
        simple_macos_note()
