"""
Write an Obsidian markdown note for a processed video.
"""

import re
from datetime import datetime
from pathlib import Path

from pipeline.config import OBSIDIAN_VAULT_PATH, OBSIDIAN_FOLDER
from pipeline.metadata import format_duration


def write_note(meta: dict, summary: str, transcript_method: str, flagged_at: str = '') -> Path:
    """
    Write a markdown note to the Obsidian vault.
    Returns the path of the written file.
    """
    folder = OBSIDIAN_VAULT_PATH / OBSIDIAN_FOLDER
    folder.mkdir(parents=True, exist_ok=True)

    title = meta.get('title', meta['video_id'])
    safe_title = _safe_filename(title)
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f'{date_str} {safe_title}.md'
    note_path = folder / filename

    # If a file with this name already exists, add video_id suffix to avoid collision
    if note_path.exists():
        filename = f'{date_str} {safe_title} [{meta["video_id"]}].md'
        note_path = folder / filename

    upload_date = _format_upload_date(meta.get('upload_date', ''))
    duration = format_duration(meta.get('duration_seconds', 0))

    content = f"""---
title: "{_escape_yaml(title)}"
source: "{meta['url']}"
video_id: "{meta['video_id']}"
channel: "{_escape_yaml(meta.get('channel', ''))}"
published: {upload_date}
duration: {meta.get('duration_seconds', 0)}
thumbnail: "{meta.get('thumbnail', '')}"
tags:
  - youtube
  - video-note
flagged_at: {flagged_at or datetime.now().isoformat()}
processed_at: {datetime.now().isoformat()}
transcript_method: {transcript_method}
---

# {title}

![]({meta.get('thumbnail', '')})

> [Watch on YouTube]({meta['url']}) | {meta.get('channel', '')} | {duration}

---

{summary}

---

*Summarized by {_get_model()} on {date_str}*
"""

    note_path.write_text(content, encoding='utf-8')
    return note_path


def _safe_filename(title: str) -> str:
    # Remove characters that are invalid in Windows filenames
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', title)
    safe = safe.strip('. ')
    return safe[:80]  # Keep filenames reasonable length


def _escape_yaml(s: str) -> str:
    return s.replace('"', '\\"')


def _format_upload_date(date_str: str) -> str:
    # yt-dlp returns YYYYMMDD
    if len(date_str) == 8:
        return f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}'
    return date_str or 'unknown'


def _get_model() -> str:
    try:
        from pipeline.config import CLAUDE_MODEL
        return CLAUDE_MODEL
    except Exception:
        return 'claude'


# ---------------------------------------------------------------------------
# Index file
# ---------------------------------------------------------------------------

def write_index(folder: Path):
    """
    Regenerate _Index.md in the given folder.
    Shows all video notes newest-first with thumbnail, wikilink, and summary.
    """
    index_path = folder / '_Index.md'

    # Collect all video note files (skip the index itself)
    note_files = [p for p in sorted(folder.glob('*.md')) if p.name != '_Index.md']

    entries = []
    for path in note_files:
        entry = _parse_note(path)
        if entry:
            entries.append(entry)

    # Sort newest flagged_at first
    entries.sort(key=lambda e: e.get('flagged_at', ''), reverse=True)

    lines = ['# YouTube Video Index\n', f'*{len(entries)} videos · updated {datetime.now().strftime("%Y-%m-%d %H:%M")}*\n\n---\n']

    for e in entries:
        stem = Path(e['filename']).stem
        display = e.get('title') or stem
        wikilink = f'[[{stem}|{display}]]'

        channel = e.get('channel', '')
        duration = format_duration(e.get('duration_seconds', 0))
        flagged_date = (e.get('flagged_at') or '')[:10]  # YYYY-MM-DD

        meta_line = ' · '.join(filter(None, [channel, duration, f'flagged {flagged_date}' if flagged_date else '']))

        block = [f'## {wikilink}']
        if e.get('thumbnail'):
            block.append(f'![]({e["thumbnail"]})')
        if meta_line:
            block.append(f'*{meta_line}*')
        if e.get('summary'):
            block.append('')
            block.append(e['summary'])
        block.append('\n---\n')

        lines.append('\n'.join(block))

    index_path.write_text('\n'.join(lines), encoding='utf-8')
    return index_path


def _parse_note(path: Path) -> dict | None:
    """Parse frontmatter and Summary section from a video note file."""
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return None

    # Split on frontmatter delimiters
    parts = text.split('---\n', 2)
    if len(parts) < 3:
        return None

    fm_text = parts[1]
    body = parts[2]

    # Parse frontmatter key: value lines (handles quoted and unquoted values)
    fm: dict = {}
    for line in fm_text.splitlines():
        if ':' in line and not line.startswith(' '):
            key, _, val = line.partition(':')
            val = val.strip().strip('"')
            fm[key.strip()] = val

    # Extract the Summary section (between ## Summary and the next ##)
    summary = ''
    m = re.search(r'## Summary\s*\n(.*?)(?=\n##|\Z)', body, re.DOTALL)
    if m:
        summary = m.group(1).strip()

    return {
        'filename': path.name,
        'title': fm.get('title', ''),
        'channel': fm.get('channel', ''),
        'thumbnail': fm.get('thumbnail', ''),
        'flagged_at': fm.get('flagged_at', ''),
        'duration_seconds': int(fm.get('duration', 0) or 0),
        'summary': summary,
    }
