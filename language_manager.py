#
# 檔案名稱: language_manager.py
#
import json
import os

SETTINGS_FILE = "settings.json"

# 所有 UI 文字都定義在這裡
LANGUAGES = {
    "zh_TW": {
        "window_title": "中文繁簡轉換工具",
        "tab_file_conversion": "TXT 檔案轉換",
        "tab_filename_conversion": "檔名轉換",
        "tab_clipboard_conversion": "剪貼簿轉換",

        # --- 通用按鈕 ---
        "import_files": "匯入檔案",
        "import_folder": "匯入資料夾",
        "clear_list": "清空列表",
        "remove_unchecked": "移除未勾選",
        "uncheck_selected_button": "取消選取",
        "undo": "復原上一步",
        "custom_conversions_manage": "詞彙轉換管理",
        "pause_button": "暫停",
        "resume_button": "繼續",
        "cancel_button": "取消",
        "close_button": "關閉",
        "help_button_tooltip": "說明",

        # --- Tab 1: TXT 檔案轉換 ---
        "s2t_radio": "簡體→繁體",
        "t2s_radio": "繁體→簡體",
        "enable_custom_toggle": "啟用自訂詞彙",
        "manual_encoding_toggle": "手動指定編碼",
        "output_folder_label": "輸出資料夾:",
        "custom_filename_toggle": "自訂輸出檔名",
        "convert_checked_button": "轉換勾選檔案",
        "convert_all_button": "轉換所有檔案",
        "treeview_header_filename": "檔案名稱",
        "preview_original_label": "原始內容",
        "preview_converted_label": "轉換後內容",
        "font_size_label": "預覽字體大小:",
        "read_error_label": "讀取失敗",
        "read_error_content": "無法讀取或解碼。",
        "encoding_label": "編碼",
        "preview_truncated_msg": "內容過長，僅顯示前 {limit} 字元",
        "preview_original_label_last_conversion": "原始內容 (上次轉換)",

        # --- Tab 2: 檔名轉換 ---
        "file_handling_label": "檔案處理:",
        "move_radio": "移動",
        "copy_radio": "複製",
        "treeview_header_original": "原始檔名",
        "treeview_header_preview": "預覽新檔名",
        "rename_checked_button": "重命名勾選檔案",
        "rename_all_button": "重命名所有檔案",
        "enable_filename_lang_detect": "啟用檔名語言偵測 (跳過非中文)",

        # --- Tab 3: 剪貼簿轉換 ---
        "input_content_label": "輸入內容",
        "output_result_label": "輸出結果",
        "paste_button": "貼上",
        "copy_result_button": "複製結果",
        "clear_button": "清除",

        # --- 訊息框、進度條、說明 ---
        "info": "提示",
        "warning": "警告",
        "error": "錯誤",
        "confirm": "確認",
        "processing_label": "正在處理",
        "processing_label_short": "載入中，請稍候...",
        "confirm_cancel_task": "確定要取消目前的任務嗎？",
        "all_files_in_list": "所有選擇的檔案均已在列表中。",
        "confirm_clear_list": "確定要清空所有已選檔案嗎？",
        "no_files_to_remove": "請先勾選要從列表中移除的檔案。",
        "confirm_remove_unchecked_files": "確定要從列表中移除這 {count} 個未勾選的檔案嗎？",
        "confirm_remove_selected_files": "確定要從列表中移除這 {count} 個選定的檔案嗎？",
        "no_selection_to_uncheck": "沒有選取任何項目可供取消勾選。",
        "no_files_for_action": "沒有 {scope} 可供{action}。",
        "action_convert": "轉換",
        "action_rename": "重命名",
        "action_remove": "移除",
        "scope_checked_files": "勾選檔案",
        "scope_all_files": "所有檔案",
        "scope_unchecked_files": "未勾選檔案",
        "invalid_output_folder": "請指定一個有效的輸出資料夾。",
        "task_cancelled": "任務取消",
        "task_cancelled_msg": "任務已被取消。\n成功: {success}, 失敗/跳過: {fail}",
        "task_complete": "處理完成",
        "task_complete_msg": "處理完成。\n成功: {success}, 失敗/跳過: {fail}\n檔案儲存於: {folder}",
        "task_complete_msg_rename": "處理完成。\n成功 {action}: {success}, 失敗: {fail}\n檔案已儲存至: {folder}",
        "action_moved": "移動",
        "action_copied": "複製",
        "nothing_to_undo": "沒有上一步操作可供復原。",
        "paste_failed": "貼上失敗",
        "paste_no_text": "剪貼簿中沒有文字內容可供貼上。",
        "copy_failed": "複製失敗",
        "copy_no_text": "輸出結果為空，沒有內容可供複製。",
        "copy_success": "成功",
        "copy_success_msg": "輸出結果已成功複製到剪貼簿。",
        "add_vocab_tooltip": "新增詞彙",
        "delete_vocab_tooltip": "刪除勾選詞彙",
        "vocab_empty_error": "原詞和目標詞都不能為空。",
        "vocab_overwrite_confirm": "詞彙 '{original}' 已存在，是否更新為 '{target}'？",
        "vocab_add_success": "詞彙 '{original} -> {target}' 已新增。",
        "vocab_delete_no_selection": "請先勾選要刪除的詞彙。",
        "vocab_delete_confirm": "確定要刪除所有勾選的詞彙嗎？",
        "vocab_delete_success": "已刪除所有勾選的詞彙。",
        "load_vocab_error": "載入特殊詞彙檔時發生錯誤",
        "save_vocab_error": "儲存特殊詞彙時發生錯誤",
        "conversion_error": "轉換時發生錯誤",
        "original_word": "原詞",
        "target_word": "目標詞",
        "conversion_rule_header": "轉換規則 (簡體 -> 繁體)",

        # --- 設定視窗 ---
        "settings_title": "語言設定",
        "settings_apply": "套用",
        "settings_language_label": "請選擇介面語言：",
        
        # --- 說明視窗 ---
        "help_title": "使用說明",
        "help_message": """
基本操作:
1.  可透過「匯入檔案」或「匯入資料夾」按鈕加入檔案。
2.  支援直接將檔案或資料夾拖曳至視窗內。
3.  在各分頁選擇轉換選項（如簡轉繁、處理方式等）。
4.  點擊「轉換」或「重命名」按鈕開始處理。

列表顏色代表意義:
- 預設 (黑色): 待處理的檔案。
- 紅色: 已成功處理的檔案。
- 藍色: 被判斷為非中文內容而跳過的檔案。
- 灰色: 因其他原因（如檔名未變、任務取消）而跳過的檔案。

提示:
- 在「檔名轉換」頁面，可勾選「啟用檔名語言偵測」來自動跳過非中文檔名，避免錯誤轉換。
- 所有列表操作（新增、移除、清空）都可以透過「復原上一步」按鈕來還原。

--------------------
Developed by: Nichiya Sen, with the assistance of AI: Gemini 2.5, thanks to the advancement of technology.
Completed on 2025/7/17
""",
    },
    "zh_CN": {
        "window_title": "中文繁简转换工具",
        "tab_file_conversion": "TXT 文件转换",
        "tab_filename_conversion": "文件名转换",
        "tab_clipboard_conversion": "剪贴板转换",
        
        # --- 通用按钮 ---
        "import_files": "导入文件",
        "import_folder": "导入文件夹",
        "clear_list": "清空列表",
        "remove_unchecked": "移除未勾选",
        "uncheck_selected_button": "取消选取",
        "undo": "恢复上一步",
        "custom_conversions_manage": "词汇转换管理",
        "pause_button": "暂停",
        "resume_button": "继续",
        "cancel_button": "取消",
        "close_button": "关闭",
        "help_button_tooltip": "说明",

        # --- Tab 1: TXT 文件转换 ---
        "s2t_radio": "简体→繁体",
        "t2s_radio": "繁体→简体",
        "enable_custom_toggle": "启用自定义词汇",
        "manual_encoding_toggle": "手动指定编码",
        "output_folder_label": "输出文件夹:",
        "custom_filename_toggle": "自定义输出文件名",
        "convert_checked_button": "转换勾选文件",
        "convert_all_button": "转换所有文件",
        "treeview_header_filename": "文件名称",
        "preview_original_label": "原始内容",
        "preview_converted_label": "转换后内容",
        "font_size_label": "预览字体大小:",
        "read_error_label": "读取失败",
        "read_error_content": "无法读取或解码。",
        "encoding_label": "编码",
        "preview_truncated_msg": "内容过长，仅显示前 {limit} 字符",
        "preview_original_label_last_conversion": "原始内容 (上次转换)",

        # --- Tab 2: 文件名转换 ---
        "file_handling_label": "文件处理:",
        "move_radio": "移动",
        "copy_radio": "复制",
        "treeview_header_original": "原始文件名",
        "treeview_header_preview": "预览新文件名",
        "rename_checked_button": "重命名勾选文件",
        "rename_all_button": "重命名所有文件",
        "enable_filename_lang_detect": "启用文件名语言检测 (跳过非中文)",

        # --- Tab 3: 剪贴簿转换 ---
        "input_content_label": "输入内容",
        "output_result_label": "输出结果",
        "paste_button": "粘贴",
        "copy_result_button": "复制结果",
        "clear_button": "清除",

        # --- 消息框、进度条、说明 ---
        "info": "提示",
        "warning": "警告",
        "error": "错误",
        "confirm": "确认",
        "processing_label": "正在处理",
        "processing_label_short": "加载中，请稍候...",
        "confirm_cancel_task": "确定要取消目前的任务吗？",
        "all_files_in_list": "所有选择的文件均已在列表中。",
        "confirm_clear_list": "确定要清空所有已选文件吗？",
        "no_files_to_remove": "请先勾选要从列表中移除的文件。",
        "confirm_remove_unchecked_files": "确定要从列表中移除这 {count} 个未勾选的文件吗？",
        "confirm_remove_selected_files": "确定要从列表中移除这 {count} 个选定的文件吗？",
        "no_selection_to_uncheck": "没有选取任何项目可供取消勾选。",
        "no_files_for_action": "没有{scope}可供{action}。",
        "action_convert": "转换",
        "action_rename": "重命名",
        "action_remove": "移除",
        "scope_checked_files": "勾选文件",
        "scope_all_files": "所有文件",
        "scope_unchecked_files": "未勾选文件",
        "invalid_output_folder": "请指定一个有效的输出文件夹。",
        "task_cancelled": "任务取消",
        "task_cancelled_msg": "任务已被取消。\n成功: {success}, 失败/跳过: {fail}",
        "task_complete": "处理完成",
        "task_complete_msg": "处理完成。\n成功: {success}, 失败/跳過: {fail}\n文件保存于: {folder}",
        "task_complete_msg_rename": "处理完成。\n成功 {action}: {success}, 失败: {fail}\n文件已保存至: {folder}",
        "action_moved": "移动",
        "action_copied": "复制",
        "nothing_to_undo": "没有上一步操作可供恢复。",
        "paste_failed": "粘贴失败",
        "paste_no_text": "剪贴板中没有文本内容可供粘贴。",
        "copy_failed": "复制失败",
        "copy_no_text": "输出结果为空，没有内容可供复制。",
        "copy_success": "成功",
        "copy_success_msg": "输出结果已成功复制到剪贴板。",
        "add_vocab_tooltip": "新增词汇",
        "delete_vocab_tooltip": "删除勾选词汇",
        "vocab_empty_error": "原词和目标词都不能为空。",
        "vocab_overwrite_confirm": "词汇 '{original}' 已存在，是否更新为 '{target}'？",
        "vocab_add_success": "词汇 '{original} -> {target}' 已新增。",
        "vocab_delete_no_selection": "请先勾选要删除的词汇。",
        "vocab_delete_confirm": "确定要删除所有勾选的词汇吗？",
        "vocab_delete_success": "已删除所有勾选的词汇。",
        "load_vocab_error": "加载特殊词汇文件时发生错误",
        "save_vocab_error": "保存特殊词汇时发生错误",
        "conversion_error": "转换时发生错误",
        "original_word": "原词",
        "target_word": "目标词",
        "conversion_rule_header": "转换规则 (简体 -> 繁体)",

        # --- 设置窗口 ---
        "settings_title": "语言设置",
        "settings_apply": "应用",
        "settings_language_label": "请选择界面语言：",
        
        # --- 说明窗口 ---
        "help_title": "使用说明",
        "help_message": """
基本操作:
1.  可通过「导入文件」或「导入文件夹」按钮加入文件。
2.  支持直接将文件或文件夹拖拽至窗口内。
3.  在各分页选择转换选项（如简转繁、处理方式等）。
4.  点击「转换」或「重命名」按钮开始处理。

列表颜色代表意义:
- 默认 (黑色): 待处理的文件。
- 红色: 已成功处理的文件。
- 蓝色: 被判断为非中文内容而跳过的文件。
- 灰色: 因其他原因（如文件名未变、任务取消）而跳过的文件。

提示:
- 在「文件名转换」页面，可勾选「启用文件名语言检测」来自动跳过非中文文件名，避免错误转换。
- 所有列表操作（新增、移除、清空）都可以通过「恢复上一步」按钮来还原。

--------------------
Developed by: Nichiya Sen, with the assistance of AI: Gemini 2.5, thanks to the advancement of technology.
Completed on 2025/7/17
""",
    },
    "en": {
        "window_title": "Chinese Converter Tool",
        "tab_file_conversion": "TXT File Conversion",
        "tab_filename_conversion": "Filename Conversion",
        "tab_clipboard_conversion": "Clipboard Conversion",
        
        # --- General Buttons ---
        "import_files": "Import Files",
        "import_folder": "Import Folder",
        "clear_list": "Clear List",
        "remove_unchecked": "Remove Unchecked",
        "uncheck_selected_button": "Uncheck Selected",
        "undo": "Undo Last Step",
        "custom_conversions_manage": "Manage Vocabulary",
        "pause_button": "Pause",
        "resume_button": "Resume",
        "cancel_button": "Cancel",
        "close_button": "Close",
        "help_button_tooltip": "Help",

        # --- Tab 1: TXT File Conversion ---
        "s2t_radio": "Simplified → Traditional",
        "t2s_radio": "Traditional → Simplified",
        "enable_custom_toggle": "Enable Custom Vocabulary",
        "manual_encoding_toggle": "Manually Specify Encoding",
        "output_folder_label": "Output Folder:",
        "custom_filename_toggle": "Custom Output Filename",
        "convert_checked_button": "Convert Checked Files",
        "convert_all_button": "Convert All Files",
        "treeview_header_filename": "File Name",
        "preview_original_label": "Original Content",
        "preview_converted_label": "Converted Content",
        "font_size_label": "Preview Font Size:",
        "read_error_label": "Read Error",
        "read_error_content": "Could not read or decode content.",
        "encoding_label": "Encoding",
        "preview_truncated_msg": "Content too long, showing first {limit} characters only",
        "preview_original_label_last_conversion": "Original Content (Last Conversion)",

        # --- Tab 2: Filename Conversion ---
        "file_handling_label": "File Handling:",
        "move_radio": "Move",
        "copy_radio": "Copy",
        "treeview_header_original": "Original Filename",
        "treeview_header_preview": "Preview New Filename",
        "rename_checked_button": "Rename Checked Files",
        "rename_all_button": "Rename All Files",
        "enable_filename_lang_detect": "Enable Filename Language Detection (Skip Non-Chinese)",

        # --- Tab 3: Clipboard Conversion ---
        "input_content_label": "Input Content",
        "output_result_label": "Output Result",
        "paste_button": "Paste",
        "copy_result_button": "Copy Result",
        "clear_button": "Clear",

        # --- Message Boxes, Progress Bar, Help ---
        "info": "Info",
        "warning": "Warning",
        "error": "Error",
        "confirm": "Confirm",
        "processing_label": "Processing",
        "processing_label_short": "Loading, please wait...",
        "confirm_cancel_task": "Are you sure you want to cancel the current task?",
        "all_files_in_list": "All selected files are already in the list.",
        "confirm_clear_list": "Are you sure you want to clear all selected files?",
        "no_files_to_remove": "Please check files to remove from the list first.",
        "confirm_remove_unchecked_files": "Are you sure you want to remove these {count} unchecked files from the list?",
        "confirm_remove_selected_files": "Are you sure you want to remove these {count} selected files from the list?",
        "no_selection_to_uncheck": "No items selected to uncheck.",
        "no_files_for_action": "No {scope} available for {action}.",
        "action_convert": "convert",
        "action_rename": "rename",
        "action_remove": "remove",
        "scope_checked_files": "checked files",
        "scope_all_files": "all files",
        "scope_unchecked_files": "unchecked files",
        "invalid_output_folder": "Please specify a valid output folder.",
        "task_cancelled": "Task Cancelled",
        "task_cancelled_msg": "Task has been cancelled.\nSuccessful: {success}, Failed/Skipped: {fail}",
        "task_complete": "Processing Complete",
        "task_complete_msg": "Processing complete.\nSuccessful: {success}, Failed/Skipped: {fail}\nFiles saved to: {folder}",
        "task_complete_msg_rename": "Processing complete.\nSuccessfully {action}: {success}, Failed: {fail}\nFiles saved to: {folder}",
        "action_moved": "moved",
        "action_copied": "copied",
        "nothing_to_undo": "No previous action to undo.",
        "paste_failed": "Paste Failed",
        "paste_no_text": "No text content in clipboard to paste.",
        "copy_failed": "Copy Failed",
        "copy_no_text": "Output result is empty, no content to copy.",
        "copy_success": "Success",
        "copy_success_msg": "Output result successfully copied to clipboard.",
        "add_vocab_tooltip": "Add Vocabulary",
        "delete_vocab_tooltip": "Delete Checked Vocabulary",
        "vocab_empty_error": "Original and target words cannot be empty.",
        "vocab_overwrite_confirm": "Vocabulary '{original}' already exists. Update to '{target}'?",
        "vocab_add_success": "Vocabulary '{original} -> {target}' added.",
        "vocab_delete_no_selection": "Please check the vocabulary to delete first.",
        "vocab_delete_confirm": "Are you sure you want to delete all checked vocabulary?",
        "vocab_delete_success": "All checked vocabulary deleted.",
        "load_vocab_error": "Error loading custom vocabulary file",
        "save_vocab_error": "Error saving custom vocabulary",
        "conversion_error": "Error during conversion",
        "original_word": "Original Word",
        "target_word": "Target Word",
        "conversion_rule_header": "Conversion Rule (Simplified -> Traditional)",

        # --- Language Settings Window ---
        "settings_title": "Language Settings",
        "settings_apply": "Apply",
        "settings_language_label": "Please select interface language:",
        
        # --- Help Window ---
        "help_title": "Help",
        "help_message": """
Basic Operation:
1.  You can add files using the "Import Files" or "Import Folder" buttons.
2.  Supports directly dragging and dropping files or folders into the window.
3.  Select conversion options (e.g., S2T, processing method) on each tab.
4.  Click "Convert" or "Rename" buttons to start processing.

List Color Meanings:
- Default (Black): Files pending processing.
- Red: Successfully processed files.
- Blue: Files skipped due to being identified as non-Chinese content.
- Grey: Files skipped for other reasons (e.g., filename unchanged, task cancelled).

Tips:
- On the "Filename Conversion" page, you can check "Enable Filename Language Detection" to automatically skip non-Chinese filenames, avoiding incorrect conversions.
- All list operations (add, remove, clear) can be undone using the "Undo Last Step" button.

--------------------
Developed by: Nichiya Sen, with the assistance of AI: Gemini 2.5, thanks to the advancement of technology.
Completed on 2025/7/17
""",
    },
    "ja": {
        "window_title": "中国語繁簡转换ツール",
        "tab_file_conversion": "TXTファイル変換",
        "tab_filename_conversion": "ファイル名変換",
        "tab_clipboard_conversion": "クリップボード変換",
        
        # --- 一般的なボタン ---
        "import_files": "ファイルをインポート",
        "import_folder": "フォルダをインポート",
        "clear_list": "リストをクリア",
        "remove_unchecked": "チェックされていない項目を削除",
        "uncheck_selected_button": "選択を解除",
        "undo": "元に戻す",
        "custom_conversions_manage": "語彙管理",
        "pause_button": "一時停止",
        "resume_button": "再開",
        "cancel_button": "キャンセル",
        "close_button": "閉じる",
        "help_button_tooltip": "ヘルプ",

        # --- タブ1: TXTファイル変換 ---
        "s2t_radio": "簡体字→繁体字",
        "t2s_radio": "繁体字→簡体字",
        "enable_custom_toggle": "カスタム語彙を有効にする",
        "manual_encoding_toggle": "手動でエンコーディング指定",
        "output_folder_label": "出力フォルダ:",
        "custom_filename_toggle": "カスタム出力ファイル名",
        "convert_checked_button": "チェック項目を変換",
        "convert_all_button": "すべて変換",
        "treeview_header_filename": "ファイル名",
        "preview_original_label": "元の内容",
        "preview_converted_label": "変換後の内容",
        "font_size_label": "プレビューフォントサイズ:",
        "read_error_label": "読み込み失敗",
        "read_error_content": "読み込みまたはデコードできません。",
        "encoding_label": "エンコーディング",
        "preview_truncated_msg": "コンテンツが長すぎます。最初の {limit} 文字のみ表示",
        "preview_original_label_last_conversion": "元の内容 (前回の変換)",

        # --- タブ2: ファイル名変換 ---
        "file_handling_label": "ファイル処理:",
        "move_radio": "移動",
        "copy_radio": "コピー",
        "treeview_header_original": "元のファイル名",
        "treeview_header_preview": "新しいファイル名をプレビュー",
        "rename_checked_button": "チェック項目をリネーム",
        "rename_all_button": "すべてリネーム",
        "enable_filename_lang_detect": "ファイル名言語検出を有効にする (非中国語をスキップ)",

        # --- タブ3: クリップボード変換 ---
        "input_content_label": "入力内容",
        "output_result_label": "出力結果",
        "paste_button": "貼り付け",
        "copy_result_button": "結果をコピー",
        "clear_button": "クリア",

        # --- メッセージボックス、プログレスバー、ヘルプ ---
        "info": "情報",
        "warning": "警告",
        "error": "エラー",
        "confirm": "確認",
        "processing_label": "処理中",
        "processing_label_short": "読み込み中、お待ちください...",
        "confirm_cancel_task": "現在のタスクをキャンセルしてもよろしいですか？",
        "all_files_in_list": "選択したすべてのファイルは既にリストにあります。",
        "confirm_clear_list": "リストからすべてのファイルをクリアしてもよろしいですか？",
        "no_files_to_remove": "まずリストから削除するファイルにチェックを入れてください。",
        "confirm_remove_unchecked_files": "リストからチェックされていない{count}個のファイルを削除してもよろしいですか？",
        "confirm_remove_selected_files": "リストからこれらの選択された {count} ファイルを削除してもよろしいですか？",
        "no_selection_to_uncheck": "選択解除する項目はありません。",
        "no_files_for_action": "{action}対象の{scope}がありません。",
        "action_convert": "変換",
        "action_rename": "リネーム",
        "action_remove": "削除",
        "scope_checked_files": "チェックしたファイル",
        "scope_all_files": "すべてのファイル",
        "scope_unchecked_files": "チェックされていないファイル",
        "invalid_output_folder": "有効な出力フォルダを指定してください。",
        "task_cancelled": "タスクがキャンセルされました",
        "task_cancelled_msg": "タスクはキャンセルされました。\n成功: {success}, 失敗/スキップ: {fail}",
        "task_complete": "処理完了",
        "task_complete_msg": "処理が完了しました。\n成功: {success}, 失敗/スキップ: {fail}\nファイル保存先: {folder}",
        "task_complete_msg_rename": "処理が完了しました。\n{action}成功: {success}, 失敗: {fail}\nファイル保存先: {folder}",
        "action_moved": "移動",
        "action_copied": "コピー",
        "nothing_to_undo": "元に戻す操作はありません。",
        "paste_failed": "貼り付け失敗",
        "paste_no_text": "クリップボードに貼り付けるテキスト内容がありません。",
        "copy_failed": "コピー失敗",
        "copy_no_text": "出力結果が空です。コピーする内容がありません。",
        "copy_success": "成功",
        "copy_success_msg": "出力結果をクリップボードにコピーしました。",
        "add_vocab_tooltip": "語彙を追加",
        "delete_vocab_tooltip": "チェックした語彙を削除",
        "vocab_empty_error": "元の単語とターゲットの単語を空にすることはできません。",
        "vocab_overwrite_confirm": "語彙 '{original}' は既に存在します。'{target}' で上書きしますか？",
        "vocab_add_success": "語彙 '{original} -> {target}' が追加されました。",
        "vocab_delete_no_selection": "削除する語彙にチェックを入れてください。",
        "vocab_delete_confirm": "チェックしたすべての語彙を削除してもよろしいですか？",
        "vocab_delete_success": "チェックしたすべての語彙が削除されました。",
        "load_vocab_error": "カスタム語彙ファイルの読み込み中にエラーが発生しました",
        "save_vocab_error": "カスタム語彙の保存中にエラーが発生しました",
        "conversion_error": "変換エラー",
        "original_word": "元の単語",
        "target_word": "ターゲット単語",
        "conversion_rule_header": "変換ルール (簡体字 -> 繁体字)",

        # --- 言語設定ウィンドウ ---
        "settings_title": "言語設定",
        "settings_apply": "適用",
        "settings_language_label": "インターフェース言語を選択してください：",
        
        # --- ヘルプウィンドウ ---
        "help_title": "ヘルプ",
        "help_message": """
基本操作:
1.  「ファイルをインポート」または「フォルダをインポート」ボタンでファイルを追加します。
2.  ファイルやフォルダをウィンドウに直接ドラッグアンドドロップすることもできます。
3.  各タブで変換オプション（例：簡体字→繁体字、処理方法）を選択します。
4.  「変換」または「リネーム」ボタンをクリックして処理を開始します。

リストの色の意味:
- デフォルト (黒): 処理待ちのファイル。
- 赤: 正常に処理されたファイル。
- 青: 非中国語コンテンツと判断されてスキップされたファイル。
- グレー: その他の理由（ファイル名が変更されていない、タスクがキャンセルされたなど）でスキップされたファイル。

ヒント:
- 「ファイル名変換」タブで、「ファイル名言語検出を有効にする」にチェックを入れると、非中国語のファイル名を自動的にスキップできます。
- すべてのリスト操作（追加、削除、クリア）は、「元に戻す」ボタンで元に戻すことができます。

--------------------
Developed by: Nichiya Sen, with the assistance of AI: Gemini 2.5, thanks to the advancement of technology.
Completed on 2025/7/17
""",
    }
}


class LanguageManager:
    def __init__(self):
        self.language_map = LANGUAGES
        self.current_language = self.load_language_setting()

    def get_string(self, key, **kwargs):
        try:
            template = self.language_map[self.current_language][key]
            return template.format(**kwargs) if kwargs else template
        except KeyError:
            try:
                # Fallback to English if key not in current language
                template = self.language_map['en'][key]
                return template.format(**kwargs) if kwargs else template
            except KeyError:
                # Return the key itself if not found anywhere
                return key

    def set_language(self, lang_code):
        if lang_code in self.language_map:
            self.current_language = lang_code
            self.save_language_setting(lang_code)

    def load_language_setting(self):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                lang = settings.get("language")
                if lang in self.language_map:
                    return lang
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        # Default language
        return "zh_TW"

    def save_language_setting(self, lang_code):
        try:
            # Load existing settings to preserve other settings
            existing_settings = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    existing_settings = json.load(f)
            
            existing_settings["language"] = lang_code # Update language setting
            
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(existing_settings, f, indent=4) # Save all settings
        except Exception as e:
            print(f"Error saving language setting: {e}")

# Global instance
lm = LanguageManager()