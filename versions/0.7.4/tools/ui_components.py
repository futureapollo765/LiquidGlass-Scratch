"""Add native Menu, Button and Background blocks to the existing glass renderer."""
import copy
import hashlib
import json
from .stable_pen import Native, Node, arg, iff, op

GLASS = 'Glass %s x %s y %s width %s height %s shape %s radius %s reflection %s distortion %s edge %s highlight %s light %s tint %s join %s group %s transition %s spring %s damping %s pull %s drag %s quality %s'
MATERIAL = ('reflection', 'distortion', 'edge', 'highlight', 'light', 'tint')
MATERIAL_VALUES = (.50, 1, 1, 1, -30, .08)
BUTTON_NAMES = ('id', 'x', 'y', 'label', 'shape', 'width', 'height', 'radius', 'action', 'pull', 'join', 'group', *MATERIAL, 'quality')
MENU_NAMES = ('id', 'x', 'y', 'label', 'launcher', 'width', 'height', 'panel width', 'row height', 'items', 'mode', 'drag', 'radius', 'pull', 'join', 'group', *MATERIAL, 'quality')
BACKGROUND_NAMES = ('id', 'x', 'y', 'width', 'height', 'radius', 'label', *MATERIAL, 'quality')

def signature(title, names):
    return title + ' %s' + ''.join(' ' + field + ' %s' for field in names[1:])

BUTTON = signature('Button', BUTTON_NAMES)
MENU = signature('Menu', MENU_NAMES)
BACKGROUND = signature('Background', BACKGROUND_NAMES)
BUTTON_DEFAULT = (2, 67, -96, 'Switch background', 'capsule', 158, 42, 16, 'Switch background', 1, 18, 1, *MATERIAL_VALUES, 2)
MENU_DEFAULT = (3, 60, 102, 'Options', 'capsule', 120, 42, 188, 34,
                'Background>Photo|Background>Grid|Detail>Fine|Detail>Balanced|Detail>Fast',
                'toggle', 1, 18, 1, 18, 1, *MATERIAL_VALUES, 2)
BACKGROUND_DEFAULT = (1, -169, 0, 112, 286, 24, 'Library', .42, .85, 1, .72, -36, .12, 2)
POINTER_BROADCAST = 'LG UI pointer down'
ACTIVATION_BROADCAST = 'UI activated'
ROW_LISTS = ('UI row id', 'UI row index', 'UI row label', 'UI row path', 'UI row role')
CANDIDATES = ('UI option label', 'UI option path', 'UI option role')
EDGE_LISTS = ('UI edge kind', 'UI edge x', 'UI edge y', 'UI edge moved')
SLOT_DEFAULT = {
    'UI live': 0, 'UI kind': '', 'UI label': '', 'UI open': 0, 'UI mode': '', 'UI page': '',
    'UI selected path': '', 'UI row height': 0, 'UI row count': 0, 'UI page offset': 0,
    'UI drag enabled': 0, 'UI offset x': 0, 'UI offset y': 0, 'UI button action': '',
    'UI bend x': 0, 'UI bend y': 0,
}
HELPERS = {'UI reset': (), 'UI begin': (), 'UI capture pointer': (), 'UI stage pointer': (),
           'UI edge %s moved %s': ('kind', 'moved'), 'UI input': (), 'UI settle': (),
           'UI rows %s options %s': ('slot', 'options'), 'UI option %s for %s': ('path', 'slot'),
           'UI choose %s row %s': ('slot', 'row'), 'UI fire %s action %s path %s': ('slot', 'action', 'path'),
           'UI back %s': ('slot',), 'UI demo action': ()}


