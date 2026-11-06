"""Restore EffOnly's native inward displacement for public and nested glass."""
from .menu_layers import SHADE, procs, replace_body
from .glass_material import SAMPLE_BG, packed, rgb
from .grid_rows import READ
from .panel_optics import PUBLIC_NORMAL
from .stable_pen import arg, iff
from .ui_components import UIProgram, AND, OR, add, div, eq, floor, gt, lt, math, maximum, minimum, mul, square, sub

PUBLIC_SHADER='LG shade %s %s %s'
SOURCE_LINEAR='LG blend source texels'
SOURCE_TAP='LG source texel %s weight %s'


def public_field(n):
    v=n.v
    cell=arg('cell')
    # Use stage distances, rather than a fixed number of low-resolution cells.
    # Centered differences of the merged field also cover connections between
    # surfaces, which have no single component center.
    body=[n.set('UI normal cells',maximum(1,minimum(16,math('ceiling',div(mul(.20,v('band')),v('q')))))),
          n.set('UI normal gx',sub(cell,add(mul(floor(div(sub(cell,1),v('cols'))),v('cols')),1))),
          n.set('UI normal gy',floor(div(sub(cell,1),v('cols')))),
          n.set('UI normal row count',floor(div(n.length('field'),v('cols'))))]
    for axis,stride,count in [('x',1,'cols'),('y',v('cols'),'UI normal row count')]:
        coordinate=v('UI normal g'+axis)
        body.extend([n.set('UI neg span',minimum(v('UI normal cells'),coordinate)),
                     n.set('UI pos span',minimum(v('UI normal cells'),sub(sub(v(count),1),coordinate)))])
        negative=sub(cell,mul(v('UI neg span'),stride))
        positive=add(cell,mul(v('UI pos span'),stride))
        delta=sub(n.item('field',positive),n.item('field',negative))
        if axis=='y':delta=mul(-1,delta)
        width=maximum(1,mul(v('q'),add(v('UI neg span'),v('UI pos span'))))
        body.append(n.set('normal'+axis.upper(),div(delta,width)))
    body.extend([n.set('normalLen',math('sqrt',add(square(v('normalX')),square(v('normalY'))))),
                 n.set('opticalGain',minimum(1,mul(2,v('normalLen')))),
                 n.set('opticalGain',mul(square(v('opticalGain')),sub(3,mul(2,v('opticalGain'))))),
                 n.set('UI normal divisor',maximum(.00001,v('normalLen'))),
                 n.set('normalX',div(v('normalX'),v('UI normal divisor'))),
                 n.set('normalY',div(v('normalY'),v('UI normal divisor'))),
                 n.set('refraction',mul(mul(div(square(maximum(0,add(v('band'),v('D')))),10),
                                            v('shadeDistortion')),v('opticalGain')))])
    return body


def source_tap(n):
    v=n.v
    return [iff(gt(arg('weight'),0),[
        iff(eq(v('matReadBG'),2),[n.call(READ,arg('index'))],[n.set('color',n.item('Original RGB',arg('index')))]),
        *[n.change(ch,mul(rgb(v('color'),ch),arg('weight'))) for ch in 'RGB']])]


def source_linear(n):
    v=n.v
    x=v('matTexX');y=v('matTexY');fx=v('UI source fx');fy=v('UI source fy')
    base=v('UI source texel')
    body=[n.set('UI source fx',sub(x,floor(x))),n.set('UI source fy',sub(y,floor(y))),
          n.set('UI source texel',add(1,add(floor(x),mul(480,floor(y))))),
          *[n.set(ch,0) for ch in 'RGB']]
    for dx,dy,weight in [(0,0,mul(sub(1,fx),sub(1,fy))),(1,0,mul(fx,sub(1,fy))),
                         (0,1,mul(sub(1,fx),fy)),(1,1,mul(fx,fy))]:
        body.append(n.call(SOURCE_TAP,add(base,dx+480*dy),weight))
    return [*body,n.set('color',packed(v('R'),v('G'),v('B')))]


