"""悬浮目录面板 - 应用内浮层"""

import tkinter as tk
from tkinter import ttk
from novel_reader.config import (
    READER_BG, WINDOW_BG, ACCENT_COLOR, BORDER_COLOR, SIDEBAR_BG,
    TOC_FONT_FAMILY, TOC_FONT_SIZE, TOC_VOLUME_FONT_SIZE,
    TOC_PANEL_WIDTH, TOC_PANEL_HEIGHT, TOC_COLUMN_WRAPLENGTH,
)
from novel_reader.utils.chinese_num import format_chapter_name
from novel_reader.models.chapter import ChapterType
import math


class TocPanel:
    """悬浮目录面板 - 应用内浮层覆盖"""

    COLS = 3
    PANEL_PAD = 80      # 面板距离父窗口边距
    COL_PAD = 10        # 列内边距

    def __init__(self, parent, book, on_chapter_select):
        self.parent = parent
        self.book = book
        self.on_chapter_select = on_chapter_select
        self.overlay = None
        self.panel = None
        self.grid_items = []
        self.current_highlight = 0
        self._visible = False
        self._mw_handler = None
        self._volumes = []
        self._volume_sticky_label = None
        self._sticky_after_id = None
        self._wraplength = TOC_COLUMN_WRAPLENGTH

    def _get_panel_size(self):
        """根据父窗口和配置计算面板尺寸"""
        try:
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
        except tk.TclError:
            pw, ph = 1200, 800
        w = min(pw - self.PANEL_PAD, TOC_PANEL_WIDTH)
        h = min(ph - 60, TOC_PANEL_HEIGHT)
        # 重新计算列换行宽度
        col_avail = (w - 40) // self.COLS  # 减去滚动条和内边距
        self._wraplength = max(col_avail - 16, 150)
        return w, h

    def _build_overlay(self):
        if self.overlay:
            return
        self.overlay = tk.Frame(self.parent, bg=WINDOW_BG)
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.overlay.lower()

        self.overlay.bind("<Button-1>", lambda e: self.hide())

        self.panel = tk.Frame(self.overlay, bg="#F5F5F7",
                               highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.panel.place(relx=0.5, rely=0.5, anchor="center")

        self.panel.bind("<Button-1>", lambda e: e.widget.focus_set())

        # 标题栏
        header = tk.Frame(self.panel, bg=SIDEBAR_BG, height=36)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_lbl = tk.Label(header, text="\uD83D\uDCD6  目录",
                              font=(TOC_FONT_FAMILY, TOC_FONT_SIZE + 1, "bold"),
                              bg=SIDEBAR_BG, fg="#1D1D1F")
        title_lbl.pack(side="left", padx=12, pady=4)

        close_btn = tk.Label(header, text="\u2715",
                              font=(TOC_FONT_FAMILY, 14),
                              bg=SIDEBAR_BG, fg="#86868B",
                              padx=12, pady=4, cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.hide())
        close_btn.bind("<Enter>", lambda e: close_btn.configure(fg="#1D1D1F"))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(fg="#86868B"))

        # 吸顶标签（初始隐藏）
        self._volume_sticky_label = tk.Label(
            self.panel, text="",
            font=(TOC_FONT_FAMILY, TOC_VOLUME_FONT_SIZE, "bold"),
            bg="#D8D8DC", fg="#1D1D1F",
            anchor="w", padx=12, pady=4,
        )

        # Canvas + 滚动条
        canvas_frame = tk.Frame(self.panel, bg="#F5F5F7")
        canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg="#F5F5F7", borderwidth=0, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview, width=40)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#F5F5F7")

        self.scrollable_frame.bind("<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        def _on_canvas_configure(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        self.canvas.bind("<Configure>", _on_canvas_configure)

        self.canvas.configure(yscrollcommand=self._on_canvas_scroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self._bind_mousewheel()

        for w in (self.overlay, self.panel, header, canvas_frame, self.canvas):
            w.bind("<Escape>", lambda e: self.hide())

        self.panel.bind("<Up>", lambda e: self._navigate_grid(-1, 0))
        self.panel.bind("<Down>", lambda e: self._navigate_grid(1, 0))
        self.panel.bind("<Left>", lambda e: self._navigate_grid(0, -1))
        self.panel.bind("<Right>", lambda e: self._navigate_grid(0, 1))
        self.panel.bind("<Return>", lambda e: self._select_highlighted())
        # Canvas 也绑定键盘导航（面板打开后焦点默认给 Canvas 以支持滚轮）
        self.canvas.bind("<Up>", lambda e: self._navigate_grid(-1, 0))
        self.canvas.bind("<Down>", lambda e: self._navigate_grid(1, 0))
        self.canvas.bind("<Left>", lambda e: self._navigate_grid(0, -1))
        self.canvas.bind("<Right>", lambda e: self._navigate_grid(0, 1))
        self.canvas.bind("<Return>", lambda e: self._select_highlighted())
        # 鼠标进入 Canvas 区域时自动聚焦
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set(), add="+")

    def _bind_mousewheel(self):
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            self._schedule_sticky_update()
            return "break"

        self._mw_handler = _on_mousewheel
        self.canvas.bind("<MouseWheel>", self._mw_handler, add="+")

    def _schedule_sticky_update(self):
        if self._sticky_after_id is not None:
            try:
                self.overlay.after_cancel(self._sticky_after_id)
            except Exception:
                pass
        self._sticky_after_id = self.overlay.after(30, self._do_sticky_update)

    def _on_canvas_scroll(self, *args):
        self.scrollbar.set(*args)
        self._schedule_sticky_update()

    def _do_sticky_update(self):
        self._sticky_after_id = None
        self._update_sticky_volume()

    def _update_sticky_volume(self):
        if not self._volumes or not self._volume_sticky_label:
            return
        try:
            canvas_top = self.canvas.canvasy(0)
        except Exception:
            return
        if canvas_top <= 0:
            if self._volume_sticky_label.winfo_manager():
                self._volume_sticky_label.pack_forget()
            return
        current_vol = None
        for vol_name, vol_label in self._volumes:
            try:
                label_y = vol_label.winfo_y()
            except Exception:
                continue
            if label_y <= canvas_top:
                current_vol = vol_name
            else:
                break
        current_text = self._volume_sticky_label.cget("text")
        if current_vol:
            new_text = "  " + current_vol
            if current_text != new_text:
                self._volume_sticky_label.configure(text=new_text)
            if not self._volume_sticky_label.winfo_manager():
                self._volume_sticky_label.pack(fill="x", before=self.canvas.master)
        else:
            if self._volume_sticky_label.winfo_manager():
                self._volume_sticky_label.pack_forget()

    def _update_panel_size(self):
        w, h = self._get_panel_size()
        try:
            self.panel.place_configure(width=w, height=h)
        except tk.TclError:
            pass

    def _get_chapter_bg(self, chapter_index):
        if chapter_index == self.current_highlight:
            return SIDEBAR_BG
        return "#F5F5F7"

    # -------- 渲染（Label Grid 方式）--------

    def _render_toc(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.grid_items = []
        self._volumes = []
        self._prev_highlight = -1

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

        if volumes:
            for vol_name, vol_chapters in volumes.items():
                # 卷标
                vol_label = tk.Label(self.scrollable_frame, text=vol_name,
                                      font=(TOC_FONT_FAMILY, TOC_VOLUME_FONT_SIZE, "bold"),
                                      bg=SIDEBAR_BG, fg="#1D1D1F",
                                      anchor="w", padx=10, pady=4)
                vol_label.pack(fill="x", pady=(8, 2))
                self._volumes.append((vol_name, vol_label))
                # 卷内章节（按每页 50 章切分）
                self._render_chapter_pages(self.scrollable_frame, vol_chapters)
        else:
            self._render_chapter_pages(self.scrollable_frame, no_volume)

        if self._mw_handler:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _render_chapter_pages(self, parent, chapters_group):
        """将章节分组（每页 50 章），每组一个 3 列 Label Grid"""
        page_size = 50
        total = len(chapters_group)
        if total <= page_size:
            self._build_page_grid(parent, chapters_group, page_label=None)
            return
        num_pages = math.ceil(total / page_size)
        for pg in range(num_pages):
            start = pg * page_size
            end = min(start + page_size, total)
            start_ch = start + 1
            page_text = f"第{pg + 1}页({start_ch}-{end}章)"
            page_label = tk.Label(parent,
                                   text=page_text,
                                   font=("Microsoft YaHei UI", 12, "bold"),
                                   bg="#F5F5F7", fg="#1D1D1F",
                                   anchor="w", padx=12, pady=6)
            page_label.pack(fill="x", pady=(6, 2))
            self._volumes.append((page_text, page_label))
            group = chapters_group[start:end]
            self._build_page_grid(parent, group, page_label=page_label)

    def _build_page_grid(self, parent, chapters_group, page_label=None):
        """
        用 Label + grid 构建 3 列单页布局。
        每行高度由该行最高 Label 决定（自动对齐）。
        """
        cols = self.COLS
        rows = math.ceil(len(chapters_group) / cols)
        wraplength = self._wraplength

        frame = tk.Frame(parent, bg="#F5F5F7")
        frame.pack(fill="x", padx=8, pady=(0, 6))

        # 配置网格行列权重
        for c in range(cols):
            frame.columnconfigure(c, weight=1, uniform="col")

        for idx, (ci, ch) in enumerate(chapters_group):
            row = idx // cols
            col = idx % cols
            display_name = format_chapter_name(ch.title)

            label = tk.Label(
                frame,
                text=display_name,
                font=(TOC_FONT_FAMILY, TOC_FONT_SIZE),
                bg="#F5F5F7", fg="#1D1D1F",
                anchor="nw", justify="left",
                wraplength=wraplength,
                padx=4, pady=2,
            )
            label.grid(row=row, column=col, sticky="nsew", padx=2, pady=1)

            # 事件绑定
            label.bind("<Button-1>", lambda e, i=ci: self._select_chapter(i))
            label.bind("<Enter>", lambda e, lbl=label: lbl.configure(bg="#D1D1D4"))
            label.bind("<Leave>", lambda e, lbl=label, i=ci:
                       lbl.configure(bg=self._get_chapter_bg(i)))

            self.grid_items.append((label, None, ci))

        # 让空列占位保持一致
        total_items = len(chapters_group)
        remaining = rows * cols - total_items
        if remaining > 0:
            for r in range(rows):
                for c in range(cols):
                    idx = r * cols + c
                    if idx >= total_items:
                        # 空占位 Label（透明）
                        spacer = tk.Label(frame, bg="#F5F5F7", text="", padx=4, pady=2)
                        spacer.grid(row=r, column=c, sticky="nsew", padx=2, pady=1)

    # -------- 交互逻辑 --------

    def _select_chapter(self, index):
        self.on_chapter_select(index)
        self.hide()

    def _navigate_grid(self, row_delta, col_delta):
        if not self.grid_items:
            return
        total = len(self.grid_items)
        if col_delta != 0:
            new_idx = self.current_highlight + col_delta
        else:
            new_idx = self.current_highlight + row_delta * self.COLS
        new_idx = max(0, min(total - 1, new_idx))
        self.current_highlight = new_idx
        self._update_highlight()
        self._scroll_to_highlighted()

    def _update_highlight(self):
        prev = getattr(self, '_prev_highlight', -1)
        if prev == self.current_highlight:
            return
        # 清除旧高亮
        if 0 <= prev < len(self.grid_items):
            widget, _, _ = self.grid_items[prev]
            try:
                widget.configure(bg="#F5F5F7",
                                  font=(TOC_FONT_FAMILY, TOC_FONT_SIZE))
            except tk.TclError:
                pass
        # 设置新高亮
        if 0 <= self.current_highlight < len(self.grid_items):
            widget, _, _ = self.grid_items[self.current_highlight]
            try:
                widget.configure(bg=SIDEBAR_BG,
                                  font=(TOC_FONT_FAMILY, TOC_FONT_SIZE, "bold"))
            except tk.TclError:
                pass
        self._prev_highlight = self.current_highlight

    def _scroll_to_highlighted(self):
        if not self.grid_items or self.current_highlight >= len(self.grid_items):
            return
        widget, _, _ = self.grid_items[self.current_highlight]
        try:
            w_y = widget.winfo_y()
            w_h = widget.winfo_height()
            canvas_top = self.canvas.canvasy(0)
            canvas_h = self.canvas.winfo_height()
            total_h = self.scrollable_frame.winfo_height()
            if total_h <= 0:
                return
            if w_y < canvas_top:
                self.canvas.yview_moveto(max(0, w_y / total_h))
            elif w_y + w_h > canvas_top + canvas_h:
                target = (w_y + w_h - canvas_h) / total_h
                self.canvas.yview_moveto(min(1.0, max(0, target)))
        except tk.TclError:
            pass

    def _select_highlighted(self):
        if not self._visible:
            return
        if self.grid_items and self.current_highlight < len(self.grid_items):
            _, _, ci = self.grid_items[self.current_highlight]
            self._select_chapter(ci)

    # -------- 生命周期 --------

    def show(self, current_chapter_index=0):
        if not self.overlay:
            self._build_overlay()
            self._update_panel_size()
            self.overlay.lift()
            self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.overlay.update_idletasks()
            self._render_toc()
            self.scrollable_frame.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        else:
            self._update_panel_size()
            self.overlay.lift()
            self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._visible = True
        # 聚焦到 Canvas，鼠标滚轮立即生效（Windows 上滚轮事件跟随焦点）
        self.canvas.focus_set()
        if self._volume_sticky_label:
            self._volume_sticky_label.pack_forget()
        if 0 <= current_chapter_index < len(self.grid_items):
            self.current_highlight = current_chapter_index
            self._update_highlight()
            self._scroll_to_highlighted()
        self.overlay.after(50, self._do_sticky_update)

    def hide(self):
        if self.overlay:
            self.overlay.place_forget()
        if self._volume_sticky_label:
            self._volume_sticky_label.pack_forget()
        self._visible = False

    def is_visible(self):
        return self._visible

    def refresh(self):
        if self.overlay:
            self._render_toc()

    def destroy(self):
        if self.overlay:
            self.overlay.destroy()
            self.overlay = None
            self.panel = None
            self._volume_sticky_label = None
            self._volumes = []