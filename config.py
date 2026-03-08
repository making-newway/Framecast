OVERLAY_HEIGHT_PX    = 38
ENCODING_MODE        = 'RGB'
MAX_PART_SIZE_BYTES  = 4 * 1024 * 1024 * 1024   # 4GB per part

FRAME_SIZES = {
    '4K'    : (3840, 2160),
    '2K'    : (2560, 1440),
    '1080p' : (1920, 1080),
    '720p'  : (1280,  720),
    '480p'  : ( 854,  480),
}

# RGB: 3 bytes per pixel, data rows only
CHUNK_SIZES = {
    label: w * (h - OVERLAY_HEIGHT_PX) * 3
    for label, (w, h) in FRAME_SIZES.items()
}

DEFAULT_CHUNK_LABEL  = '4K'
DEFAULT_FPS          = 30
