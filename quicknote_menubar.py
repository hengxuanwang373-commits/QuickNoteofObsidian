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
    import re
    image_links = []

    # 处理图片路径文本 (从对话框粘贴的图片引用)
    image_ref_pattern = r'\[Image:\s*source:\s*(/var/[^]]+)\]'
    has_image_refs = re.search(image_ref_pattern, content, re.IGNORECASE) if content else False

    if has_image_refs:
        clip_link = save_clipboard_image()
        if clip_link:
            image_links.append(clip_link)
        content = re.sub(image_ref_pattern, '', content, flags=re.IGNORECASE)

    content = content.strip()

    # 如果内容为空但仍尝试保存图片，也检查剪贴板
    if not content:
        clip_link = save_clipboard_image()
        if clip_link:
            image_links.append(clip_link)

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
    temp_png = f"/tmp/qn_clip_{timestamp}.png"

    # 方法1: 用 python3 + AppKit 读取剪贴板图片 (macOS 原生, 最可靠)
    try:
        python_clipboard_script = f'''
import sys
try:
    from AppKit import NSPasteboard, NSBitmapImageRep
    from Foundation import NSData
    pb = NSPasteboard.generalPasteboard()
    types = pb.types()
    # 检查是否有图片类型
    image_types = ["Apple TIFF pasteboard type", "Apple PNG pasteboard type",
                   "com.apple.cocoa TIFF", "com.apple.cocoa PNG",
                   "com.apple.Preview document", "public.png", "public.tiff"]
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
    except:
        pass

    # 方法2: 用 pngpaste (如果安装了: brew install pngpaste)
    try:
        result = subprocess.run(['which', 'pngpaste'], capture_output=True, text=True)
        if result.returncode == 0:
            pngpaste_temp = f"/tmp/qn_clip_paste_{timestamp}.png"
            result = subprocess.run(['pngpaste', pngpaste_temp], capture_output=True, timeout=5)
            if result.returncode == 0 and Path(pngpaste_temp).exists() and Path(pngpaste_temp).stat().st_size > 50:
                link = copy_attachment(Path(pngpaste_temp))
                Path(pngpaste_temp).unlink(missing_ok=True)
                return link
    except:
        pass

    # 方法3: 用 sips + 临时文件方法 (osascript write 方式)
    try:
        check = subprocess.run(
            ['osascript', '-e', 'clipboard info'],
            capture_output=True, text=True, timeout=5
        )
        info = check.stdout.lower()
        has_image = any(kw in info for kw in ['tiff', 'png ', 'picture', 'image', '«class png'])
        if has_image:
            # 用 python3 AppKit 作为最后的 fallback (与方法1相同, 但确保执行)
            save_script = f'''
try:
    from AppKit import NSPasteboard
    pb = NSPasteboard.generalPasteboard()
    data = pb.dataForType_("public.png")
    if data is None:
        data = pb.dataForType_("public.tiff")
    if data is None:
        from Foundation import NSData
        tiff = pb.dataForType_("com.apple.cocoa TIFF")
        if tiff:
            import subprocess
            # Convert TIFF to PNG via sips
            tiff_path = "/tmp/qn_clip_fallback.tiff"
            tiff.writeToFile_atomically_(tiff_path, True)
            import os
            os.system(f"sips -s format png {{tiff_path}} --out {temp_png}")
            print("ok")
        else:
            print("no image")
    else:
        data.writeToFile_atomically_("{temp_png}", True)
        print("ok")
except Exception as e:
    print(f"error: {{e}}")
'''
            result = subprocess.run(
                ['python3', '-c', save_script],
                capture_output=True, text=True, timeout=10
            )
            if Path(temp_png).exists() and Path(temp_png).stat().st_size > 50:
                link = copy_attachment(Path(temp_png))
                Path(temp_png).unlink(missing_ok=True)
                return link
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

    # 先检测剪贴板是否有图片
    clipboard_link = save_clipboard_image()
    has_image = "✅ 有" if clipboard_link else "❌ 无"

    script = f'''
    set theResult to (display dialog "📝 快速笔记" & return & return & "📅 日期: {date_full}" & return & "剪贴板图片: {has_image}" & return & return & "💡 提示: 先点击「粘贴图片」按钮，再写文字" default answer "" buttons {{"取消", "粘贴图片", "保存"}} default button 3 giving up after 300 with title "QuickNote ✏️")
    return text returned of theResult & "|" & button returned of theResult
    '''

    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=300)

        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split('|')
            if len(parts) >= 2:
                content = parts[0]
                button = parts[1]

                attachments = []
                image_markdown = ""

                # 粘贴图片按钮
                if button == "粘贴图片":
                    # 重新检测剪贴板图片
                    clip_link = save_clipboard_image()
                    if clip_link:
                        image_markdown = clip_link
                        show_notification("QuickNote ✏️", "🖼️ 图片已粘贴到文本!")
                    else:
                        show_notification("QuickNote ✏️", "❌ 剪贴板中没有图片")

                    # 再次弹出输入框，让用户继续输入
                    script2 = f'''
                    set theResult to (display dialog "📝 快速笔记 - 图片已插入" & return & return & "📅 日期: {date_full}" & return & "图片已添加: {image_markdown if image_markdown else "(无)"}" default answer "{image_markdown}" buttons {{"取消", "继续添加图片", "保存"}} default button 3 giving up after 300 with title "QuickNote ✏️")
                    return text returned of theResult & "|" & button returned of theResult
                    '''
                    try:
                        result2 = subprocess.run(['osascript', '-e', script2], capture_output=True, text=True, timeout=300)
                        if result2.returncode == 0 and result2.stdout.strip():
                            parts2 = result2.stdout.strip().split('|')
                            if len(parts2) >= 2:
                                content = parts2[0]
                                button2 = parts2[1]

                                # 继续添加图片循环
                                while button2 == "继续添加图片":
                                    clip_link2 = save_clipboard_image()
                                    if clip_link2:
                                        content = content + "\n" + clip_link2
                                        show_notification("QuickNote ✏️", "🖼️ 图片已追加!")
                                    else:
                                        show_notification("QuickNote ✏️", "❌ 剪贴板中没有图片")

                                    script3 = '''
                                    set theResult to (display dialog "📝 快速笔记" & return & return & "输入内容，或继续添加图片" default answer "" buttons {"取消", "继续添加图片", "保存"} default button 3 giving up after 300 with title "QuickNote ✏️")
                                    return text returned of theResult & "|" & button returned of theResult
                                    '''
                                    try:
                                        result3 = subprocess.run(['osascript', '-e', script3], capture_output=True, text=True, timeout=300)
                                        if result3.returncode == 0 and result3.stdout.strip():
                                            parts3 = result3.stdout.strip().split('|')
                                            if len(parts3) >= 2:
                                                content = parts3[0]
                                                button2 = parts3[1]
                                                if button2 != "继续添加图片":
                                                    break
                                        else:
                                            break
                                    except:
                                        break
                    except:
                        pass

                # 添加附件循环
                while button == "添加附件" or button == "继续添加图片":
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
