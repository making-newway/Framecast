import cv2
import json
import numpy as np

from config import FRAME_SIZES, DEFAULT_FPS, OVERLAY_HEIGHT_PX


def _bytes_to_rgb_frame(chunk_bytes, width, height):
    data_rows   = height - OVERLAY_HEIGHT_PX
    capacity    = width * data_rows * 3
    padded      = chunk_bytes + b'\x00' * max(0, capacity - len(chunk_bytes))
    arr         = np.frombuffer(padded[:capacity], dtype=np.uint8)
    data_region = arr.reshape((data_rows, width, 3))
    frame       = np.zeros((height, width, 3), dtype=np.uint8)
    frame[OVERLAY_HEIGHT_PX:] = data_region
    return frame


def _metadata_to_frame(metadata, width, height):
    meta_bytes  = json.dumps(metadata).encode('utf-8')
    meta_length = len(meta_bytes).to_bytes(4, byteorder='big')
    all_bytes   = meta_length + meta_bytes

    bits = []
    for byte in all_bytes:
        for b in range(7, -1, -1):
            bits.append((byte >> b) & 1)

    data_rows   = height - OVERLAY_HEIGHT_PX
    data_pixels = width * data_rows
    padded_bits = bits[:data_pixels] + [0] * max(0, data_pixels - len(bits))

    val         = np.array(padded_bits, dtype=np.uint8) * 255
    data_region = np.stack([val, val, val], axis=-1).reshape((data_rows, width, 3))
    frame       = np.zeros((height, width, 3), dtype=np.uint8)
    frame[OVERLAY_HEIGHT_PX:] = data_region

    cv2.putText(frame, f"METADATA FRAME  |  {len(meta_bytes)} bytes JSON",
                (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return frame


def open_writer(output_path, chunk_label, fps=DEFAULT_FPS):
    if chunk_label not in FRAME_SIZES:
        raise ValueError(f"Unknown chunk_label '{chunk_label}'. Choose from: {list(FRAME_SIZES)}")

    width, height   = FRAME_SIZES[chunk_label]
    lossless_codecs = ['FFV1', 'HFYU']
    writer          = None

    for codec in lossless_codecs:
        candidate = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*codec), fps, (width, height)) # type: ignore
        if candidate.isOpened():
            writer = candidate
            break
        candidate.release()

    if writer is None:
        raise IOError(f"Could not open lossless VideoWriter for: {output_path}. Tried: {lossless_codecs}")

    return writer, width, height


def write_metadata_frame(writer, metadata, width, height):
    writer.write(_metadata_to_frame(metadata, width, height))


def write_frame(writer, chunk_bytes, width, height, frame_idx=None, chunk_label=None, fps=None):
    frame = _bytes_to_rgb_frame(chunk_bytes, width, height)

    if frame_idx is not None:
        text = f"Frame {frame_idx:05d}"
        if chunk_label:
            text += f"  |  {chunk_label}"
        if fps:
            text += f"  |  {fps} fps"
        cv2.putText(frame, text, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

    writer.write(frame)
