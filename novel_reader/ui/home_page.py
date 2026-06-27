"""首页（类VSCode欢迎页） - macOS 风格"""

import tkinter as tk
from tkinter import ttk, font
import os
from novel_reader.config import (
    WINDOW_BG, READER_BG, TEXT_COLOR, ACCENT_COLOR, BORDER_COLOR,
    SHOW_RECENT_ON_HOME, KEY_OPEN_FILE, TOC_FONT_FAMILY,
)
from novel_reader.utils.file_utils import get_recent_files


class HomePage(ttk.Frame):
    """首页 - macOS 风格欢迎页"""

    def __init__(self, parent, on_open_file, on_open_recent, on_new_window, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_open_file = on_open_file
        self.on_open_recent = on_open_recent
        self.on_new_window = on_new_window
        self._build_ui()

    def _build_ui(self):
        style = ttk.Style()
        style.configure("Home.TFrame", background=WINDOW_BG)
        self.configure(style="Home.TFrame")

        # 居中容器
        center_frame = tk.Frame(self, bg=WINDOW_BG)
        center_frame.place(relx=0.5, rely=0.38, anchor="center")

        # 标题
        title_label = tk.Label(
            center_frame,
            text="NovReader",
            font=(TOC_FONT_FAMILY, 32, "bold"),
            fg="#1D1D1F",
            bg=WINDOW_BG,
        )
        title_label.pack(pady=(0, 6))

        # 副标题
        subtitle_label = tk.Label(
            center_frame,
            text="小说阅读器  ·  .nov",
            font=(TOC_FONT_FAMILY, 13),
            fg="#86868B",
            bg=WINDOW_BG,
        )
        subtitle_label.pack(pady=(0, 36))

        # 快捷键提示
        shortcuts_frame = tk.Frame(center_frame, bg=WINDOW_BG)
        shortcuts_frame.pack(pady=(0, 24))

        shortcuts = [
            ("\u2318O", "打开文件"),
            ("\u2318N", "新建窗口"),
            ("\u2190 \u2192", "翻章"),
            ("\u23CE", "打开目录"),
        ]

        for key, desc in shortcuts:
            row = tk.Frame(shortcuts_frame, bg=WINDOW_BG)
            row.pack(fill="x", pady=3)
            key_label = tk.Label(
                row, text=key,
                font=(TOC_FONT_FAMILY, 11) if TOC_FONT_FAMILY in font.families() else ("Consolas", 11),
                bg="#E8E8EA", fg="#1D1D1F",
                padx=10, pady=3,
                borderwidth=0,
            )
            key_label.pack(side="left", padx=(0, 12))
            desc_label = tk.Label(
                row, text=desc,
                font=(TOC_FONT_FAMILY, 12),
                fg="#86868B", bg=WINDOW_BG,
            )
            desc_label.pack(side="left")

        # 打开文件按钮（macOS 风格圆角按钮）
        open_btn = tk.Button(
            center_frame,
            text="打开文件",
            font=(TOC_FONT_FAMILY, 14),
            bg=ACCENT_COLOR,
            fg="white",
            padx=40, pady=8,
            borderwidth=0,
            cursor="hand2",
            command=self.on_open_file,
            activebackground="#0066CC",
            activeforeground="white",
        )
        open_btn.pack(pady=(6, 0))

        # 最近打开文件
        if SHOW_RECENT_ON_HOME:
            self._build_recent_section(center_frame)

    def _build_recent_section(self, parent):
        """构建最近打开文件区域"""
        recent_files = get_recent_files()
        if not recent_files:
            return

        sep = ttk.Separator(parent, orient="horizontal")
        sep.pack(fill="x", pady=(28, 14))

        recent_title = tk.Label(
            parent,
            text="最近打开",
            font=(TOC_FONT_FAMILY, 11, "bold"),
            fg="#86868B",
            bg=WINDOW_BG,
        )
        recent_title.pack(anchor="w", pady=(0, 8))

        self.recent_frame = tk.Frame(parent, bg=WINDOW_BG)
        self.recent_frame.pack(fill="x")

        for i, filepath in enumerate(recent_files[:10]):
            self._add_recent_item(self.recent_frame, filepath, i)

    def _add_recent_item(self, parent, filepath, index):
        """添加一个最近打开文件条目"""
        item_frame = tk.Frame(parent, bg=WINDOW_BG)
        item_frame.pack(fill="x", pady=1)

        link = tk.Label(
            item_frame,
            text=f"  {os.path.basename(filepath)}",
            font=(TOC_FONT_FAMILY, 12),
            fg=ACCENT_COLOR,
            bg=WINDOW_BG,
            cursor="hand2",
            anchor="w",
        )
        link.pack(side="left")

        link.bind("<Button-1>", lambda e, fp=filepath: self.on_open_recent(fp))
        link.bind("<Enter>", lambda e, l=link: l.configure(fg="#0066CC"))
        link.bind("<Leave>", lambda e, l=link: l.configure(fg=ACCENT_COLOR))

    def refresh(self):
        """刷新最近文件列表"""
        if SHOW_RECENT_ON_HOME and hasattr(self, 'recent_frame'):
            self.recent_frame.destroy()
            self._build_recent_section(self.recent_frame.master)