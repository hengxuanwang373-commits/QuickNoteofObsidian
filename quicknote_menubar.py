#!/usr/bin/env python3
"""
QuickNote Menu Bar - 菜单栏版本
- 每天一个文件
- 支持粘贴图片 (通过 osascript 读取剪贴板)
- 可配置设置
- 支持全局快捷键
"""

import rumps
import subprocess
import os
import shutil
import hashlib
import json
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from collections import defaultdict

try:
    import AppKit
    from PyObjCTools import AppHelper
    HAS_PYOBJC = True
except ImportError:
    HAS_PYOBJC = False

# ==================== 配置 ====================
# 使用本地 Documents 目录,避免 iCloud Drive 沙盒权限问题
LOCAL_QUICKNOTES = Path.home() / "Documents/QuickNotes"
CONFIG_PATH = Path.home() / "Library/Preferences/com.quicknote.menubar.json"

DEFAULT_CONFIG = {
    "save_path": str(LOCAL_QUICKNOTES),
    "show_notifications": True,
    "global_shortcut": "",
    "dialog_width": 500,
    "dialog_height": 300
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
    save_path_str = os.path.expanduser(config.get("save_path", str(LOCAL_QUICKNOTES)))
    save_path = Path(save_path_str)
    # 如果路径是 Obsidian vault 根目录，自动使用 QuickNotes 子文件夹
    if save_path.name == "Documents" and not str(save_path).endswith("QuickNotes"):
        save_path = save_path / "06📓QuickNotes"
    return save_path

def get_attachments_dir():
    return get_save_path() / "attachments"

# ==================== 全局快捷键管理器 ====================
class GlobalHotkeyManager:
    """全局快捷键管理器 - 使用 NSEvent 监控 """

    def __init__(self):
        self.running = False
        self.monitor = None
        self.callback = None

    def _parseShortcut(self, shortcut_str: str):
        """解析快捷键字符串，如 '⌘⇧N' -> (keycode, modifiers)"""
        modifiers = {'cmd': False, 'ctrl': False, 'alt': False, 'shift': False}
        key_char = None

        # 快捷键码映射
        key_map = {
            'A': 0x00, 'S': 0x01, 'D': 0x02, 'F': 0x03, 'H': 0x04,
            'G': 0x05, 'Z': 0x06, 'X': 0x07, 'C': 0x08, 'V': 0x09,
            'B': 0x0B, 'Q': 0x0C, 'W': 0x0D, 'E': 0x0E, 'R': 0x0F,
            'Y': 0x10, 'T': 0x11, '1': 0x12, '2': 0x13, '3': 0x14,
            '4': 0x15, '6': 0x16, '5': 0x17, '9': 0x19, '7': 0x1A,
            '8': 0x1C, '0': 0x1D, 'O': 0x1F, 'U': 0x20, 'I': 0x22,
            'P': 0x23, 'L': 0x25, 'J': 0x26, 'K': 0x28, 'N': 0x2D,
            'M': 0x2E, 'SPACE': 0x31,
        }

        for part in shortcut_str.split():
            part = part.strip()
            if '⌘' in part or 'Cmd' in part or 'Command' in part:
                modifiers['cmd'] = True
            if '⇧' in part or 'Shift' in part:
                modifiers['shift'] = True
            if '⌥' in part or 'Opt' in part or 'Alt' in part:
                modifiers['alt'] = True
            if '⌃' in part or 'Ctrl' in part:
                modifiers['ctrl'] = True
            for k in key_map:
                if k.lower() in part.lower():
                    key_char = k.upper()
                    break

        if key_char and key_char in key_map:
            return key_map[key_char], modifiers
        return None, None

    def register(self, shortcut_str: str, callback):
        """注册全局快捷键"""
        if not shortcut_str:
            self.unregister()
            return True

        keycode, mods = self._parseShortcut(shortcut_str)
        if keycode is None:
            return False

        self.unregister()
        self.callback = callback
        self.shortcut_keycode = keycode
        self.shortcut_mods = mods

        # 尝试使用 NSEvent 全局监控
        try:
            from AppKit import NSEvent

            # NSEvent event types: NSKeyDown = 10
            NSKeyDownMask = 1 << 10  # 1024

            def event_handler(event):
                try:
                    if event.type() == 10:  # NSKeyDown
                        flags = event.modifierFlags()
                        key_code = event.keyCode()

                        # 检查修饰键
                        check_cmd = mods.get('cmd', False)
                        check_shift = mods.get('shift', False)
                        check_alt = mods.get('alt', False)
                        check_ctrl = mods.get('ctrl', False)

                        # 获取当前修饰键状态 (NSEvent modifierFlags bitmasks)
                        has_cmd = bool(flags & 0x100000)   # NSCommandKeyMask
                        has_shift = bool(flags & 0x20000)  # NSShiftKeyMask
                        has_alt = bool(flags & 0x80000)    # NSAlternateKeyMask
                        has_ctrl = bool(flags & 0x40000)   # NSControlKeyMask

                        if key_code == keycode:
                            if (check_cmd == has_cmd and
                                check_shift == has_shift and
                                check_alt == has_alt and
                                check_ctrl == has_ctrl):
                                if self.callback:
                                    self.callback()
                                return True
                except:
                    pass
                return False

            self.monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                NSKeyDownMask, event_handler
            )
            self.running = True
            return True
        except Exception as e:
            print(f"NSEvent 监控失败: {e}")
            return False

    def unregister(self):
        """注销快捷键"""
        self.running = False
        if self.monitor:
            try:
                NSEvent.removeMonitor_(self.monitor)
            except:
                pass
            self.monitor = None
        self.callback = None


