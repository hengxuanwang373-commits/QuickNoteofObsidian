# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QuickNote is a macOS menu bar application for quick note-taking with clipboard image support. Notes are saved in daily Markdown files (YYMMDD.md format) to an Obsidian-compatible folder structure.

## Common Commands

### Running the App
```bash
# Run directly from source (for development/testing)
/opt/homebrew/bin/python3 quicknote_menubar.py
```

### Building the App
```bash
# Build with PyInstaller (onedir mode recommended)
/opt/homebrew/bin/python3 -m PyInstaller --windowed --onedir --name QuickNoteMenuBar quicknote_menubar.py

# Build output location
dist/QuickNoteMenuBar.app/
```

### Configuration
- Config file: `~/Library/Preferences/com.quicknote.menubar.json`
- Default save path: `~/Documents/QuickNotes`
- Attachments saved to: `{save_path}/attachments/`

## Architecture

### Main Entry Point
- `quicknote_menubar.py` - Primary application using rumps library for macOS menu bar

### Build System
- `QuickNoteMenuBar.spec` - PyInstaller spec file (for py2app-style builds)
- `setup.py` - Wrapper for spec-based builds

### Supporting Files
- `quicknote_trigger.py` - Simple version (deprecated, no image support)
- `QuickNote.scpt`, `QuickNote.sh` - Legacy AppleScript/bash versions
- `QuickNote.app/` - Simple launcher wrapper

### Key Dependencies
- **rumps** - macOS menu bar framework
- **PyObjC/AppKit** - Native macOS APIs for clipboard and global hotkeys
- **osascript** - For dialogs and notifications

### Data Flow
1. User triggers "快速记录" from menu bar
2. `show_input_dialog()` displays osascript dialog
3. `save_clipboard_image()` reads clipboard via AppKit (must run in main process, not subprocess)
4. `save_to_daily()` appends entry to daily file: `26_{MM}/{yy}{mm}{dd}.md`
5. `copy_attachment()` saves images to `{save_path}/attachments/`

## Development Workflow

### Module Isolation
**每次只修改一个模块**。每个功能应该是独立模块，修改时不会影响其他模块。

当前模块划分：
- `save_clipboard_image()` - 剪贴板读取（独立函数）
- `copy_attachment()` - 附件复制到 attachments 目录
- `save_to_daily()` - 日记文件读写
- `show_input_dialog()` - 输入对话框逻辑
- `show_settings_dialog()` - 设置对话框
- `GlobalHotkeyManager` - 全局快捷键管理（独立类）

### 测试流程（修改后必做）
**每次修改功能后，必须编写测试脚本验证修改正确性，才能构建。**

测试脚本命名规范：`test_{功能模块}.py`

测试流程：
1. 编写测试脚本，模拟输入
2. 运行测试脚本验证输出
3. 确认功能正确后，再执行构建

示例测试流程：
```bash
# 1. 编写测试脚本 test_clipboard.py
# 2. 运行测试
python3 test_clipboard.py

# 3. 测试通过后构建
python3 -m PyInstaller --windowed --onedir --name QuickNoteMenuBar quicknote_menubar.py
```

## Important Implementation Notes

### Clipboard Access
`save_clipboard_image()` must call AppKit directly in the main process. **Do not** use `subprocess.run(['python3', '-c', ...])` for clipboard access - subprocess cannot access the GUI clipboard. Always import and call AppKit directly within the same Python process.

### Save Path Logic
The `get_save_path()` function auto-redirects "Documents" folder paths to `06📓QuickNotes` subfolder. Use `os.path.expanduser()` to expand `~` in user-specified paths.

### Global Hotkeys
`GlobalHotkeyManager` uses `NSEvent.addGlobalMonitorForEventsMatchingMask_handler_()` with hardcoded bitmask values for modifier keys (not NSEvent constants, which have compatibility issues across macOS versions).
