#!/usr/bin/env bash
# End-to-end render of the Mermail Inbox Canary demo video.
#   VOICE=/path/en_US-joe-medium.onnx PYTHON=/path/venv/bin/python ./build.sh <work_dir> <out_dir>
# Short X cut: NARRATION=narration-x.json LENGTH_SCALE=1.0 NAME=mermail-inbox-canary-x-cut-20261007 ./build.sh ...
# Needs: python3 + piper-tts, node + playwright (chromium), ffmpeg/ffprobe.
# Makes no Mermail/MCP calls and sends no email: it only renders the recorded values in src/.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:?work dir}"; OUT="${2:?out dir}"
PY="${PYTHON:-python3}"
: "${VOICE:?set VOICE to the en_US-joe-medium.onnx path}"
mkdir -p "$WORK" "$OUT"

# 1) narration + timeline + captions
NARRATION="${NARRATION:-narration.json}" "$PY" "$HERE/build_audio.py" "$VOICE" "$WORK/audio" "${LENGTH_SCALE:-1.06}"

# 2) frames -> video-only.mp4
node "$HERE/render.mjs" video "$WORK/audio/timeline.json" "$WORK/render" "${WORKERS:-4}"

# 3) mux: loudness-normalised AAC narration + soft English subtitle track (captions are also burned in)
NAME="${NAME:-mermail-inbox-canary-demo-20261007}"
TITLE="${TITLE:-Mermail Inbox Canary — real diagnostic run (2026-10-07)}"
ffmpeg -y -hide_banner -loglevel error \
  -i "$WORK/render/video-only.mp4" -i "$WORK/audio/narration.wav" -i "$WORK/audio/captions.en.srt" \
  -map 0:v -map 1:a -map 2:s -c:v copy \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000" -ac 2 -c:a aac -b:a 192k \
  -c:s mov_text -metadata:s:s:0 language=eng -disposition:s:0 0 -metadata:s:a:0 language=eng \
  -metadata title="$TITLE" \
  -metadata comment="Run ACCOUNT-MERMAIL-INBOX-CANARY-20261007-01. Outbound delivered; inbound not observed; latency unavailable. https://github.com/Nudgen-Marketing/mermail-skills/pull/498" \
  -movflags +faststart "$OUT/$NAME.mp4"

cp "$WORK/audio/captions.en.srt" "$OUT/$NAME.en.srt"
cp "$WORK/audio/captions.en.vtt" "$OUT/$NAME.en.vtt"
cp "$WORK/audio/timeline.json" "$OUT/$NAME.timeline.json"

# 4) poster frame (verdict scene) + manifest
T=$("$PY" -c "import json,sys;tl=json.load(open('$WORK/audio/timeline.json'));s=[x for x in tl['scenes'] if x['id']=='verdict'][0];print(round(s['end']-1.2,2))")
ffmpeg -y -hide_banner -loglevel error -ss "$T" -i "$OUT/$NAME.mp4" -frames:v 1 -q:v 2 "$OUT/$NAME-poster.jpg"
"$PY" "$HERE/make_manifest.py" "$OUT/$NAME.mp4" "$VOICE" > "$OUT/$NAME.evidence-manifest.json"
echo "done: $OUT/$NAME.mp4"
