import cv2
import json
import os
import time
import zipfile
import hashlib
import numpy as np
from tqdm import tqdm

from config   import FRAME_SIZES, OVERLAY_HEIGHT_PX
from manifest import read_manifest, verify_part, compute_md5


# ── Internal helpers ──────────────────────────────────────────────────────────

def _detect_resolution(video_path):
    cap    = cv2.VideoCapture(video_path)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    for label, (w, h) in FRAME_SIZES.items():
        if w == width and h == height:
            return label, width, height, fps, total

    raise ValueError(f"Resolution {width}x{height} doesn't match any known FRAME_SIZES.")


def _read_metadata_frame(frame_bgr, width, height):
    chan        = frame_bgr[:, :, 2]
    bits        = (chan[OVERLAY_HEIGHT_PX:height, 0:width].flatten() >= 128).astype(np.uint8)
    meta_length = int(''.join(map(str, bits[:32])), 2)
    json_bits   = bits[32: 32 + meta_length * 8]
    meta_bytes  = bytes(
        int(''.join(map(str, json_bits[i:i + 8])), 2)
        for i in range(0, len(json_bits), 8)
    )
    return json.loads(meta_bytes.decode('utf-8'))


def _read_rgb_data_frame(frame_bgr, width, height):
    data = frame_bgr[OVERLAY_HEIGHT_PX:height, 0:width, :]
    return data.flatten()


def _preallocate_file(path, size):
    with open(path, 'wb') as f:
        f.seek(size - 1)
        f.write(b'\x00')


def _maybe_unzip(zip_path, output_dir, original_name):
    """Unzip a folder archive and remove the zip afterwards."""
    print(f"  📁  Extracting folder → {os.path.join(output_dir, original_name)}")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(output_dir)
    os.remove(zip_path)
    print(f"  ✅  Extracted: {original_name}")
    return os.path.join(output_dir, original_name)


def _maybe_decompress(output_path, compressed):
    if not compressed:
        return
    try:
        import zstandard as zstd
    except ImportError:
        raise ImportError("zstandard not installed. Run: pip install zstandard")
    with open(output_path, 'rb') as f:
        data = f.read()
    dctx = zstd.ZstdDecompressor()
    with open(output_path, 'wb') as f:
        f.write(dctx.decompress(data))


# ── Single-part decode ────────────────────────────────────────────────────────

def decode_single(video_path, output_dir, overlay=True):
    os.makedirs(output_dir, exist_ok=True)
    wall_start = time.perf_counter()

    chunk_label, width, height, video_fps, total_frames = _detect_resolution(video_path)
    video_size_bytes = os.path.getsize(video_path)

    cap     = cv2.VideoCapture(video_path)
    ret, f0 = cap.read()
    if not ret:
        cap.release()
        raise RuntimeError("Could not read metadata frame from video.")

    metadata      = _read_metadata_frame(f0, width, height)
    expected_size = metadata['filesize_bytes']
    filename      = metadata['filename']
    compressed    = metadata.get('compressed', False)
    source_type   = metadata.get('source_type', 'file')
    original_name = metadata.get('original_name', filename)

    output_path = os.path.join(output_dir, filename)
    _preallocate_file(output_path, expected_size)

    bytes_written = 0
    data_frames   = 0

    with open(output_path, 'r+b') as out_f:
        with tqdm(total=total_frames - 1, desc='Decoding', unit='frame', colour='cyan') as pbar:
            while True:
                ret, frame_bgr = cap.read()
                if not ret:
                    break
                raw       = _read_rgb_data_frame(frame_bgr, width, height).tobytes()
                remaining = expected_size - bytes_written
                to_write  = raw[:remaining]
                out_f.write(to_write)
                bytes_written += len(to_write)
                data_frames   += 1
                pbar.update(1)

    cap.release()

    with open(output_path, 'r+b') as f:
        f.truncate(expected_size)

    _maybe_decompress(output_path, compressed)

    # Unzip if source was a folder
    final_path = output_path
    if source_type == 'folder':
        final_path = _maybe_unzip(output_path, output_dir, original_name)

    checksum = compute_md5(output_path) if os.path.isfile(output_path) else 'N/A (folder extracted)'
    actual   = os.path.getsize(output_path) if os.path.isfile(output_path) else expected_size
    total_t  = time.perf_counter() - wall_start

    stats = {
        'mode'            : 'single',
        'video_path'      : video_path,
        'video_size_bytes': video_size_bytes,
        'chunk_label'     : chunk_label,
        'resolution'      : f"{width}x{height}",
        'video_fps'       : round(video_fps, 2),
        'total_frames'    : total_frames,
        'data_frames'     : data_frames,
        'total_time_s'    : round(total_t, 4),
        'source_type'     : source_type,
        'original_name'   : original_name,
        'filename'        : filename,
        'mime_type'       : metadata.get('mime_type', ''),
        'expected_bytes'  : expected_size,
        'actual_bytes'    : actual,
        'size_match'      : actual == expected_size,
        'checksum_md5'    : checksum,
        'output_path'     : final_path,
    }
    return final_path, metadata, stats


# ── Multi-part decode ─────────────────────────────────────────────────────────

