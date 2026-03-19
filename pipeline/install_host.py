"""
One-time setup: registers the Native Messaging host with Edge on Windows.

Usage:
    python pipeline/install_host.py <extension-id>

Example:
    python pipeline/install_host.py abcdefghijklmnopqrstuvwxyzabcdef

Find your extension ID at edge://extensions after loading the unpacked extension.
If you reload the extension and the ID changes, run this script again.
"""

import sys
import json
import winreg
import shutil
from pathlib import Path


HOST_NAME = 'com.ytresearch.flagger'
REGISTRY_KEY = rf'Software\Microsoft\Edge\NativeMessagingHosts\{HOST_NAME}'


def find_python() -> str:
    """Find the current Python executable."""
    return sys.executable


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print('ERROR: extension ID is required.')
        sys.exit(1)

    extension_id = sys.argv[1].strip()
    if len(extension_id) != 32 or not extension_id.isalpha():
        print(f'WARNING: "{extension_id}" does not look like a valid extension ID')
        print('Extension IDs are 32 lowercase letters. Double-check edge://extensions.')
        print('Continuing anyway...')

    project_root = Path(__file__).parent.parent.resolve()
    native_host_script = (project_root / 'pipeline' / 'native_host.py').resolve()
    bat_file = (project_root / 'pipeline' / 'run_native_host.bat').resolve()
    manifest_file = (project_root / 'pipeline' / 'native_host_manifest.json').resolve()

    python_exe = find_python()
    print(f'Python: {python_exe}')
    print(f'Script: {native_host_script}')

    # 1. Write the .bat launcher (Windows needs an executable, not a .py file)
    bat_content = f'@echo off\n"{python_exe}" "{native_host_script}" %*\n'
    bat_file.write_text(bat_content, encoding='utf-8')
    print(f'Created: {bat_file}')

    # 2. Write the native messaging host manifest
    manifest = {
        'name': HOST_NAME,
        'description': 'YT Research Flagger native host',
        'path': str(bat_file),
        'type': 'stdio',
        'allowed_origins': [
            f'chrome-extension://{extension_id}/',
        ],
    }
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Created: {manifest_file}')

    # 3. Write the Windows registry key
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY)
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, str(manifest_file))
        winreg.CloseKey(key)
        print(f'Registry key written: HKCU\\{REGISTRY_KEY}')
    except OSError as e:
        print(f'ERROR writing registry: {e}')
        sys.exit(1)

    print()
    print('Setup complete! You can now flag videos without running a server.')
    print()
    print('If you ever reload the extension and the ID changes, run:')
    print(f'  python pipeline/install_host.py <new-extension-id>')


if __name__ == '__main__':
    main()
