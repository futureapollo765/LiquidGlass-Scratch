"""Independent numerical contour-tangent audit for the approved join formula."""
import math,json
from pathlib import Path

def smooth(t):
 t=max(0,min(1,t));return t*t*(3-2*t)
def shape(p,c):
 x,y=p;cx,cy,w,h,r=c;lx=x-cx;ly=y-cy
 qx=abs(lx)-w/2+r;qy=abs(ly)-h/2+r;ox=max(qx,0);oy=max(qy,0);n=math.hypot(ox,oy)
 sx=1 if lx>=0 else -1;sy=1 if ly>=0 else -1
 if n>1e-12:normal=(sx*ox/n,sy*oy/n)
 else:normal=(sx,0) if qx>qy else(0,sy)
 return n+min(max(qx,qy),0)-r,normal

def field(x,y,a,b,join,legacy=False):
 da,na=shape((x,y),a);db,nb=shape((x,y),b);hard=min(da,db)
 dx=b[0]-a[0];dy=b[1]-a[1];d=math.hypot(dx,dy);reach=2*join
 if not d or not reach:return hard
 k=reach if legacy else reach*smooth(d/reach)
 if legacy:k*=smooth(2*(na[0]*dx+na[1]*dy)/d)*smooth(-2*(nb[0]*dx+nb[1]*dy)/d)
 left=min(a[0]-a[2]/2,b[0]-b[2]/2);right=max(a[0]+a[2]/2,b[0]+b[2]/2)
 bottom=min(a[1]-a[3]/2,b[1]-b[3]/2);top=max(a[1]+a[3]/2,b[1]+b[3]/2)
 band=max(.01,min(join,min(a[2],a[3],b[2],b[3])/4))
 k*=smooth((x-left)/band)*smooth((right-x)/band)*smooth((y-bottom)/band)*smooth((top-y)/band)
 if k<=1e-15:return hard
 q=max(k-abs(da-db),0)
 return hard-q*q/(4*k)

def upper(x,a,b,join,legacy=False):
 lo=0;hi=max(a[1]+a[3]/2,b[1]+b[3]/2)+10
 assert field(x,lo,a,b,join,legacy)<0
 for _ in range(64):
  mid=(lo+hi)/2
  if field(x,mid,a,b,join,legacy)<=0:lo=mid
  else:hi=mid
 return (lo+hi)/2

a=(0,0,120,60,12);b=(60,0,80,80,40);join=30
x0=60-math.sqrt(40**2-30**2)
results={'rectangle':a,'circle':b,'original_intersection_x':x0,'samples':[]}
for legacy in [True,False]:
 y0=upper(x0,a,b,join,legacy)
 slopes=[]
 for h in [.1,.01,.001,.0001]:
  left=(y0-upper(x0-h,a,b,join,legacy))/h
  right=(upper(x0+h,a,b,join,legacy)-y0)/h
  slopes.append({'step':h,'left_slope':left,'right_slope':right,'slope_gap':abs(right-left)})
 results['samples'].append({'model':'legacy_normal_gate' if legacy else 'bbox_only_smooth_coincidence','boundary_y':y0,'one_sided_slopes':slopes})
assert results['samples'][0]['one_sided_slopes'][-1]['slope_gap']>.8
assert results['samples'][1]['one_sided_slopes'][-1]['slope_gap']<1e-5
# Raw rectangle/circle fields are smooth outside their bodies; the new gate has
# no interior medial-axis normal discontinuity. Check finite differences on a
# dense visible contour around the former seam and across the rounded corner.
for legacy in [False]:
 maximum=0;where=None
 for idx in range(1001):
  x=20+60*idx/1000;y=upper(x,a,b,join,legacy);h=1e-4
  gap=abs((upper(x+h,a,b,join,legacy)-y)/h-(y-upper(x-h,a,b,join,legacy))/h)
  if gap>maximum:maximum=gap;where=x
 results['dense_candidate_contour']={'x_range':[20,80],'samples':1001,'slope_probe':1e-4,'max_one_sided_slope_gap':maximum,'at_x':where}
 assert maximum<1e-3
results['passed']=True
Path('research/grazing_boundary_audit.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
