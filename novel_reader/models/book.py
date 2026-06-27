"""书籍模型"""

from novel_reader.models.chapter import ChapterType


class Book:
    """书籍模型"""

    def __init__(self, filepath):
        self.filepath = filepath
        self.filename = filepath.split("\\")[-1] if "\\" in filepath else filepath.split("/")[-1]
        # 去掉后缀作为书名
        self.title = self.filename.rsplit(".", 1)[0] if "." in self.filename else self.filename
        self.chapters = []
        self.raw_text = ""
        self.volumes = {}

    def add_chapter(self, chapter):
        self.chapters.append(chapter)

    @property
    def chapter_count(self):
        return len(self.chapters)

    def get_chapter(self, index):
        if 0 <= index < len(self.chapters):
            return self.chapters[index]
        return None

    def get_volume_count(self):
        chs = [c for c in self.chapters if c.type != ChapterType.TITLE]
        volumes = set()
        for c in chs:
            if c.volume_name:
                volumes.add(c.volume_name)
        return len(volumes)

    def get_chapter_volume_info(self, chapter_index):
        ch = self.get_chapter(chapter_index)
        if not ch:
            return None

        vol_name = ch.volume_name
        vol_count = self.get_volume_count()

        # 计算当前卷是第几卷
        chs = [c for c in self.chapters if c.type != ChapterType.TITLE]
        vol_order = 0
        seen_volumes = []
        for c in chs:
            if c.volume_name and c.volume_name not in seen_volumes:
                seen_volumes.append(c.volume_name)
            if c is ch:
                break
        vol_order = len(seen_volumes)

        # 计算当前章节在当前卷中的序号和总数
        vol_chapters = [c for c in chs if c.volume_name == vol_name]
        within_vol_index = 0
        within_vol_total = len(vol_chapters)
        for i, c in enumerate(vol_chapters):
            if c is ch:
                within_vol_index = i + 1
                break

        return {
            "volume_name": vol_name,
            "volume_order": vol_order,
            "volume_count": vol_count,
            "within_vol_index": within_vol_index,
            "within_vol_total": within_vol_total,
        }