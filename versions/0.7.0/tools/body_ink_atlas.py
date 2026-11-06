"""Generate a reference outline for each SVG that the project uses for lettering.

Only custom SVGs that exceed the vector reader's vocabulary use this fallback.
An author may rasterize edited glyph artwork with Qt during a rebuild. The
shipped studio's original paths need no external graphics library.
"""
import base64
import json
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).parent


def glyph_art(target):
    return [c for c in target['costumes'] if c['name'].startswith(('UI glyph [','UI icon '))]


def rasterize(costumes, assets):
    manifest = [{'hash':c['name'], 'cx':c['rotationCenterX'], 'cy':c['rotationCenterY'],
                 'svg':base64.b64encode(assets[c['md5ext']]).decode()} for c in costumes]
    with tempfile.TemporaryDirectory() as work:
        folder = pathlib.Path(work)
        (folder/'input.json').write_text(json.dumps(manifest))
        flags = subprocess.check_output(['pkg-config','--cflags','--libs','Qt6Svg','Qt6Gui','Qt6Core'],text=True).split()
        subprocess.run(['c++','-std=c++17',str(ROOT/'body_ink_raster.cpp'),'-o',str(folder/'read-svg'),*flags],check=True)
        subprocess.run([str(folder/'read-svg'),str(folder/'input.json'),str(folder/'output.json')],check=True)
        return json.loads((folder/'output.json').read_text())


def atlas_rows(target, assets):
    costumes = glyph_art(target)
    bank = rasterize(costumes,assets)
    # Use one compact entry per *distinct* scanline, plus a glyph-local map.
    # Rows shared by capitals, repeated stems and accents are stored once.
    rows=[''];ids={'':1};maps=[]
    for costume in costumes:
        sequence=[]
        for row in bank[costume['name']]:
            if row not in ids:
                rows.append(row);ids[row]=len(rows)
            sequence.append(str(ids[row]).zfill(4))
        if len(rows)>9999:
            raise ValueError('Too many distinct font scanlines')
        maps.append(''.join(sequence))
    return rows, maps
