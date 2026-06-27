"""NovReader - 小说阅读器入口"""

import sys
import os

# 添加项目根目录到路径
root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root)

# Windows DPI 感知 - 让字体渲染更清晰
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

from novel_reader.ui.main_window import MainWindow


def _try_associate_on_startup():
    """启动时检测 .nov 关联，未关联则询问用户是否绑定（无需管理员权限）"""
    if sys.platform != "win32":
        return
    try:
        from novel_reader.associate_nov import is_associated, associate_nov_files
        if not is_associated():
            import tkinter.messagebox as mb
            result = mb.askyesno(
                title="绑定 .nov 文件格式",
                message="检测到 .nov 文件尚未关联到 NovReader。\n\n"
                        "✅ 绑定后，双击 .nov 文件即可用 NovReader 直接打开\n"
                        "✅ 绑定后，.nov 文件将显示 NovReader 专属图标\n\n"
                        "是否立即关联？（无需管理员权限）",
                icon="question",
            )
            if result:
                success = associate_nov_files(is_system=False)
                if success:
                    mb.showinfo(
                        "绑定成功",
                        ".nov 文件已成功绑定到 NovReader！\n\n"
                        "✅ 双击 .nov 文件 → 直接用 NovReader 打开\n"
                        "✅ .nov 文件 → 显示 NovReader 专属图标\n\n"
                        "（如果图标未立即显示，请刷新桌面）",
                    )
    except Exception:
        pass  # 静默失败，不影响正常启动


def _handle_cli():
    """处理命令行参数"""
    if len(sys.argv) < 2:
        return None  # 正常启动

    args = [a.lower() for a in sys.argv[1:]]

    is_system = "--system" in args

    if "--register" in args or "--associate" in args:
        try:
            from novel_reader.associate_nov import associate_nov_files
            success = associate_nov_files(is_system=is_system)
            if success:
                mode = "系统级" if is_system else "当前用户"
                print(f"[OK] .nov 文件已成功绑定到 NovReader（{mode}）")
                print("[OK] .nov 文件图标已设置")
            else:
                print("[错误] 绑定失败，请检查权限")
                sys.exit(1)
        except Exception as e:
            print(f"[错误] 绑定失败: {e}")
            sys.exit(1)
        sys.exit(0)

    if "--unregister" in args or "--unassociate" in args:
        try:
            from novel_reader.associate_nov import remove_association
            remove_association(is_system=is_system)
            mode = "系统级" if is_system else "当前用户"
            print(f"[OK] .nov 文件绑定已解除（{mode}）")
        except Exception as e:
            print(f"[错误] 解除失败: {e}")
            sys.exit(1)
        sys.exit(0)

    if "--check" in args:
        try:
            from novel_reader.associate_nov import is_associated
            if is_associated():
                print("[OK] .nov 文件已绑定到 NovReader（扩展名 + 图标 + 打开命令）")
            else:
                print("[INFO] .nov 文件尚未绑定到 NovReader")
        except Exception as e:
            print(f"[错误] 检查失败: {e}")
        sys.exit(0)

    # 不是 --xxx 参数，当作文件路径处理
    return sys.argv[1]


def main():
    filepath = _handle_cli()
    if filepath is not None and not os.path.isabs(filepath):
        filepath = os.path.abspath(filepath)

    app = MainWindow(filepath)

    # 等主窗口初始化完成后，再检测 .nov 关联（避免弹窗卡住）
    if filepath is None:
        app.root.after(500, _try_associate_on_startup)

    app.run()


if __name__ == "__main__":
    main()