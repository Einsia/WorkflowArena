"""Validate and load the original media images from separately supplied archives."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def validate(archive_dir, manifest):
    archives = []
    for row in manifest['images']:
        name = row['archive']
        if Path(name).name != name:
            raise ValueError('Archive must be a filename')
        path = archive_dir / name
        if path.stat().st_size != row['archive_bytes']:
            raise ValueError('Archive size mismatch: ' + name)
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != row['archive_sha256']:
            raise ValueError('Archive checksum mismatch: ' + name)
        archives.append((path, row))
    return archives


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-dir', type=Path, required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    manifest = json.loads(Path(__file__).with_name('manifest.json').read_text())
    archives = validate(args.archive_dir, manifest)
    for path, row in archives:
        if not args.verify_only:
            subprocess.run(['docker', 'load', '-i', str(path)], check=True)
            actual = subprocess.check_output(['docker', 'image', 'inspect', row['tag'],
                                              '--format', '{{.Id}}'], universal_newlines=True).strip()
            if actual != row['image_id']:
                raise RuntimeError('Loaded image ID mismatch: ' + row['tag'])
        print(('Validated archive: ' if args.verify_only else 'Validated image: ') + row['tag'])


if __name__ == '__main__':
    main()
