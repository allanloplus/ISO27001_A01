# -*- coding: utf-8 -*-
"""
從角色設定圖（lesson/art/*.jpg）裁切表情，去背後輸出 player/sprites/*.png。

每張表情以「固定大小的格子」裁切，同一角色的各表情在畫面上自然對齊，
切換表情時頭部位置不會跳動。

用法：python3 lesson/build_sprites.py
需要：pillow、numpy、scipy
"""
import json
import os

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "lesson", "art")
OUT = os.path.join(ROOT, "player", "sprites")

# (x, y) 為格子左上角（原圖像素）；同一角色共用格子大小，且頭部置中，換表情時不跳動
# mouth：說話時嘴型動畫的位置（格子內座標）cx, cy, 寬, 原圖嘴高；open=原圖是張嘴
ALLAN = dict(sheet="allan_sheet.jpg", size=(330, 340), cells={
    "smile": (730, 785, dict(cx=163, cy=203, w=70, h=10, open=False)),   # 微笑（說話基底）
    "laugh": (1035, 785, None),   # 大笑
    "think": (1340, 785, None),   # 托下巴思考
    "wow":   (730, 1130, None),   # 驚訝
    "point": (1035, 1130, dict(cx=165, cy=210, w=52, h=10, open=False)),  # 舉手指（重點提示）
    "wink":  (1340, 1130, None),  # 眨眼
})
ARALE = dict(sheet="arale_sheet.jpg", size=(356, 304), cells={
    "laugh":    (438, 808, None),     # 開心大笑
    "think":    (824, 808, None),     # 托下巴聆聽
    "wow":      (1211, 808, None),    # 驚訝
    "confused": (1596, 808, dict(cx=147, cy=190, w=22, h=8, open=False)),   # 抓頭疑問
    "explain":  (438, 1144, dict(cx=161, cy=189, w=26, h=26, open=True)),   # 攤手說明
    "cry":      (824, 1144, None),    # 哭哭
    "thumb":    (1211, 1144, None),   # 比讚
    "cheer":    (1596, 1144, dict(cx=158, cy=197, w=44, h=32, open=True)),  # 握拳加油
})


def cutout(img):
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    light = (a.min(axis=2) > 222) & ((a.max(axis=2) - a.min(axis=2)) < 26)
    # 只移除與邊框相連的淺色背景
    lab, _ = ndimage.label(light)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(edge))
    fg = ~bg
    # 只保留最大的前景區塊（去除相鄰格子的殘片、格線）
    lab2, n = ndimage.label(fg)
    if n > 1:
        sizes = ndimage.sum(fg, lab2, range(1, n + 1))
        fg = lab2 == (int(np.argmax(sizes)) + 1)
    fg = ndimage.binary_fill_holes(fg)
    alpha = Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    out = img.convert("RGBA")
    out.putalpha(alpha)
    return out


def skin_near(img, m):
    """取嘴巴上方（人中）一帶的膚色，用來蓋掉原本的嘴。"""
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    y0 = int(m["cy"] - m["h"] / 2 - 7)
    xs = range(int(m["cx"] - m["w"] / 2), int(m["cx"] + m["w"] / 2))
    px = [a[y, x] for y in (y0, y0 - 2) for x in xs if a[y, x].min() > 120]
    r, g, b = np.median(np.array(px), axis=0).astype(int)
    return f"#{r:02x}{g:02x}{b:02x}"


def build(spec, prefix):
    sheet = Image.open(os.path.join(ART, spec["sheet"]))
    w, h = spec["size"]
    meta = {}
    for name, (x, y, mouth) in spec["cells"].items():
        crop = sheet.crop((x, y, x + w, y + h))
        sp = cutout(crop)
        path = os.path.join(OUT, f"{prefix}_{name}.png")
        sp.save(path, optimize=True)
        print(path, sp.size)
        if mouth:
            mouth = dict(mouth, skin=skin_near(crop, mouth))
        meta[name] = dict(src=f"sprites/{prefix}_{name}.png", mouth=mouth)
    return dict(w=w, h=h, moods=meta)


def main():
    os.makedirs(OUT, exist_ok=True)
    data = dict(A=build(ALLAN, "allan"), R=build(ARALE, "arale"))
    with open(os.path.join(OUT, "sprites.js"), "w", encoding="utf-8") as f:
        f.write("window.SPRITES = " + json.dumps(data, ensure_ascii=False) + ";\n")


if __name__ == "__main__":
    main()
