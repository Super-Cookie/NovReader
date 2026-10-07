"""目录面板 — 支持悬浮浮层 / 内嵌覆盖两种模式"""

import re
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from novel_reader.config import (
    SIDEBAR_BG, TOC_BG, TOC_VOLUME_BG, TOC_VOLUME_FG,
    TOC_FIXED_VOLUME_BG, TOC_FIXED_VOLUME_FG,
    TOC_CHAPTER_BG, TOC_CHAPTER_FG,
    TOC_HIGHLIGHT_BG, TOC_READING_FG,
    WINDOW_BG, ACCENT_COLOR, BORDER_COLOR,
    TOC_FONT_FAMILY, TOC_FONT_SIZE, TOC_VOLUME_FONT_SIZE,
    TOC_PANEL_WIDTH, TOC_PANEL_HEIGHT, TOC_COLUMN_WRAPLENGTH,
    TOC_HEADER_HEIGHT, SCROLLBAR_WIDTH,
    TOC_MODE,
    READER_MARGIN_BG, READER_BG, READER_PADX_PERCENT,
    TOC_BOTTOM_NAV_HEIGHT, TOC_BOTTOM_NAV_BTN_FONT_SIZE, TOC_BOTTOM_NAV_CENTER_FONT_SIZE,
    TOOLBAR_BG,
    dp, dpf,
)
from novel_reader.utils.chinese_num import format_chapter_name, cn_num_to_arabic
from novel_reader.models.chapter import ChapterType
import math


