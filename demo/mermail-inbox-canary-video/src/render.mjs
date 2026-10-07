// Deterministic frame renderer: seeks video.html to each frame time and pipes JPEG frames to ffmpeg.
// Usage:
//   node render.mjs stills <timeline.json> <outDir> t1 t2 ...    -> PNG stills for review
//   node render.mjs video  <timeline.json> <outDir> [workers]     -> segment MP4s + video-only.mp4
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const here = path.dirname(fileURLToPath(import.meta.url));
const [mode, tlPath, outDir, ...rest] = process.argv.slice(2);
const timeline = JSON.parse(fs.readFileSync(tlPath, 'utf8'));
const W = timeline.width, H = timeline.height, FPS = timeline.fps;
fs.mkdirSync(outDir, { recursive: true });

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(path.join(here, 'video.html')).href);
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(tl => window.initTimeline(tl), timeline);
  // force-load every font face once so the first frames are not rendered with fallbacks
  await page.evaluate(async () => { await Promise.all([...document.fonts].map(f => f.load())); });
  return page;
}

async function stills(times) {
  const browser = await chromium.launch();
  const page = await openPage(browser);
  for (const t of times) {
    await page.evaluate(tt => window.seek(tt), +t);
    const f = path.join(outDir, `still_${String(t).replace('.', '_')}.png`);
    await page.screenshot({ path: f, type: 'png' });
    console.log(f);
  }
  await browser.close();
}

async function renderSegment(browser, idx, f0, f1) {
  const page = await openPage(browser);
  const out = path.join(outDir, `seg_${String(idx).padStart(2, '0')}.mp4`);
  const ff = spawn('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS),
    '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p',
    '-profile:v', 'high', '-r', String(FPS), out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg ' + c)))));
  for (let f = f0; f < f1; f++) {
    await page.evaluate(tt => window.seek(tt), f / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 93 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - f0) % 300 === 0) console.log(`seg ${idx}: frame ${f - f0}/${f1 - f0}`);
  }
  ff.stdin.end();
  await done;
  await page.close();
  return out;
}

async function video(workers) {
  const total = Math.ceil(timeline.duration * FPS);
  const per = Math.ceil(total / workers);
  const browser = await chromium.launch();
  const t0 = Date.now();
  const segs = await Promise.all(Array.from({ length: workers }, (_, i) =>
    renderSegment(browser, i, i * per, Math.min(total, (i + 1) * per))));
  await browser.close();
  const list = path.join(outDir, 'segments.txt');
  fs.writeFileSync(list, segs.map(s => `file '${path.resolve(s)}'`).join('\n') + '\n');
  await new Promise((res, rej) => spawn('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
    '-i', list, '-c', 'copy', path.join(outDir, 'video-only.mp4')], { stdio: 'inherit' })
    .on('close', c => (c === 0 ? res() : rej(new Error('concat ' + c)))));
  console.log(`rendered ${total} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}

if (mode === 'stills') await stills(rest);
else if (mode === 'video') await video(+(rest[0] || 4));
else { console.error('mode must be stills|video'); process.exit(2); }
