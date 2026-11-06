"""Build a retained Pen presentation pass in an existing native Scratch target.

apply_target mutates the supplied target and the archive asset-bytes dictionary.
Geometry, optics, the public component API, and the green-flag loop are reused.
"""
import hashlib
import struct
import zlib


BAND_HEIGHT = 8
BAND_COUNT = 360 // BAND_HEIGHT
COMMAND_LISTS = ('frameX', 'frameY', 'frameRGB', 'frameTransparency')
# These values feed geometry, optics, render bounds, and pixel resolution.
# LG advance updates the visible positions/deformation before LG render.
FRAME_PROPERTIES = ('x', 'y', 'w', 'h', 'r', 'amp', 'scaleX', 'scaleY',
                    'reflection', 'distortion', 'edge', 'highlight', 'light',
                    'tint', 'join', 'group', 'quality')


def png_chunk(kind, data):
    return (struct.pack('>I', len(data)) + kind + data +
            struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff))


def paeth(a, b, c):
    estimate = a + b - c
    da, db, dc = abs(estimate - a), abs(estimate - b), abs(estimate - c)
    if da <= db and da <= dc:
        return a
    return b if db <= dc else c


def opaque_png_rows(data):
    """Decode 8-bit RGB/RGBA rows, preserving the source image's actual texels."""
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Expected PNG costume')
    header = data[16:29]
    width, height, depth, kind, compression, filtering, interlace = struct.unpack('>IIBBBBB', header)
    if depth != 8 or kind not in (2, 6) or any((compression, filtering, interlace)):
        raise ValueError('Background must be a standard 8-bit RGB/RGBA PNG')
    channels = 3 if kind == 2 else 4
    cursor, parts = 8, []
    while cursor < len(data):
        size, label = struct.unpack('>I4s', data[cursor:cursor + 8])
        if label == b'IDAT':
            parts.append(data[cursor + 8:cursor + size + 8])
        cursor += size + 12
    raw = zlib.decompress(b''.join(parts))
    stride = width * channels
    if len(raw) != (stride + 1) * height:
        raise ValueError('Unexpected PNG row size')
    previous = bytes(stride)
    rows = []
    for start in range(0, len(raw), stride + 1):
        filter_type = raw[start]
        row = bytearray(raw[start + 1:start + 1 + stride])
        if filter_type == 1:
            for i in range(channels, stride):
                row[i] = (row[i] + row[i - channels]) & 255
        elif filter_type == 2:
            row = bytearray((a + b) & 255 for a, b in zip(row, previous))
        elif filter_type in (3, 4):
            for i in range(stride):
                left = row[i - channels] if i >= channels else 0
                up = previous[i]
                diagonal = previous[i - channels] if i >= channels else 0
                predictor = (left + up) // 2 if filter_type == 3 else paeth(left, up, diagonal)
                row[i] = (row[i] + predictor) & 255
        elif filter_type != 0:
            raise ValueError('Unknown PNG scanline filter')
        if channels == 4 and min(row[3::4]) != 255:
            raise ValueError('Background strips require opaque source pixels')
        previous = bytes(row)
        rows.append(previous)
    return width, height, kind, rows


def append_strips(target, assets):
    costumes = target['costumes']
    for bg, name in enumerate(('Reference photo', 'Calibration grid'), 1):
        full = next(c for c in costumes if c['name'] == name)
        resolution = full['bitmapResolution']
        width, height, kind, rows = opaque_png_rows(assets[full['md5ext']])
        if (width, height) != (480 * resolution, 360 * resolution):
            raise ValueError(f'{name} must cover the entire stage')
        strip_height = BAND_HEIGHT * resolution
        for band in range(BAND_COUNT):
            start = band * strip_height
            pixels = b''.join(b'\0' + row for row in rows[start:start + strip_height])
            header = struct.pack('>IIBBBBB', width, strip_height, 8, kind, 0, 0, 0)
            image = (b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', header) +
                     png_chunk(b'IDAT', zlib.compress(pixels)) + png_chunk(b'IEND', b''))
            digest = hashlib.md5(image).hexdigest()
            filename = digest + '.png'
            assets[filename] = image
            costumes.append(dict(full, name=f'LG strip {bg} {band + 1}', assetId=digest,
                                 md5ext=filename, rotationCenterX=width / 2,
                                 rotationCenterY=strip_height / 2))


# Native block constructors. A Node describes one block, including attached
# value reporters or statement stacks. Primitive variable reporters use SB3's
# compact representation. Each expression occurrence receives its own block ID.
class Node:
    def __init__(self, opcode, inputs=None, fields=None, shadow=False):
        self.opcode = opcode
        self.inputs = inputs or {}
        self.fields = fields or {}
        self.shadow = shadow


