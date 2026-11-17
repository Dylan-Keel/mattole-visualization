import numpy as np, cv2, itertools
from PIL import Image
import fit42
from ortho import zat, X0, Y0
scan=np.asarray(Image.open('up/cvl14b109.jpg').convert('L'))[100:1810,90:1820]
h,w=scan.shape; f=209.55/228.6*w
G=12.0; b=(389600,4454800,395400,4460400)
W=int((b[2]-b[0])/G); H=int((b[3]-b[1])/G)
X,Y=np.meshgrid(b[0]+(np.arange(W)+.5)*G, b[3]-(np.arange(H)+.5)*G); Z=zat(X,Y)
P=np.c_[X.ravel()-X0,Y.ravel()-Y0,Z.ravel()]
ref=fit42.REF; rb=fit42.B
r=ref[int((rb[3]-b[3])/3):int((rb[3]-b[1])/3), int((b[0]-rb[0])/3):int((b[2]-rb[0])/3)]
r=cv2.resize(r,(W,H),interpolation=cv2.INTER_AREA).astype(np.float32); rv_=r>0
hp=lambda a:cv2.GaussianBlur(a,(0,0),1.0)-cv2.GaussianBlur(a,(0,0),15)
R=hp(r)
sb=cv2.GaussianBlur(scan,(0,0),G/2.8/2).astype(np.float32)
res=[]
for mpp in (2.6,2.7,2.8,2.9,3.0):
  for rot in range(168,193,2):
    K,d,rv,tv=fit42.init_pose(391700,4457100,mpp,rot,f,w,h)
    Rm=cv2.Rodrigues(rv)[0]
    for cx in range(390900,392700,100):
      for cy in range(4456300,4457900,100):
        Zc=float(zat(np.array([cx]),np.array([cy]))[0])+f*mpp
        C=np.array([cx-X0,cy-Y0,Zc]); pc=(P-C)@Rm.T
        u=(f*pc[:,0]/pc[:,2]+w/2).reshape(H,W).astype(np.float32); v=(f*pc[:,1]/pc[:,2]+h/2).reshape(H,W).astype(np.float32)
        img=cv2.remap(sb,u,v,cv2.INTER_LINEAR,borderValue=0)
        m=(img>0)&rv_
        if m.sum()<W*H*0.3: continue
        a=hp(img)[m]; bb=R[m]; a=a-a.mean(); bb=bb-bb.mean()
        res.append(((a*bb).sum()/np.sqrt((a*a).sum()*(bb*bb).sum()),mpp,rot,cx,cy))
res.sort(reverse=True)
for x in res[:12]: print('ncc %.3f mpp %.1f rot %d cx %d cy %d'%x)
print('median',np.median([x[0] for x in res]),'n',len(res))
