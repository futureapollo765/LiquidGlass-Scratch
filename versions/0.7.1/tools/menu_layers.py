"""Add independent, animated native submenu panels to an existing 0.4.1 target.

The root remains the public Glass slot. Every pushed page has its own retained
geometry and spring in private Scratch lists. Rows keep their owner and panel
index so the front panel's pointer hits and selection events remain unambiguous.
"""
from .stable_pen import Node, arg, iff, go, transparency
from .ui_components import (UIProgram, MENU, eq, lt, gt, AND, OR, NOT, add, sub, mul, div,
    join, length, letter, math, abs_, rnd, floor, square, maximum, minimum, repeat, until)
from . import ui_labels as labels


LAYER = {
    'owner':0,'path':'','parent':'','row':0,'p':0,'v':0,'goal':1,'x':0,'y':0,'w':8,
    'h':8,'r':4,'rows':0,'pitch':34,'offset':0,'dim':0,
}
SLOT = {'UI menu open fade':0,'UI menu open velocity':0,'UI menu dim':0,'UI root offset':0,
        'UI menu panel width':120,'UI menu radius':12,'UI menu root rows':0}
RESET='UI layers reset'; BEGIN='UI layers begin'; ROWS='UI layer rows %s layer %s options %s'
STEP='UI spring page %s goal %s'; POSE='UI panels %s options %s width %s radius %s'
PUSH='UI push %s path %s from %s row %s'; POP='UI pop %s to %s'; HIT='UI layer hit %s'
ROOT='UI draw menu root'; PANEL='UI panel face'; LAUNCH='UI launcher face';
SHADE='UI layer rounded shade %s x %s y %s'; PRIVATE='UI prepare panel ink'; PAINT='UI paint panel %s'
TOP='UI paint floating menus'
KEY='UI layer frame key'
HELPERS={RESET:(),BEGIN:(),ROWS:('owner','layer','options'),STEP:('which','goal'),
         POSE:('owner','options','width','radius'),PUSH:('owner','path','parent','row'),POP:('owner','path'),
         HIT:('layer',),ROOT:(),PANEL:(),LAUNCH:(),PRIVATE:(),SHADE:('layer','x','y'),PAINT:('layer',),TOP:(),
         KEY:()}
INK=('UI panel ink x','UI panel ink y','UI panel ink color','UI panel ink alpha')


def li(n,name,i): return n.item('UI layer '+name,i)
def put(n,name,i,val): return n.replace('UI layer '+name,i,val)
def count(n): return n.length('UI layer owner')
def clamp1(x): return minimum(1,maximum(0,x))
def mix(a,b,f): return add(a,mul(sub(b,a),f))
def ghost(value):return Node('looks_seteffectto',{'VALUE':value},{'EFFECT':['GHOST',None]})
def sprite_alpha(n,value):
    return [n.set('UI ink opacity',value),ghost(mul(100,sub(1,n.v('UI ink opacity'))))]

def reset(n):
    return [*[n.clear('UI layer '+s) for s in LAYER],n.clear('UI row layer'),*[n.clear(s) for s in INK],
            *[cmd for name,val in SLOT.items() for cmd in (n.clear(name),repeat(8,[n.add(name,val)]))],
            *[n.set(name,0) for name in ('UI draw layer','UI build layer','UI hover layer','UI pressed layer')],
            n.set('UI ink opacity',1),ghost(0)]


def begin(n):
    v=n.v;i=v('UI prune')
    remove=[iff(eq(v('UI pressed layer'),i),[n.set('UI pressed layer',0),n.set('UI pressed id',0)],
                [iff(gt(v('UI pressed layer'),i),[n.change('UI pressed layer',-1)])]),
            *[n.list_op('data_deleteoflist','UI layer '+s,INDEX=i) for s in LAYER]]
    return [n.set('UI prune',count(n)),repeat(count(n),[
        iff(AND(eq(li(n,'goal',i),0),eq(li(n,'p',i),0)),remove),n.change('UI prune',-1)]),
        n.clear('UI row layer'),n.set('UI build layer',0)]


def layer_rows(n):
    owner=arg('owner'); layer=arg('layer');v=n.v
    # Reuse the original native hierarchy parser and pager. Its public page
    # stays the desired front path for event handlers and existing observers.
    root=eq(layer,0)
    read_root=[n.replace('UI page',owner,''),n.replace('UI page offset',owner,n.item('UI root offset',owner))]
    read_layer=[n.replace('UI page',owner,li(n,'path',layer)),n.replace('UI page offset',owner,li(n,'offset',layer))]
    finish_root=[n.replace('UI root offset',owner,n.item('UI page offset',owner)),
                 n.replace('UI menu root rows',owner,n.item('UI row count',owner))]
    finish_layer=[put(n,'rows',layer,n.item('UI row count',owner)),put(n,'offset',layer,n.item('UI page offset',owner))]
    return [n.set('UI saved page',n.item('UI page',owner)),n.set('UI saved offset',n.item('UI page offset',owner)),
            n.set('UI build layer',layer),iff(root,read_root,read_layer),
            n.call('UI rows %s options %s',owner,arg('options')),iff(root,finish_root,finish_layer),
            n.replace('UI page',owner,v('UI saved page')),n.replace('UI page offset',owner,v('UI saved offset')),
            n.replace('UI row count',owner,n.item('UI menu root rows',owner)),n.set('UI build layer',0)]


def spring(n):
    v=n.v
    # Semi-implicit substeps let slow Scratch frames advance safely and keep
    # position/velocity when the requested destination changes mid-flight.
    return [n.set('UI spring p',arg('which')),n.set('UI spring dt',div(v('UI step dt'),3)),repeat(3,[
        n.change('UI spring v',mul(sub(mul(320,sub(arg('goal'),v('UI spring p'))),
                                       mul(29,v('UI spring v'))),v('UI spring dt'))),
        n.change('UI spring p',mul(v('UI spring v'),v('UI spring dt')))]),
        iff(AND(lt(abs_(sub(arg('goal'),v('UI spring p'))),.002),lt(abs_(v('UI spring v')),.03)),
            [n.set('UI spring p',arg('goal')),n.set('UI spring v',0)]),
        *n.clip('UI spring p',0,1.035)]


def pop(n):
    v=n.v;o=arg('owner');path=arg('path');i=v('UI close index')
    # Preserve the specified parent and its ancestors; all other records
    # reverse their existing spring instead of dropping their geometry.
    keep=OR(eq(li(n,'path',i),path),eq(v('UI retained prefix'),join(li(n,'path',i),'>')))
    return [n.set('UI close index',1),repeat(count(n),[
        iff(eq(li(n,'owner',i),o),[n.set('UI retained prefix',''),n.set('UI prefix char',1),
            repeat(add(length(li(n,'path',i)),1),[n.set('UI retained prefix',join(v('UI retained prefix'),letter(v('UI prefix char'),path))),
                n.change('UI prefix char',1)]),iff(NOT(keep),[put(n,'goal',i,0)])]),n.change('UI close index',1)]),
        n.replace('UI page',o,path),n.replace('UI page offset',o,0)]


