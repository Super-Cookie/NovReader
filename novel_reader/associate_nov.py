"""将 .nov 文件关联到 NovReader

运行方式：
  python associate_nov.py              # 当前用户关联（推荐，无需管理员）
  python associate_nov.py --system     # 系统级关联（需管理员）
  python associate_nov.py --remove     # 移除关联
  python associate_nov.py --check      # 检查关联状态

说明：
  - --system 写入 HKLM\Software\Classes，需管理员权限
  - 默认（--user）写入 HKCU\Software\Classes，无需管理员，绿色版适用
"""

import os
import sys
import winreg


# 注册表根路径常量
HKCR = winreg.HKEY_CLASSES_ROOT  # 映射到 HKLM\Software\Classes（需管理员）
HKCU_CLASSES = r"Software\Classes"  # HKCU 下的类注册路径（无需管理员）


def get_base_dir():
    """获取脚本所在目录"""
    return os.path.dirname(os.path.abspath(__file__))


def get_app_path():
    """获取应用程序路径，优先 exe，其次 python 脚本"""
    # 如果是打包后的 exe 运行，sys.executable 就是 exe 路径
    if getattr(sys, 'frozen', False):
        return sys.executable
    base = get_base_dir()
    # 从项目根目录找 exe
    for candidate in [
        os.path.abspath(os.path.join(base, "..", "NovReader.exe")),
        os.path.join(base, "NovReader.exe"),
        os.path.join(base, "dist", "NovReader.exe"),
    ]:
        if os.path.exists(candidate):
            return candidate
    # 最后回退到 python 脚本
    return os.path.abspath(os.path.join(base, "..", "main.py"))


def get_icon_path():
    """获取图标路径，优先提取打包的 .ico 到用户目录，其次找本地 icon.ico"""
    # 打包后的 exe：从 MEIPASS 提取 icon.ico 到 ~/.novreader/ 目录
    if getattr(sys, 'frozen', False):
        try:
            import shutil
            # PyInstaller 解压时 icon.ico 在 sys._MEIPASS/resources/ 下
            src = os.path.join(sys._MEIPASS, "resources", "icon.ico")
            if os.path.exists(src):
                user_icon_dir = os.path.join(os.path.expanduser("~"), ".novreader")
                os.makedirs(user_icon_dir, exist_ok=True)
                dst = os.path.join(user_icon_dir, "icon.ico")
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                return dst
        except Exception:
            pass
        # 提取失败时回退到 exe 自身（虽然多数情况不显示，但好歹有个备选）
        return f"{sys.executable},0"
    base = get_base_dir()
    for candidate in [
        os.path.join(base, "resources", "icon.ico"),
        os.path.join(base, "dist", "resources", "icon.ico"),
    ]:
        if os.path.exists(candidate):
            return candidate
    return ""


def get_open_command(app_path):
    """获取打开命令"""
    if app_path.endswith('.exe'):
        return f'"{app_path}" "%1"'
    else:
        return f'"{sys.executable}" "{app_path}" "%1"'


def _write_reg(hkey_root, sub_key, value_name, value):
    """写入注册表值的辅助函数"""
    try:
        key = winreg.CreateKey(hkey_root, sub_key)
        winreg.SetValue(key, value_name, winreg.REG_SZ, value)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def _get_root(is_system=False):
    """获取注册表根路径"""
    if is_system:
        return HKCR, ""
    else:
        return winreg.HKEY_CURRENT_USER, HKCU_CLASSES


def _full_key(sub_key, is_system=False):
    """拼接完整子键路径"""
    if is_system:
        return sub_key
    else:
        return f"{HKCU_CLASSES}\\{sub_key}"


