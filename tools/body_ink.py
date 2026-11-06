"""Attach text, icons, and highlight positions to each glass face's local space.

Scratch stamps scale uniformly. At matching horizontal and vertical scale we use
the original SVG costume. At different scales the same costume's two ink colors
are painted from the original editable vector paths. This gives both letters and their
spacing the face's independent horizontal and vertical transformation.
"""
import copy
import json

from . import ui_labels as labels
from .body_ink_atlas import atlas_rows, glyph_art
from .body_ink_path import vector_art
from .menu_layers import COVER, LAUNCH, PANEL, STAMP, count, insert_before, li, procs
from .stable_pen import Node, arg, go, iff, transparency
from .ui_components import (UIProgram, AND, NOT, OR, abs_, add, div, eq, floor, gt,
                            join, length, letter, lt, math, maximum, minimum, mul,
                            repeat, sub, until)

FACE = 'UI artwork face %s'
AT = 'UI artwork at x %s y %s'
DRAW = 'UI draw costume on face'
SCAN = 'UI draw stretched artwork'
SPAN = 'UI artwork span left %s right %s color %s'
WASH = 'UI artwork wash x %s y %s width %s height %s tone %s'
ROWS = 'UI artwork contours'
MAPS = 'UI artwork row maps'
PATH = 'UI draw transformed path'
PASS = 'UI artwork path size %s color %s opacity %s'
VECTORS = 'UI artwork paths'
STYLES = ('UI face stroke','UI outline stroke','UI face RGB','UI outline RGB','UI outline opacity')


def face_frame(n):
    """Lay a face out in its reference dimensions, around the rendered center."""
    v=n.v
    slot=v('UI art id')
    layer=v('UI draw layer')
    def public(name): return n.item(name,slot)
    def pane(name): return li(n,name,layer)
    def size(w,h):
        return [n.set('UI width',w), n.set('UI height',h)]
    root_geometry=[
        n.set('UI cx',public('x')), n.set('UI cy',public('y')),
        n.set('UI face screen w',mul(public('w'),public('scaleX'))),
        n.set('UI face screen h',mul(public('h'),public('scaleY'))),
        n.set('UI ink row step',public('UI row height')),
        iff(eq(arg('face'),'panel'), size(public('UI expanded width'),public('UI expanded height')),
            [iff(eq(arg('face'),'background'),size(v('UI face screen w'),v('UI face screen h')),
                 size(public('UI resting width'),public('UI resting height')))])]
    child_geometry=[
        n.set('UI cx',pane('x')),n.set('UI cy',pane('y')),
        n.set('UI face screen w',pane('w')),n.set('UI face screen h',pane('h')),
        n.set('UI ink row step',pane('pitch')),
        *size(minimum(440,add(public('UI menu panel width'),8)),
              minimum(300,mul(add(pane('rows'),1),pane('pitch'))))]
    return [iff(gt(layer,0),child_geometry,root_geometry),
        # Allows a saved old UI state to render until its first registration.
        iff(NOT(gt(v('UI width'),0)),[n.set('UI width',v('UI face screen w'))]),
        iff(NOT(gt(v('UI height'),0)),[n.set('UI height',v('UI face screen h'))]),
        n.set('UI ink scale x',div(v('UI face screen w'),maximum(.001,v('UI width')))),
        n.set('UI ink scale y',div(v('UI face screen h'),maximum(.001,v('UI height')))),
        n.set('UI left',sub(v('UI cx'),div(v('UI width'),2))),
        n.set('UI top',add(v('UI cy'),div(v('UI height'),2))),
        n.set('UI bottom',sub(v('UI cy'),div(v('UI height'),2)))]


def affine(n,point,axis):
    center=n.v('UI c'+axis)
    return add(center,mul(sub(point,center),n.v('UI ink scale '+axis)))


def place(n):
    v=n.v
    return [n.set('UI letter world x',affine(n,arg('x'),'x')),
            n.set('UI letter world y',affine(n,arg('y'),'y')),
            go(v('UI letter world x'),v('UI letter world y'))]


def draw(n):
    v=n.v
    # The VM caps the minimum size of very small SVG costumes. Render narrow
    # faces through the scanline path even if their two scales happen to match.
    same=AND(lt(abs_(sub(v('UI ink scale x'),v('UI ink scale y'))),.00001),gt(v('UI ink scale x'),.76))
    size=lambda val:Node('looks_setsizeto',{'SIZE':val})
    normal=[iff(eq(v('UI ink scale x'),1),[n.call(STAMP)],
                [size(mul(100,v('UI ink scale x'))),n.call(STAMP),size(100)])]
    return [iff(same,normal,[n.set('UI path index',labels.costume_info('number')),
            n.set('UI path data',n.item(VECTORS,v('UI path index'))),
            iff(gt(length(v('UI path data')),0),[n.call(PATH)],[n.call(SCAN)] if SCAN in n.procs else None)])]