# 全局快捷键管理器实例
hotkey_manager = GlobalHotkeyManager()
hotkey_callback_ref = None


def setup_global_hotkey():
    """设置全局快捷键（由应用启动时调用）"""
    global hotkey_callback_ref
    config = load_config()
    shortcut = config.get("global_shortcut", "")

    def trigger_note():
        show_input_dialog()

    hotkey_callback_ref = trigger_note
    if shortcut:
        success = hotkey_manager.register(shortcut, trigger_note)
        if success and config.get("show_notifications", True):
            show_notification("QuickNote ✨", f"全局快捷键 {shortcut} 已配置 ✓")
        else:
            # 即使注册失败也保存配置
            show_notification("QuickNote ✨", f"快捷键已保存，重启应用后生效")


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
    if not HAS_PYOBJC:
        return None

    timestamp = datetime.now().strftime("%H%M%S")
    temp_png = f"/tmp/qn_clip_{timestamp}.png"

    # 直接用 AppKit 读取剪贴板（在主进程中调用，不需要 subprocess）
    try:
        from AppKit import NSPasteboard
        from Foundation import NSData

        pb = NSPasteboard.generalPasteboard()
        types = pb.types()

        # 检查是否有图片类型
        image_types = {
            "Apple TIFF pasteboard type", "Apple PNG pasteboard type",
            "com.apple.cocoa TIFF", "com.apple.cocoa PNG",
            "public.png", "public.tiff"
        }
        has_image = any(t in types for t in image_types)
        if not has_image:
            return None

        # 尝试获取 PNG 数据
        png_data = pb.dataForType_("public.png")
        tiff_data = pb.dataForType_("public.tiff") or pb.dataForType_("com.apple.cocoa TIFF")
        data = png_data if png_data else tiff_data

        if data is None:
            return None

        # 写入 PNG 文件
        success = data.writeToFile_atomically_(temp_png, True)
        if not success or not Path(temp_png).exists():
            return None

        file_size = Path(temp_png).stat().st_size
        if file_size < 50:
            return None

        # 复制到附件目录
        link = copy_attachment(Path(temp_png))
        Path(temp_png).unlink(missing_ok=True)
        return link

    except Exception as e:
        print(f"剪贴板读取失败: {e}")
        return None

    return None

