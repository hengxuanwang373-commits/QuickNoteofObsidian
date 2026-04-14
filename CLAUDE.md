# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QuickNote is a macOS menu bar application for quick note-taking with clipboard image support. Notes are saved in daily Markdown files (YYMMDD.md format) to an Obsidian-compatible folder structure.

## Architecture Principles

**核心目标**：通过领域驱动设计（DDD）实现高内聚、低耦合的架构，隔离 GUI 变化性，确保数据流转安全，支持未来扩展图片处理、云端同步等新模块时无需破坏现有核心代码。

### 三大架构原则

1. **控制模块间依赖方向** - 上层依赖下层，下层绝不反向引用上层
2. **实施控制反转（IoC）** - 主程序调用抽象存储接口，而非具体实现
3. **单向数据流** - 用户操作封装为 Event，通过中央分发器传递

## Three-Tier Architecture（三层分离架构）

### 表现层（Presentation Layer）
**职责**：菜单栏框架（rumps）的图标状态、下拉菜单构建、系统对话框唤起
- 监听事件总线，响应用户交互
- 绝不直接操作文件或剪贴板

### 业务逻辑层（Business Logic Layer）
**职责**：协调核心流转
- 接收"快速记录"指令后：指挥剪贴板读取、生成时间戳路径、格式化文本
- 通过事件总线与表现层和数据层通信

### 数据访问层（Data Access Layer）
**职责**：封装所有操作系统底层交互
- SSD 写入文件、创建目录树、读取配置文件
- 提供抽象存储接口供业务层调用

**层间规则**：严格单向调用 —— 上层调用下层，下层绝不反向引用上层

## Event Bus Mechanism（事件总线机制）

采用轻量级发布订阅模式（Publish-Subscribe Pattern），替代直接函数回调，避免内存泄漏和循环引用。

### 事件类型
```python
# 事件基类
@dataclass(frozen=True)
class Event:
    timestamp: datetime

@dataclass(frozen=True)
class QuickNoteTriggered(Event):
    """触发快速记录"""
    content: str
    attachments: list[str]

@dataclass(frozen=True)
class ConfigChanged(Event):
    """配置变更"""
    key: str
    value: Any

@dataclass(frozen=True)
class NoteSaved(Event):
    """笔记保存成功"""
    file_path: Path
    attachment_count: int
```

### 发布订阅示例
```python
# GlobalHotkeyManager 广播事件（不直接调用函数）
event_bus.publish(QuickNoteTriggered(content="", attachments=[]))

# 表现层监听事件
@event_bus.subscribe(QuickNoteTriggered)
def on_quick_note(event: QuickNoteTriggered):
    show_input_dialog()  # 只负责 UI 响应
```

**优势**：未来新增 10 个触发方式，无需修改核心处理逻辑

## Thread Isolation Strategy（线程隔离策略）

### 线程规则
- **主线程**：所有 AppKit/GUI 操作
- **后台线程池**：`concurrent.futures.ThreadPoolExecutor` 执行磁盘 I/O

### 实现示例
```python
# 主线程：获取内容和图像对象（深拷贝）
content, clipboard_data = main_threadCapture()

# 立即派发给后台线程池
executor.submit(save_to_disk, deep_copy(content), deep_copy(clipboard_data))
```

**禁止**：在后台线程中调用任何 AppKit API

## Type Hints and Data Classes（强类型提示与数据类）

### 严格要求
- 所有函数签名必须标注类型
- 所有类属性必须标注类型
- 使用 `mypy` 静态类型检查

### 数据类定义
```python
@dataclass(frozen=True)
class NoteEntry:
    timestamp: datetime
    content: str
    attachments: tuple[str, ...]  # 不可变元组

@dataclass
class AppConfig:
    save_path: Path
    show_notifications: bool
    global_shortcut: str
```

## Dependency Injection Container（依赖注入容器）

### 核心原则
- 禁止在类内部直接实例化其他对象
- 在程序入口处实例化存储实现，注入业务层

### 接口定义
```python
class StorageBackend(Protocol):
    def save_note(self, entry: NoteEntry) -> Path: ...
    def load_config(self) -> AppConfig: ...
    def save_config(self, config: AppConfig) -> None: ...

# 生产环境：真实 SSD 存储
class SSDStorage:
    def save_note(self, entry: NoteEntry) -> Path: ...

# 测试环境：内存虚拟存储
class InMemoryStorage:
    def save_note(self, entry: NoteEntry) -> Path: ...
```

### 注入示例
```python
# 程序入口
storage: StorageBackend = InMemoryStorage() if testing else SSDStorage()
service = NoteService(storage=storage)
```

**测试优势**：毫秒级完成数百次测试，无磁盘垃圾文件

## Module Boundaries（模块边界）

当前模块划分，修改时严格遵守单一模块原则：

| 模块 | 职责 | 层级 |
|------|------|------|
| `ClipboardService` | 剪贴板读取 | 数据访问层 |
| `AttachmentService` | 附件复制管理 | 数据访问层 |
| `StorageBackend` | 文件 I/O 抽象 | 数据访问层 |
| `NoteService` | 笔记格式化与协调 | 业务逻辑层 |
| `EventBus` | 事件发布订阅 | 业务逻辑层 |
| `HotkeyManager` | 全局快捷键 | 业务逻辑层 |
| `MenuBarPresenter` | 菜单栏 UI | 表现层 |
| `DialogPresenter` | 对话框 UI | 表现层 |

## Development Workflow（开发流程）

### 开发顺序
1. **先定义接口/事件** - 明确数据流转
2. **实现数据访问层** - 底层先行
3. **实现业务逻辑层** - 依赖已定义的接口
4. **实现表现层** - 最后处理 UI

### 测试流程（修改后必做）
**每次修改功能后，必须编写测试脚本验证修改正确性，才能构建。**

```bash
# 1. 编写测试脚本
python3 test_clipboard.py

# 2. 测试通过后构建
python3 -m PyInstaller --windowed --onedir --name QuickNoteMenuBar quicknote_menubar.py
```

### 重构检测清单
- [ ] 新增功能是否需要新事件类型？
- [ ] 是否在正确的层级添加代码？
- [ ] 是否有直接跨层调用？
- [ ] 是否所有类型都已标注？
- [ ] 是否有线程违规（后台线程调用 AppKit）？

## Common Commands

### Running the App
```bash
/opt/homebrew/bin/python3 quicknote_menubar.py
```

### Building the App
```bash
/opt/homebrew/bin/python3 -m PyInstaller --windowed --onedir --name QuickNoteMenuBar quicknote_menubar.py
# Output: dist/QuickNoteMenuBar.app/
```

### Type Checking
```bash
python3 -m mypy quicknote_menubar.py --strict
```

### Configuration
- Config file: `~/Library/Preferences/com.quicknote.menubar.json`
- Default save path: `~/Documents/QuickNotes`
- Attachments: `{save_path}/attachments/`

## Key Implementation Notes

### Clipboard Access
`ClipboardService` 必须直接在主进程调用 AppKit，**禁止**使用 subprocess 读取剪贴板（subprocess 无法访问 GUI 剪贴板）。

### Save Path Logic
`get_save_path()` 自动将 "Documents" 路径重定向到 `06📓QuickNotes` 子文件夹。使用 `os.path.expanduser()` 展开 `~`。

### Global Hotkeys
`HotkeyManager` 使用 `NSEvent.addGlobalMonitorForEventsMatchingMask_handler_()`，修饰键检测使用硬编码 bitmask（避免 NSEvent 常量跨版本兼容性问题）。
