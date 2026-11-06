"""Native foreground art for the editable Liquid Glass controls.

Each glyph and symbol is a normal sprite costume. The renderer stamps these
only after a changed glass frame is complete, so the same code works in a
standalone sprite3 import, with no helper sprites or clone budget.
"""
import hashlib
import unicodedata
import json
import math

try:
    from .stable_pen import Native, Node, arg, go, iff, op, transparency
except ImportError:
    from stable_pen import Native, Node, arg, go, iff, op, transparency


# A small proportional, rounded-stroke alphabet authored for the stage. These
# paths remain editable SVG artwork in Scratch and use no platform font.
# Glyphs share an 0..10 cap-height box with lowercase ascenders/descenders.
OUTLINES = {
    'A': 'M0 10L3.5 0 7 10M1.35 6.25h4.3',
    'B': 'M0 10V0H3.7Q6.4 0 6.4 2.6Q6.4 5 3.7 5H0M3.7 5Q6.9 5 6.9 7.55Q6.9 10 3.7 10H0',
    'C': 'M6.3 1.6Q5.4 0 3.6 0Q0 0 0 5Q0 10 3.6 10Q5.6 10 6.6 8.3',
    'D': 'M0 0H3Q7 0 7 5Q7 10 3 10H0Z',
    'E': 'M6.1 0H0V10H6.3M0 4.8h5.1',
    'F': 'M6.1 0H0V10M0 4.7h5.1',
    'G': 'M6.5 1.6Q5.2 0 3.6 0Q0 0 0 5Q0 10 3.8 10Q5.7 10 6.8 8.9V5.6H3.8',
    'H': 'M0 0V10M7 0V10M0 4.8H7',
    'I': 'M0 0h2.8M1.4 0v10M0 10h2.8',
    'J': 'M5.4 0V7Q5.4 10 2.6 10Q.65 10 0 8.2',
    'K': 'M0 0V10M6.8 0L0 6M2.65 3.6L7 10',
    'L': 'M0 0V10h6',
    'M': 'M0 10V0L4.3 7.35 8.6 0V10',
    'N': 'M0 10V0L7.2 10V0',
    'O': 'M3.6 0C-1.2 0 -1.2 10 3.6 10C8.4 10 8.4 0 3.6 0Z',
    'P': 'M0 10V0h3.6Q6.8 0 6.8 3.1Q6.8 6.15 3.6 6.15H0',
    'Q': 'M3.6 0C-1.2 0 -1.2 10 3.6 10C8.4 10 8.4 0 3.6 0ZM4.8 7.5L7.7 10.7',
    'R': 'M0 10V0h3.5Q6.8 0 6.8 2.9Q6.8 5.7 3.5 5.7H0M3.2 5.7L7 10',
    'S': 'M6.25 1.35Q5.1 0 3.25 0Q.25 0 .25 2.55Q.25 4.5 3.45 5.05Q6.6 5.6 6.6 7.65Q6.6 10 3.45 10Q1.35 10 0 8.5',
    'T': 'M0 0h7.1M3.55 0v10',
    'U': 'M0 0V6.5Q0 10 3.5 10Q7 10 7 6.5V0',
    'V': 'M0 0L3.55 10 7.1 0',
    'W': 'M0 0L2.4 10 5.05 3.05 7.7 10 10.1 0',
    'X': 'M0 0l7 10M7 0L0 10',
    'Y': 'M0 0l3.6 5.35L7.2 0M3.6 5.35V10',
    'Z': 'M0 0h6.5L0 10h6.65',
    'a': 'M5.8 3.25v6.75M5.8 5Q5.1 3 3 3Q0 3 0 6.5Q0 10 2.9 10Q5.05 10 5.8 8',
    'b': 'M0 0v10M0 5Q.8 3 3 3Q6 3 6 6.5Q6 10 3 10Q.85 10 0 8',
    'c': 'M5.5 4.15Q4.7 3 3.1 3Q0 3 0 6.5Q0 10 3.1 10Q4.7 10 5.6 8.7',
    'd': 'M5.95 0v10M5.95 5Q5.15 3 3 3Q0 3 0 6.5Q0 10 3 10Q5.1 10 5.95 8',
    'e': 'M.1 6.2h5.8Q5.8 3 3.1 3Q0 3 0 6.5Q0 10 3.35 10Q5 10 5.9 8.9',
    'f': 'M1.3 10V2.2Q1.3 -.1 3.7 0M0 3.5h3.55',
    'g': 'M5.9 3.2v6.6Q5.9 13 2.9 13Q1.3 13 .25 12M5.9 5Q5.15 3 3 3Q0 3 0 6.45Q0 9.8 3 9.8Q5.1 9.8 5.9 8',
    'h': 'M0 0v10M0 5.1Q.95 3 3 3Q5.8 3 5.8 6v4',
    'i': 'M.65 3.3V10M.65 .4v.16',
    'j': 'M1.6 3.3v7.2Q1.6 12.8 0 12.8M1.6 .4v.16',
    'k': 'M0 0v10M5.5 3.1L0 7.8M2.35 5.8L5.9 10',
    'l': 'M.65 0v9.1Q.65 10 1.6 10',
    'm': 'M0 3.25V10M0 5Q.8 3 2.55 3Q4.75 3 4.75 5.55V10M4.75 5.15Q5.45 3 7.35 3Q9.65 3 9.65 5.65V10',
    'n': 'M0 3.25V10M0 5.1Q.95 3 3 3Q5.8 3 5.8 6v4',
    'o': 'M3.05 3C-1 3 -1 10 3.05 10C7.1 10 7.1 3 3.05 3Z',
    'p': 'M0 3.25v9.7M0 5Q.8 3 3 3Q6 3 6 6.5Q6 10 3 10Q.85 10 0 8',
    'q': 'M5.95 3.25v9.7M5.95 5Q5.15 3 3 3Q0 3 0 6.5Q0 10 3 10Q5.1 10 5.95 8',
    'r': 'M0 3.25V10M0 5.6Q.85 3 3.8 3.1',
    's': 'M4.9 4Q4.1 3 2.55 3Q.15 3 .15 4.85Q.15 6.15 2.65 6.55Q5.15 6.95 5.15 8.25Q5.15 10 2.55 10Q.9 10 0 8.95',
    't': 'M1.4 1.2v6.7Q1.4 10 3.65 9.8M0 3.45h3.6',
    'u': 'M0 3.25v4Q0 10 2.55 10Q4.6 10 5.7 7.95M5.7 3.25V10',
    'v': 'M0 3.25l2.9 6.75 2.9-6.75',
    'w': 'M0 3.25L2.35 10l2.25-5.2L6.9 10l2.3-6.75',
    'x': 'M0 3.25l5.65 6.75M5.65 3.25L0 10',
    'y': 'M0 3.2l3 6.8M5.95 3.2L1.45 13',
    'z': 'M0 3.3h5.55L0 10h5.65',
    '0': 'M3.1 0C-1.05 0 -1.05 10 3.1 10C7.25 10 7.25 0 3.1 0Z',
    '1': 'M.5 2.2L3 0v10M.6 10h4.9',
    '2': 'M0 2.2Q.6 0 3 0Q6 0 6 2.65Q6 4.15 4.45 5.65L0 10h6.3',
    '3': 'M0 1.45Q1.05 0 2.95 0Q5.8 0 5.8 2.55Q5.8 5 3 5H1.95M3.05 5Q6.05 5 6.05 7.4Q6.05 10 3 10Q.9 10 0 8.55',
    '4': 'M4.65 10V0L0 6.7h6.25',
    '5': 'M5.75 0H.7L.2 4.85Q1.35 4.2 2.9 4.2Q6 4.2 6 7.15Q6 10 2.95 10Q1.1 10 0 8.75',
    '6': 'M5.5 .8Q4.55 0 3.25 0Q0 0 0 5.95Q0 10 3.2 10Q6.15 10 6.15 7Q6.15 4.35 3.4 4.35Q1 4.35 0 6.15',
    '7': 'M0 0h6.35L2 10',
    '8': 'M3.15 0C-.7 0 -.7 4.95 3.15 4.95C7 4.95 7 0 3.15 0ZM3.15 4.95C-1 4.95 -1 10 3.15 10C7.3 10 7.3 4.95 3.15 4.95Z',
    '9': 'M.65 9.3Q1.55 10 2.9 10Q6.2 10 6.2 4.05Q6.2 0 3.05 0Q0 0 0 3.05Q0 5.7 2.85 5.7Q5.1 5.7 6.2 3.85',
    ' ': '', '!': 'M.75 0v6.8M.75 9.65v.14', '?': 'M0 1.9Q.9 0 2.9 0Q5.75 0 5.75 2.5Q5.75 4.05 3.9 5.15Q2.75 5.85 2.75 7.25M2.75 9.65v.12',
    '.':'M.65 9.6v.16', ',':'M1 9.15L.2 11.55', ':':'M.75 4.2v.12M.75 9.5v.12', ';':'M.75 4.2v.12M1 9.15L.2 11.55',
    "'":'M.95 0L.4 2.55', '"':'M.8 0L.3 2.55M3.3 0l-.5 2.55', '(': 'M2.55 -.2Q-1.5 5 2.55 11.35', ')': 'M.15 -.2Q4.2 5 .15 11.35',
    '[':'M2.75 -.1H0v11.3h2.75', ']':'M0 -.1h2.75v11.3H0', '{':'M3.35 -.1Q1.2 -.1 1.2 2.3v.85Q1.2 5 0 5.45Q1.2 5.9 1.2 7.75v1Q1.2 11.15 3.35 11.15', '}':'M0 -.1Q2.15 -.1 2.15 2.3v.85Q2.15 5 3.35 5.45Q2.15 5.9 2.15 7.75v1Q2.15 11.15 0 11.15',
    '-':'M0 6h4', '_':'M0 11.7h6.5', '+':'M0 5.3h6.2M3.1 2.2v6.2', '=':'M0 3.65h6.1M0 7h6.1', '/':'M0 10L4.5 0', '\\':'M0 0l4.5 10', '|':'M.65 -.5v12.1',
    '#':'M2.65 .2L1.05 9.8M6.4 .2L4.8 9.8M0 3.4h7.3M0 6.75h7.3', '*':'M3 1v5.8M.3 2.45l5.4 3M.3 5.45l5.4-3', '%':'M.2 10L7.75 0M1.6 .2a1.4 1.4 0 1 0 .02 0M6.45 7.4a1.4 1.4 0 1 0 .02 0',
    '$':'M5.45 1.65Q4.2 .6 2.8 .6Q.2 .6 .2 2.7Q.2 4.55 2.95 5.1Q5.8 5.7 5.8 7.45Q5.8 9.65 2.8 9.65Q1.15 9.65 0 8.5M2.95 -.65V11',
    '&':'M6.8 10L2.1 4.65Q.65 3.1 1.05 1.75Q1.5 .1 3.2 .1Q5.15 .1 5.1 1.9Q5.05 3.2 2.9 4.5Q-.15 6.25 .05 7.95Q.3 10 2.75 10Q5.8 10 6.95 5.8',
    '@':'M7.4 8.55Q5.75 10.25 3.95 10Q0 9.6 0 5.2Q0 .05 4.6 0Q8.9 .05 8.65 5Q8.55 7.3 7.1 7.6Q6.1 7.8 6.25 6.4L6.65 3.45M6.45 4.08Q5.85 2.85 4.55 3.1Q2.55 3.45 2.6 5.9Q2.65 7.95 4.35 7.65Q5.55 7.4 6.25 6.15',
    '^':'M0 4L3.05 .1 6.1 4', '`':'M0 0l2.1 2.05', '~':'M0 6.05Q1.5 3.6 3.15 5.35Q4.8 7.1 6.3 4.65', '<':'M5.9 2L0 5.15l5.9 3.3', '>':'M0 2l5.9 3.15L0 8.45',
    '…':'M.65 9.6v.12M4.3 9.6v.12M7.95 9.6v.12', '–':'M0 5.65h6.6', '—':'M0 5.65h9', '•':'M2 5.5h.3', '□':'M.2 1.25h6.2v7.7H.2z',
    '‘':'M1.65 0Q.4 .9 .5 2.35', '’':'M1.3 0Q1.4 1.3 0 2.45', '“':'M1.65 0Q.4 .9 .5 2.35M4.8 0Q3.55 .9 3.65 2.35', '”':'M1.3 0Q1.4 1.3 0 2.45M4.45 0Q4.55 1.3 3.15 2.45',
    '→':'M0 5h7M4 2l3 3-3 3','←':'M7 5H0M3 2L0 5l3 3','↑':'M3.5 9V1M.5 4l3-3 3 3','↓':'M3.5 1v8M.5 6l3 3 3-3', '✓':'M0 5.7l2.4 2.5L7.2 2',
    'ß':'M.1 10V3.4Q.1 0 2.85 0Q5.35 0 5.35 2.35Q5.35 4.05 3.15 4.95Q6.4 5.7 6.4 7.85Q6.4 10 3.55 10',
    'æ':'M0 4.2Q1.05 3 2.5 3Q4.65 3 4.65 5.1V10M4.65 6H2.45Q0 6 0 8.15Q0 10 2.15 10Q4 10 4.65 8M4.8 6.15h5.3Q9.9 3 7.55 3Q4.7 3 4.7 6.5Q4.7 10 7.9 10Q9.25 10 10.1 8.95',
    'ø':'M.15 10.45L5.95 2.55', 'Ø':'M.05 10.6L7.2 -.55', 'Ð':'M0 0H3Q7 0 7 5Q7 10 3 10H0ZM-.9 5h4.15',
    'ð':'M.8 1.7Q6.4 3.45 6.15 7.4Q5.9 10 3 10Q0 10 0 7.05Q0 4 3 4Q5 4 5.9 5.75M2.45 3.45L4.8 .75',
    'Þ':'M0 0v10M0 2.6h3Q6.2 2.6 6.2 5.35Q6.2 8 3 8H0', 'þ':'M0 0v13M0 5Q.8 3 3 3Q6 3 6 6.5Q6 10 3 10Q.85 10 0 8',
    '×':'M.4 2.5l5.6 5.6M6 2.5L.4 8.1', '÷':'M0 5.2h6.4M3.2 2v.12M3.2 8.35v.12', '°':'M1.9 -.25a1.65 1.65 0 1 0 .01 0',
}
OUTLINES['ø'] += OUTLINES['o']
OUTLINES['Ø'] += OUTLINES['O']
OUTLINES['Æ'] = 'M0 10L4.3 0h5.8M2.1 5.9h2.3M4.4 0v10h5.9M4.5 4.8h4.4'
OUTLINES.update({'›':OUTLINES['>'], '‹':OUTLINES['<'], '＋':OUTLINES['+'], '−':OUTLINES['–']})
ACCENTS = {0x300:'M1 0l2.35 1.45',0x301:'M4.55 0L2.2 1.45',0x302:'M.8 1.55L3 0l2.2 1.55',
           0x303:'M.45 1.15Q1.55 -.45 3 .65Q4.45 1.75 5.45 .25',0x308:'M1.2 .55v.11M4.65 .55v.11',
           0x30A:'M2.95 -.15a.8 .8 0 1 0 .01 0',0x327:'M3.15 10.25l-.75 1.2Q4.25 11.75 3.3 12.65Q2.6 13.05 1.8 12.65'}

