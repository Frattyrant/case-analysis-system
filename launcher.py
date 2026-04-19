"""
桌面程序入口（开发与 PyInstaller 打包共用）。

打包时使用本文件作为 Analysis 入口，保证 `app` 包可被解析。
"""

from __future__ import annotations

from app.main import main

if __name__ == "__main__":
    main()
