OVERLAY_HEIGHT_PX   = 38

FRAME_SIZES = {
    '4K'    : (3840, 2160),
    '2K'    : (2560, 1440),
    '1080p' : (1920, 1080),
    '720p'  : (1280,  720),
    '480p'  : ( 854,  480),
}

CHUNK_SIZES = {
    label: w * (h - OVERLAY_HEIGHT_PX) // 8
    for label, (w, h) in FRAME_SIZES.items()
}

DEFAULT_CHUNK_LABEL = '720p'
DEFAULT_FPS         = 30