def glyph_paths(char):
    if char in OUTLINES:
        return OUTLINES[char], ''
    decomposed=unicodedata.normalize('NFD',char)
    base=decomposed[0]
    marks=[ACCENTS[ord(mark)] for mark in decomposed[1:] if ord(mark) in ACCENTS]
    if base in OUTLINES and marks:
        # For capitals the marks sit above cap height. A cedilla sits below
        # the baseline and keeps its own coordinates.
        shift=-2.6 if base.isupper() and ord(decomposed[1])!=0x327 else 0
        return OUTLINES[base], f'<path transform="translate(0 {shift})" d="{" ".join(marks)}"/>'
    return OUTLINES['□'], ''


def advance(char):
    base = unicodedata.normalize('NFD',char)[0]
    if char == ' ': return 4.0
    if char in 'MWwm@%&#…—Ææ': return 11.8
    if base in 'ijlI .,:;!|`' or char in "'‘’": return 3.9
    if base in '()[]{}tfr/-' or char == chr(92): return 5.8
    if base.isupper(): return 9.0
    if base in '0123456789': return 8.0
    return 7.9


GLYPHS = (''.join(chr(n) for n in range(32, 127)) +
          ''.join(chr(n) for n in range(0xA1, 0x100) if chr(n) in OUTLINES or len(unicodedata.normalize('NFD',chr(n)))>1) + '…–—‘’“”•›‹→←↑↓✓＋−□')