def eq(a,b): return op('equals',a,b)
def lt(a,b): return op('lt',a,b)
def gt(a,b): return op('gt',a,b)
def AND(a,b): return op('and',a,b)
def OR(a,b): return op('or',a,b)
def NOT(a): return Node('operator_not', {'OPERAND': a})
def add(a,b): return op('add',a,b)
def sub(a,b): return op('subtract',a,b)
def mul(a,b): return op('multiply',a,b)
def div(a,b): return op('divide',a,b)
def join(a,b): return op('join',a,b)
def length(a): return Node('operator_length', {'STRING':a})
def letter(i,s): return Node('operator_letter_of', {'LETTER':i,'STRING':s})
def math(name,x): return Node('operator_mathop', {'NUM':x}, {'OPERATOR':[name,None]})
def abs_(a): return math('abs',a)
def rnd(a): return Node('operator_round', {'NUM': a})
def floor(a): return math('floor',a)
def square(a): return mul(a,a)
def maximum(a,b): return div(add(add(a,b),abs_(sub(a,b))),2)
def minimum(a,b): return div(sub(add(a,b),abs_(sub(a,b))),2)
def repeat(n,body): return Node('control_repeat',{'TIMES':n,'SUBSTACK':body})
def until(c,body): return Node('control_repeat_until',{'CONDITION':c,'SUBSTACK':body})
def mouse(): return Node('sensing_mousedown')
def mx(): return Node('sensing_mousex')
def my(): return Node('sensing_mousey')

class UIProgram(Native):
    def __init__(self,target,*,exporting=False):
        super().__init__(target)
        self.exporting = exporting
        existing = [int(k[9:]) for k in self.blocks if k.startswith('lgpresent') and k[9:].isdigit()]
        self.next_id = max(existing, default=0)
        self.procs = {b['mutation']['proccode']: b['mutation'] for b in self.blocks.values()
                      if isinstance(b,dict) and b['opcode']=='procedures_prototype'}
        self.bids = {}
        for name in (POINTER_BROADCAST, ACTIVATION_BROADCAST):
            existing = next((k for k,v in target['broadcasts'].items() if v==name),None)
            key = existing or 'lgui' + hashlib.md5(name.encode()).hexdigest()[:14]
            self.bids[name] = key
            # In a .sprite3 the reference must remain global. Modern Scratch
            # imports an unresolved global onto the destination Stage. Putting
            # it into the sprite's local table would suppress that repair.
            if not self.exporting:
                target['broadcasts'][key] = name

    def declare(self,code,names,defaults=None):
        if code in self.procs:
            raise ValueError(f'Procedure already exists: {code}')
        prefix='ui'+hashlib.md5(code.encode()).hexdigest()[:13]
        ids=[prefix+'a'+str(i) for i in range(len(names))]
        self.procs[code]={'tagName':'mutation','children':[],'proccode':code,'argumentids':json.dumps(ids),
                          'argumentnames':json.dumps(names),'argumentdefaults':json.dumps([str(v) for v in
                            (defaults if defaults is not None else ['']*len(names))]),'warp':'true'}

    def emit(self,node,parent):
        key=super().emit(node,parent)
        if node.opcode == 'event_broadcast':
            input_ = self.blocks[key]['inputs']['BROADCAST_INPUT']
            if self.exporting:
                # Resolve the destination project's global message by name.
                # Keep a canonical obscured dropdown for native Scratch editing.
                name = node.broadcast_name
                input_[:] = [3, input_[1], [11, name, self.bids[name]]]
            else:
                input_[0] = 1
        if hasattr(node,'proc'):
            m=self.procs[node.proc]
            self.blocks[key]['mutation']={k:copy.deepcopy(m[k]) for k in ('tagName','children','proccode','argumentids','warp')}
        return key

    def call(self,code,*args):
        ids=json.loads(self.procs[code]['argumentids'])
        if len(ids)!=len(args): raise ValueError((code,len(ids),len(args)))
        node=Node('procedures_call',dict(zip(ids,args)));node.proc=code
        return node

    def define(self,code,body,position):
        m=self.procs[code]; key='uidef'+hashlib.md5(code.encode()).hexdigest()[:14];proto=key+'p'
        if key in self.blocks:raise ValueError('UI definition ID collision')
        self.blocks[key]={'opcode':'procedures_definition','inputs':{'custom_block':[1,proto]},'fields':{},
                          'next':None,'parent':None,'topLevel':True,'shadow':False,'x':position[0],'y':position[1]}
        self.blocks[proto]={'opcode':'procedures_prototype','inputs':{},'fields':{},'next':None,'parent':key,
                            'topLevel':False,'shadow':True,'mutation':copy.deepcopy(m)}
        for ident,name in zip(json.loads(m['argumentids']),json.loads(m['argumentnames'])):
            reporter=arg(name);reporter.shadow=True
            self.blocks[proto]['inputs'][ident]=[1,self.emit(reporter,proto)]
        if body:self.blocks[key]['next']=self.chain(body,key)[0]
        return key

    def replace(self,name,index,value):
        return self.list_op('data_replaceitemoflist',name,INDEX=index,ITEM=value)

    def clip(self,name,lo,hi):
        return [iff(lt(self.v(name),lo),[self.set(name,lo)]),iff(gt(self.v(name),hi),[self.set(name,hi)])]

    def broadcast(self,name):
        value = join('', name) if self.exporting else [11,name,self.bids[name]]
        node = Node('event_broadcast', {'BROADCAST_INPUT':value})
        node.broadcast_name = name
        return node

    def hat(self,name,node,body,x,y):
        key=self.emit(node,None)
        self.blocks[key].update(topLevel=True,x=x,y=y)
        self.blocks[key]['next']=self.chain(body,key)[0]
        return key


