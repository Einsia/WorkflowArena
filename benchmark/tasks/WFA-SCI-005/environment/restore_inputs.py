"""Restore losslessly compressed benchmark inputs and verify their content hashes."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def restore(root, manifest, remove_archives=False):
    for record in manifest['files']:
        for key in ('archive', 'path'):
            name = Path(record[key])
            if name.is_absolute() or '..' in name.parts:
                raise ValueError('Input path must stay inside its directory')
        source, target = root / record['archive'], root / record['path']
        if target.exists():
            if digest(target) != record['sha256']:
                raise ValueError('Existing input has a different checksum: ' + record['path'])
            continue
        if digest(source) != record['archive_sha256']:
            raise ValueError('Compressed input checksum mismatch: ' + record['archive'])
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + '.restoring')
        try:
            h = hashlib.sha256()
            size = 0
            with gzip.open(source, 'rb') as stream, temp.open('xb') as output:
                for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
                    size += len(block)
                    h.update(block)
                    output.write(block)
            if h.hexdigest() != record['sha256'] or size != record['bytes']:
                raise ValueError('Restored input content mismatch: ' + record['path'])
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
        if remove_archives:
            source.unlink()
        print('Verified input: ' + record['path'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--remove-archives', action='store_true')
    args = parser.parse_args()
    restore(args.input_dir, json.loads(args.manifest.read_text()), args.remove_archives)
