"""Grow each private menu from its source row and carry that row's original ink.

The child sheet, its header label, and the disclosure arrow read the same source
bounds and the same spring. Parent rows paint their own content until a child
takes ownership. While the child is visible it is the only painter of that title.
"""
from . import ui_labels as labels
from .disclosure import DISCLOSURE
from .menu_layers import (PANEL, POSE, PRIVATE, PUSH, SHADE, clamp1, count, ghost,
                          insert_before, li, mix, procs, put)
from .motion_layout import contains, set_socket
from .stable_pen import arg, iff
from .ui_components import (AND, NOT, OR, UIProgram, abs_, add, div, eq, gt, length,
                            lt, maximum, minimum, mul, repeat, sub)

SOURCE='UI read source capsule %s parent %s row %s'
PARENT='UI find parent sheet %s for %s'
GEOMETRY='UI grow sheet %s owner %s width %s radius %s'
OWNER='UI source row owner %s path %s from %s'
TITLE='UI carry source row %s'
COAT='UI carry source capsule color %s'


def source(n):
    v=n.v;o=arg('owner');parent=arg('parent');row=arg('row')
    def slot(name):return n.item(name,o)
    def above(name):return li(n,name,parent)
    root=[
        n.set('UI origin x',slot('x')),n.set('UI origin cy',slot('y')),
        n.set('UI origin screen w',mul(slot('w'),slot('scaleX'))),
        n.set('UI origin screen h',mul(slot('h'),slot('scaleY'))),
        n.set('UI origin layout w',slot('UI expanded width')),
        n.set('UI origin layout h',slot('UI expanded height')),
        n.set('UI origin pitch',slot('UI row height')),
        n.set('UI origin alpha',mul(mul(clamp1(slot('UI menu open fade')),slot('UI root page fade')),
                                   sub(1,mul(.55,slot('UI menu dim')))))]
    private=[
        n.set('UI origin x',above('x')),n.set('UI origin cy',above('y')),
        n.set('UI origin screen w',above('w')),n.set('UI origin screen h',above('h')),
        n.set('UI origin layout w',minimum(440,add(slot('UI menu panel width'),8))),
        n.set('UI origin layout h',minimum(300,mul(add(above('rows'),1),above('pitch')))),
        n.set('UI origin pitch',above('pitch')),
        n.set('UI origin alpha',mul(mul(clamp1(above('p')),above('fade')),sub(1,mul(.52,above('dim')))))]
    sx=v('UI origin sx');sy=v('UI origin sy');rh=v('UI origin pitch')
    return [iff(gt(parent,0),private,root),
        iff(NOT(gt(v('UI origin layout w'),0)),[n.set('UI origin layout w',v('UI origin screen w'))]),
        iff(NOT(gt(v('UI origin layout h'),0)),[n.set('UI origin layout h',v('UI origin screen h'))]),
        n.set('UI origin sx',div(v('UI origin screen w'),maximum(.001,v('UI origin layout w')))),
        n.set('UI origin sy',div(v('UI origin screen h'),maximum(.001,v('UI origin layout h')))),
        n.set('UI origin y',add(v('UI origin cy'),mul(sy,sub(div(v('UI origin layout h'),2),mul(add(row,.5),rh))))),
        # These are the same insets as the native pressed/hover/selected wash.
        n.set('UI origin w',maximum(.01,mul(sub(v('UI origin layout w'),10),sx))),
        n.set('UI origin h',maximum(.01,mul(sub(rh,4),sy))),
        n.set('UI origin r',div(minimum(v('UI origin w'),v('UI origin h')),2))]


def parent_sheet(n):
    v=n.v;i=v('UI origin search')
    return [n.set('UI origin parent',0),iff(gt(length(arg('path')),0),[
        n.set('UI origin search',1),repeat(count(n),[
            iff(AND(eq(li(n,'owner',i),arg('owner')),eq(li(n,'path',i),arg('path'))),[
                n.set('UI origin parent',i)]),n.change('UI origin search',1)])])]


