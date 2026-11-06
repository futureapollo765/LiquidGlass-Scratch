#!/usr/bin/env python3
"""Build native Scratch 3 blocks. Python is an authoring tool, never a runtime dependency."""
import json, math, hashlib, zipfile, struct, zlib, copy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCE = ROOT / 'inputs' / 'EffOnly_reference.sb3'
if not SOURCE.is_file():
    candidates = sorted((ROOT / 'versions').glob('*/inputs/EffOnly_reference.sb3'))
    if ROOT.parent.name == 'versions':
        candidates += sorted(ROOT.parent.glob('*/inputs/EffOnly_reference.sb3'))
    if candidates:
        SOURCE = candidates[0]
class E:
 def __init__(self,op,inputs=None,fields=None):self.op,self.inputs,self.fields=op,inputs or {},fields or {}
 def __add__(s,o):return binary('add',s,o)
 def __radd__(s,o):return binary('add',o,s)
 def __sub__(s,o):return binary('subtract',s,o)
 def __rsub__(s,o):return binary('subtract',o,s)
 def __mul__(s,o):return binary('multiply',s,o)
 def __rmul__(s,o):return binary('multiply',o,s)
 def __truediv__(s,o):return binary('divide',s,o)
 def __rtruediv__(s,o):return binary('divide',o,s)
 def __neg__(s):return 0-s

def binary(op,a,b):return E('operator_'+op,{'NUM1':a,'NUM2':b})
def lt(a,b):return E('operator_lt',{'OPERAND1':a,'OPERAND2':b})
def gt(a,b):return E('operator_gt',{'OPERAND1':a,'OPERAND2':b})
def eq(a,b):return E('operator_equals',{'OPERAND1':a,'OPERAND2':b})
def And(a,b):return E('operator_and',{'OPERAND1':a,'OPERAND2':b})
def Or(a,b):return E('operator_or',{'OPERAND1':a,'OPERAND2':b})
def Not(a):return E('operator_not',{'OPERAND':a})
def m(op,a):return E('operator_mathop',{'NUM':a},{'OPERATOR':[op,None]})
def abs_(a):return m('abs',a)
def sqrt(a):return m('sqrt',a)
def rnd(a):return E('operator_round',{'NUM':a})
def mod(a,b):return binary('mod',a,b)
def max_(a,b):return (a+b+abs_(a-b))/2 if isinstance(a,E) else (b+a+abs_(b-a))/2
# These algebraic min/max use only documented operators.
def min_(a,b):return (a+b-abs_(a-b))/2 if isinstance(a,E) else (b+a-abs_(b-a))/2
def clamp(a,lo,hi):return min_(max_(a,lo),hi)
def sq(a):return a*a
def a(name):return E('argument_reporter_string_number',fields={'VALUE':[name,None]})
def v(name):return E('data_variable',fields={'VARIABLE':[name,'v_'+name]})
def item(name,index):return E('data_itemoflist',{'INDEX':index},{'LIST':[name,'l_'+name]})
def length(name):return E('data_lengthoflist',fields={'LIST':[name,'l_'+name]})
def set_(name,value):return E('data_setvariableto',{'VALUE':value},{'VARIABLE':[name,'v_'+name]})
def change(name,value):return E('data_changevariableby',{'VALUE':value},{'VARIABLE':[name,'v_'+name]})
def add(name,value):return E('data_addtolist',{'ITEM':value},{'LIST':[name,'l_'+name]})
def replace(name,i,value):return E('data_replaceitemoflist',{'INDEX':i,'ITEM':value},{'LIST':[name,'l_'+name]})
def clear(name):return E('data_deletealloflist',fields={'LIST':[name,'l_'+name]})
def iff(cond,yes,no=None):return E('control_if_else' if no is not None else 'control_if',{'CONDITION':cond,'SUBSTACK':yes,**({'SUBSTACK2':no} if no is not None else {})})
def repeat(n,body):return E('control_repeat',{'TIMES':n,'SUBSTACK':body})
def until(c,body):return E('control_repeat_until',{'CONDITION':c,'SUBSTACK':body})
def key(k):return E('sensing_keypressed',{'KEY_OPTION':E('sensing_keyoptions',fields={'KEY_OPTION':[k,None]})})
def mouse():return E('sensing_mousedown')
def mx():return E('sensing_mousex')
def my():return E('sensing_mousey')
def timer():return E('sensing_timer')
def go(x,y):return E('motion_gotoxy',{'X':x,'Y':y})
def penparam(name,value):return E('pen_setPenColorParamTo',{'COLOR_PARAM':E('pen_menu_colorParam',fields={'colorParam':[name,None]}),'VALUE':value})

