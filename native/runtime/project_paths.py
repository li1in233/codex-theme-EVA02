"""Local build inputs. Private media and generated outputs are never tracked."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = Path(os.environ.get('EVA_ASSET_ROOT', ROOT / 'assets/private')).resolve()
MEDIA_ROOT = ASSET_ROOT / 'masters'
CACHE_ROOT = Path(os.environ.get('EVA_CACHE_ROOT', 'D:/DevCache/CodexEVA')).resolve()
TEMP_ROOT = CACHE_ROOT / 'tmp'
RELEASE_ROOT = Path(os.environ.get('EVA_RELEASE_ROOT', ROOT / 'releases')).resolve()
TEMP_ROOT.mkdir(parents=True, exist_ok=True)