def geometry(n):
    v=n.v;o=arg('owner');i=arg('layer');p=v('UI sheet growth')
    dim=li(n,'dim',i);align=n.item('UI menu alignment',o)
    sw=v('UI origin w');sh=v('UI origin h');sx=v('UI origin x');sy=v('UI origin y')
    tw=v('UI finish w');th=v('UI finish h');tx=v('UI finish x');ty=v('UI finish y')
    return [n.call(PARENT,o,li(n,'parent',i)),n.call(SOURCE,o,v('UI origin parent'),li(n,'row',i)),
        n.set('UI finish w',sub(minimum(440,maximum(16,add(abs_(arg('width')),8))),mul(10,dim))),
        n.set('UI finish h',sub(minimum(300,mul(add(li(n,'rows',i),1),li(n,'pitch',i))),mul(6,dim))),
        n.set('UI finish x',sx),n.set('UI finish y',sub(add(sy,div(sh,2)),div(th,2))),
        iff(contains(align,'left'),[n.set('UI finish x',sub(add(sx,div(sw,2)),div(tw,2)))]),
        iff(contains(align,'right'),[n.set('UI finish x',add(sub(sx,div(sw,2)),div(tw,2)))]),
        iff(contains(align,'top'),[n.set('UI finish y',add(sub(sy,div(sh,2)),div(th,2)))]),
        n.change('UI finish x',mul(4,dim)),n.change('UI finish y',mul(6,dim)),
        *n.clip('UI finish x',add(-238,div(tw,2)),sub(238,div(tw,2))),
        *n.clip('UI finish y',add(-178,div(th,2)),sub(178,div(th,2))),
        n.set('UI sheet growth',maximum(0,li(n,'p',i))),
        # A common fraction for all four edges keeps the selected row fixed at
        # the origin, even when a requested final panel meets a stage boundary.
        put(n,'w',i,maximum(.01,mix(sw,tw,p))),put(n,'h',i,maximum(.01,mix(sh,th,p))),
        put(n,'x',i,mix(sx,tx,p)),put(n,'y',i,mix(sy,ty,p)),
        put(n,'r',i,maximum(0,minimum(div(minimum(li(n,'w',i),li(n,'h',i)),2),
                                      mix(v('UI origin r'),maximum(0,arg('radius')),p)))),
        put(n,'x',i,minimum(sub(240,div(li(n,'w',i),2)),maximum(add(-240,div(li(n,'w',i),2)),li(n,'x',i)))),
        put(n,'y',i,minimum(sub(180,div(li(n,'h',i),2)),maximum(add(-180,div(li(n,'h',i),2)),li(n,'y',i))))]


def row_owner(n):
    v=n.v;i=v('UI source owner scan')
    return [n.set('UI source sheet',0),n.set('UI source owner scan',1),
        repeat(count(n),[iff(AND(gt(li(n,'p',i),.001),AND(eq(li(n,'owner',i),arg('owner')),
           AND(eq(li(n,'parent',i),arg('from')),eq(li(n,'path',i),arg('path'))))),[
               n.set('UI source sheet',i)]),n.change('UI source owner scan',1)])]