def reset(n):
    stages=[]
    for name,default in SLOT_DEFAULT.items():
        stages.extend([n.clear(name),repeat(8,[n.add(name,default)])])
    for name in ROW_LISTS+CANDIDATES+EDGE_LISTS:stages.append(n.clear(name))
    for name in ('UI down','UI sampled down','UI press serial','UI stage serial','UI pointer moved',
                 'UI hover id','UI hover row','UI pressed id','UI pressed row','UI fired','UI event number','UI source'):
        stages.append(n.set(name,0))
    return stages+[n.set('UI action',''),n.set('UI path','')]


def edge(n):
    return [n.add('UI edge kind',arg('kind')),n.add('UI edge x',mx()),n.add('UI edge y',my()),n.add('UI edge moved',arg('moved'))]


def capture_pointer(n):
    v=n.v
    drift=add(abs_(sub(mx(),v('UI raw x'))),abs_(sub(my(),v('UI raw y'))))
    moved=iff(gt(drift,6),[n.set('UI raw moved',1)])
    return [iff(eq(v('UI view'),1),[iff(mouse(),[
        iff(eq(v('UI sampled down'),0),[n.set('UI sampled down',1),n.change('UI press serial',1),
            n.set('UI raw x',mx()),n.set('UI raw y',my()),n.set('UI raw moved',0),n.call('UI edge %s moved %s',1,0)], [moved])
    ],[iff(eq(v('UI sampled down'),1),[moved,n.set('UI sampled down',0),n.call('UI edge %s moved %s',0,v('UI raw moved'))])])])]


def stage_pointer(n):
    v=n.v
    # The stage event also reaches the VM for fast taps that occur between polls.
    # The serial pair deduplicates a stage notification and a polling down edge.
    return [iff(eq(v('UI view'),1),[n.call('UI capture pointer'),
        iff(gt(v('UI press serial'),v('UI stage serial')),[n.set('UI stage serial',v('UI press serial'))],
            [iff(NOT(mouse()),[n.call('UI edge %s moved %s',1,0),n.call('UI edge %s moved %s',0,0)])])])]


def begin(n):
    v=n.v
    take=[n.set('UI edge',n.item('UI edge kind',1)),n.set('UI down',v('UI edge')),
          n.set('UI pointer x',n.item('UI edge x',1)),n.set('UI pointer y',n.item('UI edge y',1)),
          n.set('UI pointer moved',n.item('UI edge moved',1))]
    take.extend(n.list_op('data_deleteoflist',name,INDEX=1) for name in EDGE_LISTS)
    return [n.call('UI capture pointer'),n.set('UI edge',-1),n.set('UI fired',0),n.set('UI pointer moved',0),
            n.set('UI pointer x',mx()),n.set('UI pointer y',my()),iff(gt(n.length('UI edge kind'),0),take),
            *[n.clear(name) for name in ROW_LISTS],n.set('UI slot',1),
            repeat(8,[n.replace('UI live',v('UI slot'),0),n.change('UI slot',1)])]


def glass(n,x,y,w,h,shape,radius,*,pull=0,group=0,distance=0,smoothing=.25,highlight=None,tint=None):
    return n.call(GLASS,n.v('UI slot'),x,y,w,h,shape,radius,arg('reflection'),arg('distortion'),arg('edge'),
                  arg('highlight') if highlight is None else highlight,arg('light'),
                  arg('tint') if tint is None else tint,distance,group,smoothing,18,.85,pull,0,arg('quality'))


