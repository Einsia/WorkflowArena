"""Deterministic affine arrangement engine. Reads no submissions.
1D exact crossings and intervals. 2D line arrangement covers cell interiors,
edges, intersections, vertices. Unknowns never silently set to zero.
"""
import json,math,itertools
from pathlib import Path
D=Path(__file__).resolve().parent
EPS=1e-10

def val(c,p):return c[0]+sum(x*y for x,y in zip(c[1:],p))
def top(c,p,drop=None,tol=EPS):
 v={t:val(a,p) for t,a in c.items() if t!=drop}
 rank={t:1+sum(x>y+tol for x in v.values()) for t,y in v.items()}
 return {'point':p,'scores':v,'ranks':rank,'top_two':sorted(t for t in v if rank[t]<=2),'precision_possible_top_two':sorted(t for t,y in v.items() if sum(x>y+.0002 for x in v.values())<2)}
def summary(c,points):
 states=[top(c,p) for p in points];allset=set(c);pos=set()
 for s in states:allset&=set(s['top_two']);pos|=set(s['top_two'])
 robust=[]
 for a,b in itertools.permutations(c,2):
  dd=[val(c[a],p)-val(c[b],p) for p in points]
  if min(dd)>=-EPS and max(dd)>EPS:robust.append([a,b])
 loo={}
 # Tie-aware ranks are recomputed for every issuer deletion, not slicing an ordering.
 for t in c:
  sts=[top(c,p,t) for p in points];al=set(c)-{t};po=set()
  for s in sts:al&=set(s['top_two']);po|=set(s['top_two'])
  loo[t]={'always_top_two':sorted(al),'possible_top_two':sorted(po),'changed_sample_indices':[j for j,(a,b) in enumerate(zip(states,sts)) if set(a['top_two'])-{t}!=set(b['top_two'])],'robust_pairs':[x for x in robust if t not in x]}
 return {'always_top_two':sorted(allset),'possible_top_two':sorted(pos),'robust_pairs':robust,'states':states,'leave_one_out':loo}
def one(c):
 cuts={0.,1.};cross=[]
 for a,b in itertools.combinations(c,2):
  di=c[a][0]-c[b][0];s=c[a][1]-c[b][1]
  if abs(s)>EPS:
   x=-di/s
   if EPS<x<1-EPS:cuts.add(x);cross.append({'pair':[a,b],'parameter':x})
 pts=sorted(cuts);pp=sorted(set(pts+[(x+y)/2 for x,y in zip(pts,pts[1:])]))
 z=summary(c,[[x] for x in pp]);z.update(crossings=sorted(cross,key=lambda q:q['parameter']),boundaries=pts,domain=[0,1],algorithm='all pair roots, all roots and adjacent open intervals')
 return z

def clip(poly,line):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  fa,fb=val(line,a),val(line,b);ia=fa>=-EPS;ib=fb>=-EPS
  if ia:out.append(a)
  if ia!=ib and abs(fa-fb)>EPS:
   t=fa/(fa-fb);out.append([a[k]+t*(b[k]-a[k]) for k in range(2)])
 clean=[]
 for p in out:
  if not clean or math.dist(p,clean[-1])>EPS:clean.append(p)
 if len(clean)>1 and math.dist(clean[0],clean[-1])<EPS:clean.pop()
 return clean

def two(c):
 lines=[]
 for a,b in itertools.combinations(c,2):
  v=[x-y for x,y in zip(c[a],c[b])]
  if abs(v[1])+abs(v[2])>EPS:lines.append(v)
 polys=[[[0.,0.],[1.,0.],[1.,1.],[0.,1.]]]
 for line in lines:
  new=[]
  for p in polys:
   vv=[val(line,q) for q in p]
   if min(vv)<-EPS and max(vv)>EPS:
    for sign in [1,-1]:
     pp=clip(p,[sign*x for x in line])
     if len(pp)>=3:new.append(pp)
   else:new.append(p)
  polys=new
 points={}
 def add(p):points[tuple(round(x,11) for x in p)]=p
 for p in polys:
  add([sum(v[k] for v in p)/len(p) for k in range(2)])
  for a,b in zip(p,p[1:]+p[:1]):add(a);add([(x+y)/2 for x,y in zip(a,b)])
 z=summary(c,list(points.values()));z.update(domain={'x':[0,1],'y':[0,1]},cells=polys,arrangement_lines=lines,algorithm='all pair-equality lines split square; each cell interior, each edge interior and vertex evaluated; tie-aware deletion ranks')
 return z