class Builder:
 def __init__(self):self.blocks={};self.vars={};self.lists={};self.procs={};self.comments={};self.n=0
 def uid(self):self.n+=1;return 'b'+str(self.n)
 def emit(self,e,parent=None,shadow=False):
  i=self.uid();b={'opcode':e.op,'next':None,'parent':parent,'inputs':{},'fields':copy.deepcopy(e.fields),'shadow':shadow,'topLevel':False};self.blocks[i]=b
  for k,field in e.fields.items():
   if k=='VARIABLE':self.vars.setdefault(field[1],[field[0],0])
   if k=='LIST':self.lists.setdefault(field[1],[field[0],[]])
  for k,value in e.inputs.items():
   if k.startswith('SUBSTACK'):
    if value:b['inputs'][k]=[2,self.stack(value,i)]
   elif isinstance(value,E):
    sh=value.op in ('sensing_keyoptions','pen_menu_colorParam','looks_costume','looks_backdrops')
    sub=self.emit(value,i,sh)
    b['inputs'][k]=[1 if sh else 2,sub]
   else:b['inputs'][k]=[1,[4 if isinstance(value,(int,float)) else 10,str(value)]]
  return i
 def stack(self,body,parent=None):
  first=None;prev=parent
  for e in body:
   i=self.emit(e,prev)
   if first is None:first=i
   else:self.blocks[prev]['next']=i
   prev=i
  return first
 def declare(self,code,names):self.procs[code]=names
 def argids(self,code):return ['p'+hashlib.md5(code.encode()).hexdigest()[:12]+'_'+str(j) for j in range(len(self.procs[code]))]
 def call(self,code,*values):
  assert len(values)==len(self.procs[code]),(code,len(values))
  return E('procedures_call',{key:value for key,value in zip(self.argids(code),values)}, {'__proc__':code})
 def define(self,code,body,x,y,comment=''):
  names=self.procs[code];di=self.uid();pi=self.uid()
  self.blocks[di]={'opcode':'procedures_definition','next':None,'parent':None,'inputs':{'custom_block':[1,pi]},'fields':{},'shadow':False,'topLevel':True,'x':x,'y':y}
  defaults=[1,0,0,156,96,1,24,0.5,1,1,1,-30,0.05,30,1,0.45,18,0.85,0.9,1,2] if code.startswith('Glass ') else ['']*len(names)
  mut={'tagName':'mutation','children':[],'proccode':code,'argumentids':json.dumps(self.argids(code)),'argumentnames':json.dumps(names),'argumentdefaults':json.dumps([str(value) for value in defaults]),'warp':'true'}
  self.blocks[pi]={'opcode':'procedures_prototype','next':None,'parent':di,'inputs':{},'fields':{},'shadow':True,'topLevel':False,'mutation':mut}
  for key,name in zip(self.argids(code),names):self.blocks[pi]['inputs'][key]=[1,self.emit(a(name),pi,True)]
  self.blocks[di]['next']=self.stack(body,di)
  if comment:self.comment(di,comment)
 def top(self,hat,body,x,y,comment=''):
  i=self.emit(hat);self.blocks[i].update(topLevel=True,x=x,y=y);self.blocks[i]['next']=self.stack(body,i)
  if comment:self.comment(i,comment)
 def comment(self,block,text):
  i='c'+str(len(self.comments));self.blocks[block]['comment']=i;self.comments[i]={'blockId':block,'x':None,'y':None,'width':420,'height':200,'minimized':True,'text':text}
 def finish(self):
  for b in self.blocks.values():
   if b['opcode']=='procedures_call' and '__proc__' in b['fields']:
    code=b['fields'].pop('__proc__');b['mutation']={'tagName':'mutation','children':[],'proccode':code,'argumentids':json.dumps(self.argids(code)),'warp':'true'}

B=Builder();call=B.call
API='Glass %s x %s y %s width %s height %s shape %s radius %s reflection %s distortion %s edge %s highlight %s light %s tint %s join %s group %s transition %s spring %s damping %s pull %s drag %s quality %s'
B.declare(API,['id','x','y','width','height','shape','radius','reflection','distortion','edge','highlight','light','tint','join','group','transition','spring','damping','pull','drag','quality'])
for code,names in [('LG initialize',[]),('LG advance',[]),('LG render',[]),('LG field %s %s',['x','y']),('LG shape %s %s %s',['i','x','y']),('LG shade %s %s %s',['x','y','cell']),('LG background %s %s',['x','y']),('LG demo',[])]:B.declare(code,names)
state=['active','tx','ty','tw','th','tr','x','y','w','h','r','vx','vy','px','py','scaleX','scaleY','amp','reflection','distortion','edge','highlight','light','tint','join','group','transition','spring','damping','pull','drag','quality']
# Public component API: upsert one target with all settings, no source edits required.
body=[set_('id',clamp(rnd(a('id')),1,8)),set_('targetW',clamp(abs_(a('width')),8,440)),set_('targetH',clamp(abs_(a('height')),8,300)),set_('targetR',max_(a('radius'),0)),
 iff(Or(eq(a('shape'),3),eq(a('shape'),'circle')),[set_('targetH',v('targetW')),set_('targetR',v('targetW')/2)],
 [iff(Or(eq(a('shape'),2),eq(a('shape'),'capsule')),[set_('targetR',min_(v('targetW'),v('targetH'))/2)])]),set_('targetR',min_(v('targetR'),min_(v('targetW'),v('targetH'))/2)),
 iff(eq(item('active',v('id')),0),[replace('x',v('id'),a('x')),replace('y',v('id'),a('y')),replace('w',v('id'),v('targetW')),replace('h',v('id'),v('targetH')),replace('r',v('id'),v('targetR'))]),replace('active',v('id'),1-Or(eq(a('shape'),0),eq(a('shape'),'hidden')))]