def decimal_pair(string,start):
    return add(0,join(letter(start,string),letter(add(start,1),string)))


def row_number(string,at):
    return add(0,join(join(letter(at,string),letter(add(at,1),string)),
                      join(letter(add(at,2),string),letter(add(at,3),string))))


def scan(n):
    v=n.v
    sx,sy=v('UI ink scale x'),v('UI ink scale y')
    y=v('UI stroke y')
    at=v('UI run char')
    runs=v('UI contour row')
    # The source viewport is x = -12..12 and y = +11..-11 relative to the
    # costume's rotation center. Each row references its unique list of runs.
    # Iterate destination rows so compressed text never overpaints a screen row.
    run=[n.call(SPAN,sub(div(decimal_pair(runs,add(at,1)),4),12),
                sub(div(decimal_pair(runs,add(at,3)),4),12),letter(at,runs)),
         n.change('UI run char',5)]
    row=[n.set('UI sample row',floor(mul(2,sub(11,div(sub(y,v('UI letter world y')),sy))))),
         iff(AND(NOT(lt(v('UI sample row'),0)),lt(v('UI sample row'),44)),[
             n.set('UI map char',add(1,mul(v('UI sample row'),4))),
             n.set('UI contour row',n.item(ROWS,row_number(v('UI letter map'),v('UI map char')))),
             n.set('UI run char',1),repeat(div(length(runs),5),run)]),
         n.change('UI stroke y',-1)]
    return [n.set('UI letter map',n.item(MAPS,labels.costume_info('number'))),
            iff(AND(gt(length(v('UI letter map')),0),AND(gt(sx,.001),gt(sy,.001))),[
                n.set('UI stroke y',floor(add(v('UI letter world y'),mul(11,sy)))),
                n.set('UI last y',math('ceiling',sub(v('UI letter world y'),mul(11,sy)))),
                Node('pen_penUp'),Node('pen_setPenSizeTo',{'SIZE':1}),
                repeat(add(1,sub(y,v('UI last y'))),row),
                transparency(0)])]


def span(n):
    v=n.v
    left,right,y = v('UI span left'),v('UI span right'),v('UI stroke y')
    length_=sub(right,left)
    # Our dark/light contours partition the source. A translucent shadow is
    # painted exactly once per run. Fractional-width runs cover one sample in
    # proportion to their length. The transparent initial Pen point avoids a
    # brighter/darker cap at the start of each line.
    dark=[Node('pen_setPenColorToColor',{'COLOR':0x142534}),n.set('UI run opacity',.65)]
    light=[Node('pen_setPenColorToColor',{'COLOR':0xf8fbff}),n.set('UI run opacity',1)]
    point=[go(div(add(left,right),2),y),
           transparency(sub(100,mul(100,mul(length_,v('UI run opacity'))))),Node('pen_penDown')]
    line=[go(add(left,.5),y),transparency(100),Node('pen_penDown'),
          transparency(sub(100,mul(100,v('UI run opacity')))),go(sub(right,.5),y)]
    return [n.set('UI span left',add(v('UI letter world x'),mul(arg('left'),v('UI ink scale x')))),
            n.set('UI span right',add(v('UI letter world x'),mul(arg('right'),v('UI ink scale x')))),
            iff(eq(arg('color'),1),dark,light),
            n.set('UI run opacity',mul(v('UI ink opacity'),v('UI run opacity'))),
            iff(gt(count(n),v('UI draw layer')),[
                n.call(COVER,div(add(left,right),2),y,0),
                n.set('UI run opacity',mul(v('UI run opacity'),sub(1,v('UI front cover'))))]),
            iff(gt(v('UI run opacity'),.001),[iff(lt(length_,1),point,line),Node('pen_penUp')])]


def integer3(string,i):
    return add(0,join(letter(i,string),join(letter(add(i,1),string),letter(add(i,2),string))))


def path_plot(n):
    v=n.v
    slot=v('UI path index')
    # Source strokes with the same SVG materials share one coherent pen pass.
    # Apply the face transform to every control-point approximation.
    return [Node('pen_penUp'),n.call(PASS,n.item(STYLES[1],slot),n.item(STYLES[3],slot),
                    mul(v('UI ink opacity'),n.item(STYLES[4],slot))),
            n.call(PASS,n.item(STYLES[0],slot),n.item(STYLES[2],slot),v('UI ink opacity')),
            transparency(0)]