GLYPH_WIDTH_LIST = 'UI glyph widths'
ICONS = {
    'sidebar': ('M3.5 4.2h13v11.6h-13z M8 4.5v11 M5.5 7h.4 M5.5 9.5h.4', 1.45),
    'down': ('M4.8 8l5.2 5 5.2-5', 1.85),
    'up': ('M4.8 12l5.2-5 5.2 5', 1.85),
    'next': ('M8 5l5 5-5 5', 1.7),
    'back': ('M12 5l-5 5 5 5', 1.85),
    'check': ('M4 10.3l4 3.8 8-8.2', 1.9),
    'more': ('M4.8 10h.3 M9.8 10h.3 M14.8 10h.3', 2.25),
    'status': ('M7.4 10a2.6 2.6 0 1 0 5.2 0a2.6 2.6 0 1 0 -5.2 0', 1.1),
}


def append_svg(target, assets, name, body, width, height, rx, ry):
    data = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">{body}</svg>').encode('utf-8')
    digest = hashlib.md5(data).hexdigest()
    file_name = digest + '.svg'
    assets[file_name] = data
    target['costumes'].append({'name': name, 'bitmapResolution': 1,
                               'dataFormat': 'svg', 'assetId': digest, 'md5ext': file_name,
                               'rotationCenterX': rx, 'rotationCenterY': ry})


