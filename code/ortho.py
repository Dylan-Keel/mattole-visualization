import numpy as np, cv2, rasterio, sys, json
from rasterio.transform import from_origin
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
REF=rasterio.open('ref/ref2m.tif'); refimg=REF.read(1); RT=REF.transform
DEMS=rasterio.open('ref/dem10.tif'); dem=DEMS.read(1); DT=DEMS.transform
X0,Y0=393000.,4458000.
def zat(X,Y):
    c=(np.asarray(X)-DT.c)/DT.a-0.5; r=(np.asarray(Y)-DT.f)/DT.e-0.5
    c=c.astype('float32').ravel(); r=r.astype('float32').ravel(); n=c.size; pad=(-n)%1000
    c=np.pad(c,(0,pad)).reshape(-1,1000); r=np.pad(r,(0,pad)).reshape(-1,1000)
    o=np.concatenate([cv2.remap(dem,c[i:i+20000],r[i:i+20000],cv2.INTER_LINEAR) for i in range(0,len(c),20000)])
    return o.ravel()[:n].reshape(np.shape(X))
def clahe(a,clip=3,t=8): return cv2.createCLAHE(clip,(t,t)).apply(a)
def coarse(scan,mpp_scan,work=5.0,refwin=None):
    s=mpp_scan/work; a=cv2.resize(scan,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
    rs=2.0/work
    x0,y0,x1,y1=refwin if refwin else (0,0,refimg.shape[1],refimg.shape[0])
    b=cv2.resize(refimg[y0:y1,x0:x1],None,fx=rs,fy=rs,interpolation=cv2.INTER_AREA)
    sift=cv2.SIFT_create(nfeatures=40000,contrastThreshold=0.02)
    ka,da=sift.detectAndCompute(clahe(a),None); kb,db=sift.detectAndCompute(clahe(b),None)
    m=cv2.FlannBasedMatcher(dict(algorithm=1,trees=8),dict(checks=128)).knnMatch(da,db,k=2)
    good=[p for p,q in m if p.distance<0.8*q.distance]
    pa=np.float32([ka[g.queryIdx].pt for g in good])/s
    pb=np.float32([kb[g.trainIdx].pt for g in good])/rs+np.float32([x0,y0])
    H,mask=cv2.estimateAffinePartial2D(pa,pb,method=cv2.RANSAC,ransacReprojThreshold=60/2.0,maxIters=20000,confidence=0.999)
    mask=mask.ravel().astype(bool); print('coarse matches',len(good),'inliers',mask.sum(),flush=True)
    return pa[mask],pb[mask],H
def world(pb):
    X=RT.c+pb[:,0]*RT.a; Y=RT.f+pb[:,1]*RT.e; Z=zat(X,Y); return np.c_[X-X0,Y-Y0,Z].astype(np.float64)
def K_of(f,w,h): return np.array([[f,0,w/2],[0,f,h/2],[0,0,1.]])
def solve(P,p,f,w,h,dist=None,fix_f=True):
    K=K_of(f,w,h); d=np.zeros(5) if dist is None else dist
    # world Y up vs image y down: fine, PnP handles via rotation (reflection impossible) -> flip Y sign handled by using left-handed? use Z-up right-handed world; image is a view from above, OK.
    ok,rv,tv,inl=cv2.solvePnPRansac(P,p.astype(np.float64),K,d,iterationsCount=5000,reprojectionError=25,flags=cv2.SOLVEPNP_EPNP)
    inl=inl.ravel(); rv,tv=cv2.solvePnPRefineLM(P[inl],p[inl].astype(np.float64),K,d,rv,tv)
    return K,d,rv,tv,inl
def calib(P,p,K,d,rv,tv,w,h,free_dist=True):
    flags=cv2.CALIB_USE_INTRINSIC_GUESS|cv2.CALIB_FIX_ASPECT_RATIO|cv2.CALIB_ZERO_TANGENT_DIST|cv2.CALIB_FIX_K2|cv2.CALIB_FIX_K3|cv2.CALIB_FIX_PRINCIPAL_POINT
    if not free_dist: flags|=cv2.CALIB_FIX_K1
    rms,K2,d2,rvs,tvs=cv2.calibrateCamera([P.astype(np.float32)],[p.astype(np.float32)],(w,h),K.copy(),d.copy(),flags=flags)
    return rms,K2,d2.ravel(),rvs[0],tvs[0]
def proj(P,K,d,rv,tv): return cv2.projectPoints(P,rv,tv,K,d)[0].reshape(-1,2)
def dense(scan,mpp,K,d,rv,tv,step=150,win=48,search=40,area=None):
    # grid of ref points; warp local scan patch into ref geometry via local affine from projection, then NCC
    h,w=scan.shape; pts=[];wp=[]
    xs=np.arange(RT.c+200,RT.c+refimg.shape[1]*2-200,step); ys=np.arange(RT.f-refimg.shape[0]*2+200,RT.f-200,step)
    GX,GY=np.meshgrid(xs,ys); GX=GX.ravel(); GY=GY.ravel(); GZ=zat(GX,GY)
    c=proj(np.c_[GX-X0,GY-Y0,GZ],K,d,rv,tv)
    ok=(c[:,0]>300)&(c[:,0]<w-300)&(c[:,1]>300)&(c[:,1]<h-300)
    R=win+search
    for X,Y,Z in zip(GX[ok],GY[ok],GZ[ok]):
        # local grid in world at 2 m, size 2R+1
        lx=X+(np.arange(-R,R+1))*2.0; ly=Y-(np.arange(-R,R+1))*2.0
        LX,LY=np.meshgrid(lx,ly); LZ=zat(LX,LY)
        q=proj(np.c_[LX.ravel()-X0,LY.ravel()-Y0,LZ.ravel()],K,d,rv,tv).astype('float32')
        patch=cv2.remap(scan,q[:,0].reshape(LX.shape),q[:,1].reshape(LX.shape),cv2.INTER_LINEAR)
        rc=int((X-RT.c)/2); rr=int((RT.f-Y)/2)
        tmpl=refimg[rr-win:rr+win+1,rc-win:rc+win+1]
        if tmpl.shape!=(2*win+1,2*win+1) or tmpl.std()<8 or patch.std()<5: continue
        res=cv2.matchTemplate(clahe(patch,2,4),clahe(tmpl,2,4),cv2.TM_CCOEFF_NORMED)
        _,mx,_,loc=cv2.minMaxLoc(res)
        # peak uniqueness
        r2=res.copy(); cv2.circle(r2,loc,6,-1,-1); second=r2.max()
        if mx<0.35 or mx-second<0.08: continue
        dx=loc[0]-search; dy=loc[1]-search   # template found at offset in patch (world px, 2 m)
        # the ref point (X,Y) appears in the scan where patch pixel (R+dx,R+dy) samples from
        ip=q.reshape(LX.shape+(2,))[R+dy,R+dx]
        pts.append(ip); wp.append([X-X0,Y-Y0,Z])
    return np.array(wp,np.float64),np.array(pts,np.float64)
def ortho(scan,K,d,rv,tv,bounds,res):
    x0,y0,x1,y1=bounds; W=int((x1-x0)/res); H=int((y1-y0)/res)
    xs=x0+(np.arange(W)+.5)*res; ys=y1-(np.arange(H)+.5)*res
    out=np.zeros((H,W),scan.dtype); 
    for r0 in range(0,H,500):
        LX,LY=np.meshgrid(xs,ys[r0:r0+500]); LZ=zat(LX,LY)
        q=proj(np.c_[LX.ravel()-X0,LY.ravel()-Y0,LZ.ravel()],K,d,rv,tv).astype('float32')
        out[r0:r0+500]=cv2.remap(scan,q[:,0].reshape(LX.shape),q[:,1].reshape(LX.shape),cv2.INTER_CUBIC)
    return out
def run(path,name,f_mm,film_mm,crop=None,work=5.0,refwin=None):
    scan=np.asarray(Image.open(path).convert('L'))
    if crop: scan=scan[crop[1]:crop[3],crop[0]:crop[2]]
    h,w=scan.shape; pxmm=film_mm/max(h,w); f=f_mm/pxmm
    pa,pb,H=coarse(scan,MPP[name],work,refwin)
    P=world(pb); K,d,rv,tv,inl=solve(P,pa,f,w,h)
    e=np.linalg.norm(proj(P[inl],K,d,rv,tv)-pa[inl],axis=1); print('pnp inliers',len(inl),'rms px',np.sqrt((e**2).mean()),flush=True)
    for it,(step,search) in enumerate([(300,40),(200,25),(150,15)]):
        P2,p2=dense(scan,MPP[name],K,d,rv,tv,step=step,search=search)
        K0,d0,rv,tv,inl=solve(P2,p2,K[0,0],w,h,d)
        rms,K,d,rv,tv=calib(P2[inl],p2[inl],K0,d0,rv,tv,w,h)
        e=np.linalg.norm(proj(P2[inl],K,d,rv,tv)-p2[inl],axis=1)
        C=-cv2.Rodrigues(rv)[0].T@tv.ravel()
        print(f'iter {it}: dense pts {len(P2)} inl {len(inl)} rms {rms:.2f}px med {np.median(e):.2f} f {K[0,0]:.0f} k1 {d[0]:.4f} cam {C[0]+X0:.0f},{C[1]+Y0:.0f},{C[2]:.0f}',flush=True)
    np.savez(f'pose_{name}.npz',K=K,d=d,rv=rv,tv=tv,P=P2[inl],p=p2[inl])
    return scan,K,d,rv,tv
MPP={}
if __name__=='__main__':
    name,path,f_mm,film_mm,mpp=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4]),float(sys.argv[5])
    MPP[name]=mpp
    scan,K,d,rv,tv=run(path,name,f_mm,film_mm)
    o=ortho(scan,K,d,rv,tv,(392000,4456700,394400,4459400),0.5)
    with rasterio.open(f'master/{name}.tif','w',driver='GTiff',width=o.shape[1],height=o.shape[0],count=1,dtype='uint8',crs='EPSG:26910',transform=from_origin(392000,4459400,0.5,0.5),compress='deflate') as ds: ds.write(o,1)
    Image.fromarray(o[::4,::4]).save(f'{name}_ortho_th.jpg')