def path_pass(n):
    v=n.v;at=v('UI vertex');src=v('UI path data')
    # A circle swept along a transformed path has the correct two parallel
    # edges when its diameter is scaled by |det A| / |A*tangent|. This
    # retains an independently transformed line thickness and contour.
    draw_segment=[n.set('UI delta x',sub(v('UI local x'),v('UI prev local x'))),
        n.set('UI delta y',sub(v('UI local y'),v('UI prev local y'))),
        n.set('UI segment src',add(mul(v('UI delta x'),v('UI delta x')),mul(v('UI delta y'),v('UI delta y')))),
        n.set('UI screen dx',mul(v('UI delta x'),v('UI ink scale x'))),
        n.set('UI screen dy',mul(v('UI delta y'),v('UI ink scale y'))),
        n.set('UI segment dst',add(mul(v('UI screen dx'),v('UI screen dx')),mul(v('UI screen dy'),v('UI screen dy')))),
        iff(gt(v('UI segment dst'),.000001),[
            n.set('UI stroke size',mul(mul(mul(arg('size'),v('UI ink scale x')),v('UI ink scale y')),
                    math('sqrt',div(v('UI segment src'),v('UI segment dst'))))),
            n.set('UI run opacity',mul(arg('opacity'),minimum(1,v('UI stroke size')))),
            iff(gt(count(n),v('UI draw layer')),[
                n.call(COVER,div(add(v('UI vertex x'),v('UI prev x')),2),div(add(v('UI vertex y'),v('UI prev y')),2),0),
                n.set('UI run opacity',mul(v('UI run opacity'),sub(1,v('UI front cover'))))]),
            iff(gt(v('UI run opacity'),.001),[
                Node('pen_setPenSizeTo',{'SIZE':maximum(1,v('UI stroke size'))}),
                go(v('UI prev x'),v('UI prev y')),transparency(100),Node('pen_penDown'),
                transparency(sub(100,mul(100,v('UI run opacity')))),
                go(v('UI vertex x'),v('UI vertex y')),Node('pen_penUp')])])]
    plot=[n.set('UI local x',sub(div(integer3(src,add(at,1)),32),15)),
          n.set('UI local y',sub(div(integer3(src,add(at,4)),32),15)),
          n.set('UI vertex x',add(v('UI letter world x'),mul(v('UI local x'),v('UI ink scale x')))),
          n.set('UI vertex y',add(v('UI letter world y'),mul(v('UI local y'),v('UI ink scale y')))),
          iff(eq(letter(at,src),1),draw_segment),
          n.set('UI prev x',v('UI vertex x')),n.set('UI prev y',v('UI vertex y')),
          n.set('UI prev local x',v('UI local x')),n.set('UI prev local y',v('UI local y')),
          n.change('UI vertex',7)]
    return [Node('pen_setPenColorToColor',{'COLOR':arg('color')}),n.set('UI vertex',1),
            repeat(div(length(src),7),plot)]


def convert_call(n,key,code):
    """Keep a native call and its existing reporter blocks, updating its signature."""
    block=n.blocks[key]
    old=json.loads(block['mutation']['argumentids'])
    new=n.procs[code]
    new_ids=json.loads(new['argumentids'])
    if len(old)!=len(new_ids): raise ValueError('Unexpected number of UI helper arguments')
    block['inputs']={right:block['inputs'][left] for left,right in zip(old,new_ids)}
    block['mutation']={k:copy.deepcopy(new[k]) for k in ('tagName','children','proccode','argumentids','warp')}


def calls(n,owner,code):
    return [k for k in procs(n,n.definition(owner),'procedures_call') if n.blocks[k]['mutation']['proccode']==code]


def launcher_symbol(n):
    """Keep a circular launcher's symbol during its crossfade into the menu."""
    circular='UI artwork circular launcher'
    register=next(code for code in n.procs if code.startswith('Menu %s '))
    root=n.definition(register)
    slot=n.v('UI slot')
    shape=arg('launcher');w=n.item('UI resting width',slot);h=n.item('UI resting height',slot)
    circle=OR(eq(shape,3),OR(eq(shape,'circle'),eq(shape,'circular')))
    round_ends=OR(eq(shape,2),OR(eq(shape,'capsule'),NOT(lt(mul(2,arg('radius')),w))))
    n.attach(n.sequence(root)[-1],[n.replace(circular,slot,OR(circle,AND(eq(w,h),round_ends)))],None)
    n.target['lists'][n.storage(circular,True)[1]][1]=[0]*8
    face=n.definition(LAUNCH)
    replaced=0
    for key in procs(n,face,'control_if_else'):
        old=n.blocks[key]['inputs']['CONDITION'][1];b=n.blocks[old]
        if b['opcode']!='operator_and':continue
        def names(k):
            block=n.blocks[k];items={block.get('fields',{}).get('LIST',[None])[0]}
            for value in block['inputs'].values():
                if isinstance(value[1],str):
                    items.update(names(value[1]))
            return items
        if {'tw','th','tr'}.issubset(names(old)):
            n.remove(old)
            n.blocks[key]['inputs']['CONDITION']=[2,n.emit(eq(n.item(circular,n.v('UI art id')),1),key)]
            replaced+=1
    if replaced!=1:raise ValueError('Unrecognized circular launcher face')