for name,value in [('tx',a('x')),('ty',a('y')),('tw',v('targetW')),('th',v('targetH')),('tr',v('targetR')),('reflection',clamp(a('reflection'),0,1)),('distortion',clamp(a('distortion'),-3,3)),('edge',clamp(a('edge'),0,6)),('highlight',clamp(a('highlight'),0,3)),('light',a('light')),('tint',clamp(a('tint'),0,0.75)),('join',clamp(a('join'),0,60)),('group',a('group')),('transition',clamp(a('transition'),0,3)),('spring',clamp(a('spring'),1,40)),('damping',clamp(a('damping'),0.1,2)),('pull',clamp(a('pull'),0,2)),('drag',a('drag')),('quality',clamp(rnd(a('quality')),1,4))]:body.append(replace(name,v('id'),value))
B.define(API,body,30,700,'PUBLIC API • id 1–8. Call once to create; call again with the same id to animate new targets. Full width/height in stage pixels. Shape: 1/rounded rectangle, 2/capsule, 3/circle (width is diameter), 0/hidden. Reflection, edge and light retain EffOnly meanings. Same nonzero group joins; group 0 isolates. transition seconds (0 snaps), spring Hz-like rate, damping ratio, pull gain, drag 0/1, quality pixel step 1–4. Component settings live here, never in helper source. The main loop must keep LG advance + LG render running; demo calls are examples and may be replaced.')
init=[E('looks_hide'),E('pen_penUp'),E('motion_setrotationstyle',fields={'STYLE':["don't rotate",None]}),E('looks_setsizeto',{'SIZE':100})]
for name in state:init += [clear(name),repeat(8,[add(name,0)])]
for name in ['field','owner']:init.append(clear(name))
for name,val in [('grab',0),('wasDown',0),('lastTime',0),('Frames',0),('FPS',0),('fpsTime',0),('fpsFrames',0),('Menu',0),('Shape',1),('Reflection',0.5),('Distortion',1),('Edge',1),('Highlight',1),('Light',-30),('Tint',0.05),('Join',30),('Pull',0.9),('Quality',2),('Background',1),('Controls',0),('Auto',0),('PullDemo',0),('demoX1',-90),('demoY1',10),('demoX2',85),('demoY2',10),('demoX3',20),('demoY3',-100)]:init.append(set_(name,val))
init.append(E('sensing_resettimer'));B.define('LG initialize',init,30,1600)
# Time-based geometry transitions, critically damped translation, elastic release.
i=v('i');dt=v('dt')
advance=[set_('now',timer()),set_('dt',clamp(v('now')-v('lastTime'),0.008,0.05)),set_('lastTime',v('now')),
 iff(And(mouse(),eq(v('wasDown'),0)),[set_('i',8),repeat(8,[iff(And(eq(v('grab'),0),And(eq(item('active',i),1),eq(item('drag',i),1))),[call('LG shape %s %s %s',i,mx(),my()),iff(lt(v('sd'),0),[set_('grab',i),set_('grabDX',item('x',i)-mx()),set_('grabDY',item('y',i)-my())])]),change('i',-1)])]),
 iff(Not(mouse()),[set_('grab',0)]),set_('wasDown',mouse()),set_('i',1),repeat(8,[iff(eq(item('active',i),1),[
 set_('blend',1),iff(gt(item('transition',i),0),[set_('blend',1-m('e ^',(-4.6*dt)/max_(0.01,item('transition',i))))]),
 *[replace(n,i,item(n,i)+(item(t,i)-item(n,i))*v('blend')) for n,t in [('w','tw'),('h','th'),('r','tr')]],
 set_('destX',item('tx',i)),set_('destY',item('ty',i)),
 iff(eq(v('grab'),i),[set_('destX',clamp(mx()+v('grabDX'),-220,220)),set_('destY',clamp(my()+v('grabDY'),-150,125)),replace('tx',i,v('destX')),replace('ty',i,v('destY')),
 *[iff(eq(i,j),[set_(f'demoX{j}',v('destX')),set_(f'demoY{j}',v('destY'))]) for j in range(1,4)]]),
 # stable semi-implicit substeps preserve spring behavior at coarse frame rates
 repeat(3,[set_('omega',item('spring',i)),set_('subdt',dt/3),
 *[replace(vel,i,(item(vel,i)+(v(dest)-item(pos,i))*sq(v('omega'))*v('subdt'))/(1+2*item('damping',i)*v('omega')*v('subdt'))) for pos,vel,dest in [('x','vx','destX'),('y','vy','destY')]],
 *[replace(pos,i,item(pos,i)+item(vel,i)*v('subdt')) for pos,vel in [('x','vx'),('y','vy')]]]),
 iff(eq(item('transition',i),0),[replace('x',i,v('destX')),replace('y',i,v('destY')),replace('vx',i,0),replace('vy',i,0)]),
 set_('wantPX',item('vx',i)*0.08*item('pull',i)),set_('wantPY',item('vy',i)*0.08*item('pull',i)),
 *[replace(n,i,item(n,i)+(v(t)-item(n,i))*(1-m('e ^',-14*dt))) for n,t in [('px','wantPX'),('py','wantPY')]],
 set_('pullX',abs_(item('px',i))),set_('pullY',abs_(item('py',i))),
 set_('drawX',min_(v('pullX')/max_(4,item('w',i)/2),0.65)),set_('drawY',min_(v('pullY')/max_(4,item('h',i)/2),0.65)),
 set_('squeezeX',clamp(1-v('pullX')/max_(0.001,v('pullY')),0,1)),set_('squeezeY',clamp(1-v('pullY')/max_(0.001,v('pullX')),0,1)),
 set_('squeezeX',sq(v('squeezeX'))*(3-2*v('squeezeX'))),set_('squeezeY',sq(v('squeezeY'))*(3-2*v('squeezeY'))),
 replace('scaleX',i,(1+v('drawX'))/(1+v('drawY')*v('squeezeX'))),replace('scaleY',i,(1+v('drawY'))/(1+v('drawX')*v('squeezeY'))),
 replace('amp',i,max_(abs_(item('scaleX',i)-1)*item('w',i)/2,abs_(item('scaleY',i)-1)*item('h',i)/2))
 ]),change('i',1)])]
