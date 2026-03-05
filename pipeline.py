import math
import os
import time
from tqdm import tqdm
from config import CHUNK_SIZES, DEFAULT_CHUNK_LABEL, DEFAULT_FPS
from encoder import encode_chunks, get_metadata_and_header
from video_generator import open_writer, write_metadata_frame, write_frame


def encode_and_generate_video(file_path, output_path, chunk_label=DEFAULT_CHUNK_LABEL, fps=DEFAULT_FPS, video_path=None, overlay=True):
    chunk_size = CHUNK_SIZES[chunk_label]

    if video_path is None:
        base = os.path.splitext(os.path.basename(file_path))[0]
        out_dir = output_path if output_path else os.path.dirname(file_path)
        os.makedirs(out_dir, exist_ok=True)
        video_path = os.path.join(out_dir, f"{base}_{chunk_label}_{fps}fps.avi")
    else:
        video_path = os.path.splitext(video_path)[0] + '.avi'

    metadata, header_bits = get_metadata_and_header(file_path, chunk_size)
    writer, width, height = open_writer(video_path, chunk_label, fps)

    write_metadata_frame(writer, metadata, width, height)

    binary_parts = [header_bits]
    frame_count  = 0
    total_chunks = math.ceil(metadata['filesize_bytes'] / chunk_size)
    start        = time.perf_counter()

    with tqdm(total=total_chunks, desc='Encoding', unit='frame', colour='green') as pbar:
        for chunk_idx, chunk_bytes, binary_string in tqdm(encode_chunks(file_path, chunk_size), desc="Encoding chunks", unit="frame"):
            binary_parts.append(binary_string)
            write_frame(writer, chunk_bytes, width, height,
                        frame_idx   = chunk_idx   if overlay else None,
                        chunk_label = chunk_label if overlay else None,
                        fps         = fps         if overlay else None)
            frame_count += 1
            pbar.update(1)

    writer.release()

    stats = {
        'frame_count'    : frame_count,
        'total_frames'   : frame_count + 1,
        'duration_s'     : round(frame_count / fps, 2),
        'total_time_s'   : round(time.perf_counter() - start, 4),
        'resolution'     : f"{width}x{height}",
        'total_bits'     : len(''.join(binary_parts)),
        'file_size_bytes': metadata['filesize_bytes'],
        'mime_type'      : metadata['mime_type'],
        'filename'       : metadata['filename'],
        'video_path'     : video_path,
    }

    return ''.join(binary_parts), video_path, stats