class Native:
    def __init__(self, target):
        self.target = target
        self.blocks = target['blocks']
        self.next_id = 0
        self.var_ids = {pair[0]: key for key, pair in target['variables'].items()}
        self.list_ids = {pair[0]: key for key, pair in target['lists'].items()}

    def storage(self, name, is_list=False):
        ids = self.list_ids if is_list else self.var_ids
        if name not in ids:
            key = 'lgframe' + hashlib.sha256(('list:' if is_list else 'var:').encode() + name.encode()).hexdigest()[:20]
            if any(key in self.target[k] for k in ('blocks', 'variables', 'lists')):
                raise ValueError('Generated Scratch ID collides with project data')
            ids[name] = key
            self.target['lists' if is_list else 'variables'][key] = [name, [] if is_list else 0]
        return [name, ids[name]]

    def v(self, name):
        return [12, *self.storage(name)]

    def set(self, name, value):
        return Node('data_setvariableto', {'VALUE': value}, {'VARIABLE': self.storage(name)})

    def change(self, name, value):
        return Node('data_changevariableby', {'VALUE': value}, {'VARIABLE': self.storage(name)})

    def list_op(self, opcode, name, **inputs):
        return Node(opcode, inputs, {'LIST': self.storage(name, True)})

    def clear(self, name):
        return self.list_op('data_deletealloflist', name)

    def add(self, name, value):
        return self.list_op('data_addtolist', name, ITEM=value)

    def item(self, name, index):
        return self.list_op('data_itemoflist', name, INDEX=index)

    def length(self, name):
        return self.list_op('data_lengthoflist', name)

    def emit(self, node, parent):
        self.next_id += 1
        key = f'lgpresent{self.next_id}'
        if key in self.blocks:
            raise ValueError('Presentation already exists or conflicts with source IDs')
        block = {'opcode': node.opcode, 'inputs': {}, 'fields': node.fields,
                 'next': None, 'parent': parent, 'shadow': node.shadow, 'topLevel': False}
        self.blocks[key] = block
        for name, value in node.inputs.items():
            if name.startswith('SUBSTACK'):
                block['inputs'][name] = [2, self.chain(value, key)[0]]
            elif isinstance(value, Node):
                block['inputs'][name] = [1 if value.shadow else 2, self.emit(value, key)]
            elif isinstance(value, list):
                block['inputs'][name] = [2, value]
            else:
                block['inputs'][name] = [1, [10 if isinstance(value, str) else 4, str(value)]]
        return key

    def chain(self, nodes, parent):
        first, last = None, parent
        for node in nodes:
            key = self.emit(node, last)
            if first is None:
                first = key
            else:
                self.blocks[last]['next'] = key
            last = key
        return first, last

    def attach(self, parent, nodes, tail):
        first, last = self.chain(nodes, parent)
        self.blocks[parent]['next'] = first
        self.blocks[last]['next'] = tail
        if tail:
            self.blocks[tail]['parent'] = last

    def definition(self, name):
        for key, block in self.blocks.items():
            if not isinstance(block, dict) or block['opcode'] != 'procedures_definition':
                continue
            proto = self.blocks[block['inputs']['custom_block'][1]]
            if proto['mutation']['proccode'] == name:
                return key
        raise ValueError(f'Missing {name}')

    def sequence(self, definition):
        result = []
        key = self.blocks[definition]['next']
        while key:
            result.append(key)
            key = self.blocks[key]['next']
        return result

    def remove(self, key):
        """Remove a detached statement and its owned input and substack children."""
        block = self.blocks.pop(key)
        for name, binding in block['inputs'].items():
            for value in binding[1:]:
                if isinstance(value, str) and value in self.blocks:
                    if name.startswith('SUBSTACK'):
                        while value:
                            following = self.blocks[value]['next']
                            self.remove(value)
                            value = following
                    else:
                        self.remove(value)
        if block.get('comment'):
            self.target['comments'].pop(block['comment'], None)


def op(name, a, b):
    if name == 'join':
        return Node('operator_join', {'STRING1': a, 'STRING2': b})
    numeric = name in ('add', 'subtract', 'multiply', 'divide')
    prefix = 'NUM' if numeric else 'OPERAND'
    return Node('operator_' + name, {prefix + '1': a, prefix + '2': b})


def iff(condition, yes, no=None):
    inputs = {'CONDITION': condition, 'SUBSTACK': yes}
    if no is not None:
        inputs['SUBSTACK2'] = no
    return Node('control_if_else' if no is not None else 'control_if', inputs)


def go(x, y):
    return Node('motion_gotoxy', {'X': x, 'Y': y})


def transparency(value):
    menu = Node('pen_menu_colorParam', fields={'colorParam': ['transparency', None]}, shadow=True)
    return Node('pen_setPenColorParamTo', {'COLOR_PARAM': menu, 'VALUE': value})