def add_art(n, assets):
    first = len(n.target['costumes']) + 1
    chars = list(dict.fromkeys(GLYPHS))
    for char in chars:
        width = advance(char)
        outline,mark = glyph_paths(char)
        # A dark outer stroke preserves contrast across both source images.
        paths=f'<path d="{outline}"/>{mark}' if outline else ''
        body=(f'<g fill="none" stroke-linejoin="round" stroke-linecap="round" transform="translate(1.6 3)">'
              f'<g stroke="#142534" stroke-width="2.6" opacity=".65">{paths}</g>'
              f'<g stroke="#f8fbff" stroke-width="1.42">{paths}</g></g>')
        append_svg(n.target, assets, f'UI glyph [{char}]', body,
                   math.ceil(width) + 4, 18, 1.6, 9)
    ident = n.storage(GLYPH_WIDTH_LIST, True)[1]
    n.target['lists'][ident][1] = [advance(char) for char in chars]
    for name, (path, thickness) in ICONS.items():
        body = (f'<g fill="none" stroke-linecap="round" stroke-linejoin="round">'
                f'<path d="{path}" stroke="#172c3c" opacity=".7" stroke-width="{thickness+1.1}"/>'
                f'<path d="{path}" stroke="#eff8ff" stroke-width="{thickness}"/></g>')
        append_svg(n.target, assets, 'UI icon ' + name, body, 20, 20, 10, 10)
    return first