def install_face(n):
    # The old foreground computes stage bounds for its broad visibility gate.
    # Prepare canonical layout only once inside the branch that actually paints.
    fg=n.definition(labels.FOREGROUND)
    choices={}
    for k in procs(n,fg,'control_if'):
        condition=n.blocks[k]['inputs']['CONDITION'][1]
        if not isinstance(condition,str):continue
        test=n.blocks[condition]
        values=[(val[1][1] if isinstance(val[1],list) and val[1][0]==10 else None)
                for val in test.get('inputs',{}).values()]
        if test['opcode']=='operator_equals' and 'Button' in values:
            choices['button']=n.blocks[k]['inputs']['SUBSTACK'][1]
        if test['opcode']=='operator_equals' and 'Background' in values:
            choices['background']=n.blocks[k]['inputs']['SUBSTACK'][1]
    if set(choices)!= {'button','background'}: raise ValueError('Could not locate both foreground faces.')
    for face,k in choices.items():insert_before(n,k,[n.call(FACE,face)])
    for face,code in [('launcher',LAUNCH),('panel',PANEL)]:
        d=n.definition(code)
        n.attach(d,[n.call(FACE,face)],n.blocks[d]['next'])
    for owner in (labels.TEXT,labels.ICON):
        for k in procs(n,n.definition(owner),'motion_gotoxy'):
            b=n.blocks[k]
            ids=json.loads(n.procs[AT]['argumentids'])
            b['inputs']={ids[0]:b['inputs']['X'],ids[1]:b['inputs']['Y']}
            b['opcode']='procedures_call'
            b['mutation']={key:copy.deepcopy(n.procs[AT][key]) for key in ('tagName','children','proccode','argumentids','warp')}
        for k in calls(n,owner,STAMP):convert_call(n,k,DRAW)
    for owner in (labels.FOREGROUND,LAUNCH,PANEL):
        for k in calls(n,owner,labels.WASH):convert_call(n,k,WASH)


def apply_body_ink(target,assets,*,studio=True):
    n=UIProgram(target,exporting=not studio)
    if FACE in n.procs:raise ValueError('Body-space artwork is already installed.')
    art=glyph_art(target)
    traces={}
    fallback=[]
    for c in art:
        try:traces[c['name']]=vector_art(c,assets[c['md5ext']])
        except ValueError:fallback.append(c)
    helpers=[(FACE,['face'],face_frame),(AT,['x','y'],place),(DRAW,[],draw),
             (PATH,[],path_plot),
             (PASS,['size','color','opacity'],path_pass),
             (WASH,['x','y','width','height','tone'],lambda n:[n.call(labels.WASH,
                      affine(n,arg('x'),'x'),affine(n,arg('y'),'y'),mul(arg('width'),n.v('UI ink scale x')),
                      mul(arg('height'),n.v('UI ink scale y')),arg('tone'))])]
    if fallback:helpers += [(SCAN,[],scan),(SPAN,['left','right','color'],span)]
    for code,names,_ in helpers:n.declare(code,names)
    for j,(code,_,builder) in enumerate(helpers):n.define(code,builder(n),(134000+(j%3)*9000,1200+(j//3)*7000))
    for i,name in enumerate((VECTORS,*STYLES)):
        target['lists'][n.storage(name,True)[1]][1]=[
            traces[c['name']][i] if c['name'] in traces else '' for c in target['costumes']]
    if fallback:
        contours,maps=atlas_rows({'costumes':fallback},assets)
        by_name={c['name']:index for c,index in zip(fallback,maps)}
        for name,values in [(ROWS,contours),(MAPS,[by_name.get(c['name'],'') for c in target['costumes']])]:
            target['lists'][n.storage(name,True)[1]][1]=values
    # An isolated direct call from the editor has the identity transform.
    for axis in 'xy':target['variables'][n.storage('UI ink scale '+axis)[1]][1]=1
    install_face(n)
    launcher_symbol(n)
    return target
