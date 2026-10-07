#!/usr/bin/env python3
"""Emit evidence-manifest.json for a rendered MP4: output receipt, source hashes, git refs, evidence."""
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
REPO = SRC.parents[2]
PR_HEAD = "0e9c800e0003a6a72391252f5f7ece6586cd5880"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args):
    try:
        return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError:
        return None


def main():
    mp4, voice = Path(sys.argv[1]), Path(sys.argv[2])
    probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(mp4)],
        capture_output=True, text=True, check=True).stdout)
    streams = []
    for s in probe["streams"]:
        e = {k: s.get(k) for k in ("index", "codec_type", "codec_name", "profile", "width", "height",
                                   "pix_fmt", "r_frame_rate", "sample_rate", "channels", "bit_rate", "duration")}
        e["language"] = (s.get("tags") or {}).get("language")
        streams.append({k: v for k, v in e.items() if v is not None})
    out_dir = mp4.parent
    siblings = {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p)}
                for p in sorted(out_dir.iterdir())
                if p.is_file() and p != mp4 and p.name.startswith((mp4.stem + ".", mp4.stem + "-"))
                and not p.name.endswith("evidence-manifest.json")}
    sources = {str(p.relative_to(SRC)): sha256(p) for p in sorted(SRC.rglob("*")) if p.is_file()}
    skill_paths = ["skills/mermail-inbox-canary/SKILL.md", "skills/mermail-inbox-canary/references/tools.md",
                   "skills/mermail-inbox-canary/references/security.md", "tests/scenarios.json"]
    manifest = {
        "schema": "mermail-canary-video-manifest/1",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "output": {
            "file": mp4.name,
            "bytes": mp4.stat().st_size,
            "sha256": sha256(mp4),
            "duration_s": float(probe["format"]["duration"]),
            "container": probe["format"]["format_name"],
            "bit_rate": int(probe["format"].get("bit_rate", 0)),
            "streams": streams,
        },
        "companion_files": siblings,
        "render": {
            "method": "deterministic HTML scenes (src/video.html) seeked per frame in headless Chromium via Playwright, JPEG frames -> libx264; Piper TTS narration; captions burned in + soft mov_text track",
            "provider_calls_made_by_render": 0,
            "emails_sent_by_render": 0,
            "voice": {"model": voice.name, "sha256": sha256(voice), "license": "CC0 (rhasspy/piper-voices en_US-joe-medium MODEL_CARD)"},
            "fonts": "Inter, JetBrains Mono (SIL OFL 1.1; licenses in src/fonts)",
            "source_sha256": sources,
        },
        "skill_source": {
            "pr": "https://github.com/Nudgen-Marketing/mermail-skills/pull/498",
            "head": PR_HEAD,
            "blobs": {p: git("rev-parse", f"{PR_HEAD}:{p}") for p in skill_paths},
        },
        "repo": {"branch": git("rev-parse", "--abbrev-ref", "HEAD"), "base_commit": git("rev-parse", "HEAD")},
        "evidence": json.loads((SRC / "evidence.json").read_text()),
    }
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
