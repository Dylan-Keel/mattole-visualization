import numpy as np, rasterio, geopandas as gpd, json, cv2
from rasterio import features
from shapely.geometry import LineString, mapping
A=np.load('acc.npy'); fd=np.load('fd.npy'); T=rasterio.open('dem10.tif').transform
ws=gpd.read_file('watershed.geojson').geometry.iloc[0]
wm=features.rasterize([(ws,1)],out_shape=A.shape,transform=T).astype(bool)
dirmap={64:(-1,0),128:(-1,1),1:(0,1),2:(1,1),4:(1,0),8:(1,-1),16:(0,-1),32:(-1,-1)}
inv={v:k for k,v in dirmap.items()}
out=np.unravel_index(np.argmax(np.where(wm,A,0)),A.shape); print('outlet',T*(out[1]+.5,out[0]+.5),A[out])
def ups(r,c):
    res=[]
    for (dr,dc),code in [((-dr,-dc),k) for k,(dr,dc) in dirmap.items()]:
        rr,cc=r+dr,c+dc
        if 0<=rr<A.shape[0] and 0<=cc<A.shape[1] and wm[rr,cc] and fd[rr,cc]==code: res.append((rr,cc))
    return res
TH=400   # 4 ha
def trace(r,c):
    path=[(r,c)]; tribs=[]
    while True:
        u=[p for p in ups(r,c) if A[p]>=TH]
        if not u: break
        u.sort(key=lambda p:-A[p]); 
        for p in u[1:]: tribs.append((p,A[p],(r,c)))
        r,c=u[0]; path.append((r,c))
    return path,tribs
xy=lambda p:T*(p[1]+.5,p[0]+.5)
main,tribs=trace(*out)
print('main len m',len(main)*11,'tribs',[(xy(p),int(a),xy(j)) for p,a,j in sorted(tribs,key=lambda t:-t[1])][:8])
lines={'main':[xy(p) for p in main]}
for i,(p,a,j) in enumerate(sorted(tribs,key=lambda t:-t[1])[:6]):
    path,_=trace(*p); lines[f'trib{i}']=[xy(j)]+[xy(q) for q in path]; print(f'trib{i}','area ha',a/100,'join',xy(j),'head',xy(path[-1]),'len',len(path)*11)
json.dump(lines,open('streams.json','w'))
o=cv2.cvtColor(np.load('o41_63_2m.npy'),cv2.COLOR_GRAY2BGR); b=(392000,4456700,394400,4459400)
cols=[(0,255,255),(0,0,255),(0,255,0),(255,0,255),(255,128,0),(128,255,255),(200,200,0)]
for k,(n,l) in enumerate(lines.items()):
    pts=np.array([[(x-b[0])/2,(b[3]-y)/2] for x,y in l],np.int32); cv2.polylines(o,[pts],False,cols[k],2); cv2.putText(o,n,tuple(int(v) for v in pts[len(pts)//2]),0,0.6,cols[k],2)
pass
cv2.imwrite('streams_chk.jpg',o)