class Foreground(Native):
    """The existing SB3 emitter with a separate ID space for these scripts."""
    def __init__(self, target):
        super().__init__(target)
        self.next_id = max((int(s[len('lgpresent'):]) for s in self.blocks
                            if s.startswith('lgpresent') and s[len('lgpresent'):].isdigit()), default=0)

    def emit(self, node, parent):
        key = super().emit(node, parent)
        if hasattr(node, 'mutation'):
            self.blocks[key]['mutation'] = node.mutation
        return key

    @staticmethod
    def ids(code):
        digest = hashlib.sha256(code.encode()).hexdigest()[:16]
        return [f'lguitext{digest}p{i}' for i in range(code.count('%s'))]

    def call(self, code, *args):
        ids = self.ids(code)
        assert len(ids) == len(args), code
        node = Node('procedures_call', dict(zip(ids, args)))
        node.mutation = {'tagName': 'mutation', 'children': [], 'proccode': code,
                         'argumentids': json.dumps(ids), 'warp': 'true'}
        return node

    def define(self, code, args, body, x, y):
        ids = self.ids(code)
        prototype = Node('procedures_prototype', {key: Node('argument_reporter_string_number',
                         fields={'VALUE': [name, None]}, shadow=True) for key, name in zip(ids, args)}, shadow=True)
        prototype.mutation = {'tagName': 'mutation', 'children': [], 'proccode': code,
                              'argumentids': json.dumps(ids), 'argumentnames': json.dumps(args),
                              'argumentdefaults': json.dumps([''] * len(args)), 'warp': 'true'}
        top = self.emit(Node('procedures_definition', {'custom_block': prototype}), None)
        self.blocks[top].update(topLevel=True, x=x, y=y)
        self.blocks[top]['next'] = self.chain(body, top)[0]


def add(a,b): return op('add',a,b)
def sub(a,b): return op('subtract',a,b)
def mul(a,b): return op('multiply',a,b)
def div(a,b): return op('divide',a,b)
def eq(a,b): return op('equals',a,b)
def lt(a,b): return op('lt',a,b)
def gt(a,b): return op('gt',a,b)
def both(a,b): return op('and',a,b)
def either(a,b): return op('or',a,b)
def neg(a): return Node('operator_not', {'OPERAND': a})
def join(a,b): return op('join',a,b)
def repeat(count, body): return Node('control_repeat', {'TIMES': count, 'SUBSTACK': body})
def length(value): return Node('operator_length', {'STRING':value})
def letter(value,index): return Node('operator_letter_of',{'STRING':value,'LETTER':index})
def costume(value): return Node('looks_switchcostumeto',{'COSTUME':value})
def costume_info(kind): return Node('looks_costumenumbername', fields={'NUMBER_NAME':[kind,None]})

GLYPH = 'UI glyph metrics %s'
TEXT = 'UI text %s x %s y %s width %s align %s'
ICON = 'UI symbol %s x %s y %s'
WASH = 'UI wash x %s y %s width %s height %s tone %s'
HEADER = 'UI page title %s'
PANEL = 'UI passive caption %s'
FOREGROUND = 'UI foreground'
SIGNATURE = 'UI foreground signature'
IDENTITY = 'UI text identity %s'


def text_scripts(n, first):
    v=n.v
    desired = join('UI glyph [',join(arg('character'),']'))
    n.define(GLYPH,['character'],[
        costume(desired),
        iff(neg(eq(costume_info('name'),desired)),[costume('UI glyph [□]')]),
        n.set('UI letter advance',n.item(GLYPH_WIDTH_LIST,add(sub(costume_info('number'),first),1)))
    ],25040,400)
    # Measure only characters that fit. Stop after the first overflow, and
    # reserve the final advance for a single ellipsis at the clip boundary.
    measure=[n.call(GLYPH,letter(arg('text'),v('UI character'))),
             iff(gt(add(v('UI measured'),v('UI letter advance')),arg('width')),
                 [n.set('UI clipped',1)],
                 [n.change('UI measured',v('UI letter advance')),n.change('UI characters fit',1)]),
             n.change('UI character',1)]
    trim=[n.call(GLYPH,letter(arg('text'),v('UI characters fit'))),
          n.change('UI measured',mul(-1,v('UI letter advance'))),n.change('UI characters fit',-1)]
    drawing=[n.call(GLYPH,letter(arg('text'),v('UI character'))),
             iff(neg(eq(letter(arg('text'),v('UI character')),' ')),
                 [go(v('UI cursor x'),arg('y')),Node('pen_stamp')]),
             n.change('UI cursor x',v('UI letter advance')),n.change('UI character',1)]
    text=[n.set('UI measured',0),n.set('UI characters fit',0),n.set('UI clipped',0),n.set('UI character',1),
          Node('control_repeat_until',{'CONDITION':either(eq(v('UI clipped'),1),gt(v('UI character'),length(arg('text')))),
                                       'SUBSTACK':measure}),
          iff(eq(v('UI clipped'),1),[
              Node('control_repeat_until',{'CONDITION':either(lt(v('UI characters fit'),1),
                       neg(gt(add(v('UI measured'),advance('…')),arg('width')))), 'SUBSTACK':trim}),
              iff(neg(lt(arg('width'),advance('…'))),[n.change('UI measured',advance('…'))],
                  [n.set('UI clipped',0)])]),
          n.set('UI cursor x',arg('x')),
          iff(eq(arg('align'),'center'),[n.change('UI cursor x',div(v('UI measured'),-2))]),
          n.set('UI character',1),repeat(v('UI characters fit'),drawing),
          iff(eq(v('UI clipped'),1),[costume('UI glyph […]'),go(v('UI cursor x'),arg('y')),Node('pen_stamp')])]
    n.define(TEXT,['text','x','y','width','align'],[iff(gt(arg('width'),3),text)],31040,400)
    n.define(ICON,['name','x','y'],[costume(join('UI icon ',arg('name'))),go(arg('x'),arg('y')),Node('pen_stamp')],37040,400)