def push(n):
    v=n.v;o=arg('owner');parent=arg('parent');path=arg('path');i=v('UI push index')
    values=dict(LAYER,owner=o,path=path,parent=v('UI push parent'),row=arg('row'),pitch=n.item('UI row height',o))
    values.update(x=v('UI new x'),y=v('UI new y'),w=v('UI new width'),h=v('UI new pitch'))
    def seed(which,lookup):
        return [n.set('UI new x',lookup('x')),n.set('UI new y',add(lookup('y'),div(lookup('h'),2))),
                n.set('UI new width',maximum(8,sub(lookup('w'),12))),n.set('UI new pitch',which)]
    initial=[*seed(n.item('UI row height',o),lambda f:n.item(f,o)),
             iff(gt(parent,0),seed(li(n,'pitch',parent),lambda f:li(n,f,parent))),
             n.change('UI new y',mul(-1,mul(add(arg('row'),.5),v('UI new pitch')))),
             *n.clip('UI new x',add(-240,div(v('UI new width'),2)),sub(240,div(v('UI new width'),2))),
             *n.clip('UI new y',add(-180,div(v('UI new pitch'),2)),sub(180,div(v('UI new pitch'),2)))]
    append=initial+[n.add('UI layer '+s,values[s]) for s in LAYER]
    match=v('UI push match')
    def update_index(name):
        return iff(eq(v(name),match),[n.set(name,count(n))],
                   [iff(gt(v(name),match),[n.change(name,-1)])])
    # If a retiring sibling is invoked again, keep its exact spring position
    # and move the record in front of the sibling that is now retiring.
    refront=[*[cmd for f in LAYER for cmd in (n.add('UI layer '+f,li(n,f,match)),
             n.list_op('data_deleteoflist','UI layer '+f,INDEX=match))],
             n.set('UI rerank row',1),repeat(n.length('UI row layer'),[
                 n.set('UI old rank',n.item('UI row layer',v('UI rerank row'))),
                 iff(eq(v('UI old rank'),match),[n.replace('UI row layer',v('UI rerank row'),count(n))],
                     [iff(gt(v('UI old rank'),match),[n.replace('UI row layer',v('UI rerank row'),sub(v('UI old rank'),1))])]),
                 n.change('UI rerank row',1)]),update_index('UI hover layer'),update_index('UI pressed layer'),
             n.set('UI push match',count(n))]
    resume=[iff(lt(match,count(n)),refront),put(n,'goal',match,1),put(n,'row',match,arg('row'))]
    return [n.set('UI push parent',''),iff(gt(parent,0),[n.set('UI push parent',li(n,'path',parent))]),
            n.call(POP,o,v('UI push parent')),n.set('UI push match',0),n.set('UI push index',1),
            repeat(count(n),[iff(AND(eq(li(n,'owner',i),o),eq(li(n,'path',i),path)),[n.set('UI push match',i)]),n.change('UI push index',1)]),
            iff(eq(v('UI push match'),0),append,resume),
            n.replace('UI page',o,path),n.replace('UI page offset',o,0)]


def pose(n):
    v=n.v;o=arg('owner');i=v('UI panel step');j=v('UI parent index');p=li(n,'p',i)
    phase=clamp1(p);dim=li(n,'dim',i)
    # Bookkeeping for every record first; geometry is then built in stack
    # order, so a nested page can read its invoking panel's current footprint.
    tick=[iff(eq(n.item('UI open',o),0),[put(n,'goal',i,0)]),n.set('UI spring v',li(n,'v',i)),
          n.call(STEP,p,li(n,'goal',i)),put(n,'p',i,v('UI spring p')),put(n,'v',i,v('UI spring v')),put(n,'dim',i,0),
          n.call(ROWS,o,i,arg('options')),put(n,'pitch',i,n.item('UI row height',o))]
    find_parent=[n.set('UI parent index',1),repeat(count(n),[iff(AND(eq(li(n,'owner',j),o),
        eq(li(n,'path',j),li(n,'parent',i))),[n.set('UI parent match',j)]),n.change('UI parent index',1)])]
    def from_parent(f,k): return n.set('UI base '+f,li(n,k,v('UI parent match')))
    parent_geometry=[from_parent(f,k) for f,k in [('x','x'),('y','y'),('w','w'),('h','h'),('pitch','pitch')]]
    root_geometry=[n.set('UI base x',n.item('x',o)),n.set('UI base y',n.item('y',o)),n.set('UI base w',n.item('w',o)),
                   n.set('UI base h',n.item('h',o)),n.set('UI base pitch',n.item('UI row height',o))]
    parent_top=add(v('UI base y'),div(v('UI base h'),2))
    row_y=sub(parent_top,mul(add(li(n,'row',i),.5),v('UI base pitch')))
    finish=[*root_geometry,n.set('UI parent match',0),iff(gt(length(li(n,'parent',i)),0),find_parent),
            iff(gt(v('UI parent match'),0),parent_geometry),n.set('UI seed y',row_y),
            n.set('UI child width',minimum(440,maximum(16,add(abs_(arg('width')),8)))),
            n.set('UI child height',minimum(300,mul(add(li(n,'rows',i),1),li(n,'pitch',i)))),
            n.set('UI child x',sub(v('UI base x'),8)),
            n.set('UI child y',sub(add(v('UI seed y'),div(v('UI base pitch'),2)),div(v('UI child height'),2))),
            *n.clip('UI child x',add(-238,div(v('UI child width'),2)),sub(238,div(v('UI child width'),2))),
            *n.clip('UI child y',add(-178,div(v('UI child height'),2)),sub(178,div(v('UI child height'),2))),
            put(n,'x',i,add(mix(v('UI base x'),v('UI child x'),p),mul(4,dim))),
            put(n,'y',i,add(mix(v('UI seed y'),v('UI child y'),p),mul(6,dim))),
            put(n,'w',i,maximum(8,sub(mix(maximum(12,sub(v('UI base w'),12)),v('UI child width'),p),mul(10,dim)))),
            put(n,'h',i,maximum(8,sub(mix(v('UI base pitch'),v('UI child height'),p),mul(6,dim)))),
            put(n,'r',i,maximum(0,minimum(arg('radius'),div(minimum(li(n,'w',i),li(n,'h',i)),2)))),
            put(n,'x',i,minimum(sub(240,div(li(n,'w',i),2)),maximum(add(-240,div(li(n,'w',i),2)),li(n,'x',i)))),
            put(n,'y',i,minimum(sub(180,div(li(n,'h',i),2)),maximum(add(-180,div(li(n,'h',i),2)),li(n,'y',i))))]
    propagate=[n.set('UI parent match',0),iff(gt(length(li(n,'parent',i)),0),find_parent),
        iff(gt(v('UI parent match'),0),[put(n,'dim',v('UI parent match'),maximum(li(n,'dim',v('UI parent match')),phase))],
            [n.replace('UI menu dim',o,maximum(n.item('UI menu dim',o),phase))])]
    def all_records(body):
        return [n.set('UI panel step',1),repeat(count(n),[iff(eq(li(n,'owner',i),o),body),n.change('UI panel step',1)])]
    return [n.set('UI step dt',v('dt')),*n.clip('UI step dt',.012,.055),
        n.set('UI spring v',n.item('UI menu open velocity',o)),n.call(STEP,n.item('UI menu open fade',o),n.item('UI open',o)),
        n.replace('UI menu open fade',o,v('UI spring p')),n.replace('UI menu open velocity',o,v('UI spring v')),
        n.replace('UI menu panel width',o,arg('width')),n.replace('UI menu radius',o,arg('radius')),
        iff(AND(eq(n.item('UI open',o),0),gt(n.item('UI menu open fade',o),0)),[n.call(ROWS,o,0,arg('options'))]),
        n.replace('UI menu dim',o,0),*all_records(tick),*all_records(propagate),*all_records(finish),
        n.change('UI cx',mul(4,n.item('UI menu dim',o))),n.change('UI cy',mul(6,n.item('UI menu dim',o))),
        n.change('UI width',mul(-10,n.item('UI menu dim',o))),n.change('UI height',mul(-6,n.item('UI menu dim',o))),
        *n.clip('UI cx',add(-240,div(v('UI width'),2)),sub(240,div(v('UI width'),2))),
        *n.clip('UI cy',add(-180,div(v('UI height'),2)),sub(180,div(v('UI height'),2)))]


