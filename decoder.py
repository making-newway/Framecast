import cv2
import json
import os
import time
import hashlib
import numpy as np
from tqdm import tqdm
from config import FRAME_SIZES, OVERLAY_HEIGHT_PX


def _detect_chunk_label(video_path):
    cap    = cv2.VideoCapture(video_path)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    for label, (w, h) in FRAME_SIZES.items():
        if w == width and h == height:
            return label, width, height, fps

    raise ValueError(f"Video resolution {width}x{height} doesn't match any known FRAME_SIZES: {FRAME_SIZES}")


def _read_metadata_frame(frame_bgr, width, height):
    chan        = frame_bgr[:, :, 2]
    bits        = (chan[OVERLAY_HEIGHT_PX:height, 0:width].flatten() >= 128).astype(np.uint8)
    meta_length = int(''.join(map(str, bits[:32])), 2)
    json_bits   = bits[32 : 32 + meta_length * 8]
    meta_bytes  = bytes(int(''.join(map(str, json_bits[i:i+8])), 2) for i in range(0, len(json_bits), 8))
    return json.loads(meta_bytes.decode('utf-8'))


def _read_data_frame(frame_bgr, width, height, has_overlay):
    chan      = frame_bgr[:, :, 2]
    start_row = OVERLAY_HEIGHT_PX if has_overlay else 0
    return (chan[start_row:height, 0:width].flatten() >= 128).astype(np.uint8)


def _frame_density(bits):
    return float(np.mean(bits)) if len(bits) > 0 else 0.0


def decode_from_video(video_path, output_dir, overlay=True):
    os.makedirs(output_dir, exist_ok=True)
    wall_start = time.perf_counter()

    chunk_label, width, height, video_fps = _detect_chunk_label(video_path)
    video_size_bytes = os.path.getsize(video_path)

    cap          = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    ret, frame0 = cap.read()
    if not ret:
        cap.release()
        raise RuntimeError("Could not read frame 0 (metadata frame) from video.")

    metadata = _read_metadata_frame(frame0, width, height)

    all_bits         = []
    frame_densities  = []
    data_frame_count = 0
    frame_read_start = time.perf_counter()

    with tqdm(total=total_frames - 1, desc='Decoding', unit='frame', colour='cyan') as pbar:
        while True:
            ret, frame_bgr = cap.read()
            if not ret:
                break
            bits = _read_data_frame(frame_bgr, width, height, has_overlay=overlay)
            frame_densities.append(_frame_density(bits))
            all_bits.append(bits)
            data_frame_count += 1
            pbar.update(1)


    cap.release()
    frame_read_time = time.perf_counter() - frame_read_start
    all_bits        = np.concatenate(all_bits) if all_bits else np.array([], dtype=np.uint8)
    total_bits      = len(all_bits)
    ones_count      = int(np.sum(all_bits))

    decode_start   = time.perf_counter()
    trim           = (total_bits // 8) * 8
    file_bytes_raw = np.packbits(all_bits[:trim]).tobytes()
    expected_size  = metadata['filesize_bytes']
    file_bytes     = file_bytes_raw[:expected_size]
    padding_bits   = (len(file_bytes_raw) - len(file_bytes)) * 8
    decode_time    = time.perf_counter() - decode_start

    actual_size  = len(file_bytes)
    size_match   = actual_size == expected_size
    checksum_md5 = hashlib.md5(file_bytes).hexdigest()

    output_file_path = os.path.join(output_dir, metadata['filename'])
    with open(output_file_path, 'wb') as f:
        f.write(file_bytes)

    output_size_bytes = os.path.getsize(output_file_path)
    total_time        = time.perf_counter() - wall_start

    stats = {
        'video_path'           : video_path,
        'video_size_bytes'     : video_size_bytes,
        'chunk_label'          : chunk_label,
        'resolution'           : f"{width}x{height}",
        'video_fps'            : round(video_fps, 2),
        'total_frames'         : total_frames,
        'data_frames'          : data_frame_count,
        'frame_read_time_s'    : round(frame_read_time, 4),
        'decode_time_s'        : round(decode_time, 4),
        'total_time_s'         : round(total_time, 4),
        'total_bits_collected' : total_bits,
        'padding_bits'         : padding_bits,
        'ones_count'           : ones_count,
        'zeros_count'          : total_bits - ones_count,
        'bit_density'          : round(ones_count / total_bits, 4) if total_bits else 0,
        'frame_densities'      : [round(d, 4) for d in frame_densities],
        'min_frame_density'    : round(min(frame_densities), 4) if frame_densities else 0,
        'max_frame_density'    : round(max(frame_densities), 4) if frame_densities else 0,
        'avg_frame_density'    : round(sum(frame_densities) / len(frame_densities), 4) if frame_densities else 0,
        'filename'             : metadata['filename'],
        'mime_type'            : metadata['mime_type'],
        'expected_bytes'       : expected_size,
        'actual_bytes'         : actual_size,
        'size_match'           : size_match,
        'checksum_md5'         : checksum_md5,
        'output_path'          : output_file_path,
        'output_size_bytes'    : output_size_bytes,
    }

    return output_file_path, metadata, stats
