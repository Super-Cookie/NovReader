"""
NovReader 全局配置文件
=======================
所有尺寸基准值均为 96dpi（100% 缩放）下的像素/磅值。
高 DPI 环境下通过 init_dpi() 初始化缩放因子，由 dp() / dpf() 自动适配。

命名约定：_XXX=私有基准, XXX()=DPI缩放后值, XXX=直接使用常量
"""

import ctypes
import json
import os
import sys
import tkinter as tk

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                        一、DPI 缩放系统（基础设施）                          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

_DPI_SCALE = 1.0         # 当前 DPI 缩放因子（= 1.0 + (系统DPI/96 - 1) * 收敛系数）
_DPI_DAMPEN = 0      # 收敛系数：0=不缩放  1=线性缩放


def init_dpi():
    """初始化 DPI 缩放因子并同步 tkinter 内部缩放（标题栏 / 菜单 / 对话框）"""
    global _DPI_SCALE
    try:
        user32 = ctypes.windll.user32
        hdc = user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        user32.ReleaseDC(0, hdc)
        raw_scale = dpi / 96.0
        _DPI_SCALE = 1.0 + (raw_scale - 1.0) * _DPI_DAMPEN
    except Exception:
        _DPI_SCALE = 1.0

    try:
        tk.call('tk', 'scaling', _DPI_SCALE)
    except Exception:
        pass

    return _DPI_SCALE


def dp(value):
    """像素值 DPI 缩放后取整（控件尺寸、间距、边距）"""
    return int(round(value * _DPI_SCALE))


def dpf(value):
    """浮点值 DPI 缩放（字号等）"""
    return value * _DPI_SCALE


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                          二、窗口（工作区比例 + 通用 UI 色）                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ── 尺寸 ──
_WIN_WIDTH_RATIO = 0.9     # 宽度 = 工作区宽度 × 此比例
_WIN_HEIGHT_RATIO = 0.9    # 高度 = 工作区高度 × 此比例
_MIN_WIN_WIDTH_RATIO = 0.6  # 最小宽度比例
_MIN_WIN_HEIGHT_RATIO = 0.6  # 最小高度比例

# ── 颜色 ──
WINDOW_BG = "#EBE6DC"     # 窗口底色（最外层）
ACCENT_COLOR = "#007AFF"  # 按钮 / 链接强调色（通用）
BORDER_COLOR = "#D1D1D4"  # 分隔线色（通用）


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def _get_work_area():
    """获取主显示器工作区（排除任务栏）"""
    try:
        rc = _RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(rc), 0)
        w = rc.right - rc.left
        h = rc.bottom - rc.top
        return w, h, rc.left, rc.top
    except Exception:
        return 1920, 1040, 0, 0


def DEFAULT_WIN_WIDTH():
    w, _, _, _ = _get_work_area()
    return int(w * _WIN_WIDTH_RATIO)

def DEFAULT_WIN_HEIGHT():
    _, h, _, _ = _get_work_area()
    return int(h * _WIN_HEIGHT_RATIO)

def MIN_WIN_WIDTH():
    w, _, _, _ = _get_work_area()
    return int(w * _MIN_WIN_WIDTH_RATIO)

def MIN_WIN_HEIGHT():
    _, h, _, _ = _get_work_area()
    return int(h * _MIN_WIN_HEIGHT_RATIO)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    三、顶部标题栏（自定义窗口标题栏）                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# 窗口标题格式。可用占位符：{title} = 书名，{file} = 文件名
WINDOW_TITLE_FORMAT = "{title} - NovReader"
WINDOW_TITLE_DEFAULT = "NovReader"

# ── 标题栏尺寸 ──
_TITLE_BAR_HEIGHT = 32           # 标题栏高度（像素基准）
_TITLE_BAR_FONT_SIZE = 12        # 标题栏字号

