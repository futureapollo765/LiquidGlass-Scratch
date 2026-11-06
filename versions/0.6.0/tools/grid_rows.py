"""Keep every calibration pixel while storing identical scanlines once.

An editable full Grid RGB list overrides the row table. The two representations
remain independently readable while a slower Scratch VM expands or packs it.
"""
from .stable_pen import Node, arg, iff
from .ui_components import UIProgram, add, sub, mul, div, floor, eq, lt, repeat, join, AND

W, H = 480, 360
SOURCE = 'Grid RGB'
PIXELS = 'LG grid pixels'
ROWS = 'LG grid rows'
READ = 'LG grid pixel %s'
EXPAND = 'LG expand grid for editing'
PACK = 'LG pack grid rows'


def mod(x, y):
    return Node('operator_mod', {'NUM1': x, 'NUM2': y})


def apply_grid_rows(target, *, studio):
    n = UIProgram(target, exporting=not studio)
    lists = target['lists']
    full = lists[n.list_ids[SOURCE]][1]
    if len(full) != W * H:
        raise ValueError('Expected the native full-resolution calibration image.')
    unique, pixels, row_table = {}, [], []
    for start in range(0, len(full), W):
        row = tuple(full[start:start + W])
        if row not in unique:
            unique[row] = len(unique) + 1
            pixels.extend(row)
        row_table.append(unique[row])
    decoded = [value for no in row_table for value in pixels[(no-1)*W:no*W]]
    if decoded != full:
        raise ValueError('Calibration image did not round-trip.')
    lists[n.storage(PIXELS, True)[1]][1] = pixels
    lists[n.storage(ROWS, True)[1]][1] = row_table
    lists[n.list_ids[SOURCE]][1] = []
    # The source has exactly three reads: raw sampling, filtered sampling,
    # and generating the blur banks. Keep their original index expressions.
    reads = [(key, b) for key,b in n.blocks.items() if isinstance(b,dict)
             and b['opcode']=='data_itemoflist' and b['fields']['LIST'][0]==SOURCE]
    n.declare(READ, ('index',))
    for key, read in reads:
        parent_id = read['parent']
        parent = n.blocks[parent_id]
        if parent['opcode'] != 'data_setvariableto' or parent['inputs']['VALUE'][1] != key:
            raise ValueError('Unrecognized calibration reader')
        # Return in color, and let this original setter copy it to its destination.
        input_binding = read['inputs'].pop('INDEX')
        from .menu_layers import insert_before
        insert_before(n, parent_id, [n.call(READ, 1)])
        call_id = parent['parent']
        call = n.blocks[call_id]
        aid = next(iter(call['inputs']))
        call['inputs'][aid] = input_binding
        if isinstance(input_binding[1], str):
            n.blocks[input_binding[1]]['parent'] = call_id
        parent['inputs']['VALUE'] = [2, n.v('color')]
        n.remove(key)
    if len(reads) != 3:
        raise ValueError('Expected all calibration reads to use the new lookup')

    n.declare(EXPAND, ())
    n.declare(PACK, ())
    v = n.v
    zero = sub(arg('index'), 1)
    row = n.item(ROWS, add(floor(div(zero, W)), 1))
    compact_index = add(add(mul(sub(row,1),W),mod(zero,W)),1)
    n.define(READ, [iff(eq(n.length(SOURCE),W*H),
        [n.set('color',n.item(SOURCE,arg('index')))], [n.set('color',n.item(PIXELS,compact_index))])], (130000,600))
    available=eq(v('LG grid working'),0)
    n.define(EXPAND,[iff(AND(available,lt(n.length(SOURCE),W*H)),[
        n.set('LG grid working',1),n.clear(SOURCE),n.set('LG expand row',1),
        repeat(H,[n.set('LG expand pixel',add(1,mul(sub(n.item(ROWS,v('LG expand row')),1),W))),
                  repeat(W,[n.add(SOURCE,n.item(PIXELS,v('LG expand pixel'))),n.change('LG expand pixel',1)]),
                  n.change('LG expand row',1)]),n.set('LG grid working',0)])],
        (130000,2800))
    row_keys = 'LG grid row keys'
    scan = 'LG grid index'
    token = 'LG grid key'
    take = [n.set(token,'/'),n.set('LG grid start',v(scan)),
            repeat(W,[n.set(token,join(v(token),join(',',n.item(SOURCE,v(scan))))),n.change(scan,1)]),
            n.set('LG grid match',n.list_op('data_itemnumoflist',row_keys,ITEM=v(token))),
            iff(eq(v('LG grid match'),0),[n.add(row_keys,v(token)),n.set('LG grid match',n.length(row_keys)),
                n.set('LG grid copy',v('LG grid start')),repeat(W,[n.add(PIXELS,n.item(SOURCE,v('LG grid copy'))),n.change('LG grid copy',1)])]),
            n.add(ROWS,v('LG grid match'))]
    n.define(PACK,[iff(AND(available,eq(n.length(SOURCE),W*H)),[n.set('LG grid working',1),
                     n.clear(PIXELS),n.clear(ROWS),n.clear(row_keys),n.set(scan,1),repeat(H,take),
                     n.clear(SOURCE),n.clear(row_keys),n.set(token,''),n.set('LG grid working',0)])],(130000,4900))
    rebuild=n.definition('LG rebuild blur %s')
    n.attach(n.sequence(rebuild)[-1], [iff(eq(arg('background'),2),[n.call(PACK)])],None)
    init=n.definition('LG initialize')
    n.attach(n.sequence(init)[-1],[n.set('LG grid working',0)],None)
