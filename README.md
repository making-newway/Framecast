# Framecast

**Encode any file or folder into a lossless RGB video. Decode it back to the exact original.**

Framecast converts binary file data into RGB pixel values — every 3 consecutive bytes become one pixel — and writes them frame by frame into a lossless `.avi` video. The original file or folder can be perfectly reconstructed from the video alone, verified by MD5 checksum. Designed for large file distribution via Google Drive or any platform that preserves file integrity.

---

## How it works

```
+--------------------+             +----------------------+             +--------------------+
|  Any file or       |             |  Lossless .avi       |             |  Any file or       |
|  folder            |--[encode]-->|  3 bytes per pixel   |--[decode]-->|  folder restored   |
|  .zip  .exe  dir/  |             |  FFV1 lossless       |             |  MD5 verified      |
+--------------------+             +----------------------+             +--------------------+
```

**Frame layout**

```
Row 0-37    |  Info overlay bar  (frame number, resolution)
Row 38-H    |  RGB data pixels   (3 bytes per pixel)
```

**Frame 0** of every part is a metadata frame storing filename, MIME type, file size, source type and compression flag. Frames 1-N each hold one chunk of file data packed as RGB pixels.

---

## Key numbers

| Resolution | Data per frame  | 6GB file → parts |
|------------|-----------------|------------------|
| 4K         | ~23.3 MB        | ~2 parts @ 4GB   |
| 2K         | ~10.3 MB        | ~4 parts @ 4GB   |
| 1080p      | ~5.8 MB         | ~8 parts @ 4GB   |
| 720p       | ~2.5 MB         | ~18 parts @ 4GB  |
| 480p       | ~1.1 MB         | ~40 parts @ 4GB  |

**Video size vs original file size**

| Encoding      | Bytes per pixel | Size ratio |
|---------------|-----------------|------------|
| Old 1-bit     | 1 bit           | ~5.5×      |
| RGB (current) | 3 bytes         | ~1.0×      |

---

## Requirements

```bash
pip install opencv-python numpy tqdm zstandard
```
or
```bash
pip install -r requirements.txt
```

OpenCV must support `FFV1` or `HFYU` lossless codec — standard `opencv-python` on Windows includes both.

> Use [VLC](https://www.videolan.org/) to play `.avi` files. Do **not** re-encode or convert to `.mp4` — pixel values will be destroyed and the file cannot be recovered.

---

## Usage

Edit `parameters.json` then run:

```bash
python main.py
```

### Encode a file

```json
{
    "action"      : "encode",
    "file_path"   : "D:\\path\\to\\file.zip",
    "output_dir"  : "D:\\path\\to\\output",
    "chunk_label" : "4K",
    "fps"         : 30,
    "overlay"     : true,
    "compress"    : false
}
```

### Encode a folder

```json
{
    "action"      : "encode",
    "file_path"   : "D:\\path\\to\\MyFolder",
    "output_dir"  : "D:\\path\\to\\output",
    "chunk_label" : "4K",
    "fps"         : 30,
    "overlay"     : true,
    "compress"    : false
}
```

Framecast automatically zips the folder before encoding and restores it as a folder after decoding.

### Decode

Point `file_path` at the output folder, a `_manifest.json`, or a single `.avi`:

```json
{
    "action"      : "decode",
    "file_path"   : "D:\\path\\to\\output",
    "output_dir"  : "D:\\path\\to\\restored",
    "chunk_label" : "4K",
    "fps"         : 30,
    "overlay"     : true,
    "compress"    : false
}
```

Framecast scans the folder automatically — manifest first, single `.avi` fallback.

---

## File structure

```
Framecast/
├── config.py           # resolutions, chunk sizes, part size limit
├── encoder.py          # file/folder → chunks generator, optional zstd
├── video_generator.py  # chunks → RGB frames → lossless .avi
├── pipeline.py         # orchestrates encode, part splitting, manifest
├── decoder.py          # .avi parts → bytes → restored file/folder
├── manifest.py         # manifest read/write/verify
├── logger.py           # appends stats to framecast.log
├── main.py             # entry point, reads parameters.json
├── parameters.json     # user config — action, paths, settings
├── test_output/        # local test output (gitignored)
│   └── .gitkeep
└── testing.py          # local test script (gitignored)
```

---

## Multi-part output

For files larger than 4GB, Framecast automatically splits the output into multiple parts:

```
output/
├── MyFile_4K_30fps_part001.avi
├── MyFile_4K_30fps_part002.avi
├── MyFile_4K_30fps_part003.avi
└── MyFile_manifest.json
```

Each part has its own MD5 checksum stored in the manifest. The decoder verifies each part before writing — a corrupt part is skipped and reported rather than silently writing bad data.

---

## Logging

Every encode and decode run appends to `framecast.log`:

```
==========================================================
[2026-03-08 11:59:24]  ENCODE
==========================================================
  filename        : Legends ZA.zip
  file_size_bytes : 6,446,577,831
  total_parts     : 2
  total_frames    : 264
  duration_s      : 8.8
  total_time_s    : 294.431
  parts           :
    [001]  Legends ZA_4K_30fps_part001.avi  (4,277,952,000 bytes | 175 frames | MD5: 89033f6b777e...)
    [002]  Legends ZA_4K_30fps_part002.avi  (2,168,625,831 bytes | 89 frames  | MD5: d92c004bcc0b...)
==========================================================
```

---

## Compression

Set `"compress": true` in `parameters.json` to enable zstd pre-compression before encoding.

> Only effective on uncompressed source files such as `.txt`, `.csv`, `.wav`, `.bmp`, or raw database dumps. Has no effect on already-compressed files like `.zip`, `.mp4`, or `.exe`.

---

## Data integrity

| Risk                        | Protection                                      |
|-----------------------------|-------------------------------------------------|
| Corrupt part download       | Per-part MD5 verified before writing            |
| Missing part                | Pre-allocated output file, zero-filled hole     |
| Encoding interrupted        | Manifest written only after all parts complete  |
| Last frame padding          | `f.truncate(exact_filesize)` after decode       |
| Metadata frame corrupted    | Manifest JSON used as fallback                  |
| RAM overflow on large files | One frame at a time streamed directly to disk   |

---

## GitHub description

> Encode any file or folder into a lossless RGB video — 3 bytes per pixel, split into 4GB parts. Decode back to the exact original with per-part MD5 verification.
