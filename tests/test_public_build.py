from pathlib import Path
import hashlib
import importlib.util
import json
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_theme', ROOT / 'tools/build_theme.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PublicBuild(unittest.TestCase):
    def test_build_is_self_contained_and_manifest_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            target = builder.build(directory)
            text = target.read_text('utf8')
            self.assertNotIn('__EVA_CSS__', text)
            self.assertNotIn('__EVA_CONFIG__', text)
            self.assertNotIn('__EVA_ART__', text)
            self.assertNotIn('__EVA_HEADER_FONT__', text)
            manifest = json.loads((Path(directory) / 'public-theme-manifest.json').read_text())
            self.assertFalse(manifest['startupIncluded'])
            self.assertEqual(manifest['files'][target.name]['sha256'], hashlib.sha256(target.read_bytes()).hexdigest())

    def test_custom_art_is_embedded_and_unsupported_format_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / 'own.png'
            import base64
            image.write_bytes(base64.b64decode(builder.TRANSPARENT_PNG.split(',', 1)[1]))
            target = builder.build(root / 'out', image)
            manifest = json.loads((target.parent / 'public-theme-manifest.json').read_text())
            self.assertEqual(manifest['wallpaper'], 'user-supplied')
            with self.assertRaisesRegex(ValueError, 'PNG, JPEG or WebP'):
                builder.build(root / 'out', root / 'script.svg')


if __name__ == '__main__':
    unittest.main()