# ── 标题栏配色 ──
TITLE_BAR_BG = "#E8E8EA"         # 标题栏底色（与工具栏底色一致）
TITLE_BAR_FG = "#1D1D1F"         # 标题栏文字色
TITLE_BAR_BTN_HOVER = "#D1D1D4"  # 窗口按钮悬停底色
TITLE_BAR_CLOSE_HOVER = "#E81123" # 关闭按钮悬停底色（Windows 红）
TITLE_BAR_CLOSE_FG = "#FFFFFF"   # 关闭按钮悬停文字色

def TITLE_BAR_HEIGHT(): return dp(_TITLE_BAR_HEIGHT)
def TITLE_BAR_FONT_SIZE(): return round(dpf(_TITLE_BAR_FONT_SIZE))

# ── 标题栏窗口按钮（最小化/最大化/关闭） ──
_TITLE_BAR_BTN_WIDTH = 46         # 每个按钮宽度（像素基准，建议 38~50）
_TITLE_BAR_ICON_SIZE = 12         # 图标基准尺寸（最大化方框边长，最小化横线和关闭 X 等比缩放）
_TITLE_BAR_ICON_LINE_WIDTH = 1.2  # 图标线条粗细（最小化/最大化）
_TITLE_BAR_CLOSE_LINE_WIDTH = 1.6 # 关闭图标 X 线条稍粗

def TITLE_BAR_BTN_WIDTH(): return dp(_TITLE_BAR_BTN_WIDTH)
def TITLE_BAR_ICON_SIZE(): return dp(_TITLE_BAR_ICON_SIZE)
def TITLE_BAR_ICON_LINE_WIDTH(): return max(1, dpf(_TITLE_BAR_ICON_LINE_WIDTH))
def TITLE_BAR_CLOSE_LINE_WIDTH(): return max(1, dpf(_TITLE_BAR_CLOSE_LINE_WIDTH))


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                   四、顶部工具栏（正文页 + 目录页共享）                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ── 左边按钮条（打开/最近/缩放等） ──
_TOOLBAR_HEIGHT_RATIO = 0.06     # 工具栏高度 = 工作区高 × 此比例
TOOLBAR_BG = "#E8E8EA"           # 工具栏底色（也用于底部导航栏）
_TOOLBAR_FONT_SIZE = 15        # 工具栏按钮字号
TOOLBAR_BTN_FG = "#1D1D1F"      # 工具栏按钮文字色
TOOLBAR_HOVER_BG = "#D1D1D4"    # 工具栏按钮悬停底色
TOOLBAR_SEP_COLOR = "#C0C0C4"   # 工具栏分隔线色

# ── 章节信息（工具栏中央显示的章节名） ──
TOP_TITLE_FONT_FAMILY = "Microsoft YaHei UI"
_TOP_TITLE_FONT_SIZE = 14                    # 章节信息字号
TOP_TITLE_FG = "#1D1D1F"                       # 章节信息文字色
TOP_TITLE_BOLD = True                          # 是否加粗

# ── 放大/缩小字体按钮（正文页 / 目录页单独控制） ──
SHOW_ZOOM_BUTTONS_READER = False   # 正文页显示放大/缩小字体按钮
SHOW_ZOOM_BUTTONS_TOC = False      # 目录页显示放大/缩小字体按钮
SHOW_TOOLBAR_SEP = False           # 放大缩小按钮左侧的分隔竖线


def TOOLBAR_HEIGHT():
    _, h, _, _ = _get_work_area()
    return int(h * _TOOLBAR_HEIGHT_RATIO)
def TOOLBAR_FONT_SIZE(): return round(dpf(_TOOLBAR_FONT_SIZE))
def TOP_TITLE_FONT_SIZE(): return round(dpf(_TOP_TITLE_FONT_SIZE))



# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    五、正文区（阅读区 — 字体 / 字号 / 排版 / 配色）           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ── 配色 ──
READER_MARGIN_BG = "#F3EDE0"  # 阅读区左右边距底色（中层）
READER_BG = "#FDF9F2"         # 阅读区正文底色（最内层）
TEXT_COLOR = "#1A1A1A"        # 正文文字色
BG_COLOR = READER_BG          # 兼容旧引用别名

