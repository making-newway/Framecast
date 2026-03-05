import decoder
from pipeline import encode_and_generate_video
from config import CHUNK_SIZES, DEFAULT_FPS

FILE_PATH   = r"D:\Pokemon\pKHeX.zip"
OUTPUT_DIR  = r"E:\Visual\File2\data"
VIDEO_LOC   = r"E:\Visual\File2\data\pKHeX_720p_30fps.avi"
CHUNK_LABEL = '720p'
FPS         = 30
OVERLAY     = True

if __name__ == "__main__":
    choice = int(input(f"1. ▶  This will encode '{FILE_PATH}' into a video.\n2. ▶  Then decode it back to verify integrity.\n\nEnter your choice (1 or 2): "))
    if choice == 1:
        print("\n▶  Encoding and generating video...")
        binary_stream, video_path, enc = encode_and_generate_video(
            file_path   = FILE_PATH,
            output_path = OUTPUT_DIR,
            chunk_label = CHUNK_LABEL,
            fps         = FPS,
            overlay     = OVERLAY,
        )

        print(f"\n{'='*54}")
        print(f"  ✅  Encode done in {enc['total_time_s']}s")
        print(f"{'='*54}")
        print(f"  File       : {enc['filename']}")
        print(f"  MIME       : {enc['mime_type']}")
        print(f"  File size  : {enc['file_size_bytes']:,} bytes")
        print(f"  Chunk      : {CHUNK_LABEL} ({CHUNK_SIZES[CHUNK_LABEL]:,} bytes)")
        print(f"  Frames     : {enc['frame_count']} data  +  1 metadata  =  {enc['total_frames']} total")
        print(f"  Duration   : {enc['duration_s']}s @ {FPS}fps")
        print(f"  Resolution : {enc['resolution']}")
        print(f"  Video      : {video_path}")
        print(f"  Total bits : {enc['total_bits']:,}")
        print(f"{'='*54}\n")

    elif choice == 2:

        print("▶  Decoding from video...")
        print(f"[decoder] Reading from: {VIDEO_LOC}")
        output_path, metadata, dec = decoder.decode_from_video(
            video_path = VIDEO_LOC,
            output_dir = OUTPUT_DIR,
            overlay    = OVERLAY,
        )

        print(f"\n{'='*54}")
        print(f"  ✅  Decode done in {dec['total_time_s']}s")
        print(f"{'='*54}")
        print("\n  -- Timing --")
        print(f"  Frame read   : {dec['frame_read_time_s']}s")
        print(f"  Bit decode   : {dec['decode_time_s']}s")
        print(f"  Total        : {dec['total_time_s']}s")
        print("\n  -- Video --")
        print(f"  Resolution   : {dec['resolution']}  ({dec['chunk_label']})")
        print(f"  FPS          : {dec['video_fps']}")
        print(f"  Total frames : {dec['total_frames']}  (1 metadata + {dec['data_frames']} data)")
        print(f"  Video size   : {dec['video_size_bytes']:,} bytes")
        print("\n  -- Bits --")
        print(f"  Total bits   : {dec['total_bits_collected']:,}")
        print(f"  Padding bits : {dec['padding_bits']:,}")
        print(f"  Ones         : {dec['ones_count']:,}  ({dec['bit_density']*100:.1f}% density)")
        print(f"  Zeros        : {dec['zeros_count']:,}")
        print("\n  -- Per-frame density --")
        print(f"  Min          : {dec['min_frame_density']*100:.2f}%")
        print(f"  Max          : {dec['max_frame_density']*100:.2f}%")
        print(f"  Avg          : {dec['avg_frame_density']*100:.2f}%")
        print("\n  -- Integrity --")
        print(f"  Expected     : {dec['expected_bytes']:,} bytes")
        print(f"  Actual       : {dec['actual_bytes']:,} bytes")
        print(f"  Size match   : {'✅ Yes' if dec['size_match'] else '❌ No'}")
        print(f"  MD5          : {dec['checksum_md5']}")
        print(f"  Restored to  : {dec['output_path']}")
        print(f"{'='*54}\n")
