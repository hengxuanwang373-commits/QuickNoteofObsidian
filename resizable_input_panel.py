#!/usr/bin/env python3
"""
ResizableInputPanel - 可调整大小的文本输入面板
表现层组件，使用原生 AppKit 实现
"""
from dataclasses import dataclass
from typing import Protocol, Callable
from enum import Enum

try:
    import AppKit
    from AppKit import (
        NSPanel, NSTextView, NSScrollView, NSWindow,
        NSButton, NSTextField, NSFont, NSColor,
        NSHorizontalInspectionWindowLevel, NSPoint, NSSize,
        NSRect, NSBackingStoreBuffered, NSTitledWindowMask,
        NSClosableWindowMask, NSResizableWindowMask,
        NSMiniaturizableWindowMask, NSTextAlignment
    )
    from Foundation import NSSet, NSNotification, NSRunLoop
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False


class Button(Enum):
    CANCEL = "取消"
    PASTE_IMAGE = "粘贴图片"
    SAVE = "保存"
    ADD_ATTACHMENT = "添加附件"
    CONTINUE_ADD_IMAGE = "继续添加图片"


@dataclass(frozen=True)
class InputResult:
    """输入结果数据类"""
    content: str
    button: str
    attachments: tuple[str, ...]


class ResizableInputPanel:
    """
    可调整大小的文本输入面板

    使用原生 AppKit NSTextView 实现可滚动、可调整大小的文本输入区域。
    遵循表现层单一职责原则，只负责 UI 渲染和用户输入收集。
    """

    def __init__(
        self,
        title: str,
        prompt: str,
        width: int = 500,
        height: int = 300,
        default_text: str = "",
        buttons: tuple[str, ...] = None,
        clipboard_image_available: bool = False
    ):
        """
        初始化输入面板

        Args:
            title: 窗口标题
            prompt: 提示文本
            width: 面板宽度
            height: 面板高度
            default_text: 默认文本
            buttons: 自定义按钮列表
            clipboard_image_available: 剪贴板是否有图片
        """
        if not HAS_APPKIT:
            raise RuntimeError("AppKit is not available")

        self._title = title
        self._prompt = prompt
        self._width = max(400, width)
        self._height = max(200, height)
        self._default_text = default_text
        self._buttons = buttons or (Button.CANCEL.value, Button.PASTE_IMAGE.value, Button.SAVE.value)
        self._clipboard_image_available = clipboard_image_available

        self._result: InputResult | None = None
        self._panel: NSPanel | None = None
        self._text_view: NSTextView | None = None
        self._button_map: dict[str, NSButton] = {}

    def run(self) -> InputResult | None:
        """
        显示面板并等待用户输入

        Returns:
            InputResult: 用户输入结果，包含内容、按钮、附件列表
            None: 用户取消或超时
        """
        self._setup_panel()
        self._setup_content()
        self._setup_buttons()
        self._center_panel()
        self._panel.makeKeyAndOrderFront_(None)
        NSRunLoop.currentRunLoop().run()
        return self._result

    def _setup_panel(self):
        """创建面板"""
        content_rect = NSRect(0, 0, self._width, self._height)
        self._panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            content_rect,
            NSTitledWindowMask | NSClosableWindowMask | NSResizableWindowMask | NSMiniaturizableWindowMask,
            NSBackingStoreBuffered,
            False
        )
        self._panel.setTitle_(self._title)
        self._panel.setBecomesKeyOnlyIfNeeded_(False)
        self._panel.setLevel_(NSHorizontalInspectionWindowLevel)
        self._panel.setIsMovableByWindowBackground_(True)
        self._panel.setHidesOnDeactivate_(False)

    def _setup_content(self):
        """设置面板内容区域"""
        content_view = self._panel.contentView()

        # 标题标签
        title_label = NSTextField.alloc().initWithFrame_(NSRect(15, self._height - 50, self._width - 30, 30))
        title_label.setStringValue_(self._prompt)
        title_label.setEditable_(False)
        title_label.setBordered_(False)
        title_label.setBackgroundColor_(NSColor.clearColor())
        title_label.setFont_(NSFont.systemFontOfSize_(13))
        content_view.addSubview_(title_label)

        # 文本输入区域 (NSScrollView + NSTextView)
        text_view_height = self._height - 150
        scroll_view = NSScrollView.alloc().initWithFrame_(
            NSRect(15, 60, self._width - 30, max(100, text_view_height))
        )
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutohidesScrollers_(True)
        scroll_view.setBorderType_(1)  # Bezel border

        self._text_view = NSTextView.alloc().initWithFrame_(
            NSRect(0, 0, self._width - 60, max(80, text_view_height))
        )
        self._text_view.setMinSize_(NSSize(100, 80))
        self._text_view.setMaxSize_(NSSize(float('inf'), float('inf')))
        self._text_view.setVerticallyResizable_(True)
        self._text_view.setHorizontallyResizable_(False)
        self._text_view.setRichText_(False)
        self._text_view.setFont_(NSFont.systemFontOfSize_(14))
        self._text_view.setTextColor_(NSColor.textColor())
        self._text_view.setBackgroundColor_(NSColor.textBackgroundColor())
        self._text_view.setString_(self._default_text)
        self._text_view.setAllowsUndo_(True)

        scroll_view.setDocumentView_(self._text_view)
        content_view.addSubview_(scroll_view)

    def _setup_buttons(self):
        """设置按钮区域"""
        content_view = self._panel.contentView()
        button_y = 20
        button_width = 100
        button_height = 28

        # 根据按钮数量计算布局
        num_buttons = len(self._buttons)
        total_width = num_buttons * button_width + (num_buttons - 1) * 10
        start_x = (self._width - total_width) / 2

        for i, button_text in enumerate(self._buttons):
            x = start_x + i * (button_width + 10)
            button = NSButton.alloc().initWithFrame_(
                NSRect(x, button_y, button_width, button_height)
            )
            button.setTitle_(button_text)
            button.setBezelStyle_(2)  # Rounded
            button.setTarget_(self)
            button.setAction_(self._button_action_)

            # 标记按钮类型
            button.cell().setTag_(i)
            self._button_map[button_text] = button

            content_view.addSubview_(button)

    def _button_action_(self, sender: NSButton):
        """按钮点击处理"""
        button_title = sender.title()
        self._handle_button_click(button_title)

    def _handle_button_click(self, button_title: str):
        """处理按钮点击"""
        content = self._text_view.string() if self._text_view else ""

        if button_title == Button.CANCEL.value:
            self._result = InputResult(content=content, button=button_title, attachments=())
        elif button_title == Button.PASTE_IMAGE.value:
            # 粘贴图片模式，返回特殊标记让调用方处理
            self._result = InputResult(content=content, button=button_title, attachments=())
        elif button_title == Button.SAVE.value:
            self._result = InputResult(content=content, button=button_title, attachments=())
        elif button_title == Button.CONTINUE_ADD_IMAGE.value:
            self._result = InputResult(content=content, button=button_title, attachments=())

        self._close()

    def _center_panel(self):
        """将面板居中显示"""
        if self._panel:
            screen_frame = AppKit.NSScreen.mainScreen().frame()
            panel_frame = self._panel.frame()
            x = (screen_frame.size.width - panel_frame.size.width) / 2
            y = (screen_frame.size.height - panel_frame.size.height) / 2
            self._panel.setFrameOrigin_(NSPoint(x, y))

    def _close(self):
        """关闭面板"""
        if self._panel:
            self._panel.close()
            self._panel = None

    @property
    def content(self) -> str:
        """获取当前文本内容"""
        return self._text_view.string() if self._text_view else ""

    @property
    def panel(self) -> NSPanel | None:
        """获取面板实例（用于高级定制）"""
        return self._panel


def show_resizable_input_dialog(
    title: str,
    prompt: str,
    width: int = 500,
    height: int = 300,
    default_text: str = "",
    clipboard_image_available: bool = False
) -> InputResult | None:
    """
    显示可调整大小的输入对话框（便捷函数）

    Args:
        title: 窗口标题
        prompt: 提示文本
        width: 面板宽度
        height: 面板高度
        default_text: 默认文本
        clipboard_image_available: 剪贴板是否有图片

    Returns:
        InputResult: 用户输入结果
        None: 用户取消
    """
    if not HAS_APPKIT:
        raise RuntimeError("AppKit is not available. Cannot display GUI dialog.")

    panel = ResizableInputPanel(
        title=title,
        prompt=prompt,
        width=width,
        height=height,
        default_text=default_text,
        clipboard_image_available=clipboard_image_available
    )
    return panel.run()
