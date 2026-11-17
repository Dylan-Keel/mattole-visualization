import numpy as np, cv2, json, rasterio, geopandas as gpd, os, sys
from shapely.geometry import box, LineString
from PIL import Image
import ortho
from ortho import zat
E3=(391000,4455500,395500,4461000); R=2.0
CAM=np.array([393200.,4461000.,4976*0.3048]); PITCH=np.radians(20); HFOV=np.radians(60); W,H=1600,1200
f=np.array([0,-np.cos(PITCH),-np.sin(PITCH)]); r=np.array([-1.,0,0]); u=np.array([0,-np.sin(PITCH),np.cos(PITCH)])
fpx=(W/2)/np.tan(HFOV/2)
def ground_map():
    if os.path.exists('v3d/gmap.npz'):
        z=np.load('v3d/gmap.npz'); return z['X'],z['Y'],z['D']
    I,J=np.meshgrid(np.arange(W)+.5,np.arange(H)+.5)
    d=f[None,None,:]*fpx+r[None,None,:]*(I-W/2)[...,None]+u[None,None,:]*(H/2-J)[...,None]; d/=np.linalg.norm(d,axis=2,keepdims=True)
    d=d.reshape(-1,3).astype(np.float64); n=len(d)
    hit=np.zeros(n,bool); tlo=np.zeros(n); thi=np.zeros(n); t=200.0; tprev=np.full(n,200.0)
    while t<16000:
        P=CAM+d*t; inb=(P[:,0]>384100)&(P[:,0]<401900)&(P[:,1]>4450100)&(P[:,1]<4467900)
        zt=np.where(inb,zat(P[:,0],P[:,1]),-1e9)
        new=(~hit)&inb&(P[:,2]<=zt)
        tlo[new]=tprev[new]; thi[new]=t; hit|=new
        tprev[~hit]=t; t+=max(6.0,t*0.006)
    for _ in range(10):
        tm=(tlo+thi)/2; P=CAM+d*tm[:,None]; below=P[:,2]<=zat(P[:,0],P[:,1]); thi=np.where(below,tm,thi); tlo=np.where(below,tlo,tm)
    tm=(tlo+thi)/2; P=CAM+d*tm[:,None]
    X=np.where(hit,P[:,0],np.nan).reshape(H,W).astype(np.float32); Y=np.where(hit,P[:,1],np.nan).reshape(H,W).astype(np.float32); D=np.where(hit,tm,np.inf).reshape(H,W).astype(np.float32)
    np.savez('v3d/gmap.npz',X=X,Y=Y,D=D); return X,Y,D
def project(x,y):
    z=zat(np.asarray(x,float),np.asarray(y,float))+3.0; P=np.c_[x,y,z]-CAM
    zc=P@f; xc=P@r; yc=P@u; i=W/2+fpx*xc/zc; j=H/2-fpx*yc/zc; return i,j,np.linalg.norm(P,axis=1),zc
def path3d(geom,D,step=8.0):
    out=[]
    lines=[]
    for g in getattr(geom,'geoms',[geom]):
        if g.geom_type=='Polygon': lines+= [LineString(g.exterior.coords)]+[LineString(i.coords) for i in g.interiors]
        elif g.geom_type=='LineString': lines.append(g)
    for ln in lines:
        if ln.length<step: continue
        pts=np.array([ln.interpolate(s).coords[0][:2] for s in np.arange(0,ln.length+step,step)])
        i,j,dist,zc=project(pts[:,0],pts[:,1])
        ok=(zc>50)&(i>=0)&(i<W)&(j>=0)&(j<H)
        ii=np.clip(i.astype(int),0,W-1); jj=np.clip(j.astype(int),0,H-1)
        vis=ok&(dist<=D[jj,ii]+np.maximum(30,dist*0.012))
        seg=[]
        for k in range(len(pts)):
            if vis[k]: seg.append(f'{i[k]:.1f} {j[k]:.1f}')
            else:
                if len(seg)>1: out.append('M'+' L'.join(seg))
                seg=[]
        if len(seg)>1: out.append('M'+' L'.join(seg))
    return ' '.join(out)
def hill(X,Y):
    s=rasterio.open('ref/dem10.tif'); dem=s.read(1); gy,gx=np.gradient(dem,10.0); nn=np.sqrt(gx*gx+gy*gy+1)
    a=np.radians(315); e=np.radians(45); hs=np.clip((-gx*np.sin(a)*np.cos(e)+gy*np.cos(a)*np.cos(e)+np.sin(e))/nn,0,1).astype(np.float32)
    c=((X-384000)/10-0.5).astype(np.float32); rr=((4468000-Y)/10-0.5).astype(np.float32)
    return cv2.remap(hs,np.nan_to_num(c),np.nan_to_num(rr),cv2.INTER_LINEAR)
def render(tag,X,Y,D,HS):
    tex=np.asarray(Image.open(f'v3d/tex_{tag}.jpg').convert('RGB'))
    c=((X-E3[0])/R-0.5); rr=((E3[3]-Y)/R-0.5)
    col=cv2.remap(tex,np.nan_to_num(c,nan=-9).astype(np.float32),np.nan_to_num(rr,nan=-9).astype(np.float32),cv2.INTER_LINEAR,borderValue=0).astype(np.float32)
    hit=np.isfinite(D); has=(col.sum(2)>24)&hit
    grey=(70+120*HS)[...,None]*np.array([1.0,1.0,1.02],np.float32)
    img=np.where(has[...,None],col,grey)
    haze=np.clip((D-3500)/14000,0,0.5)[...,None]; img=img*(1-haze)+np.array([176,188,196],np.float32)*haze
    jj=np.linspace(0,1,H)[:,None,None]; sky=np.array([150,170,186],np.float32)*(1-jj)+np.array([206,214,220],np.float32)*jj
    img=np.where(hit[...,None],img,np.broadcast_to(sky,img.shape))
    return np.clip(img,0,255).astype(np.uint8)
if __name__=='__main__':
    X,Y,D=ground_map(); HS=hill(X,Y)
    print('hit frac',np.isfinite(D).mean(),'in E3 frac',(np.isfinite(D)&(X>E3[0])&(X<E3[2])&(Y>E3[1])&(Y<E3[3])).mean())
    for nm,(x,y) in {'mouth':(394085,4458755),'Cooskie Mtn':(392325,4456995)}.items():
        i,j,dist,zc=project(np.array([x]),np.array([y])); print(nm,'pixel',i.round(),j.round(),'dist',dist.round(),'visible',bool(dist[0]<=D[int(np.clip(j[0],0,H-1)),int(np.clip(i[0],0,W-1))]+60))
    for tag in sys.argv[1:]:
        im=render(tag,X,Y,D,HS); Image.fromarray(im).save(f'v3d/r_{tag}.jpg',quality=88)