def show_input_dialog():
    """显示输入对话框（使用可调整大小的文本框）"""
    config = load_config()
    today = datetime.now()
    date_full = today.strftime("%Y-%m-%d")

    # 获取配置的对话框尺寸
    dialog_width = config.get("dialog_width", 500)
    dialog_height = config.get("dialog_height", 300)

    # 先检测剪贴板是否有图片
    clipboard_link = save_clipboard_image()
    has_image = clipboard_link is not None

    # 提示信息
    prompt = f"📅 日期: {date_full}\n剪贴板图片: {'✅ 有' if has_image else '❌ 无'}\n\n💡 提示: 点击「粘贴图片」按钮添加截图"

    try:
        # 导入可调整大小的输入面板
        from resizable_input_panel import show_resizable_input_dialog, Button, HAS_APPKIT

        if not HAS_APPKIT:
            # 如果没有 AppKit，使用原来的 osascript 方式
            return _show_input_dialog_osascript(date_full, has_image)

        # 使用原生 AppKit 面板
        result = show_resizable_input_dialog(
            title="📝 快速笔记",
            prompt=prompt,
            width=dialog_width,
            height=dialog_height,
            clipboard_image_available=has_image
        )

        if result is None:
            show_notification("QuickNote ✏️", "⏰ 已取消")
            return

        content = result.content
        button = result.button
        attachments = []

        # 处理粘贴图片按钮
        if button == Button.PASTE_IMAGE.value:
            clip_link = save_clipboard_image()
            if clip_link:
                attachments.append(clip_link)
                show_notification("QuickNote ✏️", "🖼️ 图片已粘贴到附件!")
            else:
                show_notification("QuickNote ✏️", "❌ 剪贴板中没有图片")

            # 继续添加图片循环（使用 osascript 简单对话框）
            while True:
                script = f'''
                display dialog "📝 快速笔记 - 图片已插入" & return & return & "📅 日期: {date_full}" & return & "已添加 {len(attachments)} 个图片" buttons {{"取消", "继续添加图片", "保存"}} default button 3 giving up after 300 with title "QuickNote ✏️"
                return button returned of result
                '''
                result2 = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=300)
                if result2.returncode != 0:
                    break
                btn2 = result2.stdout.strip()
                if btn2 == "继续添加图片":
                    clip_link2 = save_clipboard_image()
                    if clip_link2:
                        attachments.append(clip_link2)
                        show_notification("QuickNote ✏️", "🖼️ 图片已追加!")
                    else:
                        show_notification("QuickNote ✏️", "❌ 剪贴板中没有图片")
                else:
                    break

        # 保存笔记
        full_content = content
        if attachments:
            if full_content:
                full_content += "\n\n" + "\n".join(attachments)
            else:
                full_content = "\n".join(attachments)

        if full_content.strip():
            success, msg = save_to_daily(full_content)
            if success:
                count = len(attachments)
                if count > 0:
                    show_notification("QuickNote ✏️", f"已保存! 含 {count} 个附件 ✓")
                else:
                    show_notification("QuickNote ✏️", "已保存到日记 ✓")
            else:
                show_notification("QuickNote ✏️", f"❌ {msg}")
        else:
            show_notification("QuickNote ✏️", "内容为空，已取消保存")

    except ImportError:
        # 导入失败时使用 osascript 回退
        return _show_input_dialog_osascript(date_full, has_image)
    except Exception as e:
        show_notification("QuickNote ✏️", f"❌ 错误: {e}")