def hit(n):
    v=n.v;i=arg('layer');px=v('UI pointer x');py=v('UI pointer y');r=li(n,'r',i)
    # A local rounded-box test also prevents the small transparent corners of
    # a new panel from claiming clicks outside its visible contour.
    xx=sub(abs_(sub(px,li(n,'x',i))),sub(div(li(n,'w',i),2),r));yy=sub(abs_(sub(py,li(n,'y',i))),sub(div(li(n,'h',i),2),r))
    return [n.set('UI hit x',xx),n.set('UI hit y',yy),iff(AND(gt(li(n,'p',i),.12),AND(eq(li(n,'goal',i),1),
        NOT(gt(add(square(maximum(0,v('UI hit x'))),square(maximum(0,v('UI hit y')))),square(r))))),[
        n.set('UI hit found',1),n.set('UI hover layer',i),n.set('UI hover id',li(n,'owner',i)),
        n.set('UI hover row',floor(div(sub(add(li(n,'y',i),div(li(n,'h',i),2)),py),li(n,'pitch',i)))),
        iff(OR(lt(v('UI hover row'),0),gt(v('UI hover row'),li(n,'rows',i))),[n.set('UI hover row',-1)])])]


def choose(n):
    v=n.v;o=arg('slot');row=arg('row');i=v('UI flat row');layer=v('UI hover layer')
    role=n.item('UI row role',i);path=n.item('UI row path',i)
    close=[n.call(POP,o,''),n.replace('UI open',o,0),n.replace('UI root offset',o,0)]
    head=[iff(gt(layer,0),[n.call(POP,o,li(n,'parent',layer))],
        [iff(gt(length(n.item('UI page',o)),0),[n.call(POP,o,'')],
             [iff(NOT(eq(n.item('UI mode',o),'panel')),[iff(eq(n.item('UI open',o),1),close,[n.replace('UI open',o,1)])])])])]
    more=[iff(gt(layer,0),[put(n,'next offset',layer,add(li(n,'offset',layer),sub(li(n,'rows',layer),1))),
        n.replace('UI page offset',o,li(n,'next offset',layer))],
        [n.replace('UI root next offset',o,add(n.item('UI root offset',o),sub(n.item('UI menu root rows',o),1))),
         n.replace('UI page offset',o,n.item('UI root next offset',o))])]
    leaf=[n.call('UI fire %s action %s path %s',o,path,path),n.call(POP,o,''),n.replace('UI root offset',o,0),
          iff(NOT(eq(n.item('UI mode',o),'panel')),[n.replace('UI open',o,0)])]
    dimmed=OR(AND(eq(layer,0),gt(n.item('UI menu dim',o),.02)),AND(gt(layer,0),gt(li(n,'dim',layer),.02)))
    front_leaf=[iff(dimmed,[n.set('UI revealed path',''),iff(gt(layer,0),[n.set('UI revealed path',li(n,'path',layer))]),n.call(POP,o,v('UI revealed path'))],leaf)]
    selected=[iff(eq(role,'submenu'),[n.call(PUSH,o,path,layer,row)],[iff(eq(role,'more'),more,front_leaf)])]
    find=[n.set('UI flat row',1),repeat(n.length('UI row id'),[
        iff(AND(eq(n.item('UI row id',i),o),AND(eq(n.item('UI row index',i),row),eq(n.item('UI row layer',i),layer))),selected),
        n.change('UI flat row',1)])]
    return [iff(eq(n.item('UI kind',o),'Button'),[n.call('UI fire %s action %s path %s',o,n.item('UI button action',o),'')]),
            iff(eq(n.item('UI kind',o),'Menu'),[iff(eq(row,0),head,find)])]


def key(n):
    v=n.v;i=v('UI key panel');o=v('UI key owner')
    def token(val): return n.set('preparedScene',join(v('preparedScene'),join('/',val)))
    return [iff(eq(v('UI view'),1),[n.set('UI key owner',1),repeat(8,[
        iff(eq(n.item('UI kind',o),'Menu'),[token(n.item('UI menu open fade',o)),token(n.item('UI menu dim',o)),token(n.item('UI root page fade',o))]),
        n.change('UI key owner',1)]),token(v('UI hover layer')),token(v('UI pressed layer')),n.set('UI key panel',1),
        repeat(count(n),[*[token(li(n,f,i)) for f in ('owner','path','p','goal','x','y','w','h','r','pitch','rows','dim','offset','fade')],
                           n.change('UI key panel',1)])])]


def rect_extent(n,dy,width,height,radius):
    # Positive half-width at a horizontal cut through a rounded rectangle.
    corner=maximum(0,sub(abs_(dy),sub(div(height,2),radius)))
    return add(sub(div(width,2),radius),math('sqrt',maximum(0,sub(square(radius),square(corner)))))