B.define('LG advance',advance,1200,1600,'Translation follows the target normally. Deformation uses separate horizontal and vertical pull channels, never a rotated or sheared axis. Pure horizontal/vertical motion retains stretch plus reciprocal cross-squeeze. Cross-squeeze fades when the other axis also moves, so diagonal movement combines both stretches instead of cancelling them. Scales are capped at 1.65; both sides change equally and relax after release.')
# World-axis deformation: the off-diagonal transform entries are always zero.
# No rotation or shear can appear even when both motion channels are active.
j=a('i');x=a('x');y=a('y')
shape=[set_('lx',x-item('x',j)),set_('ly',y-item('y',j)),set_('deformed',gt(item('amp',j),0.02)),
 iff(gt(v('deformed'),0),[set_('lx',v('lx')/item('scaleX',j)),set_('ly',v('ly')/item('scaleY',j))]),
 set_('qx',abs_(v('lx'))-item('w',j)/2+item('r',j)),set_('qy',abs_(v('ly'))-item('h',j)/2+item('r',j)),set_('ox',max_(v('qx'),0)),set_('oy',max_(v('qy'),0)),set_('outside',sqrt(sq(v('ox'))+sq(v('oy')))),set_('sd',v('outside')+min_(max_(v('qx'),v('qy')),0)-item('r',j)),
 set_('sx',1-2*lt(v('lx'),0)),set_('sy',1-2*lt(v('ly'),0)),
 iff(gt(v('outside'),0.0001),[set_('nx',v('sx')*v('ox')/v('outside')),set_('ny',v('sy')*v('oy')/v('outside'))],[iff(gt(v('qx'),v('qy')),[set_('nx',v('sx')),set_('ny',0)],[set_('nx',0),set_('ny',v('sy'))])]),
 iff(gt(v('deformed'),0),[set_('gs',v('nx')/item('scaleX',j)),set_('gt',v('ny')/item('scaleY',j)),set_('gn',max_(0.2,sqrt(sq(v('gs'))+sq(v('gt'))))),set_('nx',v('gs')/v('gn')),set_('ny',v('gt')/v('gn')),set_('sd',v('sd')/v('gn'))])]
B.define('LG shape %s %s %s',shape,2400,1600,'One rounded-box contour covers all shapes. Centered pull maps x to scaleX*x and y to scaleY*y only. There are no off-diagonal terms: rectangles stay level, circles stay axis-aligned ellipses, and capsules cannot tilt or shear. Opposite sides are symmetric. Inverse coordinates and inverse-transpose normals deform the contour, rim and refraction together; configured width/height stay unchanged.')
# Cache frame-invariant geometry once. Standalone LG field remains fresh and safe;
# the renderer uses LG sample repeatedly after a single LG prepare call.
B.declare('LG prepare',[])
B.declare('LG sample %s %s',['x','y'])
for name in ['sampleD','sampleNX','sampleNY']:B.lists['l_'+name]=[name,[0]*8]
pair_lists=['pairA','pairB','pairReach','pairLeft','pairRight','pairBottom','pairTop','pairInvBand']
prepare=[clear('activeIDs'),*[clear(name) for name in pair_lists],set_('j',1),repeat(8,[iff(eq(item('active',v('j')),1),[add('activeIDs',v('j'))]),change('j',1)]),
 set_('activeCount',length('activeIDs')),set_('ai',1),repeat(v('activeCount'),[set_('j',item('activeIDs',v('ai'))),
 iff(And(gt(item('join',v('j')),0),Not(eq(item('group',v('j')),0))),[
 set_('bi',v('ai')+1),repeat(v('activeCount')-v('ai'),[set_('k',item('activeIDs',v('bi'))),
 iff(And(eq(item('group',v('j')),item('group',v('k'))),gt(item('join',v('k')),0)),[
 set_('cx',item('x',v('k'))-item('x',v('j'))),set_('cy',item('y',v('k'))-item('y',v('j'))),set_('cd',sqrt(sq(v('cx'))+sq(v('cy')))),
 iff(gt(v('cd'),0.01),[set_('reach',2*min_(item('join',v('j')),item('join',v('k')))),
 set_('separation',clamp(v('cd')/v('reach'),0,1)),set_('reach',v('reach')*sq(v('separation'))*(3-2*v('separation'))),
 add('pairA',v('j')),add('pairB',v('k')),add('pairReach',v('reach')),
 add('pairLeft',min_(item('x',v('j'))-item('w',v('j'))/2-2*item('amp',v('j')),item('x',v('k'))-item('w',v('k'))/2-2*item('amp',v('k')))),
 add('pairRight',max_(item('x',v('j'))+item('w',v('j'))/2+2*item('amp',v('j')),item('x',v('k'))+item('w',v('k'))/2+2*item('amp',v('k')))),
 add('pairBottom',min_(item('y',v('j'))-item('h',v('j'))/2-2*item('amp',v('j')),item('y',v('k'))-item('h',v('k'))/2-2*item('amp',v('k')))),
 add('pairTop',max_(item('y',v('j'))+item('h',v('j'))/2+2*item('amp',v('j')),item('y',v('k'))+item('h',v('k'))/2+2*item('amp',v('k')))),
 add('pairInvBand',1/max_(0.01,min_(v('reach')/2,min_(min_(item('w',v('j')),item('h',v('j'))),min_(item('w',v('k')),item('h',v('k'))))/4)))])]),change('bi',1)])]),change('ai',1)]),set_('pairCount',length('pairA'))]
B.define('LG prepare',prepare,3500,330,'Cache active IDs and eligible pairs once per frame. Four pair bounds include conservative 2 × pull amplitude padding. Smoothly reduce connection strength toward zero as centers coincide, avoiding inflation of nearly identical overlapping shapes. Nothing here depends on sample position or discontinuous individual surface normals.')

