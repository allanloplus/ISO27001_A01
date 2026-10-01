// 將 player/index.html 逐格渲染成 MP4（1280×720），並混入 build/lesson.wav 音軌。
//
// 用法：
//   node lesson/render_video.mjs                 # 完整影片 → dist/ISO27001_治理Governance.mp4
//   node lesson/render_video.mjs --shots 5,60,90 # 只輸出指定秒數的截圖到 build/shots/
//
// 需要：playwright（含 Chromium）、ffmpeg。
import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
let chromium;
for (const p of ["playwright", "/opt/node-tools/node_modules/playwright", path.join(process.env.NODE_PATH || "", "playwright")]) {
  try { ({ chromium } = require(p)); break; } catch {}
}
if (!chromium) throw new Error("找不到 playwright，請先 npm i -D playwright");

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const PLAYER = path.join(ROOT, "player");
const BUILD = path.join(ROOT, "build");
const DIST = path.join(ROOT, "dist");
const FPS = 25;
const WORKERS = Math.max(1, Math.min(4, os.cpus().length));
const args = process.argv.slice(2);

// 播放器原檔是 artifact 片段（無 doctype），渲染時包成完整文件
const page = fs.readFileSync(path.join(PLAYER, "index.html"), "utf8");
const renderFile = path.join(PLAYER, ".render.html");
fs.writeFileSync(renderFile, `<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=1280">` +
  `<style>html,body{margin:0;background:#F8FAFD}</style></head><body>${page}</body></html>`);
const url = "file://" + renderFile + "?render";

async function openPage(browser) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const p = await ctx.newPage();
  p.on("pageerror", e => console.error("pageerror", e.message));
  await p.goto(url, { waitUntil: "networkidle" });
  await p.evaluate(() => window.lessonReady);
  return p;
}

function ffmpeg(argv) {
  const ff = spawn("ffmpeg", ["-y", "-v", "error", ...argv], { stdio: ["pipe", "inherit", "inherit"] });
  ff.done = new Promise((res, rej) => ff.on("close", c => (c === 0 ? res() : rej(new Error("ffmpeg " + c)))));
  return ff;
}

async function shots(times) {
  fs.mkdirSync(path.join(BUILD, "shots"), { recursive: true });
  const browser = await chromium.launch();
  const p = await openPage(browser);
  for (const t of times) {
    await p.evaluate(t => window.renderAt(t), t);
    const f = path.join(BUILD, "shots", `t${String(t).padStart(5, "0")}.png`);
    await p.screenshot({ path: f, clip: { x: 0, y: 0, width: 1280, height: 720 } });
    console.log(f);
  }
  await browser.close();
}

async function full() {
  fs.mkdirSync(DIST, { recursive: true });
  fs.mkdirSync(path.join(BUILD, "seg"), { recursive: true });
  const browser = await chromium.launch();
  const probe = await openPage(browser);
  const duration = await probe.evaluate(() => window.lessonDuration);
  await probe.context().close();
  const total = Math.ceil(duration * FPS);
  const per = Math.ceil(total / WORKERS);
  console.log(`frames ${total}, workers ${WORKERS}`);
  const t0 = Date.now();
  let doneFrames = 0;
  const segs = [];
  await Promise.all([...Array(WORKERS).keys()].map(async w => {
    const from = w * per, to = Math.min(total, from + per);
    const seg = path.join(BUILD, "seg", `seg${w}.mp4`);
    segs[w] = seg;
    const p = await openPage(browser);
    const ff = ffmpeg(["-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-",
      "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", String(FPS), seg]);
    for (let f = from; f < to; f++) {
      await p.evaluate(t => window.renderAt(t), f / FPS);
      const buf = await p.screenshot({ type: "jpeg", quality: 92, clip: { x: 0, y: 0, width: 1280, height: 720 } });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
      if (++doneFrames % 500 === 0) {
        const el = (Date.now() - t0) / 1000;
        console.log(`  ${doneFrames}/${total}  ${el.toFixed(0)}s  eta ${((total - doneFrames) * el / doneFrames).toFixed(0)}s`);
      }
    }
    ff.stdin.end();
    await ff.done;
    await p.context().close();
  }));
  await browser.close();
  const list = path.join(BUILD, "seg", "list.txt");
  fs.writeFileSync(list, segs.map(s => `file '${s}'`).join("\n"));
  const out = path.join(DIST, "ISO27001_治理Governance.mp4");
  await ffmpeg(["-f", "concat", "-safe", "0", "-i", list, "-i", path.join(BUILD, "lesson.wav"),
    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
    "-shortest", "-movflags", "+faststart", out]).done;
  console.log("done →", out);
}

const si = args.indexOf("--shots");
try {
  if (si >= 0) await shots(args[si + 1].split(",").map(Number));
  else await full();
} finally {
  fs.rmSync(renderFile, { force: true });
}
