"""Extend the four existing native public blocks without replacing their call sites.

Existing argument IDs, expressions, workspace positions, and comments stay attached.
The green-flag examples and custom calls saved by a Scratch user migrate together.
"""
import hashlib
import json
from .stable_pen import arg, iff, op
from .ui_components import UIProgram

NAMES = ('tint color', 'transparency', 'brightness', 'blur')
SUFFIX = ''.join(' ' + name + ' %s' for name in NAMES)
PRESETS = {
    'Glass': ('#748397', 84, 2, 6),
    'Button': ('#51647D', 80, 3, 2),
    'Menu': ('#414B59', 66, 4, 6),
    'Background': ('#48586E', 72, 5, 12),
}
FINISHES = {'Frosted': PRESETS['Menu'], 'Clear': ('#FFFFFF', 100, 0, 0),
            'Smoked': ('#292A32', 46, -12, 12)}
DEMO_VARS = ('Menu color', 'Menu transparency', 'Menu brightness', 'Menu blur')
DEMO_MENU = 'Background>Photo|Background>Grid|Detail>Fine|Detail>Balanced|Detail>Fast'
DEMO_CHOICES = '|'.join('Menu finish>' + name for name in FINISHES)


def public_inputs(target, *, studio):
    from .glass_material import MATERIAL
    n = UIProgram(target, exporting=not studio)
    blocks = n.blocks
    short = {name: next(code for code in n.procs if code.startswith(name + ' %s '))
             for name in PRESETS}
    if any(code.endswith(SUFFIX) for code in short.values()):
        raise ValueError('The material interface is already present.')
    templates = {}
    owner_of = {}
    for name, code in short.items():
        definition = n.definition(code)
        owner_of[definition] = name
        proto = blocks[definition]['inputs']['custom_block'][1]
        templates[code] = (name, definition, proto)

    def owner(key):
        while key:
            if key in owner_of:
                return owner_of[key]
            key = blocks[key].get('parent')
        return None

    for code,(name,definition,protoid) in templates.items():
        proto = blocks[protoid]
        m = proto['mutation']
        aids = ['lgmatarg' + hashlib.sha256((name + ':' + field).encode()).hexdigest()[:14] for field in NAMES]
        m['argumentids'] = json.dumps([*json.loads(m['argumentids']), *aids], separators=(',', ':'))
        m['argumentnames'] = json.dumps([*json.loads(m['argumentnames']), *NAMES], separators=(',', ':'))
        m['argumentdefaults'] = json.dumps([*json.loads(m['argumentdefaults']), *map(str,PRESETS[name])], separators=(',', ':'))
        m['proccode'] = code + SUFFIX
        if proto['inputs'] or proto.get('shadow'):
            for aid,field in zip(aids,NAMES):
                reporter = arg(field)
                reporter.shadow = True
                proto['inputs'][aid] = [1, n.emit(reporter,protoid)]
        for key,call in list(blocks.items()):
            if not isinstance(call,dict) or call['opcode']!='procedures_call' or call['mutation']['proccode']!=code:
                continue
            call['mutation'].update(proccode=code+SUFFIX, argumentids=m['argumentids'])
            forwarded = name=='Glass' and owner(key) in ('Menu','Button','Background')
            demo_menu = False
            if name=='Menu' and studio:
                orig = json.loads(m['argumentids'])
                choice = call['inputs'][orig[9]]
                if choice == [1,[10,DEMO_MENU]]:
                    choice[1][1] += '|' + DEMO_CHOICES
                    demo_menu = True
            for aid,field,val,vname in zip(aids,NAMES,PRESETS[name],DEMO_VARS):
                shadow = [10,str(val)]
                if forwarded:
                    call['inputs'][aid] = [3,n.emit(arg(field),key),shadow]
                elif demo_menu:
                    call['inputs'][aid] = [3,n.v(vname),shadow]
                else:
                    call['inputs'][aid] = [1,shadow]
        if name=='Glass':
            n.attach(n.sequence(definition)[-1], [n.call(MATERIAL,n.v('id'),*[arg(field) for field in NAMES])],None)
    if studio:
        # Only Studio's provided Options example reads these four variables.
        # Other calls have real editable literal values and remain independent.
        def assign(preset):
            return [n.set('Menu finish',preset),*[n.set(name,value) for name,value in zip(DEMO_VARS,FINISHES[preset])]]
        code = n.definition('LG initialize')
        n.attach(n.sequence(code)[-1], assign('Frosted'), None)
        code = n.definition('UI demo action')
        n.attach(n.sequence(code)[-1], [
            iff(op('equals',n.v('UI fired'),1),[iff(op('equals',n.v('UI action'),'Menu finish>'+p),assign(p)) for p in FINISHES]),
            iff(op('equals',n.item('UI page',3),'Menu finish'), [
                n.replace('UI selected path',3,op('join','Menu finish>',n.v('Menu finish')))])], None)
