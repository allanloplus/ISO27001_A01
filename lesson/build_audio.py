# -*- coding: utf-8 -*-
"""
產生語音（edge-tts 台灣男聲／女聲）、嘴型振幅與時間軸。

輸出：
  player/lesson.mp3       完整課程音軌（播放器使用）
  player/lesson-data.js   場景、台詞、時間軸與嘴型資料（window.LESSON）
  build/lesson.wav        影片合成用音軌

用法：python3 lesson/build_audio.py
"""
import array
import asyncio
import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import wave

import edge_tts
import edge_tts.communicate as _comm

sys.path.insert(0, os.path.dirname(__file__))
from lesson import SCENES, TITLE  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "build", "tts")
PLAYER = os.path.join(ROOT, "player")
RATE = 24000
FPS = 25

VOICES = {
    "A": dict(voice="zh-TW-YunJheNeural", rate="+6%", pitch="+0Hz"),
    "R": dict(voice="zh-TW-HsiaoYuNeural", rate="+12%", pitch="+28Hz"),
}

# 雲端環境需透過代理與其 CA；本機執行時不受影響
_ca = os.environ.get("TTS_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
if os.path.exists(_ca):
    _comm._SSL_CTX = ssl.create_default_context(cafile=_ca)
PROXY = os.environ.get("HTTPS_PROXY") or None

SPOKEN = [
    (r"ISO 27001", "ISO 兩七零零一"),
    (r"RACI", "R A C I"),
    (r"F-ISAC", "F I SAC"),
    (r"ISAC", "I SAC"),
    (r"TWCERT/CC", "TW CERT CC"),
    (r"ISMS", "I S M S"),
    (r"PIMS", "P I M S"),
    (r"MIS", "M I S"),
    (r"SaaS", "沙斯"),
]
DIGITS = "零一二三四五六七八九"


def spoken(text):
    for pat, rep in SPOKEN:
        text = re.sub(pat, rep, text)
    # 5.24 → 五點二四（控制措施編號逐字唸）
    text = re.sub(r"(\d)\.(\d{1,2})",
                  lambda m: DIGITS[int(m.group(1))] + "點" + "".join(DIGITS[int(d)] for d in m.group(2)),
                  text)
    return text


def cache_path(spk, text):
    v = VOICES[spk]
    key = hashlib.sha1(json.dumps([v, spoken(text)], ensure_ascii=False).encode()).hexdigest()[:16]
    return os.path.join(CACHE, f"{spk}_{key}.mp3")


async def synth_all(jobs):
    sem = asyncio.Semaphore(4)

    async def one(spk, text, path):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return
        v = VOICES[spk]
        async with sem:
            for attempt in range(4):
                try:
                    await edge_tts.Communicate(spoken(text), v["voice"], rate=v["rate"],
                                               pitch=v["pitch"], proxy=PROXY).save(path + ".tmp")
                    os.replace(path + ".tmp", path)
                    print("  tts", os.path.basename(path), text[:24])
                    return
                except Exception as e:  # 網路偶發錯誤重試
                    print("  retry", attempt, e)
                    await asyncio.sleep(2 ** attempt)
            raise RuntimeError("TTS failed: " + text)

    await asyncio.gather(*(one(*j) for j in jobs))


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1",
                          "-ar", str(RATE), "-"], check=True, capture_output=True).stdout
    pcm = array.array("h")
    pcm.frombytes(raw)
    # 去除前後靜音
    thr = 300
    s, e = 0, len(pcm)
    while s < e and abs(pcm[s]) < thr:
        s += 1
    while e > s and abs(pcm[e - 1]) < thr:
        e -= 1
    s = max(0, s - int(0.03 * RATE))
    e = min(len(pcm), e + int(0.08 * RATE))
    return pcm[s:e]


def envelope(pcm):
    """每 1/FPS 秒一個 0–9 的嘴型開合值。"""
    step = RATE // FPS
    vals = []
    for i in range(0, len(pcm), step):
        seg = pcm[i:i + step]
        if not seg:
            break
        vals.append((sum(x * x for x in seg[::4]) / len(seg[::4])) ** 0.5)
    peak = sorted(vals)[int(len(vals) * 0.95)] if vals else 1
    peak = peak or 1
    return "".join(str(min(9, int(9 * min(1.0, v / peak) ** 0.8))) for v in vals)


def main():
    os.makedirs(CACHE, exist_ok=True)
    jobs = []
    for sc in SCENES:
        for ln in sc["lines"]:
            jobs.append((ln[0], ln[1], cache_path(ln[0], ln[1])))
    print(f"synthesising {len(jobs)} lines")
    asyncio.run(synth_all(jobs))

    out = array.array("h")

    def silence(sec):
        out.extend([0] * int(sec * RATE))

    t = lambda: len(out) / RATE  # noqa: E731
    scenes, lines = [], []
    silence(0.6)
    for si, sc in enumerate(SCENES):
        start = t()
        silence(1.0 if sc["layout"] != "divider" else 0.8)
        reveal = {0: start}
        shown = 0
        prev = None
        for ln in sc["lines"]:
            spk, text = ln[0], ln[1]
            if prev and prev != spk:
                silence(0.15)
            want = ln[2] if len(ln) > 2 else shown
            if want > shown:
                for k in range(shown + 1, want + 1):
                    reveal[k] = t()
                shown = want
            pcm = decode(cache_path(spk, text))
            ls = t()
            out.extend(pcm)
            lines.append(dict(scene=si, spk=spk, text=text, start=round(ls, 3),
                              end=round(t(), 3), env=envelope(pcm)))
            silence(0.42)
            prev = spk
        silence(0.6 if sc["layout"] not in ("quiz", "divider") else 1.0)
        if sc["layout"] == "summary":
            silence(2.5)
        data = {k: v for k, v in sc.items() if k != "lines"}
        data["start"] = round(start, 3)
        data["end"] = round(t(), 3)
        data["reveal"] = [round(reveal[k], 3) for k in sorted(reveal)]
        scenes.append(data)

    total = t()
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    wav_path = os.path.join(ROOT, "build", "lesson.wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(out.tobytes())
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav_path, "-af", "loudnorm=I=-16:TP=-1.5",
                    "-ar", "44100", "-b:a", "96k", os.path.join(PLAYER, "lesson.mp3")], check=True)

    payload = dict(title=TITLE, duration=round(total, 3), fps=FPS, scenes=scenes, lines=lines)
    with open(os.path.join(PLAYER, "lesson-data.js"), "w", encoding="utf-8") as f:
        f.write("window.LESSON = ")
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    import build_index
    build_index.main()
    print(f"done: {len(scenes)} scenes, {len(lines)} lines, {total / 60:.1f} min")


if __name__ == "__main__":
    main()