# ── 字体 ──
BASE_FONT_FAMILY = "Microsoft YaHei UI"    # 正文字体
_BASE_FONT_SIZE = 14                       # 正文字号

HEADING_FONT_FAMILY = "Microsoft YaHei UI"  # 章节标题字体
_HEADING_FONT_SIZE = 18                     # 章节标题字号

TITLE_FONT_FAMILY = "Microsoft YaHei UI"   # 书名字体
_TITLE_FONT_SIZE = 22                      # 书名字号

_VOLUME_FONT_SIZE = 15                    # 卷名字号

# ── 排版 ──
_LINE_SPACING = 8                          # 正文行间距
_PARAGRAPH_SPACING = 10                    # 段落间距
FONT_SPACING = 0                           # 字符额外间距（0=紧凑）
TEXT_INDENT_CHARS = 2                      # 首行缩进中文字数
READER_PADX_PERCENT = 0.20                # 正文区外左右边距占比（READER_MARGIN_BG 色）
READER_TEXT_PADX_PERCENT = 0.1          # 正文左右边距占比（READER_BG 色，正文区内）
MAX_LINES_PER_PARAGRAPH = 3.5              # 窗口缩小时段落最大行数
MAX_VOLUME_NAME_LENGTH = 18                # 卷名最大字数（超出截断）

_SCROLLBAR_WIDTH = 25                      # 滚动条宽度（所有位置统一）
_READER_SIDE_PAD = 32                     # 阅读区左右边距宽度（可见，非缩进）

def BASE_FONT_SIZE(): return round(_BASE_FONT_SIZE * _DPI_SCALE)
def HEADING_FONT_SIZE(): return round(_HEADING_FONT_SIZE * _DPI_SCALE)
def TITLE_FONT_SIZE(): return round(_TITLE_FONT_SIZE * _DPI_SCALE)
def VOLUME_FONT_SIZE(): return round(_VOLUME_FONT_SIZE * _DPI_SCALE)
def LINE_SPACING(): return dp(_LINE_SPACING)
def PARAGRAPH_SPACING(): return dp(_PARAGRAPH_SPACING)
def SCROLLBAR_WIDTH(): return dp(_SCROLLBAR_WIDTH)
def READER_SIDE_PAD(): return dp(_READER_SIDE_PAD)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                      六、目录面板（悬浮浮层）                                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ── 配色 ──
SIDEBAR_BG = "#F3EDE0"        # 目录面板底色
TOC_BG = "#F0EBE2"            # 目录浮层底色（可独立于 SIDEBAR_BG 调整）
TOC_FIXED_VOLUME_BG = "#F3EDE0"  # 固定卷标背景色（与 READER_MARGIN_BG 一致）
TOC_VOLUME_BG = "#E2C4C6"     # 目录卷标背景色（列表中）
TOC_CHAPTER_BG = "#FDF9F2"    # 目录章节条目背景色（与 READER_BG 一致）
TOC_FIXED_VOLUME_FG = "#1D1D1F"  # 固定卷标文字色
TOC_VOLUME_FG = "#1D1D1F"     # 目录卷标文字色
TOC_CHAPTER_FG = "#1D1D1F"    # 目录章节条目文字色
TOC_HIGHLIGHT_BG = "#D4E8FF"  # 键盘焦点章节背景色（浅蓝）
TOC_READING_FG = "#0056CC"    # 当前阅读章节文字色（蓝色高亮）

# ── 尺寸 ──
TOC_FONT_FAMILY = "Microsoft YaHei UI"
_TOC_FONT_SIZE = 13                        # 目录章节条目字号
_TOC_VOLUME_FONT_SIZE = 14                 # 目录卷标字号

