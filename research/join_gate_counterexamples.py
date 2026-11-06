"""Read-only candidate experiments: no project/runtime or shared validator edits."""
import json, math
from pathlib import Path

def smooth(t):
 t=max(0,min(1,t));return t*t*(3-2*t)
def sdf(x,y,cx,cy,w,h,r):
 qx=abs(x-cx)-w/2+r;qy=abs(y-cy)-h/2+r
 return math.hypot(max(0,qx),max(0,qy))+min(max(qx,qy),0)-r

def candidate(x,y,a,b,join,spatial=False):
 da=sdf(x,y,*a);db=sdf(x,y,*b);hard=min(da,db)
 dx=b[0]-a[0];dy=b[1]-a[1];d=math.hypot(dx,dy);reach0=2*join
 if not d or not reach0:return hard
 k=reach0*smooth(d/reach0)
 left=min(a[0]-a[2]/2,b[0]-b[2]/2);right=max(a[0]+a[2]/2,b[0]+b[2]/2)
 bottom=min(a[1]-a[3]/2,b[1]-b[3]/2);top=max(a[1]+a[3]/2,b[1]+b[3]/2)
 band=max(.01,min(join,min(a[2],a[3],b[2],b[3])/4))
 k*=smooth((x-left)/band)*smooth((right-x)/band)*smooth((y-bottom)/band)*smooth((top-y)/band)
 if spatial:
  t=((x-a[0])*dx+(y-a[1])*dy)/(d*d)
  k*=smooth(2*t)*smooth(2*(1-t))
 if not k:return hard
 h=max(k-abs(da-db),0)
 return hard-h*h/(4*k)

r=40;d=40;u=math.sqrt(.5)
a=(-d*u/2,-d*u/2,80,80,40);b=(d*u/2,d*u/2,80,80,40)
p=(a[0]-r*u,a[1]+r*u)
# A boundary point whose outward normal is perpendicular to the pair direction.
remote={'a':a,'b':b,'point':p,'hard_distance':0,'bbox_only_distance':candidate(*p,a,b,30),'spatial_gate_distance':candidate(*p,a,b,30,True)}
# Specified grazing case: original top-edge/circle intersection.
a=(0,0,120,60,12);b=(60,0,80,80,40);p=(60-math.sqrt(40**2-30**2),30)
grazing={'a':a,'b':b,'original_intersection':p,'bbox_only_distance':candidate(*p,a,b,30),'spatial_gate_distance':candidate(*p,a,b,30,True)}
# Position gating can retain a hard-union corner at its support plane for unequal sizes.
a=(0,0,80,80,40);d=30;rB=50;b=(d,0,2*rB,2*rB,rB);p=(0,40)
endpoint={'a':a,'b':b,'intersection_on_position_gate_endpoint':p,'bbox_only_distance':candidate(*p,a,b,30),'spatial_gate_distance':candidate(*p,a,b,30,True)}
report={'bbox_only_does_not_preserve_every_remote_boundary_point':remote,'given_grazing_case':grazing,'position_gate_retains_endpoint_hard_union_corner':endpoint,
 'recommendation':'Remove the normal gate. Four C1 bbox gates with smooth coincidence damping address the demonstrated grazing corner. Do not claim every remote boundary point is unchanged: the guarantee is the pair outer axis-aligned bounds. Adding a center-projection position gate preserves circle back hemispheres but can retain a hard union corner at a gate endpoint for unequal sizes.'}
p=Path('research/join_gate_counterexamples.json');p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
