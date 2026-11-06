"""Smooth the refraction field at rounded corners and across a rear pane's edge.

Keep shape coverage from the exact signed distance. The optical normal is a
separate field. A sharp switch between two closest sides can pull samples from
opposite ends of a menu despite the silhouette itself being continuous.
"""
from .stable_pen import Node, arg, iff
from .ui_components import (
    UIProgram, add, sub, mul, div, lt, gt, eq, AND, NOT, maximum, minimum,
    abs_, square, floor, math, repeat, rnd,
)
from .menu_layers import SHADE, TAP, PRIVATE, COMPOSITE, replace_body, insert_before, li, unpack, procs

PRIVATE_NORMAL = 'UI continuous pane normal %s x %s y %s'
PUBLIC_NORMAL = 'UI continuous glass normal cell %s'
TEXEL = 'UI accumulate lower pixel %s weight %s'
TRANSFER = 'UI pass lower light rgb %s coverage %s softness %s'
LIGHT = 'UI lower light'
LIGHT_RGB = 'UI pane source color'
LIGHT_ALPHA = 'UI pane source softness'


def bounded_offset(offset, band):
    # Saturate smoothly. A high-contrast parent edge cannot be folded back
    # across the entire child when the physical rim is only a few pixels wide.
    limit = maximum(.5, mul(.55, band))
    return div(mul(offset, limit), add(limit, abs_(offset)))


def private_normal(n):
    v=n.v
    layer=arg('layer')
    # Smooth positive parts of the two box coordinates. At a corner they
    # both contribute instead of choosing either horizontal or vertical.
    # Signed coordinates fade through zero at each centerline.
    spread=v('UI corner span')
    body=[n.set('UI corner span',maximum(1,mul(.19,v('UI lens band'))))]
    for axis in ('x','y'):
        coordinate=v('UI distance '+axis)
        delta=sub(arg(axis),li(n,axis,layer))
        body.extend([n.set('UI axis weight '+axis,mul(.5,add(coordinate,
            math('sqrt',add(square(coordinate),square(spread)))))),
            n.set('UI axis sign '+axis,div(delta,math('sqrt',add(square(delta),mul(.25,square(spread))))))])
    body.append(n.set('UI normal magnitude',math('sqrt',add(
        add(square(v('UI axis weight x')),square(v('UI axis weight y'))),mul(.12,square(spread))))))
    for axis in ('x','y'):
        body.append(n.set('UI normal '+axis,div(mul(v('UI axis weight '+axis),v('UI axis sign '+axis)),v('UI normal magnitude'))))
    return body


def public_normal(n):
    v=n.v;cell=arg('cell');span=v('UI normal cells')
    # Sample the existing merged distance field over a few stage pixels.
    # This works for touching components as well as individual rounded boxes.
    body=[n.set('UI normal cells',maximum(1,minimum(6,math('ceiling',div(mul(.18,v('band')),v('q')))))),
          n.set('UI normal gx',Node('operator_mod',{'NUM1':sub(cell,1),'NUM2':v('cols')})),
          n.set('UI normal gy',floor(div(sub(cell,1),v('cols'))))]
    for axis,steps,center,total in [('x',1,'UI normal gx','cols'),('y',v('cols'),'UI normal gy','rows')]:
        body.extend([n.set('UI neg span',minimum(span,v(center))),
                     n.set('UI pos span',minimum(span,sub(sub(v(total),1),v(center))))])
        plus=add(cell,mul(v('UI pos span'),steps)); minus=sub(cell,mul(v('UI neg span'),steps))
        difference=sub(n.item('field',plus),n.item('field',minus))
        if axis=='y':difference=mul(-1,difference)
        body.append(n.set('normal'+axis.upper(),div(difference,
            maximum(1,mul(v('q'),add(v('UI pos span'),v('UI neg span')))))))
    body.append(n.set('refraction',bounded_offset(mul(div(square(maximum(0,add(v('band'),v('D')))),10),v('shadeDistortion')),v('band'))))
    return body


