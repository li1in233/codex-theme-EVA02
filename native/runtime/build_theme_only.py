"""Build the public, media-free theme. See tools/build_theme.py --help."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[2] / 'tools/build_theme.py'), run_name='__main__')