def root_ink(n):
    v=n.v;o=v('UI art id');fade=clamp1(n.item('UI menu open fade',o));dimv=n.item('UI menu dim',o)
    parent_light=sub(1,mul(.55,dimv))
    return [n.set('UI draw layer',0),n.set('UI held page',n.item('UI page',o)),n.replace('UI page',o,''),
        n.set('UI held hover',v('UI hover id')),n.set('UI held pressed',v('UI pressed id')),
        iff(gt(v('UI hover layer'),0),[n.set('UI hover id',0)]),iff(gt(v('UI pressed layer'),0),[n.set('UI pressed id',0)]),
        iff(lt(fade,.999),[*sprite_alpha(n,mul(parent_light,sub(1,fade))),n.call(LAUNCH)]),
        iff(gt(fade,.001),[*sprite_alpha(n,mul(mul(parent_light,fade),n.item('UI root page fade',o))),n.call(PANEL)]),
        *sprite_alpha(n,1),n.replace('UI page',o,v('UI held page')),n.set('UI hover id',v('UI held hover')),
        n.set('UI pressed id',v('UI held pressed'))]


def draw_layer(n):
    v=n.v;i=arg('layer');o=li(n,'owner',i)
    return [n.set('UI art id',o),n.set('UI draw layer',i),
        *[n.set('UI '+key,li(n,f,i)) for key,f in [('cx','x'),('cy','y'),('width','w'),('height','h'),('ink row step','pitch')]],
        n.set('UI left',sub(v('UI cx'),div(v('UI width'),2))),n.set('UI top',add(v('UI cy'),div(v('UI height'),2))),
        n.set('UI bottom',sub(v('UI cy'),div(v('UI height'),2))),
        n.set('UI private page',n.item('UI page',o)),n.replace('UI page',o,li(n,'path',i)),
        n.set('UI held hover',v('UI hover id')),n.set('UI held pressed',v('UI pressed id')),
        iff(NOT(eq(v('UI hover layer'),i)),[n.set('UI hover id',0)]),iff(NOT(eq(v('UI pressed layer'),i)),[n.set('UI pressed id',0)]),
        *sprite_alpha(n,mul(li(n,'fade',i),mul(clamp1(li(n,'p',i)),sub(1,mul(.52,li(n,'dim',i)))))),
        n.call(PANEL),*sprite_alpha(n,1),n.replace('UI page',o,v('UI private page')),
        n.set('UI hover id',v('UI held hover')),n.set('UI pressed id',v('UI held pressed'))]


def top(n):
    v=n.v;i=v('UI replay panel')
    return [iff(eq(v('UI view'),1),[n.set('UI replay panel',1),repeat(count(n),[
        iff(gt(li(n,'p',i),.001),[n.call(PAINT,i)]),n.change('UI replay panel',1)]),n.set('UI draw layer',0)]),
        *[n.clear(name) for name in INK]]

SAMPLE='LG material sample x %s y %s blur %s background %s'
COMPOSITE='LG material composite tint %s shine %s opacity %s red %s green %s blue %s brightness %s'
MAP='UI private sample cell x %s y %s'
PAGING='UI ease page %s layer %s'
HELPERS.update({MAP:('x','y'),PAGING:('owner','layer')})
LAYER.update(strokes=0,fade=1,**{'next offset':-1})
SLOT.update({'UI root page fade':1,'UI root next offset':-1})


def paging(n):
    v=n.v;o=arg('owner');i=arg('layer');root=eq(i,0)
    return [iff(root,[n.set('UI page fade',n.item('UI root page fade',o)),n.set('UI pending offset',n.item('UI root next offset',o))],
               [n.set('UI page fade',li(n,'fade',i)),n.set('UI pending offset',li(n,'next offset',i))]),
            n.set('UI fade delta',mul(8,maximum(.012,minimum(.055,v('dt'))))),
            iff(NOT(lt(v('UI pending offset'),0)),[n.set('UI page fade',maximum(0,sub(v('UI page fade'),v('UI fade delta')))),
                iff(eq(v('UI page fade'),0),[iff(root,[n.replace('UI root offset',o,v('UI pending offset'))],
                    [put(n,'offset',i,v('UI pending offset'))]),n.set('UI pending offset',-1)])],
                [n.set('UI page fade',minimum(1,add(v('UI page fade'),v('UI fade delta'))))]),
            iff(root,[n.replace('UI root page fade',o,v('UI page fade')),n.replace('UI root next offset',o,v('UI pending offset'))],
                [put(n,'fade',i,v('UI page fade')),put(n,'next offset',i,v('UI pending offset'))])]


def map_cell(n):
    v=n.v
    return [n.set('UI lookup x',arg('x')),n.set('UI lookup y',arg('y')),*n.clip('UI lookup x',-240,240),
            *n.clip('UI lookup y',-180,180),
            n.set('UI lookup index',add(1,add(rnd(div(add(v('UI lookup x'),240),v('UI private q'))),
                       mul(rnd(div(sub(180,v('UI lookup y')),v('UI private q'))),v('UI map columns')))))]


def unpack(word,channel):
    if channel=='R':return math('floor',div(word,65536))
    if channel=='G':return Node('operator_mod',{'NUM1':math('floor',div(word,256)),'NUM2':256})
    return Node('operator_mod',{'NUM1':word,'NUM2':256})