def register(n,kind):
    i=n.v('UI slot')
    return [n.set('UI slot',rnd(arg('id'))),*n.clip('UI slot',1,8),n.replace('UI live',i,1),n.replace('UI label',i,arg('label'))]


def button(n):
    v=n.v;i=v('UI slot');shape=v('UI shape')
    auto=OR(eq(shape,'auto'),eq(shape,''))
    circle=OR(eq(shape,3),eq(shape,'circle'))
    return [*register(n,'Button'),n.replace('UI kind',i,'Button'),n.replace('UI button action',i,arg('action')),
            n.set('UI shape',arg('shape')),n.set('UI width',abs_(arg('width'))),n.set('UI height',abs_(arg('height'))),
            *n.clip('UI height',12,300),iff(auto,[n.set('UI shape',2),iff(lt(length(arg('label')),2),[n.set('UI shape',3)]),
                       iff(gt(length(arg('label')),12),[n.set('UI shape',1)])]),
            iff(eq(v('UI width'),0),[n.set('UI width',maximum(v('UI height'),add(28,mul(7,length(arg('label'))))))]),
            iff(circle,[n.set('UI width',v('UI height'))]),
            n.set('UI growth',1),n.set('UI shine',arg('highlight')),n.set('UI tint',arg('tint')),
            iff(eq(v('UI hover id'),i),[n.set('UI growth',1.05),n.change('UI shine',.25),n.change('UI tint',.035)]),
            iff(eq(v('UI pressed id'),i),[n.set('UI growth',.94),n.change('UI shine',.35),n.change('UI tint',.085)]),
            glass(n,arg('x'),arg('y'),mul(v('UI width'),v('UI growth')),mul(v('UI height'),v('UI growth')),shape,
                  mul(arg('radius'),v('UI growth')),pull=arg('pull'),distance=arg('join'),group=arg('group'),
                  highlight=v('UI shine'),tint=v('UI tint'))]


def background(n):
    return [*register(n,'Background'),n.replace('UI kind',n.v('UI slot'),'Background'),
            glass(n,arg('x'),arg('y'),arg('width'),arg('height'),1,arg('radius'),smoothing=0)]


def option(n):
    v=n.v;p=arg('path');slot=arg('slot')
    prefix=n.item('UI page',slot)
    make_name=[n.set('UI option text',''),n.set('UI at',add(v('UI prefix length'),1)),
               until(OR(gt(v('UI at'),length(p)),eq(letter(v('UI at'),p),'>')),[
                   n.set('UI option text',join(v('UI option text'),letter(v('UI at'),p))),n.change('UI at',1)]),
               n.set('UI option full',join(v('UI prefix'),v('UI option text'))),n.set('UI option type','action'),
               iff(lt(v('UI at'),length(p)),[n.set('UI option type','submenu')]),
               n.set('UI duplicate',n.list_op('data_itemnumoflist','UI option path',ITEM=v('UI option full'))),
               iff(gt(length(v('UI option text')),0),[iff(eq(v('UI duplicate'),0),[
                   n.add('UI option label',v('UI option text')),n.add('UI option path',v('UI option full')),
                   n.add('UI option role',v('UI option type'))],
                   [iff(eq(v('UI option type'),'submenu'),[n.replace('UI option role',v('UI duplicate'),'submenu')])])])]
    return [n.set('UI prefix',''),iff(gt(length(prefix),0),[n.set('UI prefix',join(prefix,'>'))]),
            n.set('UI prefix length',length(v('UI prefix'))),n.set('UI matches',1),n.set('UI at',1),
            repeat(v('UI prefix length'),[iff(NOT(eq(letter(v('UI at'),p),letter(v('UI at'),v('UI prefix')))),
                   [n.set('UI matches',0)]),n.change('UI at',1)]),
            iff(AND(eq(v('UI matches'),1),gt(length(p),v('UI prefix length'))),make_name)]


