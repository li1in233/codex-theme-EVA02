from project_paths import ASSET_ROOT, MEDIA_ROOT, CACHE_ROOT, TEMP_ROOT, RELEASE_ROOT
"""Build a directory installer with an isolated runtime; never activate native Codex."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile

SOURCE = Path(__file__).resolve().parent
PROJECT = SOURCE.parents[1]
TEMPLATES = SOURCE / 'portable'
NAME = 'CodexEVA-v10.11-crosspc-win-x64'
VERSION = 'R7-S4-v10.11-crosspc'
BASE_FILES = ('python.exe', 'pythonw.exe', 'python3.dll', 'python312.dll',
              'vcruntime140.dll', 'vcruntime140_1.dll', 'LICENSE.txt')
EXCLUDED_STDLIB = {'site-packages', '__pycache__', 'test', 'tests', 'idlelib',
                   'tkinter', 'turtledemo', 'ensurepip', 'venv'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def files(root):
    return sorted(p for p in root.rglob('*') if p.is_file())


def copy_tree(source, destination):
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'tests', 'test'))


def build(build_root, release_root):
    assert os.name == 'nt' and sys.version_info[:2] == (3, 12) and sys.maxsize > 2**32
    build_root.mkdir(parents=True, exist_ok=True)
    release_root.mkdir(parents=True, exist_ok=True)
    for directory in (build_root, release_root):
        assert shutil.disk_usage(directory).free > 100 * 1024**3 + 1024**3, 'Keep 100 GiB free plus build space'
    work = build_root / ('crosspc-' + time.strftime('%Y%m%d-%H%M%S'))
    work.mkdir()
    package = work / NAME
    payload = package / 'payload'
    python = payload / 'runtime' / 'python'
    python.mkdir(parents=True)
    base = Path(sys.base_prefix)
    for name in BASE_FILES:
        shutil.copy2(base / name, python / name)
    dlls = python / 'DLLs'
    dlls.mkdir()
    # GUI, test, installer, SQLite and lzma modules are not used by this loader.
    omitted = {'_tkinter.pyd', 'tcl86t.dll', 'tk86t.dll', '_sqlite3.pyd', 'sqlite3.dll', '_msi.pyd', '_lzma.pyd'}
    for path in (base / 'DLLs').iterdir():
        if path.is_file() and path.suffix.lower() in {'.pyd', '.dll'} and path.name not in omitted and not path.name.startswith(('_test', '_ctypes_test')):
            shutil.copy2(path, dlls / path.name)
    stdlib_count = 0
    # Keep data beside the stdlib modules that use __file__ (including SSL).
    for root, dirs, names in os.walk(base / 'Lib'):
        dirs[:] = sorted(name for name in dirs if name not in EXCLUDED_STDLIB)
        for name in sorted(names):
            path = Path(root) / name
            if path.suffix not in {'.pyc', '.pyo'}:
                dest = python / 'Lib' / path.relative_to(base / 'Lib')
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
                stdlib_count += 1
    (python / 'python312._pth').write_text('DLLs\nLib\nLib/site-packages\n.\n', encoding='ascii')
    site = python / 'Lib' / 'site-packages'
    site.mkdir(parents=True, exist_ok=True)
    versions = {}
    for name in ('playwright', 'greenlet', 'pyee', 'typing_extensions'):
        distribution = importlib.metadata.distribution(name)
        versions[name] = distribution.version
        source = Path(distribution.locate_file(name))
        if name == 'typing_extensions':
            source = source.with_suffix('.py')
            shutil.copy2(source, site / source.name)
        else:
            copy_tree(source, site / source.name)
        metadata = Path(distribution._path)
        copy_tree(metadata, site / metadata.name)
    licenses = python / 'licenses'
    shutil.copytree(TEMPLATES / 'licenses', licenses)
    shutil.copy2(site / 'playwright' / 'driver' / 'LICENSE', licenses / 'OpenSSL-and-zlib-Node-notices.txt')
    current = json.loads((SOURCE / 'dist' / 'manifest.json').read_text(encoding='utf-8-sig'))
    for name, item in current['files'].items():
        path = SOURCE / 'dist' / name
        assert sha(path) == item['sha256'], 'Approved asset mismatch: ' + name
        shutil.copy2(path, payload / name)
    for name in ('manifest.json',):
        shutil.copy2(SOURCE / 'dist' / name, payload / name)
    shutil.copy2(SOURCE / 'loader.py', payload / 'loader.py')
    for name in ('Collect-Diagnostics.ps1', 'Collect-Diagnostics.cmd'):
        shutil.copy2(SOURCE / 'diagnostics' / name, payload / name)
    for name in ('runtime_check.py', 'THIRD-PARTY-NOTICES.txt'):
        shutil.copy2(TEMPLATES / name, payload / name)
    for name in ('Install.ps1', 'Install.cmd', 'Check.cmd', 'README.zh-CN.txt'):
        # Windows PowerShell 5 reads UTF-8 non-ASCII correctly with a BOM.
        text = (TEMPLATES / name).read_text(encoding='utf-8-sig')
        encoding = 'utf-8-sig' if name.endswith('.ps1') else 'utf-8'
        (package / name).write_text(text, encoding=encoding, newline='\r\n')
    (payload / '恢复原版.cmd').write_text('@echo off\nstart "" /b "%~dp0CodexEVA.exe" --restore\n', encoding='ascii', newline='\r\n')
    shutil.copy2(TEMPLATES / 'README.zh-CN.txt', payload / '使用说明.txt')
    assert sha(SOURCE/'Launcher.cs')==current['launcher']['sourceSha256'], 'Rebuild runtime after changing Launcher.cs'
    assert sha(SOURCE/'NativeVideo.cs')==current['launcher']['videoSourceSha256'], 'Rebuild runtime after changing NativeVideo.cs'
    assert sha(SOURCE/'dist/CodexEVA.exe')==current['launcher']['sha256'], 'Launcher build integrity failure'
    shutil.copy2(SOURCE/'dist/CodexEVA.exe',payload/'CodexEVA.exe')
    runtime = subprocess.run([str(python / 'python.exe'), '-B', str(payload / 'runtime_check.py')],
                             capture_output=True, text=True, timeout=40)
    if runtime.returncode:
        raise RuntimeError('Bundled runtime check failed:\n' + runtime.stdout + runtime.stderr)
    runtime_result = json.loads(runtime.stdout)
    entries = {p.relative_to(package).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in files(package)}
    assert not any(Path(name).name in {'state.json', 'installation.json', 'activation.json', 'failure.json', 'loader.log', 'window-placement.json'} for name in entries)
    manifest = {
        'version': VERSION, 'name': NAME, 'platform': 'windows-x64',
        'rendererVersion': current['version'], 'themeVersion': current['themeVersion'], 'minimumWindowsBuild': 19041,
        'officialCodexRequired': True, 'testedCodexVersion': '26.1103.4239.0',
        'independentRuntime': True, 'pythonVersion': sys.version.split()[0],
        'dependencies': versions, 'installedBytes': sum(v['bytes'] for k, v in entries.items() if k.startswith('payload/')),
        'files': entries,
    }
    (package / 'package-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    archive = release_root / (NAME + '.zip')
    if archive.exists():
        raise FileExistsError('Refusing to overwrite a release: ' + str(archive))
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=7) as output:
        for path in files(package):
            output.write(path, NAME + '/' + path.relative_to(package).as_posix())
    with zipfile.ZipFile(archive) as output:
        assert output.testzip() is None, 'ZIP CRC failure'
        assert len(output.infolist()) == len(entries) + 1
    checksum = sha(archive)
    (release_root / (NAME + '.sha256')).write_text(checksum + '  ' + archive.name + '\n', encoding='ascii')
    (release_root / 'SHA256SUMS.txt').write_text(checksum + '  ' + archive.name + '\n', encoding='ascii')
    report = {
        'version': VERSION, 'archive': str(archive), 'archiveBytes': archive.stat().st_size,
        'archiveSha256': checksum, 'installedPayloadBytes': manifest['installedBytes'],
        'packageFileCount': len(entries) + 1, 'stagingDirectory': str(package),
        'stdlibFiles': stdlib_count, 'runtimeCheck': runtime_result,
        'sourceProjectRequired': False, 'downloadedRuntime': False,
        'currentInstallationModified': False, 'nativeCodexActivated': False,
    }
    (work / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--build-root', type=Path, default=CACHE_ROOT)
    parser.add_argument('--release-root', type=Path, default=RELEASE_ROOT)
    args = parser.parse_args()
    build(args.build_root, args.release_root)