# Use simple variable clamps in the hot loop: algebraic nested min/max expands
# its input expression many times in ordinary Scratch's tree-shaped blocks.
def clamp01var(name):return [iff(lt(v(name),0),[set_(name,0)]),iff(gt(v(name),1),[set_(name,1)])]
p=v('pairIndex')
pair_sample=[set_('j',item('pairA',p)),set_('k',item('pairB',p)),set_('dJ',item('sampleD',v('j'))),set_('dK',item('sampleD',v('k'))),set_('delta',abs_(v('dJ')-v('dK'))),set_('reach',item('pairReach',p)),
 iff(lt(v('delta'),v('reach')),[set_('smoothK',v('reach')),set_('invBand',item('pairInvBand',p)),
 *[cmd for margin in [a('x')-item('pairLeft',p),item('pairRight',p)-a('x'),a('y')-item('pairBottom',p),item('pairTop',p)-a('y')]
 for cmd in [set_('edgeGate',margin*v('invBand')),iff(lt(v('edgeGate'),1),[set_('smoothK',v('smoothK')*sq(v('edgeGate'))*(3-2*v('edgeGate')))])]],
 iff(gt(v('smoothK'),v('delta')),[set_('pairD',min_(v('dJ'),v('dK'))-sq(v('smoothK')-v('delta'))/(4*v('smoothK'))),
 iff(lt(v('pairD'),v('D')),[set_('D',v('pairD')),set_('material',v('j')),set_('secondMaterial',v('k')),set_('materialWeight',0.5+0.5*(v('dK')-v('dJ'))/v('smoothK')),*clamp01var('materialWeight')])])])]
field=[set_('D',9999),set_('material',1),set_('ai',1),repeat(v('activeCount'),[set_('j',item('activeIDs',v('ai'))),
 call('LG shape %s %s %s',v('j'),a('x'),a('y')),replace('sampleD',v('j'),v('sd')),replace('sampleNX',v('j'),v('nx')),replace('sampleNY',v('j'),v('ny')),
 iff(lt(v('sd'),v('D')),[set_('D',v('sd')),set_('material',v('j'))]),change('ai',1)]),set_('secondMaterial',v('material')),set_('materialWeight',1),
 set_('pairIndex',1),repeat(v('pairCount'),[
 iff(And(And(gt(a('x'),item('pairLeft',p)),lt(a('x'),item('pairRight',p))),And(gt(a('y'),item('pairBottom',p)),lt(a('y'),item('pairTop',p)))),pair_sample),change('pairIndex',1)])]
B.define('LG sample %s %s',field,3900,1600,'Compact polynomial union with four C1 POSITION gates. Smooth joining stays active across overlapping sides and corners; no individual-normal gate can cut a sharp notch into the contour. Bounds prevent whole-pair enlargement, and the compact field preserves remote edges. Smooth material weights blend refraction/highlight settings across connections.')
B.define('LG field %s %s',[call('LG prepare'),call('LG sample %s %s',a('x'),a('y'))],3900,900,'Standalone field query: refresh cached geometry then sample. LG render calls LG prepare once and uses LG sample for each pixel instead.')
# renderer: two passes let field gradients include variable smoothing radius and warp.
render=[call('LG prepare'),E('pen_clear'),E('looks_switchcostumeto',{'COSTUME':E('looks_costume',fields={'COSTUME':['Reference photo',None]})}),iff(eq(v('Background'),2),[E('looks_switchcostumeto',{'COSTUME':E('looks_costume',fields={'COSTUME':['Calibration grid',None]})})]),go(0,0),E('looks_show'),E('pen_stamp'),E('looks_hide'),
 set_('left',240),set_('right',-240),set_('bottom',180),set_('top',-180),set_('q',4),set_('i',1),repeat(8,[iff(eq(item('active',i),1),[
 set_('pad',item('join',i)+2*item('amp',i)+6),set_('left',min_(v('left'),item('x',i)-item('w',i)/2-v('pad'))),set_('right',max_(v('right'),item('x',i)+item('w',i)/2+v('pad'))),set_('bottom',min_(v('bottom'),item('y',i)-item('h',i)/2-v('pad'))),set_('top',max_(v('top'),item('y',i)+item('h',i)/2+v('pad'))),set_('q',min_(v('q'),item('quality',i)))]),change('i',1)]),
 set_('left',max_(-240,m('floor',v('left')/v('q'))*v('q'))),set_('right',min_(240,m('ceiling',v('right')/v('q'))*v('q'))),set_('bottom',max_(-180,m('floor',v('bottom')/v('q'))*v('q'))),set_('top',min_(180,m('ceiling',v('top')/v('q'))*v('q'))),set_('cols',rnd((v('right')-v('left'))/v('q'))+1),set_('rows',rnd((v('top')-v('bottom'))/v('q'))+1),clear('field'),clear('owner'),clear('owner2'),clear('mixWeight'),set_('row',0),repeat(v('rows'),[set_('col',0),set_('screenY',v('top')-v('row')*v('q')),repeat(v('cols'),[set_('screenX',v('left')+v('col')*v('q')),call('LG sample %s %s',v('screenX'),v('screenY')),add('field',v('D')),add('owner',v('material')),add('owner2',v('secondMaterial')),add('mixWeight',v('materialWeight')),change('col',1)]),change('row',1)]),
 E('pen_setPenSizeTo',{'SIZE':v('q')+0.15}),set_('row',1),repeat(max_(0,v('rows')-2),[set_('col',1),set_('screenY',v('top')-v('row')*v('q')),repeat(max_(0,v('cols')-2),[set_('cell',v('row')*v('cols')+v('col')+1),set_('D',item('field',v('cell'))),iff(lt(v('D'),v('q')*0.7),[set_('screenX',v('left')+v('col')*v('q')),call('LG shade %s %s %s',v('screenX'),v('screenY'),v('cell'))]),change('col',1)]),change('row',1)]),penparam('transparency',0),change('Frames',1),change('fpsFrames',1),iff(gt(timer()-v('fpsTime'),0.8),[set_('FPS',rnd(v('fpsFrames')/(timer()-v('fpsTime')))),set_('fpsFrames',0),set_('fpsTime',timer())])]
