"""小说阅读视图 - 起点风格排版 + macOS 风格"""

import sys
import os
import time
import tkinter as tk
from tkinter import ttk, font as tkfont
from novel_reader.config import (
    READER_BG, READER_MARGIN_BG, WINDOW_BG, TEXT_COLOR, ACCENT_COLOR, BORDER_COLOR,
    BASE_FONT_FAMILY, BASE_FONT_SIZE, HEADING_FONT_SIZE,
    TITLE_FONT_FAMILY, TITLE_FONT_SIZE, VOLUME_FONT_SIZE, TEXT_INDENT_CHARS,
    LINE_SPACING, PARAGRAPH_SPACING,
    FONT_SPACING, DEFAULT_WIN_WIDTH, MAX_LINES_PER_PARAGRAPH,
    SCROLLBAR_WIDTH, READER_PADX_PERCENT, READER_TEXT_PADX_PERCENT,
    KEY_PREV_CHAPTER, KEY_NEXT_CHAPTER, KEY_OPEN_TOC,
    dp,
)
from novel_reader.utils.chinese_num import format_chapter_name
from novel_reader.models.chapter import ChapterType


class ReaderView(ttk.Frame):
    """阅读视图 - 起点风格排版"""

    def __init__(self, parent, book, on_chapter_change=None, on_toc_toggle=None, font_size=None, indent_chars=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.book = book
        self.current_chapter_index = 0
        self.on_chapter_change = on_chapter_change
        self.on_toc_toggle = on_toc_toggle
        self.font_size = font_size if font_size is not None else BASE_FONT_SIZE()
        if indent_chars is None or indent_chars <= 0:
            self.indent_chars = TEXT_INDENT_CHARS
        else:
            self.indent_chars = indent_chars
        self._build_ui()
        self._setup_keybindings()
        self._rendering = False
        self._estimated_width = 0
        # 高帧率惯性滚动状态
        self._velocity = 0.0
        self._inertia_anim_id = None
        self._last_inertia_time = 0.0
        self.FRAME_MS = ReaderView._detect_frame_ms()

    def _build_ui(self):
        self.configure(style="Reader.TFrame")
        style = ttk.Style()
        style.configure("Reader.TFrame", background=WINDOW_BG)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # 阅读卡片容器：居中，两侧留白
        card_frame = tk.Frame(self, bg=WINDOW_BG)
        card_frame.grid(row=0, column=0, sticky="nsew")
        card_frame.columnconfigure(0, weight=1)
        card_frame.rowconfigure(0, weight=1)
        card_frame.rowconfigure(1, weight=0)

        # 三段式阅读区布局
        # 外层：正文区外左右边距（READER_MARGIN_BG 色）
        self.margin_frame = tk.Frame(card_frame, bg=READER_MARGIN_BG)
        self.margin_frame.grid(row=0, column=0, sticky="nsew")

        self.left_margin = tk.Frame(self.margin_frame, bg=READER_MARGIN_BG)
        self.left_margin.place(relx=0, rely=0, relwidth=READER_PADX_PERCENT, relheight=1)

        self.right_margin = tk.Frame(self.margin_frame, bg=READER_MARGIN_BG)
        self.right_margin.place(relx=1 - READER_PADX_PERCENT, rely=0,
                                 relwidth=READER_PADX_PERCENT, relheight=1)

        # 中层：正文区容器（正文 + 正文左右边距，READER_BG 色）
        content_relx = READER_PADX_PERCENT
        content_relwidth = 1 - 2 * READER_PADX_PERCENT
        self.content_frame = tk.Frame(self.margin_frame, bg=READER_BG)
        self.content_frame.place(relx=content_relx, rely=0,
                                  relwidth=content_relwidth, relheight=1)

        # 内层：正文左右边距（READER_BG 色）
        self.inner_left = tk.Frame(self.content_frame, bg=READER_BG)
        self.inner_left.place(relx=0, rely=0, relwidth=READER_TEXT_PADX_PERCENT, relheight=1)

        self.inner_right = tk.Frame(self.content_frame, bg=READER_BG)
        self.inner_right.place(relx=1 - READER_TEXT_PADX_PERCENT, rely=0,
                                relwidth=READER_TEXT_PADX_PERCENT, relheight=1)

        # 滚动条（右侧，细圆角）
        self.scrollbar = tk.Scrollbar(card_frame, orient="vertical",
                                       width=SCROLLBAR_WIDTH(),
                                       bg="#C8C8C8", troughcolor=WINDOW_BG,
                                       activebackground="#AAAAAA",
                                       borderwidth=0, highlightthickness=0,
                                       relief="flat")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # 文本区域
        indent_px = self._calc_indent_px()
        self._body_font_name = "ReaderBodyFont"
        try:
            self.tk.call("font", "delete", self._body_font_name)
        except tk.TclError:
            pass
        self.tk.call("font", "create", self._body_font_name,
            "-family", BASE_FONT_FAMILY,
            "-size", self.font_size,
            "-weight", "normal")
        self.text_widget = tk.Text(
            self.content_frame,
            wrap="word",
            borderwidth=0,
            bg=READER_BG,
            fg=TEXT_COLOR,
            font=self._body_font_name,
            padx=0, pady=dp(20),
            spacing1=PARAGRAPH_SPACING(),
            spacing2=LINE_SPACING(),
            spacing3=PARAGRAPH_SPACING(),
            cursor="arrow",
            yscrollcommand=self.scrollbar.set,
            state="disabled",
            highlightthickness=0,
        )
        self.text_widget.place(relx=READER_TEXT_PADX_PERCENT, rely=0,
                                relwidth=1 - 2 * READER_TEXT_PADX_PERCENT, relheight=1)
        self.scrollbar.config(command=self.text_widget.yview)

        # 绑定尺寸变化事件：窗口缩放时自动重新切分段落
        self.text_widget.bind("<Configure>", self._on_text_resize, add="+")

        # 底部进度条
        self.progress_bar = tk.Frame(card_frame, bg=BORDER_COLOR, height=dp(2))
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew")



        # 配置文本标签
        self._configure_tags(indent_px)

        # 绑定滚动事件
        self.text_widget.bind("<MouseWheel>", self._on_scroll)

    def _calc_indent_px(self):
        """计算首行缩进像素值：精确测量中文字符宽度，确保缩进等于 indent_chars 个中文字符"""
        f = tkfont.Font(family=BASE_FONT_FAMILY, size=self.font_size)
        char_width = f.measure("中")
        if FONT_SPACING:
            thin_w = f.measure('\u2009')
            char_width += FONT_SPACING * thin_w
        return self.indent_chars * char_width

    def _configure_tags(self, indent_px):
        """配置文本标签样式"""
        # 书名（全书标题）
        self.text_widget.tag_configure("title",
            font=(TITLE_FONT_FAMILY, TITLE_FONT_SIZE(), "bold"),
            foreground="#1A1A1A",
            spacing1=dp(12), spacing3=dp(12),
            justify="center",
        )
        # 卷名（居中分隔）
        self.text_widget.tag_configure("volume",
            font=(TITLE_FONT_FAMILY, VOLUME_FONT_SIZE(), "bold"),
            foreground="#555555",
            spacing1=dp(16), spacing3=dp(6),
            justify="center",
        )
        # 章节标题（居中，大号）
        self.text_widget.tag_configure("chapter",
            font=(BASE_FONT_FAMILY, HEADING_FONT_SIZE(), "bold"),
            foreground="#1A1A1A",
            spacing1=dp(12), spacing3=dp(8),
            justify="center",
        )
        # 序言
        self.text_widget.tag_configure("preface",
            font=(BASE_FONT_FAMILY, HEADING_FONT_SIZE() + 2, "bold"),
            foreground="#1A1A1A",
            spacing1=dp(12), spacing3=dp(8),
            justify="center",
        )
        # 后记
        self.text_widget.tag_configure("postscript",
            font=(BASE_FONT_FAMILY, HEADING_FONT_SIZE() + 2, "bold"),
            foreground="#1A1A1A",
            spacing1=dp(12), spacing3=dp(8),
            justify="center",
        )
        # 正文段落：首行缩进，后续行不缩进
        self.text_widget.tag_configure("paragraph",
            font=self._body_font_name,
            foreground=TEXT_COLOR,
            spacing1=PARAGRAPH_SPACING(),
            spacing3=PARAGRAPH_SPACING(),
            lmargin1=indent_px,
            lmargin2=0,
        )
        # 分隔线
        self.text_widget.tag_configure("separator",
            foreground="#C0C0C0",
            font=(BASE_FONT_FAMILY, dp(4)),
            spacing1=dp(4), spacing3=dp(4),
            justify="center",
        )
        # 居中
        self.text_widget.tag_configure("center", justify="center")

    def _setup_keybindings(self):
        self.text_widget.bind(KEY_PREV_CHAPTER, lambda e: (self.navigate(-1), "break")[1])
        self.text_widget.bind(KEY_NEXT_CHAPTER, lambda e: (self.navigate(1), "break")[1])
        self.text_widget.bind("<Up>", lambda e: self._scroll_line(-1))
        self.text_widget.bind("<Down>", lambda e: self._scroll_line(1))
        self.text_widget.bind(KEY_OPEN_TOC, lambda e: (self._toggle_toc(), "break")[1])
        self.text_widget.bind("<Button-1>", lambda e: self.text_widget.focus_set())
        self.text_widget.focus_set()

    def _scroll_line(self, direction):
        """键盘 ↑↓ — 直接滚动 1 行，不触发惯性"""
        self._cancel_inertia()
        self._apply_scroll(direction * 1.0)
        return "break"

    def _toggle_toc(self):
        if self.on_toc_toggle:
            self.on_toc_toggle()

    def _on_scroll(self, event=None):
        """鼠标滚轮 — 物理惯性滚动（高帧率 ~120fps）"""
        if self._inertia_anim_id:
            self.after_cancel(self._inertia_anim_id)
            self._inertia_anim_id = None

        lines = event.delta / 120
        delta = -lines * 1.5   # 每格 ≈ 1.5 行（不累加，防止连续滚动飞到底部）
        self._velocity = delta              # 设定本次速度（不累加，避免多格叠加失控）
        self._apply_scroll(delta)            # 立即跟随
        self._start_inertia()                # 松手后惯性衰减
        if self.on_chapter_change:
            self.on_chapter_change(self.current_chapter_index, self.text_widget.yview()[0])
        return "break"

    def _get_line_height(self):
        """估算单行文本的像素高度"""
        try:
            f = tkfont.Font(font=self._body_font_name)
            return f.metrics("linespace") + LINE_SPACING()
        except Exception:
            return self.font_size + dp(4)

    # ── 高帧率惯性滚动核心 ──────────────────────────
    FRICTION = 0.92            # 摩擦力系数（越小停越快）
    VELOCITY_THRESHOLD = 0.05  # 速度低于此值停止
    FRAME_MS = None            # 启动时动态检测

    @staticmethod
    def _detect_frame_ms():
        """检测主显示器刷新率，返回最佳帧间隔（ms）

        优先 Windows GetDeviceCaps(VREFRESH)，
        失败则默认 8ms（≈120fps，满足 60~240Hz 需求）
        """
        try:
            import ctypes
            dc = ctypes.windll.user32.GetDC(0)
            # 116 = VREFRESH, 返回赫兹值（如 60、120、144）
            hz = ctypes.windll.gdi32.GetDeviceCaps(dc, 116)
            ctypes.windll.user32.ReleaseDC(0, dc)
            if hz is not None and 30 <= hz <= 500:
                # 匹配刷新周期，但保底 120fps（低刷屏过采样更跟手）
                return min(int(1000 / hz), 8)
        except Exception:
            pass
        return 8  # 兜底 120fps

    def _apply_scroll(self, line_delta):
        """按行数直接定位（像素级精度）"""
        vp_h = self.text_widget.winfo_height()
        if vp_h < 10:
            return
        line_h = self._get_line_height()
        frac_per_line = line_h / vp_h
        current = self.text_widget.yview()[0]
        target = max(0.0, min(1.0, current + line_delta * frac_per_line))
        self.text_widget.yview_moveto(target)

    def _start_inertia(self):
        """启动惯性衰减阶段"""
        self._last_inertia_time = 0.0
        self._inertia_anim_id = self.after(self.FRAME_MS, self._inertia_step)

    def _cancel_inertia(self):
        if self._inertia_anim_id:
            self.after_cancel(self._inertia_anim_id)
            self._inertia_anim_id = None
        self._velocity = 0.0

    def _inertia_step(self):
        """惯性物理迭代：摩擦力衰减 → 滚动 → 循环"""
        now = time.monotonic()
        if self._last_inertia_time <= 0:
            self._last_inertia_time = now

        # 帧率无关：根据真实时间差调整摩擦力指数
        dt = now - self._last_inertia_time
        self._last_inertia_time = now
        # 基准 60fps = 16.67ms，以此为 1.0 缩放
        norm = max(0.5, dt / 0.01667)
        self._velocity *= self.FRICTION ** norm

        if abs(self._velocity) < self.VELOCITY_THRESHOLD:
            self._velocity = 0.0
            self._inertia_anim_id = None
            return

        self._apply_scroll(self._velocity)
        self._inertia_anim_id = self.after(self.FRAME_MS, self._inertia_step)

    def _get_text_widget_width(self):
        """获取 text_widget 的实际可用像素宽度

        策略：
        1. 先强制完成布局（update_idletasks），尝试 winfo_width
        2. 如果还没映射到屏幕（返回 1），从窗口配置减去界面元素宽度估算
        """
        self.text_widget.update_idletasks()
        w = self.text_widget.winfo_width()
        if w > 1:
            self._estimated_width = w
            return w

        # 窗口还没显示，从配置估算：
        # DEFAULT_WIN_WIDTH - 窗口边框(~16) - 滚动条(48) - notebook边框(~4) - 间距
        estimated_chrome = dp(80)
        estimated = max(dp(200), DEFAULT_WIN_WIDTH() - estimated_chrome)
        self._estimated_width = estimated
        return estimated

    def _apply_char_spacing(self, text):
        """为正文添加字符间距：在 CJK 字后插入细空格（\u2009, ~1px）"""
        if not FONT_SPACING or not text:
            return text
        gap = '\u2009' * FONT_SPACING  # 每个配置单位 = 1px
        spaced = []
        for ch in text:
            spaced.append(ch)
            if '\u4e00' <= ch <= '\u9fff':
                spaced.append(gap)
        return ''.join(spaced)

    def _calc_dynamic_max_chars(self):
        """根据当前控件宽度和字号，计算段落切分阈值

        返回: (max_chars, chars_per_line, char_width) 供调试参考
        """
        widget_width = self._get_text_widget_width()
        available_width = widget_width

        f = tkfont.Font(family=BASE_FONT_FAMILY, size=self.font_size)
        char_width = f.measure("中")
        if FONT_SPACING:
            # 字符间距：通过插入细空格实现，每个细空格 ≈ 1px
            thin_w = f.measure('\u2009')
            char_width += FONT_SPACING * thin_w
        if char_width <= 0:
            char_width = self.font_size  # fallback 粗略估算

        chars_per_line = max(1, available_width // char_width)
        max_chars = int(chars_per_line * MAX_LINES_PER_PARAGRAPH)
        return max_chars, chars_per_line, char_width

    def _split_paragraphs_dynamic(self, paragraphs):
        """根据当前控件宽度和字号，动态切分过长段落"""
        max_chars, chars_per_line, char_width = self._calc_dynamic_max_chars()

        result = []
        for para in paragraphs:
            if not para or len(para) <= max_chars:
                result.append(para)
                continue

            start = 0
            while start < len(para):
                end = min(start + max_chars, len(para))
                if end < len(para):
                    # 优先在句子结束标点处切分（从后往前查找）
                    cut = end
                    for sep in '。！？；':
                        pos = para.rfind(sep, start, end)
                        if pos > start:
                            cut = pos + 1  # 标点归入上一段
                            break
                    # 次优：在句中停顿标点处切分
                    if cut == end:
                        for sep in '，、：':
                            pos = para.rfind(sep, start, end)
                            if pos > start:
                                cut = pos + 1
                                break
                    segment = para[start:cut].strip()
                    if segment:
                        result.append(segment)
                    start = cut
                else:
                    segment = para[start:end].strip()
                    if segment:
                        result.append(segment)
                    break
        return result

    def _on_text_resize(self, event):
        """文本控件尺寸变化时重新切分段落（自适应窗口缩放）"""
        if event.width <= 1:
            return
        if getattr(self, '_rendering', False):
            return
        # 防抖：快速缩放时只触发最后一次
        timer = getattr(self, '_resize_timer', None)
        if timer:
            self.after_cancel(timer)
        self._resize_timer = self.after(150, self._re_render_current)

    def _re_render_current(self):
        """重新渲染当前章节（保留滚动位置）"""
        if getattr(self, '_rendering', False):
            return
        scroll_pos = self.get_scroll_position()
        # 重新计算 max_chars 并更新显示
        self.text_widget.configure(state="normal")
        self._render_paragraphs(self.current_chapter_index)
        self.text_widget.configure(state="disabled")
        self.set_scroll_position(min(scroll_pos, 1.0))

    def _calibrate_render(self):
        """窗口首次显示后，用真实宽度校准段落切分"""
        self._calibrate_timer = None
        if getattr(self, '_rendering', False):
            return
        # 用 update_idletasks 确保拿到真实宽度
        self.text_widget.update_idletasks()
        real_w = self.text_widget.winfo_width()
        if real_w <= 1:
            # 窗口仍不可见，等下次校准
            self._calibrate_timer = self.after(200, self._calibrate_render)
            return
        # 测量并输出实际比例（仅 py 源码模式）
        self._log_ratios()
        # 计算估算时用的宽度
        estimated = getattr(self, '_estimated_width', 0)
        if estimated and estimated == real_w:
            return  # 宽度没变，无需重排
        self._estimated_width = real_w
        scroll_pos = self.get_scroll_position()
        self.text_widget.configure(state="normal")
        self._render_paragraphs(self.current_chapter_index)
        self.text_widget.configure(state="disabled")
        self.set_scroll_position(min(scroll_pos, 1.0))

    def _log_ratios(self):
        """输出实际测量的边距/正文比例（仅 py 源码运行，写入 .gitignore 忽略的 debug 目录）"""
        if getattr(sys, 'frozen', False):
            return
        if getattr(self, '_ratios_logged', False):
            return
        self._ratios_logged = True
        try:
            margin_w = self.margin_frame.winfo_width()
            content_w = self.content_frame.winfo_width()
            text_w = self.text_widget.winfo_width()
            if margin_w <= 1 or content_w <= 1 or text_w <= 1:
                return
            outer_side = (margin_w - content_w) / 2
            inner_side = (content_w - text_w) / 2
            outer_pct = outer_side / margin_w * 100
            content_pct = content_w / margin_w * 100
            inner_pct = inner_side / margin_w * 100
            text_pct = text_w / margin_w * 100

            prj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_dir = os.path.join(prj_root, "debug")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "layout_ratios.log")

            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"READER_PADX_PERCENT = {READER_PADX_PERCENT}\n")
                f.write(f"READER_TEXT_PADX_PERCENT = {READER_TEXT_PADX_PERCENT}\n")
                f.write(f"margin_frame 总宽: {margin_w}px\n")
                f.write(f"  正文区外左 margin: {outer_side:.0f}px ({outer_pct:.1f}%)\n")
                f.write(f"  正文区内左 margin: {inner_side:.0f}px ({inner_pct:.1f}%)\n")
                f.write(f"  正文:              {text_w}px ({text_pct:.1f}%)\n")
                f.write(f"  正文区内右 margin: {inner_side:.0f}px ({inner_pct:.1f}%)\n")
                f.write(f"  正文区外右 margin: {outer_side:.0f}px ({outer_pct:.1f}%)\n")

            if getattr(self, '_on_ratios_logged', None):
                self._on_ratios_logged(log_path)
        except Exception:
            pass

    def _render_paragraphs(self, index):
        """渲染指定章节的正文段落部分（仅内容区域，不修改标题/滚动/状态）"""
        chapter = self.book.get_chapter(index)
        if not chapter:
            return

        # 找到段落区域的起始位置
        # 保留标题和分隔线，只替换段落内容
        self.text_widget.delete("paragraph_start", "end")

        # 渲染段落（动态切分）
        split_paras = self._split_paragraphs_dynamic(chapter.paragraphs)
        for para in split_paras:
            if para.strip():
                spaced = self._apply_char_spacing(para.strip())
                self.text_widget.insert("end", spaced + "\n", "paragraph")

    def render_chapter(self, index):
        """渲染章节"""
        self._rendering = True
        chapter = self.book.get_chapter(index)
        if not chapter:
            self._rendering = False
            return

        self.current_chapter_index = index

        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", "end")

        # 渲染章节标题
        display_title = format_chapter_name(chapter.title)
        tag = "chapter"
        if chapter.type == ChapterType.TITLE:
            tag = "title"
        elif chapter.type == ChapterType.PREFACE:
            tag = "preface"
        elif chapter.type == ChapterType.POSTSCRIPT:
            tag = "postscript"

        self.text_widget.insert("end", "\n")

        # 卷名 + 章节名 同一行（空格隔开）
        if chapter.volume_name:
            combined = f"{chapter.volume_name} {display_title}"
        else:
            combined = display_title
        self.text_widget.insert("end", combined + "\n", tag)
        self.text_widget.insert("end", "· · ·\n", "separator")
        self.text_widget.insert("end", "\n")

        # 在段落起始位置设置书签标记，供 _render_paragraphs 增量替换使用
        self.text_widget.mark_set("paragraph_start", "end - 1 char")
        self.text_widget.mark_gravity("paragraph_start", "left")

        # 渲染段落（动态切分：根据控件宽度和字号自适应）
        split_paras = self._split_paragraphs_dynamic(chapter.paragraphs)
        for para in split_paras:
            if para.strip():
                spaced = self._apply_char_spacing(para.strip())
                self.text_widget.insert("end", spaced + "\n", "paragraph")

        self.text_widget.yview_moveto(0)
        self.text_widget.configure(state="disabled")
        self._rendering = False

        # 如果窗口已显示但宽度还是估算值，窗口稳定后重新渲染一次校准
        timer = getattr(self, '_calibrate_timer', None)
        if timer is None:
            self._calibrate_timer = self.after(200, self._calibrate_render)

    def navigate(self, direction):
        """导航到上一章/下一章"""
        new_index = self.current_chapter_index + direction
        if 0 <= new_index < self.book.chapter_count:
            self.render_chapter(new_index)
            if self.on_chapter_change:
                self.on_chapter_change(new_index, 0)

    def get_scroll_position(self):
        """获取当前滚动位置"""
        return self.text_widget.yview()[0]

    def set_scroll_position(self, pos):
        """设置滚动位置"""
        self.text_widget.yview_moveto(pos)

    def zoom_in(self):
        self.font_size = min(self.font_size + 2, 32)
        self._update_font_size()

    def zoom_out(self):
        self.font_size = max(self.font_size - 2, 10)
        self._update_font_size()

    def _update_font_size(self):
        indent_px = self._calc_indent_px()
        # 更新正文字体大小
        try:
            self.tk.call("font", "configure", self._body_font_name,
                "-size", self.font_size)
        except tk.TclError:
            pass
        self.text_widget.tag_configure("paragraph",
            font=self._body_font_name,
            foreground=TEXT_COLOR,
            spacing1=PARAGRAPH_SPACING(),
            spacing3=PARAGRAPH_SPACING(),
            lmargin1=indent_px,
            lmargin2=0,
        )
        self.render_chapter(self.current_chapter_index)