def rows(n):
    v=n.v;i=arg('slot');source=arg('options');off=n.item('UI page offset',i)
    def emit(label,path,role):
        return [n.change('UI local row',1),n.add('UI row id',i),n.add('UI row index',v('UI local row')),
                n.add('UI row label',label),n.add('UI row path',path),n.add('UI row role',role)]
    return [*[n.clear(name) for name in CANDIDATES],n.set('UI path token',''),n.set('UI path char',1),
        repeat(add(length(source),1),[n.set('UI char',letter(v('UI path char'),source)),
            iff(OR(eq(v('UI char'),'|'),gt(v('UI path char'),length(source))),
                [n.call('UI option %s for %s',v('UI path token'),i),n.set('UI path token','')],
                [n.set('UI path token',join(v('UI path token'),v('UI char')))]),n.change('UI path char',1)]),
        n.set('UI local row',0),n.set('UI row capacity',sub(floor(div(292,n.item('UI row height',i))),1)),
        *n.clip('UI row capacity',2,8),n.set('UI option count',n.length('UI option path')),
        iff(OR(NOT(lt(off,v('UI option count'))),NOT(gt(v('UI option count'),v('UI row capacity')))),
            [n.replace('UI page offset',i,0)]),n.set('UI to show',v('UI option count')),
        iff(gt(v('UI option count'),v('UI row capacity')),[n.set('UI to show',minimum(sub(v('UI row capacity'),1),sub(v('UI option count'),off)))]),
        n.set('UI read option',add(off,1)),repeat(v('UI to show'),[
            *emit(n.item('UI option label',v('UI read option')),n.item('UI option path',v('UI read option')),
                  n.item('UI option role',v('UI read option'))),n.change('UI read option',1)]),
        iff(gt(v('UI option count'),v('UI row capacity')),[*emit('More...','','more')]),
        n.replace('UI row count',i,v('UI local row'))]


def menu(n):
    v=n.v;i=v('UI slot');mode=arg('mode');open_=n.item('UI open',i)
    new=OR(NOT(eq(n.item('UI kind',i),'Menu')),NOT(eq(n.item('UI mode',i),mode)))
    return [*register(n,'Menu'),iff(new,[n.replace('UI open',i,OR(eq(mode,'open'),eq(mode,'panel'))),
              n.replace('UI page',i,''),n.replace('UI page offset',i,0),n.replace('UI offset x',i,0),n.replace('UI offset y',i,0)]),
            n.replace('UI kind',i,'Menu'),n.replace('UI mode',i,mode),n.replace('UI drag enabled',i,arg('drag')),
            n.set('UI pitch',abs_(arg('row height'))),*n.clip('UI pitch',16,72),n.replace('UI row height',i,v('UI pitch')),
            n.set('UI width',abs_(arg('width'))),n.set('UI height',abs_(arg('height'))),*n.clip('UI height',12,300),
            n.set('UI shape',arg('launcher')),n.set('UI cy',add(arg('y'),n.item('UI offset y',i))),
            iff(OR(eq(v('UI shape'),3),eq(v('UI shape'),'circle')),[n.set('UI width',v('UI height'))]),
            iff(eq(open_,1),[n.call('UI rows %s options %s',i,arg('items')),n.set('UI shape',1),n.set('UI width',arg('panel width')),
                n.set('UI panel height',mul(add(n.item('UI row count',i),1),v('UI pitch'))),
                n.change('UI cy',div(sub(v('UI height'),v('UI panel height')),2)),n.set('UI height',v('UI panel height'))],
                [n.replace('UI row count',i,0)]),
            n.set('UI cx',add(arg('x'),n.item('UI offset x',i))),
            *n.clip('UI cx',add(-240,div(v('UI width'),2)),sub(240,div(v('UI width'),2))),
            *n.clip('UI cy',add(-180,div(v('UI height'),2)),sub(180,div(v('UI height'),2))),
            n.set('UI shine',arg('highlight')),iff(eq(v('UI hover id'),i),[n.change('UI shine',.12)]),
            glass(n,v('UI cx'),v('UI cy'),v('UI width'),v('UI height'),v('UI shape'),arg('radius'),pull=arg('pull'),
                  group=arg('group'),distance=arg('join'),smoothing=.36,highlight=v('UI shine'))]


def back(n):
    v=n.v;p=n.item('UI page',arg('slot'))
    return [n.set('UI back at',0),n.set('UI back char',1),repeat(length(p),[
        iff(eq(letter(v('UI back char'),p),'>'),[n.set('UI back at',v('UI back char'))]),n.change('UI back char',1)]),
        n.set('UI parent',''),n.set('UI back char',1),repeat(maximum(0,sub(v('UI back at'),1)),[
            n.set('UI parent',join(v('UI parent'),letter(v('UI back char'),p))),n.change('UI back char',1)]),
        n.replace('UI page',arg('slot'),v('UI parent')),n.replace('UI page offset',arg('slot'),0)]


