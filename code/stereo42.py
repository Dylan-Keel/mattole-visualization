import numpy as np, cv2, rasterio
from PIL import Image
s109=np.asarray(Image.open('up/cvl14b109.jpg').convert('L'))[100:1810,90:1820]
s110=np.asarray(Image.open('up/cvl14b110.jpg').convert('L'))[135:1835,95:1805]
A=np.load('A109_110.npy').astype(np.float32)
h,w=s110.shape
w109=cv2.warpAffine(s109,A,(w,h)); valid=cv2.warpAffine(np.ones_like(s109),A,(w,h))>0
cl=lambda a:cv2.createCLAHE(2,(8,8)).apply(a)
flow=cv2.calcOpticalFlowFarneback(cl(s110),cl(w109),None,0.5,6,41,5,7,1.5,0)
b=np.array([A[0,2],A[1,2]]); b/=np.linalg.norm(b)
disp=flow[...,0]*b[0]+flow[...,1]*b[1]; perp=-flow[...,0]*b[1]+flow[...,1]*b[0]
disp[~valid]=np.nan
print('disp pct',np.nanpercentile(disp,[2,25,50,75,98]),'perp pct',np.nanpercentile(perp[valid],[2,50,98]))
np.save('disp42.npy',disp)
v=disp.copy(); lo,hi=np.nanpercentile(v,[2,98]); v=np.clip((v-lo)/(hi-lo),0,1); v[np.isnan(v)]=0
cv2.imwrite('disp42.jpg',(v*255).astype(np.uint8))
