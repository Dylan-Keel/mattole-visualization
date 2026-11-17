import numpy as np, cv2, rasterio
from PIL import Image
ref=rasterio.open('ref/ref2m.tif').read(1)
crops={'cvl14b110':(95,135,1805,1835),'cvl14b109':(90,100,1820,1810)}
S={k:np.asarray(Image.open(f'up/{k}.jpg').convert('L'))[c[1]:c[3],c[0]:c[2]] for k,c in crops.items()}
# relative transform 109 -> 110
sift=cv2.SIFT_create(8000)
ka,da=sift.detectAndCompute(S['cvl14b109'],None); kb,db=sift.detectAndCompute(S['cvl14b110'],None)
m=cv2.BFMatcher().knnMatch(da,db,k=2); g=[p for p,q in m if p.distance<0.7*q.distance]
A,inl=cv2.estimateAffinePartial2D(np.float32([ka[x.queryIdx].pt for x in g]),np.float32([kb[x.trainIdx].pt for x in g]),ransacReprojThreshold=8)
print('109->110',len(g),inl.sum(),A)
np.save('A109_110.npy',A)
G=16.0
def mask(a,mpp):
    a=cv2.GaussianBlur(a,(0,0),6/mpp*2)
    a=cv2.resize(a,None,fx=mpp/G,fy=mpp/G,interpolation=cv2.INTER_AREA)
    t,_=cv2.threshold(a,0,255,cv2.THRESH_OTSU); return (a>t).astype(np.float32)
# mosaic 109 into 110 frame for a bigger template
h,w=S['cvl14b110'].shape
off=(0,900)
Ht=np.float32([[1,0,off[0]],[0,1,off[1]]])
canvas=cv2.warpAffine(S['cvl14b110'],Ht,(w,h+900))
A2=np.vstack([A,[0,0,1]]); A2=(np.vstack([Ht,[0,0,1]])@A2)[:2]
c109=cv2.warpAffine(S['cvl14b109'],A2.astype(np.float32),(w,h+900))
valid=((canvas>0)|(c109>0))
mos=np.where(canvas>0,canvas,c109); cv2.imwrite('mos42.jpg',mos)
x0,y0=(388000-384000)//2,(4468000-4464000)//2; x1,y1=(399000-384000)//2,(4468000-4451000)//2
R=mask(ref[y0:y1,x0:x1],2.0)
best=[]
for sc in (2.45,2.6,2.75,2.9):
    T0=mask(mos,sc); V0=cv2.resize(valid.astype(np.float32),(T0.shape[1],T0.shape[0]))
    hh,ww=T0.shape; D=int(np.hypot(hh,ww))+2
    pad=lambda a:cv2.copyMakeBorder(a,(D-hh)//2,D-hh-(D-hh)//2,(D-ww)//2,D-ww-(D-ww)//2,cv2.BORDER_CONSTANT,value=0)
    T0=pad(T0); V0=pad(V0)
    for rot in range(0,360,3):
        M=cv2.getRotationMatrix2D((D/2,D/2),rot,1.0)
        T=cv2.warpAffine(T0,M,(D,D)); V=(cv2.warpAffine(V0,M,(D,D))>0.9).astype(np.float32)
        if D>=min(R.shape): continue
        res=cv2.matchTemplate(R,T,cv2.TM_CCOEFF_NORMED,mask=V); res[~np.isfinite(res)]=-1
        _,mx,_,loc=cv2.minMaxLoc(res)
        best.append((mx,sc,rot,388000+(loc[0]+D/2)*G,4464000-(loc[1]+D/2)*G))
best.sort(reverse=True)
for b in best[:10]: print('%.3f mpp %.2f rot %d mosaic-center %.0f %.0f'%b)
