# YT Research Flagger

Flag YouTube videos while browsing → get AI-summarized Obsidian notes automatically.

## How it works

```
YouTube page → Alt+S
                  └─► background.js
                          └─► chrome.runtime.sendNativeMessage()
                                  └─► native_host.py  (launched by Edge, no server needed)
                                          └─► data/queue.jsonl

Later:  python pipeline/pipeline.py
                  └─► transcript → Claude → Obsidian note
```

## Setup

### 1. Python dependencies

```bash
cd yt_summary
pip install -r requirements.txt
```

### 2. Configuration

```bash
cp .env.example .env
```

Edit `.env`:
- `ANTHROPIC_API_KEY` — get from console.anthropic.com
- `OBSIDIAN_VAULT_PATH` — full path to your vault, e.g. `C:/Users/Owner/Documents/Obsidian/Main`

### 3. Load the extension in Edge

1. Open `edge://extensions`
2. Enable **Developer mode** (toggle, top right)
3. Click **Load unpacked** → select the `extension/` folder
4. Note the **Extension ID** shown under the extension name (32-letter string)

### 4. Register the native messaging host (one-time)

```bash
python pipeline/install_host.py <your-extension-id>
```

Example:
```bash
python pipeline/install_host.py abcdefghijklmnopqrstuvwxyzabcdef
```

This writes a registry key so Edge knows how to launch `native_host.py` when you flag a video. **No server to keep running.**

> If you ever click "Reload" on the extension in `edge://extensions` and the ID changes, just re-run this command with the new ID.

## Usage

### Flagging videos

- **Keyboard**: Press `Alt+S` on any YouTube watch page
- **Button**: Click the "🔖 Flag" button in the video action row
- A blue toast confirms the video was flagged

### Processing the queue

```bash
python pipeline/pipeline.py
```

This fetches transcripts, summarizes with Claude, and writes notes to:
`<OBSIDIAN_VAULT_PATH>/YouTube Research/YYYY-MM-DD Title.md`

Options:
- `--dry-run` — show what would be processed without doing it
- `--all` — also re-process failed videos

### Schedule with Task Scheduler (optional)

Run the pipeline automatically every evening:

1. Open **Task Scheduler** → Create Basic Task
2. Trigger: Daily at e.g. 9 PM
3. Action: Start a program
   - Program: `python`
   - Arguments: `pipeline\pipeline.py`
   - Start in: `C:\path\to\yt_summary`

## Obsidian note structure

Notes land in `<vault>/YouTube Research/` as:

```markdown
---
title: "Video Title"
source: "https://youtube.com/watch?v=..."
video_id: "..."
channel: "Channel Name"
thumbnail: "https://..."
tags: [youtube, video-note]
flagged_at: 2026-03-17T14:32:00
---

# Video Title

![thumbnail](...)

> Watch on YouTube | Channel | 12:34

## Summary
...

## Key Points
- ...
```

## Troubleshooting

**"Run: python pipeline/install_host.py ..."** toast — you haven't run the install script yet, or the extension was reloaded and got a new ID.

**Transcript fails** — install Whisper for fallback: `pip install openai-whisper`

**Note not appearing in Obsidian** — check `OBSIDIAN_VAULT_PATH` in `.env` points to your vault root.

**Alt+S conflicts with another shortcut** — change it at `edge://extensions/shortcuts`.
