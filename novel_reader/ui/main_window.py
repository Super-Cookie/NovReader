"""主窗口"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ctypes
import os
import sys
import subprocess

from novel_reader.config import (
    DEFAULT_WIN_WIDTH, DEFAULT_WIN_HEIGHT, MIN_WIN_WIDTH, MIN_WIN_HEIGHT,
    WINDOW_BG, ACCENT_COLOR, BORDER_COLOR, ENABLE_MULTI_TAB, AUTO_RESTORE_LAST_FILES,
    KEY_OPEN_FILE, KEY_CLOSE_TAB, KEY_NEW_WINDOW,
    TOOLBAR_HEIGHT, TOOLBAR_FONT_SIZE,
    TOOLBAR_BG, TOOLBAR_BTN_FG, TOOLBAR_HOVER_BG, TOOLBAR_SEP_COLOR,
    TOP_TITLE_FONT_FAMILY, TOP_TITLE_FONT_SIZE, TOP_TITLE_FG, TOP_TITLE_BOLD,
    WINDOW_TITLE_FORMAT, WINDOW_TITLE_DEFAULT,
    TITLE_BAR_HEIGHT, TITLE_BAR_FONT_SIZE,
    TITLE_BAR_BG, TITLE_BAR_FG,
    TITLE_BAR_BTN_HOVER, TITLE_BAR_CLOSE_HOVER, TITLE_BAR_CLOSE_FG,
    SHOW_ZOOM_BUTTONS_READER, SHOW_ZOOM_BUTTONS_TOC, SHOW_TOOLBAR_SEP,
    TITLE_BAR_BTN_WIDTH, TITLE_BAR_ICON_SIZE,
    TITLE_BAR_ICON_LINE_WIDTH, TITLE_BAR_CLOSE_LINE_WIDTH,
    TOC_MODE, dp, dpf, _get_work_area,
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
    def __init__(self, book, reader_view, toc_panel, bottom_nav, filepath):
        self.book = book
        self.reader_view = reader_view
        self.toc_panel = toc_panel
        self.bottom_nav = bottom_nav
        self.filepath = filepath
        self.current_chapter = 0


class MainWindow:
    """主窗口 - 支持多标签页和多窗口"""

    _windows = []

    def __init__(self, filepath=None):
        self.root = tk.Tk()
        self.root.configure(bg=WINDOW_BG)

        # ── 自定义标题栏 ──
        self.root.overrideredirect(True)
        self._ensure_taskbar()
        self._maximized = False
        self._normal_geometry = None
        self._drag_data = None
        self._resize_mode = None
        self._resize_start = None

        self._window_title_text = "NovReader"
        self.root.title(self._window_title_text)   # 任务栏标题

        # 先构建标题栏（pack 顺序决定 z-order）
        self._build_title_bar()

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
                self.root.geometry(f"{DEFAULT_WIN_WIDTH()}x{DEFAULT_WIN_HEIGHT()}")
        else:
            self.root.geometry(f"{DEFAULT_WIN_WIDTH()}x{DEFAULT_WIN_HEIGHT()}")
        self.root.minsize(MIN_WIN_WIDTH(), MIN_WIN_HEIGHT())

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
        toolbar_h = TOOLBAR_HEIGHT()
        self.toolbar = tk.Frame(self.root, bg=TOOLBAR_BG, height=toolbar_h)
        self.toolbar.pack(fill="x", side="top", before=self.main_frame)
        self.toolbar.pack_propagate(False)

        self.toolbar_inner = tk.Frame(self.toolbar, bg=TOOLBAR_BG)
        self.toolbar_inner.pack(fill="both", expand=True, padx=dp(8), pady=dp(2))

        toolbar_inner = self.toolbar_inner

        toolbar_btn_font_size = TOOLBAR_FONT_SIZE()
        btn_style = {
            "font": ("Microsoft YaHei UI", toolbar_btn_font_size),
            "bg": TOOLBAR_BG,
            "fg": TOOLBAR_BTN_FG,
            "borderwidth": 0,
            "padx": dp(8),
            "pady": dp(2),
            "cursor": "hand2",
        }

        self.tb_open_btn = tk.Label(toolbar_inner, text="\u2318O  打开", **btn_style)
        self.tb_open_btn.pack(side="left", padx=dp(2))
        self.tb_open_btn.bind("<Button-1>", lambda e: self.open_file())

        self.tb_recent_btn = tk.Label(toolbar_inner, text="\u2318R  最近", **btn_style)
        self.tb_recent_btn.pack(side="left", padx=dp(2))
        self.tb_recent_btn.bind("<Button-1>", lambda e: self._show_recent_popup())

        self.sep1 = None
        if SHOW_TOOLBAR_SEP:
            self.sep1 = tk.Frame(toolbar_inner, bg=TOOLBAR_SEP_COLOR, width=dp(1))
            self.sep1.pack(side="left", fill="y", padx=dp(8), pady=dp(4))

        # 放大/缩小按钮（分别由正文/目录两个配置控制）
        if SHOW_ZOOM_BUTTONS_READER or SHOW_ZOOM_BUTTONS_TOC:
            self.tb_zoom_out = tk.Label(toolbar_inner, text="A\u207B", **btn_style)
            self.tb_zoom_out.pack(side="left", padx=dp(2))
            self.tb_zoom_out.bind("<Button-1>", lambda e: self._zoom(-1))

            self.tb_zoom_in = tk.Label(toolbar_inner, text="A\u207A", **btn_style)
            self.tb_zoom_in.pack(side="left", padx=dp(2))
            self.tb_zoom_in.bind("<Button-1>", lambda e: self._zoom(1))

            # 初始状态：根据正文配置显示或隐藏
            if not SHOW_ZOOM_BUTTONS_READER:
                self.tb_zoom_out.pack_forget()
                self.tb_zoom_in.pack_forget()
        else:
            self.tb_zoom_out = None
            self.tb_zoom_in = None

        # ── 章节标题（纯展示，在任何模式下都不可点击）──
        title_bold = "bold" if TOP_TITLE_BOLD else "normal"
        self.tb_chapter_lbl = tk.Label(
            toolbar_inner, text="",
            font=(TOP_TITLE_FONT_FAMILY, TOP_TITLE_FONT_SIZE(), title_bold),
            bg=TOOLBAR_BG, fg=TOP_TITLE_FG,
            anchor="center",
        )
        self.tb_chapter_lbl.place(relx=0.5, rely=0.5, anchor="center")

        for lbl in [self.tb_open_btn, self.tb_recent_btn,
                     self.tb_zoom_out, self.tb_zoom_in]:
            if lbl is not None:
                lbl.bind("<Enter>", lambda e, l=lbl: l.configure(bg=TOOLBAR_HOVER_BG))
                lbl.bind("<Leave>", lambda e, l=lbl: l.configure(bg=TOOLBAR_BG))

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
                font=("Microsoft YaHei UI", int(round(dpf(11.5)))),
                command=lambda f=fp: self.open_file(f),
            )
        popup.add_separator()
        popup.add_command(label="清除记录", font=("Microsoft YaHei UI", int(round(dpf(10.5)))),
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
        self._set_window_title(f"{book.title} - NovReader")

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

        toc_panel = TocPanel(parent, book, on_chapter_select=self._on_toc_select,
                              mode=TOC_MODE,
                              on_back_to_reader=lambda: self._toggle_toc(len(self.tabs) - 1))

        bottom_nav = BottomNav(
            parent,
            on_prev=lambda: reader_view.navigate(-1),
            on_next=lambda: reader_view.navigate(1),
            on_toc=lambda: self._toggle_toc(len(self.tabs) - 1),
        )

        bottom_nav.pack(fill="x", side="bottom")
        reader_view.pack(fill="both", expand=True)

        # 内嵌模式：先隐藏 TOC panel（放入 parent 但 pack_forget）
        if TOC_MODE == "embedded":
            toc_panel.pack(fill="both", expand=True)
            toc_panel.pack_forget()

        tab_data = TabData(book, reader_view, toc_panel, bottom_nav, filepath)

        idx = 0
        scroll_pos = 0
        progress = load_progress(filepath)
        if progress:
            idx = progress.get("chapter_index", 0)
            scroll_pos = progress.get("scroll_pos", 0)

        reader_view.render_chapter(idx)
        if scroll_pos > 0:
            reader_view.set_scroll_position(scroll_pos)
        self._update_toolbar_nav(tab_data)

        self.tabs.append(tab_data)
        self.current_tab_index = len(self.tabs) - 1

    def _on_chapter_change(self, chapter_index, scroll_pos):
        if self.current_tab_index < 0:
            return
        tab = self.tabs[self.current_tab_index]
        tab.current_chapter = chapter_index
        save_progress(tab.filepath, chapter_index, scroll_pos)
        self._update_toolbar_nav(tab)

    def _toggle_toc(self, tab_index):
        if tab_index < 0 or tab_index >= len(self.tabs):
            return
        tab = self.tabs[tab_index]
        if tab.toc_panel.is_visible():
            tab.toc_panel.hide()
            if TOC_MODE == "embedded":
                tab.toc_panel.pack_forget()
                tab.reader_view.pack(fill="both", expand=True)
                tab.bottom_nav.pack(fill="x", side="bottom")
            self._update_toolbar_nav(tab)  # 恢复章节信息
            # 回到正文：根据正文配置控制放大缩小按钮
            if SHOW_ZOOM_BUTTONS_READER:
                self._show_zoom_buttons()
            else:
                self._hide_zoom_buttons()
            tab.reader_view.text_widget.focus_set()
        else:
            self.tb_chapter_lbl.configure(text="")  # 目录页不显示章节信息
            # 打开目录：根据目录配置控制放大缩小按钮
            if SHOW_ZOOM_BUTTONS_TOC:
                self._show_zoom_buttons()
            else:
                self._hide_zoom_buttons()
            if TOC_MODE == "embedded":
                # 隐藏正文和底部导航，显示目录
                tab.reader_view.pack_forget()
                tab.bottom_nav.pack_forget()
                tab.toc_panel.pack(fill="both", expand=True)
            tab.toc_panel.show(tab.current_chapter)

    def _on_toc_select(self, chapter_index):
        if self.current_tab_index < 0:
            return
        tab = self.tabs[self.current_tab_index]
        tab.reader_view.render_chapter(chapter_index)
        tab.current_chapter = chapter_index
        save_progress(tab.filepath, chapter_index, 0)
        self._update_toolbar_nav(tab)  # 恢复章节名
        # 回到正文：根据正文配置控制放大缩小按钮
        if SHOW_ZOOM_BUTTONS_READER:
            self._show_zoom_buttons()
        else:
            self._hide_zoom_buttons()
        # 内嵌模式：恢复正文视图
        if TOC_MODE == "embedded":
            try:
                tab.toc_panel.pack_forget()
                tab.reader_view.pack(fill="both", expand=True)
                tab.bottom_nav.pack(fill="x", side="bottom")
            except Exception:
                pass
        tab.reader_view.text_widget.focus_set()

    def _on_tab_changed(self, event=None):
        if self.notebook:
            try:
                self.current_tab_index = self.notebook.index(self.notebook.select())
                if self.current_tab_index >= 0:
                    tab = self.tabs[self.current_tab_index]
                    self._update_toolbar_nav(tab)
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
                self._set_window_title("NovReader")

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

    def _update_toolbar_nav(self, tab):
        try:
            from novel_reader.utils.chinese_num import format_chapter_name
            ch = tab.book.get_chapter(tab.current_chapter)
            if ch:
                title = format_chapter_name(ch.title)
                if ch.volume_name:
                    title = f"{ch.volume_name} {title}"
                self.tb_chapter_lbl.configure(text=title)
            else:
                self.tb_chapter_lbl.configure(text="")
        except Exception:
            self.tb_chapter_lbl.configure(text="")

        has_prev = tab.current_chapter > 0
        has_next = tab.current_chapter < tab.book.chapter_count - 1
        bottom_nav = None
        for child in tab.reader_view.master.winfo_children():
            if isinstance(child, BottomNav):
                bottom_nav = child
                break
        if bottom_nav:
            bottom_nav.update_buttons(has_prev, has_next)

    def _hide_zoom_buttons(self):
        """隐藏工具栏的放大/缩小按钮及左侧分隔竖线"""
        if self.tb_zoom_out is None:
            return
        try:
            self.tb_zoom_out.pack_forget()
            self.tb_zoom_in.pack_forget()
            if self.sep1 is not None:
                self.sep1.pack_forget()
        except tk.TclError:
            pass

    def _show_zoom_buttons(self):
        """显示工具栏的放大/缩小按钮及左侧分隔竖线"""
        if self.tb_zoom_out is None:
            return
        try:
            self.tb_zoom_out.pack(side="left", padx=dp(2))
            self.tb_zoom_in.pack(side="left", padx=dp(2))
            if self.sep1 is not None:
                self.sep1.pack(side="left", fill="y", padx=dp(8), pady=dp(4))
        except tk.TclError:
            pass

    # ──────────────────────────────────────────────
    # 自定义标题栏
    # ──────────────────────────────────────────────

    RESIZE_MARGIN = 5  # 边缘缩放感应区宽度（像素）

    def _ensure_taskbar(self):
        """设置 WS_EX_APPWINDOW 确保窗口显示在任务栏"""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x00040000)  # WS_EX_APPWINDOW
        except Exception:
            pass

    def _build_title_bar(self):
        """构建自定义窗口标题栏（含窗口按钮、拖拽、底部边框线）"""
        bar_h = TITLE_BAR_HEIGHT()
        font_size = TITLE_BAR_FONT_SIZE()

        self.title_bar = tk.Frame(self.root, bg=TITLE_BAR_BG, height=bar_h)
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.pack_propagate(False)

        # 底部 1px 分隔线
        sep = tk.Frame(self.title_bar, bg=BORDER_COLOR, height=dp(1))
        sep.pack(side="bottom", fill="x")

        # ── 标题文本（左对齐） ──
        self.title_bar_lbl = tk.Label(
            self.title_bar,
            text=self._window_title_text,
            font=(TOP_TITLE_FONT_FAMILY, font_size),
            bg=TITLE_BAR_BG, fg=TITLE_BAR_FG,
            anchor="w",
        )
        self.title_bar_lbl.pack(side="left", padx=dp(12), fill="both", expand=True)

        # ── 窗口按钮（右对齐，Canvas 绘制固定等宽图标） ──
        btn_frame = tk.Frame(self.title_bar, bg=TITLE_BAR_BG)
        btn_frame.pack(side="right", fill="y", padx=(0, dp(4)))

        btn_w = TITLE_BAR_BTN_WIDTH()  # 按钮宽度（来自 config）
        btn_h = bar_h                  # 按钮与标题栏等高
        icon_base = TITLE_BAR_ICON_SIZE()  # 图标基准尺寸
        icon_lw = TITLE_BAR_ICON_LINE_WIDTH()
        close_lw = TITLE_BAR_CLOSE_LINE_WIDTH()
        icon_color = TITLE_BAR_FG
        self._btn_icon_color = icon_color
        self._btn_icon_base = icon_base

        def _redraw_min(canvas, bg_color):
            canvas.delete("all")
            cw, ch = btn_w, btn_h
            canvas.create_rectangle(0, 0, cw, ch, fill=bg_color, outline="")
            cx, cy = cw // 2, ch // 2
            # 最小化横线长度 = icon_base × 14/12（与关闭 X 总宽一致）
            w = icon_base * 14 // 12
            canvas.create_line(cx - w//2, cy, cx + w//2, cy,
                               fill=icon_color, width=int(round(icon_lw)), capstyle="round")

        def _redraw_max(canvas, bg_color):
            canvas.delete("all")
            cw, ch = btn_w, btn_h
            canvas.create_rectangle(0, 0, cw, ch, fill=bg_color, outline="")
            cx, cy = cw // 2, ch // 2
            s = icon_base  # 最大化方框边长
            x1, y1 = cx - s//2, cy - s//2
            x2, y2 = cx + s//2, cy + s//2
            canvas.create_rectangle(x1, y1, x2, y2, outline=icon_color,
                                    width=int(round(icon_lw)), fill="")

        def _redraw_close(canvas, bg_color):
            canvas.delete("all")
            cw, ch = btn_w, btn_h
            canvas.create_rectangle(0, 0, cw, ch, fill=bg_color, outline="")
            cx, cy = cw // 2, ch // 2
            # 关闭 X 半长 = icon_base × 7/12（X 总宽与最小化横线一致）
            s2 = icon_base * 7 // 12
            fg = TITLE_BAR_CLOSE_FG if bg_color == TITLE_BAR_CLOSE_HOVER else icon_color
            canvas.create_line(cx - s2, cy - s2, cx + s2, cy + s2,
                               fill=fg, width=int(round(close_lw)), capstyle="round")
            canvas.create_line(cx + s2, cy - s2, cx - s2, cy + s2,
                               fill=fg, width=int(round(close_lw)), capstyle="round")

        # ── 最小化按钮 ──
        self.min_btn = tk.Canvas(btn_frame, width=btn_w, height=btn_h,
                                 bg=TITLE_BAR_BG, highlightthickness=0)
        self.min_btn.pack(side="left")
        _redraw_min(self.min_btn, TITLE_BAR_BG)
        self.min_btn.bind("<Button-1>", lambda e: self._minimize_window())
        self.min_btn.bind("<Enter>", lambda e: _redraw_min(self.min_btn, TITLE_BAR_BTN_HOVER))
        self.min_btn.bind("<Leave>", lambda e: _redraw_min(self.min_btn, TITLE_BAR_BG))

        # ── 最大化按钮 ──
        self.max_btn = tk.Canvas(btn_frame, width=btn_w, height=btn_h,
                                 bg=TITLE_BAR_BG, highlightthickness=0)
        self.max_btn.pack(side="left")
        _redraw_max(self.max_btn, TITLE_BAR_BG)
        self.max_btn.bind("<Button-1>", lambda e: self._maximize_restore_window())
        self.max_btn.bind("<Enter>", lambda e: (
            _redraw_max_icon(single=False, bg_color=TITLE_BAR_BTN_HOVER)
            if self._maximized else _redraw_max(self.max_btn, TITLE_BAR_BTN_HOVER)
        ))
        self.max_btn.bind("<Leave>", lambda e: (
            _redraw_max_icon(single=False, bg_color=TITLE_BAR_BG)
            if self._maximized else _redraw_max(self.max_btn, TITLE_BAR_BG)
        ))

        # ── 关闭按钮 ──
        self.close_btn = tk.Canvas(btn_frame, width=btn_w, height=btn_h,
                                   bg=TITLE_BAR_BG, highlightthickness=0)
        self.close_btn.pack(side="left")
        _redraw_close(self.close_btn, TITLE_BAR_BG)
        self.close_btn.bind("<Button-1>", lambda e: self._on_close())
        self.close_btn.bind("<Enter>",
                            lambda e: _redraw_close(self.close_btn, TITLE_BAR_CLOSE_HOVER))
        self.close_btn.bind("<Leave>",
                            lambda e: _redraw_close(self.close_btn, TITLE_BAR_BG))

        # ── 窗口拖拽（标题栏 + 标题文本都可拖） ──
        self.title_bar.bind("<Button-1>", self._title_bar_press)
        self.title_bar.bind("<B1-Motion>", self._title_bar_drag)
        self.title_bar_lbl.bind("<Button-1>", self._title_bar_press)
        self.title_bar_lbl.bind("<B1-Motion>", self._title_bar_drag)

        # ── 窗口边缘缩放 ──
        self.root.bind("<Motion>", self._edge_motion)
        self.root.bind("<Button-1>", self._edge_press, add="+")
        self.root.bind("<B1-Motion>", self._edge_drag)
        self.root.bind("<ButtonRelease-1>", self._edge_release)

    def _set_window_title(self, text):
        """同时更新自定义标题栏文本和任务栏标题"""
        self._window_title_text = text
        self.title_bar_lbl.configure(text=text)
        self.root.title(text)

    # ── 拖拽移动 ──

    def _title_bar_press(self, event):
        if self._maximized:
            # 最大化状态拖拽 => 先还原再继续拖
            self._maximize_restore_window()
            rx = event.x_root - self.root.winfo_x()
            ry = event.y_root - self.root.winfo_y()
            # 如果鼠标落在标题栏靠左位置，还原后窗口位置偏左调整
            self._drag_data = (rx, ry)
        else:
            self._drag_data = (
                event.x_root - self.root.winfo_x(),
                event.y_root - self.root.winfo_y(),
            )

    def _title_bar_drag(self, event):
        if self._drag_data:
            x = event.x_root - self._drag_data[0]
            y = event.y_root - self._drag_data[1]
            self.root.geometry(f"+{x}+{y}")

    # ── 边缘缩放 ──

    def _edge_motion(self, event):
        """检测鼠标是否在窗口边缘，改变光标形状"""
        if self._maximized:
            if self._resize_mode:
                self.root.config(cursor="")
                self._resize_mode = None
            return

        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x, y = event.x, event.y
        m = self.RESIZE_MARGIN

        left = x <= m
        right = x >= w - m
        top = y <= m
        bottom = y >= h - m

        if top and left:
            self.root.config(cursor="top_left_corner")
            self._resize_mode = "nw"
        elif top and right:
            self.root.config(cursor="top_right_corner")
            self._resize_mode = "ne"
        elif bottom and left:
            self.root.config(cursor="bottom_left_corner")
            self._resize_mode = "sw"
        elif bottom and right:
            self.root.config(cursor="bottom_right_corner")
            self._resize_mode = "se"
        elif left or right:
            self.root.config(cursor="sb_h_double_arrow")
            self._resize_mode = "e" if right else "w"
        elif top or bottom:
            self.root.config(cursor="sb_v_double_arrow")
            self._resize_mode = "s" if bottom else "n"
        else:
            if self._resize_mode:
                self.root.config(cursor="")
                self._resize_mode = None

    def _edge_press(self, event):
        """边缘按下 => 记录初始值"""
        if not self._resize_mode or self._resize_mode in ("n", "s", "w", "e", "nw", "ne", "sw", "se"):
            self._resize_start = (
                event.x_root, event.y_root,
                self.root.winfo_x(), self.root.winfo_y(),
                self.root.winfo_width(), self.root.winfo_height(),
                self._resize_mode,
            )

    def _edge_drag(self, event):
        """拖拽缩放窗口"""
        if not self._resize_start:
            return

        dx = event.x_root - self._resize_start[0]
        dy = event.y_root - self._resize_start[1]
        x0, y0 = self._resize_start[2], self._resize_start[3]
        w0, h0 = self._resize_start[4], self._resize_start[5]
        mode = self._resize_start[6]

        if not mode:
            return

        min_w, min_h = self.root.minsize()
        new_x, new_y, new_w, new_h = x0, y0, w0, h0

        if "w" in mode:
            new_w = max(w0 - dx, min_w)
            new_x = x0 + (w0 - new_w)
        if "e" in mode:
            new_w = max(w0 + dx, min_w)
        if "n" in mode:
            new_h = max(h0 - dy, min_h)
            new_y = y0 + (h0 - new_h)
        if "s" in mode:
            new_h = max(h0 + dy, min_h)

        self.root.geometry(f"{new_w}x{new_h}+{new_x}+{new_y}")

        # 更新起始值（连续拖拽用）
        self._resize_start = (
            event.x_root, event.y_root,
            new_x, new_y, new_w, new_h, mode,
        )

    def _edge_release(self, event):
        """释放边缘缩放"""
        self._resize_start = None

    # ── 窗口按钮动作 ──

    def _minimize_window(self):
        """最小化到任务栏"""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
        except Exception:
            self.root.iconify()

    def _maximize_restore_window(self):
        """最大化 / 还原切换"""
        if self._maximized:
            # 还原
            if self._normal_geometry:
                self.root.geometry(self._normal_geometry)
            self._redraw_max_icon(single=True)
            self._maximized = False
        else:
            # 保存当前几何信息
            self._normal_geometry = self.root.geometry()
            wa_w, wa_h, wa_x, wa_y = _get_work_area()
            self.root.geometry(f"{wa_w}x{wa_h}+{wa_x}+{wa_y}")
            self._redraw_max_icon(single=False)
            self._maximized = True

    def _redraw_max_icon(self, single=True, bg_color=None):
        """重绘最大化按钮图标
        single=True : 单个方框（未最大化，点击可最大化）
        single=False: 重叠方框（已最大化，点击可还原）
        bg_color    : 背景色，None 时用 TITLE_BAR_BG
        """
        cw, ch = TITLE_BAR_BTN_WIDTH(), TITLE_BAR_HEIGHT()
        icon_base = self._btn_icon_base
        icon_color = self._btn_icon_color
        bg = bg_color or TITLE_BAR_BG
        lw = TITLE_BAR_ICON_LINE_WIDTH()

        self.max_btn.delete("all")
        self.max_btn.configure(bg=bg)
        self.max_btn.create_rectangle(0, 0, cw, ch, fill=bg, outline="")

        cx, cy = cw // 2, ch // 2

        if single:
            # 单个方框（最大化图标）
            s = icon_base
            x1, y1 = cx - s // 2, cy - s // 2
            x2, y2 = cx + s // 2, cy + s // 2
            self.max_btn.create_rectangle(x1, y1, x2, y2, outline=icon_color,
                                          width=int(round(lw)), fill="")
        else:
            # 重叠方框（还原图标）：后方大方框 + 前方小方框
            s_big = icon_base
            s_small = icon_base * 5 // 6  # 前方小方框 ≈ 后方 × 5/6
            # 后方大方框（偏左上方）
            bx1 = cx - s_big // 2
            by1 = cy - s_big // 2
            bx2 = cx + s_big // 2
            by2 = cy + s_big // 2
            self.max_btn.create_rectangle(bx1, by1, bx2, by2, outline=icon_color,
                                          width=int(round(lw)), fill="")
            # 前方小方框（偏右下方，覆盖在大方框上）
            fx1 = cx - s_small // 2 + dp(2)
            fy1 = cy - s_small // 2 + dp(2)
            fx2 = cx + s_small // 2 + dp(2)
            fy2 = cy + s_small // 2 + dp(2)
            self.max_btn.create_rectangle(fx1, fy1, fx2, fy2, outline=icon_color,
                                          width=int(round(lw)), fill=TITLE_BAR_BG)

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