def arg(name):
    return Node('argument_reporter_string_number', fields={'VALUE': [name, None]})


def clear_commands(n):
    return [n.clear(name) for name in COMMAND_LISTS]


def patch_shading(n):
    proc = n.definition('LG shade %s %s %s')
    commands = n.sequence(proc)
    start = next(i for i,k in enumerate(commands) if n.blocks[k]['opcode'] == 'pen_setPenColorToColor')
    color_id, alpha_id, *drawing = commands[start:]
    expected = ['motion_gotoxy', 'pen_penDown', 'motion_gotoxy', 'pen_penUp']
    if [n.blocks[key]['opcode'] for key in drawing] != expected:
        raise ValueError('Unexpected LG shade tail')
    # Move the exact original color/coverage expression trees into variables.
    # Their block IDs and parent links remain valid.
    color = n.blocks[color_id]
    color.update(opcode='data_setvariableto', fields={'VARIABLE': n.storage('strokeRGB')},
                 inputs={'VALUE': color['inputs']['COLOR']})
    alpha = n.blocks[alpha_id]
    old_menu = alpha['inputs']['COLOR_PARAM'][1]
    alpha.update(opcode='data_setvariableto', fields={'VARIABLE': n.storage('strokeTransparency')},
                 inputs={'VALUE': alpha['inputs']['VALUE']})
    n.remove(old_menu)
    for key in drawing:
        n.remove(key)
    n.attach(alpha_id, [iff(op('equals', n.v('preparingFrame'), 1), [
        n.add('frameX', arg('x')), n.add('frameY', arg('y')),
        n.add('frameRGB', n.v('strokeRGB')), n.add('frameTransparency', n.v('strokeTransparency')),
    ], [Node('pen_setPenColorToColor', {'COLOR': n.v('strokeRGB')}),
        transparency(n.v('strokeTransparency'))])], None)


def scene_signature(n):
    # The nonnumeric prefix forces a string comparison. Length-prefixed tokens
    # distinguish group strings even if they contain delimiters. Active slots
    # are emitted in ID order, so changes of membership also invalidate the key.
    def token(value):
        return [n.set('sceneValue', value),
                n.set('preparedScene', op('join', n.v('preparedScene'),
                      op('join', Node('operator_length', {'STRING': n.v('sceneValue')}),
                         op('join', ':', n.v('sceneValue')))))]
    component = token(n.v('sceneSlot'))
    for name in FRAME_PROPERTIES:
        component.extend(token(n.item(name, n.v('sceneSlot'))))
    return [n.set('preparedScene', op('join', 'LG/', n.v('frameBG'))),
            n.set('sceneSlot', 1), Node('control_repeat', {'TIMES': 8, 'SUBSTACK': [
                iff(op('equals', n.item('active', n.v('sceneSlot')), 1), component),
                n.change('sceneSlot', 1)]})]


def valid_frame(n):
    return op('equals', n.v('frameGeneration'), n.v('screenGeneration'))


def presentation(n):
    """Restore each affected strip, then replay every now-safe row in order."""
    v = n.v
    lower = op('subtract', 180, op('multiply', BAND_HEIGHT, v('frameBand')))
    upper = op('add', v('bandBottom'), BAND_HEIGHT)
    def intersects(top, bottom):
        return op('and', op('lt', v('bandBottom'), v(top)), op('gt', upper, v(bottom)))
    dirty = op('or',
        Node('operator_not', {'OPERAND': op('equals', v('previousBG'), v('frameBG'))}),
        op('or', intersects('previousTop', 'previousBottom'), intersects('strokeTop', 'strokeBottom')))
    costume = op('join', 'LG strip ', op('join', v('frameBG'), op('join', ' ', v('frameBand'))))
    restore = [Node('looks_switchcostumeto', {'COSTUME': costume}),
               go(0, op('add', v('bandBottom'), BAND_HEIGHT / 2)), Node('pen_stamp')]
    exhausted = op('gt', v('strokeIndex'), v('strokeCount'))
    # Allow a q/2+1.5 margin for the original line's diameter and AA. Defer
    # centers near a band boundary until the lower band is restored as well.
    too_low = op('lt', op('subtract', n.item('frameY', v('strokeIndex')), v('strokeGuard')),
                 v('bandBottom'))
    cancelled = Node('operator_not', {'OPERAND': valid_frame(n)})
    stop = op('or', cancelled, op('or', exhausted, op('and',
              op('lt', v('frameBand'), BAND_COUNT), too_low)))
    replay = [n.set('strokeX', n.item('frameX', v('strokeIndex'))),
              n.set('strokeY', n.item('frameY', v('strokeIndex'))),
              Node('pen_setPenColorToColor', {'COLOR': n.item('frameRGB', v('strokeIndex'))}),
              transparency(n.item('frameTransparency', v('strokeIndex'))),
              go(op('subtract', v('strokeX'), op('divide', v('q'), 2)), v('strokeY')),
              Node('pen_penDown'),
              go(op('add', v('strokeX'), op('divide', v('q'), 2)), v('strokeY')),
              Node('pen_penUp'), n.change('strokeIndex', 1)]
    return [n.set('preparingFrame', 0), n.set('strokeCount', n.length('frameY')),
            n.set('strokeIndex', 1), n.set('frameBand', 1),
            n.set('strokeGuard', op('add', op('divide', v('q'), 2), 1.5)),
            iff(op('gt', v('strokeCount'), 0), [
                n.set('strokeTop', op('add', n.item('frameY', 1), v('strokeGuard'))),
                n.set('strokeBottom', op('subtract', n.item('frameY', v('strokeCount')), v('strokeGuard')))],
                [n.set('strokeTop', -181), n.set('strokeBottom', 181)]),
            Node('control_repeat', {'TIMES': BAND_COUNT, 'SUBSTACK': [
                n.set('bandBottom', lower), iff(op('and', valid_frame(n), dirty), restore),
                Node('control_repeat_until', {'CONDITION': stop, 'SUBSTACK': replay}),
                n.change('frameBand', 1)]}),
            iff(valid_frame(n), [n.set('previousBG', v('frameBG')),
                n.set('previousTop', v('strokeTop')), n.set('previousBottom', v('strokeBottom')),
                n.set('displayedScene', v('preparedScene'))])]


