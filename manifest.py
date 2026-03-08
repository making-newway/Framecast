import json
import hashlib
import os


def compute_md5(file_path, chunk_size=8 * 1024 * 1024):
    h = hashlib.md5()
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(output_dir, filename, filesize, mime_type, compressed,
                   chunk_label, fps, encoding, parts_info,
                   source_type='file', original_name=None):
    manifest = {
        "filename"      : filename,
        "filesize"      : filesize,
        "mime_type"     : mime_type,
        "compressed"    : compressed,
        "chunk_label"   : chunk_label,
        "fps"           : fps,
        "encoding"      : encoding,
        "source_type"   : source_type,
        "original_name" : original_name or filename,
        "total_parts"   : len(parts_info),
        "parts"         : parts_info,
    }
    # Use original_name as base for manifest filename
    base     = os.path.splitext(original_name or filename)[0]
    path     = os.path.join(output_dir, f"{base}_manifest.json")
    with open(path, 'w') as f:
        json.dump(manifest, f, indent=2)
    return path


def read_manifest(manifest_path):
    with open(manifest_path, 'r') as f:
        return json.load(f)


def verify_part(part_path, expected_md5):
    actual = compute_md5(part_path)
    return actual == expected_md5, actual
