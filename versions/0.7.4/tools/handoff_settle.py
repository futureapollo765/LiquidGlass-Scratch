"""Let a collapsing submenu's shared ink settle into its real source row.

The optical sheet still merges on its first contact with the row. The title
and disclosure retain the signed spring state and keep a single paint owner
until both position and velocity settle. They can reverse during the return.
"""
from .body_ink import FACE
from .disclosure import DISCLOSURE
from .menu_handoff import GEOMETRY, OWNER, TITLE
from .menu_layers import BEGIN, KEY, PAINT, PANEL, POSE, PUSH, RESET, TOP, count, insert_before, li, mix, procs, put
from .menu_timing import SOLVE
from .motion_layout import set_socket
from .stable_pen import arg, iff
from .ui_components import UIProgram, AND, NOT, OR, abs_, add, div, eq, gt, join, length, maximum, minimum, mul, sub
from . import ui_labels as labels


EXTRA=('ink p','ink v','ink left travel','ink right travel','ink top travel')
TAIL='UI return ink to row %s'
ROW_WASH='UI restore source wash %s sheet %s'


def active(n,i):
    return OR(NOT(eq(li(n,'ink p',i),0)),NOT(eq(li(n,'ink v',i),0)))


def lookup(n, definition, opcode, key, field):
    return [idx for idx in procs(n,definition,opcode)
            if n.blocks[idx]['fields'].get(key,[None])[0]==field]


def only(items,description):
    if len(items)!=1:raise ValueError('Expected one '+description)
    return items[0]


def append(n,key,commands):
    n.attach(key,commands,n.blocks[key]['next'])


def bind_condition(n,key,condition):
    old=n.blocks[key]['inputs']['CONDITION'][1]
    n.remove(old)
    n.blocks[key]['inputs']['CONDITION']=[2,n.emit(condition,key)]


def install_record_state(n):
    b=n.blocks
    # Copy a currently saved record's optical phase/velocity at migration,
    # and maintain the additional fields with the original native list schema.
    for field in EXTRA:
        original='p' if field=='ink p' else 'v' if field=='ink v' else None
        values=n.target['lists'][n.storage('UI layer '+(original or 'owner'),True)[1]][1]
        dest=n.storage('UI layer '+field,True)[1]
        n.target['lists'][dest][1]=list(values) if original else [0]*len(values)
    reset=n.definition(RESET)
    append(n,n.sequence(reset)[-1],[n.clear('UI layer '+field) for field in EXTRA])
    push=n.definition(PUSH)
    add_record=only([k for k in lookup(n,push,'data_addtolist','LIST','UI layer p')
                     if isinstance(b[k]['inputs']['ITEM'][1],list)],'new private record')
    append(n,add_record,[n.add('UI layer '+field,0) for field in EXTRA])
    reorder=only(lookup(n,push,'data_deleteoflist','LIST','UI layer p'),'reordered private record')
    match=n.v('UI push match')
    append(n,reorder,[cmd for field in EXTRA for cmd in (
        n.add('UI layer '+field,li(n,field,match)),n.list_op('data_deleteoflist','UI layer '+field,INDEX=match))])
    begin=n.definition(BEGIN)
    delete=only(lookup(n,begin,'data_deleteoflist','LIST','UI layer p'),'retired private record')
    idx=n.v('UI prune')
    append(n,delete,[n.list_op('data_deleteoflist','UI layer '+field,INDEX=idx) for field in EXTRA])
    gate=delete
    while b[gate]['opcode']!='control_if':gate=b[gate]['parent']
    bind_condition(n,gate,AND(eq(li(n,'goal',idx),0),AND(eq(li(n,'p',idx),0),NOT(active(n,idx)))))
    # Removing or retyping the public Menu is an immediate removal of its
    # entire private tree. A hidden record must not outlive its public owner.
    cleanup=only(lookup(n,n.definition('UI input'),'data_replaceitemoflist','LIST','UI layer p'),'removed owner cleanup')
    append(n,cleanup,[put(n,field,n.v('UI private hit index'),0) for field in ('ink p','ink v')])