def apply_target(target, assets):
    """Patch a Studio sprite or importable component in place; return that target."""
    n = Native(target)
    append_strips(target, assets)
    patch_shading(n)
    # Standalone samples follow the live background. A frame locks the optical
    # sample and the restored stage strips to the same image even if B is hit.
    bg_proc = n.definition('LG background %s %s')
    old_start = n.blocks[bg_proc]['next']
    n.attach(bg_proc, [iff(op('equals', n.v('preparingFrame'), 0),
                           [n.set('frameBG', n.v('Background'))])], old_start)
    chooser = n.blocks[n.sequence(bg_proc)[-1]]
    equals = n.blocks[chooser['inputs']['CONDITION'][1]]
    existing = equals['inputs']['OPERAND1'][1]
    if isinstance(existing, str):
        n.remove(existing)
    equals['inputs']['OPERAND1'] = [2, n.v('frameBG')]

    render = n.definition('LG render')
    sequence = n.sequence(render)
    clear_pos = next(i for i,k in enumerate(sequence) if n.blocks[k]['opcode'] == 'pen_clear')
    hide_pos = next(i for i,k in enumerate(sequence[clear_pos:], clear_pos) if n.blocks[k]['opcode'] == 'looks_hide')
    for key in sequence[clear_pos:hide_pos + 1]:
        n.remove(key)
    done = next(key for key in sequence if key in n.blocks and n.blocks[key]['opcode'] == 'pen_setPenColorParamTo')
    last_shade = n.blocks[done]['parent']
    prepare_head = sequence[hide_pos + 1]
    prefix = [n.set('frameGeneration', n.v('screenGeneration')),
              iff(op('equals', n.v('Background'), 2),
                  [n.set('frameBG', 2)], [n.set('frameBG', 1)]), *scene_signature(n)]
    first, tail = n.chain(prefix, sequence[clear_pos - 1])
    n.blocks[sequence[clear_pos - 1]]['next'] = first
    same = op('equals', n.v('preparedScene'), n.v('displayedScene'))
    gate = n.emit(iff(Node('operator_not', {'OPERAND': same}),
                      [n.set('preparingFrame', 1), *clear_commands(n)]), tail)
    n.blocks[tail]['next'] = gate
    n.blocks[gate]['next'] = done
    n.blocks[done]['parent'] = gate
    first_work = n.blocks[gate]['inputs']['SUBSTACK'][1]
    last_work = first_work
    while n.blocks[last_work]['next']:
        last_work = n.blocks[last_work]['next']
    n.blocks[last_work]['next'] = prepare_head
    n.blocks[prepare_head]['parent'] = last_work
    n.attach(last_shade, [iff(valid_frame(n), presentation(n)),
             n.set('preparingFrame', 0), *clear_commands(n)], None)
    initializer = n.definition('LG initialize')
    n.attach(n.sequence(initializer)[-1], [n.change('screenGeneration', 1),
             n.set('displayedScene', ''), n.set('preparingFrame', 0), n.set('previousBG', 0),
             n.set('previousTop', -181), n.set('previousBottom', 181), *clear_commands(n)], None)
    return target
