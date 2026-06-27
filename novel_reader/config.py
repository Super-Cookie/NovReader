"""全局配置"""

# ==================== 功能开关 ====================
ENABLE_MULTI_TAB = False
SHOW_RECENT_ON_HOME = False
AUTO_RESTORE_LAST_FILES = False  # 启动时自动恢复上次打开的文件，默认关闭

# ==================== 窗口配置 ====================
DEFAULT_WIN_WIDTH = 1100
DEFAULT_WIN_HEIGHT = 750
MIN_WIN_WIDTH = 600
MIN_WIN_HEIGHT = 400

# ==================== 阅读器外观 ====================
# macOS 风格窗口底色（浅灰）
WINDOW_BG = "#F0F0F0"

# 阅读区底色（羊皮纸）
READER_BG = "#FDFBF7"

# 侧边栏 / 导航区底色
SIDEBAR_BG = "#E8E8EA"

# 文字色
TEXT_COLOR = "#1A1A1A"

# 强调色（macOS 蓝）
ACCENT_COLOR = "#007AFF"

# 边框色
BORDER_COLOR = "#D1D1D4"

# 导航栏背景色
NAV_BG = "#F5F5F7"

# 兼容旧引用
BG_COLOR = READER_BG


# ==================== 字体配置 ====================
# 使用微软雅黑正文排版，字形标准，阅读舒适
BASE_FONT_FAMILY = "Microsoft YaHei"
BASE_FONT_SIZE = 18            # 正文字号
HEADING_FONT_SIZE = 22         # 章节标题字号
TITLE_FONT_FAMILY = "Microsoft YaHei"
LINE_SPACING = 10               # 正文行内行间距(px)，类似Word的行距设置
FONT_SPACING = 1                # 正文字符间距(px)，0=默认，增大可使字距变宽
PARAGRAPH_SPACING = 12         # 段落间距
TEXT_INDENT_CHARS = 2      # 首行缩进（中文字符数）

# ==================== 段落配置 ====================
# 每段最多占多少行（含小数），超过则自动切分
# 会根据控件实际宽度和当前字号动态计算每行字数和切分阈值
MAX_LINES_PER_PARAGRAPH = 3.5

# 阅读区左右边距（各占控件宽度的百分比，0.10 = 10%）
READER_PADX_PERCENT = 0.15

# 卷标题配置
VOLUME_FONT_SIZE = 20
MAX_VOLUME_NAME_LENGTH = 18

# 目录面板字体
TOC_FONT_FAMILY = "Microsoft YaHei"
TOC_FONT_SIZE = 13
TOC_VOLUME_FONT_SIZE = 13

# 悬浮目录面板尺寸
TOC_PANEL_WIDTH = 1000       # 面板最大宽度
TOC_PANEL_HEIGHT = 850      # 面板最大高度
TOC_COLUMN_WRAPLENGTH = 260 # 每列章节标题换行宽度(px)

# ==================== 文件配置 ====================
CONFIG_FILE = "novel_reader_config.json"
RECENT_FILES_MAX = 10

# ==================== 快捷键配置 ====================
KEY_PREV_CHAPTER = "<Left>"
KEY_NEXT_CHAPTER = "<Right>"
KEY_OPEN_TOC = "<Return>"
KEY_OPEN_FILE = "<Control-o>"
KEY_CLOSE_TAB = "<Control-w>"
KEY_NEW_WINDOW = "<Control-n>"