_TOC_HEADER_HEIGHT_RATIO = 0.05  # 目录标题栏高度 = 工作区高 × 此比例
_TOC_PANEL_WIDTH_RATIO = 0.6              # 目录面板宽度 = 工作区宽 × 此比例
_TOC_PANEL_HEIGHT_RATIO = 0.75            # 目录面板高度 = 工作区高 × 此比例
_TOC_COLUMN_WRAPLENGTH_RATIO = 0.15        # 列内换行宽度 = 工作区宽 × 此比例

def TOC_HEADER_HEIGHT():
    _, h, _, _ = _get_work_area()
    return int(h * _TOC_HEADER_HEIGHT_RATIO)
def TOC_FONT_SIZE(): return round(_TOC_FONT_SIZE * _DPI_SCALE)
def TOC_VOLUME_FONT_SIZE(): return round(_TOC_VOLUME_FONT_SIZE * _DPI_SCALE)
def TOC_PANEL_WIDTH():
    w, _, _, _ = _get_work_area()
    return int(w * _TOC_PANEL_WIDTH_RATIO)
def TOC_PANEL_HEIGHT():
    _, h, _, _ = _get_work_area()
    return int(h * _TOC_PANEL_HEIGHT_RATIO)
def TOC_COLUMN_WRAPLENGTH():
    w, _, _, _ = _get_work_area()
    return int(w * _TOC_COLUMN_WRAPLENGTH_RATIO)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                      七、底部导航栏（正文页）                                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ── 配色 ──
NAV_BG = "#F2EFE8"            # 底部导航栏底色
BAR_BG = "#E5DFD3"            # 按钮条底色
BAR_DIVIDER = "#D5CFC3"       # 按钮分隔线
BTN_TEXT_COLOR = "#555555"    # 底部按钮文字色
BTN_TEXT_DISABLED = "#BBBBBB" # 底部按钮禁用态
CENTER_TITLE_COLOR = "#333333"  # 底部章节标题色
CENTER_PROGRESS_COLOR = "#888888"  # 底部进度文字色

# ── 尺寸 ──
_READER_BOTTOM_NAV_HEIGHT = 70                        # 正文底部导航栏高度
_READER_BOTTOM_NAV_BTN_FONT_SIZE = 21                 # 两侧按钮字号(上一章/下一章)
_READER_BOTTOM_NAV_CENTER_FONT_SIZE = 19              # 中间按钮字号(目录)

def READER_BOTTOM_NAV_HEIGHT(): return dp(_READER_BOTTOM_NAV_HEIGHT)
def READER_BOTTOM_NAV_BTN_FONT_SIZE(): return round(dpf(_READER_BOTTOM_NAV_BTN_FONT_SIZE))
def READER_BOTTOM_NAV_CENTER_FONT_SIZE(): return round(dpf(_READER_BOTTOM_NAV_CENTER_FONT_SIZE))


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                      八、底部导航栏（目录页）                                 ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ── 尺寸 ──
_TOC_BOTTOM_NAV_HEIGHT = 70                        # 目录底部导航栏高度
_TOC_BOTTOM_NAV_BTN_FONT_SIZE = 21                 # 两侧按钮字号(上一卷/下一卷)
_TOC_BOTTOM_NAV_CENTER_FONT_SIZE = 19              # 中间按钮字号(返回正文)

def TOC_BOTTOM_NAV_HEIGHT(): return dp(_TOC_BOTTOM_NAV_HEIGHT)
def TOC_BOTTOM_NAV_BTN_FONT_SIZE(): return round(dpf(_TOC_BOTTOM_NAV_BTN_FONT_SIZE))
def TOC_BOTTOM_NAV_CENTER_FONT_SIZE(): return round(dpf(_TOC_BOTTOM_NAV_CENTER_FONT_SIZE))


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                      九、功能开关 + 快捷键                                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

ENABLE_MULTI_TAB = False           # 多标签页（实验性）
SHOW_RECENT_ON_HOME = False        # 首页"最近打开"
AUTO_RESTORE_LAST_FILES = True   # 启动时恢复上次文件
RECENT_FILES_MAX = 10              # 最近文件最大记录数

