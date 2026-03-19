"""
Fetch transcript for a YouTube video.
Stage 1: yt-dlp subtitle extraction (fast, VPN-safe with cookies)
Stage 2: yt-dlp + OpenAI Whisper (fallback, ~1-5 min)
"""

import subprocess
import tempfile
import os
import re
from pathlib import Path
from pipeline.config import YTDLP_BIN
from pipeline.cookies import get_ytdlp_auth_args


def get_transcript(video_id: str) -> tuple[str, str]:
    """
    Returns (transcript_text, method) where method is
    'ytdlp_subs' or 'whisper'.
    Raises RuntimeError if both methods fail.
    """
    try:
        return _from_ytdlp_subs(video_id), 'ytdlp_subs'
    except Exception as e:
        print(f'  yt-dlp subtitles failed ({e}), trying Whisper fallback...')

    try:
        return _from_whisper(video_id), 'whisper'
    except Exception as e:
        raise RuntimeError(f'All transcript methods failed for {video_id}: {e}')


def _from_ytdlp_subs(video_id: str) -> str:
    """Extract subtitles via yt-dlp using exported cookies to bypass VPN blocks."""
    url = f'https://www.youtube.com/watch?v={video_id}'

    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [
                YTDLP_BIN,
                *get_ytdlp_auth_args(),
                '--write-subs',
                '--write-auto-subs',
                '--sub-langs', 'en.*',
                '--sub-format', 'vtt',
                '--skip-download',
                '--no-playlist',
                '--output', os.path.join(tmpdir, '%(id)s'),
                url,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f'yt-dlp subs failed: {result.stderr[:500]}')

        # Find the downloaded subtitle file
        sub_files = list(Path(tmpdir).glob('*.vtt'))
        if not sub_files:
            raise RuntimeError('No subtitle file found')

        vtt_text = sub_files[0].read_text(encoding='utf-8')
        return _parse_vtt(vtt_text)


def _parse_vtt(vtt: str) -> str:
    """Strip VTT timestamps and formatting, return plain text."""
    lines = []
    seen = set()
    for line in vtt.splitlines():
        # Skip headers, timestamps, and blank lines
        if not line.strip():
            continue
        if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
            continue
        if '-->' in line:
            continue
        # Strip HTML tags
        clean = re.sub(r'<[^>]+>', '', line).strip()
        if clean and clean not in seen:
            seen.add(clean)
            lines.append(clean)
    return ' '.join(lines)


def _from_whisper(video_id: str) -> str:
    from pipeline.config import WHISPER_MODEL
    import whisper

    url = f'https://www.youtube.com/watch?v={video_id}'

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, 'audio.mp3')

        # Download audio only
        result = subprocess.run(
            [
                YTDLP_BIN,
                *get_ytdlp_auth_args(),
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '5',   # 128kbps-ish, plenty for speech
                '--output', audio_path,
                '--no-playlist',
                url,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f'yt-dlp failed: {result.stderr[:500]}')

        # Transcribe
        model = whisper.load_model(WHISPER_MODEL)
        result = model.transcribe(audio_path, language='en', fp16=False)
        return result['text'].strip()
