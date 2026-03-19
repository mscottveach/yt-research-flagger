"""
Centralized cookie and auth management for yt-dlp YouTube requests.

Uses Firefox cookies (Firefox doesn't have Edge's app-bound encryption issue)
and includes --remote-components for JS challenge solving via Deno.
"""

from pipeline.config import COOKIE_FILE, COOKIE_SOURCE_BROWSER


def get_ytdlp_auth_args() -> list[str]:
    """Return yt-dlp CLI args for cookie auth and JS challenge solving."""
    args = ['--remote-components', 'ejs:github']

    if COOKIE_FILE.exists():
        args += ['--cookies', str(COOKIE_FILE)]
    else:
        args += ['--cookies-from-browser', COOKIE_SOURCE_BROWSER]

    return args