def fire(n):
    return [n.set('UI fired',1),n.change('UI event number',1),n.set('UI source',arg('slot')),
            n.set('UI action',arg('action')),n.set('UI path',arg('path')),
            n.replace('UI selected path',arg('slot'),arg('path')),n.broadcast(ACTIVATION_BROADCAST)]


def choose(n):
    v=n.v;i=arg('slot');row=arg('row');kind=n.item('UI kind',i);flat=v('UI flat row')
    head=[iff(AND(eq(n.item('UI open',i),1),gt(length(n.item('UI page',i)),0)),[n.call('UI back %s',i)],
              [iff(NOT(eq(n.item('UI mode',i),'panel')),[n.replace('UI open',i,sub(1,n.item('UI open',i))),
                    n.replace('UI page',i,''),n.replace('UI page offset',i,0)])])]
    role=n.item('UI row role',flat);path=n.item('UI row path',flat)
    select=[n.set('UI flat row',1),repeat(n.length('UI row id'),[
        iff(AND(eq(n.item('UI row id',flat),i),eq(n.item('UI row index',flat),row)),[
            iff(eq(role,'submenu'),[n.replace('UI page',i,path),n.replace('UI page offset',i,0)],
                [iff(eq(role,'more'),[n.replace('UI page offset',i,add(n.item('UI page offset',i),sub(n.item('UI row count',i),1)))],
                     [n.call('UI fire %s action %s path %s',i,path,path),n.replace('UI page',i,''),
                      n.replace('UI page offset',i,0),iff(NOT(eq(n.item('UI mode',i),'panel')),[n.replace('UI open',i,0)])])])]),
        n.change('UI flat row',1)])]
    return [iff(eq(kind,'Button'),[n.call('UI fire %s action %s path %s',i,n.item('UI button action',i),'')]),
            iff(eq(kind,'Menu'),[iff(eq(row,0),head,select)])]


def ui_input(n):
    v=n.v;i=v('UI scan');pressed=v('UI pressed id');hover=v('UI hover id')
    point_x=v('UI pointer x');point_y=v('UI pointer y')
    hit=[n.call('LG shape %s %s %s',i,point_x,point_y),iff(lt(v('sd'),0),[n.set('UI hover id',i),n.set('UI hover row',0),
        iff(AND(eq(n.item('UI kind',i),'Menu'),eq(n.item('UI open',i),1)),[
            n.set('UI local y',sub(point_y,n.item('y',i))),iff(gt(n.item('amp',i),.02),[
                n.set('UI local y',div(v('UI local y'),n.item('scaleY',i)))]),
            n.set('UI hover row',floor(div(sub(div(n.item('h',i),2),v('UI local y')),n.item('UI row height',i)))),
            iff(gt(v('UI hover row'),n.item('UI row count',i)),[n.set('UI hover id',0),n.set('UI hover row',0)])])])]
    down=[n.set('UI scan',1),repeat(8,[iff(AND(NOT(eq(i,hover)),AND(eq(n.item('UI kind',i),'Menu'),
             NOT(eq(n.item('UI mode',i),'panel')))),[n.replace('UI open',i,0),n.replace('UI page',i,''),n.replace('UI page offset',i,0)]),n.change('UI scan',1)]),
          n.set('UI pressed id',hover),n.set('UI pressed row',v('UI hover row')),n.set('UI down x',point_x),n.set('UI down y',point_y),
          n.set('UI moved',0),iff(gt(pressed,0),[n.set('UI base x',n.item('UI offset x',pressed)),n.set('UI base y',n.item('UI offset y',pressed))])]
    delta_x=sub(point_x,v('UI down x'));delta_y=sub(point_y,v('UI down y'))
    tracking=[iff(OR(eq(v('UI pointer moved'),1),gt(add(abs_(delta_x),abs_(delta_y)),6)),[n.set('UI moved',1)]),
        iff(AND(eq(n.item('UI kind',pressed),'Menu'),AND(eq(n.item('UI drag enabled',pressed),1),
              AND(eq(v('UI pressed row'),0),eq(v('UI moved'),1)))),[
                  n.replace('UI offset x',pressed,add(v('UI base x'),delta_x)),n.replace('UI offset y',pressed,add(v('UI base y'),delta_y))])]
    release=[iff(AND(gt(pressed,0),AND(eq(pressed,hover),AND(eq(v('UI pressed row'),v('UI hover row')),eq(v('UI moved'),0)))),
                 [n.call('UI choose %s row %s',pressed,v('UI pressed row'))]),n.set('UI pressed id',0),n.set('UI pressed row',0)]
    return [n.set('UI hover id',0),n.set('UI hover row',0),n.set('UI scan',8),repeat(8,[
            iff(eq(n.item('UI live',i),0),[iff(NOT(eq(n.item('UI kind',i),'')),[n.replace('active',i,0),n.replace('UI kind',i,'')])],
                [iff(AND(eq(hover,0),NOT(eq(n.item('UI kind',i),'Background'))),hit)]),n.change('UI scan',-1)]),
            iff(eq(v('UI edge'),1),down),iff(gt(pressed,0),tracking),iff(eq(v('UI edge'),0),release)]


