"""文本清理"""

from .regex_patterns import CLEAN_CONTROL_CHARS, CLEAN_HTML_TAGS


def clean_text(raw_text):
    """清理文本：去除控制字符和HTML标签"""
    text = CLEAN_CONTROL_CHARS.sub('', raw_text)
    text = CLEAN_HTML_TAGS.sub('', text)
    return text


def normalize_newlines(text):
    """统一换行符"""
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')
    return text