import numpy as np, cv2, rasterio
G=20.0
dem=rasterio.open('ref/dem10.tif').read(1); dem=cv2.resize(dem,None,fx=0.5,fy=0.5,interpolation=cv2.INTER_AREA)  # 20 m, 900x900, origin 384000,4468000
def hpf(a,sig): return a-cv2.GaussianBlur(a,(0,0),sig)
D=hpf(dem,30)
disp=np.load('disp42.npy'); val=~np.isnan(disp); d0=np.where(val,disp,0).astype(np.float32)
ys,xs=np.where(val); y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
d0=d0[y0:y1,x0:x1]; v0=val[y0:y1,x0:x1].astype(np.float32)
print('overlap crop offset',x0,y0,d0.shape)
best=[]
for sc in (2.5,2.65,2.8,2.95,3.1):
    k=sc/G
    d=cv2.resize(d0,None,fx=k,fy=k,interpolation=cv2.INTER_AREA); v=cv2.resize(v0,None,fx=k,fy=k,interpolation=cv2.INTER_AREA)
    # normalised high-pass with mask
    bl=cv2.GaussianBlur(d*v,(0,0),30)/np.maximum(cv2.GaussianBlur(v,(0,0),30),1e-3); t=(d-bl)*(v>0.99)
    h,w=t.shape; S=int(np.hypot(h,w))+2
    pad=lambda a:cv2.copyMakeBorder(a,(S-h)//2,S-h-(S-h)//2,(S-w)//2,S-w-(S-w)//2,cv2.BORDER_CONSTANT,value=0)
    tp=pad(t); vp=pad((v>0.99).astype(np.float32))
    for rot in range(0,360,2):
        M=cv2.getRotationMatrix2D((S/2,S/2),rot,1.0)
        tr=cv2.warpAffine(tp,M,(S,S)); vr=(cv2.warpAffine(vp,M,(S,S))>0.95).astype(np.float32); tr*=vr
        res=cv2.matchTemplate(D,tr,cv2.TM_CCORR_NORMED,mask=vr); res[~np.isfinite(res)]=0
        for sign in (1,-1):
            r=res*sign; _,mx,_,loc=cv2.minMaxLoc(r)
            best.append((mx,sign,sc,rot,384000+(loc[0]+S/2)*G,4468000-(loc[1]+S/2)*G))
best.sort(reverse=True)
for b in best[:12]: print('corr %.3f sign %d mpp %.2f rot %d overlap-center %.0f %.0f'%b)
