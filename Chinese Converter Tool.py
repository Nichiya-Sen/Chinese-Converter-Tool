#
# 檔案名稱: Chinese Converter Tool 

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, font as tkfont
from opencc import OpenCC
import os
import chardet
import json
import threading
from collections import deque
import shutil
import time
import copy
import tkinterdnd2 as tkdnd
import sys
import re

# 嘗試引入 langdetect，如果失敗則提示使用者安裝
try:
    from langdetect import detect, DetectorFactory
    from langdetect.lang_detect_exception import LangDetectException
    DetectorFactory.seed = 0 # 確保每次檢測結果一致
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

# 引入 language_manager 模組
from language_manager import lm

# --- 輔助函式：尋找打包後的資源路徑 ---
def resource_path(relative_path):
    """ 取得打包後資源的絕對路徑，適用於開發環境和 PyInstaller """
    try:
        # PyInstaller 建立一個暫時資料夾，並將路徑儲存在 _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- 常數定義 ---
CUSTOM_CONVERSIONS_FILE = "custom_conversions.json"
SETTINGS_FILE = "settings.json"
CHECK_BOX_CHECKED = "☑"
CHECK_BOX_UNCHECKED = "☐"
CHECK_BOX_PARTIAL = "▬"
WORD_BLUE_DARK = "#2B579A"
WORD_BLUE_LIGHT = "#A3C7E9"
WORD_TEXT_DARK = "#333333"
WORD_TEXT_LIGHT = "#FFFFFF"
WORD_BG_LIGHT = "#F0F0F0"
COLOR_CONVERTED = "red"
COLOR_SKIPPED = "grey"
COLOR_NON_CHINESE = "#0000CC"
DEFAULT_FONT_FAMILY = "Microsoft JhengHei"
DEFAULT_FONT_SIZE_NORMAL = 12
DEFAULT_FONT_SIZE_LARGE = 14
DEFAULT_FONT_SIZE_PREVIEW = 11
DEFAULT_FONT = (DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE_NORMAL)
TITLE_FONT = (DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE_LARGE, "bold")
PREVIEW_FONT_BASE = (DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE_PREVIEW)
PREVIEW_CHAR_LIMIT = 10000
INITIAL_READ_SIZE_FOR_CHARSET = 1024 * 100
MAX_UNDO_HISTORY = 20

# --- 輔助類別與函式 ---
class CustomCheckbutton(ttk.Frame):
    def __init__(self, parent, variable, text_key, command=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.variable = variable
        self.text_key = text_key
        self.command = command
        self._state = 'normal'
        self.configure(style='TFrame')
        self.label = ttk.Label(self, text="", cursor="hand2", style='TLabel')
        self.label.pack()
        self.label.bind("<Button-1>", self._on_click)
        self.variable.trace_add("write", self._update_visuals)
        self._update_visuals()

    def _on_click(self, event=None):
        if self._state == 'normal':
            self.variable.set(not self.variable.get())
            if self.command:
                self.after(10, self.command)

    def _update_visuals(self, *args):
        state_char = CHECK_BOX_CHECKED if self.variable.get() else CHECK_BOX_UNCHECKED
        label_text = f"{state_char} {lm.get_string(self.text_key)}"
        self.label.config(text=label_text)
        if self._state == 'disabled':
            self.label.config(foreground="grey")
        else:
            self.label.config(foreground=WORD_TEXT_DARK)

    def configure(self, **kwargs):
        if 'state' in kwargs:
            self._state = kwargs.pop('state')
            self._update_visuals()
        super().configure(**kwargs)
        if 'background' in kwargs:
             self.label.configure(background=kwargs['background'])

    def config(self, **kwargs):
        self.configure(**kwargs)

    def update_language(self):
        self._update_visuals()


def contains_chinese(text):
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def is_convertible_chinese(text):
    if not text or not LANGDETECT_AVAILABLE: return True
    try:
        if detect(text) == 'ja': return False
    except LangDetectException: pass
    return contains_chinese(text)

class Tooltip:
    def __init__(self, widget, text_key):
        self.widget = widget; self.text_key = text_key; self.tooltip_window = None
        widget.bind("<Enter>", self.enter); widget.bind("<Leave>", self.leave)
    def enter(self, event=None):
        text = lm.get_string(self.text_key)
        x, y, _, _ = self.widget.bbox("insert"); x += self.widget.winfo_rootx() + 25; y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tk.Toplevel(self.widget); self.tooltip_window.wm_overrideredirect(True); self.tooltip_window.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tooltip_window, text=text, justify='left', background="#ffffe0", relief='solid', borderwidth=1, font=(DEFAULT_FONT_FAMILY, 10)).pack(ipadx=1)
    def leave(self, event=None):
        if self.tooltip_window: self.tooltip_window.destroy()

def center_window(toplevel_window):
    toplevel_window.update_idletasks(); master = toplevel_window.master;
    x = master.winfo_x() + (master.winfo_width() - toplevel_window.winfo_width()) // 2
    y = master.winfo_y() + (master.winfo_height() - toplevel_window.winfo_height()) // 2
    toplevel_window.geometry(f"+{x}+{y}")

class ProgressDialog(tk.Toplevel):
    def __init__(self, parent, title_key, total=100, mode='determinate', min_duration=0):
        super().__init__(parent); self.title(lm.get_string(title_key)); self.geometry("500x150")
        self.transient(parent); self.grab_set();
        self.mode = mode
        self.min_duration = min_duration
        self.creation_time = time.time()
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.pause_event = threading.Event(); self.cancel_event = threading.Event()
        main_frame = ttk.Frame(self, padding="15"); main_frame.pack(fill='both', expand=True)
        self.status_label = ttk.Label(main_frame, text=f"{lm.get_string('info')}...", font=DEFAULT_FONT, wraplength=450); self.status_label.pack(fill='x', pady=5)
        self.progressbar = ttk.Progressbar(main_frame, orient='horizontal', mode=mode, maximum=total)
        self.progressbar.pack(fill='x', pady=5)
        if self.mode == 'indeterminate':
            self.status_label.config(text=f"{lm.get_string('processing_label')}...")
            self.after(200, lambda: self.progressbar.start(10))
        btn_frame = ttk.Frame(main_frame); btn_frame.pack(pady=10)
        self.pause_btn = ttk.Button(btn_frame, text=lm.get_string('pause_button'), command=self.toggle_pause)
        if self.mode == 'determinate':
             self.pause_btn.pack(side='left', padx=10)
        ttk.Button(btn_frame, text=lm.get_string('cancel_button'), command=self.cancel).pack(side='left', padx=10)
        self.update_idletasks()
        center_window(self)
    def update_progress(self, current, filename):
        if self.cancel_event.is_set(): return
        self.progressbar['value'] = current
        self.status_label.config(text=f"{lm.get_string('processing_label')}: {os.path.basename(filename)}")
    def toggle_pause(self):
        if self.pause_event.is_set(): self.pause_event.clear(); self.pause_btn.config(text=lm.get_string('resume_button'))
        else: self.pause_event.set(); self.pause_btn.config(text=lm.get_string('pause_button'))
    def cancel(self):
        if messagebox.askyesno(lm.get_string('confirm'), lm.get_string('confirm_cancel_task'), parent=self):
            self.cancel_event.set(); self._destroy_dialog()
    def close(self):
        if not self.winfo_exists(): return
        elapsed = time.time() - self.creation_time
        if elapsed < self.min_duration:
            delay = int((self.min_duration - elapsed) * 1000)
            self.after(delay, self._destroy_dialog)
        else:
            self._destroy_dialog()
    def _destroy_dialog(self):
        if self.winfo_exists():
            if self.mode == 'indeterminate': self.progressbar.stop()
            self.destroy()

class HelpDialog(tk.Toplevel):
    def __init__(self, parent, title_key, message_key):
        super().__init__(parent)
        self.title(lm.get_string(title_key))
        self.geometry("800x650") 
        self.transient(parent)
        self.grab_set()

        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill='both', expand=True)

        help_font = (DEFAULT_FONT_FAMILY, 12)

        text_area = scrolledtext.ScrolledText(main_frame, wrap='word', font=help_font, relief="flat", bg=WORD_BG_LIGHT, bd=0, highlightthickness=0)
        text_area.pack(fill='both', expand=True, pady=(0, 15))
        text_area.insert('1.0', lm.get_string(message_key))
        text_area.config(state='disabled')

        close_button = ttk.Button(main_frame, text=lm.get_string("close_button"), command=self.destroy, style='Accent.TButton')
        close_button.pack()

        center_window(self)

def convert_text(text, cc_instance, conversion_type, custom_conversions_dict, enable_custom_conversion, cc_s2t, cc_t2s):
    if not cc_instance: return text
    try:
        converted_text = cc_instance.convert(text)
        if enable_custom_conversion and custom_conversions_dict:
            for simp_key, trad_val in custom_conversions_dict.items():
                if conversion_type == 's2t': converted_text = converted_text.replace(cc_s2t.convert(simp_key), trad_val)
                elif conversion_type == 't2s': converted_text = converted_text.replace(cc_t2s.convert(trad_val), simp_key)
        return converted_text
    except Exception as e: return f"Conversion error: {e}"

def read_txt_file_with_encoding_detection(filepath, use_manual_encoding=False, manual_encoding=None):
    try:
        final_encoding = None
        with open(filepath, 'rb') as f: initial_bytes = f.read(INITIAL_READ_SIZE_FOR_CHARSET)
        if use_manual_encoding and manual_encoding: final_encoding = manual_encoding
        else:
            result = chardet.detect(initial_bytes)
            if result['encoding'] and result.get('confidence', 0) > 0.8: final_encoding = result['encoding']
            else:
                for enc in ['utf-8', 'utf-8-sig', 'gbk', 'gb18030', 'big5', 'cp936']:
                    try: initial_bytes.decode(enc, errors='strict'); final_encoding = enc; break
                    except: continue
        if not final_encoding: return None, "Cannot identify file encoding"
        with open(filepath, 'r', encoding=final_encoding, errors='replace') as f: return f.read(), final_encoding
    except Exception as e: return None, f"Error reading file: {e}"