def install_sampling(n):
    n.declare(SOURCE_TAP,('index','weight'))
    n.declare(SOURCE_LINEAR,())
    n.define(SOURCE_TAP,source_tap(n),(151000,19000))
    n.define(SOURCE_LINEAR,source_linear(n),(151000,21500))
    # Blur below the first filtered radius blends this exact full-resolution
    # source with the radius-two bank. At larger radii the original source
    # contributes no weight, so its extra taps can be skipped.
    store_blue=next(k for k in n.sequence(n.definition(SAMPLE_BG))
                    if n.blocks[k]['fields'].get('VARIABLE',[None])[0]=='B')
    fractional=OR(gt(n.v('matTexX'),floor(n.v('matTexX'))),gt(n.v('matTexY'),floor(n.v('matTexY'))))
    n.attach(store_blue,[iff(AND(lt(arg('blur'),2),fractional),[n.call(SOURCE_LINEAR)])],n.blocks[store_blue]['next'])
    # Retain the cheap direct read for zero-displacement, zero-blur pixels.
    shader=n.sequence(n.definition(PUBLIC_SHADER))
    sample=next(k for k in shader if n.blocks[k]['opcode']=='control_if_else')
    key=n.blocks[sample]['inputs']['CONDITION'][1]
    n.remove(key)
    n.blocks[sample]['inputs']['CONDITION']=[2,n.emit(OR(gt(n.v('shadeMatBlur'),0),
        gt(math('abs',n.v('refraction')),0)),sample)]

def apply_reference_refraction(target,*,studio=True):
    n=UIProgram(target,exporting=not studio)
    if any(name=='UI normal row count' for name,_ in target['variables'].values()):
        raise ValueError('Reference displacement is already installed')
    replace_body(n,PUBLIC_NORMAL,public_field(n))
    # All public roles and the raw Glass API use the same normal and scalar
    # profile. Retain the original material sampler and all downstream shading.
    definition=n.definition(PUBLIC_SHADER)
    chain=n.sequence(definition)
    start=next(i for i,k in enumerate(chain) if n.blocks[k]['fields'].get('VARIABLE',[None])[0]=='normalX')
    end=next(i for i in range(start,len(chain)) if n.blocks[chain[i]]['opcode']=='control_if_else')
    old=chain[start:end]
    if len(old)<5 or not any(n.blocks[k]['opcode']=='control_if' for k in old):
        raise ValueError('Unexpected 0.6.x optical sampling sequence')
    n.attach(chain[start-1],[n.set('band',n.v('shadeBand')),n.call(PUBLIC_NORMAL,arg('cell'))],chain[end])
    for k in old:n.remove(k)

    # Keep the smooth analytic rounded-box normal, lower-surface bilinear
    # sampling and the undimmed, softly transmitted lower layer from 0.6.0.
    # Drop only the two scalar limit operations between the source's original
    # quadratic displacement and the final coordinated X/Y lookup.
    private=n.definition(SHADE)
    source=next(k for k in procs(n,private,'data_setvariableto') if n.blocks[k]['fields']['VARIABLE'][0]=='UI source x')
    offset=n.blocks[source]['parent']
    bounded=[]
    while n.blocks[offset]['fields'].get('VARIABLE',[None])[0]=='UI lens offset' or n.blocks[offset]['opcode']=='control_if':
        bounded.insert(0,offset);offset=n.blocks[offset]['parent']
    if len(bounded)!=4 or n.blocks[bounded[0]]['fields'].get('VARIABLE',[None])[0]!='UI lens offset':
        raise ValueError('Unexpected private quadratic profile or saturation blocks')
    n.blocks[bounded[0]]['next']=source;n.blocks[source]['parent']=bounded[0]
    for k in bounded[1:]:n.remove(k)
    install_sampling(n)
    return target
