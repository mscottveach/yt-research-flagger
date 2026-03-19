"""
Fetch YouTube video metadata using yt-dlp (no API key required).
Returns a dict with title, channel, thumbnail, duration, upload_date, view_count.
"""

import subprocess
import json
from pipeline.config import YTDLP_BIN
from pipeline.cookies import get_ytdlp_auth_args


def get_metadata(video_id: str) -> dict:
    url = f'https://www.youtube.com/watch?v={video_id}'

    result = subprocess.run(
        [
            YTDLP_BIN,
            *get_ytdlp_auth_args(),
            '--dump-json',
            '--no-download',
            '--no-playlist',
            url,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        raise RuntimeError(f'yt-dlp metadata failed: {result.stderr[:500]}')

    data = json.loads(result.stdout)

    # Pick the best thumbnail — prefer maxresdefault
    thumbnail = ''
    thumbnails = data.get('thumbnails', [])
    if thumbnails:
        # yt-dlp orders by preference; last entry is usually highest quality
        thumbnail = thumbnails[-1].get('url', '')
    if not thumbnail:
        thumbnail = f'https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg'

    return {
        'title': data.get('title', ''),
        'channel': data.get('uploader', data.get('channel', '')),
        'thumbnail': thumbnail,
        'duration_seconds': data.get('duration', 0),
        'upload_date': data.get('upload_date', ''),   # YYYYMMDD string
        'view_count': data.get('view_count', 0),
        'url': f'https://www.youtube.com/watch?v={video_id}',
        'video_id': video_id,
    }


def format_duration(seconds: int) -> str:
    if not seconds:
        return '?'
    h, remainder = divmod(int(seconds), 3600)
    m, s = divmod(remainder, 60)
    if h:
        return f'{h}:{m:02d}:{s:02d}'
    return f'{m}:{s:02d}'