def process_content_background(app, filepaths, dialog, finish_callback):
    params = app.get_content_conversion_params()
    s_count, f_count, results = 0, 0, {}
    first_orig, first_conv = None, None
    try:
        for i, filepath in enumerate(filepaths):
            if dialog.cancel_event.is_set(): break
            while dialog.pause_event.is_set(): time.sleep(0.1)
            app.master.after(0, app._responsive_update_progress, dialog, i + 1, filepath)
            try:
                if not filepath.lower().endswith('.txt'): f_count += 1; results[filepath] = 'skipped_ext'; continue
                original_content, encoding = read_txt_file_with_encoding_detection(
                    filepath, params['use_manual_encoding'], params['manual_encoding'])
                if original_content is None: f_count += 1; results[filepath] = 'failed_read'; print(f"Read fail '{os.path.basename(filepath)}': {encoding}"); continue
                if not is_convertible_chinese(original_content): f_count += 1; results[filepath] = 'skipped_non_chinese'; print(f"Skip non-Chinese: {os.path.basename(filepath)}"); continue
                converted_content = convert_text(original_content, params['cc_convert'], params['conversion_type'], params['custom_conversions'], params['enable_custom'], app.cc_s2t, app.cc_t2s)
                base_name, ext = os.path.splitext(os.path.basename(filepath)); new_base_name = base_name
                if params['filename_pattern']:
                    try: new_base_name = params['filename_pattern'].format(original_name=base_name, index=i + 1)
                    except Exception as e: new_base_name = f"{base_name}_naming_error"; print(f"Filename format error: {e}")
                new_base_name = params['cc_convert'].convert(new_base_name)
                new_filepath = os.path.join(params['output_folder'], new_base_name + ext)
                counter = 1
                while os.path.exists(new_filepath): new_filepath = os.path.join(params['output_folder'], f"{new_base_name}({counter}){ext}"); counter += 1
                with open(new_filepath, 'w', encoding='utf-8') as f: f.write(converted_content)
                s_count += 1; results[filepath] = 'converted'
                if first_orig is None: first_orig, first_conv = original_content, converted_content
            except Exception as e: f_count += 1; results[filepath] = 'failed_exception'; print(f"Error on '{os.path.basename(filepath)}': {e}")
    finally:
        app.master.after(0, finish_callback, s_count, f_count, params['output_folder'], (first_orig, first_conv), dialog.cancel_event.is_set(), results)
        app.master.after(100, lambda: dialog.close() if dialog.winfo_exists() else None)

def process_filenames_background(app, filepaths, conversion_type, output_folder, operation_type, detect_language, dialog, finish_callback):
    cc = app.cc_s2t if conversion_type == 's2t' else app.cc_t2s
    s_count, f_count, results = 0, 0, {}
    try:
        for i, old_path in enumerate(filepaths):
            if dialog.cancel_event.is_set(): break
            while dialog.pause_event.is_set(): time.sleep(0.1)
            app.master.after(0, app._responsive_update_progress, dialog, i + 1, old_path)
            try:
                if not os.path.exists(old_path): f_count += 1; results[old_path] = 'failed_not_exist'; continue
                filename = os.path.basename(old_path); base_name, ext = os.path.splitext(filename)
                if detect_language and not is_convertible_chinese(base_name): f_count += 1; results[old_path] = 'skipped_non_chinese'; print(f"Skip non-Chinese filename: {filename}"); continue
                new_base_name = cc.convert(base_name)
                if new_base_name + ext == filename: f_count += 1; results[old_path] = 'skipped_unchanged'; continue
                new_path = os.path.join(output_folder, new_base_name + ext)
                counter = 1
                while os.path.exists(new_path): new_path = os.path.join(output_folder, f"{new_base_name}({counter}){ext}"); counter += 1
                if operation_type == 'move': shutil.move(old_path, new_path)
                elif operation_type == 'copy': shutil.copy2(old_path, new_path)
                s_count += 1; results[old_path] = {'status': 'converted', 'new_path': new_path}
            except Exception as e: f_count += 1; results[old_path] = 'failed_exception'; print(f"Error on file '{os.path.basename(old_path)}': {e}")
    finally:
        app.master.after(0, finish_callback, s_count, f_count, output_folder, dialog.cancel_event.is_set(), operation_type, results)
        app.master.after(100, lambda: dialog.close() if dialog.winfo_exists() else None)

def load_custom_conversions(parent_window):
    if not os.path.exists(CUSTOM_CONVERSIONS_FILE): return {}
    try:
        with open(CUSTOM_CONVERSIONS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except Exception as e: messagebox.showwarning(lm.get_string("error"), f"{lm.get_string('load_vocab_error')}: {e}", parent=parent_window); return {}
def save_custom_conversions(conversions_dict, parent_window):
    try:
        with open(CUSTOM_CONVERSIONS_FILE, 'w', encoding='utf-8') as f: json.dump(conversions_dict, f, ensure_ascii=False, indent=4)
    except Exception as e: messagebox.showerror(lm.get_string("error"), f"{lm.get_string('save_vocab_error')}: {e}", parent=parent_window)

class CustomConversionsManager(tk.Toplevel):
    def __init__(self, master, current_conversions, update_callback):
        super().__init__(master); self.title(lm.get_string("custom_conversions_manage")); self.geometry("600x450"); self.transient(master); self.grab_set()
        self.update_callback = update_callback; self.display_data = [{'key': k, 'val': v, 'checked': False} for k, v in current_conversions.items()]
        self.configure(bg=WORD_BG_LIGHT)
        s = ttk.Style(self); s.configure('CustomManager.Treeview', rowheight=25, font=DEFAULT_FONT); s.configure('CustomManager.Treeview.Heading', font=TITLE_FONT)
        add_frame = tk.Frame(self, padx=10, pady=10, bg=WORD_BG_LIGHT); add_frame.pack(fill='x')
        tk.Label(add_frame, text=f"{lm.get_string('original_word')}:", bg=WORD_BG_LIGHT).pack(side='left', padx=5)
        self.original_entry = tk.Entry(add_frame, width=20, font=DEFAULT_FONT, relief="flat"); self.original_entry.pack(side='left', padx=5)
        tk.Label(add_frame, text=f"{lm.get_string('target_word')}:", bg=WORD_BG_LIGHT).pack(side='left', padx=5)
        self.target_entry = tk.Entry(add_frame, width=20, font=DEFAULT_FONT, relief="flat"); self.target_entry.pack(side='left', padx=5)
        add_btn = ttk.Button(add_frame, text="+", command=self.add_conversion, style='Accent.TButton', width=3); add_btn.pack(side='left', padx=10); Tooltip(add_btn, "add_vocab_tooltip")
        list_frame = tk.Frame(self, padx=10, pady=10, bg=WORD_BG_LIGHT); list_frame.pack(fill='both', expand=True)
        self.treeview = ttk.Treeview(list_frame, columns=("checked_status", "rule"), show="headings", style='CustomManager.Treeview')
        self.treeview.heading("checked_status", text="☐", anchor='center', command=self.toggle_all_checkboxes)
        self.treeview.heading("rule", text=lm.get_string('conversion_rule_header'), anchor='w'); self.treeview.column("checked_status", width=50, anchor='center', stretch=False); self.treeview.column("rule", width=500, anchor='w')
        self.treeview.pack(side='left', fill='both', expand=True); scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.treeview.yview); scrollbar.pack(side='right', fill='y'); self.treeview.config(yscrollcommand=scrollbar.set); self.treeview.bind("<Button-1>", self.on_treeview_click)
        bottom_frame = tk.Frame(self, padx=10, pady=5, bg=WORD_BG_LIGHT); bottom_frame.pack(fill='x')
        del_btn = ttk.Button(bottom_frame, text="-", command=self.delete_checked_conversions, style='Accent.TButton', width=3); del_btn.pack(side='right'); Tooltip(del_btn, "delete_vocab_tooltip")
        self.load_conversions_to_treeview(); self.protocol("WM_DELETE_WINDOW", self.on_closing)
        center_window(self)
    def load_conversions_to_treeview(self): self.treeview.delete(*self.treeview.get_children()); [self.treeview.insert("", "end", iid=item['key'], values=("☑" if item["checked"] else "☐", f"{item['key']} -> {item['val']}")) for item in self.display_data]; self.update_header_checkbox()
    def update_header_checkbox(self):
        if not self.display_data: self.treeview.heading("checked_status", text="☐"); return
        states = [item["checked"] for item in self.display_data]
        if all(states): self.treeview.heading("checked_status", text="☑")
        elif not any(states): self.treeview.heading("checked_status", text="☐")
        else: self.treeview.heading("checked_status", text="▬")
    def toggle_all_checkboxes(self): new_state = self.treeview.heading("checked_status")['text'] != "☑"; [item.update({"checked": new_state}) for item in self.display_data]; self.load_conversions_to_treeview()
    def on_treeview_click(self, event):
        if self.treeview.identify_region(event.x, event.y) == "cell" and self.treeview.identify_column(event.x) == "#1":
            if item_id := self.treeview.identify_row(event.y): [item.update({"checked": not item["checked"]}) for item in self.display_data if item['key'] == item_id]; self.load_conversions_to_treeview()
    def add_conversion(self):
        original, target = self.original_entry.get().strip(), self.target_entry.get().strip()
        if not original or not target: messagebox.showwarning(lm.get_string('warning'), lm.get_string('vocab_empty_error'), parent=self); return
        if any(item['key'] == original for item in self.display_data):
            if messagebox.askyesno(lm.get_string('confirm'), lm.get_string('vocab_overwrite_confirm', original=original, target=target), parent=self): [item.update({"val": target}) for item in self.display_data if item['key'] == original]
        else: self.display_data.append({'key': original, 'val': target, 'checked': False}); messagebox.showinfo(lm.get_string('success'), lm.get_string('vocab_add_success', original=original, target=target), parent=self)
        self.load_conversions_to_treeview(); self.original_entry.delete(0, tk.END); self.target_entry.delete(0, tk.END)
    def delete_checked_conversions(self):
        if not any(item['checked'] for item in self.display_data): messagebox.showwarning(lm.get_string('warning'), lm.get_string('vocab_delete_no_selection'), parent=self); return
        if messagebox.askyesno(lm.get_string('confirm'), lm.get_string('vocab_delete_confirm'), parent=self): self.display_data = [item for item in self.display_data if not item['checked']]; self.load_conversions_to_treeview(); messagebox.showinfo(lm.get_string('success'), lm.get_string('vocab_delete_success'), parent=self)
    def on_closing(self): self.update_callback({item['key']: item['val'] for item in self.display_data}); self.destroy()

