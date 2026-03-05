file_size  = 27_139_985
chunk_size = 1280 * 720        # full frame
data_rows  = 720 - 38          # rows available per frame  
bits_per_frame = 1280 * data_rows
bytes_per_frame = bits_per_frame // 8

import math
frames_needed = math.ceil(file_size / bytes_per_frame)
print(f"Bytes per frame : {bytes_per_frame:,}")
print(f"Frames needed   : {frames_needed}")