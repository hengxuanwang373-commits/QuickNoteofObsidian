#!/usr/bin/env python3
"""
QuickNote Simple - 轻量版
直接使用 osascript 显示对话框，无需额外依赖

使用方法:
  python3 quicknote_simple.py
"""

import subprocess
import os
from datetime import datetime
from pathlib import Path

# ==================== 配置 ====================
OBSIDIAN_QUICKNOTES = Path.home() / "Documents/QuickNotes"

# ==================== 工具函数 ====================
def get_chinese_weekday():
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    return weekdays[datetime.now().weekday()]

def save_to_quicknote(content: str):
    """保存内容到 QuickNotes"""
    if not content.strip():
        return False, "内容为空"

    today = datetime.now()
    date_full = today.strftime("%Y-%m-%d")
    time_str = today.strftime("%H-%M-%S")
    weekday = get_chinese_weekday()

    # 每个笔记保存为单独文件
    filename = f"{date_full}_{time_str}.md"
    note_path = OBSIDIAN_QUICKNOTES / filename

    # 构建笔记内容
    header = f"## 📝 {date_full} {today.strftime('%H:%M')} ({weekday})"
    note_content = f"{header}\n\n{content}\n"

    # 确保目录存在
    note_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入文件
    note_path.write_text(note_content, encoding='utf-8')

    return True, str(note_path)

def show_notification(title: str, message: str):
    """显示系统通知"""
    subprocess.run([
        'osascript', '-e',
        f'display notification "{message}" with title "{title}"'
    ])

def main():
    """主函数"""
    # 获取当前时间
    today = datetime.now()
    date_full = today.strftime("%Y-%m-%d")

    # 使用 osascript 显示输入框
    script = f'''
    set theInput to text returned of (display dialog "📝 快速笔记" & return & return & "保存到: {date_full}" default answer "" buttons {{"取消", "保存"}} default button 2 giving up after 300 with title "QuickNote ✏️")
    '''

    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0 and result.stdout.strip():
            content = result.stdout.strip()
            success, msg = save_to_quicknote(content)

            if success:
                show_notification("QuickNote", "已保存到 QuickNotes ✓")
                print(f"✅ 已保存: {msg}")
            else:
                print(f"❌ {msg}")
        else:
            print("取消")

    except subprocess.TimeoutExpired:
        print("超时已取消")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    main()
