#!/usr/bin/env python3
"""Independent audit of the 0.2.0 group fold; never project runtime code."""
import json, math, itertools
from pathlib import Path

def clamp(x,a,b):return max(a,min(b,x))
def smooth(x):
 x=clamp(x,0,1);return x*x*(3-2*x)
def sdf(x,y,s):
 qx=abs(x-s['x'])-s['w']/2+s['r'];qy=abs(y-s['y'])-s['h']/2+s['r']
 return math.hypot(max(qx,0),max(qy,0))+min(max(qx,qy),0)-s['r']
def bbox(shapes):
 return (min(s['x']-s['w']/2 for s in shapes),min(s['y']-s['h']/2 for s in shapes),max(s['x']+s['w']/2 for s in shapes),max(s['y']+s['h']/2 for s in shapes))
def pair_k(x,y,a,b):
 if not a['group'] or a['group']!=b['group'] or min(a['join'],b['join'])<=0:return 0
 reach0=2*min(a['join'],b['join']);distance=math.hypot(a['x']-b['x'],a['y']-b['y'])
 if distance<=.01:return 0
 k=reach0*smooth(distance/reach0)
 left,bottom,right,top=bbox([a,b]);band=max(.01,min(k/2,min(a['w'],a['h'],b['w'],b['h'])/4))
 return k*smooth((x-left)/band)*smooth((right-x)/band)*smooth((y-bottom)/band)*smooth((top-y)/band)
def poly(a,b,k):
 if k<=1e-12:return (a,1) if a<=b else (b,0)
 h=clamp(.5+.5*(b-a)/k,0,1)
 return h*a+(1-h)*b-k*h*(1-h),h
def band(s):return min(s['w'],s['h'])*.5*s.get('reflection',.5)
def optical(s):
 angle=math.radians(2*s.get('light',-30))
 return {'Band':band(s),'Distortion':s.get('distortion',1),'Edge':s.get('edge',1),
  'Highlight':s.get('highlight',1),'LightX':math.cos(angle),'LightY':math.sin(angle),'Tint':s.get('tint',.05)}
def pairwise(x,y,shapes):
 ds=[sdf(x,y,s)for s in shapes];idx=min(range(len(shapes)),key=lambda i:ds[i]);D=ds[idx];B=band(shapes[idx]);winner=(idx,)
 candidates={}
 for i,j in itertools.combinations(range(len(shapes)),2):
  k=pair_k(x,y,shapes[i],shapes[j]);p,h=poly(ds[i],ds[j],k);pb=h*band(shapes[i])+(1-h)*band(shapes[j]);candidates[(i,j)]=(p,pb,h,k)
  if p<D:D=p;B=pb;winner=(i,j)
 return D,B,winner,candidates
def nary_full(x,y,shapes):
 groups={}
 for i,s in enumerate(shapes):groups.setdefault(('isolate',i) if not s['group'] or s['join']<=0 else ('group',s['group']),[]).append(i)
 best=(math.inf,None,None)
 for group,ids in groups.items():
  first=ids[0];D=sdf(x,y,shapes[first]);values=optical(shapes[first]);previous=[first]
  for j in ids[1:]:
   sj=shapes[j];product=1
   if sj['join']>0:
    for i in previous:product*=1-pair_k(x,y,shapes[i],sj)/(2*sj['join'])
    k=2*sj['join']*(1-product)
   else:k=0
   D,h=poly(D,sdf(x,y,sj),k);new_values=optical(sj)
   values={name:h*value+(1-h)*new_values[name] for name,value in values.items()};previous.append(j)
  if D<best[0]:best=(D,values,group)
 return best
def nary(x,y,shapes):
 D,values,group=nary_full(x,y,shapes)
 return D,values['Band'],group

def shape(name,x,y,w,h,r,join=30,group=1):return dict(name=name,x=x,y=y,w=w,h=h,r=r,join=join,group=group)