class ConverterApp:
    def __init__(self, master):
        self.master = master
        self.master.title(lm.get_string("window_title"))
        
        # --- 設定視窗圖示 ---
        try:
            icon_path = resource_path('Converter.ico')
            # 使用 PhotoImage 和 iconphoto 來確保圖示在工作列和視窗上都能正確顯示
            photo = tk.PhotoImage(file=icon_path)
            self.master.iconphoto(True, photo)
        except tk.TclError:
            print("提示：找不到 'Converter.ico' 圖示檔案或格式不支援，將使用預設圖示。")
        # ---------------------

        self.master.geometry("1400x900")
        if not LANGDETECT_AVAILABLE:
             messagebox.showwarning(lm.get_string("warning"), "Python 'langdetect' package not found.\nLanguage detection will be disabled.\nPlease install it via: pip install langdetect")
        self.cc_s2t, self.cc_t2s = OpenCC('s2t'), OpenCC('t2s')
        self.ct_undo_stack, self.fn_undo_stack, self.cl_undo_stack = deque(maxlen=MAX_UNDO_HISTORY), deque(maxlen=MAX_UNDO_HISTORY), deque(maxlen=MAX_UNDO_HISTORY)
        self.last_import_path = os.path.expanduser("~")
        self.ct_initial_sash_pos = 0
        self.ct_sash_applied = False

        self.setup_styles()
        top_bar = ttk.Frame(master); top_bar.pack(fill='x', padx=5, pady=(5,0))
        self.help_button = ttk.Button(top_bar, text="❓", command=self.show_help, width=3); self.help_button.pack(side='right', padx=(5, 0)); Tooltip(self.help_button, "help_button_tooltip")
        self.settings_button = ttk.Button(top_bar, text="⚙️", command=self.open_language_settings, width=3); self.settings_button.pack(side='right')
        self.notebook = ttk.Notebook(master); self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        self.notebook.drop_target_register(tkdnd.DND_FILES); self.notebook.dnd_bind('<<Drop>>', self.on_drop)
        self.content_tab = ttk.Frame(self.notebook, padding="10"); self.notebook.add(self.content_tab, text=lm.get_string("tab_file_conversion")); self.create_content_converter_tab()
        self.filename_tab = ttk.Frame(self.notebook, padding="10"); self.notebook.add(self.filename_tab, text=lm.get_string("tab_filename_conversion")); self.create_filename_converter_tab()
        self.clipboard_tab = ttk.Frame(self.notebook, padding="10"); self.notebook.add(self.clipboard_tab, text=lm.get_string("tab_clipboard_conversion")); self.create_clipboard_converter_tab()
        self.load_settings()
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _responsive_update_progress(self, dialog, current, filename):
        if dialog.winfo_exists():
            dialog.update_progress(current, filename)
            self.master.update()

    def on_closing(self):
        self.save_settings()
        save_custom_conversions(self.ct_custom_conversions, self.master)
        self.master.destroy()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('.', background=WORD_BG_LIGHT, foreground=WORD_TEXT_DARK, font=DEFAULT_FONT)
        self.style.configure('TFrame', background=WORD_BG_LIGHT)
        self.style.configure('TLabel', background=WORD_BG_LIGHT, foreground=WORD_TEXT_DARK, font=DEFAULT_FONT)
        self.style.configure('TButton', background=WORD_BLUE_LIGHT, foreground=WORD_BLUE_DARK, borderwidth=0, relief="flat", font=DEFAULT_FONT, padding=[10, 5])
        self.style.map('TButton', background=[('active', WORD_BLUE_DARK)], foreground=[('active', 'white')])
        self.style.configure('Accent.TButton', background=WORD_BLUE_DARK, foreground="white", borderwidth=0, relief="flat", font=DEFAULT_FONT, padding=[10, 8])
        self.style.map('Accent.TButton', background=[('active', WORD_BLUE_LIGHT)], foreground=[('active', WORD_BLUE_DARK)])
        self.style.configure('Treeview', background="white", foreground=WORD_TEXT_DARK, fieldbackground="white", borderwidth=0, relief="flat", rowheight=25, font=DEFAULT_FONT)
        self.style.map('Treeview', background=[('selected', WORD_BLUE_LIGHT)])
        self.style.configure('Treeview.Heading', background=WORD_BG_LIGHT, foreground=WORD_TEXT_DARK, font=TITLE_FONT, relief="flat", borderwidth=0)
        self.style.configure('TCombobox', fieldbackground="white", foreground=WORD_TEXT_DARK, selectbackground=WORD_BLUE_LIGHT, selectforeground=WORD_TEXT_DARK, borderwidth=1, relief="flat", font=DEFAULT_FONT)
        self.style.map('TCombobox', fieldbackground=[('readonly', 'white')], selectbackground=[('readonly', WORD_BLUE_LIGHT)])
        self.style.configure('TScale', background=WORD_BG_LIGHT, troughcolor=WORD_BLUE_LIGHT, sliderrelief='flat')
        self.style.map('TScale', background=[('active', WORD_BLUE_DARK)])
        self.style.configure('TCheckbutton', background=WORD_BG_LIGHT)

    def on_drop(self, event):
        try: filepaths = self.master.tk.splitlist(event.data)
        except tk.TclError: filepaths = [p for p in event.data.split('\n') if p]
        all_paths = []
        for path in filepaths:
            path = path.strip()
            if not path: continue
            if os.path.isdir(path):
                for root, _, files in os.walk(path): [all_paths.append(os.path.join(root, name)) for name in files]
                self.last_import_path = path
            elif os.path.isfile(path): all_paths.append(path); self.last_import_path = os.path.dirname(path)
        if not all_paths: return
        active_tab = self.notebook.index(self.notebook.select())
        if active_tab == 0:
            if txt_files := [p for p in all_paths if p.lower().endswith('.txt')]: self.ct_add_files_to_list(txt_files)
        elif active_tab == 1: self.fn_add_files_to_list(all_paths)

    def show_help(self):
        HelpDialog(self.master, "help_title", "help_message")

    def open_language_settings(self):
        settings_win = tk.Toplevel(self.master); settings_win.title(lm.get_string("settings_title")); settings_win.transient(self.master); settings_win.grab_set()
        main_frame = ttk.Frame(settings_win, padding="20"); main_frame.pack(expand=True, fill='both')
        ttk.Label(main_frame, text=lm.get_string("settings_language_label")).pack(pady=(0, 10))
        lang_var = tk.StringVar(value=lm.current_language)
        for code, name in {"zh_TW": "繁體中文", "zh_CN": "简体中文", "en": "English", "ja": "日本語"}.items():
            ttk.Radiobutton(main_frame, text=name, variable=lang_var, value=code).pack(anchor='w')
        def apply_and_close():
            lm.set_language(lang_var.get()); self.update_ui_language(); settings_win.destroy()
        ttk.Button(main_frame, text=lm.get_string("settings_apply"), command=apply_and_close, style='Accent.TButton').pack(pady=(15, 0))
        center_window(settings_win)

    def update_ui_language(self):
        self.master.title(lm.get_string("window_title"))
        for tab, key in [(self.content_tab, "tab_file_conversion"), (self.filename_tab, "tab_filename_conversion"), (self.clipboard_tab, "tab_clipboard_conversion")]: self.notebook.tab(tab, text=lm.get_string(key))
        for btn, key in [(self.ct_import_files_btn, "import_files"), (self.ct_import_folder_btn, "import_folder"), (self.ct_s2t_radio, "s2t_radio"), 
                         (self.ct_t2s_radio, "t2s_radio"), (self.ct_custom_vocab_btn, "custom_conversions_manage"), (self.ct_output_folder_label, "output_folder_label"),
                         (self.ct_convert_checked_btn, "convert_checked_button"), (self.ct_convert_all_btn, "convert_all_button"), (self.ct_treeview, "treeview_header_filename"),
                         (self.ct_clear_list_btn, "clear_list"), (self.ct_remove_unchecked_btn, "remove_unchecked"), (self.ct_uncheck_selected_btn, "uncheck_selected_button"),
                         (self.ct_undo_btn, "undo"), (self.ct_original_encoding_label, "preview_original_label"), (self.ct_converted_label, "preview_converted_label"),
                         (self.ct_font_size_label, "font_size_label"), (self.fn_import_files_btn, "import_files"), (self.fn_import_folder_btn, "import_folder"),
                         (self.fn_clear_list_btn, "clear_list"), (self.fn_remove_unchecked_btn, "remove_unchecked"), (self.fn_uncheck_selected_btn, "uncheck_selected_button"),
                         (self.fn_undo_btn, "undo"), (self.fn_s2t_radio, "s2t_radio"), (self.fn_t2s_radio, "t2s_radio"), (self.fn_file_handling_label, "file_handling_label"),
                         (self.fn_move_radio, "move_radio"), (self.fn_copy_radio, "copy_radio"), (self.fn_output_folder_label, "output_folder_label"),
                         (self.fn_rename_checked_btn, "rename_checked_button"), (self.fn_rename_all_btn, "rename_all_button"), (self.cl_input_label, "input_content_label"),
                         (self.cl_output_label, "output_result_label"), (self.cl_s2t_btn, "s2t_radio"), (self.cl_t2s_btn, "t2s_radio"), (self.cl_paste_btn, "paste_button"),
                         (self.cl_copy_btn, "copy_result_button"), (self.cl_clear_btn, "clear_button"), (self.cl_undo_btn, "undo")]:
            if isinstance(btn, ttk.Treeview): btn.heading("name", text=lm.get_string(key))
            else: btn.config(text=lm.get_string(key))
        for cb in [self.ct_enable_custom_cb, self.ct_manual_encoding_cb, self.ct_custom_filename_cb, self.fn_enable_lang_detect_cb]: cb.update_language()
        self.fn_treeview.heading("original", text=lm.get_string("treeview_header_original")); self.fn_treeview.heading("preview", text=lm.get_string("treeview_header_preview"))
        Tooltip(self.help_button, "help_button_tooltip"); self.ct_update_file_count(); self.fn_update_file_count()

    def load_settings(self):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            lm.set_language(settings.get("language", "zh_TW"))
            self.last_import_path = settings.get("last_import_path", os.path.expanduser("~"))
            if not os.path.isdir(self.last_import_path): self.last_import_path = os.path.expanduser("~")
            self.ct_output_folder.set(settings.get("ct_output_folder", os.path.expanduser("~")))
            self.fn_output_folder.set(settings.get("fn_output_folder", ""))
            self.ct_font_size.set(settings.get("ct_font_size", DEFAULT_FONT_SIZE_PREVIEW))
            self.ct_initial_sash_pos = settings.get("ct_sash_pos", 0)
        except (FileNotFoundError, json.JSONDecodeError): pass
        self.update_ui_language(); self.ct_update_all_font_controls()

    def save_settings(self):
        settings = {}; 
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f: settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): pass
        
        settings.update({
            "language": lm.current_language, "last_import_path": self.last_import_path,
            "ct_output_folder": self.ct_output_folder.get(), "fn_output_folder": self.fn_output_folder.get(),
            "ct_font_size": self.ct_font_size.get()
        })
        if hasattr(self, 'main_pane') and self.main_pane.winfo_exists():
            settings["ct_sash_pos"] = self.main_pane.sashpos(0)
        
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f: json.dump(settings, f, indent=4)
        except Exception as e: print(f"Error saving settings: {e}")

    def create_content_converter_tab(self):
        self.ct_file_data = {}
        self.ct_selected_path = None
        self.ct_conversion_type = tk.StringVar(value='s2t')
        self.ct_enable_custom = tk.BooleanVar(value=True)
        self.ct_output_folder = tk.StringVar()
        self.ct_use_manual_encoding = tk.BooleanVar(value=False)
        self.ct_manual_encoding = tk.StringVar(value="utf-8")
        self.ct_encoding_options = ['utf-8', 'utf-8-sig', 'gbk', 'gb18030', 'big5', 'cp936']
        self.ct_enable_custom_filename = tk.BooleanVar(value=False)
        self.ct_filename_pattern = tk.StringVar(value="{original_name}")
        self.ct_font_size = tk.IntVar(value=DEFAULT_FONT_SIZE_PREVIEW)
        self.ct_custom_conversions = load_custom_conversions(self.master)
        self.ct_file_count_var = tk.StringVar(value="共 0 個檔案")

        self.main_pane = ttk.PanedWindow(self.content_tab, orient='horizontal')
        self.main_pane.pack(fill='both', expand=True)
        left_frame = ttk.Frame(self.main_pane, padding=5)
        self.main_pane.add(left_frame) 
        right_frame = ttk.Frame(self.main_pane, padding=5)
        self.main_pane.add(right_frame)
        
        self.main_pane.bind("<Configure>", self._on_pane_configure)
        
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1) 

        controls_frame = ttk.Frame(left_frame); controls_frame.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        tree_container = ttk.Frame(left_frame); tree_container.grid(row=1, column=0, sticky='nsew'); tree_container.grid_rowconfigure(0, weight=1); tree_container.grid_columnconfigure(0, weight=1)
        bottom_controls_frame = ttk.Frame(left_frame); bottom_controls_frame.grid(row=2, column=0, sticky='ew', pady=(5,0))
        
        row0 = ttk.Frame(controls_frame); row0.pack(fill='x', pady=3)
        self.ct_import_files_btn = ttk.Button(row0, text=lm.get_string("import_files"), command=self.ct_select_files, style='Accent.TButton'); self.ct_import_files_btn.pack(side='left', padx=(0,5))
        self.ct_import_folder_btn = ttk.Button(row0, text=lm.get_string("import_folder"), command=self.ct_select_folder, style='Accent.TButton'); self.ct_import_folder_btn.pack(side='left')
        row1 = ttk.Frame(controls_frame); row1.pack(fill='x', pady=3,ipady=2)
        self.ct_s2t_radio = ttk.Radiobutton(row1, text=lm.get_string("s2t_radio"), variable=self.ct_conversion_type, value='s2t', command=self.ct_trigger_preview_refresh); self.ct_s2t_radio.pack(side='left')
        self.ct_t2s_radio = ttk.Radiobutton(row1, text=lm.get_string("t2s_radio"), variable=self.ct_conversion_type, value='t2s', command=self.ct_trigger_preview_refresh); self.ct_t2s_radio.pack(side='left', padx=10)
        row2 = ttk.Frame(controls_frame); row2.pack(fill='x', pady=3, anchor='w');
        self.ct_enable_custom_cb = CustomCheckbutton(row2, variable=self.ct_enable_custom, text_key='enable_custom_toggle', command=self.ct_trigger_preview_refresh); self.ct_enable_custom_cb.pack(side='left');
        self.ct_custom_vocab_btn = ttk.Button(row2, text=lm.get_string("custom_conversions_manage"), command=self.ct_open_custom_conversions_manager); self.ct_custom_vocab_btn.pack(side='left', padx=10)
        row3 = ttk.Frame(controls_frame); row3.pack(fill='x', pady=3, anchor='w');
        self.ct_manual_encoding_cb = CustomCheckbutton(row3, variable=self.ct_use_manual_encoding, text_key='manual_encoding_toggle', command=self.ct_toggle_manual_encoding_option); self.ct_manual_encoding_cb.pack(side='left');
        self.ct_encoding_combobox = ttk.Combobox(row3, textvariable=self.ct_manual_encoding, values=self.ct_encoding_options, state='disabled', width=10); self.ct_encoding_combobox.pack(side='left', padx=5); self.ct_encoding_combobox.set('utf-8')
        self.ct_encoding_combobox.bind("<<ComboboxSelected>>", self.ct_trigger_preview_refresh)
        row4 = ttk.Frame(controls_frame); row4.pack(fill='x', pady=3);
        self.ct_output_folder_label = ttk.Label(row4, text=lm.get_string("output_folder_label")); self.ct_output_folder_label.pack(side='left')
        self.ct_output_folder_entry = ttk.Entry(row4, textvariable=self.ct_output_folder); self.ct_output_folder_entry.pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(row4, text="...", command=lambda: self.ct_output_folder.set(filedialog.askdirectory(parent=self.master, initialdir=self.last_import_path) or self.ct_output_folder.get()), width=4).pack(side='left')
        row5 = ttk.Frame(controls_frame); row5.pack(fill='x', pady=3, anchor='w');
        self.ct_custom_filename_cb = CustomCheckbutton(row5, variable=self.ct_enable_custom_filename, text_key='custom_filename_toggle', command=self.ct_toggle_custom_filename_entry); self.ct_custom_filename_cb.pack(side='left');
        self.ct_filename_entry = ttk.Entry(row5, textvariable=self.ct_filename_pattern, state='disabled'); self.ct_filename_entry.pack(side='left', fill='x', expand=True, padx=5)
        row6 = ttk.Frame(controls_frame); row6.pack(fill='x', pady=(8, 5))
        self.ct_convert_checked_btn = ttk.Button(row6, text=lm.get_string("convert_checked_button"), command=self.ct_start_checked_conversion, style='Accent.TButton'); self.ct_convert_checked_btn.pack(side='left')
        self.ct_convert_all_btn = ttk.Button(row6, text=lm.get_string("convert_all_button"), command=self.ct_start_all_conversion, style='Accent.TButton'); self.ct_convert_all_btn.pack(side='left', padx=5)
        
        self.ct_treeview = ttk.Treeview(tree_container, columns=("checked", "name"), show="headings", selectmode='extended')
        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.ct_treeview.yview); hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.ct_treeview.xview)
        self.ct_treeview.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.ct_treeview.grid(row=0, column=0, sticky='nsew'); vsb.grid(row=0, column=1, sticky='ns'); hsb.grid(row=1, column=0, columnspan=2, sticky='ew')
        
        list_btn_frame1 = ttk.Frame(bottom_controls_frame); list_btn_frame1.pack(fill='x', pady=(5,2))
        self.ct_clear_list_btn = ttk.Button(list_btn_frame1, text=lm.get_string("clear_list"), command=self.ct_clear_list); self.ct_clear_list_btn.pack(side='left')
        self.ct_remove_unchecked_btn = ttk.Button(list_btn_frame1, text=lm.get_string("remove_unchecked"), command=self.ct_remove_unchecked); self.ct_remove_unchecked_btn.pack(side='left', padx=5)
        self.ct_uncheck_selected_btn = ttk.Button(list_btn_frame1, text=lm.get_string("uncheck_selected_button"), command=self.ct_uncheck_selected); self.ct_uncheck_selected_btn.pack(side='left')

        list_btn_frame2 = ttk.Frame(bottom_controls_frame); list_btn_frame2.pack(fill='x')
        list_btn_frame2.grid_columnconfigure(1, weight=1)
        self.ct_file_count_label = ttk.Label(list_btn_frame2, textvariable=self.ct_file_count_var, anchor='w'); self.ct_file_count_label.grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.ct_undo_btn = ttk.Button(list_btn_frame2, text=lm.get_string("undo"), command=self.ct_undo_list_action); self.ct_undo_btn.grid(row=0, column=2, sticky='e')
        
        self.ct_treeview.heading("checked", text="☐", command=self.ct_toggle_all_checkboxes); self.ct_treeview.column("checked", width=60, anchor='center', stretch=False)
        self.ct_treeview.heading("name", text=lm.get_string("treeview_header_filename")); self.ct_treeview.column("name", width=1000, minwidth=250, stretch=False) 
        self.ct_treeview.bind("<<TreeviewSelect>>", self.ct_on_file_select); self.ct_treeview.bind("<Button-1>", self.ct_on_treeview_click); self.ct_treeview.bind("<Delete>", self.ct_delete_selected_items)
        self.ct_treeview.tag_configure('converted', foreground=COLOR_CONVERTED); self.ct_treeview.tag_configure('skipped', foreground=COLOR_SKIPPED); self.ct_treeview.tag_configure('non_chinese', foreground=COLOR_NON_CHINESE)
        
        preview_container = ttk.Frame(right_frame); preview_container.pack(fill='both', expand=True); preview_container.grid_rowconfigure(1, weight=1); preview_container.grid_columnconfigure(0, weight=1); preview_container.grid_columnconfigure(1, weight=1)
        self.ct_original_encoding_label = ttk.Label(preview_container, text=lm.get_string("preview_original_label"), font=TITLE_FONT); self.ct_original_encoding_label.grid(row=0, column=0, sticky='w', pady=(0,5))
        self.ct_original_text = scrolledtext.ScrolledText(preview_container, wrap='word', bg='white', fg=WORD_TEXT_DARK, relief="solid", bd=1, font=PREVIEW_FONT_BASE); self.ct_original_text.grid(row=1, column=0, sticky='nsew', padx=(0, 2)); self.ct_original_text.config(state='disabled')
        self.ct_converted_label = ttk.Label(preview_container, text=lm.get_string("preview_converted_label"), font=TITLE_FONT); self.ct_converted_label.grid(row=0, column=1, sticky='w', pady=(0,5))
        self.ct_converted_text = scrolledtext.ScrolledText(preview_container, wrap='word', bg='white', fg=WORD_TEXT_DARK, relief="solid", bd=1, font=PREVIEW_FONT_BASE); self.ct_converted_text.grid(row=1, column=1, sticky='nsew', padx=(2, 0)); self.ct_converted_text.config(state='disabled')
        font_size_frame = ttk.Frame(preview_container); font_size_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(5,0))
        self.ct_font_size_label = ttk.Label(font_size_frame, text=lm.get_string("font_size_label")); self.ct_font_size_label.pack(side='left', padx=(0,5))
        self.ct_font_size_slider = ttk.Scale(font_size_frame, from_=1, to=72, orient="horizontal", command=self.ct_on_font_slider_change); self.ct_font_size_slider.pack(side='left', fill='x', expand=True)
        self.ct_font_size_entry = ttk.Entry(font_size_frame, width=3); self.ct_font_size_entry.pack(side='left', padx=5)
        self.ct_font_size_entry.bind("<FocusOut>", self.ct_update_font_from_entry); self.ct_font_size_entry.bind("<Return>", self.ct_update_font_from_entry)
    
    def _on_pane_configure(self, event):
        if self.ct_sash_applied: return
        self.ct_sash_applied = True
        
        self.main_pane.unbind("<Configure>")

        if self.ct_initial_sash_pos > 0:
            target_pos = self.ct_initial_sash_pos
        else:
            target_pos = int(event.width * (1/3))
        
        try:
            self.main_pane.sashpos(0, target_pos)
        except tk.TclError:
             pass
            
    def create_filename_converter_tab(self):
        self.fn_file_data = {}
        self.fn_conversion_type = tk.StringVar(value='s2t')
        self.fn_output_folder = tk.StringVar()
        self.fn_operation_type = tk.StringVar(value='copy')
        self.fn_enable_lang_detect = tk.BooleanVar(value=True)
        self.fn_file_count_var = tk.StringVar(value="共 0 個檔案")
        
        top_frame = ttk.Frame(self.filename_tab); top_frame.pack(fill='x', pady=(0, 10))
        middle_frame = ttk.Frame(self.filename_tab); middle_frame.pack(fill='both', expand=True)
        bottom_frame = ttk.Frame(self.filename_tab); bottom_frame.pack(fill='x', pady=(10, 0))

        fn_top_btn_row1 = ttk.Frame(top_frame); fn_top_btn_row1.pack(fill='x', pady=(0, 2))
        self.fn_import_files_btn = ttk.Button(fn_top_btn_row1, text=lm.get_string("import_files"), command=self.fn_select_files, style='Accent.TButton'); self.fn_import_files_btn.pack(side='left', padx=(0, 5))
        self.fn_import_folder_btn = ttk.Button(fn_top_btn_row1, text=lm.get_string("import_folder"), command=self.fn_select_folder, style='Accent.TButton'); self.fn_import_folder_btn.pack(side='left')
        self.fn_undo_btn = ttk.Button(fn_top_btn_row1, text=lm.get_string("undo"), command=self.fn_undo_list_action); self.fn_undo_btn.pack(side='right')

        fn_top_btn_row2 = ttk.Frame(top_frame); fn_top_btn_row2.pack(fill='x', pady=(2, 0))
        self.fn_clear_list_btn = ttk.Button(fn_top_btn_row2, text=lm.get_string("clear_list"), command=self.fn_clear_list); self.fn_clear_list_btn.pack(side='left')
        self.fn_remove_unchecked_btn = ttk.Button(fn_top_btn_row2, text=lm.get_string("remove_unchecked"), command=self.fn_remove_unchecked); self.fn_remove_unchecked_btn.pack(side='left', padx=5)
        self.fn_uncheck_selected_btn = ttk.Button(fn_top_btn_row2, text=lm.get_string("uncheck_selected_button"), command=self.fn_uncheck_selected); self.fn_uncheck_selected_btn.pack(side='left')
        self.fn_file_count_label = ttk.Label(fn_top_btn_row2, textvariable=self.fn_file_count_var); self.fn_file_count_label.pack(side='right')
        
        middle_frame.grid_rowconfigure(0, weight=1); middle_frame.grid_columnconfigure(0, weight=1)
        self.fn_treeview = ttk.Treeview(middle_frame, columns=("checked", "original", "preview"), show="headings", selectmode='extended')
        self.fn_treeview.heading("checked", text="☐", command=self.fn_toggle_all_checkboxes); self.fn_treeview.column("checked", width=60, anchor='center', stretch=False)
        self.fn_treeview.heading("original", text=lm.get_string("treeview_header_original")); self.fn_treeview.column("original", width=600, minwidth=200, stretch=False) 
        self.fn_treeview.heading("preview", text=lm.get_string("treeview_header_preview")); self.fn_treeview.column("preview", width=600, minwidth=200, stretch=False) 
        self.fn_treeview.grid(row=0, column=0, sticky='nsew')
        self.fn_treeview.tag_configure('converted', foreground=COLOR_CONVERTED); self.fn_treeview.tag_configure('skipped', foreground=COLOR_SKIPPED); self.fn_treeview.tag_configure('non_chinese', foreground=COLOR_NON_CHINESE)
        fn_vsb = ttk.Scrollbar(middle_frame, orient="vertical", command=self.fn_treeview.yview); fn_vsb.grid(row=0, column=1, sticky='ns'); self.fn_treeview.configure(yscrollcommand=fn_vsb.set)
        fn_hsb = ttk.Scrollbar(middle_frame, orient="horizontal", command=self.fn_treeview.xview); fn_hsb.grid(row=1, column=0, columnspan=2, sticky='ew'); self.fn_treeview.configure(xscrollcommand=fn_hsb.set)
        self.fn_treeview.bind("<Button-1>", self.fn_on_treeview_click); self.fn_treeview.bind("<Delete>", self.fn_delete_selected_items)

        conversion_frame = ttk.Frame(bottom_frame); conversion_frame.pack(fill='x', pady=2)
        self.fn_s2t_radio = ttk.Radiobutton(conversion_frame, text=lm.get_string("s2t_radio"), variable=self.fn_conversion_type, value='s2t', command=self.fn_update_rename_preview); self.fn_s2t_radio.pack(side='left')
        self.fn_t2s_radio = ttk.Radiobutton(conversion_frame, text=lm.get_string("t2s_radio"), variable=self.fn_conversion_type, value='t2s', command=self.fn_update_rename_preview); self.fn_t2s_radio.pack(side='left', padx=10)
        self.fn_enable_lang_detect_cb = CustomCheckbutton(conversion_frame, text_key="enable_filename_lang_detect", variable=self.fn_enable_lang_detect, command=self.fn_update_rename_preview); self.fn_enable_lang_detect_cb.pack(side='left', padx=(20, 5))
        if not LANGDETECT_AVAILABLE: self.fn_enable_lang_detect_cb.config(state='disabled'); self.fn_enable_lang_detect.set(False)
        self.fn_file_handling_label = ttk.Label(conversion_frame, text=lm.get_string("file_handling_label")); self.fn_file_handling_label.pack(side='left', padx=(20, 5))
        self.fn_move_radio = ttk.Radiobutton(conversion_frame, text=lm.get_string("move_radio"), variable=self.fn_operation_type, value='move'); self.fn_move_radio.pack(side='left')
        self.fn_copy_radio = ttk.Radiobutton(conversion_frame, text=lm.get_string("copy_radio"), variable=self.fn_operation_type, value='copy'); self.fn_copy_radio.pack(side='left', padx=10)

        output_frame = ttk.Frame(bottom_frame); output_frame.pack(fill='x', pady=2)
        self.fn_output_folder_label = ttk.Label(output_frame, text=lm.get_string("output_folder_label")); self.fn_output_folder_label.pack(side='left');
        ttk.Entry(output_frame, textvariable=self.fn_output_folder).pack(side='left', fill='x', expand=True, padx=5)
        ttk.Button(output_frame, text="...", command=lambda: self.fn_output_folder.set(filedialog.askdirectory(parent=self.master, initialdir=self.last_import_path) or self.fn_output_folder.get()), width=4).pack(side='left')

        action_frame = ttk.Frame(bottom_frame); action_frame.pack(fill='x', pady=(5,0))
        self.fn_rename_checked_btn = ttk.Button(action_frame, text=lm.get_string("rename_checked_button"), command=self.fn_start_checked_rename_process, style='Accent.TButton'); self.fn_rename_checked_btn.pack(side='left')
        self.fn_rename_all_btn = ttk.Button(action_frame, text=lm.get_string("rename_all_button"), command=self.fn_start_all_rename_process, style='Accent.TButton'); self.fn_rename_all_btn.pack(side='left', padx=5)

    def create_clipboard_converter_tab(self):
        main_pane = ttk.PanedWindow(self.clipboard_tab, orient='horizontal'); main_pane.pack(fill='both', expand=True, pady=(10,0))
        input_frame = ttk.Frame(main_pane, padding=5); main_pane.add(input_frame, weight=1)
        output_frame = ttk.Frame(main_pane, padding=5); main_pane.add(output_frame, weight=1)
        self.cl_input_label = ttk.Label(input_frame, text=lm.get_string("input_content_label"), font=TITLE_FONT); self.cl_input_label.pack(anchor='w', pady=(0,5))
        self.cl_input_text = scrolledtext.ScrolledText(input_frame, wrap='word', height=10, width=50, font=PREVIEW_FONT_BASE); self.cl_input_text.pack(fill='both', expand=True)
        self.cl_output_label = ttk.Label(output_frame, text=lm.get_string("output_result_label"), font=TITLE_FONT); self.cl_output_label.pack(anchor='w', pady=(0,5))
        self.cl_output_text = scrolledtext.ScrolledText(output_frame, wrap='word', height=10, width=50, font=PREVIEW_FONT_BASE); self.cl_output_text.pack(fill='both', expand=True); self.cl_output_text.config(state='disabled')
        button_frame_top = ttk.Frame(self.clipboard_tab); button_frame_top.pack(fill='x', pady=(10, 2))
        self.cl_s2t_btn = ttk.Button(button_frame_top, text=lm.get_string("s2t_radio"), command=lambda: self.cl_start_conversion('s2t'), style='Accent.TButton'); self.cl_s2t_btn.pack(side='left')
        self.cl_t2s_btn = ttk.Button(button_frame_top, text=lm.get_string("t2s_radio"), command=lambda: self.cl_start_conversion('t2s'), style='Accent.TButton'); self.cl_t2s_btn.pack(side='left', padx=10)
        button_frame_bottom = ttk.Frame(self.clipboard_tab); button_frame_bottom.pack(fill='x', pady=(2, 0))
        self.cl_paste_btn = ttk.Button(button_frame_bottom, text=lm.get_string("paste_button"), command=self.cl_paste_from_clipboard); self.cl_paste_btn.pack(side='left')
        self.cl_copy_btn = ttk.Button(button_frame_bottom, text=lm.get_string("copy_result_button"), command=self.cl_copy_to_clipboard); self.cl_copy_btn.pack(side='left', padx=10)
        self.cl_clear_btn = ttk.Button(button_frame_bottom, text=lm.get_string("clear_button"), command=self.cl_clear_text); self.cl_clear_btn.pack(side='right', padx=10)
        self.cl_undo_btn = ttk.Button(button_frame_bottom, text=lm.get_string("undo"), command=self.cl_undo); self.cl_undo_btn.pack(side='right')

    def get_content_conversion_params(self):
        return {'conversion_type': self.ct_conversion_type.get(), 'cc_convert': self.cc_s2t if self.ct_conversion_type.get() == 's2t' else self.cc_t2s,
                'custom_conversions': self.ct_custom_conversions, 'enable_custom': self.ct_enable_custom.get(), 'output_folder': self.ct_output_folder.get(),
                'use_manual_encoding': self.ct_use_manual_encoding.get(), 'manual_encoding': self.ct_manual_encoding.get(),
                'filename_pattern': self.ct_filename_pattern.get() if self.ct_enable_custom_filename.get() else ""}

    def ct_update_file_count(self): self.ct_file_count_var.set(f"共 {len(self.ct_file_data)} 個檔案")
    def ct_select_files(self):
        if files := filedialog.askopenfilenames(title=lm.get_string("import_files"), filetypes=[("Text files", "*.txt")], parent=self.master, initialdir=self.last_import_path):
            self.last_import_path = os.path.dirname(files[0]); self.ct_add_files_to_list(list(files))
    def ct_select_folder(self):
        if folder := filedialog.askdirectory(title=lm.get_string("import_folder"), parent=self.master, initialdir=self.last_import_path):
            self.last_import_path = folder; self.ct_add_files_to_list([os.path.join(r, f) for r, _, fs in os.walk(folder) for f in fs if f.lower().endswith(".txt")])
    def ct_add_files_to_list(self, filepaths):
        if not filepaths: return
        self.ct_save_undo_state(); added = False
        for fpath in filepaths:
            if fpath not in self.ct_file_data: self.ct_file_data[fpath] = {"checked": True, "status": "none"}; added = True
        if added: self.ct_update_treeview(); self._ct_adjust_filename_column_width()
        elif filepaths: messagebox.showinfo(lm.get_string("info"), lm.get_string("all_files_in_list"), parent=self.master)
        self.ct_update_file_count()

    def _ct_adjust_filename_column_width(self):
        if not self.ct_file_data: self.ct_treeview.column("name", width=250, minwidth=250, stretch=False); return
        max_width = max(tkfont.Font(font=DEFAULT_FONT).measure(os.path.basename(fp)) for fp in self.ct_file_data.keys())
        self.ct_treeview.column("name", width=min(max(max_width + 30, 250), 1200), minwidth=250, stretch=False)

    def ct_update_treeview(self):
        self.ct_treeview.delete(*self.ct_treeview.get_children())
        for filepath, data in self.ct_file_data.items():
            tags, status = (), data.get("status", "none")
            if status == 'converted': tags = ('converted',)
            elif status == 'skipped_non_chinese': tags = ('non_chinese',)
            elif status.startswith('skipped'): tags = ('skipped',)
            self.ct_treeview.insert("", "end", iid=filepath, values=("☑" if data.get("checked", False) else "☐", os.path.basename(filepath)), tags=tags)
        self.ct_update_all_checkbox_status(); self._ct_adjust_filename_column_width()

    def ct_clear_list(self):
        if not self.ct_file_data: return
        if messagebox.askyesno(lm.get_string("confirm"), lm.get_string("confirm_clear_list"), parent=self.master):
            self.ct_save_undo_state(); self.ct_file_data.clear(); self.ct_update_treeview(); self.ct_clear_preview(); self.ct_update_file_count(); self._ct_adjust_filename_column_width()

    def ct_remove_unchecked(self):
        if not (unchecked_items := [fp for fp, d in self.ct_file_data.items() if not d["checked"]]):
            messagebox.showinfo(lm.get_string("info"), lm.get_string("no_files_for_action", scope=lm.get_string("scope_unchecked_files"), action=lm.get_string("action_remove")), parent=self.master); return
        if messagebox.askyesno(lm.get_string("confirm"), lm.get_string("confirm_remove_unchecked_files", count=len(unchecked_items)), parent=self.master):
            self.ct_save_undo_state(); self.ct_file_data = {fp: d for fp, d in self.ct_file_data.items() if d["checked"]}
            self.ct_update_treeview(); self.ct_clear_preview(); self.ct_update_file_count(); self._ct_adjust_filename_column_width()

    def ct_delete_selected_items(self, event=None):
        if not (selected_items := self.ct_treeview.selection()): return
        if messagebox.askyesno(lm.get_string("confirm"), lm.get_string("confirm_remove_selected_files", count=len(selected_items)), parent=self.master):
            self.ct_save_undo_state()
            for item_id in selected_items:
                if item_id in self.ct_file_data: del self.ct_file_data[item_id]
            self.ct_update_treeview(); self.ct_clear_preview(); self.ct_update_file_count()

    def ct_uncheck_selected(self):
        if not (selected_items := self.ct_treeview.selection()): messagebox.showinfo(lm.get_string("info"), lm.get_string("no_selection_to_uncheck"), parent=self.master); return
        self.ct_save_undo_state()
        for item_id in selected_items:
            if item_id in self.ct_file_data: self.ct_file_data[item_id]["checked"] = False
        self.ct_update_treeview()

    def ct_toggle_all_checkboxes(self):
        if not self.ct_file_data: return
        self.ct_save_undo_state()
        new_state = self.ct_treeview.heading("checked")['text'] != "☑"
        for item_id in self.ct_treeview.get_children():
            if item_id in self.ct_file_data: self.ct_file_data[item_id]["checked"] = new_state
        self.ct_update_treeview()
    def ct_update_all_checkbox_status(self):
        if not self.ct_file_data: self.ct_treeview.heading("checked", text="☐"); return
        vals = [d["checked"] for d in self.ct_file_data.values()]
        if all(vals): self.ct_treeview.heading("checked", text="☑")
        elif not any(vals): self.ct_treeview.heading("checked", text="☐")
        else: self.ct_treeview.heading("checked", text="▬")
    def ct_on_treeview_click(self, event):
        if self.ct_treeview.identify_region(event.x, event.y) == "cell" and self.ct_treeview.identify_column(event.x) == "#1":
            if item_id := self.ct_treeview.identify_row(event.y):
                self.ct_save_undo_state(); self.ct_file_data[item_id]["checked"] = not self.ct_file_data[item_id]["checked"]; self.ct_update_treeview()
    def ct_on_file_select(self, event):
        if (sel := self.ct_treeview.selection()) and (full_path := sel[0]) and self.ct_selected_path != full_path:
            self.ct_selected_path = full_path; self.ct_start_preview_thread(full_path)
    def ct_start_preview_thread(self, full_path):
        self.ct_clear_preview()
        self.ct_original_encoding_label.config(text=f"{lm.get_string('preview_original_label')} ({lm.get_string('processing_label_short')})...")
        self.ct_update_preview_text(self.ct_original_text, lm.get_string("processing_label_short"))
        threading.Thread(target=self.ct_run_preview_in_background, args=(full_path,), daemon=True).start()
    def ct_run_preview_in_background(self, full_path):
        original_content, detected_encoding = read_txt_file_with_encoding_detection(full_path, self.ct_use_manual_encoding.get(), self.ct_manual_encoding.get())
        preview_orig, preview_conv, final_err = "", "", detected_encoding
        if original_content is not None:
            if is_convertible_chinese(original_content):
                params = self.get_content_conversion_params()
                converted_content = convert_text(original_content, params['cc_convert'], params['conversion_type'], params['custom_conversions'], params['enable_custom'], self.cc_s2t, self.cc_t2s)
            else: converted_content = original_content
            def truncate(text): return text[:PREVIEW_CHAR_LIMIT] + f"\n\n--- ({lm.get_string('preview_truncated_msg', limit=PREVIEW_CHAR_LIMIT)}) ---" if len(text) > PREVIEW_CHAR_LIMIT else text
            preview_orig, preview_conv, final_err = truncate(original_content), truncate(converted_content), None
        self.master.after(0, self.ct_update_preview_ui, full_path, preview_orig, preview_conv, detected_encoding, final_err)
    def ct_update_preview_ui(self, full_path, preview_original, preview_converted, detected_encoding, error_msg):
        if self.ct_selected_path != full_path: return
        if error_msg:
            self.ct_original_encoding_label.config(text=f"{lm.get_string('preview_original_label')} ({lm.get_string('read_error_label')}: {error_msg})")
            self.ct_update_preview_text(self.ct_original_text, lm.get_string("read_error_content")); self.ct_update_preview_text(self.ct_converted_text, "")
        else:
            self.ct_original_encoding_label.config(text=f"{lm.get_string('preview_original_label')} ({lm.get_string('encoding_label')}: {detected_encoding})")
            self.ct_update_preview_text(self.ct_original_text, preview_original); self.ct_update_preview_text(self.ct_converted_text, preview_converted)
    def ct_update_preview_text(self, text_widget, content):
        text_widget.config(state='normal'); text_widget.delete('1.0', tk.END); text_widget.insert('1.0', content or ""); text_widget.config(state='disabled')
    def ct_clear_preview(self):
        self.ct_update_preview_text(self.ct_original_text, ""); self.ct_update_preview_text(self.ct_converted_text, ""); self.ct_original_encoding_label.config(text=lm.get_string("preview_original_label"))
    def ct_start_checked_conversion(self): self.ct_start_conversion_thread([fp for fp, d in self.ct_file_data.items() if d["checked"]], "scope_checked_files")
    def ct_start_all_conversion(self): self.ct_start_conversion_thread(list(self.ct_file_data.keys()), "scope_all_files")
    def ct_start_conversion_thread(self, filepaths, scope_key):
        if not filepaths: messagebox.showwarning(lm.get_string("warning"), lm.get_string("no_files_for_action", scope=lm.get_string(scope_key), action=lm.get_string("action_convert")), parent=self.master); return
        if not (self.ct_output_folder.get() and os.path.isdir(self.ct_output_folder.get())): messagebox.showwarning(lm.get_string("warning"), lm.get_string("invalid_output_folder"), parent=self.master); return
        for path in filepaths:
            if path in self.ct_file_data: self.ct_file_data[path]['status'] = 'none'
        self.ct_update_treeview()
        progress_dialog = ProgressDialog(self.master, "tab_file_conversion", len(filepaths))
        threading.Thread(target=process_content_background, args=(self, filepaths, progress_dialog, self.ct_finish_conversion), daemon=True).start()
    def ct_finish_conversion(self, success, fail, out_folder, preview_data, was_cancelled, results):
        msg = lm.get_string("task_cancelled_msg", success=success, fail=fail) if was_cancelled else lm.get_string("task_complete_msg", success=success, fail=fail, folder=out_folder)
        title = lm.get_string("task_cancelled") if was_cancelled else lm.get_string("task_complete")
        messagebox.showinfo(title, msg, parent=self.master)
        for path, status in results.items():
            if path in self.ct_file_data: self.ct_file_data[path]['status'] = status
        self.ct_update_treeview()
        if preview_data and preview_data[0] is not None:
            self.ct_original_encoding_label.config(text=lm.get_string("preview_original_label_last_conversion"))
            self.ct_update_preview_text(self.ct_original_text, preview_data[0]); self.ct_update_preview_text(self.ct_converted_text, preview_data[1])
    def ct_save_undo_state(self): self.ct_undo_stack.append(copy.deepcopy(self.ct_file_data))
    def ct_undo_list_action(self):
        if not self.ct_undo_stack: messagebox.showinfo(lm.get_string("undo"), lm.get_string("nothing_to_undo"), parent=self.master); return
        self.ct_file_data = self.ct_undo_stack.pop(); self.ct_update_treeview(); self.ct_update_file_count()
    def ct_update_font_from_entry(self, event=None):
        try: new_size = int(self.ct_font_size_entry.get())
        except (ValueError, tk.TclError): new_size = DEFAULT_FONT_SIZE_PREVIEW
        self.ct_font_size.set(max(1, min(72, new_size))); self.ct_update_all_font_controls()
    def ct_on_font_slider_change(self, value): self.ct_font_size.set(round(float(value))); self.ct_update_all_font_controls()
    def ct_update_all_font_controls(self, *args):
        size = self.ct_font_size.get()
        new_font = (DEFAULT_FONT_FAMILY, size)
        self.ct_original_text.config(font=new_font); self.ct_converted_text.config(font=new_font)
        if hasattr(self, 'ct_font_size_slider') and round(self.ct_font_size_slider.get()) != size: self.ct_font_size_slider.set(size)
        if hasattr(self, 'ct_font_size_entry') and self.ct_font_size_entry.get() != str(size): self.ct_font_size_entry.delete(0, tk.END); self.ct_font_size_entry.insert(0, str(size))
    def ct_open_custom_conversions_manager(self): CustomConversionsManager(self.master, self.ct_custom_conversions, self.ct_update_custom_conversions)
    def ct_update_custom_conversions(self, new_dict): self.ct_custom_conversions = new_dict; save_custom_conversions(new_dict, self.master); self.ct_trigger_preview_refresh()
    def ct_trigger_preview_refresh(self, *args):
        if self.ct_selected_path: self.ct_start_preview_thread(self.ct_selected_path)
    def ct_toggle_manual_encoding_option(self, *args): self.ct_encoding_combobox.config(state='readonly' if self.ct_use_manual_encoding.get() else 'disabled'); self.ct_trigger_preview_refresh()
    def ct_toggle_custom_filename_entry(self, *args):
        state = 'normal' if self.ct_enable_custom_filename.get() else 'disabled'
        self.ct_filename_entry.config(state=state)
        if state == 'normal' and not self.ct_filename_pattern.get(): self.ct_filename_pattern.set("{original_name}")
            
    def fn_update_file_count(self): self.fn_file_count_var.set(f"共 {len(self.fn_file_data)} 個檔案")
    def fn_select_files(self): 
        if files := filedialog.askopenfilenames(title=lm.get_string("import_files"), parent=self.master, initialdir=self.last_import_path):
            self.last_import_path = os.path.dirname(files[0]); self.fn_add_files_to_list(list(files))
    def fn_select_folder(self):
        if folder := filedialog.askdirectory(title=lm.get_string("import_folder"), parent=self.master, initialdir=self.last_import_path):
            self.last_import_path = folder
            files_to_add = [os.path.join(r, f) for r, _, fs in os.walk(folder) for f in fs if os.path.isfile(os.path.join(r, f))]
            self.fn_add_files_to_list(files_to_add)
    def fn_add_files_to_list(self, filepaths):
        if not filepaths: return
        self.fn_save_undo_state(); added = False
        for fpath in filepaths:
            if fpath not in self.fn_file_data: self.fn_file_data[fpath] = {"checked": True, "status": "none"}; added = True
        if added: self.fn_update_rename_preview(); self._fn_adjust_filename_columns_width()
        elif filepaths: messagebox.showinfo(lm.get_string("info"), lm.get_string("all_files_in_list"), parent=self.master)
        self.fn_update_file_count()

    def _fn_adjust_filename_columns_width(self):
        if not self.fn_file_data:
            self.fn_treeview.column("original", width=200, minwidth=200)
            self.fn_treeview.column("preview", width=200, minwidth=200)
            return

        font = tkfont.Font(font=DEFAULT_FONT)
        cc = self.cc_s2t if self.fn_conversion_type.get() == 's2t' else self.cc_t2s
        
        max_orig_width = 0
        max_prev_width = 0

        for path in self.fn_file_data.keys():
            basename = os.path.basename(path)
            
            if os.path.isdir(path):
                display_name = f"[資料夾] {basename}"
            else:
                name, ext = os.path.splitext(basename)
                file_ext = ext.replace('.', '').lower()
                display_name = f"[{file_ext}] {basename}" if file_ext else f"[檔案] {basename}"
            max_orig_width = max(max_orig_width, font.measure(display_name))
            
            name_to_convert, ext = os.path.splitext(basename)
            if os.path.isdir(path):
                 name_to_convert, ext = basename, ""
            
            preview_name = cc.convert(name_to_convert) + ext
            max_prev_width = max(max_prev_width, font.measure(preview_name))

        self.fn_treeview.column("original", width=min(max(max_orig_width + 30, 200), 1200), minwidth=200)
        self.fn_treeview.column("preview", width=min(max(max_prev_width + 30, 200), 1200), minwidth=200)

    def fn_update_rename_preview(self):
        self.fn_treeview.delete(*self.fn_treeview.get_children())
        cc = self.cc_s2t if self.fn_conversion_type.get() == 's2t' else self.cc_t2s
        detect_language = self.fn_enable_lang_detect.get()
        for path, data in self.fn_file_data.items():
            basename = os.path.basename(path)
            
            display_name = ""
            if os.path.isdir(path):
                name, ext = basename, ""
                display_name = f"[資料夾] {basename}"
            else:
                name, ext = os.path.splitext(basename)
                file_ext = ext.replace('.', '').lower()
                display_name = f"[{file_ext}] {basename}" if file_ext else f"[檔案] {basename}"
                
            checkbox = "☑" if data["checked"] else "☐"; tags, status = (), data.get("status", "none")
            is_convertible = True
            if status == 'converted': tags = ('converted',)
            elif status == 'skipped_non_chinese': tags, is_convertible = ('non_chinese',), False
            elif status.startswith('skipped'): tags = ('skipped',)
            elif status == 'none' and detect_language and not is_convertible_chinese(name): tags, is_convertible = ('non_chinese',), False
            
            new_name = (cc.convert(name) + ext) if is_convertible else basename
            self.fn_treeview.insert("", "end", iid=path, values=(checkbox, display_name, new_name), tags=tags)
        self.fn_update_all_checkbox_status(); self._fn_adjust_filename_columns_width()

    def fn_clear_list(self):
        if not self.fn_file_data: return
        if messagebox.askyesno(lm.get_string("confirm"), lm.get_string("confirm_clear_list"), parent=self.master):
            self.fn_save_undo_state(); self.fn_file_data.clear(); self.fn_update_rename_preview(); self.fn_update_file_count(); self._fn_adjust_filename_columns_width()
    
    def fn_remove_unchecked(self):
        if not (unchecked_items := [fp for fp, d in self.fn_file_data.items() if not d["checked"]]):
            messagebox.showinfo(lm.get_string("info"), lm.get_string("no_files_for_action", scope=lm.get_string("scope_unchecked_files"), action=lm.get_string("action_remove")), parent=self.master); return
        if messagebox.askyesno(lm.get_string("confirm"), lm.get_string("confirm_remove_unchecked_files", count=len(unchecked_items)), parent=self.master):
            self.fn_save_undo_state(); self.fn_file_data = {fp: d for fp, d in self.fn_file_data.items() if d["checked"]}
            self.fn_update_rename_preview(); self.fn_update_file_count(); self._fn_adjust_filename_columns_width()
            
    def fn_delete_selected_items(self, event=None):
        if not (selected_items := self.fn_treeview.selection()): return
        if messagebox.askyesno(lm.get_string("confirm"), lm.get_string("confirm_remove_selected_files", count=len(selected_items)), parent=self.master):
            self.fn_save_undo_state()
            for item_id in selected_items:
                if item_id in self.fn_file_data: del self.fn_file_data[item_id]
            self.fn_update_rename_preview(); self.fn_update_file_count()

    def fn_uncheck_selected(self):
        if not (selected_items := self.fn_treeview.selection()): messagebox.showinfo(lm.get_string("info"), lm.get_string("no_selection_to_uncheck"), parent=self.master); return
        self.fn_save_undo_state()
        for item_id in selected_items:
            if item_id in self.fn_file_data: self.fn_file_data[item_id]["checked"] = False
        self.fn_update_rename_preview()

    def fn_toggle_all_checkboxes(self):
        if not self.fn_file_data: return
        self.fn_save_undo_state()
        new_state = self.fn_treeview.heading("checked")['text'] != "☑"
        for item_id in self.fn_treeview.get_children():
            if item_id in self.fn_file_data: self.fn_file_data[item_id]["checked"] = new_state
        self.fn_update_rename_preview()
    def fn_update_all_checkbox_status(self):
        if not self.fn_file_data: self.fn_treeview.heading("checked", text="☐"); return
        vals = [d["checked"] for d in self.fn_file_data.values()]
        if all(vals): self.fn_treeview.heading("checked", text="☑")
        elif not any(vals): self.fn_treeview.heading("checked", text="☐")
        else: self.fn_treeview.heading("checked", text="▬")
    def fn_on_treeview_click(self, event):
        if self.fn_treeview.identify_region(event.x, event.y) == "cell" and self.fn_treeview.identify_column(event.x) == "#1":
            if item_id := self.fn_treeview.identify_row(event.y):
                self.fn_save_undo_state(); self.fn_file_data[item_id]["checked"] = not self.fn_file_data[item_id]["checked"]; self.fn_update_rename_preview()
    def fn_start_rename_process(self, filepaths):
        if not filepaths: messagebox.showwarning(lm.get_string("warning"), lm.get_string("no_files_for_action", scope=lm.get_string('scope_checked_files'), action=lm.get_string('action_rename')), parent=self.master); return
        output_folder = self.fn_output_folder.get()
        if not output_folder or not os.path.isdir(output_folder): messagebox.showwarning(lm.get_string("warning"), lm.get_string("invalid_output_folder"), parent=self.master); return
        for path in filepaths:
            if path in self.fn_file_data: self.fn_file_data[path]['status'] = 'none'
        self.fn_update_rename_preview()
        operation_type, detect_language = self.fn_operation_type.get(), self.fn_enable_lang_detect.get()
        progress_dialog = ProgressDialog(self.master, "tab_filename_conversion", len(filepaths))
        threading.Thread(target=process_filenames_background, args=(self, filepaths, self.fn_conversion_type.get(), output_folder, operation_type, detect_language, progress_dialog, self.fn_finish_process), daemon=True).start()
    def fn_start_checked_rename_process(self): self.fn_start_rename_process([fp for fp, d in self.fn_file_data.items() if d["checked"]])
    def fn_start_all_rename_process(self): self.fn_start_rename_process(list(self.fn_file_data.keys()))
    def fn_finish_process(self, success, fail, out_folder, was_cancelled, operation_type, results):
        action_msg_key = 'action_moved' if operation_type == 'move' else 'action_copied'
        title = lm.get_string("task_cancelled") if was_cancelled else lm.get_string("task_complete")
        msg = lm.get_string("task_cancelled_msg", success=success, fail=fail) if was_cancelled else lm.get_string("task_complete_msg_rename", action=lm.get_string(action_msg_key), success=success, fail=fail, folder=out_folder)
        messagebox.showinfo(title, msg, parent=self.master)
        self.fn_save_undo_state(); temp_data = {}
        for old_path, result in results.items():
            if isinstance(result, dict) and result.get('status') == 'converted':
                if operation_type == 'move':
                    new_path = result['new_path']
                    if old_path in self.fn_file_data: temp_data[new_path] = {**self.fn_file_data[old_path], 'status': 'converted'}
                elif old_path in self.fn_file_data: self.fn_file_data[old_path]['status'] = 'converted'
            elif old_path in self.fn_file_data: self.fn_file_data[old_path]['status'] = result if isinstance(result, str) else 'failed'
        if operation_type == 'move':
            moved_paths = [p for p, r in results.items() if isinstance(r, dict) and r.get('status') == 'converted']
            for p in moved_paths:
                if p in self.fn_file_data: del self.fn_file_data[p]
            self.fn_file_data.update(temp_data)
        self.fn_update_rename_preview()
    def fn_save_undo_state(self): self.fn_undo_stack.append(copy.deepcopy(self.fn_file_data))
    def fn_undo_list_action(self):
        if not self.fn_undo_stack: messagebox.showinfo(lm.get_string("undo"), lm.get_string("nothing_to_undo"), parent=self.master); return
        self.fn_file_data = self.fn_undo_stack.pop(); self.fn_update_rename_preview(); self.fn_update_file_count()
        
    def cl_save_undo_state(self): self.cl_undo_stack.append((self.cl_input_text.get("1.0", tk.END), self.cl_output_text.get("1.0", tk.END)))
    def cl_start_conversion(self, direction):
        self.cl_save_undo_state()
        if not (input_text := self.cl_input_text.get("1.0", tk.END).strip()): return
        cc_instance = self.cc_s2t if direction == 's2t' else self.cc_t2s
        progress_dialog = ProgressDialog(self.master, "processing_label", mode='indeterminate', min_duration=0.4)
        threading.Thread(target=self.cl_run_conversion_in_background, args=(input_text, cc_instance, progress_dialog), daemon=True).start()
    def cl_run_conversion_in_background(self, text, cc_instance, dialog):
        try: converted_text = cc_instance.convert(text)
        except Exception as e: converted_text = f"{lm.get_string('conversion_error')}: {e}"
        if not dialog.cancel_event.is_set(): self.master.after(0, self.cl_finish_conversion, converted_text, dialog)
    def cl_finish_conversion(self, converted_text, dialog):
        self.cl_output_text.config(state='normal'); self.cl_output_text.delete('1.0', tk.END); self.cl_output_text.insert('1.0', converted_text); self.cl_output_text.config(state='disabled')
        dialog.close()
    def cl_clear_text(self):
        self.cl_save_undo_state(); self.cl_input_text.delete('1.0', tk.END)
        self.cl_output_text.config(state='normal'); self.cl_output_text.delete('1.0', tk.END); self.cl_output_text.config(state='disabled')
    def cl_undo(self):
        if not self.cl_undo_stack: messagebox.showinfo(lm.get_string("undo"), lm.get_string("nothing_to_undo"), parent=self.master); return
        last_input, last_output = self.cl_undo_stack.pop()
        self.cl_input_text.delete('1.0', tk.END); self.cl_input_text.insert('1.0', last_input)
        self.cl_output_text.config(state='normal'); self.cl_output_text.delete('1.0', tk.END); self.cl_output_text.insert('1.0', last_output); self.cl_output_text.config(state='disabled')
    def cl_paste_from_clipboard(self):
        try:
            self.cl_save_undo_state(); self.cl_input_text.delete('1.0', tk.END); self.cl_input_text.insert('1.0', self.master.clipboard_get())
        except tk.TclError: messagebox.showwarning(lm.get_string("paste_failed"), lm.get_string("paste_no_text"), parent=self.master)
    def cl_copy_to_clipboard(self):
        if not (text_to_copy := self.cl_output_text.get("1.0", tk.END).strip()): messagebox.showwarning(lm.get_string("copy_failed"), lm.get_string("copy_no_text"), parent=self.master); return
        self.master.clipboard_clear(); self.master.clipboard_append(text_to_copy); messagebox.showinfo(lm.get_string("copy_success"), lm.get_string("copy_success_msg"), parent=self.master)

# --- 程式執行入口 ---
if __name__ == "__main__":
    root = tkdnd.Tk()
    try:
        s = ttk.Style(root)
        if 'clam' in s.theme_names(): s.theme_use("clam")
    except tk.TclError: print("無法使用 'clam' 主題，將使用預設主题。")
    app = ConverterApp(root)
    root.state('zoomed')
    root.mainloop()