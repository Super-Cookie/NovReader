"""中文数字转阿拉伯数字"""

CN_NUM_MAP = {
    '零': 0, '一': 1, '壹': 1, '二': 2, '贰': 2, '两': 2,
    '三': 3, '叁': 3, '四': 4, '肆': 4, '五': 5, '伍': 5,
    '六': 6, '陆': 6, '七': 7, '柒': 7, '八': 8, '捌': 8,
    '九': 9, '玖': 9,
    '〇': 0,
}

CN_UNIT_MAP = {
    '十': 10, '拾': 10,
    '百': 100, '佰': 100,
    '千': 1000, '仟': 1000,
    '万': 10000, '萬': 10000,
    '亿': 100000000, '億': 100000000,
}

# 特殊中文数字
CN_SPECIAL = {
    '廿': 20, '卅': 30, '卌': 40,
}


def cn_num_to_arabic(cn_str):
    """将中文数字字符串转换为阿拉伯数字，无法转换返回 None"""
    if not cn_str:
        return None

    cn_str = cn_str.strip()
    if cn_str in CN_SPECIAL:
        return CN_SPECIAL[cn_str]

    # 尝试直接解析为整数
    try:
        return int(cn_str)
    except ValueError:
        pass

    result = 0
    section = 0
    num = 0
    has_valid_char = False

    for ch in cn_str:
        if ch in CN_NUM_MAP:
            num = CN_NUM_MAP[ch]
            has_valid_char = True
        elif ch in CN_UNIT_MAP:
            unit = CN_UNIT_MAP[ch]
            if num == 0:
                num = 1
            if unit >= 10000:
                section = (section + num) * unit
                result += section
                section = 0
            else:
                section += num * unit
            num = 0
            has_valid_char = True
        else:
            return None

    section += num
    result += section

    if not has_valid_char:
        return None
    return result


def format_chapter_name(name):
    """格式化章节名称：将中文数字转为阿拉伯数字"""
    import re
    pattern = r'^[第\s]*(?:(?:第\s*)?([零一二三四五六七八九十百千万亿壹贰叁肆伍陆柒捌玖拾佰仟萬億廿卅卌]+)\s*([章节回折篇幕集]))\s*(.*)'
    match = re.match(pattern, name)
    if match:
        num_part = match.group(1)
        keyword = match.group(2)
        title_part = match.group(3) or ''
        arabic = cn_num_to_arabic(num_part)
        if arabic is not None:
            return f'第{arabic}{keyword} {title_part}'.strip()
    return name