def shared_title(n):
    v=n.v;i=arg('layer');o=li(n,'owner',i);phase=clamp1(li(n,'p',i))
    # The row's original leading/trailing padding is measured from the source
    # capsule. Its title and disclosure never acquire a second competing owner.
    cx=li(n,'x',i);cy=li(n,'y',i);w=li(n,'w',i);h=li(n,'h',i)
    parent=v('UI origin parent');currentSx=v('UI saved scale x');currentSy=v('UI saved scale y')
    x=v('UI carried x');y=v('UI carried y');j=v('UI label lookup')
    scan=[iff(AND(eq(n.item('UI row id',j),o),AND(eq(n.item('UI row layer',j),parent),
                       eq(n.item('UI row path',j),li(n,'path',i)))),[
        n.set('UI carried label',n.item('UI row label',j))]),n.change('UI label lookup',1)]
    # Change only the transform around this run. Other child rows retain the
    # child face's independent affine text layout and its reveal opacity.
    saved=[n.set('UI saved '+k,v(name)) for k,name in
           [('center x','UI cx'),('center y','UI cy'),('scale x','UI ink scale x'),
            ('scale y','UI ink scale y'),('ink alpha','UI ink opacity')]]
    restore=[n.set(name,v('UI saved '+k)) for k,name in
           [('center x','UI cx'),('center y','UI cy'),('scale x','UI ink scale x'),
            ('scale y','UI ink scale y'),('ink alpha','UI ink opacity')]]
    originalAlpha=v('UI origin alpha')
    finalAlpha=mul(li(n,'fade',i),sub(1,mul(.52,li(n,'dim',i))))
    return [*saved,n.call(PARENT,o,li(n,'parent',i)),n.call(SOURCE,o,parent,li(n,'row',i)),
        n.call(labels.HEADER,li(n,'path',i)),n.set('UI carried label',v('UI page heading')),
        n.set('UI label lookup',1),repeat(n.length('UI row id'),scan),
        n.set('UI carried x',add(sub(cx,div(w,2)),mix(mul(9,v('UI origin sx')),mul(14,currentSx),phase))),
        n.set('UI carried y',sub(add(cy,div(h,2)),mix(div(v('UI origin h'),2),mul(div(li(n,'pitch',i),2),currentSy),phase))),
        n.set('UI carried arrow x',sub(add(cx,div(w,2)),mix(mul(11,v('UI origin sx')),mul(16,currentSx),phase))),
        n.set('UI carried width',mix(mul(sub(v('UI origin layout w'),42),v('UI origin sx')),
                                     mul(sub(v('UI width'),42),currentSx),phase)),
        n.set('UI ink scale x',mix(v('UI origin sx'),currentSx,phase)),
        n.set('UI ink scale y',mix(v('UI origin sy'),currentSy,phase)),
        n.set('UI ink opacity',mix(originalAlpha,finalAlpha,phase)),
        ghost(mul(100,sub(1,v('UI ink opacity')))),
        n.set('UI cx',x),n.set('UI cy',y),
        n.call(labels.TEXT,v('UI carried label'),x,y,div(v('UI carried width'),maximum(.001,v('UI ink scale x'))),'left'),
        n.set('UI cx',v('UI carried arrow x')),n.call(DISCLOSURE,mul(90,phase)),
        *restore,ghost(mul(100,sub(1,v('UI ink opacity'))))]


def coat(n):
    v=n.v;i=arg('layer');p=clamp1(li(n,'p',i))
    # Blend the released row wash into the emerging material in the retained
    # surface, so it takes the same rounded outline and never draws over itself.
    # When closing away from its source, release the final hover ink as well.
    a=v('UI transition coat');total=v('UI transition coverage')
    held=AND(eq(v('UI hover id'),li(n,'owner',i)),AND(eq(v('UI hover row'),li(n,'row',i)),
            eq(li(n,'path',v('UI hover layer')),li(n,'parent',i))))
    return [n.set('UI transition coat',mul(.15,sub(1,p))),
        iff(AND(eq(li(n,'goal',i),0),NOT(held)),[n.set('UI transition coat',mul(a,minimum(1,mul(4,p))))]),
        n.set('UI transition coverage',add(p,a)),
        n.set('UI coat mix',div(a,maximum(.000001,total)))]


def erase_chain(n,first,until=None):
    while first and first!=until:
        following=n.blocks[first]['next'];n.remove(first);first=following
    if until and first!=until:raise ValueError('Missing expected end of private menu stack')


def set_branch(n,gate,name,nodes,tail=None):
    b=n.blocks;old=b[gate]['inputs'][name][1]
    erase_chain(n,old,tail)
    first,last=n.chain(nodes,gate);b[gate]['inputs'][name]=[2,first]
    if tail:b[last]['next']=tail;b[tail]['parent']=last