def find_switch(shapes):
 left,bottom,right,top=bbox(shapes);best=None
 for y in range(math.floor(bottom)-5,math.ceil(top)+5):
  for x in range(math.floor(left)-5,math.ceil(right)+5):
   p=pairwise(x,y,shapes)
   for dx,dy in [(1,0),(0,1)]:
    q=pairwise(x+dx,y+dy,shapes)
    if len(p[2])!=2 or len(q[2])!=2 or p[2]==q[2]:continue
    a,b=p[2],q[2]
    lo,hi=0.,1.
    for _ in range(40):
     t=(lo+hi)/2;c=pairwise(x+dx*t,y+dy*t,shapes)[3];difference=c[a][0]-c[b][0]
     if difference<=0:lo=t
     else:hi=t
    t=(lo+hi)/2;px,py=x+dx*t,y+dy*t;r=pairwise(px,py,shapes);jump=abs(r[3][a][1]-r[3][b][1])
    # Prefer visible-rim or refracting-band switches, then a meaningful optical jump.
    score=jump/(1+abs(r[0])*.15)
    if best is None or score>best['score']:best=dict(x=px,y=py,direction=[dx,dy],pairs=[a,b],field=r[0],pair_bands=[r[3][a][1],r[3][b][1]],limiting_band_jump=jump,score=score)
 return best