def shade(n):
    v=n.v;i=arg('layer');sx=arg('x');sy=arg('y');owner=li(n,'owner',i);q=v('UI private q');rad=li(n,'r',i);d=v('UI distance')
    def val(name):return n.item(name,owner)
    nx=v('UI normal x');ny=v('UI normal y'); lx=v('UI distance x');ly=v('UI distance y');ox=v('UI outside x');oy=v('UI outside y')
    def packed():return add(mul(rnd(v('R')),65536),add(mul(rnd(v('G')),256),rnd(v('B'))))
    under=v('UI under word');uc=v('UI under RGB');ua=v('UI under alpha')
    underlay=[n.set('UI tap alpha',0),*[n.set('UI tap '+ch,0) for ch in ('R','G','B')],
        iff(gt(val('matBlur'),.01),[
            n.call(TAP,v('UI source x'),v('UI source y'),.5),
            *[n.call(TAP,add(v('UI source x'),mul(dx,val('matBlur'))),add(v('UI source y'),mul(dy,val('matBlur'))),.125)
              for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]]],
            [n.call(TAP,v('UI source x'),v('UI source y'),1)]),
        *[n.set(ch,add(mul(v(ch),sub(1,v('UI tap alpha'))),v('UI tap '+ch))) for ch in ('R','G','B')]]
    # Surface normal of a rounded rectangle. Compute with the same scale as
    # the public field gradient, then refract the actual pixel visible below
    # this pane. A private panel never contributes to the public SDF union.
    normal=[iff(gt(v('UI outside length'),.00001),[
             n.set('UI normal x',div(ox,v('UI outside length'))),n.set('UI normal y',div(oy,v('UI outside length')))],
             [n.set('UI normal x',gt(lx,ly)),n.set('UI normal y',NOT(gt(lx,ly)))]),
            iff(lt(sx,li(n,'x',i)),[n.set('UI normal x',mul(-1,nx))]),iff(lt(sy,li(n,'y',i)),[n.set('UI normal y',mul(-1,ny))])]
    visible=[*normal,n.set('UI lens offset',mul(div(square(maximum(0,add(v('UI lens band'),d))),10),val('distortion'))),
             *n.clip('UI lens offset',-110,110),n.set('UI source x',sub(sx,mul(nx,v('UI lens offset')))),
             n.set('UI source y',sub(sy,mul(ny,v('UI lens offset')))),
             n.call(SAMPLE,v('UI source x'),v('UI source y'),val('matBlur'),v('frameBG')),
             *underlay,
             n.set('UI lens rim',maximum(0,sub(1,div(abs_(d),maximum(mul(q,.7),val('edge')))))),
             n.set('UI lens lobe',add(.5,add(mul(mul(.5,sub(square(nx),square(ny))),val('componentLightX')),
                                  mul(mul(nx,ny),val('componentLightY'))))),
             n.set('UI lens shine',mul(gt(val('edge'),0),mul(val('highlight'),mul(v('UI lens rim'),add(28,mul(125,v('UI lens lobe'))))))),
             n.call(COMPOSITE,val('tint'),v('UI lens shine'),val('matAlpha'),val('matRed'),val('matGreen'),val('matBlue'),val('matBrightness')),
             *[n.set(ch,mix(v(ch),t,mul(.34,li(n,'dim',i)))) for ch,t in [('R',36),('G',48),('B',68)]],
             n.set('UI ink RGB',packed()),n.set('UI pixel coverage',mul(clamp1(sub(.5,div(d,q))),clamp1(li(n,'p',i)))),
             n.add('UI panel ink x',sx),n.add('UI panel ink y',sy),n.add('UI panel ink color',v('UI ink RGB')),
             n.add('UI panel ink alpha',mul(100,sub(1,v('UI pixel coverage'))))]
    return [n.set('UI distance x',add(sub(abs_(sub(sx,li(n,'x',i))),div(li(n,'w',i),2)),rad)),
            n.set('UI distance y',add(sub(abs_(sub(sy,li(n,'y',i))),div(li(n,'h',i),2)),rad)),
            n.set('UI outside x',maximum(0,lx)),n.set('UI outside y',maximum(0,ly)),
            n.set('UI outside length',math('sqrt',add(square(ox),square(oy)))),
            n.set('UI distance',sub(add(v('UI outside length'),minimum(maximum(lx,ly),0)),rad)),
            iff(lt(d,mul(.5,q)),visible)]


def prepare(n):
    v=n.v;i=v('UI raster pane');base=v('UI map stroke');q=v('UI private q');owner=li(n,'owner',i)
    # The coordinate table stores RGBA sampled from the base renderer. It is
    # transient, at most 481 × 361 entries, and is freed before presentation.
    # Child surfaces write into the same lookup for the next nested page.
    base_map=[n.call(MAP,n.item('frameX',base),n.item('frameY',base)),
              n.call(BASE,n.item('frameX',base),n.item('frameY',base),n.item('frameRGB',base)),
              n.replace('UI under surface',v('UI lookup index'),add(mul(2,v('UI base RGB')),
                    sub(1,div(n.item('frameTransparency',base),100)))),n.change('UI map stroke',1)]
    cells=[n.set('UI raster x',v('UI raster left')),repeat(v('UI raster cols'),[
            n.call(SHADE,i,v('UI raster x'),v('UI raster y')),n.change('UI raster x',q)]),n.change('UI raster y',mul(-1,q))]
    stamp=v('UI publish stroke');ca=v('UI publish alpha');oa=v('UI previous alpha');rgb=v('UI publish RGB');last=v('UI previous RGB');tot=v('UI summed alpha')
    merge=[n.set('UI previous RGB',math('floor',div(v('UI previous RGBA'),2))),
        n.set('UI previous alpha',sub(v('UI previous RGBA'),mul(2,last))),
        n.set('UI summed alpha',add(ca,mul(oa,sub(1,ca)))),
        *[n.set(ch,rnd(div(add(mul(unpack(rgb,ch),ca),mul(mul(unpack(last,ch),oa),sub(1,ca))),tot))) for ch in ('R','G','B')],
        n.set('UI publish RGB',add(mul(v('R'),65536),add(mul(v('G'),256),v('B'))))]
    publish=[n.call(MAP,n.item('UI panel ink x',stamp),n.item('UI panel ink y',stamp)),
        n.set('UI publish alpha',sub(1,div(n.item('UI panel ink alpha',stamp),100))),
        n.set('UI summed alpha',ca),n.set('UI publish RGB',n.item('UI panel ink color',stamp)),
        n.set('UI previous RGBA',n.item('UI under surface',v('UI lookup index'))),
        iff(AND(NOT(lt(v('UI previous RGBA'),0)),lt(ca,1)),merge),
        n.replace('UI under surface',v('UI lookup index'),add(mul(2,rgb),tot)),n.change('UI publish stroke',1)]
    layer=[n.set('UI raster left',mul(floor(div(sub(li(n,'x',i),add(div(li(n,'w',i),2),q)),q)),q)),
        n.set('UI raster y',mul(math('ceiling',div(add(li(n,'y',i),add(div(li(n,'h',i),2),q)),q)),q)),
        n.set('UI raster cols',add(3,math('ceiling',div(li(n,'w',i),q)))),n.set('UI raster rows',add(3,math('ceiling',div(li(n,'h',i),q)))),
        n.set('UI lens band',mul(.5,mul(minimum(li(n,'w',i),li(n,'h',i)),n.item('reflection',owner)))),
        n.set('UI first stroke',n.length('UI panel ink x')),repeat(v('UI raster rows'),cells),
        put(n,'strokes',i,sub(n.length('UI panel ink x'),v('UI first stroke'))),n.set('UI publish stroke',add(v('UI first stroke'),1)),
        repeat(li(n,'strokes',i),publish)]
    # Export the fully composited world in top-to-bottom order. The original
    # band replay now restores and displays front glass in the same band. No
    # second private-glass pass can temporarily uncover the whole front pane.
    export=[n.set('UI merged word',n.item('UI under surface',v('UI merged index'))),
        iff(NOT(lt(v('UI merged word'),0)),[n.set('UI merged RGB',math('floor',div(v('UI merged word'),2))),
           n.add('frameX',v('UI merged x')),n.add('frameY',v('UI merged y')),n.add('frameRGB',v('UI merged RGB')),
           n.add('frameTransparency',mul(100,sub(1,sub(v('UI merged word'),mul(2,v('UI merged RGB'))))))]),
        n.change('UI merged index',1),n.change('UI merged x',q)]
    work=[n.clear('UI dim ids'),n.set('UI dim collect',1),repeat(8,[iff(AND(eq(n.item('UI kind',v('UI dim collect')),'Menu'),gt(n.item('UI menu dim',v('UI dim collect')),0)),[n.add('UI dim ids',v('UI dim collect'))]),n.change('UI dim collect',1)]),
          n.set('UI private q',v('q')),n.set('UI map columns',add(1,rnd(div(480,q)))),
        repeat(mul(v('UI map columns'),add(1,rnd(div(360,q)))),[n.add('UI under surface',-1)]),
        n.set('UI map stroke',1),repeat(n.length('frameX'),base_map),n.set('UI raster pane',1),
        repeat(count(n),[put(n,'strokes',i,0),iff(gt(li(n,'p',i),.001),layer),n.change('UI raster pane',1)]),
        *[n.clear(name) for name in ('frameX','frameY','frameRGB','frameTransparency')],
        n.set('UI merged index',1),n.set('UI merged y',180),repeat(add(1,rnd(div(360,q))),[
            n.set('UI merged x',-240),repeat(v('UI map columns'),export),n.change('UI merged y',mul(-1,q))]),
        n.set('strokeCount',n.length('frameY')),n.set('strokeIndex',1),*[n.clear(name) for name in INK]]
    return [*[n.clear(name) for name in INK],n.clear('UI under surface'),
            iff(AND(eq(v('UI view'),1),gt(count(n),0)),work),n.clear('UI under surface')]


