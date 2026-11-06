"""Build and inspect a shareable tree without changing local release archives."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCAL_ONLY = {f'versions/0.6.0/validation/{name}-comparison.mp4' for name in ('drag','menu')}
ARCHIVES = {'.sb3', '.sprite3', '.zip'}
MEDIA = {'.svg', '.png', '.mp4'}
TEXT = {'', '.md', '.txt', '.py', '.cpp', '.cjs', '.json', '.log', '.sh', '.yml', '.toml', '.sha256'}
PERSONAL_PATH = re.compile(r'/(?:Users|home)/[\w. -]+/|/(?:private/)?var/folders/[a-z0-9]{2}/', re.I)
EMAIL = re.compile(r'(?i)\b[\w.%+-]+@[a-z0-9.-]+\.(?:com|org|edu|net|io|dev|us|cn)\b')
PORTABLE_SOURCE = """SOURCE = ROOT / 'inputs' / 'EffOnly_reference.sb3'
if not SOURCE.is_file():
    candidates = sorted((ROOT / 'versions').glob('*/inputs/EffOnly_reference.sb3'))
    if ROOT.parent.name == 'versions':
        candidates += sorted(ROOT.parent.glob('*/inputs/EffOnly_reference.sb3'))
    if candidates:
        SOURCE = candidates[0]"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def portable(path, data):
    if path.suffix not in TEXT:
        return data
    s = data.decode('utf-8')
    if path.name == 'build_renderer.py':
        s = re.sub(r"(?m)^SOURCE=Path\('[^'\n]+LiquidGlassRenderer_EffOnly\.sb3'\)$", PORTABLE_SOURCE, s)
    # Validation output records absolute paths. Keep paths meaningful on a clone.
    s = s.replace(str(ROOT) + '/', './')
    s = re.sub(r'/Users/[^/"\s]+/Dev/Scratch/LiqiudGlass/', './', s)
    return s.encode()


def repository_files():
    top = subprocess.check_output(['git','rev-parse','--show-toplevel'], cwd=ROOT, text=True).strip()
    if Path(top).resolve() != ROOT:
        raise ValueError('Run from the Liquid Glass project repository, not its parent.')
    names = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT)
    for item in set(os.fsdecode(names).rstrip('\0').split('\0')):
        path = Path(item)
        if path.is_absolute() or '..' in path.parts or any(part in ('.git','.github-sync','.local-tools') for part in path.parts):
            raise ValueError('Unsafe path in export.')
        if path.as_posix() in LOCAL_ONLY:
            continue
        local = ROOT/path
        if local.is_symlink() or not local.resolve().is_relative_to(ROOT):
            raise ValueError(f'External link in export: {path}')
        if local.exists():
            yield path


def export(dest):
    changed = {}
    for path in repository_files():
        local = ROOT/path
        raw = local.read_bytes()
        data = portable(path, raw)
        target = dest/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(local.stat().st_mode & 0o777)
        if raw != data:
            changed[path] = (sha(raw), sha(data), len(data))
    # Hash the shareable helper copies. Keep the recorded original hash when
    # a numbered Scratch file was edited by hand after its release.
    for manifest in dest.glob('versions/*/manifest.json'):
        obj = json.loads(manifest.read_bytes())
        touched = False
        for name, info in obj['files'].items():
            change = changed.get(manifest.parent.relative_to(dest)/name)
            if change and info['sha256'] == change[0]:
                info.update(sha256=change[1], bytes=change[2])
                touched = True
        if touched:
            manifest.write_text(json.dumps(obj, indent=2)+'\n')
    return len(changed)


