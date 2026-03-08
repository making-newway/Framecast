import os
import math
import time
from tqdm import tqdm

from config          import CHUNK_SIZES, FRAME_SIZES, DEFAULT_CHUNK_LABEL, DEFAULT_FPS, MAX_PART_SIZE_BYTES
from encoder         import encode_chunks, get_metadata, folder_to_zip
from video_generator import open_writer, write_metadata_frame, write_frame
from manifest        import write_manifest, compute_md5


# ── Helpers ───────────────────────────────────────────────────────────────────

def _prepare_source(file_path):
    """Zip folder to temp file if needed. Returns (file_path, source_type, original_name, temp_zip)."""
    if os.path.isdir(file_path):
        original_name = os.path.basename(file_path.rstrip('/\\'))
        temp_zip, _   = folder_to_zip(file_path)
        return temp_zip, 'folder', original_name, temp_zip
    return file_path, 'file', os.path.splitext(os.path.basename(file_path))[0], None


def _open_part(out_dir, base_name, chunk_label, fps, part_num, metadata, width, height):
    """Open a new VideoWriter for the next part and write its metadata frame."""
    part_path        = os.path.join(out_dir, f"{base_name}_{chunk_label}_{fps}fps_part{part_num:03d}.avi")
    writer, w, h     = open_writer(part_path, chunk_label, fps)
    write_metadata_frame(writer, metadata, w, h)
    return writer, part_path


def _close_part(writer, part_path, frames, b_start, b_end, parts_info):
    """Release writer and record part metadata."""
    writer.release()
    parts_info.append({
        "part"        : len(parts_info) + 1,
        "file"        : os.path.basename(part_path),
        "frames"      : frames,
        "byte_offset" : b_start,
        "byte_length" : b_end - b_start,
        "md5"         : compute_md5(part_path),
    })


def _overlay_args(overlay, chunk_idx, chunk_label, fps):
    """Return frame overlay kwargs or empty dict."""
    if not overlay:
        return {'frame_idx': None, 'chunk_label': None, 'fps': None}
    return {'frame_idx': chunk_idx, 'chunk_label': chunk_label, 'fps': fps}


def _cleanup_temp(temp_zip):
    if temp_zip and os.path.exists(temp_zip):
        os.remove(temp_zip)
        print("  🗑   Temp zip removed.")


# ── Main encode function ──────────────────────────────────────────────────────

def encode_and_generate_video(file_path, output_dir=None, chunk_label=DEFAULT_CHUNK_LABEL,
                               fps=DEFAULT_FPS, overlay=True, compress=False):

    file_path, source_type, original_name, temp_zip = _prepare_source(file_path)

    chunk_size    = CHUNK_SIZES[chunk_label]
    width, height = FRAME_SIZES[chunk_label]
    out_dir       = output_dir or os.path.dirname(file_path)
    os.makedirs(out_dir, exist_ok=True)

    metadata = get_metadata(
        file_path,
        chunk_size,
        compressed    = compress,
        source_type   = source_type,
        original_name = original_name,
    )

    base_name        = original_name if source_type == 'folder' \
                       else os.path.splitext(os.path.basename(file_path))[0]
    total_chunks     = math.ceil(metadata['filesize_bytes'] / chunk_size)
    frames_per_part  = max(1, math.floor(MAX_PART_SIZE_BYTES / chunk_size))
    total_parts      = math.ceil(total_chunks / frames_per_part)

    parts_info       = []
    part_num         = 1
    frame_count      = 0
    byte_offset      = 0
    part_frame_count = 0
    part_byte_start  = 0
    start            = time.perf_counter()

    writer, part_path = _open_part(out_dir, base_name, chunk_label, fps, part_num, metadata, width, height)

    with tqdm(total=total_chunks, desc='Encoding', unit='frame', colour='green') as pbar:
        for chunk_idx, chunk_bytes in encode_chunks(file_path, chunk_size, compress=compress):

            if part_frame_count > 0 and part_frame_count % frames_per_part == 0:
                _close_part(writer, part_path, part_frame_count, part_byte_start, byte_offset, parts_info)
                part_num        += 1
                part_byte_start  = byte_offset
                part_frame_count = 0
                writer, part_path = _open_part(out_dir, base_name, chunk_label, fps, part_num, metadata, width, height)

            write_frame(writer, chunk_bytes, width, height, **_overlay_args(overlay, chunk_idx, chunk_label, fps))

            part_frame_count += 1
            frame_count      += 1
            byte_offset      += len(chunk_bytes)
            pbar.update(1)

    _close_part(writer, part_path, part_frame_count, part_byte_start, byte_offset, parts_info)

    manifest_path = write_manifest(
        output_dir    = out_dir,
        filename      = metadata['filename'],
        filesize      = metadata['filesize_bytes'],
        mime_type     = metadata['mime_type'],
        compressed    = compress,
        chunk_label   = chunk_label,
        fps           = fps,
        encoding      = metadata['encoding'],
        parts_info    = parts_info,
        source_type   = source_type,
        original_name = metadata['original_name'],
    )

    _cleanup_temp(temp_zip)

    stats = {
        'filename'       : metadata['filename'],
        'mime_type'      : metadata['mime_type'],
        'file_size_bytes': metadata['filesize_bytes'],
        'source_type'    : source_type,
        'original_name'  : metadata['original_name'],
        'chunk_label'    : chunk_label,
        'chunk_size'     : chunk_size,
        'total_frames'   : frame_count,
        'total_parts'    : total_parts,
        'resolution'     : f"{width}x{height}",
        'fps'            : fps,
        'duration_s'     : round(frame_count / fps, 2),
        'total_time_s'   : round(time.perf_counter() - start, 4),
        'compressed'     : compress,
        'output_dir'     : out_dir,
        'manifest_path'  : manifest_path,
        'parts'          : parts_info,
    }

    return manifest_path, stats