"""Build a standalone theme without proprietary images or startup media."""
from pathlib import Path
import argparse
import base64
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'native/runtime'
TRANSPARENT_PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4//8/AwAI/AL+X8k1AAAAAElFTkSuQmCC'


def build(output, wallpaper=None, motion='system'):
    art = TRANSPARENT_PNG
    if wallpaper:
        wallpaper = Path(wallpaper)
        mime = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}.get(wallpaper.suffix.lower())
        if not mime:
            raise ValueError('Wallpaper must be PNG, JPEG or WebP')
        if wallpaper.stat().st_size > 20_000_000:
            raise ValueError('Wallpaper must be at most 20 MB')
        art = 'data:' + mime + ';base64,' + base64.b64encode(wallpaper.read_bytes()).decode('ascii')
    font = 'data:font/ttf;base64,' + base64.b64encode((SOURCE / 'fonts/eva-heading.ttf').read_bytes()).decode('ascii')
    css = (SOURCE / 'theme.css').read_text('utf8').replace('__EVA_ART__', art).replace('__EVA_HEADER_FONT__', font)
    bundle = (SOURCE / 'theme.js').read_text('utf8').replace('__EVA_CONFIG__', json.dumps({'motion': motion, 'muted': True})).replace('__EVA_CSS__', json.dumps(css, ensure_ascii=True))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'theme.bundle.js'
    target.write_text(bundle, encoding='utf8')
    manifest = {'themeVersion': 'R7-installed-6', 'edition': 'public-theme-only', 'startupIncluded': False,
                'wallpaper': 'user-supplied' if wallpaper else 'transparent',
                'fontLicense': 'SIL OFL 1.1; native/runtime/fonts/OFL.txt',
                'files': {target.name: {'bytes': target.stat().st_size, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}}}
    (output / 'public-theme-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf8')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    parser.add_argument('--wallpaper', type=Path, help='A PNG/JPEG/WebP that you are permitted to use; embedded without cropping or added opacity')
    parser.add_argument('--motion', choices=['system', 'on', 'off'], default='system')
    args = parser.parse_args()
    print(build(args.output, args.wallpaper, args.motion))