def install_simulation(n):
    b=n.blocks;v=n.v;i=v('UI panel step')
    solve=only([k for k in procs(n,n.definition(POSE),'procedures_call')
                if b[k]['mutation']['proccode']==SOLVE],'private spring')
    import json
    ids=json.loads(b[solve]['mutation']['argumentids'])
    set_socket(n,solve,ids[0],li(n,'ink p',i));set_socket(n,solve,ids[1],li(n,'ink v',i))
    contact=b[solve]['next']
    if (b[contact]['opcode']!='control_if' or
        b[b[contact]['inputs']['SUBSTACK'][1]]['fields'].get('VARIABLE',[None])[0]!='UI spring p'):
        raise ValueError('The 0.7.0 first-contact gate is missing')
    # Save the actual solver output before the optical surface is clamped.
    append(n,solve,[put(n,'ink p',i,v('UI spring p')),put(n,'ink v',i,v('UI spring v'))])
    # A retiring face cannot reappear when the signed caption bounces. If a
    # user reopens it before settlement, resume its physical velocity while
    # waiting for the first positive-area sample to reveal the sheet.
    bind_condition(n,contact,OR(NOT(gt(v('UI spring p'),0)),
                                AND(eq(li(n,'goal',i),0),NOT(gt(li(n,'p',i),0)))))
    geometry=n.definition(GEOMETRY);j=arg('layer')
    anchor=only(lookup(n,geometry,'data_setvariableto','VARIABLE','UI sheet growth'),'finished sheet pose')
    width_delta=div(sub(v('UI finish w'),v('UI origin w')),2)
    center_delta=sub(v('UI finish x'),v('UI origin x'))
    append(n,anchor,[
        put(n,'ink left travel',j,sub(center_delta,width_delta)),
        put(n,'ink right travel',j,add(center_delta,width_delta)),
        put(n,'ink top travel',j,add(sub(v('UI finish y'),v('UI origin y')),
                                      div(sub(v('UI finish h'),v('UI origin h')),2)))])
    stamp=only(lookup(n,n.definition(KEY),'data_changevariableby','VARIABLE','UI key panel'),'layer scene key')
    insert_before(n,stamp,[n.set('preparedScene',join(v('preparedScene'),join('/',li(n,field,v('UI key panel')))))
                           for field in ('ink p','ink v')])


def install_title(n):
    v=n.v;d=n.definition(TITLE);i=arg('layer')
    # During the tail the physical sheet stays at its source. Extend each
    # carried edge along its actual source-to-target path. These corrections
    # are zero for every sample where the sheet follows the signed spring.
    signed=v('UI title spring phase')
    difference=v('UI title edge residual')
    first=only(lookup(n,d,'data_setvariableto','VARIABLE','UI carried x'),'carried title x')
    insert_before(n,first,[
        n.set('UI title spring phase',minimum(1,li(n,'ink p',i))),
        n.set('UI title edge residual',sub(li(n,'ink p',i),maximum(0,li(n,'p',i)))),
    ])
    x,y,w,h=[li(n,k,i) for k in ('x','y','w','h')]
    sx=v('UI saved scale x');sy=v('UI saved scale y')
    positions={
        'UI carried x':add(add(sub(x,div(w,2)),mul(difference,li(n,'ink left travel',i))),
                           mix(mul(9,v('UI origin sx')),mul(14,sx),signed)),
        'UI carried y':sub(add(add(y,div(h,2)),mul(difference,li(n,'ink top travel',i))),
                           mix(div(v('UI origin h'),2),mul(div(li(n,'pitch',i),2),sy),signed)),
        'UI carried arrow x':sub(add(add(x,div(w,2)),mul(difference,li(n,'ink right travel',i))),
                                mix(mul(11,v('UI origin sx')),mul(16,sx),signed)),
    }
    for key,value in positions.items():
        setter=only(lookup(n,d,'data_setvariableto','VARIABLE',key),key)
        set_socket(n,setter,'VALUE',value)
    # Glyph orientation/scale should retrace the same slope across the row.
    # Opacity still follows its bounded material progress in the original code.
    for axis,current in (('x',sx),('y',sy)):
        name='UI ink scale '+axis
        setters=lookup(n,d,'data_setvariableto','VARIABLE',name)
        setter=only([k for k in setters if isinstance(n.blocks[k]['inputs']['VALUE'][1],str)],name)
        set_socket(n,setter,'VALUE',maximum(.001,mix(v('UI origin s'+axis),current,signed)))
    turn=only([k for k in procs(n,d,'procedures_call') if n.blocks[k]['mutation']['proccode']==DISCLOSURE],
              'shared turning disclosure')
    import json
    angle_id=json.loads(n.blocks[turn]['mutation']['argumentids'])[0]
    set_socket(n,turn,angle_id,mul(90,signed))


