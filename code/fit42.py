import numpy as np, cv2, rasterio, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
import ortho
from ortho import zat, proj, X0, Y0
# reference: 1993 ortho rendered wide at 3 m
def make_ref(b,res):
    scan=np.asarray(Image.open('napp1993.tif').convert('L')); z=np.load('pose_napp1993.npz')
    return ortho.ortho(scan,z['K'],z['d'],z['rv'],z['tv'],b,res)
B=(389000,4454600,395600,4460600); RES=3.0
try: REF=np.load('ref93_3m.npy')
except: REF=make_ref(B,RES); np.save('ref93_3m.npy',REF)
def init_pose(cx,cy,mpp,rotdeg,f,w,h):
    t=np.radians(rotdeg); c,s_=np.cos(t),np.sin(t)
    R=np.array([[c,-s_,0],[s_,c,0],[0,0,1.]])@np.array([[1,0,0],[0,-1,0],[0,0,-1.]])
    Z0=float(zat(np.array([cx]),np.array([cy]))[0]); C=np.array([cx-X0,cy-Y0,Z0+f*mpp])
    K=np.array([[f,0,w/2],[0,f,h/2],[0,0,1.]])
    return K,np.zeros(5),cv2.Rodrigues(R)[0],(-R@C).reshape(3,1)
def clahe(a,c=2.5,t=6): return cv2.createCLAHE(c,(t,t)).apply(a)
def dense(scan,K,d,rv,tv,step,win,search,minscore=0.3,gap=0.05):
    h,w=scan.shape; wp=[];ip=[];sc=[]
    xs=np.arange(B[0]+ (win+search)*RES, B[2]-(win+search)*RES, step); ys=np.arange(B[1]+(win+search)*RES,B[3]-(win+search)*RES,step)
    GX,GY=np.meshgrid(xs,ys); GX=GX.ravel();GY=GY.ravel(); GZ=zat(GX,GY)
    c=proj(np.c_[GX-X0,GY-Y0,GZ],K,d,rv,tv); ok=(c[:,0]>60)&(c[:,0]<w-60)&(c[:,1]>60)&(c[:,1]<h-60)
    R=win+search
    for X,Y,Z in zip(GX[ok],GY[ok],GZ[ok]):
        lx=X+np.arange(-R,R+1)*RES; ly=Y-np.arange(-R,R+1)*RES
        LX,LY=np.meshgrid(lx,ly); LZ=zat(LX,LY)
        q=proj(np.c_[LX.ravel()-X0,LY.ravel()-Y0,LZ.ravel()],K,d,rv,tv).astype('float32').reshape(LX.shape+(2,))
        patch=cv2.remap(scan,q[...,0],q[...,1],cv2.INTER_LINEAR)
        rc=int((X-B[0])/RES); rr=int((B[3]-Y)/RES)
        tm=REF[rr-win:rr+win+1,rc-win:rc+win+1]
        if tm.shape!=(2*win+1,2*win+1) or (tm==0).mean()>0.02 or (patch==0).mean()>0.1: continue
        res=cv2.matchTemplate(clahe(patch),clahe(tm),cv2.TM_CCOEFF_NORMED)
        _,mx,_,loc=cv2.minMaxLoc(res); r2=res.copy(); cv2.circle(r2,loc,max(4,win//6),-1,-1)
        if mx<minscore or mx-r2.max()<gap: continue
        dx=loc[0]-search; dy=loc[1]-search
        ip.append(q[R+dy,R+dx]); wp.append([X-X0,Y-Y0,Z]); sc.append(mx)
    return np.array(wp,np.float64),np.array(ip,np.float64),np.array(sc)
if __name__=='__main__':
    scan=np.asarray(Image.open('up/cvl14b109.jpg').convert('L'))[100:1810,90:1820]
    h,w=scan.shape; f=209.55/228.6*w
    K,d,rv,tv=init_pose(391700,4457100,2.9,180,f,w,h)
    C=-cv2.Rodrigues(rv)[0].T@tv.ravel(); print('init cam',C[0]+X0,C[1]+Y0,C[2])
    P,p,s=dense(scan,K,d,rv,tv,step=300,win=70,search=130,minscore=0.25,gap=0.04)
    print('candidates',len(P))
    if len(P)>=6:
        ok,rv2,tv2,inl=cv2.solvePnPRansac(P,p,K,d,iterationsCount=20000,reprojectionError=12,flags=cv2.SOLVEPNP_EPNP)
        print('inliers',None if inl is None else len(inl))
        if inl is not None:
            C=-cv2.Rodrigues(rv2)[0].T@tv2.ravel(); print('cam',C[0]+X0,C[1]+Y0,C[2])
            np.savez('pose42_try.npz',K=K,d=d,rv=rv2,tv=tv2,P=P,p=p,inl=inl.ravel())
