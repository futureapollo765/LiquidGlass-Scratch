"""Publish the two manifest-verified Scratch files from a committed release."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def prepare(destination):
    version = (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'0\.\d+\.\d+', version):
        raise ValueError(f'Invalid release version: {version!r}')
    folder = ROOT / 'versions' / version
    manifest = json.loads((folder / 'manifest.json').read_text())
    if manifest['version'] != version:
        raise ValueError('VERSION and the snapshot manifest disagree.')
    uploads = []
    for original in ('LiquidGlass_Studio.sb3', 'LiquidGlass_Component.sprite3'):
        base = Path(original)
        name = f'{base.stem}_{version}{base.suffix}'
        expected = manifest['files'][name]['sha256']
        # The numbered Studio can acquire a newer editor save. Keep it in Git,
        # and select only the manifest-matching bytes for the release download.
        for source in (folder / name, ROOT / original):
            if source.is_file() and digest(source) == expected:
                output = destination / name
                shutil.copyfile(source, output)
                uploads.append(output)
                break
        else:
            raise ValueError(f'Neither local copy matches the release manifest for {name}.')
    entries = (ROOT / 'UPDATE_LOG.txt').read_text().strip().split('\n\n')
    notes = next((entry.partition('\n')[2] for entry in entries
                  if entry.startswith(version + ' - ')), manifest['note'])
    return 'v' + version, notes, uploads


def publish(repo, commit, tag, notes, uploads):
    def gh(*args, check=True):
        return subprocess.run(['gh', 'release', *args, '--repo', repo], text=True,
                              capture_output=True, check=check)

    def read_release():
        result = gh('view', tag, '--json', 'assets,isDraft,url', check=False)
        if result.returncode == 0:
            return json.loads(result.stdout)
        if 'release not found' in result.stderr.lower() or 'http 404' in result.stderr.lower():
            return None
        raise RuntimeError(result.stderr.strip())

    release = read_release()
    if release is None:
        notes_file = uploads[0].parent / 'notes.txt'
        notes_file.write_text(notes + '\n')
        gh('create', tag, '--draft', '--target', commit, '--title', f'Liquid Glass {tag}',
           '--notes-file', str(notes_file))
        release = read_release()
    existing = {asset['name']: asset for asset in release['assets']}
    for file in uploads:
        if file.name in existing:
            continue
        if not release['isDraft']:
            raise ValueError(f'Published release is missing {file.name}.')
        gh('upload', tag, str(file))
    # Verify the bytes on GitHub before making a draft public to repo readers.
    verify = uploads[0].parent / 'downloaded'
    verify.mkdir()
    for file in uploads:
        gh('download', tag, '--pattern', file.name, '--dir', str(verify))
        if digest(verify / file.name) != digest(file):
            raise ValueError(f'GitHub release asset differs from its manifest: {file.name}')
    if release['isDraft']:
        gh('edit', tag, '--draft=false')
    print(read_release()['url'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory() as work:
            publish(args.repo, args.commit, *prepare(Path(work)))
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr or str(error))
