#!/usr/bin/env python3
"""
QuickNote Menu Bar - 菜单栏版本
- 每天一个文件
- 支持粘贴图片 (通过 osascript 读取剪贴板)
- 可配置设置
"""

import rumps
import subprocess
import os
import shutil
import hashlib
import json
import tempfile
from datetime import datetime
from pathlib import Path

# ==================== 配置 ====================
# 使用本地 Documents 目录,避免 iCloud Drive 沙盒权限问题
LOCAL_QUICKNOTES = Path.home() / "Documents/QuickNotes"
CONFIG_PATH = Path.home() / "Library/Preferences/com.quicknote.menubar.json"

DEFAULT_CONFIG = {
    "save_path": str(LOCAL_QUICKNOTES),
    "show_notifications": True
}

# ==================== 配置管理 ====================
def load_config():
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    CONFIG_PATH.write_text(json.dumps(config, indent=2))

def get_save_path():
    config = load_config()
    save_path = Path(config.get("save_path", str(LOCAL_QUICKNOTES)))
    # 如果路径是 Obsidian vault 根目录，自动使用 QuickNotes 子文件夹
    if save_path.name == "Documents" and not str(save_path).endswith("QuickNotes"):
        save_path = save_path / "06📓QuickNotes"
    return save_path

def get_attachments_dir():
    return get_save_path() / "attachments"

# ==================== 工具函数 ====================
def get_chinese_weekday():
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    return weekdays[datetime.now().weekday()]

def get_daily_file_path():
    save_path = get_save_path()
    today = datetime.now()
    date_str = today.strftime("%y%m%d")
    month_folder = f"26_{today.strftime('%m')}"
    month_path = save_path / month_folder
    if month_path.exists():
        diary_path = month_path / f"{date_str}.md"
    else:
        diary_path = save_path / f"{date_str}.md"
    return diary_path

def ensure_daily_file():
    diary_path = get_daily_file_path()
    today = datetime.now()
    date_full = today.strftime("%Y-%m-%d")
    if not diary_path.exists():
        content = f"# 日记 {date_full}\n\n"
        diary_path.parent.mkdir(parents=True, exist_ok=True)
        diary_path.write_text(content, encoding='utf-8')
    return diary_path

def save_to_daily(content: str):
    # 处理图片路径文本 (从对话框粘贴的图片)
    import re
    image_ref_pattern = r'\[Image:\s*source:\s*(/var/[^]]+)\]'
    has_image_refs = re.search(image_ref_pattern, content, re.IGNORECASE) if content else False

    image_links = []
    if has_image_refs:
        # 有图片引用 - 直接从剪贴板读取图片
        # (临时文件可能已清理,所以直接从剪贴板读取)
        clip_link = save_clipboard_image()
        if clip_link:
            image_links.append(clip_link)

        # 移除所有图片引用
        content = re.sub(image_ref_pattern, '', content, flags=re.IGNORECASE)

    content = content.strip()

    diary_path = ensure_daily_file()
    today = datetime.now()
    time_str = today.strftime("%H:%M:%S")

    existing_content = diary_path.read_text(encoding='utf-8')
    header = f"### {time_str}"

    # 组合内容和图片链接
    full_content = content
    if image_links:
        if full_content:
            full_content += "\n\n" + "\n".join(image_links)
        else:
            full_content = "\n".join(image_links)

    # 如果没有实际内容
    if not full_content.strip():
        return False, "内容为空"

    new_entry = f"{existing_content.rstrip()}\n\n{header}\n\n{full_content}\n"

    diary_path.write_text(new_entry, encoding='utf-8')
    return True, str(diary_path)

def copy_attachment(file_path: Path) -> str:
    attachments_dir = get_attachments_dir()
    attachments_dir.mkdir(parents=True, exist_ok=True)

    ext = file_path.suffix.lower()
    timestamp = datetime.now().strftime("%H%M%S")
    file_hash = hashlib.md5(file_path.read_bytes()[:1024]).hexdigest()[:6]
    new_filename = f"{timestamp}_{file_hash}{ext}"
    dest_path = attachments_dir / new_filename

    shutil.copy2(file_path, dest_path)

    image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.heic'}
    if ext in image_exts:
        return f"![{file_path.name}](attachments/{new_filename})"
    else:
        return f"[{file_path.name}](attachments/{new_filename})"

def save_clipboard_image() -> str:
    """保存剪贴板图片，返回 markdown 链接"""
    timestamp = datetime.now().strftime("%H%M%S")
    temp_tiff = f"/tmp/qn_clip_{timestamp}.tiff"
    temp_png = f"/tmp/qn_clip_{timestamp}.png"

    # 方法1: 用 pngpaste (如果安装了)
    try:
        result = subprocess.run(['which', 'pngpaste'], capture_output=True, text=True)
        if result.returncode == 0:
            result = subprocess.run(['pngpaste', temp_png], capture_output=True, timeout=5)
            if Path(temp_png).exists() and Path(temp_png).stat().st_size > 100:
                link = copy_attachment(Path(temp_png))
                Path(temp_png).unlink(missing_ok=True)
                return link
    except:
        pass

    # 方法2: 用 screencapture 截图剪贴板内容
    try:
        # 先检查剪贴板是否有图片数据
        check = subprocess.run(
            ['osascript', '-e', 'clipboard info'],
            capture_output=True, text=True, timeout=5
        )
        if 'picture' in check.stdout or 'PNG' in check.stdout or 'TIFF' in check.stdout:
            # 用 osascript 读取为 TIFF
            read_script = f'''
            try
                set the clipboard to (read (the clipboard as TIFF picture))
                do shell script "osascript -e 'set the clipboard to (read (the clipboard as TIFF picture))' > {temp_tiff} 2>/dev/null || echo ''"
                return "ok"
            on error
                return "error"
            end try
            '''
            subprocess.run(['osascript', '-e', read_script], capture_output=True, timeout=5)

            if Path(temp_tiff).exists() and Path(temp_tiff).stat().st_size > 100:
                subprocess.run(['sips', '-s', 'format', 'png', temp_tiff, '--out', temp_png],
                             capture_output=True, timeout=5)
                if Path(temp_png).exists():
                    link = copy_attachment(Path(temp_png))
                    Path(temp_tiff).unlink(missing_ok=True)
                    Path(temp_png).unlink(missing_ok=True)
                    return link
            Path(temp_tiff).unlink(missing_ok=True)
    except:
        pass

    return None