def decode_from_manifest(manifest_path, output_dir, overlay=True):
    os.makedirs(output_dir, exist_ok=True)
    wall_start  = time.perf_counter()
    manifest    = read_manifest(manifest_path)
    parts_dir   = os.path.dirname(manifest_path)

    filename      = manifest['filename']
    expected_size = manifest['filesize']
    compressed    = manifest.get('compressed', False)
    source_type   = manifest.get('source_type', 'file')
    original_name = manifest.get('original_name', filename)
    total_parts   = manifest['total_parts']
    output_path   = os.path.join(output_dir, filename)

    _preallocate_file(output_path, expected_size)

    part_results = []
    total_frames = 0

    with open(output_path, 'r+b') as out_f:
        for part_info in manifest['parts']:
            part_num     = part_info['part']
            part_file    = os.path.join(parts_dir, part_info['file'])
            expected_md5 = part_info.get('md5', None)
            byte_offset  = part_info['byte_offset']
            byte_length  = part_info['byte_length']

            if expected_md5:
                ok, actual_md5 = verify_part(part_file, expected_md5)
                if not ok:
                    part_results.append({
                        'part'  : part_num,
                        'status': 'CORRUPT',
                        'md5_ok': False,
                    })
                    print(f"  ⚠  Part {part_num} MD5 mismatch — skipping")
                    continue
            else:
                actual_md5 = compute_md5(part_file)

            cap         = cv2.VideoCapture(part_file)
            width       = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            part_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.read()  # skip metadata frame

            out_f.seek(byte_offset)
            bytes_written = 0
            t0 = time.perf_counter()

            with tqdm(total=part_frames - 1,
                      desc=f'Part {part_num}/{total_parts}',
                      unit='frame', colour='cyan') as pbar:
                while True:
                    ret, frame_bgr = cap.read()
                    if not ret:
                        break
                    raw       = _read_rgb_data_frame(frame_bgr, width, height).tobytes()
                    remaining = byte_length - bytes_written
                    to_write  = raw[:remaining]
                    out_f.write(to_write)
                    bytes_written += len(to_write)
                    pbar.update(1)

            cap.release()
            elapsed = time.perf_counter() - t0
            total_frames += part_frames - 1

            part_results.append({
                'part'         : part_num,
                'status'       : 'OK',
                'md5_ok'       : True,
                'bytes_written': bytes_written,
                'time_s'       : round(elapsed, 4),
            })

    with open(output_path, 'r+b') as f:
        f.truncate(expected_size)

    _maybe_decompress(output_path, compressed)

    # Unzip if source was a folder
    final_path = output_path
    if source_type == 'folder':
        final_path = _maybe_unzip(output_path, output_dir, original_name)

    checksum   = compute_md5(output_path) if os.path.isfile(output_path) else 'N/A (folder extracted)'
    actual     = os.path.getsize(output_path) if os.path.isfile(output_path) else expected_size
    total_t    = time.perf_counter() - wall_start
    parts_ok   = sum(1 for p in part_results if p['status'] == 'OK')
    parts_fail = total_parts - parts_ok

    stats = {
        'mode'          : 'multi-part',
        'manifest_path' : manifest_path,
        'source_type'   : source_type,
        'original_name' : original_name,
        'filename'      : filename,
        'mime_type'     : manifest.get('mime_type', ''),
        'chunk_label'   : manifest['chunk_label'],
        'total_parts'   : total_parts,
        'parts_ok'      : parts_ok,
        'parts_failed'  : parts_fail,
        'total_frames'  : total_frames,
        'total_time_s'  : round(total_t, 4),
        'expected_bytes': expected_size,
        'actual_bytes'  : actual,
        'size_match'    : actual == expected_size,
        'checksum_md5'  : checksum,
        'output_path'   : final_path,
        'part_results'  : part_results,
    }
    return final_path, manifest, stats


# ── Folder auto-detect ────────────────────────────────────────────────────────

def decode_from_folder(folder_path, output_dir, overlay=True):
    entries   = os.listdir(folder_path)
    manifests = sorted(f for f in entries if f.endswith('_manifest.json'))
    avis      = sorted(f for f in entries if f.endswith('.avi'))

    if manifests:
        manifest_path = os.path.join(folder_path, manifests[0])
        print(f"  ✅  Found manifest: {manifests[0]}")
        return decode_from_manifest(manifest_path, output_dir, overlay)

    if len(avis) == 1:
        print(f"  ✅  Found single video: {avis[0]}")
        return decode_single(os.path.join(folder_path, avis[0]), output_dir, overlay)

    if len(avis) == 0:
        raise FileNotFoundError(f"No manifest.json or .avi files found in: {folder_path}")

    raise RuntimeError(
        f"Found {len(avis)} .avi files but no manifest.json in: {folder_path}\n"
        f"Cannot safely determine part order without a manifest."
    )


# ── Auto-dispatch ─────────────────────────────────────────────────────────────

def decode(input_path, output_dir, overlay=True):
    if os.path.isdir(input_path):
        return decode_from_folder(input_path, output_dir, overlay)
    elif input_path.endswith('.json'):
        return decode_from_manifest(input_path, output_dir, overlay)
    else:
        return decode_single(input_path, output_dir, overlay)
