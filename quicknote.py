#!/usr/bin/env python3
"""
QuickNote - 浮动备忘录 for Obsidian
支持全局快捷键呼出浮动窗口，记录 Markdown 笔记并同步到 Obsidian 日记

使用方法:
  python3 quicknote.py                    # 启动
  设置全局快捷键: Cmd+Shift+N           # macOS 系统设置中配置

依赖安装:
  pip3 install python3-xlib

或仅使用基础版（无需额外依赖）
"""

import os
import sys
import re
import subprocess
from datetime import datetime
from pathlib import Path

# Obsidian 日记目录
OBSIDIAN_DIARY = Path("/Users/jiamingli_1/Library/Mobile Documents/iCloud~md~obsidian/Documents/01📘Diary")
OBSIDIAN_DIARY_2 = Path("/Users/jiamingli_1/Library/Mobile Documents/iCloud~md~obsidian/Documents/01📘Diary/26_04")

# 尝试导入 tkinter
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False
    print("Warning: tkinter not available, running in CLI mode")

# ==================== CLI 模式 ====================
def get_today_diary_path():
    """获取今天的日记文件路径"""
    today = datetime.now()
    date_str = today.strftime("%y-%m-%d")
    weekday = ["一", "二", "三", "四", "五", "六", "日"][today.weekday()]

    # 优先使用 26_04 子文件夹
    if OBSIDIAN_DIARY_2.exists():
        diary_path = OBSIDIAN_DIARY_2 / f"{date_str}.md"
    else:
        diary_path = OBSIDIAN_DIARY / f"{date_str}.md"

    return diary_path, weekday

def read_today_diary():
    """读取今日日记内容"""
    diary_path, weekday = get_today_diary_path()
    if diary_path.exists():
        with open(diary_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, diary_path
    return "", diary_path

def append_to_diary(content: str):
    """追加内容到日记"""
    if not content.strip():
        print("内容为空，跳过保存")
        return False

    existing_content, diary_path = read_today_diary()
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    weekday = ["一", "二", "三", "四", "五", "六", "日"][today.weekday()]

    # 构建新条目
    time_str = today.strftime("%H:%M")
    new_entry = f"\n## 📝 {date_str} {time_str} ({weekday})\n\n{content}\n"

    # 检查是否已存在同一天记
    if f"## 📝 {date_str}" in existing_content:
        # 追加到现有日期
        # 找到最后一个相同日期条目的位置
        pattern = f"(## 📝 {date_str}.*?)(?=## 📝 |$)"
        match = re.search(pattern, existing_content, re.DOTALL)
        if match:
            # 在现有条目后追加
            existing_entry = match.group(1)
            existing_entry_without_footer = existing_entry.rsplit('\n', 2)[0] if '\n\n' in existing_entry else existing_entry
            # 简单追加到末尾
            new_content = existing_content.rstrip() + new_entry
        else:
            new_content = existing_content + new_entry
    else:
        # 新日期，直接添加
        new_content = existing_content.rstrip() + new_entry

    # 写入文件
    with open(diary_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True

def cli_mode():
    """命令行模式"""
    print("=" * 50)
    print("QuickNote CLI 模式")
    print("=" * 50)

    print("\n📖 今日日记预览:")
    content, path = read_today_diary()
    if content:
        print(f"文件: {path}")
        print("-" * 30)
        print(content[:500] + "..." if len(content) > 500 else content)
    else:
        print("今日日记为空")

    print("\n✏️  输入你要记录的内容 (多行输入，输入 END 结束):")
    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        except EOFError:
            break

    content = '\n'.join(lines)
    if append_to_diary(content):
        print("\n✅ 已保存到日记!")
        print(f"📁 {path}")
    else:
        print("\n❌ 保存失败或内容为空")

def create_launcher_script():
    """创建 macOS 应用包装脚本"""
    script_content = '''#!/bin/bash
# QuickNote 启动器
# 将此文件保存为 QuickNote.sh 并给予执行权限

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/quicknote.py"
'''
    return script_content

if __name__ == "__main__":
    if not HAS_TKINTER:
        cli_mode()
        sys.exit(0)

    # 如果有参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--cli":
            cli_mode()
            sys.exit(0)

    # 默认启动 GUI
    print("QuickNote 浮动备忘录已启动")
    print("提示: 使用 Cmd+Shift+N (系统快捷键) 或点击窗口呼出")
    cli_mode()