def audit(dest):
    allowed = set((ROOT/'tools/reviewed_media.sha256').read_text().splitlines())
    private = ROOT/'.local-tools/private-terms.json'
    terms = json.loads(private.read_text()) if private.exists() else []
    seen, archive_ids = set(), set()

    def check_text(s, label):
        if PERSONAL_PATH.search(s) or EMAIL.search(s) or any(t.casefold() in s.casefold() for t in terms):
            raise ValueError(f'Personal information requires review in {label}.')

    def inspect(name, data, label, extracted):
        key = sha(data)
        ext = Path(name).suffix.lower()
        if (key,ext) in seen:
            return
        seen.add((key,ext))
        if ext in ARCHIVES:
            archive_ids.add(key)
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if archive.comment or len(set(archive.namelist())) != len(archive.namelist()):
                    raise ValueError(f'Review ZIP metadata in {label}.')
                for entry in archive.infolist():
                    check_text(entry.filename,label)
                    if entry.comment or entry.extra or not re.fullmatch(r'(project|sprite)\.json|[a-fA-F0-9]{32}\.(?:png|svg)',entry.filename):
                        raise ValueError(f'Review new archive member or metadata in {label}.')
                    inspect(entry.filename, archive.read(entry), label+'!'+entry.filename, extracted)
        elif ext in MEDIA:
            if key not in allowed:
                raise ValueError(f'Review the new media and its metadata before syncing {label} ({key}).')
            if ext == '.svg':
                check_text(data.decode(),label)
                (extracted/(key+ext)).write_bytes(data)
        elif ext in TEXT:
            check_text(data.decode(),label)
            (extracted/(key+ext)).write_bytes(data)
        else:
            raise ValueError(f'Review new file type before syncing {label}.')

    with tempfile.TemporaryDirectory() as scratch:
        extracted=Path(scratch)
        for p in sorted(dest.rglob('*')):
            if p.is_file():
                check_text(p.relative_to(dest).as_posix(), 'filename')
                inspect(p.name,p.read_bytes(),p.relative_to(dest).as_posix(),extracted)
        binary = os.environ.get('GITLEAKS_BIN') or shutil.which('gitleaks') or ROOT/'.local-tools/gitleaks'
        subprocess.run([binary,'dir','--redact','--no-banner','--config',str(dest/'.gitleaks.toml'),str(extracted)],check=True)
    print(f'Privacy scan passed for {len(seen)} distinct files and members, including {len(archive_ids)} distinct archives.')


def git(repo, *args, read=False):
    command = ['git', '-C', str(repo), *args]
    if read:
        return subprocess.check_output(command, text=True).strip()
    subprocess.run(command, check=True)


def commit(repo, message):
    git(repo, 'add', '-A', '--', '.')
    if git(repo, 'diff', '--cached', '--name-only', read=True):
        git(repo, 'commit', '-q', '-m', message)


def sync(message):
    # The original working directory has its own local-only Git history.
    # On a clean GitHub clone the upload can be made directly from that clone.
    remote_names = git(ROOT, 'remote', read=True).splitlines()
    local_only = subprocess.run(['git','-C',str(ROOT),'config','--get','liquidglass.localArchive'],
                                capture_output=True,text=True).stdout.strip() == 'true'
    if local_only and 'origin' in remote_names:
        raise SystemExit('Remove the origin from the original local-history checkout before syncing.')
    mirror = ROOT if 'origin' in remote_names and not local_only else ROOT/'.github-sync'
    if not (mirror/'.git').is_dir():
        raise SystemExit('Set up the private GitHub checkout in .github-sync first.')
    if git(mirror,'branch','--show-current',read=True) != 'main':
        raise SystemExit('Switch the publishing checkout to main before syncing.')
    email = git(mirror,'config','user.email',read=True).lower()
    if not email.endswith('@' + 'users.noreply.github.com'):
        raise SystemExit('Configure a GitHub no-reply commit email in the publishing checkout.')
    if mirror != ROOT and git(mirror,'status','--porcelain',read=True):
        raise SystemExit('There are pending changes in the publishing checkout. Review them before syncing.')
    with tempfile.TemporaryDirectory() as work:
        tree=Path(work)
        export(tree)
        audit(tree)
        files = {p.relative_to(tree) for p in tree.rglob('*') if p.is_file()}
        if mirror == ROOT:
            if any((ROOT/p).read_bytes() != (tree/p).read_bytes() for p in files):
                raise SystemExit('Local paths need redaction. Use a separate publishing checkout.')
            if any((ROOT/name).exists() for name in LOCAL_ONLY):
                raise SystemExit('Local-only recordings belong outside the publishing checkout.')
        else:
            commit(ROOT,message)
            tracked = subprocess.check_output(['git','-C',str(mirror),'ls-files','-z'])
            for old in os.fsdecode(tracked).rstrip('\0').split('\0'):
                if old and Path(old) not in files:
                    (mirror/old).unlink()
            for path in files:
                target = mirror/path
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(tree/path,target)
                target.chmod((tree/path).stat().st_mode & 0o777)
        commit(mirror,message)
    git(mirror, 'push','-u','origin','main')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument('--export', dest='destination', type=Path)
    operation.add_argument('--sync', metavar='COMMIT_MESSAGE')
    args = parser.parse_args()
    if args.sync:
        sync(args.sync)
    else:
        dest = args.destination.resolve()
        if dest == ROOT or dest.is_relative_to(ROOT) or (dest.exists() and any(dest.iterdir())):
            raise SystemExit('Use an empty temporary destination outside the working directory.')
        dest.mkdir(parents=True,exist_ok=True)
        print(f'Made {export(dest)} text files portable.')
        audit(dest)
