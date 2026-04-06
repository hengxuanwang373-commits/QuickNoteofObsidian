#!/bin/bash
# QuickNote.sh - 快速笔记
# 保存到 Obsidian 日记
# 使用: ./QuickNote.sh

OBSIDIAN_DIARY="/Users/jiamingli_1/Library/Mobile Documents/iCloud~md~obsidian/Documents/01📘Diary"
TODAY=$(date +%y-%m-%d)
MONTH_FOLDER="26_$(date +%m)"
TIME=$(date +%H:%M)

# 获取星期几 (中文)
WEEKDAY_CN=$(echo "一二三四五六日" | cut -c$(date +%u)-$(date +%u))

# 目标文件
if [ -d "$OBSIDIAN_DIARY/$MONTH_FOLDER" ]; then
    DIARY_FILE="$OBSIDIAN_DIARY/$MONTH_FOLDER/$TODAY.md"
else
    DIARY_FILE="$OBSIDIAN_DIARY/$TODAY.md"
fi

# 使用 macOS 的 osascript 显示输入框
INPUT=$(osascript -e 'text returned of (display dialog "📝 快速笔记" & return & return & "输入内容将追加到今日日记" default answer "" buttons {"取消", "保存"} default button 2 giving up after 300)')

if [ -n "$INPUT" ] && [ "$INPUT" != "" ]; then
    FULL_DATE=$(date +%Y-%m-%d)

    # 构建 Markdown 条目
    ENTRY="\n## 📝 $FULL_DATE $TIME ($WEEKDAY_CN)\n\n$INPUT\n"

    # 如果文件不存在，创建标题
    if [ ! -f "$DIARY_FILE" ]; then
        echo "# 日记" > "$DIARY_FILE"
    fi

    # 追加内容
    echo -e "$ENTRY" >> "$DIARY_FILE"

    # 通知
    osascript -e 'display notification "已保存到日记 ✓" with title "QuickNote"'
fi
