import numpy as np, cv2
from PIL import Image
G=20.0
# modern prairie mask from 2005 NAIP colour tiles (2 m)
M=np.zeros((9000,9000),np.uint8)
for i in range(3):
    for j in range(3):
        a=np.asarray(Image.open(f'ref/n_{i}_{j}.img').convert('RGB')).astype(np.int16)
        r,g,b=a[...,0],a[...,1],a[...,2]
        M[(2-i)*3000:(3-i)*3000,j*3000:(j+1)*3000]=((r>g-2)&(r+g+b>330)).astype(np.uint8)
M=cv2.morphologyEx(M,cv2.MORPH_OPEN,np.ones((5,5),np.uint8))
cv2.imwrite('prairie05.png',M[::4,::4]*255)
Mg=cv2.resize(M.astype(np.float32),None,fx=2/G,fy=2/G,interpolation=cv2.INTER_AREA)
def pmask(scan):
    a=cv2.GaussianBlur(scan,(0,0),3)
    t,_=cv2.threshold(a,0,255,cv2.THRESH_OTSU); return (a>t).astype(np.float32)
res={}
for nm,c in {'cvl14b110':(95,135,1805,1835),'cvl14b109':(90,100,1820,1810)}.items():
    scan=np.asarray(Image.open(f'up/{nm}.jpg').convert('L'))[c[1]:c[3],c[0]:c[2]]
    P0=pmask(scan); print(nm,'1942 open fraction',P0.mean())
    best=[]
    for sc in (2.5,2.65,2.8,2.95):
        P=cv2.resize(P0,None,fx=sc/G,fy=sc/G,interpolation=cv2.INTER_AREA); F=np.ones_like(P)
        h,w=P.shape; D=int(np.hypot(h,w))+2
        pad=lambda a:cv2.copyMakeBorder(a,(D-h)//2,D-h-(D-h)//2,(D-w)//2,D-w-(D-w)//2,cv2.BORDER_CONSTANT,value=0)
        P=pad(P);F=pad(F)
        for rot in range(0,360,3):
            R=cv2.getRotationMatrix2D((D/2,D/2),rot,1.0)
            Pr=cv2.warpAffine(P,R,(D,D)); Fr=cv2.warpAffine(F,R,(D,D))
            cMP=cv2.matchTemplate(Mg,Pr,cv2.TM_CCORR); cMF=cv2.matchTemplate(Mg,Fr,cv2.TM_CCORR)
            iou=cMP/(cMF+Pr.sum()-cMP+1e-6); iou[cMF<60]=0   # need >= 60 cells (2.4 ha*) of modern prairie in footprint
            _,mx,_,loc=cv2.minMaxLoc(iou)
            best.append((mx,sc,rot,384000+(loc[0]+D/2)*G,4468000-(loc[1]+D/2)*G))
    best.sort(reverse=True); res[nm]=best
    for b in best[:8]: print('  iou %.3f mpp %.2f rot %d center %.0f %.0f'%b)
