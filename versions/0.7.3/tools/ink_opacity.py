"""Apply opacity once to the complete transformed glyph or disclosure symbol.

The editable source vector strokes define a compact unsigned distance atlas.
Partial-opacity printing samples the whole glyph through its inverse affine
transform. Each stage pixel is stamped once with the composited face/outline
color and the group's alpha, including occlusion by a higher sheet.
"""
import math

from . import ui_labels as labels
from .body_ink import PATH, STYLES, VECTORS
from .menu_layers import COVER, clamp1, count, ghost, li
from .stable_pen import Node, arg, go, iff
from .ui_components import (UIProgram, AND, OR, NOT, abs_, add, div, eq, floor, gt, join,
                            letter, lt, maximum, minimum, mul, repeat, rnd, sub)

GRID = 3
QUANTA = 16
LEVELS = 32
STEP = .5
MAX_NATIVE_ERROR = .09
ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyz!#$%&()*+,-./:;<=>?@[]^_{}~'
MASK = 'UI stamp group opacity'
ROW = 'UI sample ink row'
CELL = 'UI sample glyph ink'
FIELD = 'UI read glyph distance'
ROUTE = 'UI composite transformed ink'
NATIVE = 'UI stamp close affine ink'
TILES = 'UI ink sample '
NAMES = {
    'left':'UI atlas left', 'top':'UI atlas top', 'cols':'UI atlas columns',
    'rows':'UI atlas height', 'start':'UI atlas first row','palette':'UI ink palette',
}
ROW_IDS = 'UI glyph row indices'
ROW_DATA = 'UI glyph distance rows'
SYMBOLS = 'UI distance digits'


def palette(target, assets, foreground, outline):
    """Opaque squares whose drawable quads meet without any overlap."""
    first = len(target['costumes'])+1
    for k in range(LEVELS+1):
        color=0
        for shift in (16,8,0):
            lo=(outline>>shift)&255;hi=(foreground>>shift)&255
            color=(color<<8) | round(lo+(hi-lo)*k/LEVELS)
        name=f'{TILES}{foreground:06x}/{outline:06x}/{k}'
        labels.append_svg(target,assets,name,
            f'<rect width="8" height="8" fill="#{color:06x}"/>',
            8,8,4,4)
    return first


def sample_rows(data,width,row_bank,all_rows,row_indices):
    vertices=[]
    for pos in range(0,len(data),7):
        vertices.append((data[pos]=='1',int(data[pos+1:pos+4])/32-15,int(data[pos+4:pos+7])/32-15))
    segments=[]
    for prev,cur in zip(vertices,vertices[1:]):
        if cur[0]:
            x,y=prev[1:];dx=cur[1]-x;dy=cur[2]-y
            segments.append((x,y,dx,dy,1/(dx*dx+dy*dy) if dx or dy else 0))
    if not segments:return (0,0,0,0,0)
    pad=width/2+1.5
    left=math.floor((min(v[1] for v in vertices)-pad)*GRID)
    right=math.ceil((max(v[1] for v in vertices)+pad)*GRID)
    bottom=math.floor((min(v[2] for v in vertices)-pad)*GRID)
    top=math.ceil((max(v[2] for v in vertices)+pad)*GRID)
    start=len(row_indices)+1
    # The distance is the minimum over the entire outline, so joints and
    # crossings occupy the same mask as the interiors of the two strokes.
    for iy in range(top,bottom-1,-1):
        py=iy/GRID
        distances=[]
        for ix in range(left,right+1):
            px=ix/GRID
            r2=10000
            for x,y,dx,dy,inv in segments:
                rx=px-x;ry=py-y
                t=min(1,max(0,(rx*dx+ry*dy)*inv))
                e=rx-t*dx;f=ry-t*dy;r2=min(r2,e*e+f*f)
            distances.append(ALPHABET[min(len(ALPHABET)-1,round(math.sqrt(r2)*QUANTA))])
        row=''.join(distances)
        if row not in row_bank:
            row_bank[row]=len(all_rows)+1;all_rows.append(row)
        row_indices.append(row_bank[row])
    return (left/GRID,top/GRID,right-left+1,top-bottom+1,start)


def build_atlas(n,assets):
    def read(name):return n.target['lists'][n.storage(name,True)[1]][1]
    def store(name,values):n.target['lists'][n.storage(name,True)[1]][1]=values
    paths=read(VECTORS); styles=[read(k) for k in STYLES]
    palettes={};row_bank={};rows=[];indices=[];entries={k:[] for k in NAMES}
    for i,data in enumerate(paths):
        values=(0,0,0,0,0)
        first=0
        if data:
            values=sample_rows(data,styles[1][i],row_bank,rows,indices)
            colors=(styles[2][i],styles[3][i])
            if colors not in palettes:palettes[colors]=palette(n.target,assets,*colors)
            first=palettes[colors]
        for key,val in zip(('left','top','cols','rows','start','palette'),(*values,first)):
            entries[key].append(val)
    for key,values in entries.items():store(NAMES[key],values)
    store(ROW_IDS,indices);store(ROW_DATA,rows);store(SYMBOLS,list(ALPHABET))


