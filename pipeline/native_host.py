"""
Native Messaging Host for YT Research Flagger.
The browser launches this script automatically when the extension calls
chrome.runtime.sendNativeMessage(). It reads one JSON message from stdin,
appends to the queue file, writes an ack to stdout, then exits.

Do NOT run this manually — it is launched by Edge.
"""

import sys
import json
import struct
import os
from pathlib import Path
from datetime import datetime


def read_message() -> dict:
    """Read one native messaging message from stdin (4-byte LE length prefix + JSON)."""
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) < 4:
        sys.exit(0)
    message_length = struct.unpack('<I', raw_length)[0]
    raw_message = sys.stdin.buffer.read(message_length)
    return json.loads(raw_message.decode('utf-8'))


def write_message(payload: dict):
    """Write one native messaging message to stdout."""
    encoded = json.dumps(payload).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('<I', len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def get_queue_file() -> Path:
    # Queue file lives next to this script's project root
    project_root = Path(__file__).parent.parent
    queue_file = project_root / 'data' / 'queue.jsonl'
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    return queue_file


def load_pending_ids(queue_file: Path) -> set:
    if not queue_file.exists():
        return set()
    pending = set()
    with open(queue_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    if entry.get('status') == 'pending':
                        pending.add(entry['video_id'])
                except (json.JSONDecodeError, KeyError):
                    pass
    return pending


def main():
    # Redirect stderr to a log file so errors don't corrupt the stdout protocol
    log_path = Path(__file__).parent.parent / 'data' / 'native_host.log'
    log_path.parent.mkdir(parents=True, exist_ok=True)
    sys.stderr = open(log_path, 'a', encoding='utf-8')

    try:
        message = read_message()
    except Exception as e:
        write_message({'status': 'error', 'error': f'Failed to read message: {e}'})
        sys.exit(1)

    video_id = message.get('video_id')
    if not video_id:
        write_message({'status': 'error', 'error': 'video_id is required'})
        sys.exit(1)

    queue_file = get_queue_file()

    # Don't double-queue
    if video_id in load_pending_ids(queue_file):
        write_message({'status': 'already_queued', 'video_id': video_id})
        sys.exit(0)

    entry = {
        'video_id': video_id,
        'url': message.get('url', f'https://www.youtube.com/watch?v={video_id}'),
        'title': message.get('title', ''),
        'flagged_at': message.get('flagged_at', datetime.now().isoformat()),
        'status': 'pending',
    }

    try:
        with open(queue_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        write_message({'status': 'error', 'error': f'Failed to write queue: {e}'})
        sys.exit(1)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Queued: {entry['title'] or video_id}",
          file=sys.stderr)
    write_message({'status': 'queued', 'video_id': video_id})


if __name__ == '__main__':
    main()