def tail(n):
    i=arg('layer');v=n.v
    # A nested parent can itself be dismissed. Its former child must never
    # pick up a coincident root path just because that source sheet retired.
    parent=li(n,'parent',i);o=li(n,'owner',i)
    return [n.set('UI art id',o),n.set('UI draw layer',i),n.call('UI find parent sheet %s for %s',o,parent),
            iff(OR(eq(length(parent),0),gt(v('UI origin parent'),0)),[
                n.call(FACE,'panel'),n.call(TITLE,i)])]


def row_wash(n):
    # While the shared title finishes its return the source already has its
    # regular hover/pressed/selected capsule. Paint only that capsule here.
    v=n.v;i=arg('sheet');row=arg('row')
    selected=AND(NOT(eq(n.item('UI selected path',v('UI art id')),'')),
                 eq(n.item('UI selected path',v('UI art id')),n.item('UI row path',row)))
    idx=n.item('UI row index',row)
    base=labels.case_state(n,v('UI art id'),idx,v('UI cx'),v('UI row center y'),
                          sub(v('UI width'),10),sub(v('UI ink row step'),4),selected)
    # All foreground geometry is specified in canonical body coordinates here.
    # The original 0.6 pipeline draws transformed artwork with this public helper.
    from .body_ink import WASH
    def migrate(node):
        if getattr(node,'proc',None)==labels.WASH:
            vals=list(node.inputs.values())
            return n.call(WASH,*vals)
        for key,value in node.inputs.items():
            if key.startswith('SUBSTACK'):node.inputs[key]=[migrate(cmd) for cmd in value]
        return node
    return [iff(AND(gt(i,0),NOT(gt(li(n,'p',i),.001))),[migrate(base)])]


def install_ownership(n):
    v=n.v;b=n.blocks
    # Once either part of the spring is moving, the shared title has exactly
    # one owner. A settled, invisible record hands the row back immediately.
    owner=n.definition(OWNER);idx=v('UI source owner scan')
    gate=only(procs(n,owner,'control_if'),'source-row ownership test')
    bind_condition(n,gate,AND(OR(gt(li(n,'p',idx),.001),active(n,idx)),
        AND(eq(li(n,'owner',idx),arg('owner')),
            AND(eq(li(n,'parent',idx),arg('from')),eq(li(n,'path',idx),arg('path'))))))
    panel=n.definition(PANEL)
    found=only([k for k in procs(n,panel,'procedures_call') if b[k]['mutation']['proccode']==OWNER],
               'source row lookup')
    append(n,found,[n.call(ROW_WASH,v('UI art row'),v('UI source sheet'))])
    top=n.definition(TOP)
    painter=only([k for k in procs(n,top,'procedures_call') if b[k]['mutation']['proccode']==PAINT],'layer painter')
    visible=b[painter]['parent'];i=v('UI replay panel')
    if b[visible]['opcode']!='control_if':raise ValueError('Private visibility branch changed')
    b[visible]['opcode']='control_if_else'
    b[visible]['inputs']['SUBSTACK2']=[2,n.chain([iff(active(n,i),[n.call(TAIL,i)])],visible)[0]]
    render=n.definition('LG render')
    change=only(lookup(n,render,'data_changevariableby','VARIABLE','UI damage slot'),'damage iterator')
    j=v('UI damage slot')
    # Signed top-edge travel may carry the title a few pixels beyond the
    # surface on a stage-clamped return. Restore both old and new dirty strips.
    guard=add(16,abs_(mul(li(n,'ink p',j),li(n,'ink top travel',j))))
    insert_before(n,change,[iff(AND(active(n,j),NOT(gt(li(n,'p',j),.001))),[
        n.set('strokeTop',maximum(v('strokeTop'),add(add(li(n,'y',j),div(li(n,'h',j),2)),guard))),
        n.set('strokeBottom',minimum(v('strokeBottom'),sub(sub(li(n,'y',j),div(li(n,'h',j),2)),guard)))])])


def apply_handoff_settle(target, *, studio=True):
    n=UIProgram(target,exporting=not studio)
    if TAIL in n.procs:raise ValueError('Settling handoff already installed')
    n.declare(TAIL,('layer',));n.declare(ROW_WASH,('row','sheet'))
    n.define(TAIL,tail(n),(195000,19800));n.define(ROW_WASH,row_wash(n),(195000,24300))
    install_record_state(n);install_simulation(n);install_title(n);install_ownership(n)
    return target