B.define('LG render',render,5700,1600,'Two passes: compute merged field once per grid point, then shade its finite-difference normal. Pixel step 1 is highest detail; 2 is balanced. Bounds are clipped to the stage. Sampling clamps BOTH coordinates before indexing, avoiding EffOnly row wrap. Background RGB and displayed costume are always the same source. Only standard Pen is used.')
# EffOnly refraction law depth from outer edge: max(0, halfSize*reflection-depth)^2/10.
ci=a('cell');own=v('mat')
def mixed(name):return item(name,own)*v('mix')+item(name,v('mat2'))*(1-v('mix'))
shade=[set_('mat',item('owner',ci)),set_('mat2',item('owner2',ci)),set_('mix',item('mixWeight',ci)),
 iff(lt(v('mat2'),1),[set_('mat2',v('mat')),set_('mix',1)]),
 set_('normalX',item('field',ci+1)-item('field',ci-1)),set_('normalY',item('field',ci-v('cols'))-item('field',ci+v('cols'))),set_('normalLen',max_(0.00001,sqrt(sq(v('normalX'))+sq(v('normalY'))))),
 set_('opticalGain',clamp(v('normalLen')/v('q'),0,1)),set_('opticalGain',sq(v('opticalGain'))*(3-2*v('opticalGain'))),
 set_('normalX',v('normalX')/v('normalLen')),set_('normalY',v('normalY')/v('normalLen')),
 set_('band',0.5*(min_(item('w',own),item('h',own))*item('reflection',own)*v('mix')+min_(item('w',v('mat2')),item('h',v('mat2')))*item('reflection',v('mat2'))*(1-v('mix')))),set_('refraction',sq(max_(0,v('band')+v('D')))/10*mixed('distortion')),set_('refraction',clamp(v('refraction'),-110,110)),
 set_('refraction',v('refraction')*v('opticalGain')),
 call('LG background %s %s',a('x')-v('normalX')*v('refraction'),a('y')-v('normalY')*v('refraction')),
 set_('R',m('floor',v('color')/65536)),set_('G',mod(m('floor',v('color')/256),256)),set_('B',mod(v('color'),256)),
 set_('rim',clamp(1-abs_(v('D'))/max_(v('q')*0.7,mixed('edge')),0,1)*gt(mixed('edge'),0)),
 set_('lightDot',v('normalX')*m('cos',mixed('light'))+v('normalY')*m('sin',mixed('light'))),set_('shine',v('rim')*mixed('highlight')*(28+125*sq(v('lightDot')))),set_('materialTint',mixed('tint')),
 *[set_(ch,clamp(v(ch)*(1-v('materialTint'))+t*v('materialTint')+v('shine'),0,255)) for ch,t in [('R',220),('G',239),('B',255)]],
 E('pen_setPenColorToColor',{'COLOR':rnd(v('R'))*65536+rnd(v('G'))*256+rnd(v('B'))}),penparam('transparency',100*(1-clamp(0.5-v('D')/v('q'),0,1))),
 go(a('x')-v('q')/2,a('y')),E('pen_penDown'),go(a('x')+v('q')/2,a('y')),E('pen_penUp')]
B.define('LG shade %s %s %s',shade,7400,1600,'EffOnly optical profile toward the interior normal; reflection 0.5, edge 1, light -30 preserve defaults. A smooth optical gain suppresses refraction where merged normals cancel, preventing near-zero gradients from becoming full-strength random displacement. Ordinary contour gradients retain full refraction. Materials and rims follow the merged boundary.')
background=[set_('sampleX',clamp(rnd(a('x')),-240,239)),set_('sampleY',clamp(rnd(a('y')),-180,179)),set_('sampleIndex',(179-v('sampleY'))*480+v('sampleX')+241),iff(eq(v('Background'),2),[set_('color',item('Grid RGB',v('sampleIndex')))],[set_('color',item('Original RGB',v('sampleIndex')))])]
B.define('LG background %s %s',background,9000,1600)
# Example configuration. Everything adjustable is passed through the public custom block.
demo=[set_('mainW',156),set_('mainH',96),set_('mainShape',v('Shape')),iff(eq(v('Shape'),3),[set_('mainW',96)]),iff(eq(v('Shape'),2),[set_('mainH',64)]),iff(eq(v('Menu'),1),[set_('mainW',238),set_('mainH',146),set_('mainShape',1)]),
 iff(eq(v('Auto'),1),[set_('demoX2',50+40*m('sin',timer()*55))]),
 iff(eq(v('PullDemo'),1),[set_('pullWave',38*m('sin',timer()*300)),set_('demoX1',-90+v('pullWave')),set_('demoX2',85+v('pullWave')),set_('demoX3',20+v('pullWave'))]),
 call(API,1,v('demoX1'),v('demoY1'),v('mainW'),v('mainH'),v('mainShape'),24,v('Reflection'),v('Distortion'),v('Edge'),v('Highlight'),v('Light'),v('Tint'),v('Join'),1,0.45,18,0.85,v('Pull'),1,v('Quality')),
 call(API,2,v('demoX2'),v('demoY2'),76,76,3,38,v('Reflection'),v('Distortion'),v('Edge'),v('Highlight'),v('Light'),v('Tint'),v('Join'),1,0.45,18,0.85,v('Pull'),1,v('Quality')),
 call(API,3,v('demoX3'),v('demoY3'),176,44,2,22,v('Reflection'),v('Distortion'),v('Edge'),v('Highlight'),v('Light'),v('Tint'),v('Join'),1,0.45,18,0.85,v('Pull'),1,v('Quality'))]
