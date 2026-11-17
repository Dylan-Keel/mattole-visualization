import numpy as np, cv2, sys, json
from PIL import Image
import ortho, fit42, hs62, loc
from ortho import zat, proj, X0, Y0
G=10.0
_H={}
def HSF(az,alt,s=15):
    k=(az,alt)
    if k not in _H: _H[k]=hs62.hp(hs62.hillshade(az,alt)*255,s)
    return _H[k]
def score(scan,K,d,rv,tv,HS,b):
    o=ortho.ortho(scan,K,d,rv,tv,b,G).astype(np.float32); m=o>0
    if m.mean()<0.2: return -1
    r0=int((4468000-b[3])/G); c0=int((b[0]-384000)/G); r=HS[r0:r0+o.shape[0],c0:c0+o.shape[1]]
    if r.shape!=o.shape: return -1
    a=hs62.hp(o,15)[m]; bb=r[m]; a=a-a.mean(); bb=bb-bb.mean(); return float((a*bb).sum()/np.sqrt((a*a).sum()*(bb*bb).sum()+1e-9))
def dense(scan,K,d,rv,tv,HS,b,step,win,search,minscore,gap):
    h,w=scan.shape; wp=[];ip=[]
    xs=np.arange(b[0]-1500,b[2]+1500,step); ys=np.arange(b[1]-1500,b[3]+1500,step)
    GX,GY=np.meshgrid(xs,ys); GX=GX.ravel().astype(float);GY=GY.ravel().astype(float)
    ok=(GX>384600)&(GX<401400)&(GY>4450600)&(GY<4467400); GX=GX[ok];GY=GY[ok]; GZ=zat(GX,GY)
    c=proj(np.c_[GX-X0,GY-Y0,GZ],K,d,rv,tv); ok=(c[:,0]>20)&(c[:,0]<w-20)&(c[:,1]>20)&(c[:,1]<h-20)&(GZ>3)
    R=win+search
    for X,Y,Z in zip(GX[ok],GY[ok],GZ[ok]):
        lx=X+np.arange(-R,R+1)*G; ly=Y-np.arange(-R,R+1)*G; LX,LY=np.meshgrid(lx,ly); LZ=zat(LX,LY)
        q=proj(np.c_[LX.ravel()-X0,LY.ravel()-Y0,LZ.ravel()],K,d,rv,tv).astype('float32').reshape(LX.shape+(2,))
        patch=cv2.remap(scan,q[...,0],q[...,1],cv2.INTER_CUBIC)
        if (patch==0).mean()>0.15: continue
        cc=int((X-384000)/G); rr=int((4468000-Y)/G); tm=HS[rr-win:rr+win+1,cc-win:cc+win+1]
        if tm.shape!=(2*win+1,2*win+1) or tm.std()<5: continue
        res=cv2.matchTemplate(hs62.hp(patch.astype(np.float32),15),tm,cv2.TM_CCOEFF_NORMED)
        _,mx,_,lc=cv2.minMaxLoc(res); r2=res.copy(); cv2.circle(r2,lc,5,-1,-1)
        if mx<minscore or mx-r2.max()<gap: continue
        ip.append(q[R+lc[1]-search,R+lc[0]-search]); wp.append([X-X0,Y-Y0,Z])
    return np.array(wp,np.float64),np.array(ip,np.float64)
def fit(path,cx,cy,mpp,rot,up=4,verbose=True,cropf=0.08):
    a=np.asarray(Image.open(path).convert('L')); hh,ww=a.shape; a=a[int(hh*cropf):int(hh*(1-cropf)),int(ww*cropf):int(ww*(1-cropf))]
    scan=cv2.resize(a,None,fx=up,fy=up,interpolation=cv2.INTER_CUBIC); h,w=scan.shape
    half=mpp*max(a.shape)/2; b=(int(cx-half),int(cy-half),int(cx+half),int(cy+half))
    best=None
    for az,alt in ((135,50),(180,50),(225,50),(200,35),(160,35)):
        HS=HSF(az,alt)
        for sgn in (1,-1):
            for ff in (0.67,0.92,1.33):
                for ms in (0.92,1.0,1.08):
                    K,d,rv,tv=fit42.init_pose(cx,cy,mpp*ms/up,sgn*rot,ff*w,w,h); s=score(scan,K,d,rv,tv,HS,b)
                    if best is None or s>best[0]: best=(s,K,d,rv,tv,(az,alt),ff,sgn,ms)
    s0,_,_,_,_,sun,ff,sgn,ms=best; HS=HSF(*sun)
    for dr in (-5,0,5):
        for dx in (-350,0,350):
            for dy in (-350,0,350):
                K,d,rv,tv=fit42.init_pose(cx+dx,cy+dy,mpp*ms/up,sgn*rot+dr,ff*w,w,h); s=score(scan,K,d,rv,tv,HS,b)
                if s>best[0]: best=(s,K,d,rv,tv,sun,ff,sgn,ms)
    best=best[:7]
    s,K,d,rv,tv,sun,ff=best; HS=HSF(*sun)
    if verbose: print('init score %.3f sun %s f/w %.2f'%(s,sun,ff),flush=True)
    ninl=0; med=99
    ws=min(1.0,max(0.5,(2*half)/4500.0))
    for it,(step,win,search,ms) in enumerate([(int(250*ws),int(45*ws),int(30*ws),0.3),(int(200*ws),int(35*ws),int(15*ws),0.35),(int(150*ws),int(30*ws),8,0.35)]):
        P,p=dense(scan,K,d,rv,tv,HS,b,step,win,search,ms,0.04)
        if len(P)<15: 
            if verbose: print('  too few matches',len(P)); 
            break
        ok,rv2,tv2,inl=cv2.solvePnPRansac(P,p,K,d,rvec=rv.copy(),tvec=tv.copy(),useExtrinsicGuess=True,iterationsCount=5000,reprojectionError=6.0,flags=cv2.SOLVEPNP_ITERATIVE)
        if inl is None or len(inl)<12: break
        inl=inl.ravel(); rv,tv=rv2,tv2
        flags=cv2.CALIB_USE_INTRINSIC_GUESS|cv2.CALIB_FIX_ASPECT_RATIO|cv2.CALIB_ZERO_TANGENT_DIST|cv2.CALIB_FIX_K1|cv2.CALIB_FIX_K2|cv2.CALIB_FIX_K3|cv2.CALIB_FIX_PRINCIPAL_POINT
        try:
            rms,K2,d2,rvs,tvs=cv2.calibrateCamera([P[inl].astype(np.float32)],[p[inl].astype(np.float32)],(w,h),K.copy(),np.zeros(5),flags=flags)
            if 0.5<K2[0,0]/K[0,0]<2: K,rv,tv=K2,rvs[0],tvs[0]
        except Exception as e: pass
        e=np.linalg.norm(proj(P[inl],K,d,rv,tv)-p[inl],axis=1); C=-cv2.Rodrigues(rv)[0].T@tv.ravel(); ninl=len(inl); med=float(np.median(e))/up
        s=score(scan,K,d,rv,tv,HS,b)
        if verbose: print(f'  iter {it}: pts {len(P)} inl {ninl} med {med:.2f} px  f/w {K[0,0]/w:.2f}  cam {C[0]+X0:.0f},{C[1]+Y0:.0f},{C[2]:.0f}  score {s:.3f}',flush=True)
    C=-cv2.Rodrigues(rv)[0].T@tv.ravel()
    return dict(scan=scan,K=K,d=d,rv=rv,tv=tv,inl=ninl,med=med,score=s,cam=(C[0]+X0,C[1]+Y0,C[2]),sun=sun)
