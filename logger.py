import os
import datetime

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'framecast.log')
SEP      = '=' * 58


def _format_parts(parts):
    lines = [f"  {'parts':<16}: "]
    for p in parts:
        lines.append(
            f"    [{p['part']:03d}]  {p['file']}"
            f"  ({p['byte_length']:,} bytes"
            f"  |  {p['frames']} frames"
            f"  |  MD5: {p['md5'][:12]}...)"
        )
    return lines


def _format_part_results(part_results):
    lines = [f"  {'part_results':<16}: "]
    for p in part_results:
        icon = '✅' if p['status'] == 'OK' else '❌'
        lines.append(f"    {icon}  Part {p['part']:03d}  {p['status']}")
    return lines


def _format_stat(key, value):
    if key == 'parts' and isinstance(value, list):
        return _format_parts(value)
    if key == 'part_results' and isinstance(value, list):
        return _format_part_results(value)
    return [f"  {key:<16}: {value}"]


def log(action, stats):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines     = [f"\n{SEP}", f"[{timestamp}]  {action.upper()}", SEP]

    for key, value in stats.items():
        lines.extend(_format_stat(key, value))

    lines.append(SEP)
    entry = '\n'.join(lines) + '\n'

    print(entry)

    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(entry)
