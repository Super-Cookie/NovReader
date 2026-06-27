"""主窗口"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import subprocess

from novel_reader.config import (
    DEFAULT_WIN_WIDTH, DEFAULT_WIN_HEIGHT, MIN_WIN_WIDTH, MIN_WIN_HEIGHT,
    WINDOW_BG, ACCENT_COLOR, ENABLE_MULTI_TAB, AUTO_RESTORE_LAST_FILES,
    KEY_OPEN_FILE, KEY_CLOSE_TAB, KEY_NEW_WINDOW,
)
from novel_reader.utils.file_utils import (
    load_config, save_config, add_recent_file, get_recent_files,
    save_last_open_files, get_last_open_files,
    save_window_geometry, load_window_geometry,
    save_progress, load_progress,
    save_font_size, load_font_size,
    save_text_indent, load_text_indent,
)
from novel_reader.parser.chapter_parser import parse_novel_file
from novel_reader.ui.home_page import HomePage
from novel_reader.ui.reader_view import ReaderView
from novel_reader.ui.toc_panel import TocPanel
from novel_reader.ui.bottom_nav import BottomNav


class TabData:
    """标签页数据"""
    def __init__(self, book, reader_view, toc_panel, filepath):
        self.book = book
        self.reader_view = reader_view
        self.toc_panel = toc_panel
        self.filepath = filepath
        self.current_chapter = 0


class MainWindow:
    """主窗口 - 支持多标签页和多窗口"""

    _windows = []

    def __init__(self, filepath=None):
        self.root = tk.Tk()
        self.root.title("NovReader")
        self.root.configure(bg=WINDOW_BG)

        # 任务栏图标
        icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        geom = load_window_geometry()
        if geom:
            try:
                self.root.geometry(geom)
            except:
                self.root.geometry(f"{DEFAULT_WIN_WIDTH}x{DEFAULT_WIN_HEIGHT}")
        else:
            self.root.geometry(f"{DEFAULT_WIN_WIDTH}x{DEFAULT_WIN_HEIGHT}")
        self.root.minsize(MIN_WIN_WIDTH, MIN_WIN_HEIGHT)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Configure>", self._on_configure)

        self.main_frame = tk.Frame(self.root, bg=WINDOW_BG)
        self.main_frame.pack(fill="both", expand=True)

        self._build_toolbar()

        self.tabs = []
        self.current_tab_index = -1

        if ENABLE_MULTI_TAB:
            self.notebook = ttk.Notebook(self.main_frame)
            self.notebook.pack(fill="both", expand=True)
            self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
            self.notebook.enable_traversal()
        else:
            self.notebook = None

        self.root.bind(KEY_OPEN_FILE, lambda e: self.open_file())
        self.root.bind(KEY_NEW_WINDOW, lambda e: self.new_window())
        if ENABLE_MULTI_TAB:
            self.root.bind(KEY_CLOSE_TAB, lambda e: self.close_current_tab())

        self._init_home_page()

        if filepath and os.path.exists(filepath):
            self.root.after(100, lambda: self.open_file(filepath))
        else:
            self.root.after(100, self._auto_restore_files)

        MainWindow._windows.append(self)

    def _build_toolbar(self):
        """macOS 风格工具栏"""
        self.toolbar = tk.Frame(self.root, bg="#E8E8EA", height=44)
        self.toolbar.pack(fill="x", side="top", before=self.main_frame)
        self.toolbar.pack_propagate(False)

        toolbar_inner = tk.Frame(self.toolbar, bg="#E8E8EA")
        toolbar_inner.pack(fill="both", expand=True, padx=12, pady=4)

        btn_style = {
            "font": ("Microsoft YaHei UI", 11),
            "bg": "#E8E8EA",
            "fg": "#1D1D1F",
            "borderwidth": 0,
            "padx": 12,
            "pady": 4,
            "cursor": "hand2",
        }

        self.tb_open_btn = tk.Label(toolbar_inner, text="\u2318O  打开", **btn_style)
        self.tb_open_btn.pack(side="left", padx=2)
        self.tb_open_btn.bind("<Button-1>", lambda e: self.open_file())

        self.tb_recent_btn = tk.Label(toolbar_inner, text="\u2318R  最近", **btn_style)
        self.tb_recent_btn.pack(side="left", padx=2)
        self.tb_recent_btn.bind("<Button-1>", lambda e: self._show_recent_popup())

        sep1 = tk.Frame(toolbar_inner, bg="#C0C0C4", width=1)
        sep1.pack(side="left", fill="y", padx=8, pady=4)

        self.tb_zoom_out = tk.Label(toolbar_inner, text="A\u207B", **btn_style)
        self.tb_zoom_out.pack(side="left", padx=2)
        self.tb_zoom_out.bind("<Button-1>", lambda e: self._zoom(-1))

        self.tb_zoom_in = tk.Label(toolbar_inner, text="A\u207A", **btn_style)
        self.tb_zoom_in.pack(side="left", padx=2)
        self.tb_zoom_in.bind("<Button-1>", lambda e: self._zoom(1))

        self.tb_title_label = tk.Label(
            toolbar_inner, text="",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg="#E8E8EA", fg="#1D1D1F",
        )
        self.tb_title_label.pack(side="right", padx=16)

        for lbl in [self.tb_open_btn, self.tb_recent_btn,
                     self.tb_zoom_out, self.tb_zoom_in]:
            lbl.bind("<Enter>", lambda e, l=lbl: l.configure(bg="#D1D1D4"))
            lbl.bind("<Leave>", lambda e, l=lbl: l.configure(bg="#E8E8EA"))

    def _show_recent_popup(self):
        """显示最近打开文件的弹出菜单"""
        recent_files = get_recent_files()
        if not recent_files:
            return

        popup = tk.Menu(self.root, tearoff=0)
        for fp in recent_files[:10]:
            name = os.path.basename(fp)
            popup.add_command(
                label=name,
                font=("Microsoft YaHei UI", 11),
                command=lambda f=fp: self.open_file(f),
            )
        popup.add_separator()
        popup.add_command(label="清除记录", font=("Microsoft YaHei UI", 10),
                          command=lambda: self._clear_recent())

        try:
            x = self.tb_recent_btn.winfo_rootx()
            y = self.tb_recent_btn.winfo_rooty() + self.tb_recent_btn.winfo_height()
            popup.tk_popup(x, y)
        finally:
            popup.grab_release()

    def _clear_recent(self):
        """清除最近打开记录"""
        from novel_reader.utils.file_utils import save_config
        config = load_config()
        config["recent_files"] = []
        save_config(config)

    def _init_home_page(self):
        self.home_page = HomePage(
            self.main_frame,
            on_open_file=self.open_file,
            on_open_recent=self.open_file,
            on_new_window=self.new_window,
        )
        self.home_page.pack(fill="both", expand=True)

    def _auto_restore_files(self):
        if not AUTO_RESTORE_LAST_FILES:
            return
        last_files = get_last_open_files()
        if last_files:
            for fp in last_files:
                if os.path.exists(fp):
                    self.open_file(fp)
                    break

    def open_file(self, filepath=None):
        if not filepath:
            filepath = filedialog.askopenfilename(
                title="打开小说文件",
                filetypes=[("小说文件", "*.nov"), ("所有文件", "*.*")]
            )
        if not filepath or not os.path.exists(filepath):
            return

        # 标准化路径，用于去重比较
        norm_path = os.path.normcase(os.path.normpath(os.path.abspath(filepath)))

        # 如果该文件已在当前窗口打开，切换到已有标签页
        for i, tab in enumerate(self.tabs):
            tab_norm = os.path.normcase(os.path.normpath(os.path.abspath(tab.filepath)))
            if tab_norm == norm_path:
                if ENABLE_MULTI_TAB and self.notebook:
                    self.notebook.select(i)
                else:
                    # 单标签模式：已显示的就是该文件，无需操作
                    pass
                # 确保恢复到之前的阅读进度
                progress = load_progress(filepath)
                if progress:
                    idx = progress.get("chapter_index", 0)
                    scroll_pos = progress.get("scroll_pos", 0)
                    tab.reader_view.render_chapter(idx)
                    if scroll_pos > 0:
                        tab.reader_view.set_scroll_position(scroll_pos)
                return

        try:
            book = parse_novel_file(filepath)
        except Exception as e:
            messagebox.showerror("错误", f"无法解析文件:\n{e}")
            return

        if book.chapter_count == 0:
            messagebox.showwarning(
                "解析结果",
                f"'{os.path.basename(filepath)}' 中未识别到任何章节内容。\n\n"
                "可能的原因：\n"
                "• 文件为空或格式异常\n"
                "• 文件编码不是 UTF-8 / GBK\n\n"
                "文件将作为纯文本显示。",
            )
            return

        add_recent_file(filepath)
        self.root.title(f"{book.title} - NovReader")
        self.tb_title_label.configure(text=book.title)

        self.home_page.pack_forget()

        self._create_tab(book, filepath)

    def _create_tab(self, book, filepath):
        if ENABLE_MULTI_TAB and self.notebook:
            tab_frame = tk.Frame(self.notebook, bg=WINDOW_BG)
            tab_frame.pack(fill="both", expand=True)
            self.notebook.add(tab_frame, text=book.title)
            self.notebook.select(tab_frame)
            parent = tab_frame
        else:
            for child in self.main_frame.winfo_children():
                if child != self.home_page:
                    child.destroy()
            # 单标签模式：旧标签的 widgets 已销毁，清理 TabData 避免 _on_close 出错
            self.tabs.clear()
            parent = self.main_frame

        reader_view = ReaderView(
            parent,
            book,
            on_chapter_change=self._on_chapter_change,
            on_toc_toggle=lambda: self._toggle_toc(len(self.tabs) - 1),
            font_size=load_font_size(),
            indent_chars=load_text_indent(),
        )

        toc_panel = TocPanel(parent, book, on_chapter_select=self._on_toc_select)

        bottom_nav = BottomNav(
            parent,
            on_prev=lambda: reader_view.navigate(-1),
            on_next=lambda: reader_view.navigate(1),
            on_toc=lambda: self._toggle_toc(len(self.tabs) - 1),
        )

        bottom_nav.pack(fill="x", side="bottom")
        reader_view.pack(fill="both", expand=True)

        tab_data = TabData(book, reader_view, toc_panel, filepath)

        idx = 0
        scroll_pos = 0
        progress = load_progress(filepath)
        if progress:
            idx = progress.get("chapter_index", 0)
            scroll_pos = progress.get("scroll_pos", 0)

        reader_view.render_chapter(idx)
        if scroll_pos > 0:
            reader_view.set_scroll_position(scroll_pos)
        self._update_bottom_info(tab_data)

        self.tabs.append(tab_data)
        self.current_tab_index = len(self.tabs) - 1

    def _on_chapter_change(self, chapter_index, scroll_pos):
        if self.current_tab_index < 0:
            return
        tab = self.tabs[self.current_tab_index]
        tab.current_chapter = chapter_index
        save_progress(tab.filepath, chapter_index, scroll_pos)
        self._update_bottom_info(tab)

    def _update_bottom_info(self, tab):
        try:
            from novel_reader.utils.chinese_num import format_chapter_name
            ch = tab.book.get_chapter(tab.current_chapter)
            if ch:
                title = format_chapter_name(ch.title)
                volume_info = tab.book.get_chapter_volume_info(tab.current_chapter)
                bottom_nav = None
                for child in tab.reader_view.master.winfo_children():
                    if isinstance(child, BottomNav):
                        bottom_nav = child
                        break
                if bottom_nav:
                    bottom_nav.update_info(
                        tab.current_chapter,
                        tab.book.chapter_count,
                        title,
                        volume_info,
                    )
                    bottom_nav.update_buttons(
                        tab.current_chapter > 0,
                        tab.current_chapter < tab.book.chapter_count - 1,
                    )
        except Exception:
            pass

    def _toggle_toc(self, tab_index):
        if tab_index < 0 or tab_index >= len(self.tabs):
            return
        tab = self.tabs[tab_index]
        if tab.toc_panel.is_visible():
            tab.toc_panel.hide()
            tab.reader_view.text_widget.focus_set()
        else:
            tab.toc_panel.show(tab.current_chapter)

    def _on_toc_select(self, chapter_index):
        if self.current_tab_index < 0:
            return
        tab = self.tabs[self.current_tab_index]
        tab.reader_view.render_chapter(chapter_index)
        tab.current_chapter = chapter_index
        save_progress(tab.filepath, chapter_index, 0)
        self._update_bottom_info(tab)
        tab.reader_view.text_widget.focus_set()

    def _on_tab_changed(self, event=None):
        if self.notebook:
            try:
                self.current_tab_index = self.notebook.index(self.notebook.select())
            except:
                pass

    def close_current_tab(self):
        if not ENABLE_MULTI_TAB or not self.tabs:
            return
        if self.current_tab_index >= 0:
            self.tabs[self.current_tab_index].toc_panel.destroy()
            self.tabs.pop(self.current_tab_index)
            if self.notebook:
                self.notebook.forget(self.current_tab_index)
            if not self.tabs:
                self._init_home_page()
                self.root.title("NovReader")

    def new_window(self):
        subprocess.Popen([sys.executable, sys.argv[0]], creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)

    def _zoom(self, direction):
        if self.current_tab_index >= 0:
            tab = self.tabs[self.current_tab_index]
            if direction > 0:
                tab.reader_view.zoom_in()
            else:
                tab.reader_view.zoom_out()
            save_font_size(tab.reader_view.font_size)

    def _on_configure(self, event):
        if event.widget == self.root:
            save_window_geometry(self.root.geometry())

    def _on_close(self):
        if self.tabs:
            last_files = []
            for tab in self.tabs:
                last_files.append(tab.filepath)
                save_progress(tab.filepath, tab.current_chapter, tab.reader_view.get_scroll_position())
            save_last_open_files(last_files)
        for tab in self.tabs[:]:
            try:
                tab.toc_panel.destroy()
            except Exception:
                pass
        MainWindow._windows.remove(self)
        self.root.destroy()

    def run(self):
        """启动主循环"""
        self.root.mainloop()