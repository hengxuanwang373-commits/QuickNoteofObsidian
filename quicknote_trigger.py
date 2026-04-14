#!/usr/bin/env python3
"""
QuickNote 快速记录 - 独立弹窗脚本
由 macOS 服务 (Service) 触发，不需要辅助功能权限
"""
import subprocess
import sys
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime

LOCAL_QUICKNOTES = Path.home() / "Desktop/Obsidian/Documents/06📓QuickNotes"
CONFIG_PATH = Path.home() / "Library/Preferences/com.quicknote.menubar.json"


def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {"save_path": str(LOCAL_QUICKNOTES)}


def get_save_path():
    config = load_config()
    path = config.get("save_path")
    if path:
        return Path(path)
    return LOCAL_QUICKNOTES


def show_quicknote_dialog():
    """通过 osascript 显示输入对话框并保存笔记"""

    # 获取当前时间信息
    now = datetime.now()
    time_str = now.strftime("%H:%M")
    date_display = now.strftime("%Y-%m-%d")

    # 预填充内容
    initial_text = f"- {time_str}\n\n"

    save_path = get_save_path()
    today = now
    date_str = today.strftime("%y%m%d")
    month_folder = f"26_{today.strftime('%m')}"
    month_path = save_path / month_folder

    if month_path.exists():
        diary_path = month_path / f"{date_str}.md"
    else:
        diary_path = save_path / f"{date_str}.md"

    diary_path_display = str(diary_path)

    # 构建 AppleScript
    # 使用多行输入对话框
    script = f'''
    set initialText to "{initial_text}"

    display dialog "快速记录" & return & "保存到: {diary_path_display}" default answer initialText buttons {{"取消", "保存"}} default button 2 giving up after 600 with title "QuickNote ✏️"
    set resultText to text returned of result
    do shell script "echo " & quoted form of resultText & " >> " & quoted form of "{diary_path_display}"
    return "saved"
    '''

    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=600
        )
        if result.returncode == 0:
            # 弹窗通知成功
            subprocess.run([
                'osascript', '-e',
                'display notification "笔记已保存 ✓" with title "QuickNote ✏️"'
            ], capture_output=True)
        else:
            if "User canceled" not in result.stderr:
                print(f"Error: {result.stderr}", file=sys.stderr)
    except subprocess.TimeoutExpired:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    show_quicknote_dialog()