def is_owner(n,k,definition):
    while k:
        if k==definition:return True
        k=n.blocks[k].get('parent')
    return False


def chain_end(n,k):
    while n.blocks[k]['next']:k=n.blocks[k]['next']
    return k


def insert_before(n,k,nodes):
    parent=n.blocks[k]['parent'];p=n.blocks[parent]
    if p['next']==k:
        n.attach(parent,nodes,k);return
    keys=[key for key,b in p.get('inputs',{}).items() if key.startswith('SUBSTACK') and b[1]==k]
    if len(keys)!=1:raise ValueError(f'Unrecognized incoming stack for {k}')
    first,last=n.chain(nodes,parent);p['inputs'][keys[0]][1]=first;n.blocks[last]['next']=k;n.blocks[k]['parent']=last


def procs(n,definition,opcode):
    return [k for k,b in n.blocks.items() if isinstance(b,dict) and b.get('opcode')==opcode and is_owner(n,k,definition)]


def wrap_cond(n,k,extra):
    b=n.blocks[k];old=b['inputs']['CONDITION'][1];wrapper=n.emit(AND(Node('operator_equals',{'OPERAND1':1,'OPERAND2':1}),extra),k)
    dummy=n.blocks[wrapper]['inputs']['OPERAND1'][1];n.remove(dummy);n.blocks[wrapper]['inputs']['OPERAND1']=[2,old];n.blocks[old]['parent']=wrapper
    b['inputs']['CONDITION']=[2,wrapper]


def replace_body(n,name,body):
    d=n.definition(name)
    for k in n.sequence(d):n.remove(k)
    n.blocks[d]['next']=n.chain(body,d)[0]


def patch_menu(n):
    import json,copy
    b=n.blocks;menu=n.definition(MENU);slot=n.v('UI slot')
    calls=procs(n,menu,'procedures_call')
    rowcall=next(k for k in calls if b[k]['mutation']['proccode']=='UI rows %s options %s')
    gcall=next(k for k in calls if b[k]['mutation']['proccode'].startswith('Glass '))
    c=b[rowcall];old_ids=json.loads(c['mutation']['argumentids']);ids=json.loads(n.procs[ROWS]['argumentids'])
    c['inputs']={ids[0]:c['inputs'][old_ids[0]],ids[1]:[1,[4,'0']],ids[2]:c['inputs'][old_ids[1]]}
    c['mutation']={key:copy.deepcopy(n.procs[ROWS][key]) for key in ('tagName','children','proccode','argumentids','warp')}
    insert_before(n,gcall,[n.call(POSE,slot,arg('items'),arg('panel width'),arg('radius'))])
    rp=n.definition('UI rows %s options %s')
    for k in procs(n,rp,'data_addtolist'):
        if b[k]['fields']['LIST'][0]=='UI row role':n.attach(k,[n.add('UI row layer',n.v('UI build layer'))],b[k]['next'])
    replace_body(n,'UI choose %s row %s',choose(n))
    back=n.definition('UI back %s');n.attach(n.sequence(back)[-1],[n.call(POP,arg('slot'),n.item('UI page',arg('slot')))],None)
    for name,code in [('UI reset',RESET),('UI begin',BEGIN)]:
        d=n.definition(name);n.attach(n.sequence(d)[-1],[n.call(code)],None)


def patch_input(n):
    v=n.v;b=n.blocks;d=n.definition('UI input');seq=n.sequence(d)
    scan=next(k for k in seq if b[k]['opcode']=='control_repeat');down,drag,release=seq[seq.index(scan)+1:]
    # A removed or retyped caller must vacate its private layers immediately.
    i=v('UI private hit index');o=li(n,'owner',i)
    cleanup=[put(n,'goal',i,0),put(n,'p',i,0),put(n,'strokes',i,0),n.replace('UI menu dim',o,0),
             n.replace('UI menu open fade',o,0),n.replace('UI root offset',o,0)]
    hit_scan=[iff(OR(NOT(eq(n.item('UI kind',o),'Menu')),eq(n.item('UI live',o),0)),cleanup,
              [iff(eq(v('UI hit found'),0),[n.call(HIT,i)])]),n.change('UI private hit index',-1)]
    insert_before(n,down,[n.set('UI hover layer',0),n.set('UI hit found',0),n.set('UI private hit index',count(n)),repeat(count(n),hit_scan)])
    down_stack=b[down]['inputs']['SUBSTACK'][1];n.attach(chain_end(n,down_stack),[n.set('UI pressed layer',v('UI hover layer'))],None)
    # Background sampling and clicks keep the original pointer queue, with
    # an extra layer identity check when a menu changes under a held pointer.
    release_stack=b[release]['inputs']['SUBSTACK'][1];wrap_cond(n,release_stack,eq(v('UI hover layer'),v('UI pressed layer')))
    n.attach(chain_end(n,release_stack),[n.set('UI pressed layer',0)],None)
    wrap_cond(n,drag,eq(v('UI pressed layer'),0))