def texel(n):
    v=n.v;a=v('UI tap a');rgb=v('UI tap RGB');word=v('UI tap word')
    return [iff(gt(arg('weight'),0),[
        n.set('UI tap word',n.item(LIGHT,arg('index'))),
        iff(NOT(lt(word,0)),[n.set('UI tap RGB',floor(div(word,2))),
            n.set('UI tap a',mul(sub(word,mul(2,rgb)),arg('weight'))),
            n.change('UI tap alpha',a),
            *[n.change('UI tap '+ch,mul(a,unpack(rgb,ch))) for ch in 'RGB']])])]


def bilinear_lower(n):
    v=n.v
    body=[n.set('UI tap fx',div(add(arg('x'),240),v('UI private q'))),
          n.set('UI tap fy',div(sub(180,arg('y')),v('UI private q'))),
          *n.clip('UI tap fx',0,sub(v('UI map columns'),1)),
          *n.clip('UI tap fy',0,div(360,v('UI private q'))),
          n.set('UI texel base',add(1,add(floor(v('UI tap fx')),mul(floor(v('UI tap fy')),v('UI map columns'))))),
          n.set('UI tap fx',sub(v('UI tap fx'),floor(v('UI tap fx')))),
          n.set('UI tap fy',sub(v('UI tap fy'),floor(v('UI tap fy'))))]
    fx=v('UI tap fx');fy=v('UI tap fy')
    for off,w in ((0,mul(sub(1,fx),sub(1,fy))), (1,mul(fx,sub(1,fy))),
                  (v('UI map columns'),mul(sub(1,fx),fy)),(add(v('UI map columns'),1),mul(fx,fy))):
        body.append(n.call(TEXEL,add(v('UI texel base'),off),mul(w,arg('weight'))))
    return body


def transfer(n):
    # A dimming overlay belongs to its rear pane. Pass the undimmed glass
    # color into the next pane's optics with a smooth footprint. The displayed
    # rear pane still has its normal rim and dimming right up to its edge.
    v=n.v;alpha=v('UI through alpha');old=v('UI through old alpha')
    total=v('UI through total');rgb=v('UI through rgb');back=v('UI through back')
    merge=[n.set('UI through back',floor(div(v('UI through word'),2))),
           n.set('UI through old alpha',sub(v('UI through word'),mul(2,back))),
           n.set('UI through total',add(alpha,mul(old,sub(1,alpha))))]
    for ch in 'RGB':
        merge.append(n.set('UI through '+ch,rnd(div(add(mul(unpack(rgb,ch),alpha),
            mul(unpack(back,ch),mul(old,sub(1,alpha)))),total))))
    merge.append(n.set('UI through rgb',add(add(mul(v('UI through R'),65536),
                                                mul(v('UI through G'),256)),v('UI through B'))))
    return [n.set('UI trans t',arg('softness')),*n.clip('UI trans t',0,1),
        n.set('UI through alpha',mul(arg('coverage'),mul(square(v('UI trans t')),sub(3,mul(2,v('UI trans t')))))),
        iff(gt(alpha,.00001),[n.set('UI through word',n.item(LIGHT,v('UI lookup index'))),
            n.set('UI through rgb',arg('rgb')),n.set('UI through total',alpha),
            iff(AND(NOT(lt(v('UI through word'),0)),lt(alpha,1)),merge),
            n.replace(LIGHT,v('UI lookup index'),add(mul(2,rgb),total))])]