def ceil(value):
    return Node('operator_mathop',{'NUM':value},{'OPERATOR':['ceiling',None]})


def square(value):return mul(value,value)


def root(value):return Node('operator_mathop',{'NUM':value},{'OPERATOR':['sqrt',None]})


def grid_floor(x,step):return mul(step,floor(div(x,step)))


def grid_ceil(x,step):return mul(step,ceil(div(x,step)))


def emit_mask(n,step=STEP):
    v=n.v;i=v('UI path index');sx=v('UI ink scale x');sy=v('UI ink scale y')
    cx=v('UI letter world x');cy=v('UI letter world y');c=v('UI mask cosine');s=v('UI mask sine')
    left=v('UI mask left');top=v('UI mask top');cols=v('UI mask columns');height=v('UI mask rows')
    # Rotate about the original costume center before scaling, exactly as the
    # source vector painter does. A conservative screen-space bounding box
    # keeps per-pixel sampling confined to this one glyph.
    bounds=[n.set('UI mask mid local x',add(left,div(sub(cols,1),2*GRID))),
            n.set('UI mask mid local y',sub(top,div(sub(height,1),2*GRID))),
            n.set('UI mask mid x',add(cx,mul(sx,add(mul(c,v('UI mask mid local x')),mul(s,v('UI mask mid local y')))))),
            n.set('UI mask mid y',add(cy,mul(sy,sub(mul(c,v('UI mask mid local y')),mul(s,v('UI mask mid local x')))))),
            n.set('UI mask half x',mul(sx,div(add(mul(abs_(c),sub(cols,1)),mul(abs_(s),sub(height,1))),2*GRID))),
            n.set('UI mask half y',mul(sy,div(add(mul(abs_(s),sub(cols,1)),mul(abs_(c),sub(height,1))),2*GRID))),
            n.set('UI mask x0',add(step/2,maximum(-240,grid_floor(sub(v('UI mask mid x'),v('UI mask half x')),step)))),
            n.set('UI mask x1',sub(minimum(240,grid_ceil(add(v('UI mask mid x'),v('UI mask half x')),step)),step/2)),
            n.set('UI mask y',sub(minimum(180,grid_ceil(add(v('UI mask mid y'),v('UI mask half y')),step)),step/2)),
            n.set('UI mask y1',add(step/2,maximum(-180,grid_floor(sub(v('UI mask mid y'),v('UI mask half y')),step))))]
    reads=[]
    for var,key in [('left','left'),('top','top'),('columns','cols'),('rows','rows'),('first','start'),('palette','palette')]:
        reads.append(n.set('UI mask '+var,n.item(NAMES[key],i)))
    return [*reads,iff(AND(gt(v('UI mask palette'),0),AND(gt(sx,.001),gt(sy,.001))),[
        n.set('UI mask cosine',1),n.set('UI mask sine',0),
        iff(eq(v('UI rotating chevron'),1),[n.set('UI mask cosine',v('UI chevron cos')),n.set('UI mask sine',v('UI chevron sin'))]),
        n.set('UI mask face radius',div(n.item(STYLES[0],i),2)),
        n.set('UI mask outer radius',div(n.item(STYLES[1],i),2)),
        n.set('UI mask shadow alpha',n.item(STYLES[4],i)),
        n.set('UI mask glyph alpha',v('UI ink opacity')),
        *bounds,
        # Scratch clamps at the moment size is set, not on costume switch. Set
        # it on the original full backdrop first. Each following opaque square
        # then owns one disjoint half-pixel quad even on a high-resolution pen.
        labels.costume('Reference photo'),Node('looks_setsizeto',{'SIZE':100*step/8}),
        labels.costume(v('UI mask palette')),
        n.set('UI mask selected',v('UI mask palette')),n.set('UI mask row cached',-1),
        n.set('UI mask check cover',gt(count(n),v('UI draw layer'))),
        repeat(maximum(0,add(1,div(sub(v('UI mask y'),v('UI mask y1')),step))),[n.call(ROW),n.change('UI mask y',-step)]),
        labels.costume(i),Node('looks_setsizeto',{'SIZE':100}),ghost(mul(100,sub(1,v('UI ink opacity')))),
        go(cx,cy)])]