def wash_body(n):
    """Paint one visible Pen primitive for every wash, including a circle."""
    v = n.v
    x, y, width, height, tone = map(arg, ('x','y','width','height','tone'))
    reach, rise, diameter = map(v, ('UI wash reach','UI wash rise','UI wash height'))
    alpha = v('UI wash transparency')
    def ink(rgb, transparency_percent):
        return [Node('pen_setPenColorToColor',{'COLOR':rgb}),
                n.set('UI wash transparency',transparency_percent)]
    # The pen-down point and the following movement are separate native draws.
    # Start the movement with an invisible point, then paint the entire capsule
    # in one motion. A circle needs just the one visible pen-down point.
    line = [transparency(100),Node('pen_penDown'),transparency(alpha),
            go(add(x,reach),add(y,rise))]
    circle = [transparency(alpha),Node('pen_penDown')]
    body = [Node('pen_penUp'),n.set('UI wash reach',0),n.set('UI wash rise',0),
            iff(gt(width,height),[n.set('UI wash height',height),
                n.set('UI wash reach',div(sub(width,height),2))],
                [n.set('UI wash height',width),n.set('UI wash rise',div(sub(height,width),2))]),
            Node('pen_setPenSizeTo',{'SIZE':diameter}),
            iff(eq(tone,'pressed'),ink(0x7cb9ff,55),
                [iff(eq(tone,'selected'),ink(0xa7cbff,72),ink(0xe3f4ff,85))]),
            go(sub(x,reach),sub(y,rise)),iff(eq(width,height),circle,line),
            Node('pen_penUp'),transparency(0)]
    return [iff(both(gt(width,0),gt(height,0)),body)]


def wash_script(n):
    n.define(WASH,['x','y','width','height','tone'],wash_body(n),43040,400)


def case_state(n, owner, row, x,y,w,h, selected=None):
    args=[x,y,w,h]
    fallback=None if selected is None else [iff(selected,[n.call(WASH,*args,'selected')])]
    return iff(both(eq(n.v('UI pressed id'),owner),eq(n.v('UI pressed row'),row)),
               [n.call(WASH,*args,'pressed')],
               [iff(both(eq(n.v('UI hover id'),owner),eq(n.v('UI hover row'),row)),
                    [n.call(WASH,*args,'hover')],fallback)])


def add_caption_script(n):
    v=n.v
    # Passive readouts use an optional pipe after the heading for each line.
    # Keep all art within the physical panel, including during transitions.
    def paint_line():
        title=[n.call(ICON,'sidebar',add(v('UI left'),13),v('UI caption y')),
               n.call(TEXT,v('UI caption line'),add(v('UI left'),26),v('UI caption y'),
                      sub(v('UI width'),32),'left')]
        item=[n.call(ICON,'status',add(v('UI left'),13),v('UI caption y')),
              n.call(TEXT,v('UI caption line'),add(v('UI left'),26),v('UI caption y'),
                     sub(v('UI width'),32),'left')]
        return [iff(both(gt(v('UI caption y'),add(v('UI bottom'),9)),gt(v('UI width'),32)),[
                    iff(eq(v('UI caption count'),0),title,item)]),
                n.set('UI caption line',''),n.change('UI caption count',1),n.change('UI caption y',-24)]
    body=[n.set('UI caption line',''),n.set('UI caption index',1),n.set('UI caption count',0),
          n.set('UI caption y',sub(v('UI top'),18)),
          repeat(length(arg('caption')),[n.set('UI caption char',letter(arg('caption'),v('UI caption index'))),
                 iff(eq(v('UI caption char'),'|'),paint_line(),
                     [n.set('UI caption line',join(v('UI caption line'),v('UI caption char')))]),
                 n.change('UI caption index',1)]),*paint_line()]
    n.define(PANEL,['caption'],body,49040,400)
    n.define(HEADER,['path'],[n.set('UI page heading',''),n.set('UI heading index',1),
        repeat(length(arg('path')),[n.set('UI heading char',letter(arg('path'),v('UI heading index'))),
               iff(eq(v('UI heading char'),'>'),[n.set('UI page heading','')],
                   [n.set('UI page heading',join(v('UI page heading'),v('UI heading char')))]),
               n.change('UI heading index',1)])],55040,400)


