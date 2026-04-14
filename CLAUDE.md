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

## Important Implementation Notes

### Clipboard Access
`save_clipboard_image()` must call AppKit directly in the main process. **Do not** use `subprocess.run(['python3', '-c', ...])` for clipboard access - subprocess cannot access the GUI clipboard. Always import and call AppKit directly within the same Python process.

### Save Path Logic
The `get_save_path()` function auto-redirects "Documents" folder paths to `06📓QuickNotes` subfolder. Use `os.path.expanduser()` to expand `~` in user-specified paths.

### Global Hotkeys
`GlobalHotkeyManager` uses `NSEvent.addGlobalMonitorForEventsMatchingMask_handler_()` with hardcoded bitmask values for modifier keys (not NSEvent constants, which have compatibility issues across macOS versions).
