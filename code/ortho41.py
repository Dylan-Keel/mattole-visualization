import numpy as np, cv2, rasterio, sys
from PIL import Image
import ortho
from ortho import zat, proj, X0, Y0
import hs62, fit42
G=10.0
HS=hs62.hp(hs62.hillshade(200,35)*255,15)      # 10 m grid, origin 384000,4468000
def refpatch(X,Y,win):
    c=int((X-384000)/G); r=int((4468000-Y)/G); return HS[r-win:r+win+1,c-win:c+win+1]
def render(scan,K,d,rv,tv,b,res):
    return ortho.ortho(scan,K,d,rv,tv,b,res)
def score(scan,K,d,rv,tv,b=(390500,4455500,395000,4460000)):
    o=render(scan,K,d,rv,tv,b,G).astype(np.float32); m=o>0
    r=HS[int((4468000-b[3])/G):int((4468000-b[1])/G),int((b[0]-384000)/G):int((b[2]-384000)/G)]
    a=hs62.hp(o,15)[m]; bb=r[m]; a-=a.mean(); bb=bb-bb.mean(); return float((a*bb).sum()/np.sqrt((a*a).sum()*(bb*bb).sum())), m.mean()
def dense(scan,K,d,rv,tv,step,win,search,minscore,gap):
    h,w=scan.shape; wp=[];ip=[]
    xs=np.arange(389500,396500,step); ys=np.arange(4454500,4461500,step)
    GX,GY=np.meshgrid(xs,ys); GX=GX.ravel().astype(float);GY=GY.ravel().astype(float); GZ=zat(GX,GY)
    c=proj(np.c_[GX-X0,GY-Y0,GZ],K,d,rv,tv); ok=(c[:,0]>15)&(c[:,0]<w-15)&(c[:,1]>15)&(c[:,1]<h-15)&(GZ>5)
    R=win+search
    for X,Y,Z in zip(GX[ok],GY[ok],GZ[ok]):
        lx=X+np.arange(-R,R+1)*G; ly=Y-np.arange(-R,R+1)*G; LX,LY=np.meshgrid(lx,ly); LZ=zat(LX,LY)
        q=proj(np.c_[LX.ravel()-X0,LY.ravel()-Y0,LZ.ravel()],K,d,rv,tv).astype('float32').reshape(LX.shape+(2,))
        patch=cv2.remap(scan,q[...,0],q[...,1],cv2.INTER_CUBIC)
        if (patch==0).mean()>0.15: continue
        tm=refpatch(X,Y,win)
        if tm.shape!=(2*win+1,2*win+1) or tm.std()<6: continue
        res=cv2.matchTemplate(hs62.hp(patch.astype(np.float32),15),tm,cv2.TM_CCOEFF_NORMED)
        _,mx,_,loc=cv2.minMaxLoc(res); r2=res.copy(); cv2.circle(r2,loc,5,-1,-1)
        if mx<minscore or mx-r2.max()<gap: continue
        ip.append(q[R+loc[1]-search,R+loc[0]-search]); wp.append([X-X0,Y-Y0,Z])
    return np.array(wp,np.float64),np.array(ip,np.float64)
def fit(n,cx,cy,mpp,rot,up=4):
    a=hs62.crop(n); scan=cv2.resize(a,None,fx=up,fy=up,interpolation=cv2.INTER_CUBIC)   # upsample so sub-pixel matches are usable
    h,w=scan.shape; f=209.55/228.6*w*1.0
    best=None
    for sgn in (1,-1):
        for ff in (0.9,1.0,1.1):
            K,d,rv,tv=fit42.init_pose(cx,cy,mpp/up,sgn*rot,f*ff,w,h); s,cov=score(scan,K,d,rv,tv)
            if best is None or s>best[0]: best=(s,K,d,rv,tv,sgn,ff)
    s,K,d,rv,tv,sgn,ff=best; print(n,'init score %.3f sign %d f-scale %.1f'%(s,sgn,ff),flush=True)
    for it,(step,win,search,ms) in enumerate([(250,45,30,0.35),(200,35,15,0.4),(150,30,8,0.4)]):
        P,p=dense(scan,K,d,rv,tv,step,win,search,ms,0.05)
        if len(P)<12: print('too few',len(P)); break
        ok,rv2,tv2,inl=cv2.solvePnPRansac(P,p,K,d,rvec=rv.copy(),tvec=tv.copy(),useExtrinsicGuess=True,iterationsCount=5000,reprojectionError=6.0*up/4,flags=cv2.SOLVEPNP_ITERATIVE)
        inl=inl.ravel()
        flags=cv2.CALIB_USE_INTRINSIC_GUESS|cv2.CALIB_FIX_ASPECT_RATIO|cv2.CALIB_ZERO_TANGENT_DIST|cv2.CALIB_FIX_K1|cv2.CALIB_FIX_K2|cv2.CALIB_FIX_K3|cv2.CALIB_FIX_PRINCIPAL_POINT
        try:
            rms,K2,d2,rvs,tvs=cv2.calibrateCamera([P[inl].astype(np.float32)],[p[inl].astype(np.float32)],(w,h),K.copy(),np.zeros(5),flags=flags)
            if 0.6<K2[0,0]/K[0,0]<1.6: K,rv,tv=K2,rvs[0],tvs[0]
            else: rv,tv=rv2,tv2
        except Exception as e: rv,tv=rv2,tv2
        e=np.linalg.norm(proj(P[inl],K,d,rv,tv)-p[inl],axis=1); C=-cv2.Rodrigues(rv)[0].T@tv.ravel()
        s,cov=score(scan,K,d,rv,tv)
        print(f'  iter {it}: pts {len(P)} inl {len(inl)} med resid {np.median(e)/up:.2f} preview-px  f {K[0,0]:.0f}  cam {C[0]+X0:.0f},{C[1]+Y0:.0f},{C[2]:.0f}  score {s:.3f}',flush=True)
    np.savez(f'pose41_{n}.npz',K=K,d=d,rv=rv,tv=tv,up=up)
    return scan,K,d,rv,tv
if __name__=='__main__':
    for n,cx,cy,mpp,rot in [(63,392588,4457712,12.5,2),(62,392406,4459381,14.0,-4)]:
        scan,K,d,rv,tv=fit(n,cx,cy,mpp,rot)
        o=render(scan,K,d,rv,tv,(391000,4455800,395000,4460200),4.0); cv2.imwrite(f'o41_{n}.jpg',o)
