"""章节模型"""


class ChapterType:
    TITLE = "title"
    VOLUME = "volume"
    CHAPTER = "chapter"
    PREFACE = "preface"
    POSTSCRIPT = "postscript"


class Chapter:
    """章节模型"""

    def __init__(self, title, index, chap_type=ChapterType.CHAPTER, paragraphs=None):
        self.title = title
        self.index = index
        self.type = chap_type
        self.paragraphs = paragraphs or []
        self.volume_name = None

    def set_volume(self, volume_name):
        self.volume_name = volume_name

    @property
    def display_title(self):
        from novel_reader.utils.chinese_num import format_chapter_name
        return format_chapter_name(self.title)

    @property
    def content(self):
        return "\n".join(self.paragraphs)