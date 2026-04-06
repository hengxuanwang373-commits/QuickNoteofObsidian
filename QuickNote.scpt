-- QuickNote.applescript
-- 浮动备忘录 for Obsidian
-- 使用方法: 保存为 .scpt 或 .app，通过快捷键触发

property OBSIDIAN_DIARY_PATH : ((path to documents folder as text) & "iCloud~md~obsidian/Documents/01📘Diary")

on run
    -- 获取今天的日期
    set todayDate to current date
    set dateString to do shell script "date +%Y-%m-%d"
    set timeString to do shell script "date +%H:%M"
    set weekdayChinese to do shell script "echo '一二三四五六日' | cut -c" & ((weekday of todayDate) as integer) & "-1"

    -- 日记文件路径
    set monthFolder to "26_" & do shell script "date +%m"
    set diaryFile to (POSIX file (OBSIDIAN_DIARY_PATH & ":" & monthFolder & ":" & do shell script "date +%y-%m-%d" & ".md")) as alias

    -- 读取现有内容
    try
        set existingContent to read diaryFile as «class utf8»
    on error
        set existingContent to ""
    end try

    -- 显示输入对话框
    set theInput to text returned of (display dialog "📝 快速笔记" & return & return & "输入内容将保存到今日日记" default answer "" buttons {"取消", "保存"} default button 2 giving up after 300)

    if theInput is not "" then
        -- 构建新条目
        set newEntry to return & "## 📝 " & dateString & " " & timeString & " (" & weekdayChinese & ")" & return & return & theInput & return

        -- 追加内容
        if existingContent is not "" then
            set newContent to existingContent & newEntry
        else
            set newContent to "# 日记" & return & return & newEntry
        end if

        -- 保存文件
        try
            set diaryFile POSIX to POSIX path of diaryFile
            do shell script "echo '" & (do shell script "echo '" & newContent & "' | sed 's/'/''/g") & "' >> " & quoted form of diaryFile POSIX
            display notification "已保存到日记 ✓" with title "QuickNote"
        on error errMsg
            display dialog "保存失败: " & errMsg buttons {"OK"} default button "OK"
        end try
    end if
end run
