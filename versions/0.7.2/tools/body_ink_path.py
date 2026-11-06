"""Flatten the native SVG lettering to short body-space vector paths.

Quadratic and cubic strokes are split only until their control polygon stays
within a tenth of a stage pixel of its chord. Store pen lifts and vertices in
one compact, directly editable Scratch list entry per original costume.
"""
import math
import re
from xml.etree import ElementTree

TOKENS=re.compile(r'[a-zA-Z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?')
TOLERANCE=.09


def midpoint(a,b): return ((a[0]+b[0])/2,(a[1]+b[1])/2)


def distance_to_chord(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    denominator=dx*dx+dy*dy
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/denominator)) if denominator else 0
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)


def bezier(points,out):
    if max(distance_to_chord(p,points[0],points[-1]) for p in points[1:-1])<=TOLERANCE:
        out.append(points[-1]);return
    work=list(points);left=[work[0]];right=[work[-1]]
    while len(work)>1:
        work=[midpoint(a,b) for a,b in zip(work,work[1:])]
        left.append(work[0]);right.append(work[-1])
    bezier(left,out);bezier(right[::-1],out)


def elliptical_arc(a,b,rx,ry,rot,large,sweep):
    rx,ry=abs(rx),abs(ry)
    if rx==0 or ry==0 or a==b:return [b]
    angle=math.radians(rot);cs,sn=math.cos(angle),math.sin(angle)
    halfx,halfy=(a[0]-b[0])/2,(a[1]-b[1])/2
    x=cs*halfx+sn*halfy;y=-sn*halfx+cs*halfy
    correction=max(1,math.hypot(x/rx,y/ry));rx*=correction;ry*=correction
    den=(rx*y)**2 + (ry*x)**2
    factor=math.sqrt(max(0,(rx*rx*ry*ry-den)/den)) * (-1 if bool(large)==bool(sweep) else 1)
    cx,cy=factor*rx*y/ry,-factor*ry*x/rx
    center=(cs*cx-sn*cy+(a[0]+b[0])/2,sn*cx+cs*cy+(a[1]+b[1])/2)
    start=math.atan2((y-cy)/ry,(x-cx)/rx)
    end=math.atan2((-y-cy)/ry,(-x-cx)/rx)
    delta=end-start
    if sweep and delta<0:delta+=math.tau
    if not sweep and delta>0:delta-=math.tau
    step=2*math.acos(max(-1,1-TOLERANCE/max(rx,ry)))
    count=max(1,math.ceil(abs(delta)/step))
    result=[]
    for i in range(1,count+1):
        theta=start+delta*i/count;xx,yy=rx*math.cos(theta),ry*math.sin(theta)
        result.append((center[0]+cs*xx-sn*yy,center[1]+sn*xx+cs*yy))
    result[-1]=b
    return result


def flatten(source):
    tokens=TOKENS.findall(source);index=0;command=None;point=(0,0);first=point;parts=[];part=[]
    while index<len(tokens):
        if tokens[index].isalpha():command=tokens[index];index+=1
        if command is None:raise ValueError('A path needs a move command')
        kind=command.upper();relative=kind!=command
        if kind=='Z':
            if part and point!=first:part.append(first)
            point=first;command=None;continue
        size={'M':2,'L':2,'H':1,'V':1,'Q':4,'C':6,'A':7}.get(kind)
        if size is None:raise ValueError('Unsupported SVG path command '+kind)
        vals=list(map(float,tokens[index:index+size]));index+=size
        def xy(at):return (vals[at]+(point[0] if relative else 0),vals[at+1]+(point[1] if relative else 0))
        if kind=='M':
            if part:parts.append(part)
            point=xy(0);first=point;part=[point];command='l' if relative else 'L'
        elif kind=='L':
            point=xy(0);part.append(point)
        elif kind=='H':
            point=(vals[0]+(point[0] if relative else 0),point[1]);part.append(point)
        elif kind=='V':
            point=(point[0],vals[0]+(point[1] if relative else 0));part.append(point)
        elif kind in ('Q','C'):
            curve=[point]+[xy(j) for j in range(0,size,2)];bezier(curve,part);point=curve[-1]
        else:
            end=xy(5);part.extend(elliptical_arc(point,end,*vals[:5]));point=end
    if part:parts.append(part)
    return parts


def vector_art(costume,payload):
    root=ElementTree.fromstring(payload);layers=[]
    def collect(el,offset,properties):
        x,y=offset
        if transform:=el.get('transform'):
            m=re.fullmatch(r'translate\(([-.\d]+)[, ]+([-.\d]+)\)',transform)
            if not m:raise ValueError('SVG transform requires outline rasterization')
            x+=float(m[1]);y+=float(m[2])
        props={**properties,**el.attrib}
        kind=el.tag.rsplit('}',1)[-1]
        if kind=='path':
            traces=flatten(el.get('d',''))
            vertices=[]
            for part in traces:
                for i,(xx,yy) in enumerate(part):
                    coords=[round((xx+x-costume['rotationCenterX']+15)*32),
                            round((costume['rotationCenterY']-yy-y+15)*32)]
                    if any(v<0 or v>999 for v in coords):raise ValueError('Large artwork requires outline rasterization')
                    vertices.append(str(int(i>0))+''.join(f'{v:03d}' for v in coords))
            if vertices:layers.append((props.get('stroke',''),float(props.get('stroke-width','1')),float(props.get('opacity','1')),''.join(vertices)))
        elif kind not in ('svg','g','title','desc'):raise ValueError('Custom SVG shape requires outline rasterization')
        for e in el:collect(e,(x,y),props)
    collect(root,(0,0),{})
    if not layers:return ('',1.42,2.6,0xf8fbff,0x142534,.65)
    ink=layers[-1][:3];outer=layers[0][:3]
    light=[c[3] for c in layers if c[:3]==ink];dark=[c[3] for c in layers if c[:3]==outer]
    if ink[2]!=1 or light!=dark or len({c[:3] for c in layers})!=2:raise ValueError('Custom glyph has more than two stroke materials')
    return (''.join(light),ink[1],outer[1],int(ink[0][1:],16),int(outer[0][1:],16),outer[2])
