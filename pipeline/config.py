import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_root = Path(__file__).parent.parent
load_dotenv(_root / '.env')

GEMINI_API_KEY: str = os.environ['GEMINI_API_KEY']
OBSIDIAN_VAULT_PATH: Path = Path(os.environ['OBSIDIAN_VAULT_PATH'])
OBSIDIAN_FOLDER: str = os.getenv('OBSIDIAN_FOLDER', '03-resources/ytv')

FLASK_PORT: int = int(os.getenv('FLASK_PORT', '5123'))

QUEUE_FILE: Path = _root / os.getenv('QUEUE_FILE', 'data/queue.jsonl')
PROCESSED_FILE: Path = _root / 'data/processed.jsonl'

WHISPER_MODEL: str = os.getenv('WHISPER_MODEL', 'base')
COOKIE_FILE: Path = _root / os.getenv('COOKIE_FILE', 'data/cookies.txt')
COOKIE_SOURCE_BROWSER: str = os.getenv('COOKIE_SOURCE_BROWSER', 'firefox')
GEMINI_MODEL: str = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')

# Use the venv's yt-dlp, not whatever is on system PATH (e.g. Anaconda's old version)
import shutil as _shutil, sys as _sys
_venv_ytdlp = Path(_sys.executable).parent / 'yt-dlp.exe'
YTDLP_BIN: str = str(_venv_ytdlp) if _venv_ytdlp.exists() else (_shutil.which('yt-dlp') or 'yt-dlp')

# Ensure Deno is in PATH for yt-dlp JS challenge solving
_deno_dir = Path.home() / '.deno' / 'bin'
if _deno_dir.exists() and str(_deno_dir) not in os.environ.get('PATH', ''):
    os.environ['PATH'] = os.environ.get('PATH', '') + os.pathsep + str(_deno_dir)

# Ensure data dir exists
QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
