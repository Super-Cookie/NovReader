"""章节解析 - 逐行处理，对标油猴脚本逻辑"""

import re
from novel_reader.models.book import Book
from novel_reader.models.chapter import Chapter, ChapterType
from novel_reader.parser.regex_patterns import VOLUME_PATTERN, CHAPTER_MAIN_PATTERN
from novel_reader.config import MAX_VOLUME_NAME_LENGTH


def _detect_encoding(filepath):
    """智能检测文件编码：先按常见编码尝试解码，再校验解码后的内容是否合理"""
    import io

    with open(filepath, 'rb') as f:
        raw = f.read()

    # 常见的试编码顺序
    encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb18030', 'latin-1']

    # 优先检测 BOM
    if raw[:3] == b'\xef\xbb\xbf':
        return 'utf-8-sig', raw.decode('utf-8-sig')
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return 'utf-16', raw.decode('utf-16')

    # 对每个编码尝试解码，并用内容校验打分
    best_enc = None
    best_text = None
    best_score = -1

    for enc in encodings:
        try:
            text = raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

        # 内容校验：统计常见中文字符的出现
        common_chars = {'第', '章', '节', '卷', '回', '的', '了', '是',
                        '不', '人', '我', '他', '她', '有', '在', '说',
                        '一', '个', '上', '下', '大', '小', '看', '到'}
        found = sum(1 for c in common_chars if c in text)

        # 计算 CJK 字符比例
        total_cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        total_chars = len(text.strip())
        cjk_ratio = total_cjk / max(total_chars, 1)

        # 评分：常见字匹配数 + CJK 比例权重
        score = found + (cjk_ratio * 50 if cjk_ratio > 0.01 else 0)

        if score > best_score:
            best_score = score
            best_enc = enc
            best_text = text

    if best_text is not None:
        return best_enc or 'utf-8', best_text

    # 最后的保底
    return 'latin-1', raw.decode('latin-1', errors='replace')


def parse_novel_file(filepath):
    """解析 .nov / .txt 文件，返回 Book 对象"""
    encoding, text = _detect_encoding(filepath)

    from novel_reader.parser.text_cleaner import clean_text, normalize_newlines
    text = normalize_newlines(text)
    text = clean_text(text)

    book = Book(filepath)

    # 按行分割
    lines = text.split('\n')
    chapters = []
    current_volume = None
    volume_set = set()
    index = 0

    # 用于收集当前章节段落
    current_paragraphs = []
    current_title = None
    current_type = ChapterType.CHAPTER

    def flush_chapter():
        """将缓存的段落保存为一个章节"""
        nonlocal index, current_title, current_type, current_paragraphs
        if current_title is not None or current_paragraphs:
            title = current_title if current_title else book.title
            # 不再在此处按固定字数切分，改为渲染时根据控件尺寸动态切分
            ch = Chapter(title, index, current_type, list(current_paragraphs))
            if current_volume:
                ch.set_volume(current_volume)
            chapters.append(ch)
            index += 1
            current_title = None
            current_type = ChapterType.CHAPTER
            current_paragraphs.clear()

    # 处理每一行
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_paragraphs:
                # 保持空行
                current_paragraphs.append('')
            continue

        # 优先检测卷名
        vol_match = VOLUME_PATTERN.match(line)
        if vol_match:
            full_line = vol_match.group(0).strip()
            clean_line = full_line.strip()

            if (len(clean_line) > MAX_VOLUME_NAME_LENGTH or
                '。' in clean_line or '.' in clean_line or
                '章' in clean_line or '节' in clean_line or '回' in clean_line):
                if current_paragraphs:
                    current_paragraphs.append(stripped)
                continue

            if clean_line in volume_set:
                if current_paragraphs:
                    current_paragraphs.append(stripped)
                continue

            # 检测到卷名，先flush之前的章节
            flush_chapter()
            volume_set.add(clean_line)
            current_volume = full_line
            continue

        # 检测章节标题 - 整行匹配
        match = CHAPTER_MAIN_PATTERN.match(line)
        if match:
            title = None
            para_text = None
            chap_type = ChapterType.CHAPTER
            is_volume = False

            if match.group(1):
                title = match.group(1).replace('《', '').replace('》', '')
                chap_type = ChapterType.TITLE
            elif match.group(2):
                title = match.group(2).strip()
                chap_type = ChapterType.PREFACE
            elif match.group(3):
                title = match.group(3).strip()
                keyword = match.group(4)
                # 如果匹配到的关键词是"卷"，当作卷名处理
                if keyword == "卷":
                    is_volume = True
                    chap_type = ChapterType.VOLUME
                else:
                    chap_type = ChapterType.CHAPTER
            elif match.group(5):
                title = match.group(5).strip()
                chap_type = ChapterType.POSTSCRIPT
            elif match.group(6):
                para_text = match.group(6)

            if title:
                if is_volume:
                    clean_line = title.strip()
                    if (len(clean_line) > MAX_VOLUME_NAME_LENGTH or
                        '。' in clean_line or '.' in clean_line):
                        current_paragraphs.append(stripped)
                    elif clean_line in volume_set:
                        current_paragraphs.append(stripped)
                    else:
                        flush_chapter()
                        volume_set.add(clean_line)
                        current_volume = title
                else:
                    flush_chapter()
                    current_title = title
                    current_type = chap_type
            elif para_text and para_text.strip():
                current_paragraphs.append(para_text.strip())
        else:
            current_paragraphs.append(stripped)

    # 收尾：flush最后一章
    flush_chapter()

    if not chapters:
        all_paras = [l.strip() for l in lines if l.strip()]
        if all_paras:
            chapter = Chapter(book.title, 0, ChapterType.CHAPTER, all_paras)
            chapters.append(chapter)
            print(f"[解析] {book.filename}: 未检测到章节标题，将全部文本作为一章（共 {len(all_paras)} 段）")

    for ch in chapters:
        book.add_chapter(ch)

    print(f"[解析] {book.filename}: 共识别 {book.chapter_count} 章")
    return book