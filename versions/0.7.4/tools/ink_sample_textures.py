"""Give native subpixel ink stamps a texture at standard Pen resolution.

Scratch renders a vector at a power-of-two texture resolution near its scale.
The procedural eight-unit squares are stamped at 6.25%, making that texture
less than one texel wide. Standard-quality Scratch also rounds drawable positions
to integer stage coordinates. A single bitmap cell stamped at an integer corner
covers the same physical area in standard and high-quality rendering.
"""
import hashlib
import re
import struct
import zlib

from .ink_opacity import CELL, LEVELS, MASK, ROW, TILES, emit_mask, emit_row
from .menu_layers import procs, replace_body
from .motion_layout import set_socket
from .stable_pen import png_chunk
from .ui_components import UIProgram, sub


TILE = re.compile(re.escape(TILES) + r'([a-f0-9]{6})/([a-f0-9]{6})/(\d+)')


def tile_color(match):
    face, outline = (bytes.fromhex(match[i]) for i in (1, 2))
    level = int(match[3])
    if not 0 <= level <= LEVELS:
        raise ValueError('Unexpected ink sample level.')
    return bytes(round(lo + (hi - lo) * level / LEVELS) for hi, lo in zip(face, outline))


def bitmap(rgb):
    # Scratch bitmap editor assets use two image pixels per stage unit.
    side = 16
    header = struct.pack('>IIBBBBB', side, side, 8, 2, 0, 0, 0)
    rows = (b'\0' + rgb * side) * side
    return (b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', header) +
            png_chunk(b'IDAT', zlib.compress(rows)) + png_chunk(b'IEND', b''))


def apply_ink_sample_textures(target, assets, *, document=None):
    """Convert only the generated palette, in place at its original indices."""
    old_files = set()
    install_grid = False
    for costume in target['costumes']:
        match = TILE.fullmatch(costume['name'])
        if not match:
            continue
        if costume['dataFormat'] == 'png':
            if (costume['rotationCenterX'], costume['rotationCenterY']) != (0,16):
                costume.update(rotationCenterX=0, rotationCenterY=16)
                install_grid = True
            continue
        rgb = tile_color(match)
        old = costume['md5ext']
        source = (f'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8" '
                  f'viewBox="0 0 8 8"><rect width="8" height="8" fill="#{rgb.hex()}"/></svg>').encode()
        if assets[old] != source or costume['dataFormat'] != 'svg':
            raise ValueError(f'Ink sample {costume["name"]} has been edited; preserving the source requires review.')
        image = bitmap(rgb)
        digest = hashlib.md5(image).hexdigest()
        filename = digest + '.png'
        assets[filename] = image
        costume.update(assetId=digest, md5ext=filename, dataFormat='png', bitmapResolution=2,
                       rotationCenterX=0, rotationCenterY=16)
        old_files.add(old)
        install_grid = True

    if install_grid:
        n = UIProgram(target, exporting=bool(document and 'targets' not in document))
        replace_body(n, MASK, emit_mask(n, step=1))
        replace_body(n, ROW, emit_row(n, step=1))
        # The sampler evaluates coverage at each cell center. Request the
        # integer lower-left corner as the drawable position; its corner pivot
        # positions the cell over exactly that sample, without GPU rounding.
        stamp_move, = procs(n, n.definition(CELL), 'motion_gotoxy')
        set_socket(n, stamp_move, 'X', sub(n.v('UI mask x'), .5))
        set_socket(n, stamp_move, 'Y', sub(n.v('UI mask y'), .5))

    # A host may have duplicated and renamed one of the old palette assets.
    # Keep that file for any other costume or sound that still references it.
    targets = (document or {}).get('targets', [target])
    referenced = {asset['md5ext'] for t in targets for asset in t.get('costumes', []) + t.get('sounds', [])}
    for old in old_files - referenced:
        del assets[old]
    return target
