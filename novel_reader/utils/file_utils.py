"""文件操作工具"""

import os
import json


def get_config_path():
    """获取配置文件路径"""
    user_dir = os.path.expanduser("~")
    return os.path.join(user_dir, ".novel_reader_config.json")


def load_config():
    """加载配置"""
    config_path = get_config_path()
    default_config = {
        "recent_files": [],
        "last_open_files": [],
        "window_geometry": "",
    }
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key in default_config:
                if key not in data:
                    data[key] = default_config[key]
            return data
    except (json.JSONDecodeError, IOError):
        pass
    return default_config


def save_config(config):
    """保存配置"""
    config_path = get_config_path()
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except IOError:
        pass


def normalize_path(filepath):
    """标准化文件路径：转为绝对路径、统一分隔符、统一大小写（Windows）"""
    return os.path.normcase(os.path.normpath(os.path.abspath(filepath)))


def add_recent_file(filepath):
    """添加最近打开文件（相同路径的文件视为同一个，保留最新记录）"""
    filepath = normalize_path(filepath)
    config = load_config()
    recent = config.get("recent_files", [])
    # 移除相同路径的文件（大小写不敏感比较）
    recent = [f for f in recent if normalize_path(f) != filepath]
    recent.insert(0, filepath)
    from novel_reader.config import RECENT_FILES_MAX
    config["recent_files"] = recent[:RECENT_FILES_MAX]
    save_config(config)


def remove_recent_file(filepath):
    """移除最近打开文件"""
    filepath = normalize_path(filepath)
    config = load_config()
    recent = config.get("recent_files", [])
    config["recent_files"] = [f for f in recent if normalize_path(f) != filepath]
    save_config(config)


def get_recent_files():
    """获取最近打开文件列表（自动去重同名文件，保留最新记录）"""
    config = load_config()
    recent = config.get("recent_files", [])
    seen = set()
    result = []
    for f in recent:
        if os.path.exists(f):
            norm = normalize_path(f)
            if norm not in seen:
                seen.add(norm)
                result.append(f)
    return result


def save_last_open_files(filepaths):
    """保存最后打开的文件列表（自动去重同名文件）"""
    seen = set()
    unique = []
    for fp in filepaths:
        norm = normalize_path(fp)
        if norm not in seen:
            seen.add(norm)
            unique.append(norm)
    config = load_config()
    config["last_open_files"] = unique
    save_config(config)


def get_last_open_files():
    """获取上次打开的文件列表（自动去重同名文件）"""
    config = load_config()
    recent = config.get("last_open_files", [])
    seen = set()
    result = []
    for f in recent:
        if os.path.exists(f):
            norm = normalize_path(f)
            if norm not in seen:
                seen.add(norm)
                result.append(f)
    return result


def save_window_geometry(geometry):
    """保存窗口几何信息"""
    config = load_config()
    config["window_geometry"] = geometry
    save_config(config)


def load_window_geometry():
    """加载窗口几何信息"""
    config = load_config()
    return config.get("window_geometry", "")


def save_font_size(size):
    """保存字体大小"""
    config = load_config()
    config["font_size"] = size
    save_config(config)


def load_font_size():
    """加载字体大小，无用户设置时返回 None，由 config.py 的 BASE_FONT_SIZE 决定"""
    config = load_config()
    return config.get("font_size")


def save_text_indent(chars):
    """保存段首缩进字符数"""
    config = load_config()
    config["text_indent"] = chars
    save_config(config)


def load_text_indent():
    """加载段首缩进字符数，无用户设置时返回 None，由 config.py 的 TEXT_INDENT_CHARS 决定"""
    config = load_config()
    return config.get("text_indent")


def save_progress(filepath, chapter_index, scroll_pos):
    """保存阅读进度（用标准化路径作为 key，同名文件共用进度）"""
    filepath = normalize_path(filepath)
    config = load_config()
    if "progress" not in config:
        config["progress"] = {}
    # 移除大小写不同但指向同一文件的旧进度记录
    old_progress = {}
    for k, v in config["progress"].items():
        if normalize_path(k) != filepath:
            old_progress[k] = v
    config["progress"] = old_progress
    config["progress"][filepath] = {
        "chapter_index": chapter_index,
        "scroll_pos": scroll_pos,
    }
    save_config(config)


def load_progress(filepath):
    """加载阅读进度（支持大小写不敏感查找）"""
    filepath = normalize_path(filepath)
    config = load_config()
    progress = config.get("progress", {})
    # 先尝试精确匹配
    result = progress.get(filepath)
    if result is not None:
        return result
    # 再尝试大小写不敏感匹配（兼容旧数据）
    for k, v in progress.items():
        if normalize_path(k) == filepath:
            return v
    return None