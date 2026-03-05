# Framecast

**Encode any file into a lossless black-and-white video. Decode it back to the exact original.**

Framecast converts binary file data into pixel values — `1` becomes a white pixel, `0` becomes a black pixel — and writes them frame by frame into a lossless `.avi` video. The original file can be perfectly reconstructed from the video alone, verified by MD5 checksum.

---

## How it works

```
┌─────────────┐              ┌──────────────────┐              ┌─────────────┐
│  Any file   │              │  Lossless .avi   │              │  Any file   │
│             │──[ encode ]─▶│  1 bit per pixel │──[ decode ]─▶│  restored   │
│ .zip  .exe  │              │  FFV1 lossless   │              │ MD5 verified│
└─────────────┘              └──────────────────┘              └─────────────┘
```

**Frame layout**

```
Row 0–37    │  Info overlay bar  (frame number, resolution, bit density)
Row 38–719  │  Binary data pixels  (white = 1, black = 0)
```

**Frame 0** of every video is a dedicated metadata frame storing the original filename, MIME type, and exact file size as pixel data. Frames 1–N each hold one chunk of file data. The decoder reads the metadata frame first, then reconstructs the file from the data frames using `numpy.packbits` for fast bit-to-byte conversion.

---

## Resolutions

| Label  | Resolution  | Data per frame  |
|--------|-------------|-----------------|
| 4K     | 3840 × 2160 | 1,018,560 bytes |
| 2K     | 2560 × 1440 | 451,840 bytes   |
| 1080p  | 1920 × 1080 | 253,440 bytes   |
| 720p   | 1280 × 720  | 109,120 bytes   |
| 480p   | 854 × 480   | 49,980 bytes    |

Each pixel stores 1 bit, so data capacity = `width × (height − 38) ÷ 8` bytes per frame.

---

## Requirements

```
pip install opencv-python numpy tqdm
```

OpenCV must support the `FFV1` or `HFYU` lossless codec (standard `opencv-python` on Windows includes both).

---

## Usage

Edit the config block at the top of `main.py`:

```python
FILE_PATH   = r"path\to\your\file"
OUTPUT_DIR  = r"path\to\output\folder"
CHUNK_LABEL = '720p'   # 4K | 2K | 1080p | 720p | 480p
FPS         = 30
OVERLAY     = True
```

Run the encoder:
```bash
python main.py
```

Choose `1` to encode, `2` to decode.

---

## File structure

```
Framecast/
├── config.py           # resolutions, chunk sizes, overlay height
├── encoder.py          # file → binary stream generator
├── video_generator.py  # binary stream → lossless .avi frames
├── pipeline.py         # single-pass encode + video simultaneously
├── decoder.py          # .avi frames → binary stream → original file
└── main.py             # entry point
```

---

## Decode stats

After decoding, Framecast reports:

- **Timing** — frame read time, bit decode time, total time
- **Bit-level** — total bits, padding bits, 1-bit density
- **Per-frame density** — min / max / avg fraction of 1-bits per frame
- **Integrity** — expected vs actual bytes, MD5 checksum, size match

---

## Important

> ⚠️ The `.avi` file uses lossless compression (FFV1). Do **not** convert it to `.mp4` or any other lossy format before decoding — pixel values will be corrupted and the file cannot be recovered. Use [VLC](https://www.videolan.org/) to play the `.avi` for viewing purposes.

---

## GitHub description

> Encode any file into a lossless black-and-white video — one bit per pixel. Decode it back to the exact original with MD5 verification.
