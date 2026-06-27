"""生成一个简单的 .ico 图标文件"""

import struct
import os


def create_ico():
    """生成一个简单的书本图标 ICO 文件"""
    output_path = os.path.join(os.path.dirname(__file__), "resources", "icon.ico")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 32x32 RGBA 图标 - 一个简单的书本图标
    width, height = 32, 32
    pixels = []

    # 背景色 (透明)
    bg = (0, 0, 0, 0)
    # 书皮颜色 (深蓝)
    cover = (74, 106, 139, 255)
    # 书页颜色 (白)
    page = (255, 255, 255, 255)
    # 书脊颜色 (深蓝)
    spine = (50, 70, 100, 255)

    for y in range(height):
        for x in range(width):
            # 书脊
            if 4 <= x <= 6 and 4 <= y <= 27:
                pixels.append(spine)
            # 左页（封面）
            elif 7 <= x <= 16 and 6 <= y <= 26:
                pixels.append(cover)
            # 右页（书页）
            elif 17 <= x <= 26 and 6 <= y <= 26:
                pixels.append(page)
            # 书页中的横线
            elif 17 <= x <= 24 and y in (8, 10, 12, 14, 16, 18, 20, 22, 24):
                pixels.append((200, 200, 210, 200))
            # 封面标题
            elif 9 <= x <= 14 and y in (9, 10):
                pixels.append((255, 255, 255, 200))
            # 封面装饰线
            elif 10 <= x <= 13 and y == 12:
                pixels.append((255, 255, 255, 180))
            elif 10 <= x <= 13 and y == 13:
                pixels.append((255, 255, 255, 180))
            # 顶部
            elif 6 <= x <= 26 and 4 <= y <= 5:
                pixels.append(cover)
            # 底部
            elif 6 <= x <= 26 and 27 <= y <= 27:
                pixels.append(cover)
            # 书页底部线
            elif 17 <= x <= 24 and y == 27:
                pixels.append(page)
            else:
                pixels.append(bg)

    # 写入 ICO
    with open(output_path, "wb") as f:
        # ICO header
        f.write(struct.pack("<HHH", 0, 1, 1))

        # AND mask (1 bit per pixel)
        and_mask = bytearray()
        row_bytes = (width + 7) // 8
        for y in range(height):
            row = 0
            for x in range(width):
                idx = y * width + x
                alpha = pixels[idx][3]
                if alpha > 128:
                    row |= (1 << (7 - (x % 8)))
                if (x % 8) == 7 or x == width - 1:
                    and_mask.append(row)
                    row = 0

        # XOR mask (BGRA)
        xor_mask = bytearray()
        for y in range(height):
            for x in range(width):
                idx = y * width + x
                b, g, r, _ = pixels[idx]
                xor_mask.extend([b, g, r, 0])

        # 图像数据大小
        xor_size = len(xor_mask)
        and_size = len(and_mask)
        image_size = 40 + xor_size + and_size

        # 偏移
        offset = 6 + 16

        # ICO directory entry
        f.write(struct.pack("<BBBBHHII",
                            width if width < 256 else 0,
                            height if height < 256 else 0,
                            0,  # color palette
                            0,  # reserved
                            1,  # color planes
                            32,  # bits per pixel
                            image_size,
                            offset))

        # BMP info header
        f.write(struct.pack("<IIIHHIIIIII",
                            40,  # header size
                            width,
                            height * 2,  # double height for ICO
                            1,  # planes
                            32,  # bpp
                            0,  # compression
                            xor_size + and_size,
                            0, 0, 0, 0))

        f.write(xor_mask)
        f.write(and_mask)

    print(f"✅ 图标已生成: {output_path}")


if __name__ == "__main__":
    create_ico()