TOC_MODE = "embedded"              # 目录模式: "floating"=悬浮浮层 / "embedded"=内嵌覆盖正文

KEY_PREV_CHAPTER = "<Left>"        # 上一章
KEY_NEXT_CHAPTER = "<Right>"       # 下一章
KEY_OPEN_TOC = "<Return>"          # 打开目录
KEY_OPEN_FILE = "<Control-o>"      # 打开文件
KEY_CLOSE_TAB = "<Control-w>"      # 关闭标签
KEY_NEW_WINDOW = "<Control-n>"     # 新建窗口


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║              十、持久化配置 — 开发模式（py）                                   ║
# ║                                                                              ║
# ║  · 读写 test/novel_reader_settings.json                                      ║
# ║  · 加载时应用所有配置项（方便调试）                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

_SETTINGS_FILE = "test/novel_reader_settings.json"

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║              十一、持久化配置 — 安装版 setup_exe                              ║
# ║                                                                              ║
# ║  · 读写 <exe目录>/config/novel_reader_settings.json                           ║
# ║  · 加载时仅应用以下 4 项用户自定义：                                           ║
# ║    BASE_FONT_FAMILY（字体）                                                   ║
# ║    _BASE_FONT_SIZE（字号）                                                   ║
# ║    TEXT_COLOR（文字色）                                                      ║
# ║    READER_BG（背景色）                                                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# 运行模式检测
_IS_FROZEN = getattr(sys, 'frozen', False)

# 用户自定义白名单（setup_exe 模式只允许写入/读取这几项）
_USER_KEYS = {"BASE_FONT_FAMILY", "_BASE_FONT_SIZE", "TEXT_COLOR", "READER_BG"}

_settings_path_cache = None


def get_settings_path():
    """获取配置文件的完整路径

    - 开发模式（py）→ <项目根>/test/novel_reader_settings.json
    - 安装版 setup_exe → <exe目录>/config/novel_reader_settings.json
    """
    global _settings_path_cache
    if _settings_path_cache is None:
        if _IS_FROZEN:
            app_dir = os.path.dirname(sys.executable)
            _settings_path_cache = os.path.join(
                app_dir, "config", "novel_reader_settings.json"
            )
        else:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            _settings_path_cache = os.path.join(app_dir, _SETTINGS_FILE)
    return _settings_path_cache


def _init_settings():
    """读取配置文件覆盖默认值（不存在则什么都不做）"""
    settings_path = get_settings_path()
    if os.path.exists(settings_path):
        _load_settings(settings_path)


def _load_settings(settings_path):
    """从配置文件加载值

    - 开发模式（py）：加载所有配置项
    - 安装版 setup_exe：只加载白名单中的 4 项用户自定义
    """
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return

    module = sys.modules[__name__]
    for key, value in data.items():
        if key.startswith("__"):
            continue
        # 开发模式加载全部；setup_exe 模式只加载白名单
        if _IS_FROZEN and key not in _USER_KEYS:
            continue
        if hasattr(module, key):
            setattr(module, key, value)


def _write_settings(settings_path):
    """生成完整的默认配置文件"""
    current = {}
    module = sys.modules[__name__]
    for key, default_value in _SETTINGS_META.items():
        if key.startswith("__"):
            current[key] = default_value
        elif hasattr(module, key):
            current[key] = getattr(module, key)
        else:
            current[key] = default_value

    try:
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
    except IOError:
        pass


def save_settings(**kwargs):
    """保存运行时变化到配置文件"""
    settings_path = get_settings_path()
    try:
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
    except (json.JSONDecodeError, IOError):
        data = {}

    # setup_exe 模式只保存白名单内的键
    if _IS_FROZEN:
        kwargs = {k: v for k, v in kwargs.items() if k in _USER_KEYS}

    data.update(kwargs)

    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError:
        pass


