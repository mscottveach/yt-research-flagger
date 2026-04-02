"""
Main pipeline — reads pending videos from the queue and processes them.

Run manually or via Windows Task Scheduler:
    python pipeline/pipeline.py

Options:
    --all       Re-process failed entries too
    --dry-run   Show what would be processed without doing it
"""

import json
import sys
import argparse
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.config import QUEUE_FILE, OBSIDIAN_VAULT_PATH, OBSIDIAN_FOLDER
from pipeline.transcript import get_transcript
from pipeline.metadata import get_metadata
from pipeline.summarizer import summarize
from pipeline.note_writer import write_note, write_index


def load_queue() -> list[dict]:
    if not QUEUE_FILE.exists():
        return []
    entries = []
    with open(QUEUE_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def save_queue(entries: list[dict]):
    with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')


def process_video(entry: dict) -> dict:
    video_id = entry['video_id']
    title = entry.get('title', '')
    print(f'\n[{video_id}] {title or "(no title yet)"}')

    # 1. Fetch metadata (title, channel, thumbnail, duration)
    print('  Fetching metadata...')
    meta = get_metadata(video_id)
    if title and not meta.get('title'):
        meta['title'] = title  # Use title from extension as fallback

    # 2. Get transcript
    print('  Fetching transcript...')
    transcript, transcript_method = get_transcript(video_id)
    print(f'  Transcript: {len(transcript)} chars via {transcript_method}')

    # 3. Summarize
    print('  Summarizing with Gemini...')
    summary = summarize(transcript, title=meta.get('title', ''))
    print(f'  Summary: {len(summary)} chars')

    # 4. Write Obsidian note
    print('  Writing Obsidian note...')
    note_path = write_note(
        meta=meta,
        summary=summary,
        transcript_method=transcript_method,
        flagged_at=entry.get('flagged_at', ''),
    )
    print(f'  Note written: {note_path}')

    return {'note_path': str(note_path), 'title': meta.get('title', '')}


def main():
    parser = argparse.ArgumentParser(description='Process queued YouTube videos')
    parser.add_argument('--all', action='store_true', help='Re-process failed entries')
    parser.add_argument('--dry-run', action='store_true', help='Show queue without processing')
    args = parser.parse_args()

    entries = load_queue()
    if not entries:
        print('Queue is empty. Flag some videos first.')
        return

    pending = [e for e in entries if e.get('status') == 'pending']
    if args.all:
        pending += [e for e in entries if e.get('status') == 'failed']

    if not pending:
        print(f'No pending videos. Total in queue: {len(entries)}')
        return

    print(f'Found {len(pending)} video(s) to process:')
    for e in pending:
        print(f"  - {e['video_id']}: {e.get('title', '(unknown)')}")

    if args.dry_run:
        return

    processed_count = 0
    failed_count = 0

    for entry in pending:
        # Find and update this entry in the full list
        idx = next(i for i, e in enumerate(entries) if e['video_id'] == entry['video_id'])

        try:
            result = process_video(entry)
            entries[idx]['status'] = 'done'
            entries[idx]['processed_at'] = datetime.now().isoformat()
            entries[idx]['note_path'] = result['note_path']
            if result.get('title'):
                entries[idx]['title'] = result['title']
            processed_count += 1
        except Exception as e:
            print(f'\n  ERROR processing {entry["video_id"]}:')
            traceback.print_exc()
            entries[idx]['status'] = 'failed'
            entries[idx]['error'] = str(e)
            entries[idx]['failed_at'] = datetime.now().isoformat()
            failed_count += 1

        # Save after each video so partial progress is not lost
        save_queue(entries)

    print(f'\nDone. Processed: {processed_count}, Failed: {failed_count}')

    # Always regenerate the index so it reflects current state
    print('Updating index...')
    index_path = write_index(OBSIDIAN_VAULT_PATH / OBSIDIAN_FOLDER)
    print(f'Index written: {index_path}')


if __name__ == '__main__':
    main()
