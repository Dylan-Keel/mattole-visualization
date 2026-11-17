import numpy as np, cv2, rasterio
G=20.0
dem=rasterio.open('ref/dem20_big.tif').read(1)  # 20 m, 900x900, origin 384000,4468000
def hpf(a,sig): return a-cv2.GaussianBlur(a,(0,0),sig)
D=hpf(dem,30)
disp=np.load('disp42.npy'); val=~np.isnan(disp); d0=np.where(val,disp,0).astype(np.float32)
ys,xs=np.where(val); y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
d0=d0[y0:y1,x0:x1]; v0=val[y0:y1,x0:x1].astype(np.float32)
print('overlap crop offset',x0,y0,d0.shape)
best=[]
for sc in (2.5,2.7,2.9):
    k=sc/G
    d=cv2.resize(d0,None,fx=k,fy=k,interpolation=cv2.INTER_AREA); v=cv2.resize(v0,None,fx=k,fy=k,interpolation=cv2.INTER_AREA)
    # normalised high-pass with mask
    bl=cv2.GaussianBlur(d*v,(0,0),30)/np.maximum(cv2.GaussianBlur(v,(0,0),30),1e-3); t=(d-bl)*(v>0.99)
    h,w=t.shape; S=int(np.hypot(h,w))+2
    pad=lambda a:cv2.copyMakeBorder(a,(S-h)//2,S-h-(S-h)//2,(S-w)//2,S-w-(S-w)//2,cv2.BORDER_CONSTANT,value=0)
    tp=pad(t); vp=pad((v>0.99).astype(np.float32))
    for rot in range(0,360,3):
        M=cv2.getRotationMatrix2D((S/2,S/2),rot,1.0)
        tr=cv2.warpAffine(tp,M,(S,S)); vr=(cv2.warpAffine(vp,M,(S,S))>0.95).astype(np.float32); tr*=vr
        n=vr.sum(); tr=(tr-tr.sum()/n)*vr
        num=cv2.matchTemplate(D,tr,cv2.TM_CCORR); s1=cv2.matchTemplate(D,vr,cv2.TM_CCORR); s2=cv2.matchTemplate(D*D,vr,cv2.TM_CCORR)
        var=np.maximum(s2-s1*s1/n,0); res=num/(np.sqrt(var)*np.linalg.norm(tr)+1e-6); res[np.sqrt(var/n)<25]=0
        for sign in (1,-1):
            r=res*sign; _,mx,_,loc=cv2.minMaxLoc(r)
            best.append((mx,sign,sc,rot,372000+(loc[0]+S/2)*G,4476000-(loc[1]+S/2)*G))
best.sort(reverse=True)
for b in best[:12]: print('corr %.3f sign %d mpp %.2f rot %d overlap-center %.0f %.0f'%b)
