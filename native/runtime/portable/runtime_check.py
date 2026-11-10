"""Check the bundled runtime without launching Codex or touching a user profile."""
import sys
sys.dont_write_bytecode = True
import ctypes
import hashlib
import importlib.metadata
import json
import os
import runpy
from pathlib import Path
import socket
import ssl
import subprocess

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / 'runtime' / 'python'
for key in ('PLAYWRIGHT_NODEJS_PATH', 'NODE_OPTIONS', 'NODE_PATH'):
    os.environ.pop(key, None)

import greenlet
import pyee
import typing_extensions
import playwright
from playwright._impl._driver import compute_driver_executable
from playwright.sync_api import sync_playwright


def main():
    assert sys.maxsize > 2**32, 'An x64 runtime is required'
    assert sys.flags.isolated and sys.flags.ignore_environment, 'Python path isolation is missing'
    assert Path(sys.executable).resolve().is_relative_to(PYTHON), 'External Python executable'
    assert all(Path(p).resolve().is_relative_to(PYTHON) for p in sys.path), 'External Python search path'
    for module in (greenlet, pyee, typing_extensions, playwright):
        assert Path(module.__file__).resolve().is_relative_to(PYTHON), 'External dependency: ' + module.__name__
    driver, cli = compute_driver_executable()
    assert Path(driver).resolve().is_relative_to(PYTHON) and Path(cli).is_file(), 'External or missing driver'
    assert greenlet.greenlet(lambda: 42).switch() == 42
    assert hashlib.sha256(b'Codex EVA').digest()
    assert ctypes.sizeof(ctypes.c_void_p) == 8
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
    ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    loader = runpy.run_path(str(ROOT / 'loader.py'), run_name='runtime_check')
    assert loader['read'](ROOT / 'manifest.json', {}).get('version'), 'Loader cannot read its bundled configuration'
    # Starts the bundled Node driver over a pipe; no browser or download is needed.
    with sync_playwright() as pw:
        assert pw.chromium.name == 'chromium'
    node = subprocess.run([driver, '--version'], capture_output=True, text=True, check=True,
                          timeout=20, creationflags=0x08000000).stdout.strip()
    print(json.dumps({
        'passed': True,
        'python': sys.version.split()[0],
        'node': node,
        'dependencies': {name: importlib.metadata.version(name) for name in
                         ('playwright', 'greenlet', 'pyee', 'typing_extensions')},
        'isolated': True,
        'bundledDriverStarted': True,
        'codexLaunched': False,
        'networkDownload': False,
    }, ensure_ascii=True))


if __name__ == '__main__':
    main()
