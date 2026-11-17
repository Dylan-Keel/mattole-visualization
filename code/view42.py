import numpy as np, cv2, sys, json
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
import ortho
scan109=np.asarray(Image.open('up/cvl14b109.jpg').convert('L'))[100:1810,90:1820]
def sim_warp(scan,cx,cy,mpp,rotdeg,b,res):
    # world->scan: scan center maps to (cx,cy); rot = rotation of image relative to north-up
    x0,y0,x1,y1=b; W=int((x1-x0)/res); H=int((y1-y0)/res)
    X,Y=np.meshgrid(x0+(np.arange(W)+.5)*res, y1-(np.arange(H)+.5)*res)
    dx=(X-cx)/mpp; dy=-(Y-cy)/mpp; t=np.radians(rotdeg); c,s=np.cos(t),np.sin(t)
    u=c*dx-s*dy+scan.shape[1]/2; v=s*dx+c*dy+scan.shape[0]/2
    return cv2.remap(scan,u.astype('float32'),v.astype('float32'),cv2.INTER_LINEAR)
def ref93(b,res):
    scan=np.asarray(Image.open('napp1993.tif').convert('L')); z=np.load('pose_napp1993.npz')
    return ortho.ortho(scan,z['K'],z['d'],z['rv'],z['tv'],b,res)
def grid(img,b,res,step=500):
    c=cv2.cvtColor(img,cv2.COLOR_GRAY2BGR); x0,y0,x1,y1=b
    for x in range(int(np.ceil(x0/step)*step),x1,step):
        p=int((x-x0)/res); cv2.line(c,(p,0),(p,c.shape[0]),(0,255,255),1); cv2.putText(c,'%.1f'%(x/1000),(p+2,12),0,0.4,(0,255,255),1)
    for y in range(int(np.ceil(y0/step)*step),y1,step):
        p=int((y1-y)/res); cv2.line(c,(0,p),(c.shape[1],p),(0,255,255),1); cv2.putText(c,'%.1f'%(y/1000),(2,p-2),0,0.4,(0,255,255),1)
    return c
if __name__=='__main__':
    cx,cy,mpp,rot=map(float,sys.argv[1:5]); b=tuple(int(v) for v in sys.argv[5:9]); res=float(sys.argv[9]); out=sys.argv[10]
    a=grid(sim_warp(scan109,cx,cy,mpp,rot,b,res),b,res); r=grid(ref93(b,res),b,res)
    cv2.imwrite(out,np.concatenate([a,np.zeros((a.shape[0],6,3),np.uint8),r],1))