def is_associated():
    """检查 .nov 是否已被完整关联（扩展名 + 图标 + 打开命令）（优先检查 HKCU，再检查 HKCR）"""
    for root, base in [(winreg.HKEY_CURRENT_USER, HKCU_CLASSES), (HKCR, "")]:
        try:
            key_path = f"{base}\\.nov" if base else ".nov"
            with winreg.OpenKey(root, key_path) as key:
                prog_id, _ = winreg.QueryValueEx(key, "")
                if prog_id != "NovReader.nov":
                    continue

            # 检查图标是否已注册
            icon_key = f"{base}\\NovReader.nov\\DefaultIcon" if base else r"NovReader.nov\DefaultIcon"
            try:
                with winreg.OpenKey(root, icon_key) as key:
                    icon_path, _ = winreg.QueryValueEx(key, "")
                    if not icon_path:
                        continue
            except (FileNotFoundError, OSError):
                continue

            # 检查打开命令是否已注册
            cmd_key = f"{base}\\NovReader.nov\\shell\\open\\command" if base else r"NovReader.nov\shell\open\command"
            try:
                with winreg.OpenKey(root, cmd_key) as key:
                    cmd, _ = winreg.QueryValueEx(key, "")
                    if not cmd:
                        continue
            except (FileNotFoundError, OSError):
                continue

            return True
        except (FileNotFoundError, OSError):
            continue
    return False


def associate_nov_files(is_system=False):
    """关联 .nov 文件（默认写入 HKCU，无需管理员）"""
    app_path = get_app_path()
    icon_path = get_icon_path()
    open_cmd = get_open_command(app_path)
    mode = "系统级" if is_system else "当前用户"

    print("=" * 50)
    print(f"  NovReader - .nov 文件关联（{mode}）")
    print("=" * 50)
    print(f"  应用: {app_path}")
    print(f"  图标: {icon_path}")
    print(f"  命令: {open_cmd}")
    print()

    root, base = _get_root(is_system)

    try:
        # 1. 创建 .nov 文件类型扩展名指向 ProgId
        _write_reg(root, _full_key(".nov", is_system), "", "NovReader.nov")

        # 2. 创建 NovReader.nov ProgId
        _write_reg(root, _full_key("NovReader.nov", is_system), "", "小说文件")

        # 3. 设置默认图标
        if icon_path:
            _write_reg(root, _full_key(r"NovReader.nov\DefaultIcon", is_system), "", icon_path)

        # 4. 设置打开命令
        _write_reg(root, _full_key(r"NovReader.nov\shell\open\command", is_system), "", open_cmd)

        print(f"✅ .nov 文件关联成功（{mode}）！")
        print("   现在双击 .nov 文件即可用 NovReader 打开。")
        print("   如果图标不显示，请刷新资源管理器。")

        return True

    except PermissionError:
        print("❌ 需要管理员权限！请以管理员身份运行此脚本。")
        return False
    except Exception as e:
        print(f"❌ 关联失败: {e}")
        return False


def remove_association(is_system=False):
    """移除 .nov 文件关联"""
    root, base = _get_root(is_system)
    mode = "系统级" if is_system else "当前用户"

    keys_to_delete = [
        r"NovReader.nov\shell\open\command",
        r"NovReader.nov\shell\open",
        r"NovReader.nov\shell",
        r"NovReader.nov\DefaultIcon",
        "NovReader.nov",
    ]

    success = True
    for sub_key in keys_to_delete:
        try:
            full = _full_key(sub_key, is_system)
            winreg.DeleteKey(root, full)
        except FileNotFoundError:
            pass
        except PermissionError:
            print(f"❌ 需要管理员权限来移除 {mode} 关联！")
            return False
        except Exception as e:
            print(f"❌ 移除 {sub_key} 失败: {e}")
            success = False

    if success:
        print(f"✅ .nov 文件关联已移除（{mode}）。")
    return success


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="关联/取消关联 .nov 文件")
    parser.add_argument("--remove", action="store_true", help="移除文件关联")
    parser.add_argument("--system", action="store_true", help="系统级关联（需管理员）")
    parser.add_argument("--check", action="store_true", help="检查关联状态")
    args = parser.parse_args()

    if args.check:
        if is_associated():
            print("✅ .nov 文件已关联到 NovReader。")
        else:
            print("ℹ️  .nov 文件尚未关联。")
    elif args.remove:
        remove_association(is_system=args.system)
    else:
        associate_nov_files(is_system=args.system)
    print()
    print("按任意键退出...")
    try:
        input()
    except EOFError:
        pass