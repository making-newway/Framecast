import os
import json
import mimetypes
import zipfile
import tempfile

from config import CHUNK_SIZES, DEFAULT_CHUNK_LABEL


def _build_metadata(file_path, chunk_size, compressed=False,
                    source_type='file', original_name=None):
    file_name = os.path.basename(file_path)
    file_type, _ = mimetypes.guess_type(file_path)
    return {
        "filename"      : file_name,
        "extension"     : os.path.splitext(file_name)[1],
        "mime_type"     : file_type or "application/octet-stream",
        "filesize_bytes": os.path.getsize(file_path),
        "chunk_size"    : chunk_size,
        "compressed"    : compressed,
        "encoding"      : "RGB",
        "source_type"   : source_type,
        "original_name" : original_name or file_name,
    }



def folder_to_zip(folder_path):
    """Zip a folder (ZIP_STORED — no compression) to a temp file. Returns temp path."""
    folder_name = os.path.basename(folder_path.rstrip('/\\'))
    tmp_path    = os.path.join(tempfile.gettempdir(), f"{folder_name}.zip")
    print(f"  📁  Zipping folder → {tmp_path}")
    with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_STORED) as zf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                full    = os.path.join(root, file)
                arcname = os.path.relpath(full, os.path.dirname(folder_path.rstrip('/\\')))
                zf.write(full, arcname)
    size = os.path.getsize(tmp_path)
    print(f"  ✅  Zipped: {size:,} bytes")
    return tmp_path, folder_name


def get_metadata(file_path, chunk_size, compressed=False,
                 source_type='file', original_name=None):
    return _build_metadata(file_path, chunk_size, compressed, source_type, original_name)


def encode_chunks(file_path, chunk_size, compress=False):
    if compress:
        try:
            import zstandard as zstd
        except ImportError:
            raise ImportError("zstandard not installed. Run: pip install zstandard")

        cctx = zstd.ZstdCompressor(level=3)
        with open(file_path, 'rb') as f:
            data = cctx.compress(f.read())

        idx = 0
        offset = 0
        while offset < len(data):
            chunk = data[offset:offset + chunk_size]
            yield idx, chunk
            offset += chunk_size
            idx += 1
    else:
        with open(file_path, 'rb') as f:
            idx = 0
            while chunk_bytes := f.read(chunk_size):
                yield idx, chunk_bytes
                idx += 1