def patch_foreground(n):
    b=n.blocks;d=n.definition(labels.FOREGROUND)
    # Extract the original two native art stacks, preserving the exact caller-
    # editable title/icon, truncation, wash and selection blocks in both stacks.
    candidates=[]
    for k in procs(n,d,'control_if_else'):
        cond=b[b[k]['inputs']['CONDITION'][1]]
        if cond['opcode']=='operator_equals' and any(isinstance(x[1],str) and b[x[1]].get('fields',{}).get('LIST',[None])[0]=='UI open' for x in cond['inputs'].values()):
            candidates.append(k)
    if len(candidates)!=1:raise ValueError('Expected one Menu open/closed foreground choice')
    k=candidates[0];node=b[k];opened=node['inputs']['SUBSTACK'][1];closed=node['inputs']['SUBSTACK2'][1]
    for code,seq in [(PANEL,opened),(LAUNCH,closed)]:
        root=n.definition(code);b[root]['next']=seq;b[seq]['parent']=root
    n.remove(node['inputs']['CONDITION'][1]);node['inputs']={};node['fields']={};node['opcode']='procedures_call';node['mutation']=n.procs[ROOT].copy()
    for key in ['argumentnames','argumentdefaults']:node['mutation'].pop(key)
    panel=n.definition(PANEL)
    for rid in procs(n,panel,'control_if'):
        cond=b[b[rid]['inputs']['CONDITION'][1]]
        if cond['opcode']=='operator_equals' and any(isinstance(x[1],str) and b[x[1]].get('fields',{}).get('LIST',[None])[0]=='UI row id' for x in cond['inputs'].values()):
            wrap_cond(n,rid,eq(n.item('UI row layer',n.v('UI art row')),n.v('UI draw layer')))
    # Attenuate the existing one-pass hover/press/selection wash during label
    # fades. Its normal ink has opacity one on all existing button paths.
    wash=n.definition(labels.WASH)
    for key in procs(n,wash,'pen_setPenColorParamTo'):
        val=b[key]['inputs']['VALUE'][1]
        if val==n.v('UI wash transparency'):
            from .ui_labels import sub as minus,mul as times
            amount=minus(100,times(minus(100,n.v('UI wash transparency')),n.v('UI ink opacity')))
            b[key]['inputs']['VALUE']=[2,n.emit(amount,key)]
    tail=n.sequence(d)[-1];n.attach(tail,[n.call(TOP)],None)


def patch_damage(n):
    v=n.v;b=n.blocks;render=n.definition('LG render');r=n.sequence(render)
    signature=next(k for k in r if b[k]['opcode']=='procedures_call' and b[k]['mutation']['proccode']==labels.SIGNATURE)
    n.attach(signature,[n.call(KEY)],b[signature]['next'])
    # Prepare overlays before any strip is replaced. The active frame bounds
    # become previousTop/Bottom only after a successful presentation, covering
    # the old footprint on the last reversing frame as well.
    loop=next(k for k in procs(n,render,'control_repeat') if b[k]['inputs'].get('TIMES')==[1,[4,'45']])
    parent=b[loop]['parent'];prev=b[parent]
    if prev['opcode']!='control_if_else':raise ValueError('Unexpected retained frame bounds')
    pick=v('UI damage slot');damage=[n.set('UI damage slot',1),repeat(count(n),[
        iff(gt(li(n,'p',pick),.001),[n.set('strokeTop',maximum(v('strokeTop'),add(add(li(n,'y',pick),div(li(n,'h',pick),2)),add(v('q'),2)))),
            n.set('strokeBottom',minimum(v('strokeBottom'),sub(sub(li(n,'y',pick),div(li(n,'h',pick),2)),add(v('q'),2))))]),n.change('UI damage slot',1)])]
    insert_before(n,loop,[n.call(PRIVATE),*damage])


