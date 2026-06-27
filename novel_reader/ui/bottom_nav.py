"""底部导航栏 - 油猴脚本风格，固定显示"""

import tkinter as tk
from tkinter import ttk, font
from novel_reader.config import WINDOW_BG, READER_BG, ACCENT_COLOR, BORDER_COLOR, NAV_BG, TOC_FONT_FAMILY


class BottomNav(ttk.Frame):
    """底部导航栏 - 油猴脚本风格，固定显示"""

    def __init__(self, parent, on_prev, on_next, on_toc=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_prev = on_prev
        self.on_next = on_next
        self.on_toc = on_toc
        self._build_ui()

    def _build_ui(self):
        self.configure(style="BottomNav.TFrame")
        style = ttk.Style()
        style.configure("BottomNav.TFrame", background="#FFFFFF")

        sep = tk.Frame(self, bg="#000000", height=2)
        sep.pack(fill="x", side="top")

        nav_frame = tk.Frame(self, bg="#FFFFFF", bd=0)
        nav_frame.pack(fill="x", padx=20, pady=8)

        nav_frame.columnconfigure(0, weight=0)
        nav_frame.columnconfigure(1, weight=1)
        nav_frame.columnconfigure(2, weight=0)

        self.prev_btn = tk.Label(
            nav_frame,
            text="\u25C0  上一章",
            font=(TOC_FONT_FAMILY, 12),
            bg="#4A6A8B", fg="white",
            padx=16, pady=8,
            cursor="hand2",
        )
        self.prev_btn.grid(row=0, column=0, padx=(0, 4), pady=4)
        self.prev_btn.bind("<Button-1>", lambda e: self.on_prev())
        self.prev_btn.bind("<Enter>", lambda e: self.prev_btn.configure(bg="#3A5A7B"))
        self.prev_btn.bind("<Leave>", lambda e: self._update_prev_style())

        info_frame = tk.Frame(nav_frame, bg="#FFFFFF", cursor="hand2")
        info_frame.grid(row=0, column=1, sticky="nsew", padx=8)
        info_frame.bind("<Button-1>", lambda e: self._on_toc_click())
        info_frame.bind("<Enter>", lambda e: self._on_info_enter())
        info_frame.bind("<Leave>", lambda e: self._on_info_leave())

        self.chapter_label = tk.Label(
            info_frame, text="",
            font=(TOC_FONT_FAMILY, 14, "bold"),
            fg="#333333", bg="#FFFFFF",
            cursor="hand2",
        )
        self.chapter_label.pack()
        self.chapter_label.bind("<Button-1>", lambda e: self._on_toc_click())
        self.chapter_label.bind("<Enter>", lambda e: self._on_info_enter())
        self.chapter_label.bind("<Leave>", lambda e: self._on_info_leave())

        self.progress_label = tk.Label(
            info_frame, text="",
            font=(TOC_FONT_FAMILY, 11),
            fg="#666666", bg="#FFFFFF",
            cursor="hand2",
        )
        self.progress_label.pack()
        self.progress_label.bind("<Button-1>", lambda e: self._on_toc_click())
        self.progress_label.bind("<Enter>", lambda e: self._on_info_enter())
        self.progress_label.bind("<Leave>", lambda e: self._on_info_leave())

        self.next_btn = tk.Label(
            nav_frame,
            text="下一章  \u25B6",
            font=(TOC_FONT_FAMILY, 12),
            bg="#4A6A8B", fg="white",
            padx=16, pady=8,
            cursor="hand2",
        )
        self.next_btn.grid(row=0, column=2, padx=(4, 0), pady=4)
        self.next_btn.bind("<Button-1>", lambda e: self.on_next())
        self.next_btn.bind("<Enter>", lambda e: self.next_btn.configure(bg="#3A5A7B"))
        self.next_btn.bind("<Leave>", lambda e: self._update_next_style())

    def update_info(self, chapter_index, total_chapters, chapter_title, volume_info=None):
        self.chapter_label.configure(text=chapter_title)

        if volume_info and volume_info["volume_name"]:
            vi = volume_info
            parts = []
            if vi["volume_count"] > 0:
                parts.append(f"第{vi['volume_order']}卷 {vi['volume_name']}")
            parts.append(f"第{vi['within_vol_index']}章/共{vi['within_vol_total']}章")
            if vi["volume_count"] > 0:
                parts.append(f"共{vi['volume_count']}卷")
            self.progress_label.configure(text=" · ".join(parts))
        else:
            self.progress_label.configure(
                text=f"第 {chapter_index + 1} 章 / 共 {total_chapters} 章"
            )

    def update_buttons(self, has_prev, has_next):
        self._has_prev = has_prev
        self._has_next = has_next
        self._update_prev_style()
        self._update_next_style()

    def _update_prev_style(self):
        if getattr(self, '_has_prev', True):
            self.prev_btn.configure(bg="#4A6A8B", fg="white")
        else:
            self.prev_btn.configure(bg="#A6A6A6", fg="#E0E0E0")

    def _on_toc_click(self):
        if self.on_toc:
            self.on_toc()

    def _on_info_enter(self):
        self.chapter_label.configure(fg=ACCENT_COLOR)
        self.progress_label.configure(fg=ACCENT_COLOR)

    def _on_info_leave(self):
        self.chapter_label.configure(fg="#333333")
        self.progress_label.configure(fg="#666666")

    def _update_next_style(self):
        if getattr(self, '_has_next', True):
            self.next_btn.configure(bg="#4A6A8B", fg="white")
        else:
            self.next_btn.configure(bg="#A6A6A6", fg="#E0E0E0")