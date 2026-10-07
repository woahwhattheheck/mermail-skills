# Mermail Inbox Canary: demo video (2026-10-07)

This is an English demo of the `mermail-inbox-canary` skill, in a long cut and an X cut,
([Nudgen-Marketing/mermail-skills PR #498](https://github.com/Nudgen-Marketing/mermail-skills/pull/498), head `0e9c800`).
It walks through the one recorded live run on hosted Mermail MCP,
`ACCOUNT-MERMAIL-INBOX-CANARY-20261007-01`, and its honest result:

> **OUTBOUND DELIVERED · INBOUND NOT OBSERVED · ROUND-TRIP LATENCY UNAVAILABLE**

## Files

There are two cuts, built from the same scenes and evidence:

| Path | What |
| --- | --- |
| `out/mermail-inbox-canary-demo-20261007.mp4` | **Long cut**, about 4:45, for the 2–5 min listing. H.264 1080p30 with AAC narration, burned-in captions and a soft English subtitle track |
| `out/mermail-inbox-canary-x-cut-20261007.mp4` | **X cut**, about 2:17 (under 140 s), for a native upload to a free X account. Same scenes without the poll, checks and report beats, with a shorter script |
| `out/<cut>.en.srt`, `out/<cut>.en.vtt` | English captions for each cut |
| `out/<cut>-poster.jpg` | Thumbnail taken from the verdict scene |
| `out/<cut>.evidence-manifest.json` | Output receipt (bytes, sha256, duration, streams), source hashes, skill blob SHAs, and the evidence values used |
| `out/<cut>.timeline.json` | Scene and caption timings |
| `src/narration.json`, `src/narration-x.json` | Scripts for the two cuts. `say` is the text sent to TTS; `show` is the caption text with exact identifiers |
| `src/evidence.json` | Every run value shown on screen, with provenance, a hash-verification note, and an explicit `not_claimed` list |
| `src/video.html` | Editable scene source. Seekable, with deterministic `seek(t)`; scenes missing from a cut's timeline are skipped |
| `src/render.mjs`, `src/build_audio.py`, `src/build.sh`, `src/make_manifest.py` | Render pipeline |

## Provenance and limits

- Primary evidence is the captured record packet from the one live run: internal Slack file `F0C783829QB`,
  `mermail-live-record-evidence-20261007.md`. It contains the authoritative JSON, the runner log, the journal and the
  inbound reconciliation, with original sha256 `2291a179…`, `f3ff6fdd…`, `195fc165…` and `64f4473a…` (full values in
  `src/evidence.json`). The packet itself is not committed, because its log contains account details the video does not
  need.
- Record cards are **typeset excerpts** of those captured files. Each fragment is verbatim; some log date prefixes are
  shortened and long lines wrapped, and both are marked on screen. They are not screenshots of software. Derived numbers,
  such as `10:51:33.363 − 10:51:26.827 = 6.536 s`, are labelled as derived.
- The render made **no** Mermail or MCP calls and sent **no** email.
- The video never shows an incoming message ID, an arrival time, a latency figure or a healthy verdict. The
  authoritative record has `inbound_message_id: null` and `round_trip_latency: null`.
- The `scan_status` / `sender_authentication` values shown belong to the outgoing Sent row, the only candidate. They
  are not an inbound result.
- The early runner result (`degraded — round-trip 6.5s`) appears only as withdrawn. It matched the outgoing Sent row
  and took its latency from the `date` field, which is a record date, not a receipt.
- The matcher repair is labelled as tested only against a synthetic case, which is not provider evidence.
- The prompt on screen is the skill's own scenario prompt from `tests/scenarios.json`, and it is labelled that way.
  The record shows the send was approved with `--approve-send` by the operator.
- The narration uses a synthetic voice: Piper `en_US-joe-medium`, which is CC0. Its wording was checked by transcribing the
  rendered narration with Whisper `base.en`. The fonts are Inter and JetBrains Mono, both under the SIL OFL.
- Earlier internal uploads, both superseded by this build: `DRAFT fallback v1` (Slack `F0C7E9UEJE6`), rendered before the packet arrived, and long candidate v2 (Slack `F0C7EC8MFDG`).
- There is no screen recording of a live client in either cut. This cloud session had no authenticated Mermail access, so the
  cuts show typeset captured records rather than client footage, and they are labelled that way.

## Rebuild

```bash
python3 -m venv venv && venv/bin/pip install piper-tts
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium/en_US-joe-medium.onnx
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium/en_US-joe-medium.onnx.json
VOICE=$PWD/en_US-joe-medium.onnx PYTHON=$PWD/venv/bin/python src/build.sh /tmp/canary-work out
# X cut (under 140 s):
NARRATION=narration-x.json LENGTH_SCALE=1.06 NAME=mermail-inbox-canary-x-cut-20261007 \
  VOICE=$PWD/en_US-joe-medium.onnx PYTHON=$PWD/venv/bin/python src/build.sh /tmp/canary-work-x out
```

The build needs Node with `playwright` (Chromium) and ffmpeg. To edit the wording, change `src/narration.json`; the
timings re-flow automatically. To change a visual, edit the matching `<section data-scene=…>` in `src/video.html`.
Elements use `data-at="c2+0.4"` to appear 0.4 s after caption 2 of their scene starts.
