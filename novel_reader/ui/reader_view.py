"""小说阅读视图 - 起点风格排版 + macOS 风格"""

import tkinter as tk
from tkinter import ttk, font as tkfont
from novel_reader.config import (
    READER_BG, WINDOW_BG, TEXT_COLOR, ACCENT_COLOR, BORDER_COLOR,
    BASE_FONT_FAMILY, BASE_FONT_SIZE, HEADING_FONT_SIZE,
    TITLE_FONT_FAMILY, VOLUME_FONT_SIZE, TEXT_INDENT_CHARS,
    LINE_SPACING, PARAGRAPH_SPACING, READER_PADX_PERCENT,
    FONT_SPACING, DEFAULT_WIN_WIDTH, MAX_LINES_PER_PARAGRAPH,
    KEY_PREV_CHAPTER, KEY_NEXT_CHAPTER, KEY_OPEN_TOC,
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
        self.font_size = font_size if font_size is not None else BASE_FONT_SIZE
        if indent_chars is None or indent_chars <= 0:
            self.indent_chars = TEXT_INDENT_CHARS
        else:
            self.indent_chars = indent_chars
        self._build_ui()
        self._setup_keybindings()
        self._rendering = False
        self._estimated_width = 0

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

        # 滚动条（右侧）
        self.scrollbar = tk.Scrollbar(card_frame, orient="vertical", width=48,
                                       bg="#E0E0E0", troughcolor=WINDOW_BG,
                                       activebackground="#C0C0C0")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # 文本区域（起点风格：宽边距，大字号）
        indent_px = self._calc_indent_px()
        # 创建正文字体（字符间距通过插入细空格实现，见 _apply_char_spacing）
        self._body_font_name = "ReaderBodyFont"
        try:
            self.tk.call("font", "delete", self._body_font_name)
        except tk.TclError:
            pass
        self.tk.call("font", "create", self._body_font_name,
            "-family", BASE_FONT_FAMILY,
            "-size", self.font_size)
        self.text_widget = tk.Text(
            card_frame,
            wrap="word",
            borderwidth=0,
            bg=READER_BG,
            fg=TEXT_COLOR,
            font=self._body_font_name,
            padx=0, pady=24,
            spacing1=PARAGRAPH_SPACING,
            spacing2=LINE_SPACING,
            spacing3=PARAGRAPH_SPACING,
            cursor="arrow",
            yscrollcommand=self.scrollbar.set,
            state="disabled",
            highlightthickness=0,
        )
        self.text_widget.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.config(command=self.text_widget.yview)

        # 绑定尺寸变化事件：窗口缩放时自动重新切分段落
        self.text_widget.bind("<Configure>", self._on_text_resize, add="+")

        # 底部进度条
        self.progress_bar = tk.Frame(card_frame, bg=BORDER_COLOR, height=3)
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
            font=(TITLE_FONT_FAMILY, 32, "bold"),
            foreground="#1A1A1A",
            spacing1=16, spacing3=16,
            justify="center",
        )
        # 卷名（居中分隔）
        self.text_widget.tag_configure("volume",
            font=(TITLE_FONT_FAMILY, VOLUME_FONT_SIZE, "bold"),
            foreground="#555555",
            spacing1=20, spacing3=8,
            justify="center",
        )
        # 章节标题（居中，大号）
        self.text_widget.tag_configure("chapter",
            font=(BASE_FONT_FAMILY, HEADING_FONT_SIZE, "bold"),
            foreground="#1A1A1A",
            spacing1=16, spacing3=10,
            justify="center",
        )
        # 序言
        self.text_widget.tag_configure("preface",
            font=(BASE_FONT_FAMILY, HEADING_FONT_SIZE + 2, "bold"),
            foreground="#1A1A1A",
            spacing1=16, spacing3=10,
            justify="center",
        )
        # 后记
        self.text_widget.tag_configure("postscript",
            font=(BASE_FONT_FAMILY, HEADING_FONT_SIZE + 2, "bold"),
            foreground="#1A1A1A",
            spacing1=16, spacing3=10,
            justify="center",
        )
        # 正文段落：首行缩进，后续行不缩进
        self.text_widget.tag_configure("paragraph",
            font=self._body_font_name,
            foreground=TEXT_COLOR,
            spacing1=PARAGRAPH_SPACING,
            spacing3=PARAGRAPH_SPACING,
            lmargin1=indent_px,
            lmargin2=0,
        )
        # 分隔线
        self.text_widget.tag_configure("separator",
            foreground="#C0C0C0",
            font=(BASE_FONT_FAMILY, 4),
            spacing1=4, spacing3=4,
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
        self.text_widget.yview_scroll(direction, "units")

    def _toggle_toc(self):
        if self.on_toc_toggle:
            self.on_toc_toggle()

    def _on_scroll(self, event=None):
        if self.on_chapter_change:
            self.on_chapter_change(self.current_chapter_index, self.text_widget.yview()[0])

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
        estimated_chrome = 80
        estimated = max(200, DEFAULT_WIN_WIDTH - estimated_chrome)
        self._estimated_width = estimated
        return estimated

    def _get_padx(self):
        """根据控件宽度和百分比配置计算实际 padx 像素值"""
        widget_width = self._get_text_widget_width()
        return max(20, int(widget_width * READER_PADX_PERCENT))

    def _update_padx(self):
        """更新 Text 控件的左右边距"""
        padx = self._get_padx()
        self.text_widget.configure(padx=padx)
        return padx

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
        current_padx = self._get_padx()
        available_width = widget_width - 2 * current_padx

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
        self._update_padx()
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
        # 根据当前控件宽度动态更新边距
        self._update_padx()
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

        # 渲染卷名（居中，先于章节名）
        if chapter.volume_name:
            self.text_widget.insert("end", chapter.volume_name + "\n", "volume")
            self.text_widget.insert("end", "\n")

        self.text_widget.insert("end", display_title + "\n", tag)
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
            spacing1=PARAGRAPH_SPACING,
            spacing3=PARAGRAPH_SPACING,
            lmargin1=indent_px,
            lmargin2=0,
        )
        self.render_chapter(self.current_chapter_index)