def show_notification(title: str, message: str):
    config = load_config()
    if config.get("show_notifications", True):
        subprocess.run(['osascript', '-e', f'display notification "{message}" with title "{title}"'])

def show_input_dialog():
    """显示输入对话框"""
    today = datetime.now()
    date_full = today.strftime("%Y-%m-%d")

    script = f'''
    set theResult to (display dialog "📝 快速笔记" & return & return & "日期: {date_full}" & return & "保存时自动检测剪贴板图片" default answer "" buttons {{"取消", "添加附件", "保存"}} default button 3 giving up after 300 with title "QuickNote ✏️")
    return text returned of theResult & "|" & button returned of theResult
    '''

    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=300)

        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split('|')
            if len(parts) >= 2:
                content = parts[0]
                button = parts[1]

                # 添加附件循环
                attachments = []
                while button == "添加附件":
                    file_script = '''
                    set theFiles to choose file with prompt "选择图片或附件" with multiple selections allowed
                    set filePaths to ""
                    repeat with aFile in theFiles
                        if filePaths is "" then
                            set filePaths to POSIX path of aFile
                        else
                            set filePaths to filePaths & "," & POSIX path of aFile
                        end if
                    end repeat
                    return filePaths
                    '''
                    try:
                        file_result = subprocess.run(['osascript', '-e', file_script],
                                                    capture_output=True, text=True, timeout=60)
                        if file_result.returncode == 0 and file_result.stdout.strip():
                            for path in file_result.stdout.strip().split(','):
                                path = path.strip()
                                if path:
                                    link = copy_attachment(Path(path))
                                    attachments.append(link)
                    except:
                        pass

                    # 继续添加?
                    cont_script = '''
                    display dialog "继续添加?" buttons {"完成", "添加更多"} default button 1 giving up after 60 with title "QuickNote ✏️"
                    return button returned of result
                    '''
                    try:
                        cont_result = subprocess.run(['osascript', '-e', cont_script],
                                                     capture_output=True, text=True, timeout=65)
                        if cont_result.returncode == 0:
                            if cont_result.stdout.strip() == "添加更多":
                                continue
                    except:
                        pass
                    break

                # 自动检测剪贴板图片
                clipboard_link = save_clipboard_image()
                if clipboard_link:
                    attachments.append(clipboard_link)

                # 组合内容
                full_content = content
                if attachments:
                    if full_content:
                        full_content += "\n\n" + "\n".join(attachments)
                    else:
                        full_content = "\n".join(attachments)

                success, msg = save_to_daily(full_content)

                if success:
                    count = len(attachments) + (1 if clipboard_link else 0)
                    if count > 0:
                        show_notification("QuickNote ✏️", f"已保存! 含 {count} 个附件 ✓")
                    else:
                        show_notification("QuickNote ✏️", "已保存到日记 ✓")
                else:
                    show_notification("QuickNote ✏️", f"❌ {msg}")
    except subprocess.TimeoutExpired:
        show_notification("QuickNote ✏️", "⏰ 超时已取消")
    except Exception as e:
        show_notification("QuickNote ✏️", f"❌ 错误: {e}")

def show_settings_dialog():
    """显示设置对话框"""
    config = load_config()
    save_path = config.get("save_path", str(LOCAL_QUICKNOTES))
    show_notify = config.get("show_notifications", True)

    script = f'''
    set theDialog to display dialog "⚙️ QuickNote 设置" & return & return & "保存路径:" default answer "{save_path}" buttons {{"取消", "保存"}} default button 2 giving up after 300 with title "QuickNote ✏️"
    return text returned of theDialog
    '''

    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and result.stdout.strip():
            new_path = result.stdout.strip()
            if new_path:
                config["save_path"] = new_path
                save_config(config)
                show_notification("QuickNote ✏️", "设置已保存 ✓")
    except:
        pass

# ==================== 菜单栏应用 ====================
class QuickNoteApp(rumps.App):
    def __init__(self):
        super().__init__("📝")
        self.menu = [
            rumps.MenuItem("快速记录 ✏️", callback=self.on_quick_note),
            None,
            rumps.MenuItem("设置 ⚙️", callback=self.on_settings),
            rumps.MenuItem("打开 QuickNotes", callback=self.open_folder),
            None,
            rumps.MenuItem("退出", callback=self.on_quit)
        ]

    @rumps.clicked("快速记录 ✏️")
    def on_quick_note(self, sender):
        show_input_dialog()

    @rumps.clicked("设置 ⚙️")
    def on_settings(self, sender):
        show_settings_dialog()

    @rumps.clicked("打开 QuickNotes")
    def open_folder(self, sender):
        subprocess.run(['open', str(get_save_path())])

    @rumps.clicked("退出")
    def on_quit(self, sender):
        rumps.quit_application()

# ==================== 主程序 ====================
if __name__ == "__main__":
    app = QuickNoteApp()
    app.run()