_init_settings()  # 模块导入时自动执行

_SETTINGS_META = {
    # -- 说明 --
    "__说明__": "NovReader 配置文件。修改任意参数后重启生效。删除此文件后重启将重新生成默认值。",
    "__运行时数据__": "以下由软件自动维护，请勿手动修改",
    "window_geometry": "",
    "recent_files": [],
    "last_open_files": [],
    # -- 一、DPI 缩放 --
    "__DPI缩放__": "收敛系数：0=不缩放 1=等比",
    "_DPI_DAMPEN": _DPI_DAMPEN,
    # -- 二、窗口 --
    "__窗口尺寸__": "工作区比例：宽度/高度/最小宽度/最小高度 + 通用 UI 色",
    "_WIN_WIDTH_RATIO": _WIN_WIDTH_RATIO,
    "_WIN_HEIGHT_RATIO": _WIN_HEIGHT_RATIO,
    "_MIN_WIN_WIDTH_RATIO": _MIN_WIN_WIDTH_RATIO,
    "_MIN_WIN_HEIGHT_RATIO": _MIN_WIN_HEIGHT_RATIO,
    "WINDOW_BG": WINDOW_BG,
    "ACCENT_COLOR": ACCENT_COLOR,
    "BORDER_COLOR": BORDER_COLOR,
    # -- 三、顶部标题栏 --
    "__顶部标题栏(自定义)__": "标题栏高度/字号/配色/按钮尺寸 + 窗口标题格式",
    "_TITLE_BAR_HEIGHT": _TITLE_BAR_HEIGHT,
    "_TITLE_BAR_FONT_SIZE": _TITLE_BAR_FONT_SIZE,
    "_TITLE_BAR_BTN_WIDTH": _TITLE_BAR_BTN_WIDTH,
    "_TITLE_BAR_ICON_SIZE": _TITLE_BAR_ICON_SIZE,
    "_TITLE_BAR_ICON_LINE_WIDTH": _TITLE_BAR_ICON_LINE_WIDTH,
    "_TITLE_BAR_CLOSE_LINE_WIDTH": _TITLE_BAR_CLOSE_LINE_WIDTH,
    "TITLE_BAR_BG": TITLE_BAR_BG,
    "TITLE_BAR_FG": TITLE_BAR_FG,
    "TITLE_BAR_BTN_HOVER": TITLE_BAR_BTN_HOVER,
    "TITLE_BAR_CLOSE_HOVER": TITLE_BAR_CLOSE_HOVER,
    "TITLE_BAR_CLOSE_FG": TITLE_BAR_CLOSE_FG,
    "WINDOW_TITLE_FORMAT": WINDOW_TITLE_FORMAT,
    "WINDOW_TITLE_DEFAULT": WINDOW_TITLE_DEFAULT,
    # -- 四、顶部工具栏（正文页 + 目录页共享） --
    "__顶部工具栏__": "工具栏配色/字号 + 章节信息 + 放大缩小按钮开关",
    "TOP_TITLE_FONT_FAMILY": TOP_TITLE_FONT_FAMILY,
    "_TOP_TITLE_FONT_SIZE": _TOP_TITLE_FONT_SIZE,
    "TOP_TITLE_FG": TOP_TITLE_FG,
    "TOP_TITLE_BOLD": TOP_TITLE_BOLD,
    "_TOOLBAR_HEIGHT_RATIO": _TOOLBAR_HEIGHT_RATIO,
    "TOOLBAR_BG": TOOLBAR_BG,
    "_TOOLBAR_FONT_SIZE": _TOOLBAR_FONT_SIZE,
    "TOOLBAR_BTN_FG": TOOLBAR_BTN_FG,
    "TOOLBAR_HOVER_BG": TOOLBAR_HOVER_BG,
    "TOOLBAR_SEP_COLOR": TOOLBAR_SEP_COLOR,
    "SHOW_ZOOM_BUTTONS_READER": SHOW_ZOOM_BUTTONS_READER,
    "SHOW_ZOOM_BUTTONS_TOC": SHOW_ZOOM_BUTTONS_TOC,
    "SHOW_TOOLBAR_SEP": SHOW_TOOLBAR_SEP,
    # -- 五、正文区(阅读区) --
    "__正文区__": "字体 / 字号 / 排版 / 配色",
    "BASE_FONT_FAMILY": BASE_FONT_FAMILY,
    "HEADING_FONT_FAMILY": HEADING_FONT_FAMILY,
    "TITLE_FONT_FAMILY": TITLE_FONT_FAMILY,
    "_BASE_FONT_SIZE": _BASE_FONT_SIZE,
    "_HEADING_FONT_SIZE": _HEADING_FONT_SIZE,
    "_TITLE_FONT_SIZE": _TITLE_FONT_SIZE,
    "_VOLUME_FONT_SIZE": _VOLUME_FONT_SIZE,
    "_LINE_SPACING": _LINE_SPACING,
    "_PARAGRAPH_SPACING": _PARAGRAPH_SPACING,
    "FONT_SPACING": FONT_SPACING,
    "TEXT_INDENT_CHARS": TEXT_INDENT_CHARS,
    "READER_PADX_PERCENT": READER_PADX_PERCENT,
    "READER_TEXT_PADX_PERCENT": READER_TEXT_PADX_PERCENT,
    "MAX_LINES_PER_PARAGRAPH": MAX_LINES_PER_PARAGRAPH,
    "MAX_VOLUME_NAME_LENGTH": MAX_VOLUME_NAME_LENGTH,
    "_SCROLLBAR_WIDTH": _SCROLLBAR_WIDTH,
    "_READER_SIDE_PAD": _READER_SIDE_PAD,
    "READER_MARGIN_BG": READER_MARGIN_BG,
    "READER_BG": READER_BG,
    "TEXT_COLOR": TEXT_COLOR,
    # -- 六、目录面板 --
    "__目录面板__": "悬浮目录浮层",
    "TOC_FONT_FAMILY": TOC_FONT_FAMILY,
    "_TOC_FONT_SIZE": _TOC_FONT_SIZE,
    "_TOC_VOLUME_FONT_SIZE": _TOC_VOLUME_FONT_SIZE,
    "_TOC_PANEL_WIDTH_RATIO": _TOC_PANEL_WIDTH_RATIO,
    "_TOC_PANEL_HEIGHT_RATIO": _TOC_PANEL_HEIGHT_RATIO,
    "_TOC_COLUMN_WRAPLENGTH_RATIO": _TOC_COLUMN_WRAPLENGTH_RATIO,
    "_TOC_HEADER_HEIGHT_RATIO": _TOC_HEADER_HEIGHT_RATIO,
    "SIDEBAR_BG": SIDEBAR_BG,
    "TOC_BG": TOC_BG,
    "TOC_VOLUME_BG": TOC_VOLUME_BG,
    "TOC_VOLUME_FG": TOC_VOLUME_FG,
    "TOC_FIXED_VOLUME_BG": TOC_FIXED_VOLUME_BG,
    "TOC_FIXED_VOLUME_FG": TOC_FIXED_VOLUME_FG,
    "TOC_CHAPTER_BG": TOC_CHAPTER_BG,
    "TOC_CHAPTER_FG": TOC_CHAPTER_FG,
    "TOC_HIGHLIGHT_BG": TOC_HIGHLIGHT_BG,
    "TOC_READING_FG": TOC_READING_FG,
    # -- 七、底部导航栏（正文页） --
    "__正文底部导航栏__": "高度/按钮字号 + 配色",
    "_READER_BOTTOM_NAV_HEIGHT": _READER_BOTTOM_NAV_HEIGHT,
    "_READER_BOTTOM_NAV_BTN_FONT_SIZE": _READER_BOTTOM_NAV_BTN_FONT_SIZE,
    "_READER_BOTTOM_NAV_CENTER_FONT_SIZE": _READER_BOTTOM_NAV_CENTER_FONT_SIZE,
    "NAV_BG": NAV_BG,
    "BAR_BG": BAR_BG,
    "BAR_DIVIDER": BAR_DIVIDER,
    "BTN_TEXT_COLOR": BTN_TEXT_COLOR,
    "BTN_TEXT_DISABLED": BTN_TEXT_DISABLED,
    "CENTER_TITLE_COLOR": CENTER_TITLE_COLOR,
    "CENTER_PROGRESS_COLOR": CENTER_PROGRESS_COLOR,
    # -- 八、底部导航栏（目录页） --
    "__目录底部导航栏__": "高度/按钮字号",
    "_TOC_BOTTOM_NAV_HEIGHT": _TOC_BOTTOM_NAV_HEIGHT,
    "_TOC_BOTTOM_NAV_BTN_FONT_SIZE": _TOC_BOTTOM_NAV_BTN_FONT_SIZE,
    "_TOC_BOTTOM_NAV_CENTER_FONT_SIZE": _TOC_BOTTOM_NAV_CENTER_FONT_SIZE,
    # -- 九、功能开关 + 快捷键 --
    "__功能开关__": "true=开启  false=关闭",
    "ENABLE_MULTI_TAB": ENABLE_MULTI_TAB,
    "SHOW_RECENT_ON_HOME": SHOW_RECENT_ON_HOME,
    "AUTO_RESTORE_LAST_FILES": AUTO_RESTORE_LAST_FILES,
    "__快捷键__": "参考: Left Right Up Down Return Escape Control/Alt/Shift+字母",
    "KEY_PREV_CHAPTER": KEY_PREV_CHAPTER,
    "KEY_NEXT_CHAPTER": KEY_NEXT_CHAPTER,
    "KEY_OPEN_TOC": KEY_OPEN_TOC,
    "KEY_OPEN_FILE": KEY_OPEN_FILE,
    "KEY_CLOSE_TAB": KEY_CLOSE_TAB,
    "KEY_NEW_WINDOW": KEY_NEW_WINDOW,
}

