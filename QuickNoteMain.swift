-- QuickNote.app (AppleScript Application)
-- 后台运行，随时通过快捷键呼出

-- 属性
property OBSIDIAN_DIARY_PATH : ((path to documents folder as text) & "iCloud~md~obsidian/Documents/01📘Diary")

-- 菜单栏图标状态
global isMenuBarActive
set isMenuBarActive to true

-- 获取今天的日记路径
on getDiaryPath()
    set todayDate to current date
    set dateString to do shell script "date +%y-%m-%d"
    set monthFolder to "26_" & do shell script "date +%m"

    set diaryFolder to (POSIX file (OBSIDIAN_DIARY_PATH & ":" & monthFolder)) as alias

    set diaryFile to (diaryFolder as text) & dateString & ".md"

    return diaryFile
end getDiaryPath

-- 获取中文星期
on getChineseWeekday()
    set todayDate to current date
    set weekdayNum to weekday of todayDate
    set weekdayChinese to "日"
    if weekdayNum is 2 then set weekdayChinese to "一"
    if weekdayNum is 3 then set weekdayChinese to "二"
    if weekdayNum is 4 then set weekdayChinese to "三"
    if weekdayNum is 5 then set weekdayChinese to "四"
    if weekdayNum is 6 then set weekdayChinese to "五"
    if weekdayNum is 7 then set weekdayChinese to "六"
    return weekdayChinese
end getChineseWeekday

-- 显示快速笔记输入框
on showQuickNote()
    -- 获取当前时间
    set dateString to do shell script "date +%Y-%m-%d"
    set timeString to do shell script "date +%H:%M"
    set weekdayChinese to my getChineseWeekday()

    -- 读取现有日记
    set diaryFile to my getDiaryPath()

    try
        set existingContent to read file diaryFile as «class utf8»
    on error
        set existingContent to "# 日记 " & dateString & return & return
    end try

    -- 显示输入框
    set theInput to text returned of (display dialog "📝 快速笔记" & return & return & "保存到: " & dateString & return & return & "快捷键: Cmd+Enter 保存 | Esc 取消" default answer "" buttons {"取消", "保存"} default button 2 giving up after 300 with title "QuickNote ✏️")

    if theInput is not "" then
        -- 构建新条目
        set newEntry to return & "## 📝 " & dateString & " " & timeString & " (" & weekdayChinese & ")" & return & return & theInput & return

        -- 追加内容
        set newContent to existingContent & newEntry

        -- 保存文件
        try
            set diaryFilePOSIX to POSIX path of diaryFile
            do shell script "mkdir -p $(dirname '" & diaryFilePOSIX & "')"
            set fp to open for access file diaryFilePOSIX with write permission
            write newContent to fp as «class utf8»
            close access fp

            -- 显示通知
            display notification "已保存到日记 ✓" with title "QuickNote"

        on error errMsg
            display dialog "保存失败: " & errMsg buttons {"OK"} default button "OK"
        end try
    end if
end showQuickNote

-- 创建菜单栏应用
on run
    -- 确保日记目录存在
    set diaryPath to POSIX file OBSIDIAN_DIARY_PATH
    tell application "System Events"
        if not (exists disk item (OBSIDIAN_DIARY_PATH as text)) then
            do shell script "mkdir -p " & quoted form of OBSIDIAN_DIARY_PATH
        end if
    end tell

    -- 显示启动提示
    display notification "QuickNote 已启动" with title "QuickNote ✏️"

    -- 进入空闲状态
    repeat
        delay 1
    end repeat
end run

-- 处理菜单栏点击
on click_menu(theObject)
    if title of theObject is "新建笔记" then
        my showQuickNote()
    else if title of theObject is "Quit" then
        quit
    end if
end click_menu
