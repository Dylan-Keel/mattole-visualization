import numpy as np, cv2, rasterio, sys
from PIL import Image
ref=rasterio.open('ref/ref2m.tif').read(1)
G=16.0
def prep(a,mpp):
    a=cv2.resize(a,None,fx=mpp/G,fy=mpp/G,interpolation=cv2.INTER_AREA).astype(np.float32)
    bg=cv2.GaussianBlur(a,(0,0),40); a=a-bg   # remove broad tone
    return cv2.GaussianBlur(a,(0,0),1.2)
R=prep(ref,2.0)   # 1125x1125 covers 384-402E, 4450-4468N
crops={'cvl14b110':(95,135,1805,1835),'cvl14b109':(90,100,1820,1810)}
for nm,c in crops.items():
    scan=np.asarray(Image.open(f'up/{nm}.jpg').convert('L'))[c[1]:c[3],c[0]:c[2]]
    best=[]
    for sc in (2.4,2.55,2.7,2.85,3.0):
        S=prep(scan,sc); h,w=S.shape
        for rot in range(0,360,4):
            M=cv2.getRotationMatrix2D((w/2,h/2),rot,1.0)
            T=cv2.warpAffine(S,M,(w,h),flags=cv2.INTER_LINEAR,borderValue=0)
            m=np.zeros((h,w),np.uint8); cv2.circle(m,(w//2,h//2),int(min(h,w)*0.48),1,-1)
            T=T[int(h*.02):int(h*.98),int(w*.02):int(w*.98)]; mm=m[int(h*.02):int(h*.98),int(w*.02):int(w*.98)]
            res=cv2.matchTemplate(R,T,cv2.TM_CCORR_NORMED,mask=mm.astype(np.float32))
            res[~np.isfinite(res)]=0
            _,mx,_,loc=cv2.minMaxLoc(res)
            cx=384000+(loc[0]+T.shape[1]/2)*G; cy=4468000-(loc[1]+T.shape[0]/2)*G
            best.append((mx,sc,rot,cx,cy))
    best.sort(reverse=True)
    print(nm); [print('  %.3f mpp %.2f rot %d center %.0f %.0f'%b) for b in best[:8]]