def emit_row(n,step=STEP):
    v=n.v;sx=v('UI ink scale x');sy=v('UI ink scale y');c=v('UI mask cosine');s=v('UI mask sine')
    dx=div(sub(v('UI mask x0'),v('UI letter world x')),sx)
    dy=div(sub(v('UI mask y'),v('UI letter world y')),sy)
    # Two affine increments advance along a whole screen row. On ordinary
    # nonrotated letters the same two atlas rows are reused for every sample.
    return [n.set('UI mask x',v('UI mask x0')),
        n.set('UI grid x',mul(GRID,sub(sub(mul(c,dx),mul(s,dy)),v('UI mask left')))),
        n.set('UI grid y',mul(GRID,sub(v('UI mask top'),add(mul(s,dx),mul(c,dy))))),
        n.set('UI grid step x',div(mul(GRID*step,c),sx)),n.set('UI grid step y',div(mul(-GRID*step,s),sx)),
        repeat(maximum(0,add(1,div(sub(v('UI mask x1'),v('UI mask x0')),step))),[
            iff(AND(AND(NOT(lt(v('UI grid x'),0)),lt(v('UI grid x'),sub(v('UI mask columns'),1))),
                    AND(NOT(lt(v('UI grid y'),0)),lt(v('UI grid y'),sub(v('UI mask rows'),1)))),[n.call(CELL)]),
            n.change('UI mask x',step),n.change('UI grid x',v('UI grid step x')),n.change('UI grid y',v('UI grid step y'))])]


def sample_digit(n,row,index):
    # Quantized distance digits are case-insensitively distinct in Scratch.
    return sub(n.list_op('data_itemnumoflist',SYMBOLS,ITEM=letter(index,row)),1)


def read_field(n):
    v=n.v;ix=v('UI grid column');iy=v('UI grid row');fx=v('UI grid fx');fy=v('UI grid fy')
    row1=v('UI mask upper row');row2=v('UI mask lower row')
    a,b,c,d=(v('UI sample '+x) for x in 'abcd')
    reads=[n.set('UI mask upper row',n.item(ROW_DATA,n.item(ROW_IDS,add(v('UI mask first'),iy)))),
           n.set('UI mask lower row',n.item(ROW_DATA,n.item(ROW_IDS,add(add(v('UI mask first'),iy),1)))),
           n.set('UI mask row cached',iy)]
    return [n.set('UI grid column',floor(v('UI grid x'))),n.set('UI grid row',floor(v('UI grid y'))),
        n.set('UI grid fx',sub(v('UI grid x'),ix)),n.set('UI grid fy',sub(v('UI grid y'),iy)),
        iff(NOT(eq(iy,v('UI mask row cached'))),reads),
        *[n.set('UI sample '+k,sample_digit(n,row,add(ix,offset)))
          for k,row,offset in [('a',row1,1),('b',row1,2),('c',row2,1),('d',row2,2)]],
        n.set('UI dist upper',add(a,mul(fx,sub(b,a)))),n.set('UI dist lower',add(c,mul(fx,sub(d,c)))),
        n.set('UI mask distance',div(add(v('UI dist upper'),mul(fy,sub(v('UI dist lower'),v('UI dist upper')))),QUANTA))]


def emit_cell(n):
    v=n.v;c=v('UI mask cosine');s=v('UI mask sine')
    a,b,cc,d=(v('UI sample '+x) for x in 'abcd');fy=v('UI grid fy')
    gx=v('UI mask grad x');gy=v('UI mask grad y');dist=v('UI mask distance');foot=v('UI mask filter')
    shape=v('UI mask face');coverage=v('UI mask coverage')
    # An analytic one-pixel filter based on the distance gradient preserves
    # thin antialiased contours even during diagonal rotation or strong squash.
    deriv=[n.set('UI mask grad x',mul(GRID/QUANTA,add(sub(b,a),mul(fy,sub(sub(d,cc),sub(b,a)))))),
           n.set('UI mask grad y',mul(-GRID/QUANTA,sub(v('UI dist lower'),v('UI dist upper')))),
           n.set('UI mask filter',maximum(.22,mul(.64,root(add(
               square(div(add(mul(c,gx),mul(s,gy)),v('UI ink scale x'))),
               square(div(sub(mul(c,gy),mul(s,gx)),v('UI ink scale y')))))))),
           n.set('UI mask face',clamp1(add(.5,div(sub(v('UI mask face radius'),dist),foot)))),
           n.set('UI mask outer',clamp1(add(.5,div(sub(v('UI mask outer radius'),dist),foot)))),
           n.set('UI mask coverage',add(shape,mul(mul(sub(1,shape),v('UI mask shadow alpha')),v('UI mask outer'))))]
    visible=[n.set('UI mask pixel alpha',mul(coverage,v('UI mask glyph alpha'))),
             iff(eq(v('UI mask check cover'),1),[n.call(COVER,v('UI mask x'),v('UI mask y'),0),
                 n.set('UI mask pixel alpha',mul(v('UI mask pixel alpha'),sub(1,v('UI front cover'))))]),
             iff(gt(v('UI mask pixel alpha'),.001),[
                n.set('UI mask color',add(v('UI mask palette'),rnd(div(mul(LEVELS,shape),coverage)))),
                iff(NOT(eq(v('UI mask color'),v('UI mask selected'))),[
                    labels.costume(v('UI mask color')),n.set('UI mask selected',v('UI mask color'))]),
                ghost(mul(100,sub(1,v('UI mask pixel alpha')))),
                go(v('UI mask x'),v('UI mask y')),Node('pen_stamp')])]
    return [n.call(FIELD),*deriv,iff(gt(coverage,.001),visible)]


