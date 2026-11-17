import numpy as np, cv2, json, sys
from PIL import Image
G=40.0
mod=np.asarray(Image.open('big/mod10.png').convert('RGB')).astype(np.int16)
r,g,b=mod[...,0],mod[...,1],mod[...,2]
pm=((r>g+3)&(r+g+b>300)&(b<r)).astype(np.float32)
D=cv2.resize(pm,None,fx=10/G,fy=10/G,interpolation=cv2.INTER_AREA)       # 1000x1000 @40 m
cv2.imwrite('big/pm.png',(D*255).astype(np.uint8))
T=np.load('hc/strip_T.npy',allow_pickle=True).item()
def load(n):
    a=np.asarray(Image.open(f'hc/p14/{n}.jpg').convert('L')); h,w=a.shape; return a[int(h*.06):int(h*.94),int(w*.06):int(w*.94)]
def substrip(frames):
    ref=frames[len(frames)//2]; Ti={n:np.linalg.inv(T[ref])@T[n] for n in frames}
    pts=[]
    for n,M in Ti.items():
        a=load(n); h,w=a.shape; pts.append((M@np.array([[0,0,1],[w,0,1],[w,h,1],[0,h,1]]).T)[:2].T)
    pts=np.concatenate(pts); mn=pts.min(0); W,H=np.ceil(pts.max(0)-mn).astype(int); S=np.array([[1,0,-mn[0]],[0,1,-mn[1]],[0,0,1.]])
    acc=np.zeros((H,W),np.float32); cnt=np.zeros((H,W),np.float32)
    for n,M in Ti.items():
        a=load(n).astype(np.float32); a=cv2.GaussianBlur(a,(0,0),1.5)
        t=np.percentile(a,[50,97]); m=(a>t[0]+0.45*(t[1]-t[0])).astype(np.float32)   # bright = open ground
        A=(S@M)[:2].astype(np.float32); acc+=cv2.warpAffine(m,A,(W,H)); cnt+=cv2.warpAffine(np.ones_like(m),A,(W,H))
    return np.where(cnt>0,acc/np.maximum(cnt,1),0),(cnt>0).astype(np.float32),S,ref
frames=[int(x) for x in sys.argv[1].split(',')]
P0,V0,S,ref=substrip(frames); cv2.imwrite('hc/sub_mask.png',(P0*255).astype(np.uint8)); print('substrip',P0.shape,'open frac',P0.sum()/V0.sum())
best=[]
for mpp in (11.5,12.5,13.5,14.5):
    k=mpp/G; p=cv2.resize(P0,None,fx=k,fy=k,interpolation=cv2.INTER_AREA); v=(cv2.resize(V0,None,fx=k,fy=k,interpolation=cv2.INTER_AREA)>0.99).astype(np.float32)
    h,w=p.shape; Sz=int(np.hypot(h,w))+2
    pad=lambda a:cv2.copyMakeBorder(a,(Sz-h)//2,Sz-h-(Sz-h)//2,(Sz-w)//2,Sz-w-(Sz-w)//2,cv2.BORDER_CONSTANT,value=0)
    pp=pad(p*v); vp=pad(v)
    for rot in range(0,360,3):
        M=cv2.getRotationMatrix2D((Sz/2,Sz/2),rot,1.0); tr=cv2.warpAffine(pp,M,(Sz,Sz)); vr=(cv2.warpAffine(vp,M,(Sz,Sz))>0.95).astype(np.float32)
        n=vr.sum(); tr=(tr-(tr*vr).sum()/n)*vr
        num=cv2.matchTemplate(D,tr,cv2.TM_CCORR); s1=cv2.matchTemplate(D,vr,cv2.TM_CCORR); s2=cv2.matchTemplate(D*D,vr,cv2.TM_CCORR)
        var=np.maximum(s2-s1*s1/n,0); res=num/(np.sqrt(var)*np.linalg.norm(tr)+1e-6); res[var/n<0.004]=0
        _,mx,_,loc=cv2.minMaxLoc(res)
        best.append((mx,mpp,rot,372000+(loc[0]+Sz/2)*G,4476000-(loc[1]+Sz/2)*G))
best.sort(reverse=True)
for x in best[:10]: print('ncc %.3f mpp %.1f rot %d center %.0f %.0f'%x)
print('median',np.median([x[0] for x in best]))