_settings_path_cache = None


def get_settings_path():
    """获取配置文件的完整路径"""
    global _settings_path_cache
    if _settings_path_cache is None:
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
            _settings_path_cache = os.path.join(app_dir, "config", "novel_reader_settings.json")
        else:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            _settings_path_cache = os.path.join(app_dir, _SETTINGS_FILE)
    return _settings_path_cache


def _init_settings():
    """读取 exe 目录的配置文件覆盖默认值（不存在则什么都不做）"""
    settings_path = get_settings_path()
    if os.path.exists(settings_path):
        _load_settings(settings_path)


def _load_settings(settings_path):
    """从配置文件加载值，覆盖模块中的同名属性"""
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return

    # 只允许用户自定义以下 4 项：字体 / 字号 / 文字色 / 背景色
    _USER_KEYS = {"BASE_FONT_FAMILY", "_BASE_FONT_SIZE", "TEXT_COLOR", "READER_BG"}
    module = sys.modules[__name__]
    for key, value in data.items():
        if key in _USER_KEYS and hasattr(module, key):
            setattr(module, key, value)


def _write_settings(settings_path):
    """生成完整的默认配置文件"""
    current = {}
    module = sys.modules[__name__]
    for key, default_value in _SETTINGS_META.items():
        if key.startswith("__"):
            current[key] = default_value
        elif hasattr(module, key):
            current[key] = getattr(module, key)
        else:
            current[key] = default_value

    try:
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
    except IOError:
        pass


def save_settings(**kwargs):
    """保存运行时变化到配置文件"""
    settings_path = get_settings_path()
    try:
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
    except (json.JSONDecodeError, IOError):
        data = {}

    data.update(kwargs)

    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError:
        pass


_init_settings()  # 模块导入时自动执行