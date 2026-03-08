import os
import sys
import json

from pipeline import encode_and_generate_video
from decoder  import decode
from logger   import log

PARAMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'parameters.json')


def load_params():
    if not os.path.isfile(PARAMS_FILE):
        print(f"❌  parameters.json not found at: {PARAMS_FILE}")
        sys.exit(1)
    with open(PARAMS_FILE, 'r') as f:
        return json.load(f)


if __name__ == "__main__":
    params = load_params()

    action     = params.get('action', '').lower()
    file_path  = params.get('file_path', '')
    output_dir = params.get('output_dir', '')
    chunk_label= params.get('chunk_label', '4K')
    fps        = params.get('fps', 30)
    overlay    = params.get('overlay', True)
    compress   = params.get('compress', False)

    print("\nFramecast v0.1.1")
    print(f"Action  : {action}")
    print(f"Input   : {file_path}")
    print(f"Output  : {output_dir}\n")

    if action == 'encode':
        if not os.path.exists(file_path):
            print(f"❌  Path not found: {file_path}")
            sys.exit(1)
        _, stats = encode_and_generate_video(
            file_path   = file_path,
            output_dir  = output_dir,
            chunk_label = chunk_label,
            fps         = fps,
            overlay     = overlay,
            compress    = compress,
        )
        log('encode', stats)

    elif action == 'decode':
        if not os.path.exists(file_path):
            print(f"❌  Path not found: {file_path}")
            sys.exit(1)
        _, _, stats = decode(file_path, output_dir, overlay=overlay)
        log('decode', stats)

    else:
        print(f"❌  Unknown action '{action}'. Set action to 'encode' or 'decode' in parameters.json.")
        sys.exit(1)