def wire_light_buffer(n):
    v=n.v
    private=n.definition(PRIVATE)
    for op in ('data_deletealloflist','data_addtolist'):
        for k in procs(n,private,op):
            storage=n.blocks[k]['fields'].get('LIST',[None])[0]
            if storage=='UI under surface':
                cmd=n.clear(LIGHT) if op=='data_deletealloflist' else n.add(LIGHT,-1)
                n.attach(k,[cmd],n.blocks[k]['next'])
            elif op=='data_deletealloflist' and storage=='UI panel ink color':
                n.attach(k,[n.clear(LIGHT_RGB),n.clear(LIGHT_ALPHA)],n.blocks[k]['next'])
    for k in procs(n,private,'data_replaceitemoflist'):
        if n.blocks[k]['fields'].get('LIST',[None])[0]!='UI under surface':continue
        after=n.blocks[k]['next'];counter=n.blocks[after]['fields']['VARIABLE'][0]
        if counter=='UI map stroke':
            index=v(counter)
            x=n.item('frameX',index);y=n.item('frameY',index)
            cell=add(1,add(rnd(div(sub(x,v('left')),v('q'))),
                           mul(rnd(div(sub(v('top'),y),v('q'))),v('cols'))))
            cmds=[n.set('UI depth index',cell),n.call(TRANSFER,n.item('frameRGB',index),
                sub(1,div(n.item('frameTransparency',index),100)),div(sub(0,n.item('field',v('UI depth index'))),12))]
        elif counter=='UI publish stroke':
            index=v(counter)
            cmds=[n.call(TRANSFER,n.item(LIGHT_RGB,index),v('UI publish alpha'),n.item(LIGHT_ALPHA,index))]
        else:
            raise ValueError('Unknown under-map publisher')
        n.attach(k,cmds,after)
    composites=[k for k in procs(n,n.definition(SHADE),'procedures_call')
                if n.blocks[k]['mutation']['proccode']==COMPOSITE]
    if len(composites)!=1:raise ValueError('Missing undimmed pane color')
    k=composites[0]
    n.attach(k,[n.add(LIGHT_RGB,add(add(mul(rnd(v('R')),65536),mul(rnd(v('G')),256)),rnd(v('B')))),
                n.add(LIGHT_ALPHA,div(sub(0,v('UI distance')),12))],n.blocks[k]['next'])
    for code in ('LG initialize','UI release buffers'):
        d=n.definition(code)
        n.attach(n.sequence(d)[-1],[n.clear(name) for name in (LIGHT,LIGHT_RGB,LIGHT_ALPHA)],None)


def apply_panel_optics(target, *, studio):
    n=UIProgram(target,exporting=not studio)
    for i,(code,args,fn) in enumerate(((PRIVATE_NORMAL,('layer','x','y'),private_normal),
            (PUBLIC_NORMAL,('cell',),public_normal),(TEXEL,('index','weight'),texel),
            (TRANSFER,('rgb','coverage','softness'),transfer))):
        n.declare(code,args)
        n.define(code,fn(n),(132000,9000+i*4000))
    replace_body(n,TAP,bilinear_lower(n))
    nblocks=n.blocks
    definition=n.definition(SHADE)
    visible=n.sequence(definition)[-1]
    first=nblocks[visible]['inputs']['SUBSTACK'][1]
    # The old three statements choose a single nearest side then flip its signs.
    obsolete=[first,nblocks[first]['next'],nblocks[nblocks[first]['next']]['next']]
    tail=nblocks[obsolete[-1]]['next']
    if nblocks[tail]['fields'].get('VARIABLE',[None])[0]!='UI lens offset':
        raise ValueError('Unrecognized private optical normal')
    new=n.emit(n.call(PRIVATE_NORMAL,arg('layer'),arg('x'),arg('y')),visible)
    nblocks[visible]['inputs']['SUBSTACK'][1]=new;nblocks[new]['next']=tail;nblocks[tail]['parent']=new
    for key in obsolete:n.remove(key)
    sx=nblocks[tail]['next']
    while nblocks[sx]['fields'].get('VARIABLE',[None])[0]!='UI source x':sx=nblocks[sx]['next']
    insert_before(n,sx,[n.set('UI lens offset',bounded_offset(n.v('UI lens offset'),n.v('UI lens band')))])

    prep=n.definition('LG prepare')
    n.attach(n.sequence(prep)[-1],[n.set('UI glass optics',0),iff(eq(n.v('UI view'),1),[
        n.set('UI optics id',1),repeat(8,[iff(eq(n.item('UI live',n.v('UI optics id')),1),[n.set('UI glass optics',1)]),
                                        n.change('UI optics id',1)])])],None)
    shader=n.definition('LG shade %s %s %s')
    last=next(key for key in reversed(n.sequence(shader))
              if nblocks[key]['fields'].get('VARIABLE',[None])[0]=='refraction')
    n.attach(last,[iff(eq(n.v('UI glass optics'),1),[n.call(PUBLIC_NORMAL,arg('cell'))])],nblocks[last]['next'])
    wire_light_buffer(n)
