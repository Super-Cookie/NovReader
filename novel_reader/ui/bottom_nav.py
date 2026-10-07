"""底部导航栏 — 上一章 / 目录 / 下一章"""

import tkinter as tk
from novel_reader.config import (
    ACCENT_COLOR,
    TOC_FONT_FAMILY, dpf, dp,
    BTN_TEXT_COLOR, BTN_TEXT_DISABLED, BORDER_COLOR,
    READER_BOTTOM_NAV_HEIGHT, READER_BOTTOM_NAV_BTN_FONT_SIZE, READER_BOTTOM_NAV_CENTER_FONT_SIZE,
    TOOLBAR_BG,
)

class BottomNav(tk.Frame):
    """底部导航栏 — 上一章 | 目录 | 下一章"""

    def __init__(self, parent, on_prev, on_next, on_toc=None, **kwargs):
        super().__init__(parent, bg=TOOLBAR_BG, height=READER_BOTTOM_NAV_HEIGHT(), **kwargs)
        self.pack_propagate(False)
        self.on_prev = on_prev
        self.on_next = on_next
        self.on_toc = on_toc
        self._has_prev = True
        self._has_next = True
        self._build_ui()

    def _build_ui(self):
        side_font = (TOC_FONT_FAMILY, READER_BOTTOM_NAV_BTN_FONT_SIZE())
        mid_font = (TOC_FONT_FAMILY, READER_BOTTOM_NAV_CENTER_FONT_SIZE())

        # 居中容器
        center = tk.Frame(self, bg=TOOLBAR_BG)
        center.pack(expand=True, fill="both")

        # 按钮组（用 place 完美居中）
        btn_group = tk.Frame(center, bg=TOOLBAR_BG)
        btn_group.place(relx=0.48, rely=0.5, anchor="center")

        # 上一章
        self._prev_lbl = tk.Label(
            btn_group, text="\u25C0  上一章",
            font=side_font, bg=TOOLBAR_BG, fg=BTN_TEXT_COLOR,
            cursor="hand2", padx=dp(20), pady=dp(10),
        )
        self._prev_lbl.pack(side="left", padx=dp(8))
        self._prev_lbl.bind("<Button-1>", lambda e: self._on_prev_click())
        self._prev_lbl.bind("<Enter>", lambda e: self._on_hover("prev", True))
        self._prev_lbl.bind("<Leave>", lambda e: self._on_hover("prev", False))

        # 分隔符
        sep1 = tk.Frame(btn_group, bg=BORDER_COLOR, width=dp(1))
        sep1.pack(side="left", fill="y", padx=dp(6), pady=dp(8))

        # ── 目录按钮（纯黑色，无高亮）──
        self._toc_lbl = tk.Label(
            btn_group, text="\uD83D\uDCD6  目录",
            font=mid_font,
            bg=TOOLBAR_BG, fg="#1D1D1F",
            cursor="hand2", padx=dp(18), pady=dp(10),
        )
        self._toc_lbl.pack(side="left", padx=dp(4))
        self._toc_lbl.bind("<Button-1>", lambda e: self._on_toc_click())

        # 分隔符
        sep2 = tk.Frame(btn_group, bg=BORDER_COLOR, width=dp(1))
        sep2.pack(side="left", fill="y", padx=dp(6), pady=dp(8))

        # 下一章
        self._next_lbl = tk.Label(
            btn_group, text="下一章  \u25B6",
            font=side_font, bg=TOOLBAR_BG, fg=BTN_TEXT_COLOR,
            cursor="hand2", padx=dp(20), pady=dp(10),
        )
        self._next_lbl.pack(side="left", padx=dp(8))
        self._next_lbl.bind("<Button-1>", lambda e: self._on_next_click())
        self._next_lbl.bind("<Enter>", lambda e: self._on_hover("next", True))
        self._next_lbl.bind("<Leave>", lambda e: self._on_hover("next", False))

    def _on_prev_click(self):
        if self._has_prev:
            self.on_prev()

    def _on_next_click(self):
        if self._has_next:
            self.on_next()

    def _on_toc_click(self):
        if self.on_toc:
            self.on_toc()

    def _on_hover(self, section, entering):
        if section == "prev":
            if not self._has_prev:
                return
            self._prev_lbl.configure(
                fg=ACCENT_COLOR if entering else BTN_TEXT_COLOR)
        elif section == "next":
            if not self._has_next:
                return
            self._next_lbl.configure(
                fg=ACCENT_COLOR if entering else BTN_TEXT_COLOR)

    def _apply_state(self):
        if self._has_prev:
            self._prev_lbl.configure(fg=BTN_TEXT_COLOR, cursor="hand2")
        else:
            self._prev_lbl.configure(fg=BTN_TEXT_DISABLED, cursor="arrow")

        if self._has_next:
            self._next_lbl.configure(fg=BTN_TEXT_COLOR, cursor="hand2")
        else:
            self._next_lbl.configure(fg=BTN_TEXT_DISABLED, cursor="arrow")

    # ═══════════════════════════════════════════════════════════
    #  公开接口
    # ═══════════════════════════════════════════════════════════

    def update_info(self, chapter_index, total_chapters, chapter_title, volume_info=None):
        pass

    def update_buttons(self, has_prev, has_next):
        self._has_prev = has_prev
        self._has_next = has_next
        self._apply_state()