def migrate_pose(n):
    b=n.blocks;push=n.definition(PUSH);pose=n.definition(POSE)
    candidates=[]
    for k in procs(n,push,'control_if_else'):
        first=b[k]['inputs']['SUBSTACK'][1]
        if b[first].get('fields',{}).get('VARIABLE',[None])[0]=='UI new x':candidates.append(k)
    if len(candidates)!=1:raise ValueError('Missing original submenu seed')
    gate=candidates[0];first=b[gate]['inputs']['SUBSTACK'][1]
    while b[first]['opcode']!='data_addtolist':first=b[first]['next']
    set_branch(n,gate,'SUBSTACK',[n.call(SOURCE,arg('owner'),arg('parent'),arg('row'))],first)
    k=first
    fields={'UI layer '+f:'UI origin '+f for f in ('x','y','w','h','r')}
    found=set()
    while k:
        name=b[k].get('fields',{}).get('LIST',[None])[0]
        if name in fields:
            set_socket(n,k,'ITEM',n.v(fields[name]));found.add(name)
        k=b[k]['next']
    if set(fields)!=found:raise ValueError('Missing private capsule state')
    candidates=[]
    for k in procs(n,pose,'control_if'):
        substack=b[k]['inputs']['SUBSTACK'][1]
        if b[substack].get('fields',{}).get('VARIABLE',[None])[0]=='UI base x':
            value=b[substack]['inputs']['VALUE'][1]
            if isinstance(value,str) and b[value]['fields'].get('LIST',[None])[0]=='x':candidates.append(k)
    if len(candidates)!=1:raise ValueError('Missing private panel geometry pass')
    set_branch(n,candidates[0],'SUBSTACK',[n.call(GEOMETRY,n.v('UI panel step'),arg('owner'),arg('width'),arg('radius'))])


def migrate_faces(n):
    b=n.blocks;panel=n.definition(PANEL);v=n.v
    private_title=next(key for key in procs(n,panel,'procedures_call') if b[key]['mutation']['proccode']==labels.HEADER)
    gate=b[private_title]['parent']
    if b[gate]['inputs']['SUBSTACK2'][1]!=private_title:raise ValueError('Unrecognized private header layout')
    set_branch(n,gate,'SUBSTACK2',[n.call(TITLE,v('UI draw layer'))])
    row_mid=next(key for key in procs(n,panel,'data_setvariableto') if b[key]['fields']['VARIABLE'][0]=='UI row center y')
    row_gate=b[row_mid]['next']
    before=b[row_gate]['inputs']['CONDITION'][1]
    search=n.call(OWNER,v('UI art id'),n.item('UI row path',v('UI art row')),
                  li(n,'path',v('UI draw layer')))
    # Scratch's list item zero returns the empty string, the root path.
    insert_before(n,row_gate,[search])
    wrapper=n.emit(AND(eq(v('UI source sheet'),0),eq(1,1)),row_gate)
    tmp=b[wrapper]['inputs']['OPERAND2'][1];n.remove(tmp)
    b[wrapper]['inputs']['OPERAND2']=[2,before];b[before]['parent']=wrapper
    b[row_gate]['inputs']['CONDITION']=[2,wrapper]


def migrate_coat(n):
    b=n.blocks;d=n.definition(SHADE)
    rgb=next(k for k in procs(n,d,'data_setvariableto') if b[k]['fields']['VARIABLE'][0]=='UI ink RGB')
    coverage=next(k for k in procs(n,d,'data_setvariableto') if b[k]['fields']['VARIABLE'][0]=='UI pixel coverage')
    prep=n.definition(PRIVATE)
    start=next(k for k in procs(n,prep,'data_setvariableto') if b[k]['fields']['VARIABLE'][0]=='UI raster left')
    insert_before(n,start,[n.call(COAT,n.v('UI raster pane'))])
    insert_before(n,rgb,[iff(gt(n.v('UI coat mix'),.000001),[
        n.set(ch,mix(n.v(ch),tone,n.v('UI coat mix'))) for ch,tone in [('R',227),('G',244),('B',255)]])])
    set_socket(n,coverage,'VALUE',mul(clamp1(sub(.5,div(n.v('UI distance'),n.v('UI private q')))),n.v('UI transition coverage')))


def apply_menu_handoff(target,*,studio=True):
    n=UIProgram(target,exporting=not studio)
    if SOURCE in n.procs:raise ValueError('Source row handoff is already installed')
    if DISCLOSURE not in n.procs:raise ValueError('Install the native disclosure rotation helper first')
    helpers=((SOURCE,('owner','parent','row'),source),(PARENT,('owner','path'),parent_sheet),
             (GEOMETRY,('layer','owner','width','radius'),geometry),
             (OWNER,('owner','path','from'),row_owner),(TITLE,('layer',),shared_title),
             (COAT,('layer',),coat))
    for code,names,_ in helpers:n.declare(code,names)
    for j,(code,_,emit) in enumerate(helpers):n.define(code,emit(n),(173000+(j%3)*8000,1000+(j//3)*6800))
    migrate_pose(n);migrate_faces(n);migrate_coat(n)
    return target