B.declare('LG demo targets',[])
B.define('LG demo targets',demo[:-3],30,330,'Demo target values for the keyboard controls. The three PUBLIC Glass calls are directly in the green-flag forever loop. Edit those calls to customize components; helpers never need hard-coded changes.')
B.define('LG demo',[call('LG demo targets'),*demo[-3:]],30,330,'One-shot demo setup helper, also used by validation. The main green-flag loop contains its own visible Glass calls.')
B.top(E('event_whenflagclicked'),[call('LG initialize'),E('control_forever',{'SUBSTACK':[call('LG demo targets'),*demo[-3:],call('LG advance'),call('LG render'),E('control_wait',{'DURATION':0})]})],30,30,'START HERE • These three Glass calls create and update the rectangle, circle, and capsule every frame using only native Scratch blocks. Edit their inputs. LG advance animates; LG render draws. Replace the demo target helper with your own variables as needed. Standard Scratch 3 + Pen; no custom extensions, shaders, JavaScript, or TurboWarp-only blocks.')
for idx,k in enumerate(['1','2','3','space','m','p','b','q','e','r']):
 if k in ['1','2','3']:seq=[set_('Shape',int(k)),set_('Menu',0)]
 elif k=='space':seq=[set_('Menu',1-v('Menu'))]
 elif k=='m':seq=[set_('Auto',1-v('Auto'))]
 elif k=='p':seq=[set_('PullDemo',1-v('PullDemo')),set_('Auto',0)]
 elif k=='b':seq=[set_('Background',3-v('Background'))]
 elif k=='q':seq=[set_('Quality',mod(v('Quality'),3)+1)]
 elif k=='r':seq=[call('LG initialize')]
 else:
  seq=[set_('Controls',1-v('Controls'))]
  for name in ['Reflection','Distortion','Edge','Highlight','Light','Join','Pull','Quality']:
   seq.append(iff(eq(v('Controls'),1),[E('data_showvariable',fields={'VARIABLE':[name,'v_'+name]})],[E('data_hidevariable',fields={'VARIABLE':[name,'v_'+name]})]))
 B.top(E('event_whenkeypressed',fields={'KEY_OPTION':[k,None]}),seq,900+idx*420,30)
B.finish()