def settle(n):
    v=n.v;i=v('UI settle id')
    button=[n.set('UI target bend x',0),n.set('UI target bend y',0)]
    bend=[]
    for axis,dim in [('x','w'),('y','h')]:
        delta=abs_(sub(v('UI pointer '+axis),v('UI down '+axis)))
        bend.append(n.set('UI target bend '+axis,minimum(.60,mul(div(delta,maximum(8,n.item(dim,i))),n.item('pull',i)))))
    button.append(iff(AND(eq(v('UI pressed id'),i),eq(v('UI down'),1)),bend))
    for axis in ['x','y']:
        name='UI bend '+axis;value=n.item(name,i)
        button.extend([n.replace(name,i,add(value,mul(sub(v('UI target bend '+axis),value),v('UI relax')))),
                       iff(lt(n.item(name,i),.00075),[n.replace(name,i,0)])])
    bx=n.item('UI bend x',i);by=n.item('UI bend y',i)
    button.extend([n.replace('scaleX',i,div(add(1,bx),add(1,maximum(0,sub(by,bx))))),
                   n.replace('scaleY',i,div(add(1,by),add(1,maximum(0,sub(bx,by))))),
                   n.replace('amp',i,maximum(div(mul(abs_(sub(n.item('scaleX',i),1)),n.item('w',i)),2),
                                             div(mul(abs_(sub(n.item('scaleY',i),1)),n.item('h',i)),2)))])
    fixed=[n.replace('x',i,n.item('tx',i)),n.replace('y',i,n.item('ty',i)),
           n.replace('vx',i,0),n.replace('vy',i,0)]
    return [n.set('UI relax',sub(1,math('e ^',mul(-20,v('dt'))))),n.set('UI settle id',1),repeat(8,[
        iff(AND(eq(n.item('UI live',i),1),eq(n.item('UI kind',i),'Button')),fixed+button),n.change('UI settle id',1)])]


def demo_calls(n):
    def configured(code,names,defaults):
        values=list(defaults)
        for prop in (*MATERIAL,'quality'):
            values[names.index(prop)]=n.v(prop.capitalize())
        return n.call(code,*values)
    return [configured(BACKGROUND,BACKGROUND_NAMES,BACKGROUND_DEFAULT),configured(BUTTON,BUTTON_NAMES,BUTTON_DEFAULT),
            configured(MENU,MENU_NAMES,MENU_DEFAULT)]


