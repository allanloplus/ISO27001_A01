# -*- coding: utf-8 -*-
"""
由 player/index.html（Artifact 片段，無 doctype）產生可直接雙擊開啟的根目錄 index.html。
資源路徑改指向 player/ 資料夾。

用法：python3 lesson/build_index.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    with open(os.path.join(ROOT, "player", "index.html"), encoding="utf-8") as f:
        body = f.read()
    body = body.replace('src="lesson.mp3"', 'src="player/lesson.mp3"')
    body = body.replace('src="lesson-data.js"', 'src="player/lesson-data.js"')
    assert "player/lesson.mp3" in body and "player/lesson-data.js" in body
    html = ("<!doctype html>\n<html lang=\"zh-Hant\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            "<!-- 自動產生：請修改 player/index.html 後執行 python3 lesson/build_index.py -->\n"
            "<style>body{margin:0}</style>\n</head>\n<body>\n" + body + "\n</body>\n</html>\n")
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote index.html")


if __name__ == "__main__":
    main()
