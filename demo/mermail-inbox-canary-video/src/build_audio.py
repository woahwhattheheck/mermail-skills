#!/usr/bin/env python3
"""Synthesize narration with Piper, then emit timeline.json, narration.wav and captions.

Usage: [NARRATION=narration-x.json] build_audio.py <voice.onnx> <out_dir> [length_scale]
"""
import json
import os
import sys
import wave
from pathlib import Path

from piper import PiperVoice, SynthesisConfig

SRC = Path(__file__).resolve().parent
GAP = 0.38  # seconds between sentences inside a scene


def fmt_ts(t, sep):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def main():
    voice_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    length_scale = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    out_dir.mkdir(parents=True, exist_ok=True)
    clips = out_dir / "clips"
    clips.mkdir(exist_ok=True)

    narration = json.loads((SRC / os.environ.get("NARRATION", "narration.json")).read_text())
    gap = narration.get("gap", GAP)
    voice = PiperVoice.load(str(voice_path))
    cfg = SynthesisConfig(length_scale=length_scale)
    rate = voice.config.sample_rate

    timeline = {"fps": 30, "width": 1920, "height": 1080, "scenes": [], "cues": []}
    pcm = bytearray()
    t = 0.0

    def pad(seconds):
        nonlocal t
        n = int(round(seconds * rate))
        pcm.extend(b"\x00\x00" * n)
        t += n / rate

    for scene in narration["scenes"]:
        start = t
        pad(scene["lead"])
        cues = []
        for i, s in enumerate(scene["sentences"]):
            clip = clips / f"{scene['id']}_{i:02d}.wav"
            with wave.open(str(clip), "wb") as wf:
                voice.synthesize_wav(s["say"], wf, syn_config=cfg)
            with wave.open(str(clip), "rb") as rf:
                frames = rf.readframes(rf.getnframes())
            cue_start = t
            pcm.extend(frames)
            t += len(frames) / 2 / rate
            cues.append({"scene": scene["id"], "index": i, "start": round(cue_start, 3),
                         "end": round(t, 3), "text": s["show"]})
            if i < len(scene["sentences"]) - 1:
                pad(gap)
        pad(scene["tail"])
        timeline["scenes"].append({"id": scene["id"], "start": round(start, 3), "end": round(t, 3),
                                   "cues": [c["start"] for c in cues]})
        timeline["cues"].extend(cues)

    timeline["duration"] = round(t, 3)
    with wave.open(str(out_dir / "narration.wav"), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(bytes(pcm))
    (out_dir / "timeline.json").write_text(json.dumps(timeline, indent=2))

    srt, vtt = [], ["WEBVTT", ""]
    for n, c in enumerate(timeline["cues"], 1):
        srt += [str(n), f"{fmt_ts(c['start'], ',')} --> {fmt_ts(c['end'], ',')}", c["text"], ""]
        vtt += [f"{fmt_ts(c['start'], '.')} --> {fmt_ts(c['end'], '.')}", c["text"], ""]
    (out_dir / "captions.en.srt").write_text("\n".join(srt))
    (out_dir / "captions.en.vtt").write_text("\n".join(vtt))

    for sc in timeline["scenes"]:
        print(f"{sc['id']:<11} {sc['start']:7.2f} -> {sc['end']:7.2f}  ({sc['end'] - sc['start']:5.2f}s)")
    print(f"TOTAL {t:.2f}s")


if __name__ == "__main__":
    main()