def embed_main(n,studio):
    b=n.blocks
    hats=[key for key,block in b.items() if isinstance(block,dict) and block['opcode']=='event_whenflagclicked']
    if len(hats)!=1:raise ValueError('Expected the original renderer green flag')
    hat=hats[0];initializer=b[hat]['next'];forever=b[initializer]['next'];setup=None
    if not studio:
        setup=forever;forever=b[setup]['next']
    if b[forever]['opcode']!='control_forever':raise ValueError('Expected renderer forever loop')
    old=b[forever]['inputs']['SUBSTACK'][1];tail=old
    while b[tail]['next']:tail=b[tail]['next']
    if b[tail]['opcode']!='control_wait':raise ValueError('Expected original loop yield')
    last=b[tail]['parent'];b[last]['next']=None
    branch=[n.call('UI begin'),*demo_calls(n),n.call('UI input')]
    if studio:branch.append(n.call('UI demo action'))
    branch += [n.call('LG advance'),n.call('UI settle'),n.call('LG render'),n.call('UI release buffers')]
    switch=n.emit(iff(eq(n.v('UI view'),1),branch),forever);b[switch]['opcode']='control_if_else'
    b[forever]['inputs']['SUBSTACK']=[2,switch]
    if studio:
        b[switch]['inputs']['SUBSTACK2']=[2,old];b[old]['parent']=switch
    else:
        setup_if=n.emit(iff(eq(n.v('UI legacy setup'),1),[n.set('UI legacy setup',0)]),switch)
        resetflag=b[setup_if]['inputs']['SUBSTACK'][1];b[resetflag]['next']=setup;b[setup]['parent']=resetflag;b[setup]['next']=None
        b[switch]['inputs']['SUBSTACK2']=[2,setup_if];b[setup_if]['next']=old;b[old]['parent']=setup_if
    b[switch]['next']=tail;b[tail]['parent']=switch
    n.attach(initializer,[n.set('UI view',1)],forever)
    comment=b[hat].get('comment')
    if comment in n.target['comments']:
        n.target['comments'][comment]['text']='START HERE • Edit Background, Button and Menu in the green-flag loop. G switches to/from the original Glass demo. Buttons activate on release; menu paths use | between choices and > between levels.'
    # Each initialize resets the view's data but preserves the selected view.
    init=n.definition('LG initialize');n.attach(n.sequence(init)[-1],[n.call('UI reset'),n.set('UI legacy setup',1)],None)
    n.hat('pointer sampler',Node('event_whenflagclicked'),[Node('control_forever',{'SUBSTACK':[n.call('UI capture pointer'),Node('control_wait',{'DURATION':0})]})],40,30000)
    n.hat('stage pointer',Node('event_whenbroadcastreceived',fields={'BROADCAST_OPTION':[POINTER_BROADCAST,n.bids[POINTER_BROADCAST]]}),[n.call('UI stage pointer')],800,30000)
    n.hat('switch view',Node('event_whenkeypressed',fields={'KEY_OPTION':['g',None]}),[n.set('UI view',sub(1,n.v('UI view'))),n.call('LG initialize')],1600,30000)
    if not studio:n.hat('reset',Node('event_whenkeypressed',fields={'KEY_OPTION':['r',None]}),[n.call('LG initialize')],2400,30000)


def apply_target(target,*,studio=True):
    """Install UI blocks into one 0.3.0 renderer target in place."""
    n=UIProgram(target,exporting=not studio)
    for code,names,defaults in ((MENU,MENU_NAMES,MENU_DEFAULT),(BUTTON,BUTTON_NAMES,BUTTON_DEFAULT),
                                (BACKGROUND,BACKGROUND_NAMES,BACKGROUND_DEFAULT)):
        n.declare(code,names,defaults)
    for name,params in HELPERS.items():n.declare(name,params)
    n.declare('UI release buffers',())
    code={MENU:menu(n),BUTTON:button(n),BACKGROUND:background(n),'UI begin':begin(n),'UI reset':reset(n),
          'UI capture pointer':capture_pointer(n),'UI stage pointer':stage_pointer(n),'UI input':ui_input(n),
          'UI settle':settle(n),'UI edge %s moved %s':edge(n),'UI rows %s options %s':rows(n),
          'UI option %s for %s':option(n),'UI back %s':back(n),'UI choose %s row %s':choose(n),
          'UI fire %s action %s path %s':fire(n),'UI demo action':[],
          'UI release buffers':[n.clear(name) for name in ('field','pixelBand','pixelDistortion','pixelEdge','pixelHighlight','pixelLightX','pixelLightY','pixelTint')]}
    for j,(name,body) in enumerate(code.items()):n.define(name,body,(24040+(j%3)*8000,2400+(j//3)*5500))
    # Initialize new storage declarations in the file as well as on green flag.
    for name,value in SLOT_DEFAULT.items():target['lists'][n.storage(name,True)[1]][1]=[value]*8
    embed_main(n,studio)
    return target