def foreground_script(n):
    v=n.v
    slot=v('UI art id')
    row=v('UI art row')
    idx=n.item('UI row index',row)
    def val(name): return n.item(name,slot)
    x,y,w,h=(v('UI '+name) for name in ('cx','cy','width','height'))
    left,top,bottom=(v('UI '+name) for name in ('left','top','bottom'))
    rh=v('UI ink row step')
    button=[case_state(n,slot,0,x,y,sub(w,7),sub(h,7)),
            n.call(TEXT,val('UI label'),x,y,sub(w,14),'center')]
    headerY=v('UI head y')
    circle=both(eq(val('tw'),val('th')),eq(mul(2,val('tr')),val('tw')))
    one_symbol=both(eq(length(val('UI label')),1),neg(eq(val('UI label'),' ')))
    compact=[iff(one_symbol,[n.call(TEXT,val('UI label'),x,y,sub(w,8),'center')],
                 [n.call(ICON,'more',x,y)])]
    wide=[n.call(TEXT,val('UI label'),add(left,12),y,sub(w,39),'left'),
          iff(gt(w,40),[n.call(ICON,'down',sub(add(left,w),15),y)])]
    closed=[case_state(n,slot,0,x,y,sub(w,7),sub(h,7)),iff(circle,compact,wide)]
    nested=[n.call(HEADER,val('UI page')),n.call(ICON,'back',add(left,15),headerY),
            n.call(TEXT,v('UI page heading'),add(left,28),headerY,sub(w,38),'left')]
    root=[n.call(TEXT,val('UI label'),add(left,13),headerY,sub(w,39),'left'),
          n.call(ICON,'up',sub(add(left,w),16),headerY)]
    rowY=v('UI row center y')
    selected=both(neg(eq(val('UI selected path'),'')),
                  eq(n.item('UI row path',row),val('UI selected path')))
    row_paint=[case_state(n,slot,idx,x,rowY,sub(w,10),sub(rh,4),selected),
               n.call(TEXT,n.item('UI row label',row),add(left,14),rowY,sub(w,42),'left'),
               iff(eq(n.item('UI row role',row),'submenu'),[n.call(ICON,'next',sub(add(left,w),16),rowY)],
                   [iff(eq(n.item('UI row role',row),'more'),[n.call(ICON,'more',sub(add(left,w),16),rowY)],
                       [iff(selected,[n.call(ICON,'check',sub(add(left,w),16),rowY)])])])]
    matching_row=[n.set('UI row center y',sub(headerY,mul(idx,rh))),
                  iff(both(gt(rowY,add(bottom,9)),lt(rowY,sub(top,9))),row_paint)]
    opened=[n.set('UI head y',sub(top,div(rh,2))),
            iff(both(gt(headerY,add(bottom,9)),gt(w,39)),[
                case_state(n,slot,0,x,headerY,sub(w,10),sub(rh,4)),
                iff(eq(val('UI page'),''),root,nested)]),
            n.set('UI art row',1),repeat(n.length('UI row id'),[
                iff(eq(n.item('UI row id',row),slot),matching_row),n.change('UI art row',1)])]
    geometry=[n.set('UI cx',val('x')),n.set('UI cy',val('y')),n.set('UI width',val('w')),
              n.set('UI height',val('h')),n.set('UI ink row step',val('UI row height')),
              # Input maps a transformed pointer back into the local menu. Apply
              # the inverse map here so row artwork follows its hit target while
              # the glass is pulled without stretching the text glyph itself.
              iff(gt(val('amp'),.02),[n.set('UI width',mul(w,val('scaleX'))),
                  n.set('UI height',mul(h,val('scaleY'))),
                  n.set('UI ink row step',mul(rh,val('scaleY')))]),n.set('UI left',sub(x,div(w,2))),
              n.set('UI top',add(y,div(h,2))),n.set('UI bottom',sub(y,div(h,2)))]
    kinds=[iff(eq(val('UI kind'),'Background'),[n.call(PANEL,val('UI label'))]),
           iff(eq(val('UI kind'),'Button'),button),
           iff(eq(val('UI kind'),'Menu'),[iff(eq(val('UI open'),1),opened,closed)])]
    n.define(FOREGROUND,[],[iff(eq(v('UI view'),1),[
         Node('pen_penUp'),n.set('UI art id',1),repeat(8,[
             iff(both(eq(val('active'),1),neg(eq(val('UI kind'),''))),
                 [*geometry,iff(both(gt(w,10),gt(h,16)),kinds)]),
             n.change('UI art id',1)]),transparency(0),Node('looks_hide')])],61040,400)