def apply_menu_layers(target,assets,*,studio=True):
    """Install the menu stack; call before the shared material API migration."""
    n=UIProgram(target,exporting=not studio)
    if 'UI layer owner' in n.list_ids:raise ValueError('Native menu layers already installed')
    # The subsequent material upgrade defines these public-to-the-kit internal
    # helpers with the same native argument IDs.
    n.declare(SAMPLE,['x','y','blur','background']);n.declare(COMPOSITE,['tint','shine','opacity','red','green','blue','brightness'])
    for name,args in HELPERS.items():n.declare(name,args)
    ls=layer_rows(n);ls.insert(0,n.call(PAGING,arg('owner'),arg('layer')))
    body={RESET:reset(n),BEGIN:begin(n),ROWS:ls,STEP:spring(n),POSE:pose(n),PUSH:push(n),POP:pop(n),HIT:hit(n),
          ROOT:root_ink(n),PANEL:[],LAUNCH:[],SHADE:shade(n),PRIVATE:prepare(n),PAINT:draw_layer(n),TOP:top(n),
          KEY:key(n),MAP:map_cell(n),PAGING:paging(n),TAP:under_tap(n),BASE:base_sample(n),COVER:cover(n),STAMP:protected_stamp(n),CLIP:clipped_wash(n)}
    for j,(code,cmd) in enumerate(body.items()):n.define(code,cmd,(82040+(j%4)*11000,400+(j//4)*15000))
    patch_menu(n);patch_input(n);patch_foreground(n);patch_damage(n);protect_art(n)
    for name,value in SLOT.items():target['lists'][n.storage(name,True)[1]][1]=[value]*8
    target['variables'][n.storage('UI ink opacity')[1]][1]=1
    return target

TAP='UI under tap x %s y %s weight %s';BASE='UI dimmed sample x %s y %s rgb %s'
COVER='UI foreground cover x %s y %s margin %s';STAMP='UI protected stamp';
CLIP='UI covered wash x %s y %s width %s height %s tone %s';
HELPERS.update({TAP:('x','y','weight'),BASE:('x','y','rgb'),COVER:('x','y','margin'),STAMP:(),
                CLIP:('x','y','width','height','tone')})


def under_tap(n):
    v=n.v;word=v('UI tap word');rgb=v('UI tap RGB');a=v('UI tap a')
    return [n.call(MAP,arg('x'),arg('y')),n.set('UI tap word',n.item('UI under surface',v('UI lookup index'))),
            iff(NOT(lt(word,0)),[n.set('UI tap RGB',math('floor',div(word,2))),n.set('UI tap a',mul(sub(word,mul(2,rgb)),arg('weight'))),
                 n.change('UI tap alpha',a),*[n.change('UI tap '+ch,mul(a,unpack(rgb,ch))) for ch in ('R','G','B')]])]


def base_sample(n):
    v=n.v;i=v('UI dim id');o=n.item('UI dim ids',i)
    positive=[n.set('UI dim dx',sub(abs_(sub(arg('x'),n.item('x',o))),sub(div(n.item('w',o),2),n.item('r',o)))),
              n.set('UI dim dy',sub(abs_(sub(arg('y'),n.item('y',o))),sub(div(n.item('h',o),2),n.item('r',o)))),
              iff(NOT(gt(add(square(maximum(0,v('UI dim dx'))),square(maximum(0,v('UI dim dy')))),square(n.item('r',o)))),
                  [n.set('UI dim factor',maximum(v('UI dim factor'),mul(.34,n.item('UI menu dim',o))))])]
    return [n.set('UI base RGB',arg('rgb')),n.set('UI dim factor',0),n.set('UI dim id',1),repeat(n.length('UI dim ids'),[
        *positive,n.change('UI dim id',1)]),iff(gt(v('UI dim factor'),0),[
            *[n.set(ch,rnd(mix(unpack(arg('rgb'),ch),t,v('UI dim factor')))) for ch,t in [('R',36),('G',48),('B',68)]],
            n.set('UI base RGB',add(mul(v('R'),65536),add(mul(v('G'),256),v('B'))))])]


def cover(n):
    v=n.v;i=v('UI front scan');r=li(n,'r',i)
    layer=[n.set('UI cover dx',sub(abs_(sub(arg('x'),li(n,'x',i))),sub(div(li(n,'w',i),2),r))),
           n.set('UI cover dy',sub(abs_(sub(arg('y'),li(n,'y',i))),sub(div(li(n,'h',i),2),r))),
           n.set('UI cover distance',sub(add(math('sqrt',add(square(maximum(0,v('UI cover dx'))),square(maximum(0,v('UI cover dy'))))),
                                              minimum(maximum(v('UI cover dx'),v('UI cover dy')),0)),r)),
           n.set('UI front cover',maximum(v('UI front cover'),mul(clamp1(li(n,'p',i)),
                      clamp1(div(sub(add(arg('margin'),1),v('UI cover distance')),2)))))]
    return [n.set('UI front cover',0),n.set('UI front scan',add(v('UI draw layer'),1)),repeat(sub(count(n),v('UI draw layer')),[
        iff(gt(li(n,'p',i),.001),layer),n.change('UI front scan',1)])]


def protected_stamp(n):
    v=n.v
    return [iff(gt(count(n),v('UI draw layer')),[n.call(COVER,Node('motion_xposition'),Node('motion_yposition'),10),
        iff(lt(v('UI front cover'),.999),[ghost(mul(100,sub(1,mul(v('UI ink opacity'),sub(1,v('UI front cover')))))),Node('pen_stamp')]),
        ghost(mul(100,sub(1,v('UI ink opacity'))))],[Node('pen_stamp')])]


def clipped_wash(n):
    v=n.v;w=arg('width');h=arg('height');x=arg('x');y=arg('y');tone=arg('tone');i=v('UI clip panel');radius=minimum(div(w,2),div(h,2))
    pos=v('UI clip x');stop=v('UI clip stop');cy=v('UI clip y')
    interval=[n.set('UI clip span',rect_extent(n,sub(cy,li(n,'y',i)),li(n,'w',i),li(n,'h',i),li(n,'r',i))),
        n.set('UI clip left',sub(li(n,'x',i),v('UI clip span'))),n.set('UI clip right',add(li(n,'x',i),v('UI clip span'))),
        iff(gt(v('UI clip left'),pos),[n.set('UI clip stop',minimum(stop,v('UI clip left')))],
            [iff(gt(v('UI clip right'),pos),[n.set('UI clip stop',minimum(stop,v('UI clip right'))),
                n.set('UI clip transmission',mul(v('UI clip transmission'),sub(1,clamp1(li(n,'p',i)))))])])]
    draw=[transparency(100),go(add(pos,.5),cy),Node('pen_penDown'),
          transparency(sub(100,mul(v('UI clip ink'),v('UI clip transmission')))),
          go(sub(stop,.5),cy),Node('pen_penUp')]
    segment=[n.set('UI clip stop',v('UI wash right')),n.set('UI clip transmission',1),n.set('UI clip panel',add(v('UI draw layer'),1)),
         repeat(sub(count(n),v('UI draw layer')),[iff(AND(gt(li(n,'p',i),.001),lt(abs_(sub(cy,li(n,'y',i))),div(li(n,'h',i),2))),interval),
            n.change('UI clip panel',1)]),iff(AND(gt(sub(stop,pos),.9),gt(v('UI clip transmission'),.001)),draw),n.set('UI clip x',add(stop,.00001))]
    row=[n.set('UI cover span',rect_extent(n,sub(cy,y),w,h,radius)),n.set('UI clip x',sub(x,v('UI cover span'))),
         n.set('UI wash right',add(x,v('UI cover span'))),until(NOT(lt(pos,v('UI wash right'))),segment),n.change('UI clip y',-1)]
    def color(rgb,alpha):return [Node('pen_setPenColorToColor',{'COLOR':rgb}),n.set('UI clip ink',mul(alpha,v('UI ink opacity')))]
    return [iff(AND(gt(w,0),gt(h,0)),[Node('pen_penUp'),Node('pen_setPenSizeTo',{'SIZE':1}),
        iff(eq(tone,'pressed'),color(0x7cb9ff,45),[iff(eq(tone,'selected'),color(0xa7cbff,28),color(0xe3f4ff,15))]),
        n.set('UI clip y',sub(floor(add(y,div(h,2))),.5)),repeat(floor(h),row),transparency(0)])]


def protect_art(n):
    # Geometry has already been composited in front-to-back order. Fade the
    # earlier glyph underneath the nearest overlapping front footprint. A
    # bounded strip-clipped wash avoids painting hover ink over front glass.
    for code in (labels.TEXT,labels.ICON):
        for ident in procs(n,n.definition(code),'pen_stamp'):
            b=n.blocks[ident];b['opcode']='procedures_call';b['mutation']={k:n.procs[STAMP][k] for k in ('tagName','children','proccode','argumentids','warp')}
    wash=n.definition(labels.WASH);original=n.blocks[wash]['next'];wrapper=n.emit(iff(gt(count(n),n.v('UI draw layer')),
        [n.call(CLIP,*[arg(k) for k in ('x','y','width','height','tone')])]),wash)
    n.blocks[wash]['next']=wrapper;n.blocks[wrapper]['opcode']='control_if_else';n.blocks[wrapper]['inputs']['SUBSTACK2']=[2,original];n.blocks[original]['parent']=wrapper