def arrange(builder):
 """Keep the native entry script first and isolated from long helper definitions."""
 tops=[i for i,b in builder.blocks.items() if b.get('topLevel')]
 main=next(i for i in tops if builder.blocks[i]['opcode']=='event_whenflagclicked')
 builder.blocks[main].update(x=40,y=40)
 keys=[i for i in tops if builder.blocks[i]['opcode']=='event_whenkeypressed']
 for n,i in enumerate(keys):builder.blocks[i].update(x=40+600*n,y=900)
 defs=[i for i in tops if builder.blocks[i]['opcode']=='procedures_definition']
 for n,i in enumerate(defs):builder.blocks[i].update(x=40+(n%3)*8000,y=2400+(n//3)*7000)
 # Blockly's first imported top-level script determines initial workspace focus.
 builder.blocks={main:builder.blocks[main],**{i:b for i,b in builder.blocks.items() if i!=main}}

arrange(B)

def png(pixels,w=480,h=360):
 def chunk(k,d):return struct.pack('!I',len(d))+k+d+struct.pack('!I',zlib.crc32(k+d)&0xffffffff)
 data=b''.join(b'\x00'+b''.join(int(c).to_bytes(3,'big') for c in pixels[y*w:(y+1)*w]) for y in range(h))
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(data))+chunk(b'IEND',b'')
assets={}
def costume(name,data,ext='svg',w=480,h=360):
 ident=hashlib.md5(data).hexdigest();assets[ident+'.'+ext]=data
 return {'assetId':ident,'name':name,'bitmapResolution':1,'md5ext':ident+'.'+ext,'dataFormat':ext,'rotationCenterX':w/2,'rotationCenterY':h/2}
with zipfile.ZipFile(SOURCE) as z:src=json.loads(z.read('project.json'))
original=next(value[1] for value in src['targets'][0]['lists'].values() if value[0]=='original')
original=[int(c) for c in original]
# Native bitmap calibration background provides fine structures to assess refraction.
grid=[]
for yy in range(360):
 for xx in range(480):
  rr=24+int(75*xx/480);gg=35+int(100*yy/360);bb=80+int(70*(1-xx/480))
  if xx%24<2 or yy%24<2:rr,gg,bb=170,210,231
  if xx%96<2 or yy%96<2:rr,gg,bb=244,245,238
  grid.append(rr*65536+gg*256+bb)
B.lists['l_Original RGB']=['Original RGB',original];B.lists['l_Grid RGB']=['Grid RGB',grid]
blank=b'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360"><path fill="#183049" d="M0 0h480v360H0z"/></svg>'
stage={'isStage':True,'name':'Stage','variables':{},'lists':{},'broadcasts':{},'blocks':{},'comments':{},'currentCostume':0,'costumes':[costume('Backdrop',blank)],'sounds':[],'volume':100,'layerOrder':0,'tempo':60,'videoTransparency':50,'videoState':'off','textToSpeechLanguage':None}
sprite={'isStage':False,'name':'Liquid Glass','variables':B.vars,'lists':B.lists,'broadcasts':{},'blocks':B.blocks,'comments':B.comments,'currentCostume':0,'costumes':[costume('Reference photo',png(original),'png'),costume('Calibration grid',png(grid),'png')],'sounds':[],'volume':100,'layerOrder':1,'visible':False,'x':0,'y':0,'size':100,'direction':90,'draggable':False,'rotationStyle':"don't rotate"}
hud_svg=b'''<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360"><rect width="480" height="61" fill="#081729" fill-opacity="0.83"/><text x="20" y="27" fill="#f2f7ff" font-family="Helvetica,Arial,sans-serif" font-size="20" font-weight="600">Liquid Glass</text><text x="460" y="26" text-anchor="end" fill="#a7cbdc" font-family="Helvetica,Arial,sans-serif" font-size="10" letter-spacing="1.5">NATIVE SCRATCH</text><text x="20" y="46" fill="#bad4e2" font-family="Helvetica,Arial,sans-serif" font-size="10">Drag any shape. Bring edges together to merge.</text><rect y="315" width="480" height="45" fill="#081729" fill-opacity="0.83"/><text x="20" y="333" fill="#edf6ff" font-family="Helvetica,Arial,sans-serif" font-size="10">1 / 2 / 3 Shape   SPACE Expand   M Join   P Pull demo</text><text x="20" y="349" fill="#bad4e2" font-family="Helvetica,Arial,sans-serif" font-size="10">B  Background     Q  Detail     E  Effect sliders     R  Reset</text></svg>'''
hud={'isStage':False,'name':'Demo guide (optional)','variables':{},'lists':{},'broadcasts':{},'blocks':{},'comments':{},'currentCostume':0,'costumes':[costume('Guide',hud_svg)],'sounds':[],'volume':100,'layerOrder':2,'visible':True,'x':0,'y':0,'size':100,'direction':90,'draggable':False,'rotationStyle':"don't rotate"}
monitors=[]
for n,lo,hi,dis in [('Reflection',0,1,False),('Distortion',-3,3,False),('Edge',0,6,False),('Highlight',0,3,False),('Light',-180,180,True),('Join',0,60,True),('Pull',0,2,False),('Quality',1,4,True)]:
 monitors.append({'id':'v_'+n,'mode':'slider','opcode':'data_variable','params':{'VARIABLE':n},'spriteName':'Liquid Glass','value':0,'width':0,'height':0,'x':302,'y':64+len(monitors)*29,'visible':False,'sliderMin':lo,'sliderMax':hi,'isDiscrete':dis})
project={'targets':[stage,sprite,hud],'monitors':monitors,'extensions':['pen'],'meta':{'semver':'3.0.0','vm':'0.2.0','agent':'Native Scratch block authoring; reference EffOnly + V1.7 + V5 + V7'}}
# A clean importable component: one visible example, with no demo key bindings.
C=copy.deepcopy(B)
def remove_tree(i):
 if not i or i not in C.blocks:return
 block=C.blocks.pop(i)
 if block.get('comment'):C.comments.pop(block['comment'],None)
 for inp in block['inputs'].values():
  for value in inp[1:]:
   if isinstance(value,str):remove_tree(value)
 remove_tree(block.get('next'))
for bid,block in list(C.blocks.items()):
 if block.get('topLevel') and block['opcode'] in ('event_whenflagclicked','event_whenkeypressed'):remove_tree(bid)
 elif block.get('topLevel') and block['opcode']=='procedures_definition':
  proto=C.blocks[block['inputs']['custom_block'][1]]
  if proto['mutation']['proccode'] in ('LG demo','LG demo targets'):remove_tree(bid)
C.top(E('event_whenflagclicked'),[C.call('LG initialize'),C.call(API,1,0,0,156,96,1,24,0.5,1,1,1,-30,0.05,30,1,0.45,18,0.85,0.9,1,2),E('control_forever',{'SUBSTACK':[C.call('LG advance'),C.call('LG render'),E('control_wait',{'DURATION':0})]})],40,40,'YOUR COMPONENT • Edit this Glass call to configure the first object. Duplicate it with a new id for another object. Call the same id again to animate new targets. LG advance/render keep running in the native Scratch forever loop. No helper edits are needed.')
C.finish();arrange(C)
component=copy.deepcopy(sprite);component.update(blocks=C.blocks,comments=C.comments,variables=C.vars,lists=C.lists)
# Save a source JSON to support independent verification; archive only standard SB3 entries.
(ROOT/'LiquidGlass_Studio.project.json').write_text(json.dumps(project,separators=(',',':')))
for filename,obj in [('LiquidGlass_Studio.sb3',project),('LiquidGlass_Component.sprite3',component)]:
 with zipfile.ZipFile(ROOT/filename,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('project.json' if filename.endswith('sb3') else 'sprite.json',json.dumps(obj,separators=(',',':')))
  for name,data in assets.items():z.writestr(name,data)
(ROOT/'research/preview-background.png').write_bytes(png(original))
print(f'Built {len(B.blocks)} native blocks, {len(B.procs)} procedures, {len(B.vars)} variables. Output: LiquidGlass_Studio.sb3')
# Preserve every newly built update before it is loaded into the native editor.
from tools.snapshot_release import snapshot
snapshot(note='Generated native Scratch update; see CHANGELOG.md for behavior changes.')