def _show_input_dialog_osascript(date_full: str, has_image: bool):
    """原始的 osascript 输入对话框（回退方案）"""
    has_image_str = "✅ 有" if has_image else "❌ 无"

    script = f'''
    set theResult to (display dialog "📝 快速笔记" & return & return & "📅 日期: {date_full}" & return & "剪贴板图片: {has_image_str}" & return & return & "💡 提示: 先点击「粘贴图片」按钮，再写文字" default answer "" buttons {{"取消", "粘贴图片", "保存"}} default button 3 giving up after 300 with title "QuickNote ✏️")
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

                # 粘贴图片按钮
                if button == "粘贴图片":
                    # 重新检测剪贴板图片
                    clip_link = save_clipboard_image()
                    if clip_link:
                        attachments.append(clip_link)
                        show_notification("QuickNote ✏️", "🖼️ 图片已粘贴到附件!")
                    else:
                        show_notification("QuickNote ✏️", "❌ 剪贴板中没有图片")

                    # 再次弹出输入框，让用户继续输入
                    script2 = '''
                    set theResult to (display dialog "📝 快速笔记 - 图片已插入" & return & return & "📅 日期: %s" & return & "图片已添加到附件" buttons {"取消", "继续添加图片", "保存"} default button 3 giving up after 300 with title "QuickNote ✏️")
                    return text returned of theResult & "|" & button returned of theResult
                    ''' % date_full
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
                                        attachments.append(clip_link2)
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
                    count = len(attachments)
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
    dialog_width = config.get("dialog_width", 500)
    dialog_height = config.get("dialog_height", 300)

    script = f'''
    display dialog "⚙️ QuickNote 设置" & return & return & "保存路径:" default answer "{save_path}" buttons {{"取消", "设置快捷键", "对话框大小", "保存"}} default button 4 giving up after 300 with title "QuickNote ✏️"
    return button returned of result
    '''

    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and result.stdout.strip():
            button = result.stdout.strip()

            if button == "设置快捷键":
                show_shortcut_dialog()
                # show_shortcut_dialog 保存后重新加载 config
                config = load_config()
                save_path = config.get("save_path", str(LOCAL_QUICKNOTES))
                # 设置完快捷键后，继续修改保存路径
                script2 = f'''
                display dialog "保存路径:" default answer "{save_path}" buttons {{"取消", "保存"}} default button 2 giving up after 300 with title "QuickNote ✏️"
                return text returned of result & "|" & button returned of result
                '''
                result2 = subprocess.run(['osascript', '-e', script2], capture_output=True, text=True, timeout=300)
                if result2.returncode == 0 and result2.stdout.strip():
                    parts2 = result2.stdout.strip().split('|')
                    if len(parts2) >= 2:
                        new_path = parts2[0].strip()
                        btn = parts2[1].strip()
                        if btn == "保存" and new_path:
                            config["save_path"] = new_path
                            save_config(config)
                            show_notification("QuickNote ✨", "设置已保存 ✓")
                return

            if button == "对话框大小":
                # 弹出对话框让用户输入宽高
                script2 = f'''
                display dialog "📐 对话框大小" & return & return & "宽度:" default answer "{dialog_width}" buttons {{"取消", "保存"}} default button 2 giving up after 300 with title "QuickNote ✏️"
                return text returned of result & "|" & button returned of result
                '''
                result2 = subprocess.run(['osascript', '-e', script2], capture_output=True, text=True, timeout=300)
                if result2.returncode == 0 and result2.stdout.strip():
                    parts2 = result2.stdout.strip().split('|')
                    if len(parts2) >= 2:
                        new_width_str = parts2[0].strip()
                        btn = parts2[1].strip()
                        if btn == "保存" and new_width_str.isdigit():
                            dialog_width = int(new_width_str)

                            # 弹出对话框让用户输入高度
                            script3 = f'''
                            display dialog "📐 对话框高度" & return & return & "高度:" default answer "{dialog_height}" buttons {{"取消", "保存"}} default button 2 giving up after 300 with title "QuickNote ✏️"
                            return text returned of result & "|" & button returned of result
                            '''
                            result3 = subprocess.run(['osascript', '-e', script3], capture_output=True, text=True, timeout=300)
                            if result3.returncode == 0 and result3.stdout.strip():
                                parts3 = result3.stdout.strip().split('|')
                                if len(parts3) >= 2:
                                    new_height_str = parts3[0].strip()
                                    btn3 = parts3[1].strip()
                                    if btn3 == "保存" and new_height_str.isdigit():
                                        dialog_height = int(new_height_str)
                                        config["dialog_width"] = dialog_width
                                        config["dialog_height"] = dialog_height
                                        save_config(config)
                                        show_notification("QuickNote ✨", f"对话框大小已设为 {dialog_width}x{dialog_height}")

                # 继续修改保存路径
                config = load_config()
                save_path = config.get("save_path", str(LOCAL_QUICKNOTES))
                script4 = f'''
                display dialog "保存路径:" default answer "{save_path}" buttons {{"取消", "保存"}} default button 2 giving up after 300 with title "QuickNote ✏️"
                return text returned of result & "|" & button returned of result
                '''
                result4 = subprocess.run(['osascript', '-e', script4], capture_output=True, text=True, timeout=300)
                if result4.returncode == 0 and result4.stdout.strip():
                    parts4 = result4.stdout.strip().split('|')
                    if len(parts4) >= 2:
                        new_path = parts4[0].strip()
                        btn4 = parts4[1].strip()
                        if btn4 == "保存" and new_path:
                            config["save_path"] = new_path
                            save_config(config)
                            show_notification("QuickNote ✨", "设置已保存 ✓")
                return

            if button == "保存":
                script2 = f'''
                display dialog "保存路径:" default answer "{save_path}" buttons {{"取消", "保存"}} default button 2 giving up after 300 with title "QuickNote ✏️"
                return text returned of result & "|" & button returned of result
                '''
                result2 = subprocess.run(['osascript', '-e', script2], capture_output=True, text=True, timeout=300)
                if result2.returncode == 0 and result2.stdout.strip():
                    parts2 = result2.stdout.strip().split('|')
                    if len(parts2) >= 2:
                        new_path = parts2[0].strip()
                        btn = parts2[1].strip()
                        if btn == "保存" and new_path:
                            config["save_path"] = new_path
                            save_config(config)
                            show_notification("QuickNote ✨", "设置已保存 ✓")
    except:
        pass


def show_shortcut_dialog():
    """显示快捷键设置对话框"""
    config = load_config()
    current_shortcut = config.get("global_shortcut", "")
    display_shortcut = current_shortcut if current_shortcut else "未设置"

    script = f'''
    display dialog "⚙️ 全局快捷键设置" & return & return & "当前: {display_shortcut}" & return & return & "输入格式: ⌘⇧N (Cmd+Shift+N)" & return & "需要系统辅助功能权限才能生效" buttons {{"取消", "禁用", "保存"}} default button 3 giving up after 300 with title "QuickNote ✏️"
    return text returned of result & "|" & button returned of result
    '''

    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split('|')
            if len(parts) >= 2:
                new_shortcut = parts[0].strip()
                button = parts[1].strip()

                if button == "禁用":
                    config["global_shortcut"] = ""
                    hotkey_manager.unregister()
                    save_config(config)
                    show_notification("QuickNote ✏️", "已禁用")
                    return

                if new_shortcut and button == "保存":
                    test_key, test_mods = hotkey_manager._parseShortcut(new_shortcut)
                    if test_key is not None:
                        config["global_shortcut"] = new_shortcut
                        save_config(config)
                        # 重新注册
                        hotkey_manager.unregister()
                        success = hotkey_manager.register(new_shortcut, hotkey_callback_ref)
                        show_notification("QuickNote ✏️", f"快捷键已保存!")
                    else:
                        show_notification("QuickNote ✏️", "格式错误，请用 ⌘⇧N 格式")
    except Exception as e:
        show_notification("QuickNote ✏️", f"设置失败")

# ==================== 菜单栏应用 ====================
class QuickNoteApp(rumps.App):
    def __init__(self):
        super().__init__("📝")
        self.menu = [
            rumps.MenuItem("快速记录 ✏️", callback=self.on_quick_note),
            rumps.MenuItem("🌐 全局快捷键", callback=self.on_global_shortcut),
            None,
            rumps.MenuItem("设置 ⚙️", callback=self.on_settings),
            rumps.MenuItem("打开 QuickNotes", callback=self.open_folder),
            None,
            rumps.MenuItem("退出", callback=self.on_quit)
        ]
        # 启动时注册全局快捷键
        setup_global_hotkey()

    @rumps.clicked("快速记录 ✏️")
    def on_quick_note(self, sender):
        show_input_dialog()

    @rumps.clicked("🌐 全局快捷键")
    def on_global_shortcut(self, sender):
        show_shortcut_dialog()

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