class TocPanel(tk.Frame):
    """目录面板 — 两种模式：

    - floating (悬浮) : 旧版浮层覆盖 + Canvas 滚动列表
    - embedded (内嵌) : 一巻一页 + 底部翻页，直接嵌入正文区
    """

    COLS = 3
    PANEL_PAD = 60

    def __init__(self, parent, book, on_chapter_select, mode=None, on_back_to_reader=None):
        self.toc_mode = mode if mode is not None else TOC_MODE
        super().__init__(parent, bg=WINDOW_BG if self.toc_mode == "embedded" else "#F5F5F7")

        self.parent = parent
        self.book = book
        self.on_chapter_select = on_chapter_select
        self.on_back_to_reader = on_back_to_reader
        self.grid_items = []
        self.current_highlight = 0
        self._visible = False
        self._wraplength = TOC_COLUMN_WRAPLENGTH()
        self._after_id = None
        self._overlay = None
        self._prev_highlight = -1
        self._reading_chapter_index = -1  # 当前阅读章节的全局索引
        self._anim_after_id = None
        self._FRAME_MS = TocPanel._detect_frame_ms()  # 自适应刷新率

        # ── 浮动模式专用 ──
        if self.toc_mode == "floating":
            self._canvas = None
            self._scrollbar = None
            self._scrollable_frame = None
            self._volume_fixed_label = None
            self._hidden_vol_entry = None
            self._volumes = []
            self._overlay = None
            self._panel_frame = None
            self._mw_handler = None
        else:
            # ── 内嵌模式专用 ──
            self._volume_pages = []
            self._current_page = 0
            self._prev_vol_btn = None
            self._next_vol_btn = None
            self._volume_header = None
            self._content_frame = None
            self._bottom_bar = None
            self._margin_frame = None
            self._content_wrapper = None
            self._content_canvas = None
            self._content_scrollbar = None
            self._canvas_window_id = None
            # 跟踪动画中新建的窗口/框架，用于取消时清理
            self._pending_new_wid = None
            self._pending_new_frame = None
            self._build_embedded_ui()

    @staticmethod
    def _detect_frame_ms():
        """检测主显示器刷新率，返回最佳帧间隔（ms）

        保底 8ms（120fps），确保动画在高刷屏上流畅
        """
        try:
            import ctypes
            dc = ctypes.windll.user32.GetDC(0)
            hz = ctypes.windll.gdi32.GetDeviceCaps(dc, 116)
            ctypes.windll.user32.ReleaseDC(0, dc)
            if hz is not None and 30 <= hz <= 500:
                return min(int(1000 / hz), 8)
        except Exception:
            pass
        return 8

    # ════════════════════════════════════════════════════════════════════
    #  内嵌模式 UI — 三层边距 + 底部导航（章节 / 卷）
    # ════════════════════════════════════════════════════════════════════

    def _build_embedded_ui(self):
        """构建内嵌模式界面"""

        # ── 三层边距：WINDOW_BG → READER_MARGIN_BG → READER_BG ──
        self._margin_frame = tk.Frame(self, bg=READER_MARGIN_BG)
        self._margin_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        # 左右边距（中层）
        left_margin = tk.Frame(self._margin_frame, bg=READER_MARGIN_BG)
        left_margin.place(relx=0, rely=0, relwidth=READER_PADX_PERCENT, relheight=1)
        right_margin = tk.Frame(self._margin_frame, bg=READER_MARGIN_BG)
        right_margin.place(relx=1 - READER_PADX_PERCENT, rely=0,
                            relwidth=READER_PADX_PERCENT, relheight=1)

        # 内容区（内层）
        content_relx = READER_PADX_PERCENT
        content_rw = 1 - 2 * READER_PADX_PERCENT
        self._content_wrapper = tk.Frame(self._margin_frame, bg=READER_BG)
        self._content_wrapper.place(relx=content_relx, rely=0,
                                     relwidth=content_rw, relheight=1)

        # ── 卷标头 ──
        sticky_font = TOC_VOLUME_FONT_SIZE()
        self._volume_header = tk.Label(
            self._content_wrapper, text="",
            font=(TOC_FONT_FAMILY, sticky_font, "bold"),
            bg=TOC_FIXED_VOLUME_BG, fg=TOC_FIXED_VOLUME_FG,
            anchor="center", padx=dp(12), pady=dp(4),
        )
        self._volume_header.pack(fill="x")

        # ── 章节列表容器（可滚动）──
        scroll_container = tk.Frame(self._content_wrapper, bg=READER_BG)
        scroll_container.pack(fill="both", expand=True)

        self._content_canvas = tk.Canvas(scroll_container, bg=READER_BG,
                                          highlightthickness=0, borderwidth=0)
        self._content_scrollbar = tk.Scrollbar(scroll_container, orient="vertical",
                                                 command=self._content_canvas.yview,
                                                 width=SCROLLBAR_WIDTH(),
                                                 bg="#C8C8C8", troughcolor=READER_BG,
                                                 activebackground="#AAAAAA",
                                                 borderwidth=0, highlightthickness=0,
                                                 relief="flat")
        self._content_frame = tk.Frame(self._content_canvas, bg=READER_BG)

        self._content_frame.bind("<Configure>",
            lambda e: self._content_canvas.configure(
                scrollregion=self._content_canvas.bbox("all")))
        self._canvas_window_id = self._content_canvas.create_window(
            (0, 0), window=self._content_frame, anchor="nw")

        def _on_canvas_configure(event):
            self._content_canvas.itemconfig(self._canvas_window_id, width=event.width)
        self._content_canvas.bind("<Configure>", _on_canvas_configure)

        self._content_canvas.configure(yscrollcommand=self._content_scrollbar.set)
        self._content_canvas.pack(side="left", fill="both", expand=True)
        self._content_scrollbar.pack(side="right", fill="y")

        # 滚动事件：绑定到 Canvas 和内层框架，确保鼠标在任意位置都能滚动
        self._content_canvas.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self._content_frame.bind("<MouseWheel>", self._on_mousewheel, add="+")

        # ── 底部导航栏：上一卷 | 返回正文 | 下一卷 ──
        self._bottom_bar = tk.Frame(self._content_wrapper, bg=TOOLBAR_BG, height=TOC_BOTTOM_NAV_HEIGHT())
        self._bottom_bar.pack(fill="x")
        self._bottom_bar.pack_propagate(False)

        nav_font_side = (TOC_FONT_FAMILY, TOC_BOTTOM_NAV_BTN_FONT_SIZE())
        nav_font_mid = (TOC_FONT_FAMILY, TOC_BOTTOM_NAV_CENTER_FONT_SIZE())

        # 居中容器
        center_bar = tk.Frame(self._bottom_bar, bg=TOOLBAR_BG)
        center_bar.pack(expand=True, fill="both")

        # 按钮组（用 place 完美居中）
        btn_group = tk.Frame(center_bar, bg=TOOLBAR_BG)
        btn_group.place(relx=0.48, rely=0.5, anchor="center")

        # 上一卷
        self._prev_vol_btn = tk.Label(
            btn_group, text="\u25C0  上一卷",
            font=nav_font_side, bg=TOOLBAR_BG, fg="#1D1D1F",
            cursor="hand2", padx=dp(20), pady=dp(10),
        )
        self._prev_vol_btn.pack(side="left", padx=dp(8))
        self._prev_vol_btn.bind("<Button-1>", lambda e: self._go_to_page(self._current_page - 1, vertical=True))

        # 返回正文（纯黑色，无高亮）
        self._back_btn = tk.Label(
            btn_group, text="\u25C0  返回正文",
            font=nav_font_mid,
            bg=TOOLBAR_BG, fg="#1D1D1F",
            cursor="hand2", padx=dp(18), pady=dp(10),
        )
        self._back_btn.pack(side="left", padx=dp(4))
        self._back_btn.bind("<Button-1>", lambda e: self._on_back_click())

        # 下一卷
        self._next_vol_btn = tk.Label(
            btn_group, text="下一卷  \u25B6",
            font=nav_font_side, bg=TOOLBAR_BG, fg="#1D1D1F",
            cursor="hand2", padx=dp(20), pady=dp(10),
        )
        self._next_vol_btn.pack(side="left", padx=dp(8))
        self._next_vol_btn.bind("<Button-1>", lambda e: self._go_to_page(self._current_page + 1, vertical=True))

        # 键盘导航
        self.bind("<Up>", lambda e: self._navigate_grid(-1, 0))
        self.bind("<Down>", lambda e: self._navigate_grid(1, 0))
        self.bind("<Left>", lambda e: self._navigate_grid(0, -1))
        self.bind("<Right>", lambda e: self._navigate_grid(0, 1))
        self.bind("<Return>", lambda e: self._select_highlighted())
        self.bind("<Escape>", lambda e: self.hide())

    def _on_back_click(self):
        """点击"返回正文"按钮：通过回调返回阅读视图"""
        if self.on_back_to_reader:
            self.on_back_to_reader()

    # ════════════════════════════════════════════════════════════════════
    #  悬浮模式 UI（旧版 Canvas 滚动列表 + 浮层）
    # ════════════════════════════════════════════════════════════════════

    def _get_panel_size(self):
        try:
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
        except tk.TclError:
            pw, ph = 1200, 800
        w = min(pw - dp(self.PANEL_PAD), TOC_PANEL_WIDTH())
        h = min(ph - dp(60), TOC_PANEL_HEIGHT())
        col_avail = (w - dp(40)) // self.COLS
        self._wraplength = max(col_avail - dp(16), dp(150))
        return w, h

    def _build_floating_overlay(self):
        if self._overlay:
            return

        self._overlay = tk.Frame(self.parent, bg=WINDOW_BG)
        self._overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._overlay.lower()

        self._overlay.bind("<Button-1>", lambda e: self.hide())

        self._panel_frame = tk.Frame(self._overlay, bg="#F5F5F7",
                                      highlightbackground=BORDER_COLOR, highlightthickness=dp(1))
        self._panel_frame.place(relx=0.5, rely=0.5, anchor="center")

        self._panel_frame.bind("<Button-1>", lambda e: e.widget.focus_set())

        # 标题栏
        header_h = TOC_HEADER_HEIGHT()
        header = tk.Frame(self._panel_frame, bg=SIDEBAR_BG, height=header_h)
        header.pack(fill="x")
        header.pack_propagate(False)

        toc_title_font = TOC_FONT_SIZE()
        title_lbl = tk.Label(header, text="\uD83D\uDCD6  目录",
                              font=(TOC_FONT_FAMILY, toc_title_font, "bold"),
                              bg=SIDEBAR_BG, fg="#1D1D1F")
        title_lbl.pack(side="left", padx=dp(10), pady=dp(2))

        close_font_size = int(round(dpf(12)))
        close_btn = tk.Label(header, text="\u2715",
                              font=(TOC_FONT_FAMILY, close_font_size),
                              bg=SIDEBAR_BG, fg="#86868B",
                              padx=dp(10), pady=dp(2), cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.hide())
        close_btn.bind("<Enter>", lambda e: close_btn.configure(fg="#1D1D1F"))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(fg="#86868B"))

        # 固定卷标（始终可见）
        sticky_font = TOC_VOLUME_FONT_SIZE()
        self._volume_fixed_label = tk.Label(
            self._panel_frame, text="",
            font=(TOC_FONT_FAMILY, sticky_font, "bold"),
            bg=TOC_FIXED_VOLUME_BG, fg=TOC_FIXED_VOLUME_FG,
            anchor="w", padx=dp(12), pady=dp(4),
        )

        # Canvas + 滚动条
        canvas_frame = tk.Frame(self._panel_frame, bg="#F5F5F7")
        canvas_frame.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(canvas_frame, bg="#F5F5F7", borderwidth=0, highlightthickness=0)
        self._scrollbar = tk.Scrollbar(canvas_frame, orient="vertical",
                                        command=self._canvas.yview, width=SCROLLBAR_WIDTH(),
                                        bg="#C8C8C8", troughcolor="#F5F5F7",
                                        activebackground="#AAAAAA",
                                        borderwidth=0, highlightthickness=0,
                                        relief="flat")
        self._scrollable_frame = tk.Frame(self._canvas, bg="#F5F5F7")

        self._scrollable_frame.bind("<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas_window = self._canvas.create_window((0, 0), window=self._scrollable_frame, anchor="nw")

        def _on_canvas_configure(event):
            self._canvas.itemconfig(self._canvas_window, width=event.width)
        self._canvas.bind("<Configure>", _on_canvas_configure)

        self._canvas.configure(yscrollcommand=self._on_canvas_scroll)
        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.pack(side="right", fill="y")

        self._bind_mousewheel()

        for w in (self._overlay, self._panel_frame, header, canvas_frame, self._canvas):
            w.bind("<Escape>", lambda e: self.hide())

        self._panel_frame.bind("<Up>", lambda e: self._navigate_grid(-1, 0))
        self._panel_frame.bind("<Down>", lambda e: self._navigate_grid(1, 0))
        self._panel_frame.bind("<Left>", lambda e: self._navigate_grid(0, -1))
        self._panel_frame.bind("<Right>", lambda e: self._navigate_grid(0, 1))
        self._panel_frame.bind("<Return>", lambda e: self._select_highlighted())
        self._canvas.bind("<Up>", lambda e: self._navigate_grid(-1, 0))
        self._canvas.bind("<Down>", lambda e: self._navigate_grid(1, 0))
        self._canvas.bind("<Left>", lambda e: self._navigate_grid(0, -1))
        self._canvas.bind("<Right>", lambda e: self._navigate_grid(0, 1))
        self._canvas.bind("<Return>", lambda e: self._select_highlighted())
        self._canvas.bind("<Enter>", lambda e: self._canvas.focus_set(), add="+")

    def _bind_mousewheel(self):
        def _on_mousewheel(event):
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            self._schedule_fixed_update()
            return "break"
        self._mw_handler = _on_mousewheel
        self._canvas.bind("<MouseWheel>", self._mw_handler, add="+")

    def _schedule_fixed_update(self):
        if self._after_id is not None:
            try:
                self._overlay.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self._overlay.after(30, self._do_fixed_update)

    def _on_canvas_scroll(self, *args):
        self._scrollbar.set(*args)
        self._schedule_fixed_update()

    def _do_fixed_update(self):
        self._after_id = None
        self._update_fixed_volume_floating()

    def _update_fixed_volume_floating(self):
        """悬浮模式：在固定卷标头显示当前可见卷名，不隐藏列表中的卷标"""
        if not self._volumes or not self._volume_fixed_label:
            return
        try:
            canvas_top = self._canvas.canvasy(0)
        except Exception:
            return
        current_vol = None
        for vol_name, _ in self._volumes:
            pass
        for vol_name in [v[0] for v in self._volumes]:
            current_vol = vol_name
            break
        if current_vol:
            new_text = "  " + current_vol
            if self._volume_fixed_label.cget("text") != new_text:
                self._volume_fixed_label.configure(text=new_text)
        if not self._volume_fixed_label.winfo_manager():
            self._volume_fixed_label.pack(fill="x", before=self._canvas.master)

    def _update_floating_panel_size(self):
        w, h = self._get_panel_size()
        try:
            self._panel_frame.place_configure(width=w, height=h)
        except tk.TclError:
            pass

    # ════════════════════════════════════════════════════════════════════
    #  渲染（两种模式共用）
    # ════════════════════════════════════════════════════════════════════

    def _get_chapter_bg(self, chapter_index):
        """chapter_index 是章节全局索引（ci）"""
        if (0 <= self.current_highlight < len(self.grid_items) and
                self.grid_items[self.current_highlight][2] == chapter_index):
            return TOC_HIGHLIGHT_BG  # 浅蓝
        return READER_BG

    def _build_volume_pages(self):
        """将全书章节分组：

        - 有卷名的 → 按卷分组（一卷一页）
        - 无卷名的 →
            · 如果全书已有卷结构 → 归入第一卷最前面
            · 如果全书都没有卷名 → 每 50 章一组
        """
        chapters = self.book.chapters
        volumes = {}
        no_volume = []

        for i, ch in enumerate(chapters):
            if ch.volume_name:
                vn = ch.volume_name
                if vn not in volumes:
                    volumes[vn] = []
                volumes[vn].append((i, ch))
            else:
                no_volume.append((i, ch))

        pages = []
        if volumes:
            if no_volume:
                # 无卷名的章节放在第一卷最前面
                first_vn = next(iter(volumes))
                volumes[first_vn] = no_volume + volumes[first_vn]
            for vol_name, vol_chapters in volumes.items():
                pages.append((vol_name, vol_chapters))
        elif no_volume:
            # 全书都没有卷名 → 每 50 个有编号的章节拆一页
            # 无编号的章节（如「介绍」「楔子」）归入当前页，不占计数
            PAGE_SIZE = 50

            def _chapter_num(ch):
                """从标题提取 (阿拉伯数字编号, 关键词)，如「第一章」→ (1, '章')、「第100回」→ (100, '回')"""
                m = re.search(r'第\s*([零一二三四五六七八九十百千万亿壹贰叁肆伍陆柒捌玖拾佰仟萬億廿卅卌]+)\s*([章节回折篇幕集])', ch.title)
                if m:
                    num = cn_num_to_arabic(m.group(1))
                    if num is not None:
                        return num, m.group(2)
                return None, None

            pages_data = []  # [(chunk, first_num, last_num, keyword)]
            current_chunk = []
            numbered_in_chunk = 0
            for item in no_volume:
                current_chunk.append(item)
                n, kw = _chapter_num(item[1])
                if n is not None:
                    if numbered_in_chunk == 0:
                        first_n, first_kw = n, kw
                    numbered_in_chunk += 1
                    last_n = n
                    last_kw = kw
                if numbered_in_chunk == PAGE_SIZE:
                    pages_data.append((list(current_chunk), first_n, last_n, first_kw))
                    current_chunk = []
                    numbered_in_chunk = 0
            if current_chunk:
                # 最后一页不足 50 章
                if numbered_in_chunk > 0:
                    pages_data.append((current_chunk, first_n, last_n, first_kw))
                else:
                    pages_data.append((current_chunk, None, None, None))

            for chunk, first_n, last_n, kw in pages_data:
                if first_n is not None and len(pages_data) > 1:
                    label = f"正文 · 第{first_n}-{last_n}{kw}"
                else:
                    label = "正文"
                pages.append((label, chunk))

        return pages

    # ── 悬浮模式渲染 ──

    def _render_floating_toc(self):
        for widget in self._scrollable_frame.winfo_children():
            widget.destroy()
        self.grid_items = []
        self._volumes = []
        self._hidden_vol_entry = None
        self._prev_highlight = -1

        pages = self._build_volume_pages()
        vol_font_size = TOC_VOLUME_FONT_SIZE()

        for vol_name, vol_chapters in pages:
            vol_label = tk.Label(self._scrollable_frame, text=vol_name,
                                  font=(TOC_FONT_FAMILY, vol_font_size, "bold"),
                                  bg=TOC_VOLUME_BG, fg=TOC_VOLUME_FG,
                                  anchor="w", padx=dp(8), pady=dp(3))
            vol_label.pack(fill="x", pady=(dp(6), dp(2)))
            self._volumes.append((vol_name, vol_label))
            self._build_page_grid(self._scrollable_frame, vol_chapters)

        if self._mw_handler:
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    # ── 内嵌模式渲染 ──

    def _update_page_ui(self):
        """更新卷标头和翻页按钮状态（不重新渲染内容）"""
        if not self._volume_pages:
            return
        vol_name, _ = self._volume_pages[self._current_page]
        total_pages = len(self._volume_pages)
        if "正文" in vol_name:
            # 没有卷名 → "第X卷 (X/总数卷)"
            header_text = f"第{self._current_page + 1}卷（{self._current_page + 1}/{total_pages}卷）"
        elif total_pages > 1:
            header_text = f"{vol_name}（{self._current_page + 1}/{total_pages}卷）"
        else:
            header_text = vol_name
        self._volume_header.configure(text=header_text)
        self._prev_vol_btn.configure(
            fg="#1D1D1F" if self._current_page > 0 else "#CCCCCC",
            cursor="hand2" if self._current_page > 0 else "arrow",
        )
        self._next_vol_btn.configure(
            fg="#1D1D1F" if self._current_page < total_pages - 1 else "#CCCCCC",
            cursor="hand2" if self._current_page < total_pages - 1 else "arrow",
        )

    def _render_embedded_page(self):
        if not self._volume_pages:
            return

        for widget in self._content_frame.winfo_children():
            widget.destroy()
        self.grid_items = []
        self._prev_highlight = -1

        vol_name, vol_chapters = self._volume_pages[self._current_page]
        self._update_page_ui()

        grid_h, _ = self._build_page_grid(self._content_frame, vol_chapters,
                                  self._reading_chapter_index)
        # 更新 canvas window 高度，至少撑满视口
        ch = self._content_canvas.winfo_height()
        canvas_item_h = max(grid_h + dp(16), ch)
        self._content_canvas.itemconfig(self._canvas_window_id, height=canvas_item_h)
        self.winfo_toplevel().update_idletasks()

    # ── 共通章节 grid（Canvas 批量绘制，替代逐个 Label） ──

    def _build_page_grid(self, parent, chapters_group, reading_chapter_index=-1, available_width=None):
        """返回 (total_height, total_rows) 供调用方设置 canvas window 高度"""
        cols = self.COLS
        toc_font_size = TOC_FONT_SIZE()
        chapter_bg = READER_BG
        hover_bg = "#EAE5D9"

        canvas = tk.Canvas(parent, bg=chapter_bg, highlightthickness=0)
        # 只用 fill="x"（不 expand），高度由 canvas.configure(height=…) 精确控制
        canvas.pack(fill="x", padx=dp(12), pady=dp(8))

        # 计算列宽和行高
        canvas.update_idletasks()
        cw = available_width or max(canvas.winfo_width(), dp(200))
        col_w = cw // cols
        f = tkfont.Font(family=TOC_FONT_FAMILY, size=toc_font_size)
        row_h = f.metrics("linespace") + dp(10)
        pad_x = dp(4)

        # 可复用测宽字体
        _measure_font = tkfont.Font(family=TOC_FONT_FAMILY, size=toc_font_size)

        for idx, (ci, ch) in enumerate(chapters_group):
            row = idx // cols
            col = idx % cols
            display_name = format_chapter_name(ch.title)

            is_reading = (ci == reading_chapter_index)
            fg = TOC_READING_FG if is_reading else TOC_CHAPTER_FG

            # ── 自适应字号：长章节名自动缩小以单行容下 ──
            available_w = col_w - dp(8)  # create_text 的 width 参数同
            _measure_font.configure(size=toc_font_size,
                                     weight="bold" if is_reading else "normal")
            text_px = _measure_font.measure(display_name)
            final_size = toc_font_size
            if text_px > available_w:
                for sz in range(toc_font_size - 1, 6, -1):  # 最小 6pt
                    _measure_font.configure(size=sz)
                    if _measure_font.measure(display_name) <= available_w:
                        final_size = sz
                        break
            font_style = ((TOC_FONT_FAMILY, final_size, "bold")
                          if is_reading else
                          (TOC_FONT_FAMILY, final_size))

            cx = col * col_w + col_w // 2
            cy = row * row_h + row_h // 2

            # 背景矩形（用于悬停/高亮）
            bg_tag = f"bg_{idx}"
            canvas.create_rectangle(
                col * col_w + pad_x, row * row_h,
                (col + 1) * col_w - pad_x, (row + 1) * row_h,
                fill=chapter_bg, outline="", tags=bg_tag,
            )

            # 章节名文本（不设 width，让字体自适应避免换行）
            text_tag = f"ch_{idx}"
            text_id = canvas.create_text(
                cx, cy,
                text=display_name,
                font=font_style,
                fill=fg,
                anchor="center", justify="center",
                tags=text_tag,
            )

            # 保存引用：(canvas, text_id, bg_tag, 全局章节索引 ci, 自适应字号)
            self.grid_items.append((canvas, text_id, bg_tag, ci, final_size))

        # 计算 Canvas 总高度 + 兼容旧 scroll 逻辑
        total_rows = max(1, math.ceil(len(chapters_group) / cols))
        canvas_h = total_rows * row_h + dp(8)
        canvas.configure(scrollregion=(0, 0, cw, canvas_h))
        canvas.configure(height=canvas_h)

        # ── 鼠标交互（仅在当前 Canvas 的 item 范围内） ──
        _last_hover = [-1]  # 闭包记住上一个悬停索引，避免全量遍历

        def _tag_to_idx(tags):
            for t in tags:
                if t.startswith("ch_"):
                    return int(t[3:])
            return -1

        def _on_click(event):
            items = canvas.find_overlapping(event.x, event.y, event.x, event.y)
            for item in items:
                idx = _tag_to_idx(canvas.gettags(item))
                if 0 <= idx < len(self.grid_items):
                    _, _, _, ci, _ = self.grid_items[idx]
                    self._select_chapter(ci)
                    return

        def _on_motion(event):
            items = canvas.find_overlapping(event.x, event.y, event.x, event.y)
            hover_idx = -1
            for item in items:
                idx = _tag_to_idx(canvas.gettags(item))
                if 0 <= idx < len(self.grid_items):
                    hover_idx = idx
                    break
            # 只更新变化项
            prev = _last_hover[0]
            if hover_idx == prev:
                return
            _last_hover[0] = hover_idx
            # 恢复上一个
            if 0 <= prev < len(self.grid_items):
                c, _, bg_t, _, _ = self.grid_items[prev]
                is_hl = (prev == self.current_highlight)
                c.itemconfig(bg_t, fill=TOC_HIGHLIGHT_BG if is_hl else chapter_bg)
            # 高亮当前
            if 0 <= hover_idx < len(self.grid_items) and hover_idx != self.current_highlight:
                c, _, bg_t, _, _ = self.grid_items[hover_idx]
                c.itemconfig(bg_t, fill=hover_bg)

        def _on_leave(event):
            prev = _last_hover[0]
            _last_hover[0] = -1
            if 0 <= prev < len(self.grid_items):
                c, _, bg_t, _, _ = self.grid_items[prev]
                is_hl = (prev == self.current_highlight)
                c.itemconfig(bg_t, fill=TOC_HIGHLIGHT_BG if is_hl else chapter_bg)

        canvas.bind("<Button-1>", _on_click)
        canvas.bind("<Motion>", _on_motion)
        canvas.bind("<Leave>", _on_leave)
        # 让子 Canvas 的滚轮事件也能驱动外层的 _content_canvas 滚动
        canvas.bind("<MouseWheel>", self._on_mousewheel, add="+")

        return canvas_h, total_rows

    # ════════════════════════════════════════════════════════════════════
    #  交互逻辑
    # ════════════════════════════════════════════════════════════════════

    def _on_mousewheel(self, event):
        """鼠标滚轮：仅在当前卷内滚动"""
        if self.toc_mode != "embedded":
            return
        self._content_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _select_chapter(self, index):
        self.on_chapter_select(index)
        self.hide()

    # ── 弹性动画 ──

    def _animate_slide_in(self):
        """直接显示内容，跳过滑入动画"""
        self._content_canvas.coords(self._canvas_window_id, 0, 0)

    def _cleanup_pending_animation(self):
        """清理上一次被取消动画的残留窗口/框架"""
        if self._pending_new_wid is not None:
            try:
                self._content_canvas.delete(self._pending_new_wid)
            except tk.TclError:
                pass
            self._pending_new_wid = None
        if self._pending_new_frame is not None:
            try:
                self._pending_new_frame.destroy()
            except Exception:
                pass
            self._pending_new_frame = None

    def _cleanup_orphan_windows(self):
        """清理 Canvas 中除当前内容窗口之外的所有残留窗口

        快速连续翻页时，被取消动画创建的 Canvas window 会残留在画布上，
        积累后导致显示错乱。此方法彻底清除它们。
        """
        try:
            all_items = self._content_canvas.find_all()
        except tk.TclError:
            return
        for item in all_items:
            if item == self._canvas_window_id:
                continue
            try:
                item_type = self._content_canvas.type(item)
            except tk.TclError:
                continue
            if item_type == "window":
                try:
                    # 获取该 window 对应的 tk 框架并销毁
                    frame_widget = self._content_canvas.itemcget(item, "window")
                    if frame_widget and frame_widget.winfo_exists():
                        frame_widget.destroy()
                except Exception:
                    pass
                try:
                    self._content_canvas.delete(item)
                except tk.TclError:
                    pass

    def _animate_page_switch(self, page_index, vertical=False, target_highlight=0):
        """弹性滑动翻页 — 时间驱动 + after_idle（自适应刷新率）

        vertical=True 时上下滑动，否则左右滑动
        """
        # 取消进行中的动画，并清理上一次被取消动画的残留窗口
        if self._anim_after_id is not None:
            try:
                self._content_canvas.after_cancel(self._anim_after_id)
            except Exception:
                pass
            self._anim_after_id = None
        # 清理之前被取消动画留下的孤儿窗口（new_wid / new_frame）
        self._cleanup_pending_animation()

        direction = 1 if page_index > self._current_page else -1
        cw = self._content_canvas.winfo_width()
        ch = self._content_canvas.winfo_height()
        if cw < 10:
            cw = getattr(self, '_content_wrapper', self).winfo_width() or 600
        if ch < 10:
            ch = 400

        # 裁剪画布到视口大小，禁止溢出显示（水平也要，防止两帧重叠）
        self._content_canvas.configure(scrollregion=(0, 0, cw, ch))

        # 更新状态 + UI（卷标头、翻页按钮）
        self._current_page = page_index
        self._update_page_ui()

        # 构建新页面内容
        self.grid_items = []
        self._prev_highlight = -1
        new_frame = tk.Frame(self._content_canvas, bg=READER_BG)
        vol_chapters = self._volume_pages[page_index][1]
        # 注意：grid Canvas 内部 pack(padx=dp(12))，实际绘图区比视口窄 2*dp(12)
        # 必须传入正确宽度，否则最右列文字会被裁剪
        grid_h, _ = self._build_page_grid(
            new_frame, vol_chapters, self._reading_chapter_index,
            available_width=cw - 2 * dp(12))
        # 用 max(grid_h, ch) 确保新页面高度至少撑满视口，不留旧内容痕迹
        new_h = max(grid_h + dp(16), ch)
        self.winfo_toplevel().update_idletasks()

        if vertical:
            start_y = direction * ch
            new_wid = self._content_canvas.create_window(
                (0, start_y), window=new_frame, anchor="nw", width=cw, height=new_h)
        else:
            start_x = direction * cw
            new_wid = self._content_canvas.create_window(
                (start_x, 0), window=new_frame, anchor="nw", width=cw, height=new_h)

        # 记录当前动画的新窗口，以便被取消时清理
        self._pending_new_wid = new_wid
        self._pending_new_frame = new_frame

        old_wid, old_frame = self._canvas_window_id, self._content_frame
        axis_len = ch if vertical else cw
        DUR_MS = 360  # 总时长

        def ease_out_quart(t):
            return 1 - (1 - t)**4

        anim_start = time.monotonic()

        def _anim():
            elapsed = (time.monotonic() - anim_start) * 1000  # ms
            progress = min(1.0, elapsed / DUR_MS)

            if progress >= 1.0:
                # 收尾：移除旧帧，更新引用
                self._content_canvas.delete(old_wid)
                try:
                    old_frame.destroy()
                except Exception:
                    pass
                self._content_frame = new_frame
                self._canvas_window_id = new_wid
                self._content_canvas.coords(new_wid, 0, 0)
                self.winfo_toplevel().update_idletasks()
                self._content_canvas.configure(
                    scrollregion=self._content_canvas.bbox("all"))
                self._content_canvas.yview_moveto(0)
                self.current_highlight = target_highlight
                self._anim_after_id = None
                # 动画完成，清除 pending 标记
                self._pending_new_wid = None
                self._pending_new_frame = None
                self._update_highlight()
                return

            eased = ease_out_quart(progress)
            offset = int(axis_len * (1 - eased) * direction)

            if vertical:
                self._content_canvas.coords(old_wid, 0, offset - direction * ch)
                self._content_canvas.coords(new_wid, 0, offset)
            else:
                self._content_canvas.coords(old_wid, offset - direction * cw, 0)
                self._content_canvas.coords(new_wid, offset, 0)

            # after_idle 自然匹配显示器刷新率，不抢 CPU
            self._anim_after_id = self._content_canvas.after_idle(_anim)

        _anim()

    def _go_to_page(self, page_index, vertical=False, target_highlight=0):
        if self.toc_mode != "embedded":
            return
        total = len(self._volume_pages)
        if page_index < 0 or page_index >= total:
            return
        if page_index == self._current_page and self.grid_items:
            return

        # 有现有内容 → 弹性动画翻页
        if self.grid_items:
            self._animate_page_switch(page_index, vertical=vertical,
                                       target_highlight=target_highlight)
        else:
            # 初始渲染
            self._current_page = page_index
            self.current_highlight = 0
            self._render_embedded_page()
            if self.grid_items:
                self._prev_highlight = -1
                self._update_highlight()

    def _navigate_grid(self, row_delta, col_delta):
        if not self.grid_items:
            return
        total = len(self.grid_items)
        if col_delta != 0:
            new_idx = self.current_highlight + col_delta
        else:
            new_idx = self.current_highlight + row_delta * self.COLS

        # 跨页导航（内嵌模式）：边界溢出时自动翻卷
        if self.toc_mode == "embedded" and len(self._volume_pages) > 1:
            if new_idx < 0:
                # 还没到本页开头，只是索引溢出了 → 停在第一个
                if self.current_highlight > 0:
                    new_idx = 0
                    self.current_highlight = new_idx
                    self._update_highlight()
                    return
                # 已在第一个 → 去上一卷
                if self._current_page <= 0:
                    return
                target_col = (self.current_highlight % self.COLS
                              if col_delta == 0 else self.COLS - 1)
                is_vertical = True
                total2 = len(self._volume_pages[self._current_page - 1][1])
                rows2 = (total2 + self.COLS - 1) // self.COLS
                target_idx = (rows2 - 1) * self.COLS + target_col
                if target_idx >= total2:
                    target_idx = total2 - 1
                self._go_to_page(self._current_page - 1, vertical=is_vertical,
                                  target_highlight=target_idx)
                return
            elif new_idx >= total:
                # 还没到本页末尾，只是索引溢出了 → 停在最后一个
                if self.current_highlight < total - 1:
                    new_idx = total - 1
                    self.current_highlight = new_idx
                    self._update_highlight()
                    return
                # 已在最后一个 → 去下一卷
                if self._current_page >= len(self._volume_pages) - 1:
                    return
                target_col = (self.current_highlight % self.COLS
                              if col_delta == 0 else 0)
                is_vertical = True
                total2 = len(self._volume_pages[self._current_page + 1][1])
                target_idx = min(target_col, total2 - 1)
                self._go_to_page(self._current_page + 1, vertical=is_vertical,
                                  target_highlight=target_idx)
                return

        new_idx = max(0, min(total - 1, new_idx))
        self.current_highlight = new_idx
        self._update_highlight()

    def _update_highlight(self):
        prev = self._prev_highlight
        if prev == self.current_highlight:
            return
        if 0 <= prev < len(self.grid_items):
            canvas, text_id, bg_tag, ci, fsize = self.grid_items[prev]
            is_reading = (ci == self._reading_chapter_index)
            try:
                canvas.itemconfig(text_id,
                    fill=TOC_READING_FG if is_reading else TOC_CHAPTER_FG,
                    font=(TOC_FONT_FAMILY, fsize,
                          "bold" if is_reading else "normal"),
                )
                canvas.itemconfig(bg_tag, fill=READER_BG)
            except tk.TclError:
                pass
        if 0 <= self.current_highlight < len(self.grid_items):
            canvas, text_id, bg_tag, ci, fsize = self.grid_items[self.current_highlight]
            is_reading = (ci == self._reading_chapter_index)
            try:
                canvas.itemconfig(text_id,
                    fill=TOC_READING_FG if is_reading else TOC_CHAPTER_FG,
                    font=(TOC_FONT_FAMILY, fsize, "bold"),
                )
                canvas.itemconfig(bg_tag, fill=TOC_HIGHLIGHT_BG)
            except tk.TclError:
                pass
        self._prev_highlight = self.current_highlight

    def _select_highlighted(self):
        if not self._visible:
            return
        if self.grid_items and self.current_highlight < len(self.grid_items):
            _, _, _, ci, _ = self.grid_items[self.current_highlight]
            self._select_chapter(ci)

    # ════════════════════════════════════════════════════════════════════
    #  生命周期 — 显示 / 隐藏
    # ════════════════════════════════════════════════════════════════════

    def show(self, current_chapter_index=0):
        if self.toc_mode == "floating":
            self._show_floating(current_chapter_index)
        else:
            self._show_embedded(current_chapter_index)

    def hide(self):
        if self.toc_mode == "floating":
            self._hide_floating()
        else:
            self._hide_embedded()
        self._visible = False

    def is_visible(self):
        return self._visible

    def refresh(self):
        """刷新目录内容"""
        if self.toc_mode == "floating":
            if self._overlay:
                self._render_floating_toc()
        else:
            self._volume_pages = []
            if self._visible:
                # 注意：self._reading_chapter_index 是全局章节索引，不能传 self.current_highlight（页内本地索引）
                self.show(self._reading_chapter_index)

    def destroy(self):
        if self.toc_mode == "floating":
            if self._overlay:
                self._overlay.destroy()
                self._overlay = None
                self._panel_frame = None
                self._volume_fixed_label = None
                self._volumes = []
        else:
            try:
                super().destroy()
            except Exception:
                pass

    # ── 悬浮模式 ──

    def _show_floating(self, current_chapter_index=0):
        if not self._overlay:
            self._build_floating_overlay()

        self._update_floating_panel_size()
        self._overlay.lift()
        self._overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._overlay.update_idletasks()
        self._render_floating_toc()
        self._scrollable_frame.update_idletasks()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

        self._visible = True
        self._canvas.focus_set()
        if self._volume_fixed_label:
            self._volume_fixed_label.pack_forget()
        if 0 <= current_chapter_index < len(self.grid_items):
            self.current_highlight = current_chapter_index
            self._update_highlight()
            self._scroll_to_highlighted()
        self._overlay.after(50, self._do_fixed_update)

    def _hide_floating(self):
        if self._overlay:
            self._overlay.place_forget()
        if self._volume_fixed_label:
            self._volume_fixed_label.pack_forget()

    def _scroll_to_highlighted(self):
        if not self.grid_items or self.current_highlight >= len(self.grid_items):
            return
        canvas, text_id, _, _, _ = self.grid_items[self.current_highlight]
        try:
            bbox = canvas.bbox(text_id)
            if not bbox:
                return
            w_y = canvas.winfo_y() + bbox[1]
            w_h = bbox[3] - bbox[1]
            canvas_top = self._canvas.canvasy(0)
            canvas_h = self._canvas.winfo_height()
            total_h = self._scrollable_frame.winfo_height()
            if total_h <= 0:
                return
            if w_y < canvas_top:
                self._canvas.yview_moveto(max(0, w_y / total_h))
            elif w_y + w_h > canvas_top + canvas_h:
                target = (w_y + w_h - canvas_h) / total_h
                self._canvas.yview_moveto(min(1.0, max(0, target)))
        except tk.TclError:
            pass

    # ── 内嵌模式 ──

    def _show_embedded(self, current_chapter_index=0):
        # 清理之前快速翻页可能残留的孤儿窗口，防止显示错乱
        self._cleanup_pending_animation()
        if self._content_canvas and self._canvas_window_id:
            self._cleanup_orphan_windows()

        # 每次都重新构建，确保和当前章节数据一致
        self._volume_pages = self._build_volume_pages()

        self._reading_chapter_index = current_chapter_index

        # 找到当前阅读章节所在的卷页
        found_page = 0
        for pg, (_, vol_chapters) in enumerate(self._volume_pages):
            if any(ci == current_chapter_index for ci, _ in vol_chapters):
                found_page = pg
                break
        self._current_page = found_page

        self.current_highlight = 0
        if self._volume_pages:
            _, vol_chapters = self._volume_pages[self._current_page]
            for idx, (ci, _) in enumerate(vol_chapters):
                if ci == current_chapter_index:
                    self.current_highlight = idx
                    break

        self._render_embedded_page()
        self._update_highlight()
        # 弹性滑入动画（仅多卷时更明显）
        self._animate_slide_in()
        self._visible = True
        self.focus_set()

    def _hide_embedded(self):
        # 隐藏时停止动画，清理残留窗口，防止回到正文后回调访问已销毁的控件
        if self._anim_after_id is not None:
            try:
                self._content_canvas.after_cancel(self._anim_after_id)
            except Exception:
                pass
            self._anim_after_id = None
        self._cleanup_pending_animation()

    def on_chapter_selected(self, chapter_index):
        """章节被选中后的回调（由 MainWindow 调用）"""
        if self.toc_mode == "embedded":
            self._volume_pages = []