def attach_display_hook(n):
    # Extend only the cache key and successful presentation tail. The glass
    # sampler, its render bounds and its native RGBA Pen work stay independent.
    v=n.v
    sig_slot=v('UI signature id')
    def token(value):
        return [n.set('UI signature value',value),
                n.set('preparedScene',join(v('preparedScene'),join(length(v('UI signature value')),
                       join(':',v('UI signature value')))))]
    slot_fields=('UI kind','UI label','UI open','UI page','UI row height','UI selected path')
    row_fields=('UI row id','UI row index','UI row label','UI row path','UI row role')
    # Scratch string equality folds case, while lookup of a costume name is
    # case-sensitive. Include actual glyph indices for labels that can be
    # displayed. This path only reads/switches hidden costumes and uses no Pen.
    n.define(IDENTITY,['text'],[n.set('UI identity index',1),
             repeat(length(arg('text')),[n.call(GLYPH,letter(arg('text'),v('UI identity index'))),
                    n.set('preparedScene',join(v('preparedScene'),join('/',costume_info('number')))),
                    n.change('UI identity index',1)])],73040,400)
    def field_token(field, index):
        value=n.item(field,index)
        extra=[n.call(IDENTITY,value)] if field in ('UI label','UI page','UI row label') else []
        return token(value)+extra
    values=[]
    for field in ('UI hover id','UI hover row','UI pressed id','UI pressed row'):
        values.extend(token(v(field)))
    values.extend([n.set('UI signature id',1),repeat(8,[
        iff(eq(n.item('active',sig_slot),1),[block for field in slot_fields
             for block in field_token(field,sig_slot)]),n.change('UI signature id',1)]),
        n.set('UI signature row',1),repeat(n.length('UI row id'),[
            *[block for field in row_fields for block in field_token(field,v('UI signature row'))],
            n.change('UI signature row',1)])])
    n.define(SIGNATURE,[],[iff(eq(v('UI view'),1),[n.set('preparedScene',join(v('preparedScene'),'UI/')),*values])],67040,400)
    render=n.definition('LG render')
    gates=[]
    for ident in n.sequence(render):
        b=n.blocks[ident]
        if b['opcode']=='control_if':
            condition=n.blocks[b['inputs']['CONDITION'][1]]
            if condition['opcode']=='operator_not':
                reporter=n.blocks[condition['inputs']['OPERAND'][1]]
                if reporter['opcode']=='operator_equals' and 'displayedScene' in str(reporter['inputs']):
                    gates.append(ident)
    if len(gates)!=1:
        raise ValueError('Expected a single prepared/displayed scene guard in LG render')
    gate=gates[0]
    n.attach(n.blocks[gate]['parent'],[n.call(SIGNATURE)],gate)
    display_writes=[key for key,b in n.blocks.items() if isinstance(b,dict)
                    and b['opcode']=='data_setvariableto' and b['fields'].get('VARIABLE',[None])[0]=='displayedScene'
                    and 'preparedScene' in str(b['inputs'])]
    if len(display_writes)!=1:
        raise ValueError('Expected a single committed frame assignment')
    assignment=display_writes[0]
    n.attach(assignment,[n.call(FOREGROUND)],n.blocks[assignment]['next'])


def apply_labels(target, assets):
    if any(c['name']=='UI glyph [A]' for c in target['costumes']):
        raise ValueError('UI foreground is already installed')
    n=Foreground(target)
    first=add_art(n,assets)
    text_scripts(n,first)
    wash_script(n)
    add_caption_script(n)
    foreground_script(n)
    attach_display_hook(n)
    return target


def patch_washes(target):
    """Upgrade a 0.4.0 target in place, preserving its foreground callers.

    Move the existing selection branch into the hover fallback and replace the
    internals of the wash helper. Its definition, blocks at each call site, and
    all of the artwork retain their original identifiers.
    """
    n = Foreground(target)
    blocks = n.blocks
    foreground = n.definition(FOREGROUND)
    wash = n.definition(WASH)
    def owns(ident, root):
        while ident and ident != root:
            ident = blocks[ident]['parent']
        return ident == root
    def tone(ident):
        b = blocks[ident]
        if b.get('opcode') != 'procedures_call' or b.get('mutation',{}).get('proccode') != WASH:
            return None
        args = json.loads(b['mutation']['argumentids'])
        value = b['inputs'][args[-1]][1]
        return value[1] if isinstance(value,list) and value[0] == 10 else None
    chosen = [key for key,b in blocks.items() if isinstance(b,dict) and tone(key)=='selected'
              and owns(key,foreground)]
    if len(chosen) != 1:
        raise ValueError('Expected a single selected-row wash in UI foreground')
    select = blocks[chosen[0]]['parent']
    selection = blocks[select]
    parent = blocks[selection['parent']]
    if selection['opcode'] != 'control_if' or selection['inputs']['SUBSTACK'][1] != chosen[0]:
        raise ValueError('Unrecognized selected-row branch')
    if selection['next']:
        # The old selected-row wash ran independently ahead of the hover/press
        # choice. Retain its condition and move its entire block into the new
        # else branch. Existing row text and its check mark are outside here.
        press_id = selection['next']
        press = blocks[press_id]
        if press['opcode']!='control_if_else' or tone(press['inputs']['SUBSTACK'][1])!='pressed':
            raise ValueError('Expected pressed-row choice after selection')
        hover_id = press['inputs']['SUBSTACK2'][1]
        hover = blocks[hover_id]
        if hover['opcode']!='control_if' or tone(hover['inputs']['SUBSTACK'][1])!='hover':
            raise ValueError('Expected a single hover-row fallback')
        if parent['next'] == select:
            parent['next'] = press_id
        else:
            incoming = [binding for key,binding in parent['inputs'].items()
                        if key.startswith('SUBSTACK') and binding[1] == select]
            if len(incoming) != 1:
                raise ValueError('Selected-row branch has no unique incoming stack')
            incoming[0][1] = press_id
        press['parent'] = selection['parent']
        selection.update(parent=hover_id,next=None)
        hover['opcode'] = 'control_if_else'
        hover['inputs']['SUBSTACK2'] = [2,select]
    elif parent['opcode']!='control_if_else' or parent['inputs'].get('SUBSTACK2',[None,None])[1]!=select:
        raise ValueError('Unrecognized selected-row fallback')
    original_body = n.sequence(wash)
    for ident in original_body:
        n.remove(ident)
    blocks[wash]['next'] = n.chain(wash_body(n),wash)[0]
    return target