def audit():
 cases=[
  [shape('rectangle',-35,0,130,80,18),shape('circle',40,10,70,70,35),shape('capsule',10,-35,120,38,19)],
  [shape('rectangle',-40,15,100,70,15),shape('circle',35,15,70,70,35),shape('capsule',0,-35,100,36,18)],
  [shape('rectangle',-35,15,90,70,15),shape('circle',40,10,60,60,30),shape('capsule',0,-25,110,30,15)],
 ]
 result={'version':'0.2.0','model':'Per-group ordered polynomial smooth union with K=2join_j*(1-product_i(1-Kij/(2join_j))); same h blends all seven optics. Group0 and join0 isolated; different groups hard union. Pair gates use attenuated reach for their edge band.','cases':[]}
 max_equivalence=0;outside_max=0;outside_count=0
 for shapes in cases:
  switch=find_switch(shapes);samples=[]
  assert switch
  x,y=switch['x'],switch['y'];dx,dy=switch['direction']
  for h in [.1,.01,.001,.0001,.00001]:
   oldL=pairwise(x-dx*h,y-dy*h,shapes);oldR=pairwise(x+dx*h,y+dy*h,shapes)
   newL=nary(x-dx*h,y-dy*h,shapes);newR=nary(x+dx*h,y+dy*h,shapes)
   samples.append(dict(offset=h,pairwise_band_jump=abs(oldR[1]-oldL[1]),nary_band_difference=abs(newR[1]-newL[1]),pairwise_D_difference=abs(oldR[0]-oldL[0]),nary_D_difference=abs(newR[0]-newL[0])))
  assert samples[-1]['nary_band_difference']<1e-4
  left,bottom,right,top=bbox(shapes)
  for t in range(101):
   x=left+(right-left)*t/100;y=bottom+(top-bottom)*t/100
   for eps in [0,1e-5,.1,1,10]:
    for px,py in [(left-eps,y),(right+eps,y),(x,bottom-eps),(x,top+eps)]:
     value=nary(px,py,shapes)[0];hard=min(sdf(px,py,s)for s in shapes)
     outside_max=max(outside_max,abs(value-hard));outside_count+=1
     assert value>=-1e-9
  for i,j in itertools.combinations(range(len(shapes)),2):
   pair=[shapes[i],shapes[j]]
   for x in range(-120,121,8):
    for y in range(-90,91,9):
     a=pairwise(x,y,pair);b=nary(x,y,pair);max_equivalence=max(max_equivalence,abs(a[0]-b[0]),abs(a[1]-b[1]))
  # Order dependence is measured, not hidden: all orderings are still continuous.
  order_values=[{'order':[s['name']for s in perm],'D':nary(switch['x'],switch['y'],perm)[0],'band':nary(switch['x'],switch['y'],perm)[1]}for perm in itertools.permutations(shapes)]
  result['cases'].append({'shapes':shapes,'winner_switch':switch,'one_sided_samples':samples,'orders_at_switch':order_values})
 assert max_equivalence<1e-10
 assert outside_max<1e-10
 # Differentgroups, disabledjoin, and group0 stay independent hard unions.
 a=shape('a',-15,0,80,80,40);b=shape('b',15,0,80,80,40,group=0)
 for variant in [0,2]:
  b['group']=variant
  for x in range(-60,61,5):
   assert abs(nary(x,0,[a,b])[0]-min(sdf(x,0,a),sdf(x,0,b)))<1e-10
 # A disabled member must not leak into another member's smooth accumulator.
 disabled=shape('disabled',0,0,30,30,15,join=0)
 enabled=[shape('left',-35,0,80,80,40),shape('right',35,0,80,80,40)]
 disabled_error=0
 for x in range(-60,61,3):
  for y in range(-45,46,3):
   actual=nary(x,y,[enabled[0],disabled,enabled[1]])[0]
   expected=min(nary(x,y,enabled)[0],sdf(x,y,disabled))
   disabled_error=max(disabled_error,abs(actual-expected))
 assert disabled_error<1e-10
 # All optical values share the same smooth weights, including vectors for
 # the existing 180-degree-periodic opposing highlight lobes.
 full_material_cases=[]
 for case in result['cases']:
  shapes=[dict(s,reflection=.25+.2*i,distortion=-1+i,edge=.5+i,
               highlight=.4+.6*i,light=[179,-179,45][i],tint=.1*i)
          for i,s in enumerate(case['shapes'])]
  switch=case['winner_switch'];x,y=switch['x'],switch['y'];dx,dy=switch['direction'];samples=[]
  for step in (.1,.01,.001,.0001,.00001):
   left=nary_full(x-dx*step,y-dy*step,shapes)[1];right=nary_full(x+dx*step,y+dy*step,shapes)[1]
   samples.append({'step':step,'property_differences':{name:abs(left[name]-right[name]) for name in left}})
  assert max(samples[-1]['property_differences'].values())<1e-4
  full_material_cases.append({'at':[x,y],'one_sided_samples':samples})
 light_error=0
 for light in range(-180,181,15):
  values=optical(dict(a,light=light))
  for normal in range(-180,181,9):
   nx,ny=math.cos(math.radians(normal)),math.sin(math.radians(normal))
   lobe=.5*(nx*nx+ny*ny)+.5*(nx*nx-ny*ny)*values['LightX']+nx*ny*values['LightY']
   direct=(nx*math.cos(math.radians(light))+ny*math.sin(math.radians(light)))**2
   light_error=max(light_error,abs(lobe-direct))
 assert light_error<1e-12
 result.update(passed=True,max_two_shape_D_or_band_equivalence_error=max_equivalence,outer_bbox_samples=outside_count,max_outer_bbox_hard_union_error=outside_max,
  max_disabled_join_isolation_error=disabled_error,all_seven_optics_continuity=full_material_cases,
  max_isolated_double_angle_lobe_error=light_error,
  limitations=['Sequential folding is order-dependent; stable ascending componentIDs make it deterministic.','N-ary smoothing can add more interior bridge area than minimum-of-pairs, while retaining exact group outerAABB bounds.','Cross-group hard unions intentionally retain abrupt material choices.','At K=0 and equalfields, material selection is a hardtie; lowgradient shading guards remain relevant for isolated/coincident cases.'])
 return result

if __name__=='__main__':
 report=audit();dest=Path(__file__).resolve().parents[1]/'research/nary_blend_audit.json';dest.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
