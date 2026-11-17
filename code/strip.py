import numpy as np, cv2, json
from PIL import Image
def load(n):
    a=np.asarray(Image.open(f'hc/p14/{n}.jpg').convert('L'))
    # crop to image area: find bbox of mid-tones (exclude white/black borders) crudely via central 88%
    h,w=a.shape; return a[int(h*.06):int(h*.94),int(w*.06):int(w*.94)]
ns=list(range(100,119)); I={n:load(n) for n in ns}
sift=cv2.SIFT_create(4000,contrastThreshold=0.02)
big={n:cv2.resize(I[n],None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC) for n in ns}
F={n:sift.detectAndCompute(cv2.createCLAHE(2,(8,8)).apply(big[n]),None) for n in ns}
T={109:np.eye(3)}; ok={}
def rel(a,b):
    ka,da=F[a]; kb,db=F[b]
    m=cv2.BFMatcher().knnMatch(da,db,k=2); g=[p for p,q in m if p.distance<0.75*q.distance]
    if len(g)<8: return None,0
    A,inl=cv2.estimateAffinePartial2D(np.float32([ka[x.queryIdx].pt for x in g])/2,np.float32([kb[x.trainIdx].pt for x in g])/2,ransacReprojThreshold=3)
    return (np.vstack([A,[0,0,1]]),int(inl.sum())) if A is not None else (None,0)
for seq in (range(110,119),range(108,99,-1)):
    for n in seq:
        prev=n-1 if n>109 else n+1
        if prev not in T: break
        A,c=rel(n,prev); print(n,'->',prev,'inliers',c, None if A is None else (round(float(np.hypot(A[0,0],A[1,0])),3),A[0,2].round(1),A[1,2].round(1)))
        if A is None or c<12: break
        T[n]=T[prev]@A
np.save('hc/strip_T.npy',{k:v for k,v in T.items()},allow_pickle=True)
# mosaic
pts=[]
for n,M in T.items():
    h,w=I[n].shape; c=np.array([[0,0,1],[w,0,1],[w,h,1],[0,h,1]]).T; pts.append((M@c)[:2].T)
pts=np.concatenate(pts); mn=pts.min(0); mx=pts.max(0); W,H=(np.ceil(mx-mn)).astype(int)
S=np.array([[1,0,-mn[0]],[0,1,-mn[1]],[0,0,1.]])
mos=np.zeros((H,W),np.float32); cnt=np.zeros((H,W),np.float32)
for n,M in sorted(T.items()):
    A=(S@M)[:2].astype(np.float32); a=I[n].astype(np.float32); a=(a-a.mean())/a.std()*40+110
    mos+=cv2.warpAffine(a,A,(W,H)); cnt+=cv2.warpAffine(np.ones_like(a),A,(W,H))
mos=np.where(cnt>0,mos/np.maximum(cnt,1),0); cv2.imwrite('hc/strip.png',np.clip(mos,0,255).astype(np.uint8))
json.dump({'S':S.tolist(),'frames':sorted(T)},open('hc/strip.json','w')); print(W,H,sorted(T))
