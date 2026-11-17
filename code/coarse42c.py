import numpy as np, cv2
from PIL import Image
W=np.load('wide93.npy')  # 4 m/px, origin (389000,4461000), 2000x2000; valid where >0
G=12.0
def hp(a,mpp):
    a=cv2.resize(a,None,fx=mpp/G,fy=mpp/G,interpolation=cv2.INTER_AREA).astype(np.float32)
    return cv2.GaussianBlur(a,(0,0),1.5)-cv2.GaussianBlur(a,(0,0),25)
R=hp(W,4.0); Rv=cv2.resize((W>0).astype(np.float32),(R.shape[1],R.shape[0]))>0.99
R[~Rv]=0
scan=np.asarray(Image.open('up/cvl14b109.jpg').convert('L'))[100:1810,90:1820]
best=[]
for sc in (2.4,2.5,2.6,2.7,2.8,2.9):
    T0=hp(scan,sc); h,w=T0.shape
    for rot in range(150,211,2):
        M=cv2.getRotationMatrix2D((w/2,h/2),rot,1.0); T=cv2.warpAffine(T0,M,(w,h))
        m=np.zeros((h,w),np.float32); cv2.circle(m,(w//2,h//2),int(min(h,w)*0.47),1,-1); T=T*m
        # pad reference so template can hang off
        P=120; Rp=cv2.copyMakeBorder(R,P,P,P,P,cv2.BORDER_CONSTANT,value=0)
        res=cv2.matchTemplate(Rp,T,cv2.TM_CCORR_NORMED)
        _,mx,_,loc=cv2.minMaxLoc(res)
        cx=389000+(loc[0]-P+w/2)*G; cy=4461000-(loc[1]-P+h/2)*G
        best.append((mx,sc,rot,cx,cy))
best.sort(reverse=True)
for b in best[:10]: print('%.3f mpp %.2f rot %d center109 %.0f %.0f'%b)