def emit_native(n,default_rotation):
    v=n.v
    # In this branch the biggest affine-to-uniform displacement is bounded by
    # MAX_NATIVE_ERROR, below the source path flattening tolerance. The native
    # vector gives full display-resolution curves and exactly one ghosted stamp.
    turn=eq(v('UI rotating chevron'),1)
    set_style=lambda style:Node('motion_setrotationstyle',fields={'STYLE':[style,None]})
    direction=lambda degrees:Node('motion_pointindirection',{'DIRECTION':degrees})
    return [n.set('UI opacity saved heading',Node('motion_direction')),
            iff(turn,[set_style('all around'),direction(add(90,v('UI opacity angle')))]),
            Node('looks_setsizeto',{'SIZE':mul(50,add(v('UI ink scale x'),v('UI ink scale y')))}),
            go(v('UI letter world x'),v('UI letter world y')),ghost(mul(100,sub(1,v('UI ink opacity')))),Node('pen_stamp'),
            iff(turn,[direction(v('UI opacity saved heading')),set_style(default_rotation)]),
            Node('looks_setsizeto',{'SIZE':100})]


def route(n):
    v=n.v;i=v('UI path index');j=v('UI overlap probe')
    x=v('UI letter world x');y=v('UI letter world y');radius=v('UI glyph support')
    sx=v('UI ink scale x');sy=v('UI ink scale y')
    left=n.item(NAMES['left'],i);top=n.item(NAMES['top'],i)
    ex=maximum(abs_(left),abs_(add(left,div(sub(n.item(NAMES['cols'],i),1),GRID))))
    ey=maximum(abs_(top),abs_(sub(top,div(sub(n.item(NAMES['rows'],i),1),GRID))))
    rx=abs_(sub(li(n,'x',j),x));ry=abs_(sub(li(n,'y',j),y))
    overlaps=AND(lt(rx,add(div(li(n,'w',j),2),v('UI overlap reach'))),
                 lt(ry,add(div(li(n,'h',j),2),v('UI overlap reach'))))
    return [n.set('UI glyph support',root(add(square(ex),square(ey)))),
            n.set('UI overlap reach',add(1,mul(maximum(sx,sy),radius))),
            n.set('UI overlap found',0),n.set('UI overlap probe',add(v('UI draw layer'),1)),
            repeat(sub(count(n),v('UI draw layer')),[
                iff(AND(gt(li(n,'p',j),.001),overlaps),[n.set('UI overlap found',1)]),n.change('UI overlap probe',1)]),
            iff(AND(eq(v('UI overlap found'),0),AND(gt(minimum(sx,sy),.76),
                       lt(mul(mul(.5,abs_(sub(sx,sy))),radius),MAX_NATIVE_ERROR))),
                [n.call(NATIVE)],[n.call(MASK)])]


def apply_ink_opacity(target,assets,*,studio=True):
    n=UIProgram(target,exporting=not studio)
    if MASK in n.procs:raise ValueError('Single-cover artwork is already installed.')
    build_atlas(n,assets)
    routines=((MASK,emit_mask),(ROW,emit_row),(CELL,emit_cell),(FIELD,read_field),
              (NATIVE,lambda n:emit_native(n,target.get('rotationStyle',"don't rotate"))),(ROUTE,route))
    for name,_ in routines:n.declare(name,())
    for j,(name,body) in enumerate(routines):n.define(name,body(n),(190000+j*7300,1000))
    old=n.definition(PATH)
    previous=n.blocks[old]['next']
    condition=OR(lt(n.v('UI ink opacity'),.999999),gt(count(n),n.v('UI draw layer')))
    branch=n.emit(iff(condition,[n.call(ROUTE)]),old)
    n.blocks[branch]['opcode']='control_if_else'
    n.blocks[branch]['inputs']['SUBSTACK2']=[2,previous];n.blocks[previous]['parent']=branch
    n.blocks[old]['next']=branch
    disclosure='UI disclosure facing %s'
    if disclosure in n.procs:
        d=n.definition(disclosure);n.attach(d,[n.set('UI opacity angle',arg('angle'))],n.blocks[d]['next'])
    return target
