# ISO 27001:2022 治理 Governance — 動畫教學影片

ISO/IEC 27001:2022 附錄A 中，控制屬性「運作能力」歸類為 **治理（Governance）** 的控制措施
（5.1、5.2、5.3、5.4、5.5、5.6、5.8、5.24）動畫課程，約 15 分鐘。

- 講者：Q版 **Allan Lo 講師**（台灣男聲 `zh-TW-YunJheNeural`）
- 串場：Q版 **助教阿拉蕾**（`zh-TW-HsiaoYuNeural`，語調調高）
- 三個面向：**ISMS 作業重點**、**稽核查核重點**、**常見的缺失**，含 2 則管理實際案例與 3 題隨堂考

## 快速開始

下載整個資料夾後，直接雙擊根目錄的 **`index.html`**，按「▶ 開始上課」即可播放（可點章節跳轉、變速、全螢幕）。
`index.html` 需與 `player/` 資料夾放在一起；字型需連網載入，離線時會改用系統字型。

## 課程大綱

| 段落 | 內容 |
|---|---|
| 導論 | 開場、治理運作流程全景圖（原圖 5.5 特殊關注群組更正為 5.6）、三個面向 |
| 第一篇 作業重點 | 5.1／5.2／5.3／5.4 → 案例①總經理的私人隨身碟 → 5.5／5.6／5.8／5.24 → 案例②週五晚上的勒索軟體 |
| 第二篇 稽核重點 | 稽核三招（看文件、問人員、查紀錄）、三組查核清單與稽核員常問問句 |
| 第三篇 常見缺失 | 9 則典型缺失（次要不符合／觀察事項）與改善建議 |
| 測驗與總結 | 阿拉蕾隨堂考 3 題、治理三句話 |

## 檔案

| 路徑 | 說明 |
|---|---|
| `index.html` | **直接雙擊開啟的動畫播放器**（自動產生，引用 `player/` 內的音檔與資料） |
| `dist/ISO27001_治理Governance.mp4` | 成品影片（1280×720, 25fps, AAC） |
| `player/index.html` | 播放器原始檔（Artifact 片段，無 doctype）；修改後執行 `python3 lesson/build_index.py` 更新根目錄 `index.html` |
| `lesson/build_index.py` | 由 `player/index.html` 產生根目錄 `index.html` |
| `lesson/lesson.py` | **課程腳本**（台詞、投影片內容）— 修改內容只要改這裡 |
| `lesson/build_audio.py` | 產生語音、嘴型資料與時間軸 |
| `lesson/render_video.mjs` | 逐格渲染播放器並合成 MP4 |

## 重新產生

```bash
pip install edge-tts                 # 語音合成
python3 lesson/build_audio.py        # → player/lesson.mp3、player/lesson-data.js、build/lesson.wav
node lesson/render_video.mjs --shots 30,120   # 先看幾張截圖（build/shots/）
node lesson/render_video.mjs         # → dist/ISO27001_治理Governance.mp4（需 playwright + ffmpeg）
python3 lesson/build_index.py        # 更新根目錄 index.html（build_audio.py 也會自動執行）
```

語音快取在 `build/tts/`，只有改過的台詞會重新合成。
台詞中的 `5.24` 等編號會自動轉成「五點二四」的唸法，英文縮寫的唸法規則在 `build_audio.py` 的 `SPOKEN`。

> 案例為輔導現場改編、已去識別化；台灣法規通報時限請以主管機關最新公告為準。
> 阿拉蕾為致敬造型的 Q 版助教角色，僅供教學使用。
