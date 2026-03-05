import os
import json
import mimetypes


def _build_metadata(file_path, chunk_size):
    file_name = os.path.basename(file_path)
    file_type, _ = mimetypes.guess_type(file_path)
    return {
        "filename"      : file_name,
        "extension"     : os.path.splitext(file_name)[1],
        "mime_type"     : file_type or "application/octet-stream",
        "filesize_bytes": os.path.getsize(file_path),
        "chunk_size"    : chunk_size,
    }


def _metadata_to_header(metadata):
    meta_bytes  = json.dumps(metadata).encode('utf-8')
    meta_length = len(meta_bytes).to_bytes(4, byteorder='big')
    header_bits = ''.join(format(b, '08b') for b in meta_length + meta_bytes)
    return header_bits, meta_bytes


def encode_chunks(file_path, chunk_size):
    with open(file_path, 'rb') as f:
        idx = 0
        while chunk_bytes := f.read(chunk_size):
            yield idx, chunk_bytes, ''.join(format(b, '08b') for b in chunk_bytes)
            idx += 1


def get_metadata_and_header(file_path, chunk_size):
    metadata        = _build_metadata(file_path, chunk_size)
    header_bits, _  = _metadata_to_header(metadata)
    return metadata, header_bits


def file_to_binary_stream(file_path, chunk_size):
    _, header_bits = get_metadata_and_header(file_path, chunk_size)
    chunk_bits = ''.join(bs for _, _, bs in encode_chunks(file_path, chunk_size))
    return header_bits + chunk_bits
